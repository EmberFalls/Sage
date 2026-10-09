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
CALENDAR_VERSION = "illustrative-stage-calendar-v4"
CALENDAR_PROVENANCE = {
    "source": "Sage illustrative demo rule; no region-verified crop calendar admitted",
    "method": "inclusive season-relative windows preserving fixed stage proportions; short seasons with fewer than five days expose later stages as unavailable",
    "uncertainty": "high; dates are demo assumptions and are not an agronomic recommendation",
    "geography": "unverified; not district calibrated",
    "version": CALENDAR_VERSION,
    "timezone": "Asia/Kolkata",
    "timezone_rule": "inclusive ISO calendar dates; weather day labels retain the provider timezone; no UTC date conversion",
}
STAGE_WINDOWS = {"planting": (0, 24), "vegetative": (25, 54), "flowering": (55, 75), "grain_fill": (76, 112), "harvest": (113, 145)}
STAGE_NAMES = tuple(STAGE_WINDOWS)
STAGE_WEIGHTS = tuple(end - start + 1 for start, end in STAGE_WINDOWS.values())
WEATHER_AVAILABILITY_LAG_DAYS = 5
WEATHER_HEAT_THRESHOLD_C = 35.0
ILLUSTRATIVE_RAIN_REFERENCE_MM_PER_DAY = 4.0
SENSITIVITY = {
    "Wheat": {"planting": "0.4", "vegetative": "0.6", "flowering": "1", "grain_fill": "0.85", "harvest": "0.25"},
    "Maize": {"planting": "0.45", "vegetative": "0.65", "flowering": "1", "grain_fill": "0.8", "harvest": "0.3"},
}
WARNING_CONFIG = json.loads((Path(__file__).parents[1] / "config" / "warnings.json").read_text())
WEATHER_PATH = Path(__file__).parents[3] / "data" / "raw" / "open_meteo" / "pune_kharif_2015_era5.json"


def _calendar(b: dict) -> list[dict]:
    """Partition an inclusive season into ordered, non-overlapping illustrative stages."""
    sowing, harvest = b["sowing_date"], b["harvest_date"]
    if harvest < sowing:
        raise ValueError("Harvest date must be on or after sowing date")
    days = (harvest - sowing).days + 1
    stage_days = [0] * len(STAGE_NAMES)
    if days >= len(STAGE_NAMES):
        remaining = days - len(STAGE_NAMES)
        quotas = [remaining * weight / sum(STAGE_WEIGHTS) for weight in STAGE_WEIGHTS]
        stage_days = [1 + int(quota) for quota in quotas]
        for index in sorted(range(len(quotas)), key=lambda i: (quotas[i] - int(quotas[i]), -i), reverse=True)[:days - sum(stage_days)]:
            stage_days[index] += 1
    else:
        # Too few calendar days to represent every stage. Keep the first available
        # windows explicit and mark later stages unavailable rather than collapsing
        # them onto harvest day or inventing overlap.
        stage_days[:days] = [1] * days
    rows, cursor = [], sowing
    for index, name in enumerate(STAGE_NAMES):
        count = stage_days[index]
        if count:
            start_date, end_date = cursor, cursor + timedelta(days=count - 1)
            cursor = end_date + timedelta(days=1)
            status = "assumed_illustrative"
        else:
            start_date = end_date = None
            status = "unavailable_short_season"
        rows.append({"name": name, "start_date": start_date.isoformat() if start_date else None,
                     "end_date": end_date.isoformat() if end_date else None, "calendar_status": status,
                     "overlap": False, "gap_before_days": 0, "source": CALENDAR_PROVENANCE["source"],
                     "method": CALENDAR_PROVENANCE["method"], "uncertainty": CALENDAR_PROVENANCE["uncertainty"],
                     "geography": CALENDAR_PROVENANCE["geography"], "version": CALENDAR_VERSION,
                     "timezone": CALENDAR_PROVENANCE["timezone"]})
    return rows


def _daily_reanalysis(b: dict, stages: list[dict], as_of: date) -> dict:
    """Return only dated ERA5 rows overlapping a matching Pune season and available as of assessment."""
    if b["district"].strip().casefold() != "pune":
        return {"source_class": "reanalysis", "status": "missing_geography_mismatch", "timezone": "Asia/Kolkata", "stages": {}}
    try:
        raw_bytes = WEATHER_PATH.read_bytes()
        if hashlib.sha256(raw_bytes).hexdigest().upper() != "5B1CBCFC830C3FBDD67C53A76AB7E220A88C23D56177DF10B7AED1C40E495F9E":
            return {"source_class": "reanalysis", "status": "invalid_fixture_checksum", "timezone": "Asia/Kolkata", "stages": {}}
        payload = json.loads(raw_bytes)
    except (OSError, json.JSONDecodeError):
        return {"source_class": "reanalysis", "status": "missing_fixture", "timezone": "Asia/Kolkata", "stages": {}}
    if payload.get("timezone") != "Asia/Kolkata":
        return {"source_class": "reanalysis", "status": "invalid_fixture_timezone", "timezone": payload.get("timezone"), "stages": {}}
    daily = payload["daily"]
    variable_names = ("time", "precipitation_sum", "temperature_2m_max", "temperature_2m_min")
    if any(name not in daily for name in variable_names) or len({len(daily[name]) for name in variable_names}) != 1:
        return {"source_class": "reanalysis", "status": "invalid_fixture_schema", "timezone": "Asia/Kolkata", "stages": {}}
    if any(any(value is None for value in daily[name]) for name in variable_names[1:]):
        return {"source_class": "reanalysis", "status": "invalid_fixture_missing_values", "timezone": "Asia/Kolkata", "stages": {}}
    rows = {date.fromisoformat(day): {"precipitation_mm": rain, "tmax_c": high, "tmin_c": low}
            for day, rain, high, low in zip(daily["time"], daily["precipitation_sum"], daily["temperature_2m_max"], daily["temperature_2m_min"])}
    if len(rows) != len(daily["time"]):
        return {"source_class": "reanalysis", "status": "invalid_fixture_duplicate_dates", "timezone": "Asia/Kolkata", "stages": {}}
    # ERA5 is published with a five-day delay. For historical as-of replay,
    # enforce the same availability boundary instead of using hindsight.
    available_through = as_of - timedelta(days=WEATHER_AVAILABILITY_LAG_DAYS)
    output = {}
    any_rows = False
    for stage in stages:
        if not stage["start_date"]:
            output[stage["name"]] = {"status": "unavailable_short_season", "days_observed": 0}
            continue
        start = date.fromisoformat(stage["start_date"])
        end = min(date.fromisoformat(stage["end_date"]), available_through)
        expected = max(0, (end - start).days + 1)
        selected_days = sorted(day for day in rows if start <= day <= end)
        selected = [rows[day] for day in selected_days]
        if selected:
            any_rows = True
            output[stage["name"]] = {"status": "available" if len(selected) == expected else "partial_coverage",
                "days_expected_available": expected, "days_observed": len(selected),
                "missing_days": max(0, expected - len(selected)), "coverage_fraction": round(len(selected) / expected, 4) if expected else 0,
                "precipitation_total_mm": round(sum(x["precipitation_mm"] for x in selected), 2),
                "tmax_mean_c": round(sum(x["tmax_c"] for x in selected) / len(selected), 2),
                "tmax_ge_threshold_days": sum(x["tmax_c"] >= WEATHER_HEAT_THRESHOLD_C for x in selected),
                "heat_threshold_c": WEATHER_HEAT_THRESHOLD_C,
                "tmin_mean_c": round(sum(x["tmin_c"] for x in selected) / len(selected), 2),
                "precipitation_unit": "mm", "temperature_unit": "degC",
                "date_start": selected_days[0].isoformat(), "date_end": selected_days[-1].isoformat()}
        else:
            output[stage["name"]] = {"status": "missing_date_coverage", "days_expected_available": expected, "days_observed": 0, "missing_days": expected, "coverage_fraction": 0}
    return {"source_class": "reanalysis", "status": "available" if any_rows else "missing_date_coverage",
            "dataset": "Open-Meteo ERA5 daily Pune grid fixture", "version": "ERA5-2015-retained-full-archive",
            "source_id": "open-meteo-pune-historical-era5-2015",
            "sha256": "5B1CBCFC830C3FBDD67C53A76AB7E220A88C23D56177DF10B7AED1C40E495F9E",
            "geography": "Pune grid cell; not farm observation", "timezone": "Asia/Kolkata",
            "as_of_cutoff": as_of.isoformat(), "availability_lag_days": WEATHER_AVAILABILITY_LAG_DAYS,
            "latest_admissible_observation_date": available_through.isoformat(),
            "future_observations_excluded": True, "stages": output}


def _stage_response_features(stages: list[dict], reanalysis: dict, *, crop: str,
                             heat_stage: str | None, heat_days: int, rainfall_change_pct: float,
                             irrigation_fraction: float) -> dict:
    """Create an explicitly illustrative response from available weather and scenario inputs."""
    result, total_loss = {}, D("0")
    observed_stage_data = reanalysis.get("stages", {})
    for stage in stages:
        name = stage["name"]
        sensitivity = D(SENSITIVITY[crop][name])
        evidence = observed_stage_data.get(name, {})
        observed_complete = evidence.get("status") == "available" and evidence.get("days_observed", 0) > 0
        observed_heat = D(str(evidence.get("tmax_ge_threshold_days", 0))) if observed_complete else D("0")
        observed_days = D(str(evidence.get("days_observed", 0))) if observed_complete else D("0")
        observed_rain = D(str(evidence.get("precipitation_total_mm", 0))) if observed_complete else D("0")
        reference_rain = D(str(ILLUSTRATIVE_RAIN_REFERENCE_MM_PER_DAY)) * observed_days
        historical_water_deficit = max(D("0"), (reference_rain - observed_rain) / reference_rain) if reference_rain else D("0")
        scenario_heat = D(heat_days if name == heat_stage else 0)
        scenario_rain_deficit = D(str(max(0.0, -rainfall_change_pct) / 100))
        heat_component = (observed_heat + scenario_heat) * D("0.012") * sensitivity
        historical_water_component = historical_water_deficit * D("0.22") * (1 - D(str(irrigation_fraction))) * sensitivity
        scenario_water_component = scenario_rain_deficit * D("0.22") * (1 - D(str(irrigation_fraction))) * sensitivity
        stress = min(D("1"), heat_component + historical_water_component + scenario_water_component)
        total_loss += stress
        if stage["calendar_status"] == "unavailable_short_season":
            status = "unavailable_short_season"
        elif observed_complete and (heat_days or rainfall_change_pct):
            status = "reanalysis_plus_hypothetical"
        elif observed_complete:
            status = "historical_reanalysis"
        elif heat_days or rainfall_change_pct:
            status = "hypothetical_fallback"
        else:
            status = "missing_weather_zero_response_fallback"
        result[name] = {
            "stress_index": round(float(stress), 4), "status": status,
            "source_class": ("reanalysis_and_hypothetical" if observed_complete and (heat_days or rainfall_change_pct)
                             else "reanalysis" if observed_complete else "hypothetical_scenario" if heat_days or rainfall_change_pct else "missing"),
            "weather_evidence_id": reanalysis.get("source_id") if observed_complete else None,
            "weather_days": int(observed_days), "observed_heat_days_ge_35c": int(observed_heat),
            "historical_rain_deficit_fraction": round(float(historical_water_deficit), 4) if observed_complete else None,
            "hypothetical_heat_days": int(scenario_heat),
            "hypothetical_rainfall_change_pct": rainfall_change_pct,
            "irrigation_mitigation_fraction": irrigation_fraction,
            "assumptions": {"heat_yield_loss_per_day": 0.012,
                "illustrative_reference_rain_mm_per_day": ILLUSTRATIVE_RAIN_REFERENCE_MM_PER_DAY,
                "water_stress_weight": 0.22, "stage_sensitivity": float(sensitivity)},
        }
    return {"stages": result, "combined_loss_fraction": min(D("0.45"), total_loss),
            "rule_version": "stage-response-v4", "source_class": "illustrative_rule",
            "status": "illustrative_not_trained_or_calibrated",
            "limitations": ["Crop calendar and response coefficients are illustrative, not region-calibrated.",
                "ERA5 is a roughly 25 km grid reanalysis, not farm weather.",
                "Missing or partial weather is not treated as an observed zero.",
                "Rainfall reference and response weights are explicit demonstration assumptions."]}


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
    accrued_interest = money(original_due - principal)
    if action == "reschedule_30d":
        extra = money(principal * rate * 30 / 365)
        schedule = [{"date": due_date + timedelta(days=30), "amount_inr": original_due + extra,
                     "principal_due_inr": principal, "interest_due_inr": accrued_interest + extra, "fee_due_inr": D("0.00")}]
    elif action == "split_payment":
        fee = money(original_due * D("0.015"))
        extra_interest = money(principal / 2 * rate * 45 / 365)
        extra = fee + extra_interest
        first = money((original_due + fee) / 2)
        principal_first = money(principal / 2)
        interest_first = money(accrued_interest / 2)
        fee_first = money(fee / 2)
        schedule = [{"date": due_date, "amount_inr": first, "principal_due_inr": principal_first,
                     "interest_due_inr": interest_first, "fee_due_inr": money(first-principal_first-interest_first)},
                    {"date": due_date + timedelta(days=45), "amount_inr": original_due + fee - first + extra_interest,
                     "principal_due_inr": money(principal-principal_first),
                     "interest_due_inr": money(accrued_interest-interest_first+extra_interest),
                     "fee_due_inr": money(fee-fee_first)}]
    else:
        schedule = [{"date": due_date, "amount_inr": original_due, "principal_due_inr": principal,
                     "interest_due_inr": accrued_interest, "fee_due_inr": D("0.00")}]
    return schedule, money(extra), original_due


def build_dated_ledger(b: dict, revenue: Decimal, sale_date: date, schedule: list[dict], bridge_limit: Decimal,
                       *, opening_cash=None, carried_formal=D("0"), carried_informal=D("0"), shift=0,
                       minimum_reserve=D("0")) -> dict:
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
        events.append({"date": item["date"], "kind": "bank_due", "due_inr": item["amount_inr"], "priority": 2,
                       "principal_due_inr": item.get("principal_due_inr", b["loan_principal_inr"]),
                       "interest_due_inr": item.get("interest_due_inr", D("0")) + (carried_formal * b["annual_rate"] if item is scheduled[0] else D("0")),
                       "fee_due_inr": item.get("fee_due_inr", D("0"))})
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
        available = max(D("0.00"), money(pre - minimum_reserve))
        gap = max(D("0.00"), money(amount - available))
        draw = min(remaining_bridge, gap)
        if draw:
            post(event["date"], "informal_bridge_draw", draw)
            draws.append((event["date"], draw))
            remaining_bridge -= draw
        paid = min(amount, max(D("0.00"), money(cash - minimum_reserve)))
        unpaid = money(amount - paid)
        formal_balance += unpaid
        fee_paid = min(paid, money(event.get("fee_due_inr", D("0"))))
        interest_paid = min(money(paid-fee_paid), money(event.get("interest_due_inr", D("0"))))
        principal_paid = min(money(paid-fee_paid-interest_paid), money(event.get("principal_due_inr", b["loan_principal_inr"])))
        post(event["date"], "bank_payment", -paid, scheduled_due_inr=amount,
             principal_paid_inr=principal_paid, interest_paid_inr=interest_paid, fee_paid_inr=fee_paid)
        payments.append({"date": event["date"].isoformat(), "cash_before_due_inr": pre,
                         "cash_available_above_reserve_inr": available, "minimum_reserve_inr": money(minimum_reserve),
                         "bank_due_inr": amount, "cash_gap_inr": gap, "informal_draw_inr": draw,
                         "formal_paid_inr": paid, "principal_paid_inr": principal_paid,
                         "interest_paid_inr": interest_paid, "fee_paid_inr": fee_paid, "unmet_due_inr": unpaid,
                         "unpaid_principal_inr": money(event.get("principal_due_inr", b["loan_principal_inr"])-principal_paid),
                         "unpaid_interest_inr": money(event.get("interest_due_inr", D("0"))-interest_paid),
                         "unpaid_fee_inr": money(event.get("fee_due_inr", D("0"))-fee_paid),
                         "cash_after_due_inr": cash, "signed_post_payment_cash_inr": cash})
    season_end = max(sale_date, scheduled[-1]["date"]) + timedelta(days=7)
    informal_rate = D(WARNING_CONFIG["informal_rate"])
    informal_interest = money(carried_informal * informal_rate + sum((amount * informal_rate * D((season_end - when).days) / 365 for when, amount in draws), D("0")))
    informal_due = money(carried_informal + sum((amount for _, amount in draws), D("0")) + informal_interest)
    informal_paid = min(max(D("0.00"), cash), informal_due)
    if informal_paid:
        post(season_end, "informal_payment", -informal_paid)
    informal_balance = money(informal_due - informal_paid)
    return {"opening_cash_inr": money(opening), "minimum_reserve_inr": money(minimum_reserve), "cash_by_date": ledger, "payments": payments,
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
    stages = _calendar(b)
    stage_by_name = {row["name"]: row for row in stages}
    selected_window = stage_by_name[stage]
    if selected_window["calendar_status"] == "unavailable_short_season":
        if heat:
            raise ValueError(f"The {stage} stage is unavailable because the season is too short to define all five stages")
        stage = next(row["name"] for row in stages if row["start_date"])
        selected_window = stage_by_name[stage]
    event_start = o.heatwave_start_date if shock and o.heatwave_start_date else (
        date.fromisoformat(selected_window["start_date"]) +
        timedelta(days=max(0, (date.fromisoformat(selected_window["end_date"]) -
                               date.fromisoformat(selected_window["start_date"])).days - max(heat - 1, 0)) // 2))
    if heat:
        matched = next((row for row in stages if row["start_date"] and
                        date.fromisoformat(row["start_date"]) <= event_start <= date.fromisoformat(row["end_date"])), None)
        if matched is None or date.fromisoformat(matched["end_date"]) < event_start + timedelta(days=heat - 1):
            raise ValueError("Hypothetical heat event must fit inside one declared stage window and crop season")
        stage = matched["name"]
    reanalysis = _daily_reanalysis(b, stages, req.as_of)
    response = _stage_response_features(stages, reanalysis, crop=b["crop"],
        heat_stage=stage if shock else None, heat_days=heat if shock else 0,
        rainfall_change_pct=rain if shock else 0, irrigation_fraction=float(irrigation))
    stress_features = {name: response["stages"][name]["stress_index"] for name in STAGE_NAMES}
    yield_value = (b["yield_t_per_ha"] * (1 - response["combined_loss_fraction"])).quantize(D("0.0001"))
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
    stage_weather = {}
    for row in stages:
        raw = reanalysis["stages"].get(row["name"], {"status": reanalysis.get("status", "missing"), "days_observed": 0})
        stage_weather[row["name"]] = {"reanalysis": raw, "response": response["stages"][row["name"]],
            "hypothetical": {"status": "provided" if shock and (heat or rain) else "not_provided",
                "source_class": "hypothetical_scenario", "heat_event_applies_to_stage": bool(shock and heat and row["name"] == stage),
                "heat_event_start_date": event_start.isoformat() if shock and heat and row["name"] == stage else None,
                "heat_event_end_date": (event_start + timedelta(days=heat - 1)).isoformat() if shock and heat and row["name"] == stage else None,
                "heatwave_days": heat if shock else 0,
                "rainfall_change_pct": rain if shock else 0,
                "illustrative_stress_index": stress_features[row["name"]]}}
    inputs = {
        "satellite": {"name": "NDVI / FPAR", "value": None, "unit": "index", "status": "unavailable", "source": None},
        "weather_forecast": {"rainfall_change_pct": rain, "heatwave_days": heat, "heatwave_growth_stage": stage, "heatwave_start_date": event_start if shock and heat else None, "status": "hypothetical_scenario", "issued_at": None, "operational_forecast": {"status": "unavailable"}},
        "soil": {"name": "Soil moisture", "value": None, "unit": "volumetric fraction", "status": "unavailable"},
        "crop": {"name": b["crop"], "area_ha": b["area_ha"], "season_start": b["sowing_date"], "season_end": b["harvest_date"], "status": "synthetic_borrower_assumption"},
        "irrigation": {"fraction": irrigation, "unit": "fraction of area", "status": "synthetic_borrower_input"},
        "yield_history": {"baseline_t_per_ha": b["yield_t_per_ha"], "projected_t_per_ha": yield_value, "unit": "t/ha", "status": "assumed_illustrative_response", "historical_observations": None,
            "source_class": "illustrative_rule", "rule_version": response["rule_version"], "limitations": response["limitations"]},
        "market_price": {"inr_per_quintal": price, "unit": "INR/quintal", "status": "assumed_demo_input", "observed_at": None},
        "credit_history": {"events": b["credit_history"], "status": "synthetic_demo_records", "observed_bank_data": False},
    }
    return {**ledger, "yield_t_per_ha": yield_value, "production_tonnes": production, "price_inr_per_quintal": price,
            "gross_revenue_inr": revenue, "sale_date": sale_date.isoformat(), "due_date": schedule[0]["date"].isoformat(),
            "contractual_due_inr": original_due, "loan_schedule": schedule, "action_cost_inr": cost, "action_id": action,
            "stage_stress": stress_features, "stage_weather_features": stage_weather, "crop_stages": stages,
            "crop_calendar": {**CALENDAR_PROVENANCE, "crop": b["crop"], "declared_geography": b["district"], "sowing_date": b["sowing_date"], "harvest_date": b["harvest_date"], "season_days": (b["harvest_date"]-b["sowing_date"]).days + 1, "ordered": True, "overlap_policy": "none; season-relative partition", "short_season_policy": "leave stages without a day unavailable"},
            "reanalysis": reanalysis,
            "yield_projection": {"value": yield_value, "unit": "t/ha", "source_class": "illustrative_rule", "version": response["rule_version"], "status": response["status"], "limitations": response["limitations"], "combined_loss_fraction": response["combined_loss_fraction"]},
            "heat_event": {"stage": stage, "start_date": event_start.isoformat() if heat else None,
                           "end_date": (event_start + timedelta(days=heat - 1)).isoformat() if heat else None, "duration_days": heat,
                           "source_class": "hypothetical_scenario" if heat else "none"},
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
                     "yield_projection": a["yield_projection"],
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
            "reconciliation_delta_inr": money(balance - stress["cash_pre_due_inr"]),
            "attribution": "Sequential quantity then price attribution when both sales arrive by the due date; otherwise proceeds timing is attributed as one dated effect. Rounded residual pennies are assigned to the final effect. Sale proceeds after due are excluded."}


# ---------------------------------------------------------------------------
# F5 — Canonical dated ledger, credit history summary, feasibility detail
# ---------------------------------------------------------------------------

def build_canonical_ledger(b: dict, stress: dict) -> dict:
    """F5: Authoritative chronological ledger with stable event IDs and formal/informal breakdown.

    Each event carries a stable ID derived from its date+kind so replaying the
    same inputs always produces the same IDs. Amounts are in exact INR (Decimal,
    rounded to paise). The running cash balance is computed sequentially and
    reconciles to the paise against stress[net_free_cash_inr].
    """
    import hashlib as _hl

    def _eid(when: str, category: str, seq: int) -> str:
        return "EVT-" + _hl.sha256(f"{when}:{category}:{seq}".encode()).hexdigest()[:12].upper()

    raw_events = stress["cash_by_date"]   # from build_dated_ledger
    balance = money(b["initial_cash_inr"])

    # Rebuild principal / interest breakdown for bank_payment rows
    # Principal is the loan principal; interest = due - principal
    principal = b["loan_principal_inr"]
    principal_repaid = D("0")

    canonical_events: list[dict] = []
    seq = 0

    # Opening balance synthetic entry
    canonical_events.append({
        "event_id": _eid(b["disbursed_at"].isoformat(), "opening_balance", seq),
        "effective_date": b["disbursed_at"].isoformat(),
        "category": "opening_balance",
        "direction": "credit",
        "amount_inr": str(money(b["initial_cash_inr"])),
        "principal_component_inr": None,
        "interest_component_inr": None,
        "running_cash_inr": str(money(b["initial_cash_inr"])),
        "data_status": "synthetic_and_assumed",
        "source_ids": [SOURCE_VERSION],
        "evidence_id": None,
        "scenario_only": True,
        "note": "Synthetic opening cash from demo borrower profile",
    })
    seq += 1

    for ev in raw_events:
        kind = ev["kind"]
        amount = D(str(ev["amount_inr"]))
        when = ev["date"]
        direction = "credit" if amount >= 0 else "debit"
        abs_amount = money(abs(amount))

        principal_comp = None
        interest_comp = None

        if kind == "bank_payment":
            interest = money(ev.get("interest_paid_inr", 0))
            fee = money(ev.get("fee_paid_inr", 0))
            p_paid = money(ev.get("principal_paid_inr", max(D("0"), abs_amount - interest - fee)))
            principal_repaid = money(principal_repaid + p_paid)
            principal_comp = str(p_paid)
            interest_comp = str(interest)
            fee_comp = str(fee)
            cat = "bank_debt_service"
        elif kind == "loan_disbursement":
            cat = "loan_disbursement"
            principal_comp = str(abs_amount)
        elif kind == "crop_inputs":
            cat = "input_cost"
        elif kind == "household_expense":
            cat = "household_cost"
        elif kind == "crop_sale":
            cat = "crop_sale_proceeds"
        elif kind == "informal_bridge_draw":
            cat = "informal_bridge_draw"
        elif kind == "informal_payment":
            cat = "informal_debt_service"
        else:
            cat = kind
        if kind != "bank_payment":
            fee_comp = None

        canonical_events.append({
            "event_id": _eid(when, cat, seq),
            "effective_date": when,
            "category": cat,
            "direction": direction,
            "amount_inr": str(abs_amount),
            "principal_component_inr": principal_comp,
            "interest_component_inr": interest_comp,
            "fee_component_inr": fee_comp,
            "running_cash_inr": str(money(D(str(ev["cash_after_inr"])))),
            "data_status": "synthetic_and_assumed",
            "source_ids": [SOURCE_VERSION],
            "evidence_id": None,
            "scenario_only": True,
            "note": f"Modelled {cat.replace('_', ' ')} entry; not a bank transaction record.",
        })
        seq += 1

    # Reconciliation check
    last_cash = D(str(canonical_events[-1]["running_cash_inr"])) if canonical_events else D("0")
    expected = money(D(str(stress["net_free_cash_inr"])))
    reconciled = last_cash == expected

    return {
        "events": canonical_events,
        "opening_cash_inr": str(money(b["initial_cash_inr"])),
        "closing_cash_inr": str(last_cash),
        "expected_closing_cash_inr": str(expected),
        "reconciled_to_paise": reconciled,
        "rounding_policy": "ROUND_HALF_UP to 2 decimal places (paise) at each step",
        "event_id_policy": "SHA-256 of effective_date:category:sequence_index, first 12 hex chars upper-cased",
        "data_status": "synthetic_and_assumed",
        "source_ids": [SOURCE_VERSION],
        "limitations": [
            "All entries are synthetic; no real bank transaction data is connected.",
            "Loan disbursement and crop sale dates are demo assumptions.",
            "Principal/interest breakdown uses the contractual split; arrears interest is simplified.",
        ],
        "minimum_reserve_policy": "INR 0.00; all non-negative cash is available for a contractual payment.",
        "unpaid_obligations": [
            {"obligation_id": "OBL-" + _hl.sha256(f"{p['date']}:bank_due:{i}".encode()).hexdigest()[:12].upper(),
             "effective_date": p["date"], "category": "unpaid_formal_bank_due",
             "amount_inr": str(p["unmet_due_inr"]), "scenario_only": True,
             "source_ids": [SOURCE_VERSION]}
            for i, p in enumerate(stress.get("payments", [])) if p["unmet_due_inr"] > 0
        ],
    }


def derive_credit_history_summary(b: dict, as_of: date) -> dict:
    """F5: Credit history with explicit provenance; distinguishes missing from perfect record."""
    events = [*b.get("credit_history", []), *b.get("posted_loan_events", [])]
    as_of_events = []
    undated_events = []
    for e in events:
        d = e.get("date") or e.get("effective_date")
        if d:
            if date.fromisoformat(str(d)) <= as_of:
                as_of_events.append(e)
        else:
            undated_events.append(e)
    scheduled = sum(1 for e in as_of_events if e.get("kind") == "scheduled_repayment")
    reversed_event_ids = {e.get("reversal_of_event_id") for e in as_of_events if e.get("kind") == "reversal"}
    active_events = [e for e in as_of_events if e.get("event_id") not in reversed_event_ids]
    actual = sum(1 for e in active_events if e.get("kind") in {"actual_repayment", "repayment"})
    overdue_events = [e for e in active_events if e.get("days_overdue", 0) > 0]
    renewals = sum(1 for e in active_events if e.get("kind") in {"renewal", "rollover"} or e.get("status") in {"renewal", "rollover"})
    utilization_values = [D(str(e["utilization_fraction"])) for e in active_events if e.get("utilization_fraction") is not None]
    return {
        "events_as_of": [{**_jsonable(e), "data_provenance": e.get("source_status", "synthetic_demo_records")} for e in as_of_events],
        "undated_history_events": [{**_jsonable(e), "data_provenance": e.get("source_status", "synthetic_demo_records"), "as_of_eligibility": "unknown_date_excluded_from_as_of_counts"} for e in undated_events],
        "total_scheduled_payments": scheduled,
        "total_actual_payments": actual,
        "overdue_event_count": len(overdue_events),
        "max_days_overdue": max((e.get("days_overdue", 0) for e in overdue_events), default=0),
        "arrears_detected": len(overdue_events) > 0,
        "renewal_or_rollover_count": renewals,
        "utilization_fraction": str(utilization_values[-1]) if utilization_values else None,
        "data_provenance": "synthetic_demo_records_and_posted_demo_journal" if b.get("posted_loan_events") else "synthetic_demo_records",
        "observed_bank_data": False,
        "history_completeness": "partial_synthetic" if as_of_events or undated_events else "absent_no_history_available",
        "limitations": [
            "Records are synthetic; no real bank repayment history is connected.",
            "Absent history is distinguished from a confirmed perfect payment record.",
            "Future payment events are excluded; undated records are retained separately but not counted as of the assessment date.",
        ],
    }


def derive_feasibility_detail(stress: dict, b: dict) -> dict:
    """F5: Deterministic feasibility with documented scope; no invented probability."""
    pb = stress["probability_basis"]
    payments = stress.get("payments", [])
    gap_payments = [p for p in payments if D(str(p["cash_gap_inr"])) > 0]
    total_gap = money(sum(D(str(p["cash_gap_inr"])) for p in gap_payments))
    return {
        "deterministic_result": "gap_exists" if gap_payments else "no_gap_at_current_inputs",
        "cash_gap_inr": str(stress["cash_gap_inr"]),
        "cash_gap_total_all_dues_inr": str(stress.get("cash_gap_total_inr", stress["cash_gap_inr"])),
        "payments_with_gap": len(gap_payments),
        "total_payments": len(payments),
        "simulated_repayment_rate": str(stress["repayment_probability_simulated"]),
        "simulated_shortfall_rate": str(stress["p_shortfall"]),
        "simulation_scope": {
            "paths": pb["paths"],
            "repaid_paths": pb["repaid_paths"],
            "shortfall_paths": pb["shortfall_paths"],
            "type": pb["type"],
            "yield_range": pb["yield_range"],
            "price_range": pb["price_range"],
            "calibrated_to_observed_defaults": pb["calibrated"],
        },
        "formal_balance_end_inr": str(stress["formal_balance_end_inr"]),
        "formal_repayment_status": stress["formal_repayment_status"],
        "revenue_before_due": str(stress["cash_pre_due_inr"]),
        "contractual_due": str(stress["due_inr"]),
        "minimum_reserve_inr": str(stress.get("minimum_reserve_inr", D("0.00"))),
        "same_day_ordering_policy": "Loan disbursement and crop sale (priority 0, then kind order), input and household costs (priority 1), then bank due (priority 2); same-priority events use stable kind order.",
        "revenue_after_due_policy": "Sale proceeds dated after the bank due date cannot settle that due.",
        "limitations": [
            "Feasibility is conditioned on the synthetic demo scenario only.",
            "21-path simulation uses equally weighted hypothetical yield/price perturbations.",
            "No model is trained or calibrated to observed agricultural credit defaults.",
            "Probability fields describe this finite scenario set, not population-level default risk.",
        ],
    }


def evaluate_scenario(req: ScenarioRequest) -> dict:
    b = _resolve_borrower(req.borrower_id)
    # New demo applications can be assessed against their requested principal
    # without mutating the borrower's existing synthetic profile.
    if req.loan_principal_override_inr is not None:
        b["loan_principal_inr"] = D(str(req.loan_principal_override_inr))
    from app.db import get_loan_record
    posted = (get_loan_record(req.borrower_id) or {}).get("posted_events", [])
    b["posted_loan_events"] = [event for event in posted if date.fromisoformat(event["date"]) <= req.as_of]
    baseline = _assessment(b, req, shock=False)
    stress = _assessment(b, req, shock=True)
    # Persist the actual calendar stage as the canonical request value when a
    # date was supplied, so UI controls, snapshots, and driver text agree.
    req.overrides.heatwave_growth_stage = stress["heat_event"]["stage"]
    eligible = req.as_of < b["due_at"]
    action = _assessment(b, req, shock=True, action=req.action_id) if req.action_id != "none" and eligible else None
    baseline["debt_cycle"] = _three_seasons(b, baseline, req, bridge_enabled=False)
    stress["debt_cycle"] = _three_seasons(b, stress, req, bridge_enabled=True)
    if action:
        action["debt_cycle"] = _three_seasons(b, action, req, bridge_enabled=True)
    warnings = derive_debt_warnings(stress["debt_cycle"], stress, action)
    path_definition = [{"path": i, "yield_multiplier_pct": i * 2, "price_multiplier_pct": i}
                       for i in range(-10, 11)]
    climate_path_hash = hashlib.sha256(json.dumps({"seed": DEMO_SEED, "paths": path_definition},
        sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    climate_snapshot_hash = hashlib.sha256(WEATHER_PATH.read_bytes()).hexdigest() if WEATHER_PATH.exists() else "unavailable"
    source_versions = {"demo_fixture": SOURCE_VERSION, "engine": ENGINE_VERSION,
                       "crop_calendar": CALENDAR_VERSION, "yield_rule": "stage-response-v3",
                       "weather_fixture": "ERA5-2015-retained-full-archive", "warnings": WARNING_CONFIG["version"],
                       "weather_snapshot_hash": climate_snapshot_hash, "climate_path_hash": climate_path_hash}
    frozen = {"borrower": _jsonable(b), "as_of": req.as_of.isoformat(), "timezone": "Asia/Kolkata",
              "seed": DEMO_SEED, "climate_paths": {"count": len(path_definition), "hash": climate_path_hash},
              "sources": source_versions}
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
        "warnings": ["All lending records are synthetic; climate/yield/price inputs are assumed.", "Crop calendar is an illustrative timing fixture, not a verified regional agronomic calendar.", "Actions require bank review; informal borrowing is a user-selected simulation."],
        # F5 — additive new fields; do not remove or rename existing keys above
        "snapshot_freshness": "current",
        "snapshot_stale_reasons": [],
        "cash_ledger": build_canonical_ledger(b, stress),
        "credit_history_summary": derive_credit_history_summary(b, req.as_of),
        "feasibility_detail": derive_feasibility_detail(stress, b),
        "f5_ledger_version": "f5-canonical-ledger-v1",
    })
