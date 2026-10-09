"""F8 intervention catalog, eligibility, evaluation metadata, and ranking."""
from __future__ import annotations

from copy import deepcopy
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
from typing import Any

from app.schemas import InterventionEvaluationRequest, ScenarioRequest
from app.services.assessment import _resolve_borrower, evaluate_scenario, money

D = Decimal
POLICY = json.loads((Path(__file__).parents[1] / "config" / "interventions.json").read_text(encoding="utf-8"))
CATALOG = {row["id"]: row for row in POLICY["catalog"]}


def action_catalog() -> dict:
    return deepcopy(POLICY)


def _date(value: Any) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        return None


def _option(candidate_id: str, action_ids: list[str], inputs: dict[str, Any], base_request: ScenarioRequest,
            base: dict) -> dict:
    rows = [CATALOG[action_id] for action_id in action_ids]
    option = {"candidate_id": candidate_id, "action_ids": action_ids, "label": " + ".join(row["label"] for row in rows),
              "evaluable": all(row["evaluable"] for row in rows), "eligible": True, "status": "eligible",
              "reasons": [], "mechanisms": [row["mechanism"] for row in rows],
              "source_tags": sorted({row["source_tag"] for row in rows}), "policy_version": POLICY["version"],
              "policy_class": POLICY["policy_class"], "numeric_effects_declared": True}
    if not option["evaluable"]:
        option.update({"status": "unsupported", "eligible": False, "numeric_effects_declared": False})
        borrower = _resolve_borrower(base_request.borrower_id)
        sowing_complete = base_request.as_of >= borrower["sowing_date"]
        option["sowing_status"] = "already_sown" if sowing_complete else "pre_sowing"
        option["reasons"].append(
            ("Sowing is already complete; " if sowing_complete else "Assessment is pre-sowing; ")
            + "no admitted region and crop-specific agronomic configuration supports this hypothetical option.")
        return option

    as_of = base_request.as_of
    borrower = _resolve_borrower(base_request.borrower_id)
    due = borrower["due_at"]
    stress = base["stress"]
    parameters: dict[str, Any] = {"candidate_id": candidate_id, "schedule_action": "none", "cash_events": [],
                                  "program_cost_inr": "0.00", "source_tags": option["source_tags"]}
    for action_id in action_ids:
        action_input = inputs.get(action_id, {}) if isinstance(inputs.get(action_id, {}), dict) else {}
        if action_id in {"reschedule_30d", "split_payment"}:
            if as_of >= due:
                option["eligible"] = False
                option["reasons"].append("The contractual due date has passed as of this assessment.")
            parameters["schedule_action"] = action_id
        elif action_id == "outreach":
            option["numeric_effects_declared"] = False
            option["reasons"].append("Outreach has no automatic numeric risk reduction in this model.")
        elif action_id == "irrigation_support":
            water = action_input.get("water_access_confirmed") is True
            effective = _date(action_input.get("effective_date"))
            stress_start = _date(stress.get("heat_event", {}).get("start_date"))
            fraction = action_input.get("irrigation_fraction_after")
            if not water:
                option["eligible"] = False
                option["reasons"].append("Water access is not explicitly confirmed for this scenario.")
            if effective is None or stress_start is None or effective > stress_start or effective < as_of:
                option["eligible"] = False
                option["reasons"].append("Effective date must be on or after assessment and before the modeled stress window.")
            try:
                fraction = D(str(fraction))
                if fraction <= borrower["irrigation_fraction"] or fraction > 1:
                    raise ValueError()
                parameters["irrigation_fraction_after"] = str(fraction)
            except (ValueError, TypeError, InvalidOperation):
                option["eligible"] = False
                option["reasons"].append("A valid higher post-support irrigation fraction from 0 to 1 is required.")
            try:
                cost = D(str(action_input.get("cost_inr", "0")))
                if cost < 0:
                    raise ValueError()
                parameters["program_cost_inr"] = str(cost)
            except (ValueError, TypeError, InvalidOperation):
                option["eligible"] = False
                option["reasons"].append("A non-negative assumed support cost is required.")
            option["source_tags"].append("assumed_intervention_effect")
        elif action_id == "hypothetical_assistance":
            try:
                amount = money(D(str(action_input.get("amount_inr", "0"))))
                budget = money(D(str(action_input.get("budget_inr", "0"))))
                effective = _date(action_input.get("effective_date"))
                if amount <= 0 or amount > D(str(POLICY["constraints"]["assistance_max_inr"])):
                    raise ValueError("Assistance amount must be positive and within the illustrative policy maximum.")
                if budget < amount:
                    raise ValueError("Declared scenario budget does not cover the assistance amount.")
                if effective is None or effective < as_of:
                    raise ValueError("Assistance needs an explicit date on or after the assessment date.")
                parameters["cash_events"].append({"kind": "hypothetical_assistance", "date": effective.isoformat(),
                    "amount_inr": str(amount), "source_tag": "assumed"})
                parameters["program_cost_inr"] = str(amount)
                option["assumption_tags"] = ["hypothetical_assistance_amount", "declared_budget", "assumed_effective_date"]
            except (ValueError, TypeError, InvalidOperation) as exc:
                option["eligible"] = False
                option["reasons"].append(str(exc))
        elif action_id == "insurance_scenario":
            enrolled = action_input.get("enrolled") is True
            enrollment = _date(action_input.get("enrollment_date"))
            policy_days = int(POLICY["constraints"]["insurance_enrollment_cutoff_days_before_due"])
            shift_days = int(POLICY["constraints"]["max_due_shift_days"])
            split_delay = int(POLICY["constraints"]["split_second_payment_delay_days"])
            if "reschedule_30d" in action_ids:
                repayment_dates = [due + timedelta(days=shift_days)]
            elif "split_payment" in action_ids:
                repayment_dates = [due, due + timedelta(days=split_delay)]
            else:
                repayment_dates = [due]
            repayment_cutoffs = [{"repayment_date": repayment_date.isoformat(),
                "enrollment_cutoff": (repayment_date - timedelta(days=policy_days)).isoformat()}
                for repayment_date in repayment_dates]
            cutoff = min(date.fromisoformat(row["enrollment_cutoff"]) for row in repayment_cutoffs)
            trigger = action_input.get("trigger_met") is True
            payout_date = _date(action_input.get("payout_date"))
            try:
                payout = money(D(str(action_input.get("payout_inr", "0"))))
                premium = money(D(str(action_input.get("premium_inr", "0"))))
                if payout < 0 or premium < 0:
                    raise ValueError()
            except (ValueError, TypeError, InvalidOperation):
                payout, premium = D("0.00"), D("0.00")
                option["eligible"] = False
                option["reasons"].append("Payout and premium must be non-negative numeric amounts.")
            modeled_end = max(_date(stress.get("sale_date")) or due, due) + timedelta(days=7)
            payout_allowed = enrolled and enrollment is not None and enrollment <= cutoff and trigger and payout_date is not None and as_of <= payout_date <= modeled_end and payout_date >= enrollment and payout > 0
            option["insurance_terms"] = {"enrolled_explicitly": enrolled, "enrollment_cutoff": cutoff.isoformat(),
                "repayment_cutoffs": repayment_cutoffs,
                "trigger_met_explicitly": trigger, "modeled_payout_inr": str(payout if payout_allowed else D("0.00")),
                "payout_date": payout_date.isoformat() if payout_allowed else None, "premium_inr": str(premium if enrolled else D("0.00"))}
            if enrolled and enrollment is None:
                option["eligible"] = False
                option["reasons"].append("Enrollment date is required; retroactive enrollment is never assumed.")
            elif enrolled and enrollment and enrollment > cutoff:
                option["eligible"] = False
                option["reasons"].append("Enrollment date misses the illustrative cutoff; payout is zero.")
            elif not enrolled:
                option["eligible"] = False
                option["reasons"].append("No explicit enrollment is supplied; modeled payout is zero.")
            if enrolled and (not trigger or payout_date is None or payout_date < enrollment or payout_date < as_of or payout_date > modeled_end):
                option["reasons"].append("Payout remains zero without an explicit valid trigger and dated payout timing.")
            if enrolled and premium > 0:
                if enrollment is None:
                    option["eligible"] = False
                    option["reasons"].append("Premium enrollment date must be explicit.")
                else:
                    parameters["program_cost_inr"] = str(premium)
                    if enrollment >= as_of:
                        parameters["cash_events"].append({"kind": "insurance_premium", "date": enrollment.isoformat(),
                            "amount_inr": str(-premium), "source_tag": "assumed"})
            if payout_allowed:
                parameters["cash_events"].append({"kind": "insurance_payout", "date": payout_date.isoformat(),
                    "amount_inr": str(payout), "source_tag": "assumed"})
            option["source_tags"].append("illustrative_insurance_terms_unverified")
    if not option["eligible"]:
        option["status"] = "ineligible"
        return option
    if not option["reasons"]:
        option["reasons"].append("Meets the declared illustrative scenario constraints; this is not operational eligibility.")
    option["action_parameters"] = parameters
    return option


def evaluate_action_candidates(req: InterventionEvaluationRequest) -> tuple[dict, list[dict]]:
    base_request = ScenarioRequest.model_validate(req.model_dump(exclude={"action_inputs", "action_id", "action_parameters"}) |
                                                  {"action_id": "none", "action_parameters": {}})
    baseline = evaluate_scenario(base_request)
    options: list[dict] = []
    for action_id in CATALOG:
        options.append(_option(action_id, [action_id], req.action_inputs, base_request, baseline))
    for pair in POLICY["compatible_pairs"]:
        action_ids = list(pair)
        candidate_id = "+".join(action_ids)
        options.append(_option(candidate_id, action_ids, req.action_inputs, base_request, baseline))
    for pair in POLICY["incompatible_pairs"]:
        action_ids = list(pair)
        options.append({"candidate_id": "+".join(action_ids), "action_ids": action_ids,
            "label": " + ".join(CATALOG[a]["label"] for a in action_ids), "evaluable": False,
            "eligible": False, "status": "incompatible", "reasons": ["These actions change the same repayment schedule and cannot be combined."],
            "policy_version": POLICY["version"], "policy_class": POLICY["policy_class"], "source_tags": ["assumed"]})
    return baseline, options


def score_action_option(option: dict, base: dict, result: dict) -> dict:
    weights = POLICY["objective"]["weights"]
    control = base["stress"]
    action = result.get("stress_with_action")
    if action is None:
        return {**option, "eligible": False, "status": "ineligible", "reasons": [*option["reasons"], "Shared assessment rejected this action at the current as-of date."]}
    gap_relief = D(str(control["cash_gap_inr"])) - D(str(action["cash_gap_inr"]))
    base_interest = sum((D(str(row.get("interest_due_inr", 0))) for row in control["loan_schedule"]), D("0"))
    action_interest = sum((D(str(row.get("interest_due_inr", 0))) for row in action["loan_schedule"]), D("0"))
    additional_interest = max(D("0"), action_interest - base_interest)
    total_cost = D(str(action["action_cost_inr"]))
    incremental_non_interest_cost = max(D("0"), total_cost - additional_interest)
    future_debt_delta = D(str(action["debt_cycle"][-1]["total_debt_end_inr"])) - D(str(control["debt_cycle"][-1]["total_debt_end_inr"]))
    score = (gap_relief * D(str(weights["immediate_gap_relief_inr"]))
             - incremental_non_interest_cost * D(str(weights["incremental_cost_inr"]))
             - additional_interest * D(str(weights["additional_interest_inr"]))
             - future_debt_delta * D(str(weights["season3_debt_increase_inr"])))
    scored = {**option, "status": "evaluated", "metrics": {
        "immediate_gap_relief_inr": str(money(gap_relief)), "incremental_cost_inr": str(money(incremental_non_interest_cost)),
        "additional_interest_inr": str(money(additional_interest)), "season3_debt_increase_inr": str(money(future_debt_delta)),
        "objective_score_inr": str(money(score)), "baseline_due_date": control["due_date"],
        "action_due_dates": [row["date"].isoformat() if hasattr(row["date"], "isoformat") else row["date"] for row in action["loan_schedule"]],
        "baseline_exact_due_gap_inr": str(control["cash_gap_inr"]), "action_exact_due_gap_inr": str(action["cash_gap_inr"]),
        "formal_interest_due_inr": str(money(action_interest)),
        "season3_total_debt_inr": action["debt_cycle"][-1]["total_debt_end_inr"]},
        "evaluable": True, "successful": gap_relief > 0 and score > 0,
        "reasons": [*option["reasons"], "Ranked only when gap relief and declared weighted objective are both positive."]}
    return scored
