# Data sources, provenance and claim audit

Audit state: 2026-10-09. F3 retains the full Open-Meteo ERA5 daily response for 2015-06-01 through 2015-10-31. F4 verifies its checksum and schema, aligns complete stage windows to local dates, applies the five-day ERA5 publication delay for historical as-of replay, and uses eligible features in a versioned illustrative yield response. It is a roughly 25 km grid cell, not a farm observation or crop-yield join. The seeded borrower, crop calendar, and response rule remain synthetic/illustrative.

## Pilot scope decision

Use **maize — Pune district, Maharashtra — Kharif 2015** as the single F0 feasibility target. It aligns with the repository's existing Pune maize demo geography/crop for UX continuity and gives a fixed historical period for weather and other source checks. It does **not** imply that the demo record or 2015 weather belongs to a real borrower. Geography representations are not interchangeable: the retained weather is a gridded reanalysis point near Pune, not district yield, field weather, or a farm observation.

| Data class | Runtime status | Version / evidence | Permitted claim |
|---|---|---|---|
| Borrower, loan, expenses, repayment | Synthetic | Fixture `demo-fixture-2026-10-09.2`, seed `20261009`, [`fixtures.py`](backend/app/services/fixtures.py) | Synthetic example only; no real borrower, contract, or bank outcome |
| Weather used by assessment | Hypothetical input, distinct from evidence | `scenario-controls-v1`; no operational forecast connected | Scenario input only; no issued time or forecast claim |
| Open-Meteo historical weather | Checksum-verified stage features used when geography, dates, complete coverage, and as-of availability match | 153 ERA5 daily rows retained in `data/raw/open_meteo/pune_kharif_2015_era5.json`; response hash and grid coordinates in [`manifest.yaml`](data/manifest.yaml) | Five-day publication delay is applied. Grid values are not farm/station observations and are not a yield-training join. |
| Crop calendar and stage response | Assumed, versioned rule used by assessment | `illustrative-stage-calendar-v4` partitions inclusive season dates; `stage-response-v4` uses eligible reanalysis and separate hypothetical inputs | Not a region-verified crop calendar or calibrated crop response. Rainfall reference, heat threshold, and response coefficients are explicit demonstration assumptions. |
| Irrigation | Assumed | Fixture/default or scenario override | Scenario input only |
| Yield | Assumed | Rule response; no fitted artifact/evaluation set | Illustrative yield estimate; not trained or calibrated |
| Market price | Assumed | User input/local reference fixture; no verified mandi observation | Hypothetical price change only |
| NDVI / satellite | Unavailable | No source-backed rows retained | No vegetation observation or satellite insight claim |
| Soil moisture | Unavailable in app | No source-backed rows retained | No soil observation claim; retained weather archive does not contain the soil input used by the app |
| Credit performance / repayment frequency | Synthetic / simulated | 21 declared hypothetical paths; no labeled real outcomes | Simulation-conditioned frequency only; not default probability or accuracy |

## External source review

| Candidate | F0 status | Direct source, version and local evidence | Licence / access / limits |
|---|---|---|---|
| Open-Meteo Historical API | **Full no-auth ERA5 response retained and schema-validated** | [Historical API docs](https://open-meteo.com/en/docs/historical-weather-api); exact 153-day response in `data/raw/open_meteo/pune_kharif_2015_era5.json`; SHA-256 `5B1CBCFC830C3FBDD67C53A76AB7E220A88C23D56177DF10B7AED1C40E495F9E`; request 18.5204, 73.8567; returned grid 18.5, 73.75, elevation 561m; daily period 2015-06-01—2015-10-31; model pinned to ERA5 because ERA5-Land does not provide precipitation | Data CC BY 4.0 with attribution. Free API is non-commercial only. ERA5 at about 25 km is reanalysis, not operational forecast, district average, station or farm measurement. Check [current terms](https://open-meteo.com/en/terms) before any non-demo/commercial usage. |
| NABARD Pune PLP 2019-20 | **Annual candidate only; not admitted** | [District report](https://www.nabard.org/auth/writereaddata/tender/1710180622Pune%20PLP%202019-20.pdf), page 10; local review-copy SHA-256 `693A6C7D082C3C761787CE0016301DA3DCBC61C57DD76E7D97C0FB481E235C2C`; candidate extraction at `data/raw/agriculture/pune_maize_2015_16_candidate.json` | Reports Pune maize 2015-16 area (313 × 100 ha), production (794 × 100 MT), and annual district rainfall (666.4 mm); derived annual yield 2.537 t/ha. Not a Kharif-specific yield. Reuse terms and boundary vintage/crosswalk are unverified. Local report PDF is a review copy and is not included in the repository. No assessment use. |
| Maharashtra district APY 2015-16 | **Season-specific row found in a third-party mirror; not admitted** | [Scribd mirror](https://www.scribd.com/document/1004670718/DISTRICTWISE-APY-2015-16), Pune row in the Kharif maize table; candidate transcription at `data/raw/agriculture/pune_maize_2015_16_candidate.json` | Mirror attributes the report to Maharashtra Agriculture Department and shows Pune Kharif maize yield 852 kg/ha (area 32 × 100 ha; production 27 × 100 tonnes). The primary report bytes/checksum were not obtained; the mirror says “All Rights Reserved”; boundary-to-grid crosswalk is absent. Candidate only, no assessment use. |
| CY-Bench | **Current metadata reviewed; archive and India rows still uninspected; not used** | [Zenodo record 17279151](https://zenodo.org/records/17279151), version 1.10; current archive is about 6.2 GB. The [official project repository](https://github.com/WUR-AI/AgML-CY-Bench) describes subnational yield and predictor data; the precise Pune row, admin ID, yield unit and source component terms remain unverified. | Do not infer Pune coverage from India coverage. Inspect the actual data files and component-source attribution/terms before admission or redistribution. The optional CLI streams only two CSV members and requires a reviewed `adm_id` crosswalk plus explicit yield unit; it retains a normalized subset, not the multi-GB archive. |
| AGMARKNET | **Portal identified; anonymous endpoint and price rows unverified** | [Official portal](https://agmarknet.gov.in/home); no local extract | No price, commodity mapping, date coverage, API access, or redistribution claim until raw rows and terms are checked. |
| Open-Meteo forecast / seasonal forecast | **Not part of the F0 pilot evidence** | Candidate endpoints only; no forecast response/cache | Forecasts need issue time, valid time, horizon and ensemble/member metadata; historical reanalysis cannot substitute for a forecast. |
| Earth Search / Sentinel-2 | **Not retrieved** | Candidate only | No NDVI/crop-condition claim; verify actual item/assets, cloud quality, spatial resolution and terms before use. |
| VDSA / NSS | **Not ingested for this pilot** | See [`F3 calibration source review`](docs/F3_CALIBRATION_SOURCE_REVIEW.md) | Household/aggregate socioeconomic sources do not establish linked bank repayment or default labels. |

## Baseline versioning (frozen F0 reference)

- Offline data fixture: `demo-fixture-2026-10-09.2`.
- Assessment engine: `risk-engine-v2-demo.2`.
- Crop response/calendar: `illustrative-v2`.
- Demo seed: `20261009`.
- Warning rules: `backend/app/config/warnings.json` (version is not self-declared today; add explicit rule version before changing thresholds).
- Manifest: `data/manifest.yaml` version 2.

Keep the existing deterministic offline walk-through. A source/model/rule change must receive a new version and document its effect; don't overwrite an old result or imply old snapshots are reproducible with new versions. This freeze records current version strings, not proof of cross-version regression equivalence.

## Dated weather and crop-stage assessment (2026-10-09)

- Runtime engine: `risk-engine-v2-demo.4`; calendar: `illustrative-stage-calendar-v4`; yield response: `stage-response-v4`.
- `GET /api/crop-calendar?borrower_id=...` returns explicit sowing/harvest dates, inclusive ordered windows, timezone rule, source, method, uncertainty, declared geography, and overlap/out-of-season flags.
- `POST /api/scenarios/evaluate` accepts optional `overrides.heatwave_start_date`. The event date is assigned to the containing stage; invalid or out-of-window durations return a visible validation error. The Scenario Lab displays stage dates, ERA5 coverage per stage, hypothetical stress per stage, and the event-date control.
- ERA5 daily totals/means/counts are clipped to each stage and to `as_of - 5 days`, the documented ERA5 publication delay. Each stage reports expected and observed days; partial coverage does not become a complete observed feature. The current 2026 demo seasons report missing ERA5 coverage instead of substituting 2015 values.
- Complete matched ERA5 stages contribute source-linked heat and illustrative rainfall-deficit components to stress and yield. Hypothetical event/rain inputs stay separately tagged. If weather is missing, the response uses only the explicitly hypothetical rule or unadjusted illustrative baseline; missing weather is not zero observed weather.
- Yield output carries source class, rule version, `t/ha`, and limitations. No aligned, admitted real yield rows exist, so no historical yield model is trained or calibrated. The response remains an illustrative rule, not a scientific or fitted model.

## Data quality and upgrade thresholds

1. **Source admission (F3):** retain actual source bytes/response, retrieval time, direct URL, applicable licence/terms, SHA-256, schema, units, source version, spatial/temporal resolution and attribution. The full Open-Meteo ERA5 response now satisfies this for its grid-point weather evidence; yield-source admission remains pending.
2. **Pune maize season join (F3):** include a row only when crop definition, district/geographic key, season/year, dates, and units are explicit. Do not infer farm-scale values from district/grid. Maintain source IDs and tolerances; no nearest-date joins without a declared tolerance. There is still no admitted yield/weather match for this target.
3. **Minimum real agronomy coverage before F4:** the chosen pilot must have at least one inspectable historical yield row for Pune (or an explicitly documented district boundary crosswalk) for maize with unit/year, and dated weather over the same declared season. NDVI and price remain separately `missing`/`assumed` until their own dated, aligned rows and quality/units are validated. This minimum enables exploratory integration only, not model validation.
4. **Yield-model upgrade:** require multiple years and a time-ordered holdout before claiming out-of-time evaluation; report sample counts, baseline, units, split years, missingness and geography. If sample size or matching is inadequate, retain the rule-based illustrative response.
5. **Credit model:** no real-world default/repayment performance claim without properly permissioned, linked historical loan outcomes and independent temporal/geographic validation. Generated loans only support simulation-conditional outputs.
6. **Runtime use:** only wire an external source after cache/fallback, source freshness and missing-data state have been exercised; preserve the offline fixture and include source/model versions in saved outputs.

## Claim audit

- Allowed: synthetic demo borrowers; assumed/hypothetical crop, weather, irrigation, yield and price; simulated debt cycle; the retained full weather response is a real historical reanalysis series at a grid location; NDVI/soil unavailable in runtime.
- Not allowed: live weather; observed crop stress; real borrower repayment behavior; farm-specific weather from this grid; satellite-derived condition; trained yield model; calibrated default probability; detected hidden debt; approved restructuring; live market price; matched Pune maize yield-weather-NDVI-price coverage.

Use `SOURCE_OBSERVED`, `SOURCE_FORECAST`, `MODEL_PREDICTED_YIELD`, `MODEL_SCENARIO_SHORTFALL`, `SIMULATED_CREDIT_OUTCOME`, `ASSUMED_INTERVENTION_EFFECT`, or `HUMAN_ENTERED` for new numerical assertions. Weather rows above are reanalysis (`SOURCE_OBSERVED` only in the broad historical-source sense; always display the more precise *gridded reanalysis* label), never a station observation.

## Normalized provider-export intake

The Data Sources page accepts a JSON provider export at `POST /api/data-sources/import` for `cybench`, `agmarknet`, `satellite`, `soil`, or `crop_calendar`. Each file must include an HTTPS source URL, attribution, license, version, declared geography, and normalized observations. NDVI/soil rows require valid coordinates; price rows require a market and commodity; yield rows require crop, source geography ID and harvest year. Crop calendar rows require crop/geography ID, `temporal_basis: static_primary_season`, both start/end day-of-year variables and `day_of_year` units; no year is implied. SHA-256 values for source files, when provided, must have valid format. CY-Bench pilot imports require Pune maize yield for harvest year 2015 and all 153 days of 2015-06-01 through 2015-10-31 for each of rainfall, minimum and maximum temperature. Accepted normalized data are stored immutably with canonical UTF-8 bytes and a content SHA-256. This validates normalized structure and consistency only; it does not independently verify upstream files, identity, license, source geography, or scientific fitness. Status stays `validated_pending_source_admission`; imports are not assessment inputs.

For a locally downloaded CY-Bench v1.10 ZIP, `backend/import_cybench_subset.py` streams the India maize yield and meteorology CSV members without extracting the full archive. It requires a human-reviewed JSON mapping of `adm_id` to district/state and an explicit yield unit. The resulting subset is still pending human source admission; no ZIP is included in the repository. The importer intentionally fails if a row or file naming convention differs from the expected schema rather than guessing a match.

The source monitor records every historical-weather refresh attempt in SQLite. It requests pinned ERA5 (ERA5-Land has no precipitation variable), validates all 153 requested dates, units and non-null values, prefers a previously verified full-window cache on outage, and uses the retained 3-row sample only when no verified complete cache exists. A fallback is clearly marked stale and is not treated as full-season coverage. Annual and season-specific Pune maize yield candidates are retained for traceability; the annual candidate is not Kharif-specific, while the season candidate lacks primary bytes, confirmed reuse terms and a geography crosswalk. Neither is admitted to the pilot.

`GET /api/source-snapshots` returns metadata without embedding large source contents. Retrieve retained bytes and the normalized payload explicitly from `/api/source-snapshots/{snapshot_id}/content`.
