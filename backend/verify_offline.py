"""Run the judge's local-only offline acceptance smoke against a running API."""
import json
import os
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from app.schemas import ScenarioBundle

API = os.environ.get("PHENOCREDIT_API_URL", "http://127.0.0.1:8000").rstrip("/")
if urlparse(API).hostname not in {"127.0.0.1", "localhost", "::1"}:
    raise SystemExit("Offline verification only permits a loopback API URL.")
OUT = Path(__file__).resolve().parents[1] / "demo" / "verification"
OUT.mkdir(parents=True, exist_ok=True)
WALKTHROUGH = json.loads((Path(__file__).resolve().parents[1] / "data" / "fixtures" / "judge-walkthrough.json").read_text(encoding="utf-8"))


def call(path, payload=None):
    request = Request(
        API + path,
        data=json.dumps(payload).encode("utf-8") if payload is not None else None,
        headers={"Content-Type": "application/json"},
    )
    with urlopen(request, timeout=10) as response:
        return json.load(response)


def run_pass():
    health = call("/health")
    assert health["status"] == "ok" and health["demo_seeded"]
    seed = call("/api/demo/seed", {})
    assert seed["status"] == "seeded" and seed["borrower_count"] == 2

    borrowers = call("/api/borrowers")
    assert len(borrowers) == 2 and all(row["synthetic"] for row in borrowers)
    borrower_id = borrowers[0]["id"]
    assert call(f"/api/borrowers/{borrower_id}")["synthetic"]
    assert call(f"/api/borrowers/{borrower_id}/loan")["synthetic"]
    sources = call("/api/sources")["sources"]
    assert any(row["status"] == "assumed" for row in sources)
    assert any(row["status"] == "unavailable" for row in sources)

    baseline_request = {"borrower_id": borrower_id, "as_of": "2026-10-09"}
    baseline = call("/api/scenarios/evaluate", baseline_request)
    ScenarioBundle.model_validate(baseline)
    baseline_clone = call("/api/scenarios/evaluate", baseline_request)
    assert baseline_clone == baseline, "Identical source version and request must be deterministic."

    heat_request = {"borrower_id": borrower_id, "as_of": "2026-10-09",
                    "overrides": {"heatwave_days": 4, "heatwave_growth_stage": "flowering"}}
    heat = call("/api/scenarios/evaluate", heat_request)
    baseline_context = dict(baseline["baseline"])
    heat_context = dict(heat["baseline"])
    baseline_context.pop("comparison_context_hash", None)
    heat_context.pop("comparison_context_hash", None)
    assert heat_context == baseline_context
    assert heat["comparison_context_hash"] != baseline["comparison_context_hash"]
    assert heat["stress"]["sale_date"] > heat["stress"]["due_date"]
    assert heat["stress"]["cash_gap_inr"] != "0.00"
    assert call("/api/scenarios/evaluate", {**heat_request,
           "overrides": {"heatwave_days": 4, "heatwave_growth_stage": "harvest"}})["stress"]["yield_t_per_ha"] != heat["stress"]["yield_t_per_ha"]

    bridge_request = {"borrower_id": borrower_id, "as_of": "2026-10-09",
                      "overrides": {"heatwave_days": 14, "market_price_change_pct": -70,
                                    "assumed_informal_bridge_inr": 150000}}
    bridge = call("/api/scenarios/evaluate", bridge_request)
    assert bridge["stress"]["formal_balance_end_inr"] == "0.00"
    assert float(bridge["stress"]["informal_balance_end_inr"]) > 0
    assert len(bridge["stress"]["debt_cycle"]) == 3

    walkthrough = call("/api/scenarios/evaluate", WALKTHROUGH["request"])
    expected = WALKTHROUGH["expected"]
    assert walkthrough["stress"]["sale_date"] == expected["stress_sale_date"]
    assert walkthrough["stress"]["cash_pre_due_inr"] == expected["stress_cash_before_due_inr"]
    assert walkthrough["stress"]["cash_gap_inr"] == expected["stress_due_gap_inr"]
    assert walkthrough["action_status"] == expected["action_status"]
    assert walkthrough["scenario_request"]["action_id"] == expected["action_id"]

    candidates = call("/api/interventions/evaluate", heat_request)["candidates"]
    assert len(candidates) == 2 and all(
        item["comparison_context_hash"] == heat["comparison_context_hash"] for item in candidates
    )
    assert len({item["stress_with_action"]["bank_total_due_inr"] for item in candidates}) == 2

    for bundle in (baseline, heat, bridge, *candidates):
        reopened = call(f"/api/scenarios/{bundle['scenario_id']}")
        assert reopened == bundle
        loan = call(f"/api/borrowers/{bundle['borrower_id']}/loan?scenario_id={bundle['scenario_id']}")
        selected = bundle["stress_with_action"] or bundle["stress"]
        assert loan["schedule"] == selected["loan_schedule"]

    catalog_ids = {row["scenario_id"] for row in call("/api/scenarios?limit=100")["scenarios"]}
    assert {baseline["scenario_id"], heat["scenario_id"], bridge["scenario_id"]} <= catalog_ids
    climate = call("/api/climate?region=Nashik&crop=Wheat&as_of=2026-10-09")
    assert climate["weather"]["forecast_issued_at"] is None
    assert climate["ndvi"]["status"] == "unavailable"
    return {
        "status": "passed",
        "api": API,
        "requests": "loopback only; no external source service called",
        "checks": ["health and idempotent seed", "borrower, loan and source provenance",
                   "deterministic cloned assessment", "heat timing and stage sensitivity",
                   "bridge versus formal/total debt", "two aligned interventions",
                   "saved report reopen and loan schedule", "saved catalog", "missing data labels"],
        "scenario_ids": [baseline["scenario_id"], heat["scenario_id"], bridge["scenario_id"], walkthrough["scenario_id"]],
    }


for pass_number in (1, 2):
    evidence = run_pass()
    path = OUT / f"offline-smoke-pass-{pass_number}.json"
    path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(f"Offline acceptance pass {pass_number}/2 passed; evidence: {path.name}")
