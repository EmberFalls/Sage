# Yield training

This toolchain produces retrospective research artifacts. It does not replace the operational illustrative yield rules in Sage.

## Data and attribution

- Pinned CY-Bench dataset v1.2: https://zenodo.org/records/13838912. CY-Bench is maintained by the AgML community; cite the dataset and constituent providers when sharing results.
- India district yields: ICRISAT District-Level Database, source card at https://github.com/WUR-AI/AgML-CY-Bench/tree/main/data_preparation/crop_statistics_IN. The source card specifies CC BY 4.0.
- CY-Bench supplies MODIS NDVI, WorldCereal-derived crop calendars and WISE soil properties. Provider terms and definitions apply. File SHA-256 and archive paths are preserved in the downloaded manifest.
- The local `crop_production` mirror is a separate preliminary experiment. Its exact origin and license are unverified, so its artifact cannot be admitted as sourced production evidence.

## Reproduce

From the repository root, use Python 3.12 with the isolated requirements:

```powershell
python -m venv backend/.venv-yield
backend/.venv-yield/Scripts/python -m pip install -r tools/yield_training/requirements.txt
backend/.venv-yield/Scripts/python tools/yield_training/fetch_cybench.py
backend/.venv-yield/Scripts/python tools/yield_training/train_cybench.py
backend/.venv-yield/Scripts/python tools/yield_training/package_model.py
backend/.venv-yield/Scripts/python tools/yield_training/finalize_run.py
backend/.venv-yield/Scripts/python tools/yield_training/predict_research.py --request models/yield/india-ndvi-research-v1/example_request.json
```

Downloads use byte ranges to retrieve selected India CSVs from the 12.6 GB archive. Certificate verification stays enabled; a server that does not support byte ranges is rejected. The downloaded manifest checks each CSV before training. Raw data files are excluded from Git; rerun the fetch command to obtain them.

Training uses pre-midseason NDVI with an assumed seven-day availability lag. Yield histories have an assumed two-year reporting delay; validation and holdout labels do not enter their respective features. Preprocessing and candidate selection use training/validation only. The latest three observed years are reserved for the final evaluation; no random row split is used. Current-year area, production and loan outcomes are excluded from input features.

The portability step deserializes only the locally generated model. Never load an untrusted `joblib`/pickle upload. `model.json` supports dependency-free inference, rejects unsupported years/districts and returns explicit research metadata and missing uncertainty.

## Admission

Read `models/yield/india-ndvi-research-v1/evaluation.json` for sample counts, missingness, splits, geography, model and baseline errors, crop/state-code results, and limitations. The model must beat a preselected historical baseline, have supported deployment geography and inputs, and pass source/time availability review before operational integration. A retrospective district-yield error never validates borrower default probability.

Retraining after looking at the holdout requires a new independent evaluation period; do not repeatedly tune against these same final years and call them untouched.
