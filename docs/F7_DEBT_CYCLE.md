# F7 modeled debt cycle and warning contract

## Scenario boundaries

F7 evaluates three synthetic crop seasons from one frozen assessment context. Season dates use the crop fixture's calendar anniversary (2026, 2027, and 2028); sale, due, input, and household expense dates retain their offsets within each season. The bridge and no-bridge worlds use the same climate and price path. In the current demo, the selected climate and price shocks repeat in each season. The output says `same_frozen_shock_repeated_each_season`; it does not represent distinct observed future forecasts.

No real hidden liabilities are inferred. Informal bridge draws are scenario inputs, have a per-season cap, use the assumed annual rate in `backend/app/config/warnings.json`, accrue simple actual-day interest on a 365-day basis, and are repaid from available end-of-season cash. Draws expose an event ID, amount, cap, date, rate, repayment date, provenance tag, and scenario-only marker.

## Debt accounting

Cash events follow the F5 chronological ledger ordering and paise rounding. Closing cash equals opening cash plus dated disbursement, sale, draw, and expense/payment events. Formal debt carries prior unpaid principal forward, accrues interest over actual days, and allocates payment to fees, interest, then principal. Unpaid interest is capitalized once at season close; paid interest never reduces principal. Informal interest is paid before informal principal and unpaid interest is capitalized at season close. The season row returns a `debt_conservation_delta_inr`, which must be zero:

```text
closing total debt = opening total debt
  + new formal principal + formal capitalized interest + unpaid formal fees
  - formal principal paid
  + bridge principal + informal capitalized interest
  - informal principal paid
  - permitted writeoffs
```

Formal payment status and modeled sustainability status are distinct. Paying a formal due through a bridge draw can satisfy the formal schedule while leaving greater total debt. The scenario does not claim that the modeled debt exists outside the scenario.

## Warning evidence and F9 handoff

Rules are versioned by `f7-debt-warnings-v2`. Every triggered result includes a deterministic derivation key and immutable evidence fields for rule/version, assessment and season IDs, thresholds, measured values, event IDs, and assumption tags. `warning_evidence.derivation_key` is a primary key and inserts use `INSERT OR IGNORE`; a repeated derivation is idempotent. A new rule version or threshold changes the key and appends a new record. `GET /api/warnings` returns the evidence feed for F9 watchlists. Assignment, acknowledgment, and resolution remain F9 lifecycle responsibilities.

The rule set covers bridge-to-formal-payment, material shortfall in at least two seasons, material carried informal debt growth, formal payment while total debt rises, and an action that reduces the current gap while increasing future cost or season-three debt. Trigger and just-below-threshold tests live in `backend/app/tests/test_f7_debt.py`.

## Integration gates

F7 consumes the F5 dated cash ledger semantics and stores scenario results as F6 saved evidence. Before production acceptance, verify the existing F5 ledger integration and F6 saved-evidence lifecycle in their owning gates. F8 action results can feed the action-specific future-burden rule without moving warning derivation or F9 lifecycle ownership.
