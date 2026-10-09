# Data sources, provenance and claim audit

Audit state: 2026-10-09. **No external data files have been downloaded or ingested.** Therefore there are no retrieved URLs, source dates, licence decisions, immutable versions, or file hashes to claim for external observations. The candidate names below are research leads from the implementation plan, not dependencies or evidence in the running demo.

| Input | Runtime status | Evidence/version | Claim allowed in this demo |
|---|---|---|---|
| Borrower, loan, expenses, repayment | Synthetic | Deterministic local fixture `demo-fixture-2026-10-09.2`; not a real dataset | Synthetic example only; not an observed borrower or repayment outcome |
| Weather | Assumed | Local slider scenario `scenario-controls-v1`; no forecast issue time or observation file | Hypothetical rainfall/heat stress only |
| Crop calendar and stage response | Assumed | Local rules `illustrative-v2`; no validated regional calendar source | Illustrative crop-stage sensitivity only |
| Irrigation | Assumed | Borrower fixture/default or explicit scenario override | Scenario input only |
| Yield | Assumed | Rule response; no fitted artifact or evaluation dataset | Illustrative yield estimate; not trained or calibrated |
| Market price | Assumed | User input and local reference fixture; no mandi observation | Hypothetical price change only |
| NDVI / satellite | Unavailable | API returns null and status `unavailable` | No vegetation observation or satellite insight claim |
| Soil moisture | Unavailable | API returns null and status `unavailable` | No soil observation claim |
| Credit performance / repayment frequency | Synthetic / simulated | 21 declared hypothetical paths; no labeled outcomes | Simulation-conditioned frequency only; not default probability or accuracy |

## External source candidates — not retrieved

| Candidate | Status in this repository | URL/version/hash | Licence and terms |
|---|---|---|---|
| CY-Bench | Named in the hackathon plan; no files used | Not retrieved; no version or hash | Not reviewed; do not redistribute/use until verified |
| Open-Meteo | Named in the hackathon plan; no API called or cache used | Not retrieved; no request or response date | Not reviewed for this project; no runtime dependence |
| AGMARKNET | Named in the hackathon plan; no price observations used | Not retrieved; no version or hash | Not reviewed; no runtime dependence |

## Claim audit

- UI/API may say: synthetic borrowers; assumed/hypothetical weather, crop calendar, irrigation, yield and price; simulated debt cycle; unavailable NDVI and soil; offline demo fixture.
- UI/API must not say: live weather, observed crop stress, real borrower repayment behavior, satellite-derived condition, trained yield model, calibrated default probability, detected hidden debt, approved restructuring, or live market price.
- No claim of data licensing, external source freshness, accuracy, validation, or coverage is made.

When a real source is added, record its direct URL, retrieval timestamp, immutable version or response parameters, crop/region/time coverage, licence/terms, SHA-256 for cached files, and whether a field is observed, forecast, assumption or derived. Keep raw snapshots and calculations separately so provenance remains auditable.
