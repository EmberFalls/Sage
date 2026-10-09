# India NDVI yield model: completed research run

Status: **RESEARCH_ONLY — not enabled in Sage assessments**.

## Data

- CY-Bench v1.2 India district data: https://zenodo.org/records/13838912.
- Crops: maize and wheat. Geography: 567 distinct CY-Bench district IDs in India.
- Aligned samples: 14,000 district/crop/harvest-year rows with usable pre-midseason NDVI.
- Targets: observed district yield in tonnes/hectare; inputs: NDVI, static soil/calendar, district ID, year, and prior yield history.
- Provenance: SHA-256 and archive file paths recorded in `data/training/cybench_india_v1_2/manifest.json`.

## Chronological evaluation

| Partition | Years | Rows |
| --- | --- | ---: |
| Initial fit | 2001–2009 | 7,278 |
| Candidate selection | 2011–2013 | 2,519 |
| Final fit | 2001–2013 | 10,618 |
| Untouched final holdout | 2015–2017 | 2,528 |

Outcome availability uses a conservative assumed two-year delay. Validation feature histories are capped at 2009; holdout histories at 2013. No held-out outcome is used as a feature for a later held-out year. NDVI stops seven days before the midseason assessment date. The reporting delays are assumptions; source publication timestamps are unknown.

## Results

| Predictor | Holdout MAE (t/ha) | Holdout RMSE (t/ha) |
| --- | ---: | ---: |
| Selected model: ridge_100 | 0.693511 | 1.027935 |
| Preselected historical baseline: history_trend | 0.691074 | 1.066763 |

The selected model **does not beat the baseline in MAE**. The operational accuracy gate is not met. Keep this artifact for reproducibility and further research, not live prediction. This experiment does not establish weather/stage-response accuracy or credit-default accuracy.

`evaluation.json` contains every validation candidate, crop/state-code results, missingness, rejected-row counts and limitations. `model.json` is a portable trained ridge model. Its predictions agree with the training artifact on 2,424 supported holdout rows (maximum difference 1.78e-15 t/ha); an identical request returns identical output. The inference interface rejects 104 held-out rows from districts absent from fitting. The evaluation scores above include those rows using the candidate pipeline's generic unknown-category behavior, so the evaluation population is broader than supported research inference.

## Remaining admission requirements

1. A new independent evaluation period for any future iteration, since this final holdout has now been inspected.
2. Source-backed mapping to Pune/Nashik and validated crop/season definitions for the intended deployment.
3. Verified data publication dates and predictor availability for strict as-of replay.
4. Aligned weather/forecast features and evaluation of any claimed stage-shock response.
5. Better-than-baseline performance for the supported crops/geographies, plus reviewed missing-data and uncertainty behavior.

No application code uses this trained artifact. The existing illustrative yield rules remain explicitly labeled. No calibrated prediction intervals are claimed, and 2026 extrapolation is rejected by the research inference tool.
