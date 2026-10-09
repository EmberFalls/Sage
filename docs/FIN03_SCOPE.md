# F0 — frozen FIN-03 scope and evidence gate

**Freeze date:** 2026-10-09  
**Source of requirements:** `Sage_FULL_Implementation_Plan_V2.md`, Phase F0. This file applies that plan's instructions to the existing Sage repository; it is not permission to treat roadmap prose as implemented behavior.

## Scope decision

Pilot source-feasibility target: **maize, Pune district, Maharashtra, Kharif 2015**. Choose one crop-region-season before feature development so source joins have a stable key. Pune + maize is already represented in the synthetic demo, but the demo dates and numbers are not observations from this selected 2015 season. The real weather excerpt is a grid point, not district or farm truth.

**F0 exit state: PARTIAL — documentation/baseline deliverables frozen; real-data join gate not met.** A no-auth Open-Meteo historical request and three raw daily sample rows are recorded. No matched real yield + weather + NDVI + price season has been demonstrated, so F3+ must preserve simulation/assumption labels and cannot start real-data model claims. Do not mark F0 fully complete.

## Frozen FIN-03 input checklist

| Official input | Present in existing demo? | Source class and F0 disposition | F0 acceptance for a future real-data upgrade |
|---|---|---|---|
| Satellite crop observations | No | NDVI unavailable; no inferred crop/stress | Actual pixel/item, acquisition date, resolution, cloud/quality flag, location and licence; no farm-level claim from district/grid data |
| Weather forecasts | No operational forecast | Scenario slider is hypothetical; historical Open-Meteo sample is reanalysis only | Forecast has `issued_at <= assessment_as_of`, `valid_for`, model/member and units; historical reanalysis kept as a separate type |
| Soil moisture | No | Unavailable in runtime; no observed soil claim | Actual source, layer/depth, unit, date, geometry/resolution and quality; display missingness |
| Crop type | Yes, synthetic fixture | Pune maize synthetic record; not externally verified for the target season | Explicit crop taxonomy and source-backed crop assignment if used outside demo |
| Irrigation | Yes, assumed fixture/override | Scenario assumption | Provenance, value bounds and date; distinguish reported from modeled |
| Historical yield | No real history | Rule-generated demo yield | Source-backed district/year/crop, unit, boundary crosswalk, vintage; holdout required before performance claim |
| Market prices | No verified local observation | Assumed/user-entered fixture | Dated market and crop mapping, price unit (e.g. INR/quintal), source and quality; never call MSP a realized sale price |
| Credit history | Yes, synthetic | Synthetic demo only; not a loan dataset | Permissioned, linked outcome/ledger evidence before any real repayment/default claim |
| Dynamic repayment estimate | Yes, illustrative simulation | Conditional on synthetic paths/rules | Describe semantic target and population; no real-world PD/calibration until external labeled data + independent validation |
| Explainable drivers | Yes, demo engine | Formula/rule evidence for simulated outputs | Every factor links to input/source/version, date, computation and uncertainty; server remains authoritative |

## Data alignment rules

- Keep distinct keys for crop, season, dates, district/admin boundary, grid coordinates, data resolution and units. A point/grid sample must not silently become district truth; district evidence must not be represented as farm measurement.
- `Kharif 2015` is a feasibility key, not proof that all required seasonal windows overlap. In particular, no yield-year or price observations are currently aligned to this target.
- Keep raw source bytes separate from normalized records and derived features. Record direct URL/query, retrieval time, immutable version, license/terms, attribution, hash, schema, units, geo/time resolution and missingness before ingestion.
- Preserve the working seeded offline fixture. New live calls must never be needed for the core walkthrough.

## Measurable phase-entry thresholds

These are gates, not claims that the source corpus already meets them.

| Upgrade | Entry threshold |
|---|---|
| F3 source ingestion | Each chosen input has retrievable bytes or a recorded honest fallback, a schema/units check, provenance and hash. For the Pune maize pilot, at least one source-backed yield row with year/unit and an explicit geography crosswalk must align to dated same-season weather. NDVI and prices stay separately missing/assumed until each has a dated aligned row. |
| F4 real agronomic features | Crop season dates and ordered stage windows have cited provenance; all feature rows respect `as_of`, carry source and unit metadata, and no future observation enters a past assessment. If a crop calendar or real yield baseline cannot be supported, continue only as labeled illustrative modeling. |
| F5 credit probability | No `real PD` label until a permissioned real outcome cohort is joined to as-of features and independently evaluated with temporal/geographic holdouts; synthetic scenarios alone never satisfy this gate. |
| F6 reproducibility | For pinned data/engine versions, baseline and stress rerun deterministically; resetting restores the same baseline input/result identity; changed versions are explicit and old snapshots remain inspectable. |
| F7 debt warnings | Warning rule IDs/threshold version, deterministic evidence, idempotent lifecycle and acknowledgement without altering modeled score/debt. Never describe simulated informal debt as detected fact. |
| F8 interventions | Reject infeasible options with reasons; date, incremental interest/cost, ledger and later seasons recompute; no real loan mutation. |
| F9 allocation | Allocation respects the explicit budget invariant, logs decisions and leaves unselected borrowers/options visible. |
| F10 farmer/report UX | All navigation destinations function; role/privacy limits are true; exports include assumptions/source/engine versions; desktop, narrow viewport and keyboard checks recorded. |
| F11 empirical upgrade | Time-ordered holdout, sample count, baseline comparison, geography coverage and target-specific uncertainty coverage reported. If not sufficient, keep existing rule/assumption path. |

## Registered assumptions and limitations

1. The only retained external sample is a three-day Open-Meteo historical reanalysis excerpt. It is not a forecast, station measurement, field measurement, source adapter, complete season archive or matched crop outcome.
2. `Pune maize Kharif 2015` is a source feasibility target. No yield, NDVI, soil observation, price, or real credit-performance rows are verified for it.
3. Existing borrower/loan/repayment values and the 21 simulation paths are synthetic. Crop response, calendar, rainfall/heat effects, irrigation and prices are assumptions/illustrations.
4. A farmer record's district does not certify exact coordinates or establish that the weather grid is the farm's exposure.
5. Open-Meteo free API is non-commercial only and its data requires CC-BY attribution. Do not use the free API in commercial/promotional deployment; confirm suitable paid terms first.
6. Historical yield fit, real default accuracy, actual hidden-debt detection, bank eligibility, policy compliance and intervention efficacy are not established.
7. Existing stack/UI differs from the full plan's target architecture. F0 freezes current baseline; any later migration requires its own compatibility/regression evidence.

## F0 source gate evidence

- Successful no-auth historical API response observed for `archive-api.open-meteo.com`, query coordinates near Pune and date span 2015-06-01 through 2015-10-31. Three raw rows are retained in `data/raw/open_meteo/pune_kharif_2015_sample.json`; the complete response was not persisted and no checksum is claimed for it.
- Response grid metadata: latitude 18.523726, longitude 73.86876, elevation 561m, timezone Asia/Kolkata. First three dates/values are documented in the retained excerpt.
- Official API documentation describes historical data as reanalysis and documents its temporal/spatial datasets; terms state free access is non-commercial and data is CC-BY 4.0. See source links in `DATA_SOURCES.md`.
- CY-Bench record metadata/version was reviewed; its multi-GB archive was not downloaded/inspected for India maize/Pune keys. It is not admitted as evidence.
- **Join result:** weather sample only. No actual known crop-yield/weather/NDVI/price geo-time join; F0 data gate remains open.
