import unittest
import os
import tempfile
from datetime import date
from decimal import Decimal as D, ROUND_HALF_UP

from app.services import assessment
from app.services.assessment import build_dated_ledger, derive_debt_warnings, evaluate_scenario
from app.schemas import ScenarioRequest
from app.services.fixtures import BORROWERS
from app.db import list_warning_evidence, save_scenario


def cycle(gaps=(D("0"), D("0"), D("0")), informal=(D("0"), D("0"), D("0")),
          debts=(D("0"), D("0"), D("0")), openings=(D("0"), D("0"), D("0")), costs=None):
    costs = costs or (D("0"), D("0"), D("0"))
    return [{"season": i + 1, "season_id": f"S{i+1}-202{6+i}", "cash_gap_inr": gaps[i],
             "informal_balance_end_inr": informal[i], "opening_total_debt_inr": openings[i],
             "total_debt_end_inr": debts[i], "unmet_due_inr": D("0"), "formal_paid_inr": D("100"),
             "action_cost_inr": costs[i], "assumption_tags": ["synthetic_fixture"],
             "bridge_events": []} for i in range(3)]


class F7DebtTests(unittest.TestCase):
    def warnings(self, rows, payments=None, stress_gap=D("0"), action=None):
        return derive_debt_warnings(rows, {"payments": payments or [], "cash_gap_inr": stress_gap,
            "scenario_id": "fixture-assessment"}, action)

    def test_three_explicit_seasons_reconcile_formal_and_informal_debt(self):
        result = evaluate_scenario(ScenarioRequest(overrides={"heatwave_days": 14,
            "market_price_change_pct": -70, "assumed_informal_bridge_inr": 150000}))
        self.assertEqual(len(result["debt_cycle"]), 3)
        self.assertEqual([r["season_start_date"] for r in result["debt_cycle"]],
                         ["2026-06-20", "2027-06-20", "2028-06-20"])
        for row in result["debt_cycle"]:
            self.assertEqual(D(row["debt_conservation_delta_inr"]), D("0.00"))
            self.assertEqual(D(row["total_debt_end_inr"]),
                D(row["formal_balance_end_inr"]) + D(row["informal_balance_end_inr"]))
        self.assertEqual(result["debt_worlds"]["bridge"]["seasons"][0]["opening_cash_inr"],
                         result["debt_worlds"]["no_bridge"]["seasons"][0]["opening_cash_inr"])
        self.assertEqual(result["debt_worlds"]["comparison_context_hash"], result["comparison_context_hash"])
        self.assertEqual(result["debt_worlds"]["bridge"]["seasons"][0]["shock_path"],
                         "same_frozen_shock_repeated_each_season")
        prior_due = None
        prior_end = None
        new_loan_days = (date.fromisoformat(result["stress"]["due_date"]) -
                         date.fromisoformat(result["frozen_context"]["borrower"]["disbursed_at"])).days
        for row in result["debt_cycle"]:
            current_interest = (D(row["new_formal_principal_inr"]) * D("0.12") * D(new_loan_days) / D("365")).quantize(D("0.01"), rounding=ROUND_HALF_UP)
            carried_days = (date.fromisoformat(row["payments"][0]["date"]) - prior_due).days if prior_due else 365
            carried_interest = (D(row["opening_formal_principal_inr"]) * D("0.12") * D(carried_days) / D("365")).quantize(D("0.01"), rounding=ROUND_HALF_UP)
            self.assertEqual(D(row["formal_interest_accrued_inr"]), current_interest + carried_interest)
            actual_days = (date.fromisoformat(row["season_end_date"]) - prior_end).days if prior_end else 365
            informal_interest = D(row["opening_informal_principal_inr"]) * D("0.18") * D(actual_days) / D("365")
            for event in row["bridge_events"]:
                informal_interest += D(event["amount_inr"]) * D("0.18") * D((date.fromisoformat(row["season_end_date"]) - date.fromisoformat(event["effective_date"])).days) / D("365")
            informal_interest = informal_interest.quantize(D("0.01"), rounding=ROUND_HALF_UP)
            self.assertEqual(D(row["informal_interest_accrued_inr"]), informal_interest)
            prior_due = date.fromisoformat(row["payments"][-1]["date"])
            prior_end = date.fromisoformat(row["season_end_date"])
        self.assertEqual(result["stress"]["formal_repayment_status"], "simulated_due_satisfied")
        self.assertGreater(D(result["stress"]["informal_balance_end_inr"]), D("0"))
        self.assertNotEqual(result["stress"]["formal_repayment_status"], result["stress"]["modeled_sustainability_status"])

    def test_zero_partial_insufficient_bridge_no_income_and_payoff(self):
        b = dict(BORROWERS["B-DEMO-001"])
        b.update(initial_cash_inr=D("0"), input_cost_inr=D("100"), living_cost_inr=D("0"),
                 loan_principal_inr=D("100"), annual_rate=D("0"), disbursed_at=date(2026, 1, 1),
                 sowing_date=date(2026, 1, 1), due_at=date(2026, 1, 10))
        due = [{"date": date(2026, 1, 10), "amount_inr": D("100"),
                "principal_due_inr": D("100"), "interest_due_inr": D("0"), "fee_due_inr": D("0")}]
        zero = build_dated_ledger(b, D("0"), date(2026, 1, 20), due, D("0"))
        partial = build_dated_ledger(b, D("0"), date(2026, 1, 20), due, D("40"))
        insufficient = build_dated_ledger(b, D("0"), date(2026, 1, 20), due, D("80"))
        sufficient = build_dated_ledger(b, D("0"), date(2026, 1, 20), due, D("100"))
        payoff = build_dated_ledger(b, D("100"), date(2026, 1, 5), due, D("0"))
        self.assertEqual(zero["bridge_draw_inr"], D("0.00"))
        self.assertEqual(zero["formal_balance_end_inr"], D("100.00"))
        self.assertEqual(partial["bridge_draw_inr"], D("40.00"))
        self.assertEqual(partial["formal_balance_end_inr"], D("60.00"))
        self.assertEqual(insufficient["bridge_draw_inr"], D("80.00"))
        self.assertEqual(insufficient["formal_balance_end_inr"], D("20.00"))
        self.assertEqual(sufficient["bridge_draw_inr"], D("100.00"))
        self.assertEqual(sufficient["formal_balance_end_inr"], D("0.00"))
        self.assertEqual(payoff["formal_balance_end_inr"], D("0.00"))
        self.assertEqual(payoff["informal_balance_end_inr"], D("0.00"))

    def test_warning_rules_have_trigger_and_near_threshold_negative_cases(self):
        threshold = D(assessment.WARNING_CONFIG["materiality_inr"])
        pairs = [
            ("BRIDGE_USED_FOR_FORMAL_DUE", self.warnings(cycle(), [{"informal_draw_inr": D("1"),
                 "formal_paid_inr": D("1"), "cash_gap_inr": D("1")}]), self.warnings(cycle(),
                 [{"informal_draw_inr": D("0"), "formal_paid_inr": D("1"), "cash_gap_inr": D("1")} ])),
            ("REPEATED_SHORTFALL", self.warnings(cycle((threshold, threshold, D("0")))),
                 self.warnings(cycle((threshold - D("0.01"), D("0"), D("0"))))),
            ("INFORMAL_DEBT_GROWING", self.warnings(cycle(informal=(D("0"), threshold, threshold))),
                 self.warnings(cycle(informal=(D("0"), threshold - D("0.01"), threshold - D("0.01"))))),
            ("FORMAL_PAID_TOTAL_DEBT_RISES", self.warnings(cycle(debts=(threshold + D("0.01"), D("0"), D("0")),
                 openings=(D("0"), D("0"), D("0"))), [{"unmet_due_inr": D("0")}]),
                 self.warnings(cycle(debts=(threshold - D("0.01"), D("0"), D("0")),
                 openings=(D("0"), D("0"), D("0"))), [{"unmet_due_inr": D("0")} ])),
            ("ACTION_SHIFTS_BURDEN", self.warnings(cycle(), stress_gap=D("100"), action={"cash_gap_inr": D("0"),
                 "debt_cycle": cycle(costs=(threshold, D("0"), D("0")))}),
                 self.warnings(cycle(), stress_gap=D("100"), action={"cash_gap_inr": D("0"),
                 "debt_cycle": cycle(costs=(threshold - D("0.01"), D("0"), D("0")))})),
        ]
        for rule, positive, negative in pairs:
            with self.subTest(rule=rule):
                self.assertIn(rule, [w["id"] for w in positive])
                self.assertNotIn(rule, [w["id"] for w in negative])

    def test_warning_derivation_is_idempotent_and_versioned(self):
        rows = cycle((D("1000"), D("1000"), D("0")))
        original = self.warnings(rows)
        repeated = self.warnings(rows)
        original_key = next(w["derivation_key"] for w in original if w["id"] == "REPEATED_SHORTFALL")
        repeated_key = next(w["derivation_key"] for w in repeated if w["id"] == "REPEATED_SHORTFALL")
        self.assertEqual(original_key, repeated_key)
        old_version = assessment.WARNING_CONFIG["version"]
        try:
            assessment.WARNING_CONFIG["version"] = "fixture-v-next"
            updated = self.warnings(rows)
        finally:
            assessment.WARNING_CONFIG["version"] = old_version
        updated_warning = next(w for w in updated if w["id"] == "REPEATED_SHORTFALL")
        self.assertNotEqual(original_key, updated_warning["derivation_key"])
        self.assertEqual(updated_warning["rule_version"], "fixture-v-next")

    def test_warning_evidence_persistence_is_immutable_and_deduplicated(self):
        warning = next(w for w in self.warnings(cycle((D("1000"), D("1000"), D("0"))))
                       if w["id"] == "REPEATED_SHORTFALL")
        prior = os.environ.get("DATABASE_URL")
        with tempfile.TemporaryDirectory(dir=os.path.dirname(__file__)) as temp_dir:
            os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(temp_dir, "f7.sqlite")
            try:
                save_scenario("fixture-1", "synthetic", "hash-1", {}, {"debt_warnings": [warning]})
                save_scenario("fixture-1", "synthetic", "hash-1", {}, {"debt_warnings": [warning]})
                rows = list_warning_evidence()
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0]["derivation_key"], warning["derivation_key"])
                changed = {**warning, "derivation_key": "new-version-key", "rule_version": "new-rule-version"}
                changed["evidence_record"] = {**warning["evidence_record"], "version": "new-rule-version"}
                save_scenario("fixture-2", "synthetic", "hash-2", {}, {"debt_warnings": [changed]})
                self.assertEqual(len(list_warning_evidence()), 2)
            finally:
                if prior is None:
                    os.environ.pop("DATABASE_URL", None)
                else:
                    os.environ["DATABASE_URL"] = prior


if __name__ == "__main__":
    unittest.main()
