from contextlib import asynccontextmanager
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app.config import PRODUCT_NAME
from app.db import (append_loan_event, create_application, get_application, get_borrower_record,
                   get_loan_record, get_scenario, get_source_snapshot, list_applications, list_borrower_records, list_loan_records,
                   list_scenarios, list_source_records,
                   list_source_refresh_events, list_source_snapshots, save_borrower_record,
                   save_scenario, seed_demo_records, update_application,
                   update_application_with_demo_loan)
from app.schemas import (ApplicationCreate, ApplicationStatusUpdate, BorrowerCreate, LedgerEventCreate,
                         FeatureSnapshotImport, ScenarioBundle, ScenarioRequest)
from app.services.assessment import BORROWERS, SOURCE_VERSION, STAGE_WINDOWS, evaluate_scenario
from app.services.sources import list_data_sources, refresh_pune_historical_weather
from app.services.feature_ingest import freeze_feature_import

@asynccontextmanager
async def lifespan(app):
    seed_demo_records(BORROWERS, SOURCE_FIXTURES)
    yield


app = FastAPI(title=PRODUCT_NAME, version="0.2.0", description="Offline synthetic agricultural credit scenario demo", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=False, allow_methods=["*"], allow_headers=["*"])

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
        repayments = sum((Decimal(str(event["amount_inr"])) for event in loan["posted_events"] if event["kind"] == "repayment"), Decimal("0"))
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
            "weather": {"status": "assumed_scenario_only", "forecast_issued_at": None, "observed_history": None,
                        "note": "No issued forecast or observed weather fixture is connected; use hypothetical scenario controls."},
            "crop_calendar": {"status": "assumed_illustrative", "version": "illustrative-v2",
                              "stages": [{"name": k, "days_after_sowing": list(v)} for k, v in STAGE_WINDOWS.items()]},
            "ndvi": {"status": "unavailable", "value": None, "resolution": None},
            "soil_moisture": {"status": "unavailable", "value": None},
            "yield_baseline": {"status": "assumed_illustrative_response"},
            "market_price": {"status": "assumed_demo_input"}}


@app.post("/api/assessments/evaluate", response_model=ScenarioBundle)
@app.post("/api/debt-cycle/evaluate", response_model=ScenarioBundle)
@app.post("/api/scenarios/evaluate", response_model=ScenarioBundle)
def scenario(req: ScenarioRequest):
    try:
        result = evaluate_scenario(req)
        save_scenario(result["scenario_id"], req.borrower_id, result["input_hash"], req.model_dump(mode="json"), result)
        return result
    except KeyError: raise HTTPException(404, "Select a seeded demo borrower")


@app.post("/api/interventions/evaluate")
def intervention_candidates(req: ScenarioRequest):
    selected = scenario(req)
    candidates = [scenario(req.model_copy(update={"action_id": action_id})) for action_id in ("reschedule_30d", "split_payment")]
    return {"selected": selected, "candidates": candidates}


@app.get("/api/scenarios/{scenario_id}", response_model=ScenarioBundle)
def reopen_scenario(scenario_id: str):
    result = get_scenario(scenario_id)
    if result is None: raise HTTPException(404, "Saved scenario not found")
    return result


@app.get("/api/scenarios")
def saved_scenarios(limit: int = Query(default=50, ge=1, le=100)):
    return {"scenarios": list_scenarios(limit)}


@app.get("/api/sources")
def sources():
    return {"sources": list_source_records()}


@app.get("/api/source-snapshots")
def source_snapshots(source_id: str | None = None):
    return {"snapshots": list_source_snapshots(source_id)}


@app.get("/api/source-refreshes")
def source_refreshes(source_id: str | None = None, limit: int = Query(default=50, ge=1, le=200)):
    return {"refreshes": list_source_refresh_events(source_id, limit)}


@app.get("/api/source-snapshots/{snapshot_id}/content")
def source_snapshot_content(snapshot_id: str):
    record = get_source_snapshot(snapshot_id)
    if record is None:
        raise HTTPException(404, "Source snapshot not found")
    return {"snapshot_id": snapshot_id, "content_sha256": record["content_sha256"],
            "raw_body_utf8": record.get("raw_body_utf8"), "payload": record.get("payload")}


@app.get("/api/data-sources")
def data_sources():
    return list_data_sources()


@app.post("/api/data-sources/open-meteo/refresh")
def refresh_open_meteo():
    try:
        return refresh_pune_historical_weather()
    except (OSError, ValueError, RuntimeError) as exc:
        raise HTTPException(502, f"Source refresh failed and no verified fallback is available: {exc}") from exc


@app.post("/api/data-sources/import", status_code=201)
def import_feature_snapshot(payload: FeatureSnapshotImport):
    try:
        return freeze_feature_import(payload)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
