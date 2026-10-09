# F1–F4 implementation record

Updated 2026-10-09. These are the phase names from section 11 of the full product plan. This record distinguishes code delivered from source-data and release gates that remain open.

## F1 — Design system and navigable app scaffold

**Outcome: DEMO_ONLY.** The React app now resolves URL paths for the lender workspace, borrower details, application review, data sources, reports, help, and the separate farmer demo shell. Browser back/forward updates the page, borrower details have stable borrower IDs in the URL, and loan pages preserve borrower selection. Routes with no authenticated settings behavior say “Not implemented” instead of presenting a working-looking dead link. Existing shared theme, typography, demo labeling, responsive sidebar, empty states, and loading/error feedback remain in use.

Farmer demo routes: `/farmer/home`, `/farmer/my-farm`, `/farmer/my-loan`, `/farmer/outlook`, `/farmer/options`, `/farmer/help`. They deliberately state that there is no authentication or private identity boundary. They are not real role-based access control. Acceptance on 2026-10-09 covered all lender and farmer routes, borrower deep links, in-app navigation, browser back/forward, the mobile drawer at 390px, and no horizontal overflow at that viewport. The drawer's open and close controls have accessible names.

## F2 — Persistence and borrower/loan application operations

**Outcome: DEMO_ONLY.** SQLite schema migration 2 adds durable application records and source snapshots while preserving existing borrowers, loans, and scenario snapshots. The borrower registry can create and edit synthetic profiles. The application queue supports the recorded transition path `draft → assessed → referred_to_officer → under_review → reviewed → approved_in_demo | rejected_in_demo`; invalid transitions return HTTP 409. Assessment uses the requested amount as an explicit frozen loan-principal override. Approval atomically records the demo decision, updates the synthetic borrower principal, and creates a synthetic loan. Demo repayment events append to the loan record with event IDs and principal-only reconciliation metadata.

API contracts:

- `POST /api/borrowers`, `PUT /api/borrowers/{borrower_id}`, `GET /api/borrowers`
- `POST /api/applications`, `GET /api/applications`, `PATCH /api/applications/{application_id}/status`
- `GET /api/loans`, `GET /api/borrowers/{borrower_id}/loan`, `POST /api/loans/{loan_id}/events`

The stored ledger remains synthetic. An application “approval” is a local workflow simulation, not a sanction, payment, or bank posting. The workflow has not been promoted to authenticated lender operations. Acceptance on 2026-10-09 passed against a temporary isolated SQLite database: borrower and draft creation, every valid review transition, frozen assessment, approval and synthetic loan/schedule creation, repayment reconciliation with idempotent event replay, invalid-transition rejection, principal immutability, and rejection without loan creation. The ordinary demo database was not modified by this acceptance run.

## F3 — Data adapters and feature snapshots

**Outcome: weather source gate passed; crop/yield join gate BLOCKED.** The repository now retains the full Open-Meteo ERA5 historical response for 2015-06-01 through 2015-10-31 with a verified SHA-256. ERA5 is pinned because ERA5-Land does not provide precipitation. An explicit refresh validates the exact 153-day sequence, units and non-null values, stores exact response text and retrieval metadata in an immutable SQLite snapshot, and records every attempt. On outage it prefers a prior verified complete archive, otherwise uses the checksum-verified three-row excerpt. Full-window status is never inferred from row count. This is a roughly 25 km grid cell, not district or farm weather; source snapshots are not inputs to the assessment engine.

The normalized import path rejects incomplete CY-Bench pilot windows, malformed source file hashes, duplicates, invalid units/ranges and missing crop/geography keys. `backend/import_cybench_subset.py` streams only the India maize yield and weather CSV members from a local v1.10 archive, selects 2015 using an explicit reviewed admin crosswalk, requires an explicitly confirmed yield unit, and freezes source-member and normalized-payload hashes. Calendar exports have an explicit static-primary-season representation with validated start/end day-of-year values; the registry identifies the official WorldCereal candidate. The source monitor reports refresh history and diagnostic candidate status. These controls do not validate upstream identity, licenses, administrative boundary equivalence or scientific representativeness. The 6.2 GB CY-Bench archive has not been downloaded/inspected. A Kharif 2015 Pune maize row (852 kg/ha) is transcribed from a third-party mirror attributed to Maharashtra Agriculture Department, but primary report bytes, reuse terms and a district-to-weather-grid crosswalk remain unresolved; it is recorded but not admitted. No WorldCereal calendar extraction, NDVI, soil or AGMARKNET price rows are admitted. The weather point is grid-cell reanalysis, not district/farm/station weather. Crop-stage dates in F4 remain illustrative until a source-backed crop calendar is admitted. VDSA/NSS candidate-use and calibration limits are documented in `docs/F3_CALIBRATION_SOURCE_REVIEW.md`.

API contracts: `GET /api/data-sources`, `POST /api/data-sources/open-meteo/refresh`, `POST /api/data-sources/import`, `GET /api/source-refreshes`, `GET /api/source-snapshots?source_id=...`, and `GET /api/source-snapshots/{snapshot_id}/content`. The provider-export intake validates normalized CY-Bench, AGMARKNET, NDVI and soil rows and stores immutable normalized bytes/hash; its status is pending human source admission and it never feeds scoring automatically.

## F4 — Agronomic stage model and yield projection

**Outcome: deferred and not included in the F1–F3 branch.** F4 agronomic stage modeling and yield projection will be implemented later, after source data are ready. Model training and validation are explicitly deferred.

No F4-specific API or trained model is included in this branch. Until F4 is implemented and validated, existing yield outputs remain illustrative and must not be represented as calibrated predictions.

## Release and acceptance evidence

F1 and F2 acceptance for their **demo scope** is recorded above. This does not make farmer identity private, provide lender roles, or make loan decisions or postings real. F3 source outage/refresh and F4 historical-model/date-alignment gates remain separate; do not promote them to complete without their corresponding evidence and admitted data. No authentication, live lending decision, or real agricultural model is introduced here.
