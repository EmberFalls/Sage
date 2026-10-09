# Existing app sitemap at F0 freeze

This records actual destinations found in `frontend/src/App.tsx`; it does not claim deep-link routing or production permissions. Navigation is local React state and the app has a mobile drawer. The full-product roadmap is aspirational; each unimplemented destination must be shown as unavailable or explicitly deferred when introduced.

| Navigation group | Destination | Current behavior | F roadmap |
|---|---|---|---|
| Workspace | Overview | Demo portfolio and current assessment summary | F06 |
| Workspace | Borrowers | Search/filter synthetic borrower list; opens selected borrower detail | F03 |
| Workspace | Borrower detail | Loan-linked demo dossier | F03 |
| Workspace | Loans | Demo loan records for selected borrower | F05 |
| Intelligence | Climate intelligence | Assumed/scenario climate, crop stage and climate fixture panels | F07–F10 |
| Intelligence | Credit assessment | Current server-calculated illustrative assessment and FIN-03 input status | F13–F15 |
| Intelligence | Scenario lab | Climate/price/irrigation/bridge assumptions, baseline/stress/action comparison | F16, F19, F31–F33 |
| Decisions | Intervention center | Simulated proposal selection and comparison; no bank term mutation | F20 |
| Decisions | Watchlist & reports | Rule-derived simulated warnings, JSON/CSV, print, saved snapshots | F22, F24, F30, F32 |
| Sidebar bottom | Farmer view | Simplified synthetic borrower and scenario summary | F23 |
| Sidebar bottom | Data & methodology | Calculation walkthrough, source classes and claim limits | F25, F29 |

## Known navigation gaps at freeze

- No URL/deep-link route structure or landing/demo onboarding route (F01–F02 remain work).
- No create/edit borrower, application wizard/review, branch assignments, operational alert state, portfolio allocator or role-based access controls (F03–F04, F21–F22, F26 remain incomplete).
- “Climate intelligence” is not a real-source data browser and does not establish NDVI/soil/forecast availability (F08–F10/F25 remain incomplete).
- Existing routes are a hackathon demo shell, not completed full-product pages. See `FULL_EXPANSION_STATUS.md` for per-feature classification.
