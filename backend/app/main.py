from contextlib import asynccontextmanager
from datetime import date
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app.config import PRODUCT_NAME
from app.db import (get_borrower_record, get_loan_record, get_scenario, list_borrower_records,
                   list_scenarios, list_source_records, save_scenario, seed_demo_records)
from app.schemas import ScenarioBundle, ScenarioRequest
from app.services.assessment import BORROWERS, SOURCE_VERSION, STAGE_WINDOWS, evaluate_scenario

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
            "crop_calendar": {"status": "assumed", "stages": [{"name": k, "days_after_sowing": list(v)} for k, v in STAGE_WINDOWS.items()]},
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
