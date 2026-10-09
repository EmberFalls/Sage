# F9 branch allocation and warning operations

## Allocation

`GET /api/allocations/candidates?branch_id=…` builds candidates only from immutable saved F8 comparisons. The API derives the exact assistance cost and date from the saved hypothetical assistance event, then checks the submitted borrower/branch, scenario, comparison, context hash, policy version, engine version, benefit definition, and INR unit. Unsupported, ineligible, stale, mismatched, or unknown-benefit candidates are excluded with a reason.

`POST /api/allocations` accepts those frozen candidate references, an exact Decimal INR budget, and optional enabled coverage floors. At most one candidate per borrower is selected. The objective is total immediate due-gap relief measured in `INR_due_gap_relief`; support cost is constrained by the exact budget and is not subtracted from that benefit objective. Candidate ID provides a deterministic tie break. Coverage floors are only active when explicitly enabled.

`branch-allocation-enumeration-v1` is a bounded exact enumerator with a 250,000-node cap and request timeout of up to five seconds. Complete search reports `optimal`; interrupted search reports `time_limit_feasible` or `time_limit_no_solution`, with no optimality claim and an optimistic bound gap where a feasible result exists. Unsatisfied coverage floors report `infeasible` and select nothing. Every allocation saves immutable input/result snapshots. Selected support is reevaluated into a new saved scenario with the dated program event; prior candidate scenarios are immutable.

## Warning workflow

F7 warning evidence remains immutable in `warning_evidence`. `warning_tasks` stores current operational status separately and `warning_task_events` stores append-only creation, assignment, acknowledgment, resolution, reopening, and supersession history. A unique derivation key creates at most one task; repeated assessment saves do not duplicate evidence or task creation. Supersession requires existing replacement evidence for the same rule and preserves the prior task events.

`GET /api/watchlist` filters persisted warning records by branch, status, and severity; it paginates the matching rows and calculates KPIs over that same filtered record set. `POST /api/warnings/{derivation_key}/workflow` performs validated task transitions.

The visible branch filter is not access control. These endpoints label their scope `synthetic_demo_unprotected_until_f10`; authenticated branch authorization remains a final gate for protected mode. F8 must provide real saved action evaluations and F7 must provide persisted warning evidence before operational deployment.
