# G0–G4 verification — 2026-10-09

Scope: five gates, G0 through G4, against the supplied V2 plan. Verification includes fixes, not just an inspection of the previous implementation.

## Results

| Gate | Functional demo result | Remaining specification gap |
|---|---|---|
| G0 | Both servers boot; production TypeScript/Vite build passes; seeded SQLite records, deterministic hashes, Pydantic response envelope and JSON schema captured. | Nested assessment objects still use flexible dictionaries rather than a fully typed contract. Existing stack uses plain CSS/sqlite3 and state-based navigation instead of the prescribed Tailwind/shadcn/SQLAlchemy/React Router stack. |
| G1 | Pass with explicit fallback. Browser registry search → second borrower dossier → loan → climate works. SQLite records and source statuses checked. | No real source ingestion. Navigation does not support URL deep links. |
| G2 | Pass for the disclosed illustrative fallback. Eight input groups, dated stage calendar, exact money, sale timing, repayment/shortfall frequencies and explanations verified. | The plan's real-data baseline is absent. No aligned training data, fitted yield artifact, validation metrics or calibrated credit model. |
| G3 | Core demo passes. Browser heat/stage/price controls recompute, baseline remains unchanged, bridge reconciles to paise, reset restores zero shocks. | Out-of-order response protection inspected in code; an adversarial delayed-network race was not automated. No mobile layout acceptance check. |
| G4 | Core demo passes. Both eligible demo proposals have different costs and full payment schedules; three-season liabilities and rule-derived warnings tested; browser bridge repays bank while informal debt persists/grows. | Eligibility is a demo pre-due-date rule, not bank policy. Comparison presents aligned metrics and season cards rather than every chart/layout detail in H27. |

These are functional demo results, not full acceptance of every requirement in the plan. G0 contract/stack and G2 real-data requirements remain partial.

## Executed evidence

- `backend-tests.txt`: 15/15 unittest financial/API checks passed (0.524 seconds). Temporary databases isolate each test.
- `frontend-build.txt`: `npm run build`, TypeScript and Vite production build passed.
- `live-api.txt`: five live HTTP scenarios passed schema validation, immutable snapshot reopening, selected loan schedule consistency and backend action-cost reconciliation.
- `baseline.json`, `heat.json`, `bridge.json`, `reschedule.json`, `split.json`: actual API responses.
- `scenario-bundle.schema.json` and `openapi.json`: captured contract artifacts.
- Browser walkthrough: registry search for Pune, B-DEMO-002 dossier, loan events, climate source/calendar screen, heat +4 days, flowering → harvest, price −80%, bridge cap ₹150,000, split and +30-day actions, and reset. No warning/error console entries observed in the checked tab.

## Reconciled examples (B-DEMO-001)

| Case | Pre-first-due cash | First-due gap before bridge | Total bank payment | Actual bridge draw |
|---|---:|---:|---:|---:|
| Baseline | ₹246,107.20 | ₹0.00 | ₹125,365.48 | ₹0.00 |
| Four-day flowering heat | ₹73,000.00 | ₹52,365.48 | ₹73,000.00 | ₹0.00 |
| Heat +30-day proposal | ₹237,798.05 | ₹0.00 | ₹126,549.04 | ₹0.00 |
| Heat split proposal | ₹73,000.00 | ₹0.00 | ₹128,133.63 | ₹0.00 |

Split payments: ₹63,622.98 on 2026-11-05 and ₹64,510.65 on 2026-12-20. Three-season proposal cost: ₹8,304.45. The +30-day proposal adds ₹1,183.56 interest per season exactly once.

Four-day harvest heat, price −80%, bridge enabled: bank receives ₹125,365.48, formal ending balance is zero, and informal liabilities end at ₹18,443.56 / ₹58,304.61 / ₹105,340.65 over three seasons. A satisfied bank due does not imply sustainable total debt.

## Repairs made during verification

- Removed duplicate principal accumulation in the debt cycle and duplicate restructuring interest.
- Implemented both split installments in the dated cash ledger.
- Carry unpaid formal/informal balances and available cash; repay informal debt from available surplus.
- Use actual disbursement-to-due days for bank interest and Decimal money throughout.
- Derive repayment feasibility from 21 explicitly hypothetical paths instead of a heuristic score presented as probability.
- Freeze baseline context, preserve scenario IDs, reconcile financial bridge rounding, reject invalid inputs, and evaluate action eligibility.
- Configure warning thresholds and return rule IDs with exact ledger evidence.
- Add explicit bank-payment versus financial-resilience comparison and both installment rows.
- Keep selected borrower/loan/scenario consistent, clear old dossier data during loading, and guard stale exports and action comparisons.
- Remove external font import so the UI does not require Google's font service.

## Modeling limits

Both borrower profiles and credit histories are synthetic. Weather, irrigation, yield, calendar and price are illustrative assumptions; NDVI/soil are unavailable. The wheat summer calendar is a timing fixture, not a validated Nashik calendar. Yield and price paths move together and are equally weighted; their repayment frequency is not an empirical default probability.

The three-season model repeats a new synthetic seasonal loan and the same shock, carries cash and arrears, and uses assumed simple interest. Missed bank payments remain arrears until the next scheduled season rather than automatically settling after a late sale. These are demo policy assumptions, not verified lending practice.

No real loan is changed. At the time of the original G0–G4 audit, later gates had not yet been verified; subsequent G5–G9 evidence is appended below. No Git commit was created because this workspace exposes `.git` as read-only.

## Reproduce

Install `backend/requirements-dev.txt`, then from `backend` run `python -m unittest app.tests.test_gates -v`. Start `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`, then `python verify_live.py`. From `frontend`, run `npm ci` and `npm run build`; use `npm run dev -- --host 127.0.0.1` for the browser walkthrough.

This machine's `py` launcher has no Python installed. Verification used bundled Python 3.12.14 with dependencies in `backend/.packages` and `PYTHONPATH` pointing there, Node 22.23.2 and npm 10.9.8.

## G5–G7 follow-up (2026-10-09)

G5 adds `GET /api/scenarios?limit=50`, immutable saved-assessment listings, stored-request replay for reopen (including older snapshots), UI controls restored to the chosen snapshot, bridge CSV and a print-ready report with comparison metrics, rule evidence, provenance and hashes. Browser checks reopened a split-payment scenario, checked borrower search/dossier/loan/climate, report screen and farmer view. PDF rendering still needs a print-output check on the judge's machine.

G6 aligns currency displays to two decimal places and repairs the desktop scenario bridge width; the waterfall scrolls horizontally inside narrow cards. At 390px, page scroll width equaled the viewport (375 CSS px in the browser), with stacked scenario cards and usable controls. No allocator or yield-model work was attempted because no suitable real training table is present.

G7 adds the repeatable judge flow in [REHEARSAL.md](REHEARSAL.md). Final backend suite: 17/17 passed, including snapshot reopen and compatibility with older immutable records. Final frontend TypeScript/Vite build passed. Five live HTTP scenarios and saved catalog/reopen/loan-schedule consistency were checked. The UI's weather/calendar/yield/price behavior is explicitly assumption-based and the app code uses no external weather or market service. No video backup was recorded.

The bridge CSV download was also exercised in the browser and inspected locally; its headers, provenance statuses and paise amounts match the selected assessment snapshot. Print/PDF was not invoked to avoid a system print dialog; the print stylesheet is in place and the PDF output remains unverified.

## G5–G7 recheck (2026-10-09)

The recheck found and repaired a snapshot integrity problem: reopening a saved assessment triggered automatic evaluation, which could replace frozen results. Reopen now restores its saved date, irrigation override and controls without a POST evaluation. Legacy stored requests are normalized through ScenarioRequest defaults without recomputing their financial results. The UI uses the frozen borrower context while showing that snapshot; selecting another borrower clears the inherited irrigation override.

The saved date also drives climate context and intervention eligibility. Both proposal buttons are disabled when the contractual due date has passed. Reports cannot be exported while the current controls are awaiting an assessment. The print report now includes informal debt after season 3 and cumulative action cost, and identifies an ineligible action.

Evidence:

- 18/18 backend tests passed. A new isolated database test edits the borrower record after saving, verifies that a new evaluation changes context, and verifies that reopening preserves the original saved result and custom inputs.
- Final TypeScript/Vite production build passed; five live HTTP scenarios, catalog membership, loan schedules and saved reopening passed.
- `verify_recheck.py` created scenario `259189771ef3e1aea71d`, as of 2026-11-06, with irrigation 0.8, rain -20%, heat 4 days and an ineligible split proposal. Its API response is saved in `recheck-snapshot.json`.
- Browser reopening restored the controls, date and ineligible state. API logs showed the snapshot GET and no automatic evaluation POST. Downloaded JSON retained the exact comparison hash, assessment date and irrigation override.
- Browser climate context displayed 2026-11-06 and both intervention buttons were disabled with the due-date explanation. The print-report DOM contains formal and informal debt and action cost.

Rendered PDF output remains unverified. The previously documented real-data, model calibration, stack/schema and G8–G9 limitations still apply.

## G8–G9 rehearsal and handoff (2026-10-09)

G8's local-only smoke and browser walkthrough were repeated twice. `verify_offline.py` checks the live app using only loopback requests: health and idempotent seed, borrower/loan/source provenance, deterministic cloned inputs, fixed baseline with changed heat-stage results, bridge-driven bank payment with informal debt, distinct interventions sharing comparison context, saved report and loan schedule, catalog presence, and explicit unavailable weather/satellite claims. The script rejects any non-loopback API URL and records each pass in `offline-smoke-pass-1.json` and `offline-smoke-pass-2.json`.

Two browser passes covered overview/watchlist, borrower registry, climate provenance, four-day heat and split payment, proposal eligibility, report controls, snapshot reopen and Farmer view. A representative screen is saved as `browser-g8-rehearsal.jpg`. The one-command launcher was started on alternate ports, health-checked, exercised with the two-pass smoke, and stopped through the owned-process stop script. `frontend-build.txt` and `backend-tests.txt` record the passing TypeScript/Vite build and 18/18 API/ledger checks.

G9 adds a reproducible single-command local launch, owned-process stop and deterministic fixture reseed; a saved judge scenario with browser load/reset controls; exact dependency pins; optional environment example; architecture sketch/project summary; source and claim audit; runbook; known limitations; and browser screenshots. The launcher was started on alternate ports, the fresh UI connected to its matching API, and the verification-owned services were stopped cleanly. External candidates CY-Bench, Open-Meteo and AGMARKNET remain named as unverified research leads only. No source observations, licences, file versions or hashes are claimed because none were retrieved. No video backup was recorded and rendered PDF remains unverified.

Ship checks completed: borrower select/search and loan records, input/status disclosure, backend recalculation, dated cash and bridge, simulated debt, distinct eligible actions, scenario-based exports, offline startup and two repetitions. Partial/open: mobile navigation acceptance, real-data/model validation, stack/schema alignment, PDF rendering, and event-permitted video. These gates therefore describe a runnable prototype, not full acceptance of every plan requirement.
