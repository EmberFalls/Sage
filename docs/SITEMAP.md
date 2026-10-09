# Application sitemap

This records the URL-addressable destinations currently wired in `frontend/src/App.tsx`. The farmer shell is a public synthetic demo view, not a private or authenticated role. Routes shown as unavailable are explicit placeholders.

| Navigation group | Route | Destination | Current behavior | F roadmap |
|---|---|---|---|
| Home | `/` | Landing and demo onboarding | Landing page with path to the workspace | F1 |
| Workspace | `/app/overview` | Overview | Demo portfolio and current assessment summary | F1/F06 |
| Lending | `/app/borrowers`, `/app/borrowers/:id` | Borrower registry and profile | Search, create/edit synthetic profile, loan-linked dossier | F2/F03 |
| Lending | `/app/applications` | Applications | Persistent application draft, assessment, review, demo decision | F2/F04 |
| Lending | `/app/loans?borrower_id=...` | Loans & repayments | Scenario schedule and synthetic repayment event ledger | F2/F05 |
| Intelligence | `/app/climate` | Climate intelligence | Assumed/scenario climate and source status | F3/F07–F10 |
| Intelligence | `/app/assessments` | Credit assessment | Server-calculated illustrative assessment and FIN-03 input status | F13–F15 |
| Intelligence | `/app/scenarios` | Scenario lab | Climate/price/irrigation/bridge assumptions, baseline/stress/action | F16/F19/F31–F33 |
| Decisions | `/app/interventions` | Intervention center | Simulated proposal selection and comparison; no bank term mutation | F20 |
| Decisions | `/app/watchlist` | Watchlist & alerts | Rule-derived simulated warnings and snapshots | F22/F32 |
| Operations | `/app/allocator` | Portfolio allocator | Budget-bounded, persisted synthetic support allocation with explicit priority policy | Feature F21 / phase F9 |
| Operations | `/app/reports` | Reports & audit | JSON/CSV/print and saved snapshots | F24/F30 |
| Operations | `/app/data-sources` | Data sources | Provider state, validated JSON import, snapshot hashes, fallback and source limitations | F3/F25 |
| Operations | `/app/settings` | Settings | Explicit “not implemented” state; no auth or role management | F1/F26 |
| Farmer shell | `/farmer/home`, `/farmer/my-farm`, `/farmer/my-loan`, `/farmer/outlook`, `/farmer/options`, `/farmer/help` | Farmer demo | Separate simplified synthetic demo shell; no private access boundary | F1/F23 |
| Help | `/app/help` | Data & methodology | Calculation walkthrough, source classes and claim limits | F1/F29 |

## Remaining route and workflow gaps

- Farmer routes do not authenticate or isolate identity; no real RBAC is implemented.
- Settings, branch assignments, and a full authenticated application workflow remain incomplete (F21–F22/F26). The allocator and warning lifecycle are available as unauthenticated demo workflows only.
- The weather snapshot browser does not connect sources to scoring and does not establish NDVI/soil/price/yield availability or a matched Pune maize dataset (F08–F12/F25).
- See [`FULL_EXPANSION_STATUS.md`](../FULL_EXPANSION_STATUS.md) and [`PHASE_F1_F4_IMPLEMENTATION.md`](PHASE_F1_F4_IMPLEMENTATION.md) for completion gates.
