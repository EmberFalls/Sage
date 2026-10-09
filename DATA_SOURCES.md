# Data sources, provenance and claim audit

Audit state: 2026-10-09. F0 captured a small, anonymous Open-Meteo historical-weather response excerpt for a declared Pune maize Kharif 2015 feasibility target. The excerpt is **not** wired into the assessment runtime and does not make the target a matched real-data season. The existing offline demo remains seeded and synthetic/illustrative.

## Pilot scope decision

Use **maize — Pune district, Maharashtra — Kharif 2015** as the single F0 feasibility target. It aligns with the repository's existing Pune maize demo geography/crop for UX continuity and gives a fixed historical period for weather and other source checks. It does **not** imply that the demo record or 2015 weather belongs to a real borrower. Geography representations are not interchangeable: the retained weather is a gridded reanalysis point near Pune, not district yield, field weather, or a farm observation.

| Data class | Runtime status | Version / evidence | Permitted claim |
|---|---|---|---|
| Borrower, loan, expenses, repayment | Synthetic | Fixture `demo-fixture-2026-10-09.2`, seed `20261009`, [`fixtures.py`](backend/app/services/fixtures.py) | Synthetic example only; no real borrower, contract, or bank outcome |
| Weather used by assessment | Assumed | `scenario-controls-v1`; no runtime external calls | Hypothetical rainfall/heat scenario only |
| Open-Meteo historical weather | Raw sample excerpt verified; not runtime-ingested | Three rows retained in `data/raw/open_meteo/pune_kharif_2015_sample.json`; query and response grid coordinates in [`manifest.yaml`](data/manifest.yaml) | The sample contains historical gridded reanalysis values, not station/field observations or forecast. Do not use as model evidence until the full response and season join are validated. |
| Crop calendar and stage response | Assumed | `illustrative-v2`; fixture dates/rules | Illustrative crop-stage sensitivity only |
| Irrigation | Assumed | Fixture/default or scenario override | Scenario input only |
| Yield | Assumed | Rule response; no fitted artifact/evaluation set | Illustrative yield estimate; not trained or calibrated |
| Market price | Assumed | User input/local reference fixture; no verified mandi observation | Hypothetical price change only |
| NDVI / satellite | Unavailable | No source-backed rows retained | No vegetation observation or satellite insight claim |
| Soil moisture | Unavailable in app | No source-backed rows retained | No soil observation claim; reanalysis variables are not currently ingested |
| Credit performance / repayment frequency | Synthetic / simulated | 21 declared hypothetical paths; no labeled real outcomes | Simulation-conditioned frequency only; not default probability or accuracy |

## External source review

| Candidate | F0 status | Direct source, version and local evidence | Licence / access / limits |
|---|---|---|---|
| Open-Meteo Historical API | **No-auth access verified; sample excerpt retained; full season not ingested** | [Historical API docs](https://open-meteo.com/en/docs/historical-weather-api); request details and three sample days in `data/raw/open_meteo/pune_kharif_2015_sample.json`; excerpt SHA-256 `D239158776E1277E2370E40DEDC96B25167AB4D41FC4CE0A13E55C6958E39ADD`; query lat/lon 18.5204, 73.8567; returned grid 18.523726, 73.86876, elevation 561m; daily period 2015-06-01—2015-10-31 requested | Data CC BY 4.0 with attribution. Free API is non-commercial only. Reanalysis is not operational forecast or farm-level measurement. Check [current terms](https://open-meteo.com/en/terms) before any non-demo/commercial usage. |
| CY-Bench | **Record metadata reviewed; multi-GB archive and India rows uninspected; not used** | [Zenodo record 13838912](https://zenodo.org/records/13838912), record version 1.2. Metadata lists archives including a ~12.65 GB data zip; no Pune maize rows, key, or file hash established. | License was not verifiable from the rendered record; inspect record metadata and included files directly before use/redistribution. No data coverage claim from repository URL alone. |
| AGMARKNET | **Portal identified; anonymous endpoint and price rows unverified** | [Official portal](https://agmarknet.gov.in/home); no local extract | No price, commodity mapping, date coverage, API access, or redistribution claim until raw rows and terms are checked. |
| Open-Meteo forecast / seasonal forecast | **Not part of the F0 pilot evidence** | Candidate endpoints only; no forecast response/cache | Forecasts need issue time, valid time, horizon and ensemble/member metadata; historical reanalysis cannot substitute for a forecast. |
| Earth Search / Sentinel-2 | **Not retrieved** | Candidate only | No NDVI/crop-condition claim; verify actual item/assets, cloud quality, spatial resolution and terms before use. |
| VDSA / NSS | **Not ingested for this pilot** | Candidates listed in the full plan | Household/aggregate socioeconomic sources do not establish linked bank repayment or default labels. |

## Baseline versioning (frozen F0 reference)

- Offline data fixture: `demo-fixture-2026-10-09.2`.
- Assessment engine: `risk-engine-v2-demo.2`.
- Crop response/calendar: `illustrative-v2`.
- Demo seed: `20261009`.
- Warning rules: `backend/app/config/warnings.json` (version is not self-declared today; add explicit rule version before changing thresholds).
- Manifest: `data/manifest.yaml` version 2.

Keep the existing deterministic offline walk-through. A source/model/rule change must receive a new version and document its effect; don't overwrite an old result or imply old snapshots are reproducible with new versions. This freeze records current version strings, not proof of cross-version regression equivalence.

## Data quality and upgrade thresholds

1. **Source admission (F3):** retain actual source bytes/response, retrieval time, direct URL, applicable licence/terms, SHA-256, schema, units, source version, spatial/temporal resolution and attribution. A URL or metadata page alone is insufficient.
2. **Pune maize season join (F3):** include a row only when crop definition, district/geographic key, season/year, dates, and units are explicit. Do not infer farm-scale values from district/grid. Maintain source IDs and tolerances; no nearest-date joins without a declared tolerance.
3. **Minimum real agronomy coverage before F4:** the chosen pilot must have at least one inspectable historical yield row for Pune (or an explicitly documented district boundary crosswalk) for maize with unit/year, and dated weather over the same declared season. NDVI and price remain separately `missing`/`assumed` until their own dated, aligned rows and quality/units are validated. This minimum enables exploratory integration only, not model validation.
4. **Yield-model upgrade:** require multiple years and a time-ordered holdout before claiming out-of-time evaluation; report sample counts, baseline, units, split years, missingness and geography. If sample size or matching is inadequate, retain the rule-based illustrative response.
5. **Credit model:** no real-world default/repayment performance claim without properly permissioned, linked historical loan outcomes and independent temporal/geographic validation. Generated loans only support simulation-conditional outputs.
6. **Runtime use:** only wire an external source after cache/fallback, source freshness and missing-data state have been exercised; preserve the offline fixture and include source/model versions in saved outputs.

## Claim audit

- Allowed: synthetic demo borrowers; assumed/hypothetical crop, weather, irrigation, yield and price; simulated debt cycle; the retained weather excerpt is a real historical reanalysis sample at a grid location; NDVI/soil unavailable in runtime.
- Not allowed: live weather; observed crop stress; real borrower repayment behavior; farm-specific weather from this grid; satellite-derived condition; trained yield model; calibrated default probability; detected hidden debt; approved restructuring; live market price; matched Pune maize yield-weather-NDVI-price coverage.

Use `SOURCE_OBSERVED`, `SOURCE_FORECAST`, `MODEL_PREDICTED_YIELD`, `MODEL_SCENARIO_SHORTFALL`, `SIMULATED_CREDIT_OUTCOME`, `ASSUMED_INTERVENTION_EFFECT`, or `HUMAN_ENTERED` for new numerical assertions. Weather rows above are reanalysis (`SOURCE_OBSERVED` only in the broad historical-source sense; always display the more precise *gridded reanalysis* label), never a station observation.
