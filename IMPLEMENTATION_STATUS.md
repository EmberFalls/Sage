# Sage implementation status

Updated 2026-10-09 after G8–G9 offline rehearsal, submission readiness work, and full-plan F0 scope/source freeze.

## Gates

| Gate | Status | Evidence / outstanding scope |
|---|---|---|
| G0 | Core runtime verified; specification partial | Both servers boot, TypeScript/build passes, response envelope/schema saved, fixtures and ledger tests. Nested schema and prescribed stack incomplete. |
| G1 | Verified demo fallback | SQLite registry/detail/loan/sources; browser search/dossier/loan/climate. No real ingestion or URL routing. |
| G2 | Verified illustrative path; real-data requirement open | Eight inputs, dated stages/cash, Decimal money, simulation frequencies. No observed baseline/trained artifact. |
| G3 | Core demo verified | Backend heat/stage/price changes, fixed baseline, reconciled bridge, browser reset. Adversarial race/mobile acceptance not exercised. |
| G4 | Core demo verified | Bridge/total-debt divergence, three seasons, two proposals, both installments, H27/H28. Demo eligibility; chart acceptance partial. |
| G5 | Core workflow implemented | Saved snapshot catalog and exact reopen with date/irrigation preservation, warning drilldown, JSON/bridge CSV/print report, farmer summary. PDF rendering itself still needs a judge's-machine check. |
| G6 | Implemented; responsive browser checked | Consistent paise formatting, report/layout refinements, 390px view has no horizontal page overflow. No data-ready model or portfolio allocator added. |
| G7 | Rehearsal documented; offline path checked | Reproducible local run, 18 tests, build, live API evidence and judge flow in `demo/verification/REHEARSAL.md`. No video backup created. |
| G8 | Verified local offline flow | Loopback-only smoke passed twice; browser judge path completed twice; exact outputs and claim labels inspected. No external data service used. |
| G9 | Core runnable submission prepared | One-command PowerShell launch, owned-process stop, deterministic reseed, saved walkthrough load/reset, pinned dependencies, env example, source/claim audit, architecture summary, screenshots and known limits. No video backup; PDF render still open. |

Detailed evidence and limitations: [verification report](demo/verification/REPORT.md).

## Feature coverage

| Feature | State | Notes |
|---|---|---|
| H01 | Partial | Desktop shell/navigation inspected; no deep links/mobile check. |
| H02 | Verified demo | Source badges and explicit missing data. |
| H03 | Verified demo | DB registry search/dossier. |
| H04 | Verified demo | Loan events use selected snapshot. |
| H05 | Verified illustrative | Explicit inclusive local-date windows with calendar provenance, geography, version, uncertainty, and overlap flags. |
| H06 | Unavailable | NDVI/soil absent. |
| H07 | Conditional evidence + fallback | Pune ERA5 daily features align by date when geography and stage windows match; future observations are cut at `as_of`; otherwise missing. Forecast unavailable; hypothetical inputs remain separate. |
| H08 | Verified illustrative | Yield output is versioned `stage-response-v3`, labeled illustrative, `t/ha`, with limitations; no aligned real yield rows are admitted. |
| H09 | Verified simulation | 21 declared paths; uncalibrated feasibility frequency. |
| H10 | Verified demo | Dated ledger, actual-day interest, Decimal cents. |
| H11 | Verified core | Debounced backend requests; stale guards inspected. |
| H12 | Verified illustrative | Date-positioned heat event changes stage features and illustrative yield; API/UI baseline and changed-stage flow verified. |
| H13 | Verified simulated | Capped bridge draws and carried/repaid informal debt. |
| H14 | Verified simulated | Three-season cash/arrears; no duplicate principal. |
| H15 | Verified demo | Two different proposal schedules, costs/eligibility tests. |
| H16 | Verified demo | Lender and farmer view checked against the selected shared assessment. |
| H17 | Verified demo | Overview portfolio and watchlist checked against current scenario. |
| H18 | Core implemented | Immutable snapshot catalog/reopen restores inputs; JSON/CSV and print-to-PDF report. Print/PDF still needs rendered-output check. |
| H19–H26 | Not verified | No stretch-feature acceptance claim. |
| H27 | Verified core; layout partial | Shared context and financial resilience/cost/debt/payment comparison. |
| H28 | Verified core | Configured rule IDs, thresholds and exact simulated evidence. |
| H29 | Verified core | Accounting bridge reconciles to paise. |

## Full-plan continuation (F0)

F0 documentation deliverables are recorded in [`FULL_EXPANSION_STATUS.md`](FULL_EXPANSION_STATUS.md), [`docs/FIN03_SCOPE.md`](docs/FIN03_SCOPE.md), [`docs/SITEMAP.md`](docs/SITEMAP.md), [`DATA_SOURCES.md`](DATA_SOURCES.md), and [`data/frozen-baseline.yaml`](data/frozen-baseline.yaml). F0 is **PARTIAL**: a full Open-Meteo ERA5 historical weather archive is retained, but the required admitted and matched Pune maize yield/weather/NDVI/price geo-time join is not available. A Kharif 2015-16 yield row appears in a third-party mirror but remains unadmitted pending primary-source bytes, terms, and geography review. No external sample is wired into runtime scoring. See the full feature matrix for F01–F33 classifications and dependencies.

Post-hackathon phase status is recorded in [`docs/PHASE_F1_F4_IMPLEMENTATION.md`](docs/PHASE_F1_F4_IMPLEMENTATION.md). The F1–F3 branch does not include F4; its stage model and model training are deferred.

## Dated weather and crop stage issue

Implemented: `GET /api/crop-calendar`; calendar provenance and bounded windows; date-based hypothetical heat placement; ERA5 daily stage aggregates for overlapping Pune dates only; `as_of` cutoff; explicit missing geography/date states; versioned illustrative yield metadata. The default 2026 Nashik demo has no geography match for the Pune ERA5 grid, and its season also does not overlap the 2015 archive; both remain visibly missing. No historical yield baseline/model is available because aligned, admitted yield rows are absent. API suite: 20 tests pass. Frontend production build passes. Browser check: baseline flowering heat vs July 1 planting heat changed stage stress and projected yield (3.05 to 3.14 t/ha) through the UI.

## Limits

No admitted aligned yield/weather/market/repayment dataset. ERA5 features are conditionally aligned for matching Pune dates, but do not drive or calibrate the illustrative yield rule. Default 2026 scenarios have missing ERA5 date coverage. A three-row excerpt remains only as source-monitor outage fallback. Crop rules/calendar are illustrative. No real credit decision or restructuring. Existing stack uses custom CSS, sqlite3 and state navigation. Nested Pydantic objects remain dictionaries. PDF output and a video backup remain unverified/unavailable.
