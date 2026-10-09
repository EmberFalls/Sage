"""Canonical scenario engine: dated cash, scheduled payments and carried liabilities."""
from __future__ import annotations

from copy import deepcopy
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
import hashlib
import json
from pathlib import Path

from app.config import DEMO_SEED, ENGINE_VERSION
from app.schemas import ScenarioRequest
from app.services.fixtures import BORROWERS

D = Decimal
SOURCE_VERSION = "demo-fixture-2026-10-09.2"
STAGE_WINDOWS = {"planting": (0, 24), "vegetative": (25, 54), "flowering": (55, 75), "grain_fill": (76, 112), "harvest": (113, 145)}
SENSITIVITY = {
    "Wheat": {"planting": "0.4", "vegetative": "0.6", "flowering": "1", "grain_fill": "0.85", "harvest": "0.25"},
    "Maize": {"planting": "0.45", "vegetative": "0.65", "flowering": "1", "grain_fill": "0.8", "harvest": "0.3"},
}
WARNING_CONFIG = json.loads((Path(__file__).parents[1] / "config" / "warnings.json").read_text())


def money(value) -> Decimal:
    return D(str(value)).quantize(D("0.01"), rounding=ROUND_HALF_UP)


def _jsonable(value):
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return value


def _resolve_borrower(borrower_id: str) -> dict:
    # API and calculator both resolve the seeded SQLite profile. Pure engine tests
    # can use the same offline fixture before an application lifespan is started.
    from app.db import get_borrower_record
    stored = get_borrower_record(borrower_id)
    b = deepcopy(stored or BORROWERS.get(borrower_id))
    if b is None:
        raise KeyError(borrower_id)
    for key in ("sowing_date", "harvest_date", "disbursed_at", "due_at"):
        if isinstance(b[key], str):
            b[key] = date.fromisoformat(b[key])
    for key in ("loan_principal_inr", "annual_rate", "initial_cash_inr", "input_cost_inr", "living_cost_inr", "yield_t_per_ha", "price_inr_per_quintal", "sale_fraction"):
        b[key] = D(str(b[key]))
    return b


def _schedule(b: dict, action: str, shift: int = 0) -> tuple[list[dict], Decimal, Decimal]:
    principal, rate = b["loan_principal_inr"], b["annual_rate"]
    days = D((b["due_at"] - b["disbursed_at"]).days)
    original_due = money(principal * (1 + rate * days / 365))
    extra = D("0.00")
    due_date = b["due_at"] + timedelta(days=shift)
    if action == "reschedule_30d":
        extra = money(principal * rate * 30 / 365)
        schedule = [{"date": due_date + timedelta(days=30), "amount_inr": original_due + extra}]
    elif action == "split_payment":
        fee = money(original_due * D("0.015"))
        extra_interest = money(principal / 2 * rate * 45 / 365)
        extra = fee + extra_interest
        first = money((original_due + fee) / 2)
        schedule = [{"date": due_date, "amount_inr": first},
                    {"date": due_date + timedelta(days=45), "amount_inr": original_due + fee - first + extra_interest}]
    else:
        schedule = [{"date": due_date, "amount_inr": original_due}]
    return schedule, money(extra), original_due


def build_dated_ledger(b: dict, revenue: Decimal, sale_date: date, schedule: list[dict], bridge_limit: Decimal,
                       *, opening_cash=None, carried_formal=D("0"), carried_informal=D("0"), shift=0) -> dict:
    """Cash is carried forward; principal enters once and unpaid due enters debt once.

    Every season receives a new synthetic crop loan. Carried bank arrears accrue
    one year of assumed bank interest. Informal debt is settled from surplus cash
    after sale/final bank payment, with explicit simple interest and dates.
    """
    opening = b["initial_cash_inr"] if opening_cash is None else opening_cash
    cash = money(opening)
    events = [
        {"date": b["disbursed_at"] + timedelta(days=shift), "kind": "loan_disbursement", "amount_inr": b["loan_principal_inr"], "priority": 0},
        {"date": b["sowing_date"] + timedelta(days=8 + shift), "kind": "crop_inputs", "amount_inr": -b["input_cost_inr"], "priority": 1},
        {"date": b["due_at"] + timedelta(days=shift - 3), "kind": "household_expense", "amount_inr": -b["living_cost_inr"], "priority": 1},
        {"date": sale_date, "kind": "crop_sale", "amount_inr": revenue, "priority": 0},
    ]
    scheduled = deepcopy(schedule)
    scheduled[0]["amount_inr"] = money(scheduled[0]["amount_inr"] + carried_formal * (1 + b["annual_rate"]))
    for item in scheduled:
        events.append({"date": item["date"], "kind": "bank_due", "due_inr": item["amount_inr"], "priority": 2})
    ledger, payments, draws = [], [], []
    remaining_bridge = money(bridge_limit)
    formal_balance = D("0.00")
    def post(when, kind, amount, **extra):
        nonlocal cash
        cash = money(cash + amount)
        ledger.append({"date": when.isoformat(), "kind": kind, "amount_inr": money(amount), "cash_after_inr": cash, **extra})
    for event in sorted(events, key=lambda x: (x["date"], x["priority"])):
        if event["kind"] != "bank_due":
            post(event["date"], event["kind"], event["amount_inr"])
            continue
        amount, pre = money(event["due_inr"]), cash
        gap = max(D("0.00"), money(amount - max(D("0.00"), pre)))
        draw = min(remaining_bridge, max(D("0.00"), money(amount - cash)))
        if draw:
            post(event["date"], "informal_bridge_draw", draw)
            draws.append((event["date"], draw))
            remaining_bridge -= draw
        paid = min(amount, max(D("0.00"), cash))
        post(event["date"], "bank_payment", -paid, scheduled_due_inr=amount)
        unpaid = money(amount - paid)
        formal_balance += unpaid
        payments.append({"date": event["date"].isoformat(), "cash_before_due_inr": pre,
                         "bank_due_inr": amount, "cash_gap_inr": gap, "informal_draw_inr": draw,
                         "formal_paid_inr": paid, "unmet_due_inr": unpaid, "cash_after_due_inr": cash})
    season_end = max(sale_date, scheduled[-1]["date"]) + timedelta(days=7)
    informal_rate = D(WARNING_CONFIG["informal_rate"])
    informal_interest = money(carried_informal * informal_rate + sum((amount * informal_rate * D((season_end - when).days) / 365 for when, amount in draws), D("0")))
    informal_due = money(carried_informal + sum((amount for _, amount in draws), D("0")) + informal_interest)
    informal_paid = min(max(D("0.00"), cash), informal_due)
    if informal_paid:
        post(season_end, "informal_payment", -informal_paid)
    informal_balance = money(informal_due - informal_paid)
    return {"opening_cash_inr": money(opening), "cash_by_date": ledger, "payments": payments,
            "cash_pre_due_inr": payments[0]["cash_before_due_inr"], "due_inr": payments[0]["bank_due_inr"],
            "cash_gap_inr": payments[0]["cash_gap_inr"], "cash_gap_total_inr": money(sum(p["cash_gap_inr"] for p in payments)),
            "formal_paid_inr": money(sum(p["formal_paid_inr"] for p in payments)),
            "formal_balance_end_inr": money(formal_balance), "bridge_draw_inr": money(sum((v for _, v in draws), D("0"))),
            "informal_balance_end_inr": informal_balance, "informal_interest_inr": informal_interest,
            "informal_paid_inr": money(informal_paid), "net_free_cash_inr": cash,
            "bank_total_due_inr": money(sum(p["bank_due_inr"] for p in payments)), "season_end": season_end.isoformat()}


def _assessment(b: dict, req: ScenarioRequest, *, shock: bool, action: str = "none") -> dict:
    o = req.overrides
    stage = o.heatwave_growth_stage if shock else "flowering"
    heat, rain, price_delta = (o.heatwave_days, o.rainfall_change_pct, o.market_price_change_pct) if shock else (0, 0, 0)
    irrigation = o.irrigation_fraction if shock and o.irrigation_fraction is not None else b["irrigation_fraction"]
    sensitivity = D(SENSITIVITY[b["crop"]][stage])
    heat_loss = min(D("0.45"), D(heat) * D("0.012")) * sensitivity
    rain_factor = max(D("0.72"), 1 + D(str(rain)) / 100 * D("0.22") * (1 - D(str(irrigation))))
    yield_value = (b["yield_t_per_ha"] * (1 - heat_loss) * rain_factor).quantize(D("0.0001"))
    production = yield_value * D(str(b["area_ha"]))
    price = money(b["price_inr_per_quintal"] * (1 + D(str(price_delta)) / 100))
    revenue = money(production * 10 * price * b["sale_fraction"])
    sale_date = b["harvest_date"] + timedelta(days=heat * 2)
    schedule, cost, original_due = _schedule(b, action)
    ledger = build_dated_ledger(b, revenue, sale_date, schedule, money(o.assumed_informal_bridge_inr if shock else 0))
    # 21 equally weighted, declared hypothetical yield/price paths. Frequencies
    # describe only this finite scenario set, never historical borrower defaults.
    shortfalls = repaid = 0
    for i in range(-10, 11):
        path_revenue = money(revenue * (1 + D(i) / 50) * (1 + D(i) / 100))
        path = build_dated_ledger(b, path_revenue, sale_date, schedule, money(o.assumed_informal_bridge_inr if shock else 0))
        shortfalls += int(any(p["cash_gap_inr"] > 0 for p in path["payments"]))
        repaid += int(path["formal_balance_end_inr"] == 0)
    stages = [{"name": name, "start_date": (b["sowing_date"] + timedelta(days=window[0])).isoformat(),
               "end_date": min(b["sowing_date"] + timedelta(days=window[1]), b["harvest_date"]).isoformat(),
               "calendar_status": "assumed"} for name, window in STAGE_WINDOWS.items()]
    selected_stage = next(s for s in stages if s["name"] == stage)
    stress_features = {name: round(min(1.0, float(D(heat) / 20 * D(SENSITIVITY[b["crop"]][name]) if name == stage else D("0")) + max(0, -rain) / 100 * (1 - float(irrigation)) * .25), 4) for name in STAGE_WINDOWS}
    inputs = {
        "satellite": {"name": "NDVI / FPAR", "value": None, "unit": "index", "status": "unavailable", "source": None},
        "weather_forecast": {"rainfall_change_pct": rain, "heatwave_days": heat, "heatwave_growth_stage": stage, "status": "hypothetical_scenario", "issued_at": None},
        "soil": {"name": "Soil moisture", "value": None, "unit": "volumetric fraction", "status": "unavailable"},
        "crop": {"name": b["crop"], "area_ha": b["area_ha"], "season_start": b["sowing_date"], "season_end": b["harvest_date"], "status": "synthetic_borrower_assumption"},
        "irrigation": {"fraction": irrigation, "unit": "fraction of area", "status": "synthetic_borrower_input"},
        "yield_history": {"baseline_t_per_ha": b["yield_t_per_ha"], "projected_t_per_ha": yield_value, "unit": "tonnes/hectare", "status": "assumed_illustrative_response", "historical_observations": None},
        "market_price": {"inr_per_quintal": price, "unit": "INR/quintal", "status": "assumed_demo_input", "observed_at": None},
        "credit_history": {"events": b["credit_history"], "status": "synthetic_demo_records", "observed_bank_data": False},
    }
    return {**ledger, "yield_t_per_ha": yield_value, "production_tonnes": production, "price_inr_per_quintal": price,
            "gross_revenue_inr": revenue, "sale_date": sale_date.isoformat(), "due_date": schedule[0]["date"].isoformat(),
            "contractual_due_inr": original_due, "loan_schedule": schedule, "action_cost_inr": cost, "action_id": action,
            "stage_stress": stress_features, "crop_stages": stages,
            "heat_event": {"stage": stage, "start_date": selected_stage["start_date"] if heat else None,
                           "end_date": (date.fromisoformat(selected_stage["start_date"]) + timedelta(days=heat - 1)).isoformat() if heat else None, "duration_days": heat},
            "fin03_inputs": inputs, "source_status": {k: v["status"] for k, v in inputs.items()},
            "repayment_probability_simulated": (D(repaid) / 21).quantize(D("0.0001")),
            "p_shortfall": (D(shortfalls) / 21).quantize(D("0.0001")),
            "probability_basis": {"paths": 21, "repaid_paths": repaid, "shortfall_paths": shortfalls,
                                  "type": "equally_weighted_hypothetical_paths", "yield_range": "±20%", "price_range": "±10%", "calibrated": False},
            "formal_repayment_status": "simulated_due_satisfied" if ledger["formal_balance_end_inr"] == 0 else "simulated_unpaid_due"}


def _three_seasons(b: dict, a: dict, req: ScenarioRequest, *, bridge_enabled: bool) -> list[dict]:
    cash, formal, informal = b["initial_cash_inr"], D("0"), D("0")
    rows = []
    for season in range(1, 4):
        shift = 365 * (season - 1)
        schedule, action_cost, _ = _schedule(b, a["action_id"], shift)
        opening_liabilities = money(formal + informal + b["loan_principal_inr"])
        flow = build_dated_ledger(b, a["gross_revenue_inr"], date.fromisoformat(a["sale_date"]) + timedelta(days=shift),
                                  schedule, money(req.overrides.assumed_informal_bridge_inr if bridge_enabled else 0),
                                  opening_cash=cash, carried_formal=formal, carried_informal=informal, shift=shift)
        cash, formal, informal = flow["net_free_cash_inr"], flow["formal_balance_end_inr"], flow["informal_balance_end_inr"]
        rows.append({"season": season, "climate_shock": bridge_enabled, "yield_t_per_ha": a["yield_t_per_ha"],
                     "gross_revenue_inr": a["gross_revenue_inr"], "opening_total_debt_inr": opening_liabilities,
                     "cash_before_due_inr": flow["cash_pre_due_inr"], "bank_due_inr": flow["bank_total_due_inr"],
                     "formal_paid_inr": flow["formal_paid_inr"], "informal_draw_inr": flow["bridge_draw_inr"],
                     "formal_balance_end_inr": formal, "informal_balance_end_inr": informal,
                     "total_debt_end_inr": money(formal + informal), "net_free_cash_inr": cash,
                     "cash_gap_inr": flow["cash_gap_total_inr"], "unmet_due_inr": formal,
                     "interest_paid_inr": flow["informal_interest_inr"], "action_cost_inr": action_cost,
                     "cash_by_date": flow["cash_by_date"], "payments": flow["payments"], "simulation_only": True})
    return rows


def derive_debt_warnings(cycle: list[dict], stress: dict, action: dict | None) -> list[dict]:
    warnings = []
    threshold = D(WARNING_CONFIG["materiality_inr"])
    def add(rule, severity, season, evidence, bridge=False):
        warnings.append({"id": rule, "severity": severity, "season": season, "evidence": evidence,
                         "trace": "Rule evaluated against the canonical modeled payment/debt ledger.",
                         "proposed_officer_action": "Review dated cash needs and affordable repayment options with the borrower.",
                         "simulation_only": True, "triggered_by_assumed_informal_borrowing": bridge,
                         "threshold_version": WARNING_CONFIG["version"]})
    for payment in stress["payments"]:
        if payment["informal_draw_inr"] > 0 and payment["formal_paid_inr"] > 0 and payment["cash_gap_inr"] > 0:
            add("BRIDGE_USED_FOR_FORMAL_DUE", "high", 1, payment, True)
            break
    short = [row for row in cycle if row["cash_gap_inr"] >= threshold]
    if len(short) >= WARNING_CONFIG["repeated_seasons"]:
        add("REPEATED_SHORTFALL", "high", short[0]["season"], {"seasons": [r["season"] for r in short], "gaps_inr": [r["cash_gap_inr"] for r in short]})
    growing = [(prev, row) for prev, row in zip(cycle, cycle[1:]) if row["informal_balance_end_inr"] - prev["informal_balance_end_inr"] >= threshold]
    if growing:
        prev, row = growing[0]
        add("INFORMAL_DEBT_GROWING", "high", row["season"], {"opening_balance_inr": prev["informal_balance_end_inr"], "closing_balance_inr": row["informal_balance_end_inr"], "assumed_rate": WARNING_CONFIG["informal_rate"]}, True)
    for row in cycle:
        if row["unmet_due_inr"] == 0 and row["total_debt_end_inr"] > row["opening_total_debt_inr"] + threshold:
            add("FORMAL_PAID_TOTAL_DEBT_RISES", "high", row["season"], {"opening_debt_inr": row["opening_total_debt_inr"], "closing_debt_inr": row["total_debt_end_inr"]}, True)
            break
    if action and action["cash_gap_inr"] < stress["cash_gap_inr"]:
        extra = sum(r["action_cost_inr"] for r in action["debt_cycle"]) - sum(r["action_cost_inr"] for r in cycle)
        if extra >= threshold:
            add("ACTION_SHIFTS_BURDEN", "moderate", 1, {"stress_first_gap_inr": stress["cash_gap_inr"], "action_first_gap_inr": action["cash_gap_inr"], "extra_three_season_cost_inr": money(extra)})
    return warnings


def derive_financial_bridge(b: dict, baseline: dict, stress: dict) -> dict:
    due = date.fromisoformat(stress["due_date"])
    base_sale = baseline["gross_revenue_inr"] if date.fromisoformat(baseline["sale_date"]) <= due else D("0")
    stressed_sale = stress["gross_revenue_inr"] if date.fromisoformat(stress["sale_date"]) <= due else D("0")
    effects = []
    if base_sale and stressed_sale:
        quantity = money((stress["production_tonnes"] - baseline["production_tonnes"]) * 10 * baseline["price_inr_per_quintal"] * b["sale_fraction"])
        effects = [("quantity", "Yield / quantity effect", quantity),
                   ("price", "Crop price effect", money(stressed_sale - base_sale - quantity))]
    else:
        effects = [("timing", "Sale timing effect by due date", money(stressed_sale - base_sale))]
    balance = baseline["cash_pre_due_inr"]
    steps = [{"id": "baseline_pre_due", "label": "Baseline cash before due", "amount_inr": balance,
              "running_balance_inr": balance, "data_status": "synthetic_and_assumed", "source_ids": [SOURCE_VERSION],
              "formula": "sum of dated cash flows before the first bank payment", "to_date": baseline["due_date"]}]
    for key, label, amount in effects:
        balance = money(balance + amount)
        steps.append({"id": key, "label": label, "amount_inr": amount, "running_balance_inr": balance,
                      "data_status": "assumed", "source_ids": [SOURCE_VERSION], "to_date": stress["due_date"],
                      "formula": "quantity at reference price, then price on shocked quantity; timing excludes proceeds after due"})
    return {"steps": steps, "cash_pre_due_inr": stress["cash_pre_due_inr"], "due_inr": stress["due_inr"],
            "post_due_cash_inr": money(stress["cash_pre_due_inr"] - stress["due_inr"]), "shortfall_inr": stress["cash_gap_inr"],
            "attribution": "Fixed sequential accounting attribution; rounded pennies are assigned to the price effect. Sale proceeds after due are excluded."}


def evaluate_scenario(req: ScenarioRequest) -> dict:
    b = _resolve_borrower(req.borrower_id)
    baseline = _assessment(b, req, shock=False)
    stress = _assessment(b, req, shock=True)
    eligible = req.as_of < b["due_at"]
    action = _assessment(b, req, shock=True, action=req.action_id) if req.action_id != "none" and eligible else None
    baseline["debt_cycle"] = _three_seasons(b, baseline, req, bridge_enabled=False)
    stress["debt_cycle"] = _three_seasons(b, stress, req, bridge_enabled=True)
    if action:
        action["debt_cycle"] = _three_seasons(b, action, req, bridge_enabled=True)
    warnings = derive_debt_warnings(stress["debt_cycle"], stress, action)
    source_versions = {"demo_fixture": SOURCE_VERSION, "engine": ENGINE_VERSION, "crop_rules": "illustrative-v2", "warnings": WARNING_CONFIG["version"]}
    frozen = {"borrower": _jsonable(b), "as_of": req.as_of.isoformat(), "seed": DEMO_SEED, "sources": source_versions}
    context = {**frozen, "overrides": req.overrides.model_dump()}
    canonical = lambda v: json.dumps(_jsonable(v), sort_keys=True, separators=(",", ":"), allow_nan=False)
    context_hash = hashlib.sha256(canonical(context).encode()).hexdigest()
    input_hash = hashlib.sha256(canonical({**context, "action_id": req.action_id}).encode()).hexdigest()
    for result in (baseline, stress, action):
        if result:
            result["comparison_context_hash"] = context_hash
            last = result["debt_cycle"][-1]
            result["three_season_action_cost_inr"] = money(sum(r["action_cost_inr"] for r in result["debt_cycle"]))
            result["modeled_sustainability_status"] = "projected_financial_strain" if last["total_debt_end_inr"] > 0 or last["net_free_cash_inr"] < 0 else "timing_gap_only" if any(r["cash_gap_inr"] > 0 for r in result["debt_cycle"]) else "self_funded_payments"
    candidates = [{"action_id": a, "eligible": eligible, "reason": "Illustrative officer proposal; requires bank approval." if eligible else "The contractual due date has passed as of this assessment."} for a in ("reschedule_30d", "split_payment")]
    return _jsonable({"borrower_id": req.borrower_id, "scenario_id": input_hash[:20], "input_hash": input_hash,
        "comparison_context_hash": context_hash, "engine_version": ENGINE_VERSION, "assessment_as_of": req.as_of,
        "source_versions": source_versions, "source_snapshot_ids": [SOURCE_VERSION], "frozen_context": frozen,
        "scenario_request": req.model_dump(mode="json"),
        "claim_scope": "synthetic_lending_scenario_conditional", "baseline": baseline, "stress": stress,
        "stress_with_action": action, "action_status": "not_selected" if req.action_id == "none" else "simulated_proposal" if eligible else "ineligible",
        "action_candidates": candidates, "debt_cycle": stress["debt_cycle"], "debt_warnings": warnings,
        "comparison_deltas": {"stress_minus_baseline": {"cash_gap_inr": money(stress["cash_gap_inr"] - baseline["cash_gap_inr"]), "gross_revenue_inr": money(stress["gross_revenue_inr"] - baseline["gross_revenue_inr"])},
            "action_minus_stress": None if action is None else {"cash_gap_inr": money(action["cash_gap_inr"] - stress["cash_gap_inr"]), "action_cost_inr": action["action_cost_inr"]}},
        "repayment_bridge": derive_financial_bridge(b, baseline, stress),
        "input_data_status": {"observed": [], "forecast": [], "assumed": ["weather", "calendar", "yield", "price"], "simulated": ["borrower", "loan", "credit history"], "unavailable": ["NDVI", "soil moisture"]},
        "risk_semantics": "Repayment feasibility is the fraction of 21 equally weighted hypothetical yield/price paths that settle all scheduled bank dues. This finite simulation is not calibrated to real borrowers or observed defaults.",
        "drivers": [f"Crop sale {stress['sale_date']} vs first bank due {stress['due_date']}", f"Assumed {b['crop']} heat sensitivity in {req.overrides.heatwave_growth_stage}; illustrative response", "Dated expenses, permitted bridge draws and both installments are reconciled in the cash ledger"],
        "warnings": ["All lending records are synthetic; climate/yield/price inputs are assumed.", "Crop calendar is an illustrative timing fixture, not a verified regional agronomic calendar.", "Actions require bank review; informal borrowing is a user-selected simulation."]})
