# Full-product expansion status — F0 gate, F1–F4 and non-model operations

Updated 2026-10-09. This is an inventory against `Sage_FULL_Implementation_Plan_V2.md` Phase F0 and its F01–F33 acceptance matrix. The full-plan phase F0 is **PARTIAL**: scope, provenance, baseline and sitemap are documented, but the required matched real-source join has not been achieved. The hackathon implementation and its G0–G9 status remain separately recorded in `IMPLEMENTATION_STATUS.md`.


## F0 gate

| Deliverable | State | Evidence / gap |
|---|---|---|
| Frozen FIN-03 checklist | Done | `docs/FIN03_SCOPE.md` |
| Single India crop-region-season | Target frozen | Pune, Maharashtra maize Kharif 2015; target only, not matched real coverage |
| Source manifest and provenance | Done for known evidence; partial corpus | `data/manifest.yaml`, `DATA_SOURCES.md`; full ERA5 weather archive retained; other sources honestly marked uninspected/unavailable |
| Baseline/version freeze | Done | `data/frozen-baseline.yaml`; cross-version identity still unverified |
| No-auth proof or fallback | **Complete for weather** | Anonymous 153-day ERA5 response and checksum retained; unrelated yield, NDVI and price sources remain unavailable/unadmitted |
| Assumptions/limitations | Done | `docs/FIN03_SCOPE.md` and `DATA_SOURCES.md` |
| UI sitemap | Done | `docs/SITEMAP.md`, reconciled against app navigation |
| Real matched geo/time sample join | **Blocked** | Only grid-cell weather rows; no aligned yield, NDVI, price. Do not claim F0 data gate passed. |

## Phase delivery record

The phase names F1–F4 below are the development phases in section 11 of the full plan; they are distinct from the feature IDs F01–F33 in the feature matrix.

| Phase | Current outcome | Delivered | Gate still open |
|---|---|---|---|
| F1 design system and navigable app scaffold | **DEMO_ONLY — acceptance passed** | URL-addressable lender routes and borrower deep links, separate demo farmer shell/routes, explicit unavailable routes, responsive/shared theme; lender/farmer route sweep, browser back/forward, mobile drawer, and 390px overflow check passed on 2026-10-09. | Farmer routes are not private or authenticated; final frontend revamp remains last by request. |
| F2 persistence and borrower/loan operations | **DEMO_ONLY — acceptance passed** | Isolated-database acceptance passed on 2026-10-09 for borrower/draft creation, full valid review transitions, assessment, approve/reject outcomes, synthetic loan/schedule, repayment balance reconciliation, idempotent replay, and invalid-transition/principal-mutation rejection. | No lender roles or bank posting; all operations and ledger data remain synthetic. |
| F3 data adapters and feature snapshots | **WEATHER ADMISSION COMPLETE; yield source admission BLOCKED** | Full 153-day ERA5 response retained and schema-validated; immutable SQLite snapshot/cache fallback, persistent refresh history, strict normalized CY-Bench pilot intake, streaming local ZIP subset loader requiring explicit Pune admin crosswalk/yield unit, source monitor UI, and VDSA/NSS calibration limits memo. A Kharif 2015 Pune maize yield candidate (852 kg/ha) was found in a third-party mirror and logged with its limitations. | Primary yield report bytes/checksum and reuse terms remain unverified; district boundary-to-grid crosswalk is absent. Crop calendar, NDVI, soil, and AGMARKNET rows remain unverified. Imports remain excluded from scoring. |
| F4 agronomic stage model and yield projection | **DEFERRED — not part of this push** | No F4 model or agronomic stage implementation is included in the F1–F3 branch. | Training and F4 implementation remain future work after the source gate and model data are ready. |

Implementation details and API routes are recorded in [`docs/PHASE_F1_F4_IMPLEMENTATION.md`](docs/PHASE_F1_F4_IMPLEMENTATION.md). F1/F2 acceptance is complete for the explicitly synthetic demo scope; that does not make the product production-ready. F3's reusable software path is implemented, but external source admission and a valid matched join are blocked on source artifacts and review. F4 remains blocked on its historical-model gate.

## Feature inventory

`ALREADY_VERIFIED` means full-plan acceptance has evidence; `UPGRADE_REQUIRED` means some hackathon/demo behavior exists but full-plan acceptance is not proven; `NEW` means the full behavior is not present; `BLOCKED_REAL_DATA` means empirical/source-dependent acceptance lacks data; `DEFERRED` means explicitly postponed. A file or UI card alone never earns `ALREADY_VERIFIED`.

| ID | Feature | F0 classification | Existing evidence / remaining work |
|---|---|---|---|
| F01 | Landing and demo onboarding | NEW | Current shell opens overview; no onboarding/enter-demo landing. |
| F02 | Full route/navigation structure | DEMO_ONLY | Lender/farmer URLs and borrower deep links, route coverage, history navigation, accessible responsive drawer verified; no auth or private farmer boundary. |
| F03 | Borrower registry CRUD/filter | DEMO_ONLY | Synthetic create/edit and borrower dossier are implemented; production identity and authorization are absent. |
| F04 | Loan application and review | DEMO_ONLY | Persistent synthetic draft/review transitions and approve/reject paths accepted; no real lending decision or sanction. |
| F05 | Loan schedule/ledger | DEMO_ONLY | Synthetic schedule and append-only repayment events with balance reconciliation and idempotency accepted; no bank posting. |
| F06 | Portfolio dashboard | UPGRADE_REQUIRED | Demo overview/watchlist; full filters and borrower drilldown acceptance remain. |
| F07 | Crop/crop stages | UPGRADE_REQUIRED | Illustrative stages exist; regionally sourced calendar and lifecycle not established. |
| F08 | Satellite vegetation history | BLOCKED_REAL_DATA | NDVI unavailable; no source-backed observation or quality/resolution evidence. |
| F09 | Weather and forecast | UPGRADE_REQUIRED | Scenario assumptions and historical sample; no operational forecast issue/valid time pipeline. |
| F10 | Soil and irrigation | BLOCKED_REAL_DATA | Irrigation assumption exists; soil source/observation absent. |
| F11 | Historical yield model | BLOCKED_REAL_DATA | Illustrative rule only; no matched yield corpus/model evaluation. |
| F12 | Market price signal | BLOCKED_REAL_DATA | Assumed price only; no verified Pune maize dated market rows. |
| F13 | Credit history | UPGRADE_REQUIRED | Synthetic history exists; real evidence intentionally absent. |
| F14 | Dynamic credit risk estimate | BLOCKED_REAL_DATA | Demo simulation exists; real probability/validation is impossible without permissioned linked outcomes. Keep simulation semantics. |
| F15 | Driver explanations | UPGRADE_REQUIRED | Demo rule/formula explanations exist; source/date/computation lineage must be expanded. |
| F16 | Stress-at-Due | UPGRADE_REQUIRED | Core dated cash demo exists; source-backed crop-stage and full acceptance not established. |
| F17 | Formal vs sustainable repayment | UPGRADE_REQUIRED | Simulated debt-cycle distinction exists; lifecycle/claim checks remain. |
| F18 | Multi-season debt-cycle | UPGRADE_REQUIRED | Three-season demo exists; richer invariants and acceptance remain. |
| F19 | Scenario Lab | UPGRADE_REQUIRED | Hackathon comparator exists; full route/deep links and source snapshot contracts remain. |
| F20 | Borrower intervention engine | UPGRADE_REQUIRED | Two simulated proposals exist; eligibility/cost/lifecycle completeness remains. |
| F21 | Budget allocator | UPGRADE_REQUIRED | No allocator implementation is included in the F1–F3 branch. |
| F22 | Watchlist and alert actions | UPGRADE_REQUIRED | Simulated warnings exist; saved acknowledge/assign/resolve lifecycle is not included in the F1–F3 branch. |
| F23 | Farmer portal | UPGRADE_REQUIRED | Demo farmer view exists; identity isolation, permissions and complete workflow absent. |
| F24 | Export/report | UPGRADE_REQUIRED | JSON/CSV/print report exists; rendered PDF and full source lineage acceptance open. |
| F25 | Source/data-quality dashboard | UPGRADE_REQUIRED | Methodology/source badges exist; freshness/cache monitor and source browser absent. |
| F26 | RBAC/audit | NEW | No authenticated roles, branch isolation, or access audit. |
| F27 | Uncertainty and deferral | UPGRADE_REQUIRED | Explicit demo assumption/missing labels exist; calibrated intervals unavailable and must remain deferred. |
| F28 | Responsive polished design | UPGRADE_REQUIRED | Hackathon UI and 390px overflow check exist; full route/keyboard review not evidenced. |
| F29 | Help and methodology | UPGRADE_REQUIRED | Methodology panel exists; complete help/role-specific explanations remain. |
| F30 | Saved assessments/scenario histories | UPGRADE_REQUIRED | Snapshot catalog/reopen exists; immutable source/data/model replay guarantees remain. |
| F31 | Frozen-context three-way workbench | UPGRADE_REQUIRED | H27 comparator exists; multi-candidate full lifecycle and version contract remain. |
| F32 | Debt warning/action queue | UPGRADE_REQUIRED | Rule-derived warnings exist; persistent action lifecycle is not included in the F1–F3 branch. |
| F33 | Cash/repayment impact decomposition | UPGRADE_REQUIRED | H29 bridge exists; exact source/date/event drill-through and full acceptance remain. |

F1–F3 work is scoped to a feature branch. F4 model training and later-phase operational features are not included in that branch.

## Dependency and issue ordering recommendation

1. **F0 data gate / F3 adapters** — first resolve sample retention/checksum, CY-Bench archive subset and Pune maize source join; add explicit unavailable fallbacks. Don't begin a yield-model claim while this remains blocked.
2. **F1 app scaffold + F2 operations** — establish stable routes and persistence/application/loan workflows before adding more feature pages.
3. **F3 source and provenance layer** — source snapshots, normalized schema, cache/fallback and honest source badges underpin F07–F12 and future model inputs.
4. **F4 agronomy/yield then F5 finance/risk** — add staged crop response and dated cash/credit only after source admission; preserve synthetic-only risk semantics in the absence of real outcomes.
5. **F6 scenarios → F7 debt cycle → F8 interventions** — preserve shared assessment engine and complete actions against the same frozen context before portfolio workflow.
6. **F9 portfolio operations → F10 farmer/report/design polish** — do operational and privacy-dependent behavior before the final frontend revamp.
7. **F11 empirical/pilot readiness** — optional and explicitly last; blocked on permissioned outcomes for real repayment modeling.

The final frontend revamp should remain the last issue as requested. Avoid making isolated visual changes that preempt its acceptance scope, while permitting minimal UI integration necessary to prove the earlier backend/data features end to end.
