"""Bounded exact branch allocation for frozen, illustrative support candidates."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
import time
from typing import Any

from app.db import get_comparison_bundle, get_scenario, save_scenario
from app.schemas import ScenarioRequest
from app.services.assessment import evaluate_scenario

D = Decimal
SOLVER_VERSION = "branch-allocation-enumeration-v1"
OBJECTIVE = {"name": "maximize_total_immediate_due_gap_relief",
             "unit": "INR_due_gap_relief", "tie_break": "lexicographically_smallest_selected_candidate_ids"}
BENEFIT_DEFINITION = "immediate_due_gap_relief_inr"


def freeze_from_saved_comparisons(request: dict) -> tuple[list[dict], list[dict]]:
    """Resolve client references into immutable eligible candidate facts from saved evidence."""
    frozen, excluded = [], []
    seen = set()
    for submitted in request["candidates"]:
        item = dict(submitted)
        cid = item.get("candidate_id", "")
        if cid in seen:
            excluded.append({**item, "reason": "duplicate_candidate_id"})
            continue
        seen.add(cid)
        try:
            bundle = get_comparison_bundle(item["comparison_id"])
            if bundle is None:
                raise ValueError("saved comparison not found")
            if bundle.get("comparison_context_hash") != item.get("scenario_context_hash"):
                raise ValueError("comparison context reference mismatch")
            if bundle.get("policy_version") != item.get("policy_version", bundle.get("policy_version")):
                raise ValueError("policy version reference mismatch")
            option = next((row for row in bundle.get("action_options", [])
                           if row.get("candidate_id") == item["action_candidate_id"]), None)
            if option is None or not option.get("eligible") or not option.get("evaluable"):
                raise ValueError("saved action is unsupported or ineligible")
            result_ref = option.get("result_ref", {}).get("scenario_id")
            if result_ref != item["scenario_id"]:
                raise ValueError("scenario reference does not match the frozen candidate")
            result = get_scenario(result_ref)
            if result is None or result.get("borrower_id") != item["borrower_id"]:
                raise ValueError("saved candidate assessment is unavailable or borrower mismatched")
            if result.get("comparison_context_hash") != item["scenario_context_hash"]:
                raise ValueError("saved assessment context reference mismatch")
            if result.get("engine_version") != item["engine_version"]:
                raise ValueError("saved assessment engine version reference mismatch")
            borrower = result.get("frozen_context", {}).get("borrower", {})
            if borrower.get("branch") != item["branch_id"] or item["branch_id"] != request["branch_id"]:
                raise ValueError("candidate branch does not match the saved borrower and allocation branch")
            params = result.get("scenario_request", {}).get("action_parameters", {})
            aid_events = [event for event in params.get("cash_events", []) if event.get("kind") == "hypothetical_assistance"]
            if item["action_candidate_id"] != "hypothetical_assistance" and not item["action_candidate_id"].endswith("+hypothetical_assistance"):
                raise ValueError("only hypothetical assistance candidates can enter this support allocator")
            if not aid_events:
                raise ValueError("saved candidate has no dated hypothetical assistance event")
            exact_cost = sum((D(str(event["amount_inr"])) for event in aid_events), D("0"))
            event_dates = sorted({str(event["date"]) for event in aid_events})
            if len(event_dates) != 1 or str(item.get("cost_date")) != event_dates[0]:
                raise ValueError("program cost date differs from the saved dated assistance event")
            declared_program_cost = D(str(params.get("program_cost_inr", "0")))
            if exact_cost != declared_program_cost or D(str(item["cost_inr"])) != exact_cost:
                raise ValueError("declared program cost differs from the saved dated assistance amount")
            metrics = option.get("metrics")
            if not metrics or metrics.get("immediate_gap_relief_inr") is None:
                raise ValueError("candidate has no measured benefit")
            benefit = D(str(metrics["immediate_gap_relief_inr"]))
            if item.get("benefit_definition") != BENEFIT_DEFINITION or item.get("benefit_unit") != OBJECTIVE["unit"]:
                raise ValueError("benefit definition or objective unit is unknown")
            if item.get("benefit_value") is None or D(str(item["benefit_value"])) != benefit:
                raise ValueError("benefit value differs from the frozen assessment result")
            if exact_cost < 0 or exact_cost > D("100000000") or benefit < 0:
                raise ValueError("cost or benefit is outside supported bounds")
            frozen.append({**item, "cost_inr": str(exact_cost), "benefit_value": str(benefit),
                "scenario_context_hash": result["comparison_context_hash"], "engine_version": result["engine_version"],
                "policy_version": bundle.get("policy_version"), "cost_date": event_dates[0], "program_cost_events": aid_events,
                "scenario_request": result["scenario_request"], "coverage_tags": list(item.get("coverage_tags", [])),
                "action_assumption_tags": params.get("source_tags", ["assumed"]), "scenario_result_hash": result.get("result_hash")})
        except (KeyError, ValueError, InvalidOperation) as exc:
            excluded.append({**item, "reason": str(exc)})
    return frozen, excluded


def solve_allocation(candidates: list[dict], budget: Decimal, *, coverage_enabled: bool = False,
                     coverage_floors: dict[str, int] | None = None, timeout_ms: int = 500,
                     excluded: list[dict] | None = None) -> dict:
    floors = coverage_floors or {}
    budget = D(str(budget))
    good, bad = [], list(excluded or [])
    seen = set()
    for row in candidates:
        try:
            cost, benefit = D(str(row["cost_inr"])), D(str(row["benefit_value"]))
            if cost < 0 or benefit < 0:
                raise ValueError("negative cost or benefit")
            if row.get("benefit_definition") != BENEFIT_DEFINITION or row.get("benefit_unit") != OBJECTIVE["unit"]:
                raise ValueError("unknown benefit definition or unit")
            if not row.get("borrower_id") or not row.get("candidate_id"):
                raise ValueError("borrower/candidate identifier missing")
            if row["candidate_id"] in seen:
                raise ValueError("duplicate candidate identifier")
            seen.add(row["candidate_id"])
            good.append({**row, "cost_inr": str(cost), "benefit_value": str(benefit)})
        except (KeyError, InvalidOperation, ValueError) as exc:
            bad.append({**row, "reason": f"invalid_candidate: {exc}"})
    if budget < 0:
        raise ValueError("budget must be non-negative")
    if not coverage_enabled and floors:
        raise ValueError("coverage floors require explicit enablement")
    if any(v < 0 for v in floors.values()):
        raise ValueError("coverage floors must be non-negative")
    groups: dict[str, list[dict]] = {}
    for row in good:
        groups.setdefault(row["borrower_id"], []).append(row)
    borrowers = sorted(groups)
    for rows in groups.values():
        rows.sort(key=lambda r: r["candidate_id"])

    started = time.monotonic()
    deadline = started + timeout_ms / 1000
    node_limit = 250000
    nodes = 0
    timed_out = False
    best_value: Decimal | None = None
    best_rows: list[dict] = []
    best_ids: tuple[str, ...] | None = None
    # Suffix bounds deliberately overestimate value by ignoring shared budget and coverage.
    suffix = [D("0")] * (len(borrowers) + 1)
    for index in range(len(borrowers) - 1, -1, -1):
        maximum = max([D(str(row["benefit_value"])) for row in groups[borrowers[index]]] + [D("0")])
        suffix[index] = suffix[index + 1] + maximum

    def visit(index: int, cost: Decimal, value: Decimal, chosen: list[dict], counts: dict[str, int]):
        nonlocal nodes, timed_out, best_value, best_rows, best_ids
        nodes += 1
        if nodes > node_limit or time.monotonic() >= deadline:
            timed_out = True
            return
        if cost > budget:
            return
        if best_value is not None and value + suffix[index] < best_value:
            return
        if coverage_enabled and any(counts.get(tag, 0) + sum(any(tag in row.get("coverage_tags", []) for row in groups[b])
                for b in borrowers[index:]) < floor for tag, floor in floors.items()):
            return
        if index == len(borrowers):
            if coverage_enabled and any(counts.get(tag, 0) < floor for tag, floor in floors.items()):
                return
            ids = tuple(sorted(row["candidate_id"] for row in chosen))
            if best_value is None or value > best_value or (value == best_value and (best_ids is None or ids < best_ids)):
                best_value, best_rows, best_ids = value, list(chosen), ids
            return
        borrower_id = borrowers[index]
        # None is a valid option; candidate order plus stable tie break gives deterministic results.
        visit(index + 1, cost, value, chosen, counts)
        if timed_out:
            return
        for row in groups[borrower_id]:
            next_cost = cost + D(str(row["cost_inr"]))
            if next_cost > budget:
                continue
            next_counts = dict(counts)
            for tag in set(row.get("coverage_tags", [])):
                next_counts[tag] = next_counts.get(tag, 0) + 1
            visit(index + 1, next_cost, value + D(str(row["benefit_value"])), [*chosen, row], next_counts)
            if timed_out:
                return

    visit(0, D("0"), D("0"), [], {})
    if best_value is None:
        status = "time_limit_no_solution" if timed_out else "infeasible"
        selected = []
        objective = None
        used = D("0")
        gap = None
    else:
        status = "time_limit_feasible" if timed_out else "optimal"
        selected = best_rows
        objective = best_value
        used = sum((D(str(row["cost_inr"])) for row in selected), D("0"))
        upper_bound = max(best_value, suffix[0]) if timed_out else best_value
        gap = (str((upper_bound - best_value) / max(abs(upper_bound), D("1"))) if timed_out else "0")
    selected_ids = {row["candidate_id"] for row in selected}
    unselected = [{**row, "reason": "not_selected_by_budget_objective"} for row in good if row["candidate_id"] not in selected_ids]
    return {"solver": SOLVER_VERSION, "solver_status": status, "optimality_proven": status == "optimal",
        "timeout_ms": timeout_ms, "elapsed_ms": round((time.monotonic() - started) * 1000, 3),
        "nodes_explored": nodes, "optimality_gap": gap, "objective": OBJECTIVE,
        "objective_value": str(objective) if objective is not None else None,
        "budget_inr": str(budget), "selected_cost_inr": str(used), "remaining_budget_inr": str(budget - used),
        "coverage_enabled": coverage_enabled, "coverage_floors": floors,
        "selected": selected, "unselected": unselected, "excluded": bad}


def stable_allocation_id(input_snapshot: dict, result_snapshot: dict) -> str:
    stable_result = {key: result_snapshot.get(key) for key in
        ("solver", "solver_status", "optimality_proven", "optimality_gap", "objective_value",
         "budget_inr", "selected_cost_inr", "remaining_budget_inr", "coverage_enabled", "coverage_floors")}
    stable_result["selected_candidate_ids"] = sorted(row.get("candidate_id") for row in result_snapshot.get("selected", []))
    raw = json.dumps({"input": input_snapshot, "result": stable_result}, sort_keys=True, separators=(",", ":"), default=str)
    return "AL-" + sha256(raw.encode()).hexdigest()[:24].upper()


def apply_allocated_candidate(candidate: dict, allocation_id: str) -> dict:
    """Create and persist a new hypothetical outcome; never edits the source result or loan events."""
    request = ScenarioRequest.model_validate(candidate["scenario_request"])
    parameters = {**request.action_parameters, "allocation_id": allocation_id,
        "allocation_candidate_id": candidate["candidate_id"],
        "allocation_program_cost_inr": candidate["cost_inr"]}
    allocated_request = request.model_copy(update={"action_parameters": parameters})
    result = evaluate_scenario(allocated_request)
    result["allocation_application"] = {"allocation_id": allocation_id,
        "candidate_id": candidate["candidate_id"], "program_cost_inr": candidate["cost_inr"],
        "program_cost_date": candidate["cost_date"], "scope": "new_hypothetical_scenario_only",
        "original_scenario_preserved": True, "existing_loan_events_mutated": False,
        "external_message_sent": False}
    return save_scenario(result["scenario_id"], result["borrower_id"], result["input_hash"],
        allocated_request.model_dump(mode="json"), result)
