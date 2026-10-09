from contextlib import asynccontextmanager
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4
import os
from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.config import PRODUCT_NAME, APP_MODE
from app.auth.service import seed_demo_users
from app.auth.router import router as auth_router
from app.auth.farmer import router as farmer_router
from app.auth.dependencies import require_roles, get_optional_current_user
from app.db import (add_audit_event, append_loan_event, create_application, get_application, get_borrower_record,
                   create_intervention_proposal, get_intervention_proposal, get_loan_record, get_scenario, get_comparison_bundle, list_comparison_bundles, get_source_snapshot, list_applications, list_borrower_records, list_intervention_proposals, list_loan_records,
                   list_scenarios, list_source_records, get_warning_evidence, get_warning_task, ensure_warning_task, transition_warning_task,
                   list_allocation_snapshots, get_allocation_snapshot, save_allocation_snapshot,
                   list_source_refresh_events, list_source_snapshots, list_warning_evidence, save_borrower_record,
                   save_comparison_bundle, save_scenario, seed_demo_records, transition_intervention_proposal, update_application,
                   update_application_with_demo_loan)
from app.schemas import (ApplicationCreate, ApplicationStatusUpdate, BorrowerCreate, LedgerEventCreate,
                         FeatureSnapshotImport, InterventionEvaluationRequest, InterventionProposalCreate,
                         InterventionReviewUpdate, ScenarioBundle, ScenarioRequest, AllocationRequest,
                         WarningWorkflowUpdate)
from app.services.assessment import BORROWERS, SOURCE_VERSION, STAGE_WINDOWS, evaluate_scenario
from app.services.interventions import POLICY as INTERVENTION_POLICY, action_catalog, evaluate_action_candidates, score_action_option
from app.services.allocation import (apply_allocated_candidate, freeze_from_saved_comparisons,
                                     solve_allocation, stable_allocation_id)
from app.services.watchlist import page_watchlist
from app.services.sources import list_data_sources, refresh_pune_historical_weather
from app.services.feature_ingest import freeze_feature_import
from app.services.soil_moisture import get_soil_moisture_telemetry
from app.services.satellite_ndvi import get_satellite_ndvi_telemetry

@asynccontextmanager
async def lifespan(app):
    if APP_MODE == "demo":
        seed_demo_records(BORROWERS, SOURCE_FIXTURES)
        seed_demo_users()
    yield


app = FastAPI(title=PRODUCT_NAME, version="0.2.0", description="Offline synthetic agricultural credit scenario demo", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=(os.getenv("CORS_ALLOWED_ORIGINS", "").split(",") if APP_MODE == "hosted" else ["*"]),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router)
app.include_router(farmer_router)


@app.middleware("http")
async def hosted_route_gate(request: Request, call_next):
    # Legacy portfolio routes are intentionally demo-only until branch scope
    # filters and hosted identity provisioning are available on every query.
    path = request.url.path
    if APP_MODE == "hosted" and path.startswith("/api/") and not path.startswith(("/api/auth/", "/api/private/", "/api/sources", "/api/source-", "/api/data-sources")):
        return JSONResponse({"detail": "Not found"}, status_code=404)
    return await call_next(request)


def source_administration_access(current_user: dict | None = Depends(get_optional_current_user)):
    if APP_MODE == "hosted" and (not current_user or current_user.get("role") != "admin"):
        raise HTTPException(403, "Administrator access required")
    return current_user

SOURCE_FIXTURES = [
    {"id": "demo-finance", "type": "synthetic", "label": "Synthetic demo borrower and loan ledger", "status": "simulated", "version": SOURCE_VERSION, "verified_bytes": False},
    {"id": "weather-scenario", "type": "assumed", "label": "Slider-driven hypothetical weather scenario", "status": "assumed", "version": "scenario-controls-v1", "verified_bytes": False},
    {"id": "crop-calendar", "type": "assumed", "label": "Illustrative crop calendar and yield response", "status": "assumed", "version": "illustrative-v2", "verified_bytes": False},
    {"id": "satellite", "type": "satellite", "label": "NDVI / FPAR", "status": "unavailable", "version": None, "verified_bytes": False},
    {"id": "soil", "type": "soil", "label": "Soil moisture", "status": "unavailable", "version": None, "verified_bytes": False},
    {"id": "market-price", "type": "market_price", "label": "Market price reference", "status": "assumed", "version": "demo-input-v1", "verified_bytes": False},
]


@app.post("/api/demo/seed")
def initialize_demo_database():
    if APP_MODE != "demo":
        raise HTTPException(404, "Not found")
    seed_demo_records(BORROWERS, SOURCE_FIXTURES)
    return {"status": "seeded", "borrower_count": len(list_borrower_records()), "source_version": SOURCE_VERSION}


@app.get("/health")
def health():
    return {"status": "ok", "demo_seeded": bool(list_borrower_records()), "data_mode": "offline_assumptions_and_synthetic_finance"}


@app.get("/api/borrowers")
def borrowers():
    return [{"id": b["id"], "alias": b["alias"], "district": b["district"], "branch": b["branch"],
             "crop": b["crop"], "area_ha": b["area_ha"], "irrigation_fraction": b["irrigation_fraction"],
             "due_at": b["due_at"], "synthetic": True} for b in list_borrower_records()]


@app.post("/api/borrowers", status_code=201)
def create_borrower(payload: BorrowerCreate):
    record = payload.model_dump(mode="json")
    record.update({"id": f"B-{uuid4().hex[:10].upper()}", "synthetic": True, "land_class": "unclassified",
                   "credit_history": [], "created_at": datetime.now(timezone.utc).isoformat()})
    try:
        save_borrower_record(record, create=True)
    except Exception as exc:
        raise HTTPException(409, "Could not create borrower record") from exc
    return record


@app.put("/api/borrowers/{borrower_id}")
def replace_borrower(borrower_id: str, payload: BorrowerCreate):
    current = get_borrower_record(borrower_id)
    if current is None:
        raise HTTPException(404, "Borrower not found")
    record = payload.model_dump(mode="json")
    loan = get_loan_record(borrower_id)
    if loan:
        protected = {"loan_principal_inr": loan["principal_inr"], "annual_rate": loan["annual_rate"],
                     "disbursed_at": loan["disbursed_at"], "due_at": loan["due_at"]}
        changed = [key for key, value in protected.items()
                   if (Decimal(str(record[key])) != Decimal(str(value)) if key in ("loan_principal_inr", "annual_rate")
                       else record[key] != value)]
        if changed:
            raise HTTPException(409, "Contract terms are managed through a new application; this profile edit cannot rewrite a linked loan.")
    record.update({"id": borrower_id, "synthetic": True, "land_class": current.get("land_class", "unclassified"),
                   "credit_history": current.get("credit_history", []), "created_at": current.get("created_at")})
    try:
        save_borrower_record(record)
    except KeyError as exc:
        raise HTTPException(404, "Borrower not found") from exc
    return record


@app.get("/api/applications")
def applications():
    return {"applications": list_applications()}


@app.post("/api/applications", status_code=201)
def create_application_record(payload: ApplicationCreate):
    if get_borrower_record(payload.borrower_id) is None:
        raise HTTPException(404, "Borrower not found")
    now = datetime.now(timezone.utc).isoformat()
    record = {"application_id": f"A-{uuid4().hex[:10].upper()}", "borrower_id": payload.borrower_id,
              "requested_amount_inr": str(payload.requested_amount_inr), "purpose": payload.purpose,
              "notes": payload.notes, "status": "draft", "status_history": [{"status": "draft", "at": now,
              "rationale": "Application created in demo mode."}], "created_at": now, "updated_at": now,
              "synthetic": True, "loan_id": None, "assessment_id": None}
    create_application(record)
    return record


@app.patch("/api/applications/{application_id}/status")
def transition_application(application_id: str, payload: ApplicationStatusUpdate):
    record = get_application(application_id)
    if record is None:
        raise HTTPException(404, "Application not found")
    transitions = {"draft": {"assessed"}, "assessed": {"referred_to_officer"},
                   "referred_to_officer": {"under_review"}, "under_review": {"reviewed"},
                   "reviewed": {"approved_in_demo", "rejected_in_demo"}}
    if payload.status not in transitions.get(record["status"], set()):
        raise HTTPException(409, f"Invalid application transition: {record['status']} → {payload.status}")
    now = datetime.now(timezone.utc).isoformat()
    record["status"] = payload.status
    record["updated_at"] = now
    record["status_history"].append({"status": payload.status, "at": now, "rationale": payload.rationale})
    if payload.status == "assessed":
        req = ScenarioRequest(borrower_id=record["borrower_id"], as_of=date.today(),
                              loan_principal_override_inr=record["requested_amount_inr"])
        result = evaluate_scenario(req)
        save_scenario(result["scenario_id"], req.borrower_id, result["input_hash"], req.model_dump(mode="json"), result)
        record["assessment_id"] = result["scenario_id"]
    if payload.status == "approved_in_demo":
        borrower_record = get_borrower_record(record["borrower_id"])
        if borrower_record is None:
            raise HTTPException(409, "Application borrower no longer exists")
        borrower_record["loan_principal_inr"] = record["requested_amount_inr"]
        loan_id = f"L-{record['application_id']}"
        loan = {"loan_id": loan_id, "borrower_id": record["borrower_id"],
                "principal_inr": record["requested_amount_inr"], "annual_rate": borrower_record["annual_rate"],
                "disbursed_at": borrower_record["disbursed_at"], "due_at": borrower_record["due_at"],
                "synthetic": True, "application_id": application_id, "posted_events": [],
                "events": [{"date": borrower_record["disbursed_at"], "kind": "disbursement",
                            "amount_inr": record["requested_amount_inr"], "source_status": "synthetic"}]}
        record["loan_id"] = loan_id
        update_application_with_demo_loan(record, borrower_record, loan)
    else:
        update_application(record)
    return record


@app.get("/api/loans")
def loans():
    return {"loans": list_loan_records()}


@app.post("/api/loans/{loan_id}/events", status_code=201)
def add_loan_event(loan_id: str, payload: LedgerEventCreate):
    loan_before = next((row for row in list_loan_records() if row["loan_id"] == loan_id), None)
    if loan_before is None:
        raise HTTPException(404, "Loan not found")
    if payload.date > date.today():
        raise HTTPException(422, "Demo ledger events must be dated today or earlier")
    if payload.date < date.fromisoformat(loan_before["disbursed_at"]):
        raise HTTPException(422, "Ledger event cannot precede loan disbursement")
    if payload.kind == "reversal":
        original = next((event for event in loan_before.get("posted_events", [])
                         if event["event_id"] == payload.reversal_of_event_id), None)
        if original is None:
            raise HTTPException(422, "Reversal target does not exist in this loan ledger")
        if original.get("kind") == "reversal":
            raise HTTPException(422, "A reversal cannot itself be reversed")
        if any(event.get("reversal_of_event_id") == payload.reversal_of_event_id
               for event in loan_before.get("posted_events", [])):
            raise HTTPException(409, "This ledger event has already been reversed")
        if payload.date < date.fromisoformat(original["date"]):
            raise HTTPException(422, "Reversal cannot precede the original event")
        if payload.amount_inr != Decimal(str(original["amount_inr"])):
            raise HTTPException(422, "Reversal amount must exactly match the original event")
    event_data = payload.model_dump(mode="json")
    event_id = event_data.pop("event_id", None) or f"E-{uuid4().hex[:10].upper()}"
    event = {**event_data, "event_id": event_id,
             "source_status": "synthetic_demo_entry", "simulation_only": True,
             "created_at": datetime.now(timezone.utc).isoformat()}
    loan = append_loan_event(loan_id, event)
    if loan is None:
        raise HTTPException(404, "Loan not found")
    return {"loan": loan, "notice": "This is a synthetic demo ledger event, not a bank posting."}


@app.get("/api/overview")
def overview():
    rows = []
    for borrower_record in list_borrower_records():
        result = evaluate_scenario(ScenarioRequest(borrower_id=borrower_record["id"]))
        stress = result["stress"]
        rows.append({"borrower_id": borrower_record["id"], "alias": borrower_record["alias"],
                     "crop": borrower_record["crop"], "due_at": borrower_record["due_at"],
                     "cash_gap_inr": stress["cash_gap_inr"], "repayment_probability_simulated": stress["repayment_probability_simulated"],
                     "warnings": result["debt_warnings"], "synthetic": True})
    return {"borrower_count": len(rows), "synthetic_records": True, "rows": rows,
            "data_mode": "offline_assumptions_and_synthetic_finance"}


@app.get("/api/borrowers/{borrower_id}")
def borrower(borrower_id: str):
    b = get_borrower_record(borrower_id)
    if not b: raise HTTPException(404, "Borrower not found")
    return b


@app.get("/api/borrowers/{borrower_id}/loan")
def borrower_loan(borrower_id: str, scenario_id: str | None = None):
    loan = get_loan_record(borrower_id)
    if not loan: raise HTTPException(404, "Loan not found")
    try:
        assessment = get_scenario(scenario_id) if scenario_id else evaluate_scenario(ScenarioRequest(borrower_id=borrower_id))
        if assessment is None: raise HTTPException(404, "Saved scenario not found")
        if assessment["borrower_id"] != borrower_id: raise HTTPException(422, "Scenario belongs to a different borrower")
        selected = assessment["stress_with_action"] or assessment["stress"]
        loan["events"] = [{**event, "source_status": "synthetic_and_assumed"} for event in selected["cash_by_date"]]
        loan["posted_events"] = loan.get("posted_events", [])
        principal = Decimal(str(loan["principal_inr"]))
        reversed_event_ids = {event.get("reversal_of_event_id") for event in loan["posted_events"] if event.get("kind") == "reversal"}
        repayments = sum((Decimal(str(event["amount_inr"])) for event in loan["posted_events"]
                          if event["kind"] == "repayment" and event["event_id"] not in reversed_event_ids), Decimal("0"))
        paid_principal = min(principal, repayments)
        loan["outstanding_principal_inr"] = format(max(Decimal("0"), principal - repayments).quantize(Decimal("0.01")), ".2f")
        loan["principal_ledger_reconciles"] = Decimal(loan["outstanding_principal_inr"]) + paid_principal == principal
        loan["schedule"] = selected["loan_schedule"]
        loan["scenario_id"] = assessment["scenario_id"]
        loan["computed_cash_pre_due_inr"] = selected["cash_pre_due_inr"]
        loan["computed_due_gap_inr"] = selected["cash_gap_inr"]
        loan["proposal_status"] = assessment["action_status"]
        loan["computation_status"] = "simulation_conditioned"
        return loan
    except KeyError:
        raise HTTPException(404, "Borrower not found")


@app.get("/api/climate")
def climate(region: str = Query(default="Nashik"), crop: str = Query(default="Wheat"), as_of: date = Query(default=date(2026, 10, 9))):
    return {"region": region, "crop": crop, "as_of": as_of, "data_mode": "offline_demo_fixture",
            "weather": {"status": "reanalysis_conditional_by_stage_dates_and_geography", "forecast_issued_at": None,
                        "operational_forecast": {"status": "unavailable"},
                        "observed_history": {"status": "conditional_reanalysis", "source_class": "gridded_reanalysis"},
                        "note": "Scenario assessment aligns historical Pune ERA5 only where declared stage dates and geography overlap; otherwise returns missing coverage. Hypothetical controls remain a separate input class."},
            "crop_calendar": {"status": "assumed_illustrative", "version": "illustrative-stage-calendar-v3",
                              "source": "Sage illustrative demo rule; no region-verified crop calendar admitted",
                              "method": "inclusive fixed days-after-sowing windows clipped to declared harvest date",
                              "uncertainty": "high; not an agronomic recommendation", "geography": "unverified; not district calibrated",
                              "timezone": "Asia/Kolkata", "stages": [{"name": k, "days_after_sowing": list(v)} for k, v in STAGE_WINDOWS.items()]},
            "ndvi": {"status": "unavailable", "value": None, "resolution": None},
            "soil_moisture": {"status": "unavailable", "value": None},
            "yield_baseline": {"status": "assumed_illustrative_response"},
            "market_price": {"status": "assumed_demo_input"}}


@app.get("/api/crop-calendar")
def crop_calendar(borrower_id: str = Query(default="B-DEMO-001")):
    try:
        result = evaluate_scenario(ScenarioRequest(borrower_id=borrower_id))
    except KeyError:
        raise HTTPException(404, "Select a seeded demo borrower")
    return result["stress"]["crop_calendar"] | {"stages": result["stress"]["crop_stages"]}


@app.post("/api/assessments/evaluate", response_model=ScenarioBundle)
@app.post("/api/debt-cycle/evaluate", response_model=ScenarioBundle)
@app.post("/api/scenarios/evaluate", response_model=ScenarioBundle)
def scenario(req: ScenarioRequest):
    try:
        result = evaluate_scenario(req)
        result["snapshot_freshness"] = "current"
        result["snapshot_stale_reasons"] = []
        return save_scenario(result["scenario_id"], req.borrower_id, result["input_hash"], req.model_dump(mode="json"), result)
    except KeyError: raise HTTPException(404, "Select a seeded demo borrower")
    except ValueError as exc: raise HTTPException(422, str(exc))


@app.post("/api/interventions/evaluate")
def intervention_candidates(req: InterventionEvaluationRequest):
    try:
        base_req = ScenarioRequest.model_validate(req.model_dump(exclude={"action_inputs", "action_id", "action_parameters"}) |
                                                   {"action_id": "none", "action_parameters": {}})
        baseline, options = evaluate_action_candidates(req)
        base_saved = save_scenario(baseline["scenario_id"], req.borrower_id, baseline["input_hash"],
                                   base_req.model_dump(mode="json"), baseline)
        evaluated_results: dict[str, dict] = {}
        ranked: list[dict] = []
        for option in options:
            if not option.get("eligible") or not option.get("evaluable"):
                continue
            parameters = option.get("action_parameters", {})
            schedule_action = parameters.get("schedule_action") or "none"
            candidate_req = base_req.model_copy(update={"action_id": schedule_action, "action_parameters": parameters})
            result = evaluate_scenario(candidate_req)
            result = save_scenario(result["scenario_id"], req.borrower_id, result["input_hash"],
                                   candidate_req.model_dump(mode="json"), result)
            option = score_action_option(option, baseline, result)
            option["result_ref"] = {"scenario_id": result["scenario_id"], "result": "stress_with_action"}
            evaluated_results[option["candidate_id"]] = result
            if option.get("successful"):
                ranked.append(option)
            else:
                option["status"] = "eligible_unranked"
                option["not_ranked_reason"] = "No positive net benefit under the declared objective."
        ranked.sort(key=lambda row: (-float(row["metrics"]["objective_score_inr"]), row["candidate_id"]))
        for rank, option in enumerate(ranked, start=1):
            option["rank"] = rank
            option["selected"] = rank == 1
        options_by_id = {row["candidate_id"]: row for row in options}
        options = [options_by_id[row["candidate_id"]] for row in ranked] + [row for row in options if row["candidate_id"] not in {r["candidate_id"] for r in ranked}]
        context_hash = baseline["comparison_context_hash"]
        if any(result["comparison_context_hash"] != context_hash for result in evaluated_results.values()):
            raise HTTPException(409, "Action results do not share the frozen stress inputs and climate paths")
        legacy_candidates = [evaluated_results[action_id] for action_id in ("reschedule_30d", "split_payment") if action_id in evaluated_results]
        requested_candidate = req.action_inputs.get("selected_candidate_id")
        selected_id = requested_candidate if requested_candidate in evaluated_results else req.action_id if req.action_id in evaluated_results else (ranked[0]["candidate_id"] if ranked else None)
        selected = evaluated_results.get(selected_id, base_saved)
        bundle = save_comparison_bundle({
            "borrower_id": req.borrower_id, "comparison_context_hash": context_hash,
            "baseline_ref": {"scenario_id": base_saved["scenario_id"], "result": "baseline"},
            "stress_ref": {"scenario_id": base_saved["scenario_id"], "result": "stress"},
            "candidate_refs": [{"action_id": action_id, "scenario_id": evaluated_results[action_id]["scenario_id"], "result": "stress_with_action"}
                               for action_id in ("reschedule_30d", "split_payment") if action_id in evaluated_results],
            "action_options": options,
            "action_result_refs": {key: value["scenario_id"] for key, value in evaluated_results.items()},
            "ranked_candidate_ids": [row["candidate_id"] for row in ranked],
            "objective": INTERVENTION_POLICY["objective"], "policy_version": INTERVENTION_POLICY["version"],
            "policy_class": INTERVENTION_POLICY["policy_class"], "seed": base_saved["frozen_context"]["seed"],
            "climate_path_hash": base_saved["frozen_context"]["climate_paths"]["hash"],
            "idempotency_policy": "SHA-256 of frozen scenario, catalog/policy versions, action options, and result refs; same comparison returns first saved record",
        })
        selected["comparison_bundle_id"] = bundle["bundle_id"]
        for candidate in legacy_candidates:
            candidate["comparison_bundle_id"] = bundle["bundle_id"]
        return {"selected": selected, "candidates": legacy_candidates, "candidate_results": evaluated_results,
                "action_options": options, "ranked_candidate_ids": [row["candidate_id"] for row in ranked],
                "non_selected_options": [row for row in options if row.get("candidate_id") not in {r["candidate_id"] for r in ranked}],
                **bundle}
    except KeyError:
        raise HTTPException(404, "Select a seeded demo borrower")
    except ValueError as exc:
        raise HTTPException(422, str(exc))


@app.get("/api/interventions/catalog")
def intervention_catalog():
    return action_catalog()


@app.post("/api/interventions/proposals", status_code=201)
def propose_intervention(payload: InterventionProposalCreate):
    comparison = get_comparison_bundle(payload.comparison_id)
    if comparison is None:
        raise HTTPException(404, "Saved intervention comparison not found")
    candidate = next((row for row in comparison.get("action_options", []) if row.get("candidate_id") == payload.candidate_id), None)
    if candidate is None:
        raise HTTPException(404, "Action candidate not found in this comparison")
    if not candidate.get("evaluable") or not candidate.get("eligible") or not candidate.get("result_ref"):
        raise HTTPException(422, "Unsupported or ineligible options cannot be proposed")
    return create_intervention_proposal(comparison_id=payload.comparison_id, candidate_id=payload.candidate_id,
        assessment_id=comparison["comparison_context_hash"], scenario_id=candidate["result_ref"]["scenario_id"],
        actor=payload.actor, reason=payload.reason)


@app.get("/api/interventions/proposals")
def intervention_proposals(limit: int = Query(default=100, ge=1, le=250)):
    return {"proposals": list_intervention_proposals(limit), "simulation_only": True}


@app.patch("/api/interventions/proposals/{proposal_id}/review")
def review_intervention_proposal(proposal_id: str, payload: InterventionReviewUpdate):
    proposal = get_intervention_proposal(proposal_id)
    if proposal is None:
        raise HTTPException(404, "Intervention proposal not found")
    if payload.status not in INTERVENTION_POLICY["review_transitions"].get(proposal["status"], []):
        raise HTTPException(409, f"Invalid intervention review transition: {proposal['status']} -> {payload.status}")
    applied = None
    if payload.status == "approved_in_demo":
        saved_candidate = get_scenario(proposal["scenario_id"])
        if saved_candidate is None:
            raise HTTPException(409, "Proposed assessment evidence is no longer available")
        request = ScenarioRequest.model_validate(saved_candidate["scenario_request"])
        parameters = {**request.action_parameters, "approval_proposal_id": proposal_id,
                      "approval_actor": payload.actor, "approved_at": datetime.now(timezone.utc).isoformat()}
        approved_request = request.model_copy(update={"action_parameters": parameters})
        result = evaluate_scenario(approved_request)
        result["applied_simulation"] = {"proposal_id": proposal_id, "approved_by": payload.actor,
            "approved_at": parameters["approved_at"], "scope": "new_simulated_result_only",
            "existing_loan_events_mutated": False, "external_message_sent": False}
        result = save_scenario(result["scenario_id"], result["borrower_id"], result["input_hash"],
                               approved_request.model_dump(mode="json"), result)
        applied = {"scenario_id": result["scenario_id"], "result_hash": result["result_hash"],
                   "scope": "new_simulated_result_only", "existing_loan_events_mutated": False,
                   "external_message_sent": False}
    try:
        updated = transition_intervention_proposal(proposal_id, status=payload.status, actor=payload.actor,
            reason=payload.reason, allowed_transitions=INTERVENTION_POLICY["review_transitions"],
            applied_simulation=applied)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    return updated


@app.get("/api/comparison-bundles/{bundle_id}")
def reopen_comparison_bundle(bundle_id: str):
    bundle = get_comparison_bundle(bundle_id)
    if bundle is None:
        raise HTTPException(404, "Saved comparison bundle not found")
    refs = [bundle["baseline_ref"]["scenario_id"], bundle["stress_ref"]["scenario_id"],
            *[row["scenario_id"] for row in bundle["candidate_refs"]],
            *bundle.get("action_result_refs", {}).values()]
    refs = list(dict.fromkeys(refs))
    results = {scenario_id: get_scenario(scenario_id) for scenario_id in refs}
    if any(result is None for result in results.values()):
        raise HTTPException(500, "Comparison bundle has a missing linked result")
    action_results = {candidate_id: results[scenario_id] for candidate_id, scenario_id in bundle.get("action_result_refs", {}).items()}
    return {**bundle, "selected": results[bundle["stress_ref"]["scenario_id"]],
            "candidates": [{**results[ref["scenario_id"]], "comparison_context_hash": bundle["comparison_context_hash"]}
                           for ref in bundle["candidate_refs"]], "action_results": action_results, "results": results}


@app.get("/api/scenarios/{scenario_id}", response_model=ScenarioBundle)
def reopen_scenario(scenario_id: str):
    result = get_scenario(scenario_id)
    if result is None: raise HTTPException(404, "Saved scenario not found")
    return result


@app.get("/api/scenarios")
def saved_scenarios(limit: int = Query(default=50, ge=1, le=100)):
    return {"scenarios": list_scenarios(limit)}


@app.get("/api/warnings")
def warning_evidence(limit: int = Query(default=200, ge=1, le=500)):
    """Immutable F7 evidence; mutable warning task state is stored separately."""
    return {"warnings": list_warning_evidence(limit), "synthetic_scenarios_only": True,
            "lifecycle_owner": "F9", "evidence_is_immutable": True}


@app.get("/api/watchlist")
def warning_watchlist(branch_id: str | None = None, status: str | None = None,
                      severity: str | None = None, page: int = Query(default=1, ge=1),
                      page_size: int = Query(default=25, ge=1, le=100)):
    evidence_rows = list_warning_evidence(5000)
    records = []
    for row in evidence_rows:
        scenario = get_scenario(row["assessment_id"])
        if scenario is None:
            continue
        borrower = scenario.get("frozen_context", {}).get("borrower", {})
        task = ensure_warning_task(row["derivation_key"])
        warning = row.get("warning", {})
        records.append({"derivation_key": row["derivation_key"], "assessment_id": row["assessment_id"],
            "borrower_id": scenario.get("borrower_id"), "borrower_alias": borrower.get("alias"),
            "branch_id": borrower.get("branch"), "rule": row["rule"], "rule_version": row["rule_version"],
            "severity": warning.get("severity", "unknown"), "season": warning.get("season"),
            "evidence": row.get("record", {}), "assumption_tags": row.get("record", {}).get("assumption_tags", []),
            "created_at": row["created_at"], "task": task})
    return page_watchlist(records, branch_id=branch_id, status=status, severity=severity,
                          page=page, page_size=page_size)


@app.post("/api/warnings/{derivation_key}/workflow")
def update_warning_workflow(derivation_key: str, payload: WarningWorkflowUpdate):
    if get_warning_evidence(derivation_key) is None:
        raise HTTPException(404, "Persisted warning evidence not found")
    ensure_warning_task(derivation_key)
    if payload.operation == "supersede" and not payload.superseded_by:
        raise HTTPException(422, "Supersede requires superseded_by evidence key")
    try:
        return transition_warning_task(derivation_key, operation=payload.operation,
            actor=payload.actor, reason=payload.reason, assigned_to=payload.assigned_to,
            superseded_by=payload.superseded_by)
    except (KeyError, ValueError) as exc:
        raise HTTPException(409, str(exc)) from exc


@app.post("/api/allocations")
def create_allocation(payload: AllocationRequest):
    frozen, excluded = freeze_from_saved_comparisons(payload.model_dump(mode="json"))
    solved = solve_allocation(frozen, payload.budget_inr, coverage_enabled=payload.coverage_enabled,
        coverage_floors=payload.coverage_floors, timeout_ms=payload.timeout_ms, excluded=excluded)
    input_snapshot = payload.model_dump(mode="json")
    input_snapshot["candidates"] = frozen
    allocation_id = stable_allocation_id(input_snapshot, solved)
    applied = []
    if solved["solver_status"] in {"optimal", "time_limit_feasible"}:
        for candidate in solved["selected"]:
            result = apply_allocated_candidate(candidate, allocation_id)
            applied.append({"candidate_id": candidate["candidate_id"], "borrower_id": candidate["borrower_id"],
                "scenario_id": result["scenario_id"], "result_hash": result["result_hash"],
                "program_cost_inr": candidate["cost_inr"], "program_cost_date": candidate["cost_date"],
                "cash_gap_inr": result["stress_with_action"]["cash_gap_inr"],
                "three_season_debt_cycle": result["debt_cycle"]})
    solved["applied_scenarios"] = applied
    solved["branch_id"] = payload.branch_id
    solved["scenario_scope"] = "synthetic_demo_unprotected_until_f10"
    return save_allocation_snapshot(allocation_id, payload.branch_id, input_snapshot, solved)


@app.get("/api/allocations/candidates")
def allocation_candidate_pool(branch_id: str, limit: int = Query(default=200, ge=1, le=500)):
    candidates, excluded = [], []
    for bundle in list_comparison_bundles(limit):
        baseline_id = bundle.get("baseline_ref", {}).get("scenario_id")
        baseline = get_scenario(baseline_id) if baseline_id else None
        if baseline is None:
            continue
        borrower = baseline.get("frozen_context", {}).get("borrower", {})
        if borrower.get("branch") != branch_id:
            continue
        for option in bundle.get("action_options", []):
            if "hypothetical_assistance" not in option.get("action_ids", []):
                continue
            scenario_id = option.get("result_ref", {}).get("scenario_id")
            result = get_scenario(scenario_id) if scenario_id else None
            params = (result or {}).get("scenario_request", {}).get("action_parameters", {})
            events = [event for event in params.get("cash_events", []) if event.get("kind") == "hypothetical_assistance"]
            metric = option.get("metrics", {}).get("immediate_gap_relief_inr")
            if not option.get("eligible") or not option.get("evaluable") or not result or not events or metric is None:
                excluded.append({"borrower_id": baseline["borrower_id"], "candidate_id": option.get("candidate_id"),
                                 "reason": option.get("not_ranked_reason") or "not a frozen eligible assistance result"})
                continue
            exact_cost = sum((Decimal(str(event["amount_inr"])) for event in events), Decimal("0"))
            candidate = {"candidate_id": f"{baseline['borrower_id']}:{bundle['bundle_id']}:{option['candidate_id']}",
                "borrower_id": baseline["borrower_id"], "branch_id": borrower.get("branch"),
                "scenario_id": scenario_id, "comparison_id": bundle["bundle_id"],
                "action_candidate_id": option["candidate_id"], "scenario_context_hash": result["comparison_context_hash"],
                "policy_version": bundle["policy_version"], "engine_version": result["engine_version"],
                "cost_inr": str(exact_cost), "cost_date": events[0]["date"] if len({event["date"] for event in events}) == 1 else None,
                "benefit_value": str(metric),
                "benefit_definition": "immediate_due_gap_relief_inr", "benefit_unit": "INR_due_gap_relief",
                "coverage_tags": [f"branch:{borrower.get('branch')}", f"district:{borrower.get('district')}"]}
            candidates.append(candidate)
    return {"branch_id": branch_id, "candidates": candidates, "excluded": excluded,
        "candidate_source": "immutable_saved_f8_comparisons", "security_scope_mode": "synthetic_demo_unprotected_until_f10"}


@app.get("/api/allocations")
def allocation_history(branch_id: str | None = None, limit: int = Query(default=50, ge=1, le=250)):
    return {"allocations": list_allocation_snapshots(branch_id, limit),
            "security_scope_mode": "synthetic_demo_unprotected_until_f10"}


@app.get("/api/allocations/{allocation_id}")
def allocation_detail(allocation_id: str):
    allocation = get_allocation_snapshot(allocation_id)
    if allocation is None:
        raise HTTPException(404, "Allocation snapshot not found")
    allocation["security_scope_mode"] = "synthetic_demo_unprotected_until_f10"
    return allocation


@app.get("/api/sources")
def sources(current_user: dict | None = Depends(source_administration_access)):
    return {"sources": list_source_records()}


@app.get("/api/source-snapshots")
def source_snapshots(source_id: str | None = None, current_user: dict | None = Depends(source_administration_access)):
    return {"snapshots": list_source_snapshots(source_id)}


@app.get("/api/source-refreshes")
def source_refreshes(source_id: str | None = None, limit: int = Query(default=50, ge=1, le=200),
                     current_user: dict | None = Depends(source_administration_access)):
    return {"refreshes": list_source_refresh_events(source_id, limit)}


@app.get("/api/source-snapshots/{snapshot_id}/content")
def source_snapshot_content(snapshot_id: str, current_user: dict | None = Depends(source_administration_access)):
    record = get_source_snapshot(snapshot_id)
    if record is None:
        raise HTTPException(404, "Source snapshot not found")
    return {"snapshot_id": snapshot_id, "content_sha256": record["content_sha256"],
            "raw_body_utf8": record.get("raw_body_utf8"), "payload": record.get("payload")}


@app.get("/api/data-sources")
def data_sources(current_user: dict | None = Depends(source_administration_access)):
    return list_data_sources()


@app.post("/api/data-sources/open-meteo/refresh")
def refresh_open_meteo(current_user: dict = Depends(require_roles("admin"))):
    try:
        result = refresh_pune_historical_weather()
        add_audit_event(actor_id=current_user["id"], actor_role=current_user["role"], entity_type="data_source",
                        entity_id="open-meteo", action="refresh", reason="Administrator refreshed a source snapshot",
                        result_ref=result.get("snapshot_id") if isinstance(result, dict) else None)
        return result
    except (OSError, ValueError, RuntimeError) as exc:
        raise HTTPException(502, f"Source refresh failed and no verified fallback is available: {exc}") from exc


@app.post("/api/data-sources/import", status_code=201)
def import_feature_snapshot(payload: FeatureSnapshotImport, current_user: dict = Depends(require_roles("admin"))):
    try:
        result = freeze_feature_import(payload)
        add_audit_event(actor_id=current_user["id"], actor_role=current_user["role"], entity_type="data_source",
                        entity_id=payload.source_id, action="import", reason="Administrator imported a source snapshot",
                        result_ref=result.get("snapshot_id") if isinstance(result, dict) else None)
        return result
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.get("/api/telemetry/soil-moisture")
def soil_moisture_telemetry(district: str = "Nashik", as_of: str = "2026-10-09"):
    """Fetch high-resolution volumetric soil water and root-zone metrics."""
    return get_soil_moisture_telemetry(district, as_of)


@app.get("/api/telemetry/ndvi")
def satellite_ndvi_telemetry(district: str = "Nashik", crop: str = "Wheat", stage: str = "flowering", as_of: str = "2026-10-09"):
    """Fetch Sentinel-2 L2A optical NDVI vegetation index and phenology curve."""
    return get_satellite_ndvi_telemetry(district, crop, stage, as_of)
