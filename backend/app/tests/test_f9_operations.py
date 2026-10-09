import os
import tempfile
import unittest
from decimal import Decimal as D

from app.db import (get_allocation_snapshot, get_warning_task, save_allocation_snapshot,
    save_scenario, transition_warning_task, save_comparison_bundle, get_scenario)
from app.schemas import InterventionEvaluationRequest, ScenarioRequest
from app.services.assessment import evaluate_scenario
from app.services.interventions import evaluate_action_candidates, score_action_option
from app.services.allocation import apply_allocated_candidate, freeze_from_saved_comparisons
from app.services.watchlist import page_watchlist
from app.services.allocation import stable_allocation_id, solve_allocation


def candidate(candidate_id, borrower, cost, benefit, tags=(), definition="immediate_due_gap_relief_inr", unit="INR_due_gap_relief"):
    return {"candidate_id": candidate_id, "borrower_id": borrower, "cost_inr": str(cost),
        "benefit_value": str(benefit), "benefit_definition": definition, "benefit_unit": unit,
        "coverage_tags": list(tags)}


class F9OperationsTests(unittest.TestCase):
    def test_exact_solver_matches_exhaustive_enumeration_with_borrower_limit(self):
        rows = [candidate("a1", "a", "2.25", "6"), candidate("a2", "a", "1", "5"),
                candidate("b1", "b", "2", "5"), candidate("c1", "c", "0", "1")]
        result = solve_allocation(rows, D("4.25"))
        # Exhaustive independent fixture: a1+b1+c1 costs 4.25 and yields 12.
        self.assertEqual(result["solver_status"], "optimal")
        self.assertTrue(result["optimality_proven"])
        self.assertEqual(result["objective_value"], "12")
        self.assertEqual({row["candidate_id"] for row in result["selected"]}, {"a1", "b1", "c1"})
        self.assertLessEqual(D(result["selected_cost_inr"]), D("4.25"))

    def test_zero_budget_zero_cost_exact_fit_fractional_and_tie_behavior(self):
        zero = solve_allocation([candidate("free", "a", "0", "2.5")], D("0"))
        self.assertEqual([row["candidate_id"] for row in zero["selected"]], ["free"])
        exact = solve_allocation([candidate("half", "a", "0.12", "1.5"), candidate("quarter", "b", "0.13", "1.5")], D("0.25"))
        self.assertEqual(exact["selected_cost_inr"], "0.25")
        tied = solve_allocation([candidate("z", "z", "1", "2"), candidate("a", "a", "1", "2")], D("1"))
        self.assertEqual(tied["selected"][0]["candidate_id"], "a")

    def test_ineligible_unknown_benefit_and_invalid_cost_excluded(self):
        rows = [candidate("good", "a", "1", "3"), candidate("unknown", "b", "1", "0", definition="unknown"),
                candidate("negative", "c", "-0.01", "5")]
        result = solve_allocation(rows, D("2"))
        self.assertEqual([row["candidate_id"] for row in result["selected"]], ["good"])
        self.assertEqual({row["candidate_id"] for row in result["excluded"]}, {"unknown", "negative"})

    def test_coverage_floor_infeasible_and_timeout_are_truthful(self):
        infeasible = solve_allocation([candidate("n", "a", "1", "3", ["district:N"])], D("1"),
            coverage_enabled=True, coverage_floors={"district:S": 1})
        self.assertEqual(infeasible["solver_status"], "infeasible")
        self.assertEqual(infeasible["selected"], [])
        rows = [candidate(f"c{i:02d}", f"b{i:02d}", "1", "1") for i in range(28)]
        timed = solve_allocation(rows, D("14"), timeout_ms=1)
        if timed["solver_status"].startswith("time_limit"):
            self.assertFalse(timed["optimality_proven"])
            self.assertTrue(timed["solver_status"] in {"time_limit_feasible", "time_limit_no_solution"})
            self.assertLessEqual(D(timed["selected_cost_inr"]), D("14"))
        else:
            self.assertEqual(timed["solver_status"], "optimal")

    def test_warning_task_is_idempotent_audited_and_persistent(self):
        previous = os.environ.get("DATABASE_URL")
        with tempfile.TemporaryDirectory(dir=os.path.dirname(__file__)) as folder:
            os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(folder, "f9.sqlite")
            try:
                warning = {"id": "REPEATED_SHORTFALL", "severity": "high", "season": 1,
                    "rule_version": "fixture-v1", "derivation_key": "f" * 64,
                    "evidence_record": {"assessment_id": "scenario-one", "rule": "REPEATED_SHORTFALL",
                        "version": "fixture-v1", "season_ids": ["S1"], "assumption_tags": ["synthetic"]}}
                result = {"scenario_id": "scenario-one", "debt_warnings": [warning]}
                save_scenario("scenario-one", "B-1", "hash", {}, result)
                save_scenario("scenario-one", "B-1", "hash", {}, result)
                task = get_warning_task("f" * 64)
                self.assertEqual(len(task["history"]), 1)
                assigned = transition_warning_task("f" * 64, operation="assign", actor="A", reason="Route to staff", assigned_to="Officer 1")
                ack = transition_warning_task("f" * 64, operation="acknowledge", actor="B", reason="Seen")
                resolved = transition_warning_task("f" * 64, operation="resolve", actor="B", reason="Reviewed")
                self.assertEqual(resolved["status"], "resolved")
                self.assertEqual(resolved["assigned_to"], "Officer 1")
                with self.assertRaises(ValueError):
                    transition_warning_task("f" * 64, operation="acknowledge", actor="B", reason="Invalid repeated ack")
                reopened = transition_warning_task("f" * 64, operation="reopen", actor="C", reason="New evidence")
                self.assertEqual(reopened["status"], "reopened")
                self.assertEqual(len(reopened["history"]), 5)
                replacement = {**warning, "derivation_key": "g" * 64,
                    "evidence_record": {**warning["evidence_record"], "assessment_id": "scenario-two"}}
                save_scenario("scenario-two", "B-1", "hash-2", {}, {"scenario_id": "scenario-two", "debt_warnings": [replacement]})
                superseded = transition_warning_task("f" * 64, operation="supersede", actor="C",
                    reason="Newer evidence replaces this warning", superseded_by="g" * 64)
                self.assertEqual(superseded["status"], "superseded")
                self.assertEqual(superseded["history"][-1]["superseded_by"], "g" * 64)
                self.assertEqual(len(get_warning_task("f" * 64)["history"]), 6)
            finally:
                if previous is None:
                    os.environ.pop("DATABASE_URL", None)
                else:
                    os.environ["DATABASE_URL"] = previous

    def test_allocation_snapshot_idempotency(self):
        previous = os.environ.get("DATABASE_URL")
        with tempfile.TemporaryDirectory(dir=os.path.dirname(__file__)) as folder:
            os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(folder, "alloc.sqlite")
            try:
                inp = {"branch_id": "N", "budget_inr": "0.25"}
                result = {"solver_status": "optimal", "selected_cost_inr": "0.25"}
                allocation_id = stable_allocation_id(inp, result)
                save_allocation_snapshot(allocation_id, "N", inp, result)
                save_allocation_snapshot(allocation_id, "N", inp, {"solver_status": "changed"})
                self.assertEqual(get_allocation_snapshot(allocation_id)["result_snapshot"], result)
            finally:
                if previous is None:
                    os.environ.pop("DATABASE_URL", None)
                else:
                    os.environ["DATABASE_URL"] = previous

    def test_watchlist_filters_pagination_and_kpis_match_saved_rows(self):
        records = [
            {"derivation_key": "a", "branch_id": "North", "severity": "high", "task": {"status": "open"}},
            {"derivation_key": "b", "branch_id": "North", "severity": "high", "task": {"status": "resolved"}},
            {"derivation_key": "c", "branch_id": "South", "severity": "moderate", "task": {"status": "assigned"}},
        ]
        page = page_watchlist(records, branch_id="North", status=None, severity="high", page=1, page_size=1)
        self.assertEqual(page["total"], 2)
        self.assertEqual(page["total_pages"], 2)
        self.assertEqual(page["kpis"], {"open": 1, "assigned": 0, "acknowledged": 0,
            "resolved": 1, "reopened": 0, "superseded": 0})
        self.assertEqual(page["items"][0]["derivation_key"], "a")
        second = page_watchlist(records, branch_id="North", status=None, severity="high", page=2, page_size=1)
        self.assertEqual(second["items"][0]["derivation_key"], "b")

    def test_allocator_freezes_saved_assistance_and_rejects_changed_cost(self):
        previous = os.environ.get("DATABASE_URL")
        with tempfile.TemporaryDirectory(dir=os.path.dirname(__file__)) as folder:
            os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(folder, "freeze.sqlite")
            try:
                req = InterventionEvaluationRequest(as_of="2026-10-09", overrides={"heatwave_days": 8,
                    "market_price_change_pct": -30}, action_inputs={"hypothetical_assistance": {
                    "amount_inr": 3000, "budget_inr": 5000, "effective_date": "2026-10-20"}})
                base, options = evaluate_action_candidates(req)
                option = next(row for row in options if row["candidate_id"] == "hypothetical_assistance")
                base_req = ScenarioRequest.model_validate(req.model_dump(exclude={"action_inputs", "action_id", "action_parameters"}))
                candidate_req = base_req.model_copy(update={"action_parameters": option["action_parameters"]})
                result = evaluate_scenario(candidate_req)
                result = save_scenario(result["scenario_id"], result["borrower_id"], result["input_hash"],
                    candidate_req.model_dump(mode="json"), result)
                option = score_action_option(option, base, result)
                option["result_ref"] = {"scenario_id": result["scenario_id"]}
                bundle = save_comparison_bundle({"borrower_id": result["borrower_id"],
                    "comparison_context_hash": result["comparison_context_hash"], "policy_version": option["policy_version"],
                    "baseline_ref": {"scenario_id": result["scenario_id"]}, "stress_ref": {"scenario_id": result["scenario_id"]},
                    "candidate_refs": [], "action_result_refs": {}, "action_options": [option]})
                frozen_candidate = {"candidate_id": "one-aid", "borrower_id": result["borrower_id"],
                    "branch_id": result["frozen_context"]["borrower"]["branch"], "scenario_id": result["scenario_id"],
                    "comparison_id": bundle["bundle_id"], "action_candidate_id": option["candidate_id"],
                    "scenario_context_hash": result["comparison_context_hash"], "policy_version": option["policy_version"],
                    "engine_version": result["engine_version"], "cost_inr": "3000.00", "cost_date": "2026-10-20",
                    "benefit_value": option["metrics"]["immediate_gap_relief_inr"],
                    "benefit_definition": "immediate_due_gap_relief_inr", "benefit_unit": "INR_due_gap_relief",
                    "coverage_tags": ["district:Nashik"]}
                payload = {"branch_id": frozen_candidate["branch_id"], "candidates": [frozen_candidate]}
                rows, excluded = freeze_from_saved_comparisons(payload)
                self.assertEqual(len(rows), 1, excluded)
                self.assertEqual(excluded, [], excluded)
                before = get_scenario(result["scenario_id"])
                allocated = apply_allocated_candidate(rows[0], "AL-test-allocation-0001")
                self.assertNotEqual(allocated["scenario_id"], result["scenario_id"])
                self.assertEqual(allocated["allocation_application"]["program_cost_inr"], "3000.00")
                self.assertEqual(allocated["allocation_application"]["program_cost_date"], "2026-10-20")
                self.assertEqual(D(str(allocated["stress_with_action"]["action_cost_inr"])), D("3000.00"))
                after = get_scenario(result["scenario_id"])
                self.assertEqual(after["result_hash"], before["result_hash"])
                self.assertNotIn("allocation_application", after)
                changed = {**frozen_candidate, "cost_inr": "2999.99"}
                _, rejected = freeze_from_saved_comparisons({**payload, "candidates": [changed]})
                self.assertIn("declared program cost differs", rejected[0]["reason"])
            finally:
                if previous is None:
                    os.environ.pop("DATABASE_URL", None)
                else:
                    os.environ["DATABASE_URL"] = previous


if __name__ == "__main__":
    unittest.main()
