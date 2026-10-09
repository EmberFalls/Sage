import os
import tempfile
import unittest
from datetime import date
from decimal import Decimal as D

from app.db import (create_intervention_proposal, get_intervention_proposal,
                    transition_intervention_proposal)
from app.schemas import InterventionEvaluationRequest, ScenarioRequest
from app.services.assessment import evaluate_scenario
from app.services.interventions import (CATALOG, POLICY, _option,
    evaluate_action_candidates, score_action_option)
from app.services.assessment import WARNING_CONFIG


class F8InterventionTests(unittest.TestCase):
    def setUp(self):
        self.request = InterventionEvaluationRequest(
            borrower_id="B-DEMO-001", as_of=date(2026, 10, 9),
            overrides={"rainfall_change_pct": -10, "heatwave_days": 4,
                       "heatwave_growth_stage": "flowering", "market_price_change_pct": -20})
        self.base, self.options = evaluate_action_candidates(self.request)
        self.by_id = {row["candidate_id"]: row for row in self.options}

    def evaluate_option(self, option):
        params = option["action_parameters"]
        req = ScenarioRequest.model_validate(self.request.model_dump(
            exclude={"action_inputs", "action_id", "action_parameters"}) |
            {"action_id": params.get("schedule_action", "none"), "action_parameters": params})
        return evaluate_scenario(req)

    def test_catalog_is_versioned_and_unsupported_crop_options_are_visible(self):
        self.assertFalse(POLICY["operational_policy_verified"])
        self.assertEqual(self.by_id["crop_change"]["status"], "unsupported")
        self.assertEqual(self.by_id["sowing_timing"]["status"], "unsupported")
        self.assertEqual(self.by_id["crop_change"]["sowing_status"], "already_sown")
        self.assertIn("region", " ".join(self.by_id["crop_change"]["reasons"]).lower())

    def test_rescheduling_moves_due_date_and_exposes_interest_and_later_debt(self):
        option = self.by_id["reschedule_30d"]
        result = self.evaluate_option(option)
        scored = score_action_option(option, self.base, result)
        metrics = scored["metrics"]
        self.assertEqual(metrics["baseline_due_date"], "2026-11-05")
        self.assertEqual(metrics["action_due_dates"], ["2026-12-05"])
        self.assertGreater(D(metrics["additional_interest_inr"]), 0)
        self.assertGreater(D(metrics["additional_interest_inr"]), 0,
                           "the moved due date creates a later interest burden")
        self.assertEqual(result["comparison_context_hash"], self.base["comparison_context_hash"])

    def test_split_installments_reconcile_principal_interest_and_fees(self):
        result = self.evaluate_option(self.by_id["split_payment"])
        rows = result["stress_with_action"]["loan_schedule"]
        self.assertEqual([row["date"].isoformat() if hasattr(row["date"], "isoformat") else row["date"] for row in rows],
                         ["2026-11-05", "2026-12-20"])
        self.assertEqual(sum((D(str(row["principal_due_inr"])) for row in rows), D("0")), D("120000.00"))
        for row in rows:
            self.assertEqual(D(str(row["amount_inr"])), D(str(row["principal_due_inr"])) +
                D(str(row["interest_due_inr"])) + D(str(row["fee_due_inr"])))
        self.assertEqual(D(str(result["stress_with_action"]["formal_balance_end_inr"])), D("0.00"))

    def test_irrigation_requires_water_and_timing(self):
        baseline = evaluate_scenario(ScenarioRequest.model_validate(
            self.request.model_dump(exclude={"action_inputs", "action_id", "action_parameters"})))
        eligible_input = {"irrigation_support": {"water_access_confirmed": True,
            "effective_date": "2026-10-20", "irrigation_fraction_after": 0.8, "cost_inr": 1000}}
        option = _option("irrigation_support", ["irrigation_support"], eligible_input,
                         ScenarioRequest.model_validate(self.request.model_dump(exclude={"action_inputs", "action_id", "action_parameters"})), baseline)
        self.assertFalse(option["eligible"], "synthetic shock starts before 2026-10-20")
        eligible_input["irrigation_support"].update({"effective_date": "2026-10-09", "water_access_confirmed": False})
        option = _option("irrigation_support", ["irrigation_support"], eligible_input,
                         ScenarioRequest.model_validate(self.request.model_dump(exclude={"action_inputs", "action_id", "action_parameters"})), baseline)
        self.assertFalse(option["eligible"])
        self.assertTrue(any("Water access" in reason for reason in option["reasons"]))

    def test_assistance_budget_date_and_insurance_cutoff_gate(self):
        base_req = ScenarioRequest.model_validate(self.request.model_dump(exclude={"action_inputs", "action_id", "action_parameters"}))
        assistance = _option("hypothetical_assistance", ["hypothetical_assistance"],
            {"hypothetical_assistance": {"amount_inr": 5000, "budget_inr": 5000, "effective_date": "2026-10-20"}}, base_req, self.base)
        self.assertTrue(assistance["eligible"])
        self.assertEqual(len(assistance["action_parameters"]["cash_events"]), 1)
        no_budget = _option("hypothetical_assistance", ["hypothetical_assistance"],
            {"hypothetical_assistance": {"amount_inr": 5000, "budget_inr": 4999, "effective_date": "2026-10-20"}}, base_req, self.base)
        self.assertFalse(no_budget["eligible"])
        insured = _option("insurance_scenario", ["insurance_scenario"], {"insurance_scenario": {
            "enrolled": True, "enrollment_date": "2026-10-20", "trigger_met": True,
            "payout_date": "2026-11-01", "payout_inr": 10000, "premium_inr": 500}}, base_req, self.base)
        self.assertFalse(insured["eligible"])
        self.assertEqual(insured["insurance_terms"]["modeled_payout_inr"], "0.00")
        self.assertTrue(any("cutoff" in reason.lower() for reason in insured["reasons"]))
        split_insured = _option("split_payment+insurance_scenario", ["split_payment", "insurance_scenario"],
            {"insurance_scenario": {"enrolled": True, "enrollment_date": "2026-10-20",
             "trigger_met": True, "payout_date": "2026-11-01", "payout_inr": 10000, "premium_inr": 0}}, base_req, self.base)
        self.assertEqual([row["repayment_date"] for row in split_insured["insurance_terms"]["repayment_cutoffs"]],
                         ["2026-11-05", "2026-12-20"])
        self.assertFalse(split_insured["eligible"], "later installment does not erase the earlier cutoff")
        self.assertFalse(self.by_id["insurance_scenario"]["eligible"])

    def test_outreach_has_no_automatic_relief_and_pair_conflict_is_rejected(self):
        outreach = self.by_id["outreach"]
        self.assertFalse(outreach["numeric_effects_declared"])
        scored = score_action_option(outreach, self.base, self.evaluate_option(outreach))
        self.assertEqual(scored["metrics"]["immediate_gap_relief_inr"], "0.00")
        self.assertEqual(self.by_id["reschedule_30d+split_payment"]["status"], "incompatible")

    def test_action_specific_future_burden_warning_is_derived_by_shared_assessment(self):
        base_request = ScenarioRequest.model_validate(self.request.model_dump(
            exclude={"action_inputs", "action_id", "action_parameters"}))
        parameters = {"candidate_id": "hypothetical_assistance", "schedule_action": "none",
            "cash_events": [{"kind": "hypothetical_assistance", "date": "2026-10-20",
                             "amount_inr": "60000.00", "source_tag": "assumed"}],
            "program_cost_inr": "60000.00", "source_tags": ["assumed"]}
        action_request = base_request.model_copy(update={"action_parameters": parameters})
        result = evaluate_scenario(action_request)
        warnings = result["debt_warnings"]
        self.assertIn("ACTION_SHIFTS_BURDEN", [row["id"] for row in warnings])
        warning = next(row for row in warnings if row["id"] == "ACTION_SHIFTS_BURDEN")
        self.assertEqual(warning["rule_version"], WARNING_CONFIG["version"])
        self.assertIn("assumed", warning["evidence_record"]["assumption_tags"])

    def test_no_gap_means_no_successful_ranked_candidate(self):
        req = InterventionEvaluationRequest(overrides={"rainfall_change_pct": 0, "heatwave_days": 0,
            "market_price_change_pct": 0, "irrigation_fraction": None})
        base, options = evaluate_action_candidates(req)
        self.assertEqual(D(str(base["stress"]["cash_gap_inr"])), D("0.00"))
        self.assertFalse(any(option.get("successful") for option in options))

    def test_proposal_review_history_and_invalid_transitions(self):
        previous = os.environ.get("DATABASE_URL")
        with tempfile.TemporaryDirectory(dir=os.path.dirname(__file__)) as folder:
            os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(folder, "f8.sqlite")
            try:
                proposal = create_intervention_proposal(comparison_id="cmp-1", candidate_id="reschedule_30d",
                    assessment_id="assessment-1", scenario_id="scenario-1", actor="reviewer", reason="Assess schedule option")
                rules = POLICY["review_transitions"]
                reviewed = transition_intervention_proposal(proposal["proposal_id"], status="under_review",
                    actor="reviewer-2", reason="Check terms", allowed_transitions=rules)
                self.assertEqual(len(reviewed["review_history"]), 2)
                self.assertEqual(reviewed["review_history"][-1]["assessment_id"], "assessment-1")
                with self.assertRaises(ValueError):
                    transition_intervention_proposal(proposal["proposal_id"], status="proposed", actor="reviewer",
                        reason="Invalid reverse", allowed_transitions=rules)
                approved = transition_intervention_proposal(proposal["proposal_id"], status="approved_in_demo",
                    actor="reviewer-3", reason="Apply in simulation", allowed_transitions=rules,
                    applied_simulation={"scenario_id": "new-sim", "existing_loan_events_mutated": False})
                self.assertEqual(approved["applied_simulation"]["scenario_id"], "new-sim")
                self.assertEqual(get_intervention_proposal(proposal["proposal_id"])["status"], "approved_in_demo")
            finally:
                if previous is None:
                    os.environ.pop("DATABASE_URL", None)
                else:
                    os.environ["DATABASE_URL"] = previous


if __name__ == "__main__":
    unittest.main()
