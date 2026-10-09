# Sage: detailed GitHub issues F4–F13

Prepared: 9 October 2026.

Purpose: copy each issue below into GitHub and assign it independently where practical. This is a proposed implementation backlog, not a statement that the features already work.

Source: `PhenoCredit_FULL_Implementation_Plan_V2.md`, especially sections 6–12, the F01–F33 feature inventory, and the full demonstration journey. Project branding in these issues is **Sage**.

## Numbering and scope

- **F4–F11 are development phases** from section 11 of the source plan. They are different from feature IDs such as F04 (applications) or F11 (historical yield).
- **F12 and F13 are additional issue wrappers**, introduced here to give release verification and the final frontend revamp explicit owners. The source plan itself ends at phase F11.
- F13 remains the last implementation issue. Earlier issues include the functional UI needed to use and verify their features; F13 completes the final visual redesign and interaction review.
- Model training is deferred by the project owner. F4 must deliver its complete illustrative path now. F11 contains explicit future data and empirical-model gates; missing training data cannot block unrelated software.
- Preserve the existing React/TypeScript frontend, FastAPI backend, SQLite persistence, and shared assessment service. Extend the existing implementation rather than generating a second product or competing scoring engine.
- Use a feature branch based on the latest agreed integration commit. The previously pushed F1–F3 branch is `feature/f1-f3-sage`; confirm which branch has been merged before starting. Do not assume local untracked files are reviewed or available to teammates.

## Current baseline and external blockers

Repository evidence in `docs/PHASE_F1_F4_IMPLEMENTATION.md` records F1/F2 as verified for their synthetic demo scope. F3 has an admitted 153-day Open-Meteo ERA5 archive for 1 June–31 October 2015. It represents a roughly 25 km grid cell, not a farm observation.

F3's historical yield join remains blocked: the Pune maize yield candidate is not admitted; primary source bytes, reuse terms, and an administrative-to-grid crosswalk are unresolved. Crop calendars, NDVI, soil and market price rows also lack admitted evidence. Imported candidates do not automatically become assessment inputs.

These are genuine data restrictions. Every issue must support explicit missing or illustrative states. A seeded fixture demonstrates software behavior; it does not establish observed agricultural or credit accuracy.

## How to minimize dependencies without hiding incomplete integration

Agree on the contracts below before parallel feature work. Each issue may consume a frozen fixture through the same interface its eventual production provider will use. Fixtures must say `SIMULATED` or `ASSUMED`, and the executable demo must expose this status.

**Independent module acceptance** proves the module works with its declared inputs. **Integration acceptance** proves it works with the actual upstream module through API and UI. Both are required when an issue promises an integrated journey. If the upstream service is absent, report the integration item as blocked; do not close the entire issue as complete using a mock.

No new frontend financial or agronomic formulas. All screens, reports, comparisons and exports consume authoritative backend results. Adapters can connect modules, but must not implement competing business calculations.

### Shared contracts to agree first

These are proposed contract requirements, not a claim that these exact schemas already exist. Extend the current Pydantic/OpenAPI and TypeScript contracts compatibly.

| Contract | Minimum fields and rules | Primary owner |
|---|---|---|
| Assessment context | Borrower, branch, plot, crop season and loan IDs; `as_of`; timezone; source snapshot IDs; input revisions; seed/path set; model/rule versions; context hash. Changing material context invalidates current results. | F6, with review by all consumers |
| Provenance envelope | Value, units, source class, source references, valid/observation time, issue/publication/availability time where applicable, geography/resolution, quality/missingness, limitations and version. Unknown availability must not pass strict historical replay as verified evidence. | F4/F11 using F3 |
| Yield projection | Crop, area in hectares, yield in tonnes/hectare, stage features, sale/harvest dates, source class, version, uncertainty method or missing state. | F4 |
| Dated ledger | Stable event ID, effective date and tie-break order, category, direction, exact INR amount, principal/interest/fees breakdown where applicable, evidence and scenario IDs, running cash and unpaid obligations. | F5 |
| Assessment result | Context hash, yield projection, ledger, due schedule, due-date gap, probability semantics, drivers, warnings, source/rule/model versions and limitations. Unsupported values are null/missing with a reason. | F5 through the shared orchestrator |
| Saved bundle | Baseline and stress result IDs; optional action result IDs; common context/path hashes; immutable inputs, results and versions; created actor/time; supersession links. | F6 |
| Debt trajectory | Season index and dates; opening/closing cash; formal and informal principal; interest; drawdowns; repayments; unpaid obligations; conservation reconciliation. | F7 |
| Action evaluation | Action ID/parameters; eligibility and reason codes; policy version; effective dates; farmer/lender costs; altered schedule; result/bundle references; multi-season tradeoffs; human review state. | F8 |
| Allocation candidate | Borrower/branch IDs; frozen scenario/action IDs; exact program cost; defined benefit/units; eligibility; optional coverage group; validity/version. | F9 |
| Warning and workflow | Immutable rule event and evidence; separate mutable assignment/acknowledgment/resolution state with actor/time/reason and audit history. | F7 rules, F9 workflow |
| Authorized projection | Server-controlled actor, role, branch and borrower scope; allowed fields; assessment references; redaction policy. Demo role selection is not authentication. | F10 security foundation |

Money must use Decimal or integer paise internally, with an explicit rounding policy and exact serialized representation. JSON floating-point round trips must not corrupt balances. Dates and timestamps must distinguish a crop-local date from a timezone-aware instant. Define whether stage windows use inclusive endpoints or half-open intervals and apply that convention everywhere.

### Suggested parallel starts and genuine integration gates

| Issue | Can start independently with contracts/fixtures? | Dependencies for final integrated acceptance |
|---|---|---|
| F4 agronomy/yield | Yes: source-backed weather where admitted; declared illustrative calendar/yield elsewhere. | F3 admission for any sourced claim; real aligned yield rows for historical-model claims only. |
| F5 finance/credit | Yes: dated yield, price and loan fixtures. | F4 yield wiring; F3 only when claiming sourced prices/evidence. |
| F6 scenarios/snapshots | Yes: persistence, hashes, replay and versioning around existing assessment service. | Actual F4/F5 results; F7/F8 for complete multi-season action comparison. |
| F7 debt/rules | Yes: frozen dated cash and loan schedules. | F5 ledger; F6 persistence; F8 only for action-specific warning rules. |
| F8 interventions | Yes: eligibility/catalog/review state and evaluator interface. | F4/F5 for effects; F7 for future costs; F6 for controlled comparisons. |
| F9 portfolio/workflow | Yes: allocator over frozen candidates and workflow over saved warning fixtures. | F8 candidates; F7 warning derivation; F10 authorization for authenticated branch operations. |
| F10 farmer/reports/security | Yes: authentication, access tests and reporting over frozen result fixtures. | Real F5–F9 results for complete journeys; no dependency on F11 training. |
| F11 data/ML/pilot preparation | Yes: provider admission, registry and validation infrastructure. | Admitted data for empirical claims; permissioned loan labels for real repayment models. Training remains deferred. |
| F12 release/reconciliation | Yes: regression harness, setup, operational diagnostics. | Required F4–F10 paths integrated; F11 only for claims actually enabled. Final release signoff repeats relevant checks after F13. |
| F13 frontend revamp | Design inventory can start early; implementation is last. | Stable APIs and completed feature journeys from F4–F10; F12 checks available. |

Suggested allocation: one engineer takes F4; another F5/F7; another F6/F8; another F9 or F10. F11 admission work can proceed whenever source evidence becomes available. This is an ownership suggestion, not a required staffing plan.

### Definition of done to include in every issue

- [ ] Backend behavior, typed API, persistence/migrations where needed, and usable UI are delivered together.
- [ ] Existing relevant behavior is inspected and upgraded; duplicated services and score formulas are avoided.
- [ ] Migrations work from the current database and a fresh database; seeds are deterministic and do not erase saved records.
- [ ] Success, invalid input, unavailable data, stale evidence and failure states are visible and actionable.
- [ ] Numerical values carry units, source class, version and limitations at the decision point and in exports.
- [ ] Meaningful automated invariants and a reproducible API/UI journey pass; results and commands are included in the PR.
- [ ] Parallel fixture tests are distinguished from real service integration evidence.
- [ ] Existing offline demo still works without live provider access.
- [ ] Documentation records implemented scope, empirical blockers and deferred items separately.
- [ ] No issue is marked complete solely because files, cards, endpoints or unintegrated model scripts exist.

---

## F4 — Dated crop stages, weather alignment and transparent yield projections

**GitHub title:** `[F4] Implement dated crop-stage stress and versioned yield projection with an explicit illustrative fallback`

### Goal

Connect dated weather and crop-stage assumptions to yield projections. Users must be able to change stage timing and inspect the different weather observations selected by that timing.

### Scope and deliverables

1. Add crop/region/season configuration with sowing and harvest dates, stage names, start/end dates, thresholds, weights, method, uncertainty, provenance and version. Reject unsupported crops or require an explicit illustrative configuration.
2. Validate stage ordering, boundaries and season coverage. Flag declared overlaps/gaps and define their aggregation treatment; accidental overlap must not silently double-count weather.
3. Connect admitted F3 snapshots to the assessment path through a reviewed geographic/time match. The existing source browser alone is insufficient. Unsupported geography remains missing or explicitly assumed.
4. Aggregate actual dated rain, heat and available water-balance/soil/NDVI features by stage. Report contributing source/event IDs, day counts, missing days and feature units. A percentile or anomaly requires a documented reference distribution; a sum alone must not be labeled a percentile.
5. Separate observations/reanalysis, forecasts issued by `as_of`, and hypothetical future overrides. Historical backtests must account for when reanalysis or yield data became available, not just observation dates.
6. Apply irrigation only to the documented water-stress component; heat and market effects remain separately computed.
7. Implement a deterministic illustrative response rule with visible configuration/version and nonnegative yield. Historical climatology/trend baselines may activate only when admitted aligned yield rows support them.
8. Add API responses and a crop-stage/yield view showing dated stages, source scale, selected weather features and output limitations.

### Suggested API behavior

Extend the shared assessment response with `stage_stress[]` and `yield_projection`. Add crop configuration read/update endpoints only where needed, with input validation and version preservation. Candidate inputs never silently become admitted scoring sources.

### Acceptance criteria

- [ ] Stages are ordered and inside the declared crop season; overlap/gap cases are rejected or explicitly flagged with a documented rule.
- [ ] Moving flowering across a known heat event changes the selected dates, heat-day count and stage features through API and UI.
- [ ] Same frozen input, source snapshot and rule version produce identical features and yield.
- [ ] Each yield shows tonnes/hectare, source class, configuration/model version and limitations.
- [ ] Future observations and later harvest outcomes cannot enter an earlier as-of run.
- [ ] Missing dates, missing observations and unsupported geography produce visible states rather than invented values.
- [ ] A baseline and changed-stage scenario are saved, reopened and traceable to the source rows used.
- [ ] A real model, if introduced later, has sample count, split years, geography, missingness, a time-ordered holdout and baseline comparison.

### Verification and completion boundaries

Use dated weather fixtures containing a heat event immediately inside/outside a stage boundary, missing days, overlap, unsupported geography and post-as-of observations. Verify date boundaries in the declared timezone. Demonstrate one admitted-weather path and one explicitly illustrative/missing path where available.

**Dependencies:** F3 for sourced features. Training is deferred; the illustrative feature can be completed independently of model training. The historical yield portion remains `BLOCKED_REAL_DATA` until admitted aligned rows exist. Report these outcomes separately.

---

## F5 — Exact dated cash flow, repayment feasibility and reconciled explanations

**GitHub title:** `[F5] Complete exact dated cash flow, scenario repayment feasibility and source-linked impact explanations`

### Goal

Translate crop production and price into money on actual dates, then show whether resources meet each contractual due obligation. Deliver the F33 financial bridge as part of the financial engine.

### Scope and deliverables

1. Use one authoritative chronological ledger for opening cash, loan disbursement, inputs, household costs, crop sales, other income, eligible modeled assistance and scheduled debt service.
2. Preserve formal principal/interest/fees separately. Actual demo journal entries stay immutable; corrections are reversal entries. Simulated forecasts never overwrite posted repayment records.
3. Normalize area/yield/price units. Convert INR/quintal to INR/tonne by multiplying by ten; distinguish mandi modal price, realized sale price and a user assumption. Store sale fraction, fees and dated realization explicitly.
4. Define same-day event ordering and minimum reserve policy. Compute cash immediately before each payment, cash gap, principal/interest paid, unpaid obligations and signed post-payment cash separately.
5. Calculate scenario shortfall frequency only over an explicit frozen scenario set with documented weights. When no distribution exists, show a deterministic feasibility result rather than invent a probability.
6. Present any rule-based or synthetically trained repayment estimate with its exact scope. No training is required now; label modeled feasibility accordingly.
7. Derive drivers from computed stage/revenue/ledger changes with dates and evidence. Build baseline-to-stress cash attribution that reconciles to one paise and separates yield, price, timing and other event contributions.
8. Add a usable loan/cash-flow view, explanation drawer and API result consumed by reports and scenarios.

Represent credit history explicitly: previous scheduled/actual payments, arrears, days overdue, renewals/rollovers and utilization where supported. Derive each feature only from records available by `as_of`; distinguish missing history from a perfect payment record. Every record/derived feature identifies its synthetic or user-entered provenance. If a feasibility rule uses history, expose the rule and contribution without claiming observed default calibration.

### Acceptance criteria

- [ ] Opening INR 10,000 + disbursement 70,000 − inputs 60,000 + sales 100,000 − household costs 15,000 − debt service 77,000 closes at INR 28,000.
- [ ] Inputs are expensed once; loan disbursement and principal repayment are distinct events.
- [ ] Revenue after a due date cannot pay an earlier installment retroactively.
- [ ] Multiple installments, partial payment, zero cash, reserve policy and equal-date events have explicit deterministic behavior.
- [ ] Principal balances reconcile and never become negative through rounding or excess-payment handling.
- [ ] Quantity/price attribution sums exactly to revenue change under the documented rounding policy.
- [ ] Baseline pre-due cash plus attributed event differences equals stressed pre-due cash within one paise.
- [ ] Rescheduled due dates use separate declared cutoffs; comparisons do not imply equal clocks when dates differ.
- [ ] Probability fields state distribution, horizon and simulation scope; unsupported probability fields are missing with a reason.
- [ ] API, UI and report values agree for the same assessment ID.
- [ ] Past payments/arrears/rollovers are represented with provenance; future repayment events cannot enter an earlier assessment and absent history is visibly unknown.

### Verification and dependencies

Include independently calculated fixtures for the example above, harvest after due, interacting price/yield changes, multiple dues and ledger reversals. Trace a contribution from UI to its exact event/source.

**Can start now:** consume a typed yield/price fixture or existing illustrative output. **Integration gates:** F4 projection wiring; admitted F3 price rows only for sourced claims. F7/F8 consume this ledger later and should not be prerequisites for core F5 completion.

---

## F6 — Immutable scenario bundles, replay and controlled comparisons

**GitHub title:** `[F6] Upgrade Scenario Lab with immutable replay and frozen-context multi-candidate comparisons`

### Goal

Compare baseline, stress and candidate actions on exactly the same borrower/loan/source context, and preserve what users actually evaluated.

### Scope and deliverables

1. Freeze borrower/loan revisions, opening balances, crop season, as-of/timezone, source snapshots, climate paths, seed, model/rule/configuration versions and canonical inputs.
2. Define canonical serialization/hashing. Exclude transport timestamps from deterministic content hashes; retain created-at metadata separately.
3. Persist baseline, stress and each action result plus a bundle linking them. Changes create new immutable records and supersession links.
4. Reopen stored results without recalculating against today's borrower/source data. A separate rerun produces a new assessment. If an older evaluator is unavailable, show stored results and disclose inability to recompute that version.
5. Evaluate `baseline = reference climate + no action`, `stress = changed climate + no action`, and `action = same stress + specified action`. Keep seed/path hashes equal across controlled comparisons.
6. Wire all supported controls to backend inputs; show pending/stale states, reset and retry. Prevent late responses from replacing newer inputs.
7. Compare multiple candidate actions with units, eligibility, first-season relief, added interest, future debt and evidence links. Unavailable debt/action providers show explicit missing sections.
8. Invalidate current-result badges when borrower terms, stage configuration or selected evidence changes. Preserve historical assessments unchanged.

### Acceptance criteria

- [ ] Identical frozen inputs produce identical canonical results/context hashes.
- [ ] Reset restores the exact baseline content for fixed data.
- [ ] Baseline/stress/action differ only in their declared overrides and permitted action effects.
- [ ] An action compared against another seed/path set is rejected as incomparable or clearly separated.
- [ ] Saved results survive process restart and source/borrower updates unchanged.
- [ ] Duplicate save/retry is idempotent under a declared idempotency policy.
- [ ] Changed loan terms mark the old current assessment stale.
- [ ] UI shows pending input/results and never labels an old response current.
- [ ] Every report/comparison includes bundle/result/context references.
- [ ] At least two candidate actions complete the same-shock comparison after F8 integration.

### Verification and dependencies

Test canonical hashes, persistence across restart, changed provider snapshot, edited borrower, unsupported old version and deliberately reordered asynchronous responses. Demonstrate baseline → stress → save → reopen → reset.

**Can start now:** wrap the existing shared evaluator. **Final gates:** F4/F5 actual results; F7/F8 for full life-cycle action comparisons. Persistence and generic comparison infrastructure do not need to wait for those modules.

---

## F7 — Three-season debt conservation and evidence-based warning rules

**GitHub title:** `[F7] Complete three-season formal/informal debt simulation and deterministic warning evidence`

### Goal

Show how modeled additional borrowing can make formal repayment appear successful while increasing future financial pressure. Preserve all debt and interest across seasons.

### Scope and deliverables

1. Run three explicitly dated seasons using F5 ledger semantics and frozen climate/price assumptions. Explain whether shocks repeat or follow distinct paths.
2. Carry opening/closing cash, formal principal, informal principal, accrued/capitalized interest and unpaid obligations separately.
3. Model bridge draws with amount, limit, date, interest terms and repayment date. Tag each as assumed, simulated or borrower-entered; never infer real hidden liabilities.
4. Provide no-bridge and bridge worlds from the same starting context. Formal payment status and sustainable repayment status must be separate outputs.
5. Enforce debt conservation: closing debt = opening debt + new principal + modeled capitalized interest − principal paid − permitted writeoffs. Interest payments must not accidentally reduce principal twice.
6. Implement versioned warning derivation for bridge-to-pay, recurring material gap in at least two seasons, carried informal debt growth, formal paid while total debt rises, and action relief that worsens future burden.
7. Persist immutable warning evidence containing rule/version, thresholds, season/assessment IDs, measured values, event IDs and assumption tags. Provide a stable idempotent derivation key.
8. Deliver a debt timeline/table with event drill-through and API results suitable for F9 watchlists.

### Acceptance criteria

- [ ] A bridge draw can pay a formal due while increasing informal outstanding.
- [ ] All three seasons reconcile principal and interest under independent fixture calculations.
- [ ] Zero bridge, partial bridge, insufficient bridge, no-income season and debt payoff behave explicitly.
- [ ] Formal paid does not erase total debt or imply sustainable repayment.
- [ ] Every warning has a positive trigger test and a near-threshold negative case.
- [ ] Repeated derivation does not duplicate the same immutable warning.
- [ ] Threshold/rule changes create new versioned evidence rather than rewriting old warnings.
- [ ] UI uses scenario language and never asserts undisclosed debt as a detected fact.
- [ ] Action-specific future-burden warnings work after F8 integration.

### Boundaries and dependencies

F7 owns rule derivation and debt computation; F9 owns staff assignment/acknowledgment/resolution. This splits the original phase's lifecycle work into an independently implementable operational issue without dropping it.

**Can start now:** dated ledger fixtures and contracts. **Final gates:** F5 ledger integration and F6 saved evidence. F8 is needed only for action-specific warnings. Real loan/debt records are not required for the explicitly synthetic demo.

---

## F8 — Eligible interventions, dated costs and human review

**GitHub title:** `[F8] Implement policy-versioned interventions with full cost comparisons and demo review workflow`

### Goal

Offer feasible actions whose modeled relief, costs and later consequences can be inspected. A recommendation must never silently execute a loan modification.

### Scope and deliverables

1. Build a versioned action catalog: outreach, due-date shift, installment change, irrigation support, hypothetical assistance, insurance scenario, and pre-sowing timing/crop options where the agronomic configuration supports them.
2. Each catalog entry declares whether it is evaluable or unsupported. Unsupported options remain visibly unavailable with reasons; do not give every option an invented benefit.
3. Check dates, policy maximums, water access, crop/region support, sowing status, enrollment/cutoff/trigger and budget requirements. Version policy assumptions and separate illustrative policy from sourced rules.
4. Generate bounded single-action and compatible pair candidates. Reject incompatible combinations and account for each cost once.
5. Evaluate candidates through the shared assessment service with identical stress inputs/paths. Include actual dated effects, revised installments, additional interest, premium/support cost and later debt.
6. Rank by a declared objective or Pareto tradeoffs. Explain visible weights and ties; show ineligible and non-selected options separately.
7. Implement proposal/review transitions with actor, reason, assessment reference and timestamps. Approval applies only to a new simulated result; existing loan events remain intact.
8. Show exact due-date cash impact and separate cutoffs where the repayment date moves. Deliver a functional intervention comparison/review view.

### Acceptance criteria

- [ ] Rescheduling changes due dates and interest according to declared terms and exposes later burden.
- [ ] Installment changes conserve principal and reconcile payments/fees.
- [ ] Irrigation is rejected without water access or when its effective date misses the intended stress window.
- [ ] Sowing/crop changes after sowing are rejected unless explicitly supported as a hypothetical scenario with appropriate limitations.
- [ ] Insurance payouts are zero without required enrollment, valid trigger and modeled payout timing; retroactive enrollment cannot be silently assumed.
- [ ] Outreach has no automatic numeric risk reduction without a declared mechanism.
- [ ] Ineligible or unsupported actions cannot be ranked as successful or passed to the allocator.
- [ ] Comparison includes immediate gap relief, cost, interest, three-season debt and source/assumption tags.
- [ ] Invalid review transitions fail and review history persists.
- [ ] A proposal approval does not mutate a posted loan or send an external message.

### Verification and dependencies

Use fixtures for affordable-but-costly rescheduling, unavailable irrigation, missed insurance cutoff, unsupported crop, conflicting pairs and no beneficial candidates. Complete API/UI proposal → review → applied-in-simulation.

**Can start now:** catalog, constraints, review persistence and evaluator interface. **Final gates:** F4/F5 effects, F7 later consequences, F6 controlled comparisons. Current legal/lender policy must be verified before presenting policy as operationally valid; illustrative demo rules do not establish eligibility for a real program.

---

## F9 — Portfolio allocation and branch warning operations

**GitHub title:** `[F9] Deliver exact-budget portfolio allocation and persistent branch alert workflows`

### Goal

Let a branch prioritize hypothetical support under an explicit budget and act on saved warnings through an auditable workflow.

### Scope and deliverables

1. Accept frozen eligible action candidates with borrower/branch IDs, exact program cost, benefit definition, scenario IDs and version/context references.
2. Select at most one candidate per borrower; enforce the total budget and explicitly enabled coverage constraints. Define objective units and prohibit unknown benefit or invalid cost candidates.
3. Choose an appropriate bounded solver. Report solver status, timeout and optimality gap where supported; a heuristic or timed-out result must not claim proven optimality.
4. Store immutable allocation input/result snapshots with selected/unselected candidates, costs, remaining budget, constraints and solver version.
5. Apply selected assistance only to new hypothetical scenarios for selected borrowers. Show its dated cost and recomputed outcome; preserve unselected saved results.
6. Build branch filters, KPI drilldowns and paginated watchlists from real saved records, not hardcoded chart totals.
7. Implement assign, acknowledge, resolve, reopen and supersede operations with validation, actor/time/reason and append-only history. Workflow state is separate from F7 warning evidence.
8. Connect F7 derivation after assessment save idempotently. New evidence may supersede a warning but must preserve historical events.

### Acceptance criteria

- [ ] Total selected cost never exceeds budget by a paise.
- [ ] Each borrower receives at most one selected action; ineligible/undefined candidates are excluded with reasons.
- [ ] Zero budget, exact fit, fractional INR costs, zero-cost candidates, tied benefits and infeasible coverage floors have explicit behavior.
- [ ] A tiny fixture's selected objective matches exhaustive enumeration when the solver claims optimality.
- [ ] Timeout/infeasibility returns a truthful status and no invalid allocation.
- [ ] Selected scenario results include program cost; unselected immutable assessments remain unchanged.
- [ ] Watchlist filters and KPI counts match underlying saved rows.
- [ ] Assignment/acknowledgment/resolution persist after restart and invalid transitions fail.
- [ ] Duplicate assessment processing does not duplicate warnings/tasks.
- [ ] Authorized branch scoping is enforced after F10 security integration; a UI filter alone is insufficient.

### Verification and dependencies

Allocator development is independent of the intervention engine when using clearly marked frozen candidate fixtures. Warning workflow development is independent of the rules engine when using persisted evidence fixtures.

**Final gates:** F8 actual candidate evaluations, F7 actual warning events and F10 authenticated branch boundaries for protected mode. The synthetic workflow can operate earlier with a visible non-authenticated demo label.

---

## F10 — Authorized farmer views, reports and understandable methodology

**GitHub title:** `[F10] Complete farmer isolation, auditable reports and role-specific help`

### Goal

Provide a usable farmer journey and complete exports from the same saved results officers use. Establish actual server-side access boundaries before claiming private farmer or branch access.

### Scope and deliverables

1. Introduce an explicit authenticated mode alongside isolated synthetic guest demo mode. Document identity/session approach and do not treat a client role selector as identity verification.
2. Enforce server-side officer/branch-lead/farmer/admin scopes across reads, writes, list queries, exports, source administration and direct object-ID access. Actor/branch identity comes from trusted server auth context.
3. Protect credentials/secrets; use appropriate password hashing if passwords are stored; define session expiry/revocation and safe cookie/CSRF handling where relevant. Restrict permissive development CORS in hosted mode.
4. Add append-only access/action audit records with actor, entity, time, reason and result reference; avoid logging raw sensitive financial payloads or credentials.
5. Deliver farmer home, farm, loan, outlook, options and help using authorized projections of saved assessments. Explain dates, assumptions, missing evidence and action limitations in plain language.
6. Add a persistent in-app request/review interaction linked to farmer and assessment. External email/SMS delivery is not required by this issue.
7. Generate valid PDF/CSV/JSON as applicable from immutable results, including IDs, as-of, inputs, assumptions, sources, versions, limitations, totals and human review status. Protect report access and downloads.
8. Add glossary, methodology, error/empty/stale states and basic keyboard/mobile usability. F13 performs final visual revamp; this issue still needs usable pages.

### Acceptance criteria

- [ ] Farmer A cannot read or export farmer B's data by guessing IDs, altering parameters or opening saved scenario URLs.
- [ ] Officers cannot cross branch boundaries without an explicitly authorized role; admins cannot silently impersonate users.
- [ ] Unauthorized requests return consistent 401/403/404 behavior under a documented disclosure policy.
- [ ] Guest demo routes access only synthetic demo records and cannot reach authenticated private records.
- [ ] Farmer summary values match the underlying assessment while unauthorized fields are excluded server-side.
- [ ] Farmer can inspect outlook, compare eligible options and create a persistent request.
- [ ] PDF renders, CSV parses, and exported amounts/IDs agree with API/UI for the same immutable run.
- [ ] Export shows simulation scope and unavailable data, even when only a subset of results exists.
- [ ] Sensitive actions and report downloads are auditable without exposing secrets in logs.
- [ ] Both farmer and officer journeys work on mobile and with keyboard navigation.

### Verification and dependencies

Test an access matrix with two branches and two farmers, direct-ID access, list/filter leakage, revoked/expired sessions, admin-only source updates and export authorization. Render a report with long notes/missing sources and compare totals against its stored assessment.

**Can start now:** authentication/access infrastructure, methodology and report templates over frozen results. **Final gates:** F5–F9 complete result/workflow wiring. F11 training is not required. This issue owns application security; F11 adds pilot-specific governance and empirical safeguards rather than duplicating auth.

---

## F11 — Source expansion, model handoff and future empirical validation

**GitHub title:** `[F11] Prepare admitted data, versioned model handoff and claim-specific validation gates; defer training`

### Goal

Make real-data improvements and later trained artifacts replaceable and auditable. The current deliverable is infrastructure and admission controls; empirical training remains deferred until separately enabled.

### Scope and deliverables

1. Track each source candidate through raw bytes, checksum, license/reuse review, codebook/units, geographic coverage, time coverage, missingness and explicit admission decision.
2. Prioritize the unresolved crop/calendar/yield/weather match, then NDVI/soil/market data. Do not call a provider integrated because its website or URL exists.
3. Reject mismatched crop/geography/year/units; record a reviewed crosswalk where needed. Retain original and normalized immutable data with lineage.
4. Handle forecast issue/valid/availability times and reanalysis release limitations for historical as-of replay. Separate cached forecasts, historical reanalysis and analogues.
5. Define an offline artifact handoff: safe supported format, checksum, model version, runtime/dependencies, feature order/types/units, crop/geography coverage, training cutoff, data hashes, evaluation metadata and inference example.
6. Add a model registry and load-time schema/coverage checks. Reject incompatible, missing or tampered artifacts; preserve an explicitly labeled illustrative fallback. Never load arbitrary untrusted pickle artifacts automatically.
7. Prepare validation tooling for seasonal climatology/trend baseline, time-ordered holdout and geographic holdout where samples permit. Record counts, split years, errors, missingness and training-only preprocessing.
8. Add calibrated yield intervals only after calibration/holdout evidence exists. Otherwise display scenario ranges with their method; do not translate yield coverage into calibrated default-probability coverage.
9. Document pilot privacy/governance, authorized data use, retention, source terms and security review. Real credit modeling requires governed linked repayment labels; household surveys alone are insufficient.

Extend the existing source monitor with admitted versus candidate status, last successful refresh, latest failed attempt, observation/issue time, freshness policy, geographic resolution, cached/live mode, exact units and assessment usage. Satellite views must show cloud/coverage quality and spatial resolution; soil views must show layer depth and units; price views must show commodity/market/date and modal versus realized/assumed semantics. Unsupported providers display missing states rather than synthetic traces styled as observations. Any published dataset or policy claim requires checking the relevant primary source at implementation time.

### Acceptance criteria for software delivered now

- [ ] Source admission distinguishes candidate, rejected, admitted and unavailable with reasons and evidence.
- [ ] Missing yield/calendar/NDVI/soil/price data remain visibly missing or illustrative.
- [ ] An artifact fixture can be registered and run through the existing evaluator without changing frontend contracts.
- [ ] Feature-schema/version/coverage mismatch and checksum failure are rejected with visible fallback/error states.
- [ ] Evaluation reports distinguish illustrative fixtures from real held-out rows.
- [ ] Training jobs are offline and never triggered by ordinary assessment clicks.
- [ ] Data/ML status and current limitations are visible in API/UI and exports.

### Deferred empirical acceptance checklist

- [ ] Admitted aligned yield rows exist with adequate crop/region/season coverage.
- [ ] A time-ordered evaluation reports sample count, baseline comparison, split years, geography and missingness.
- [ ] Preprocessing, target selection and feature availability exclude leakage.
- [ ] Claimed yield interval coverage is measured on the quantity/horizon calibrated.
- [ ] Real repayment claims have permissioned linked labels, event/horizon definition and independent temporal/geographic validation.

**Dependencies:** F3 intake contracts and admitted source evidence; F4 inference interface for real yield integration; F10 for protected pilot access. Source admission and artifact preparation can start independently. Report software delivery as complete only for that explicit scope; empirical work remains `DEFERRED`/`BLOCKED_REAL_DATA` until evidence exists.

---

## F12 — Cross-feature reconciliation, offline release and operational readiness

**GitHub title:** `[F12] Verify integrated Sage journeys, exact reconciliation and reproducible offline release`

### Goal

Give the team one reproducible release gate covering the full product, including features that were built independently. Detect incomplete integration before final frontend polish and repeat relevant checks afterward.

### Scope and deliverables

1. Maintain a mapping from plan feature IDs F01–F33 to issue owner, endpoint, page, data/rule provenance, verification evidence and unresolved blocker. Inventory IDs must not be confused with phase numbers.
2. Provide documented fresh setup, dependency locks, env template, migration/seed and localhost start/stop commands. Avoid machine-specific absolute paths in startup scripts.
3. Preserve seeded offline mode with frozen dates/data/seed, isolated test database and no required paid/login provider. Live provider failures use only admitted cache or visible unavailable states.
4. Exercise borrower → application → demo loan → crop evidence → assessment → stress → debt worlds → intervention → portfolio workflow → farmer projection → report.
5. Verify F31 same-context comparison, F32 rule/workflow evidence and F33 exact cash attribution together. Check API/UI/export/saved-result consistency.
6. Add operational request IDs, version/hash references, source refresh/error status and runtime diagnostics without raw sensitive payload logging.
7. Measure cached single-borrower latency and portfolio responsiveness on actual hardware. Treat plan numbers as targets; record measured results and limitations. Do not fabricate throughput claims.
8. Verify backup/restore of demo database and saved results, controlled error responses, migration upgrade and current access matrix.

### Acceptance criteria

- [ ] A clean checkout starts using documented commands and creates a deterministic demo.
- [ ] Existing databases migrate without losing journal or saved assessment records.
- [ ] Live weather outage preserves an admitted cached source or displays unavailable; stale data is never marked LIVE.
- [ ] A baseline/stress/action bundle traces identical context/paths through API, UI and export.
- [ ] Price×yield and harvest-after-due fixtures reconcile the financial waterfall within one paise.
- [ ] Three-season debt, intervention cost and portfolio budget invariants hold together.
- [ ] Branch/farmer isolation is verified for authenticated mode; demo limitations remain visible.
- [ ] Every required route completes its intended journey or shows a documented blocker; no decorative dead controls.
- [ ] Each inventory item has evidence or an honest status; no global completion claim hides empirical blockers.
- [ ] Verification records include exact commit, environment, commands, observed results and outstanding failures.

### Completion and dependencies

Prepare harnesses and operational checks in parallel with other issues. Full journey verification requires F4–F10 integration; only enabled empirical claims require F11 evidence. Record an initial integration gate before F13 and perform final release signoff after F13 without creating another implementation phase.

---

## F13 — Final Sage frontend revamp and product usability review

**GitHub title:** `[F13] Revamp Sage frontend across landing, lender and farmer journeys with responsive accessible design`

### Goal

Make the completed platform coherent, readable and polished across every feature. This is the final implementation issue so design work uses stable behavior and real API result states.

### Scope and deliverables

1. Audit landing, overview, borrowers/dossier, applications, loans, climate, assessments, Scenario Lab, debt timelines, interventions, portfolio allocation, watchlist, reports, source monitor, settings and farmer routes.
2. Refine shared theme tokens, typography, spacing, contrast, tables, forms, buttons, chips and charts. Landing typography must have a readable weight; inspect actual font loading and fallback rather than changing a font name alone.
3. Use Sage consistently in visible product copy and generated reports; retain original source-document names as provenance references where necessary.
4. Preserve URL routes, browser back/forward, filters, borrower/season/loan/as-of context and saved result IDs. Maintain distinct officer and farmer shells.
5. Make primary journeys discoverable: portfolio → borrower → evidence → assessment → scenario → action → review → report. Add useful breadcrumbs, focused page actions and clear return paths.
6. Present baseline/stress/action comparisons with readable units, due dates, costs, future consequences and clickable source/event evidence. Financial waterfall has an equivalent exact numeric table.
7. Design real loading, empty, error, stale, missing evidence, ineligible action, no feasible allocation and access-denied states. Pending controls must not imply results already updated.
8. Make charts understandable through labels, textual summaries, non-color status indicators and accessible alternatives. Ensure keyboard focus, form labels, validation, dialog/drawer behavior and sensible tab order.
9. Review desktop/tablet/mobile including 390 px width, touch targets, long content, scrolling tables and reduced-motion preferences. Keep core actions reachable without horizontal page overflow.
10. Preserve all provenance, demo/synthetic labels, uncertainty and human-review boundaries at the point of decision. Improve copy without turning assumptions into claims.

### Acceptance criteria

- [ ] Every supported route works by direct URL, in-app navigation and browser history.
- [ ] Core officer and farmer journeys finish using actual API results, not hardcoded replacement numbers.
- [ ] Landing and app typography remain readable with loaded and fallback fonts; text is not excessively thin.
- [ ] No clipping/page overflow at agreed desktop/tablet/mobile viewports; usable table scrolling is explicit.
- [ ] Baseline/stress/action numbers and waterfall tables match the backend for the saved context.
- [ ] Source class, units, as-of, versions, stale/missing state and limitations remain visible.
- [ ] Keyboard users can navigate menus, forms, dialogs, comparisons and report actions.
- [ ] Loading/failure/empty/ineligible states are reviewed with reproducible fixtures.
- [ ] Screenshots of agreed journeys and the exact verification commit are included in the PR.
- [ ] F12's relevant regression and final release checks pass after the revamp.

### Dependencies and boundaries

Implementation starts after required feature APIs/journeys stabilize, with F12 verification available. A design inventory can be prepared earlier. Do not replace the financial engine, hide missing functionality behind polished cards or silently change calculation semantics during redesign. Any business-logic defect found here gets an explicit fix and renewed relevant verification.

---

## Coverage map and final handoff

| Source-plan feature IDs | Primary issue coverage |
|---|---|
| F01–F04 landing/navigation/borrowers/applications | Preserve existing F1/F2 functionality; F12 regression and F13 final design. |
| F05 ledger, F12 market prices, F13 credit history, F14 risk, F15 explanation, F16 Stress-at-Due | F5; F11 source improvements. |
| F06 portfolio | F9 operations and F13 presentation. |
| F07 crop stages, F08 satellite, F09 weather, F10 soil/irrigation, F11 yield | F4 scoring/visibility and F11 actual source admission/model extension. F3 remains source-intake prerequisite for sourced claims. |
| F17 sustainable repayment, F18 debt cycles | F7. |
| F19 Scenario Lab, F30 saved histories, F31 three-way workbench | F6; F8 for action effects and tradeoffs. |
| F20 interventions | F8. |
| F21 allocator, F22 watchlist | F9; F7 warning evidence. |
| F23 farmer, F24 reports, F26 security/audit, F29 help | F10; domain audit in F8/F9 and final review in F12. |
| F25 source quality, F27 uncertainty/deferral | F3 baseline, F4/F5 point-of-decision semantics, F11 extensions, F12 consistency. |
| F28 responsive polished design | Functional accessibility in each issue; final F13 revamp. |
| F32 debt early warnings | F7 derivation and F9 lifecycle. |
| F33 financial impact decomposition | F5 exact arithmetic, F8 revised-cutoff action attribution, F6 comparison, F13 final visual presentation. |

Each PR should include: implemented scope; migrations and contract changes; API/UI demonstration steps; relevant verification commands/results; source/model/rule versions; integration dependencies actually exercised; missing evidence and deferred items. Attach a sample saved result/report when it helps review.

**Release labels:** `COMPLETE` means all declared software and integration acceptance passed; `DEMO_ONLY` means functioning synthetic scope with explicit limitations; `BLOCKED_REAL_DATA` means specific source/empirical criteria cannot pass; `DEFERRED` means the owner has deliberately postponed work. These labels describe scope and must never be collapsed into an unsupported claim of production readiness.
