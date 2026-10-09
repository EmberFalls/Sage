"""Record model export agreement and write a human-readable training result."""
import csv
import hashlib
import json
import math
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent))
from predict_research import predict
from package_model import package

FOLDER=Path('models/yield/india-ndvi-research-v1')

def main():
    model=json.loads((FOLDER/'model.json').read_text())
    report=json.loads((FOLDER/'evaluation.json').read_text())
    with (FOLDER/'holdout_predictions.csv').open(newline='') as stream:
        rows=list(csv.DictReader(stream))
    requests=[]
    differences=[]
    unsupported=0
    for row in rows:
        if row['adm_id'] not in model['supported_districts']:
            unsupported+=1
            continue
        request={key:row[key] for key in ['adm_id','crop','as_of','latest_observation','sowing_assumption','harvest_assumption']}
        for key in model['numeric_features']:
            value=row[key]
            request[key]=float(value) if value and math.isfinite(float(value)) else None
        actual=predict(model,request)
        differences.append(abs(actual['yield_t_per_ha']-float(row['prediction_t_per_ha'])))
        requests.append(request)
    maximum=max(differences)
    if maximum>1e-9: raise ValueError(f'Portable model disagrees with training output: {maximum}')
    example=requests[0]
    if predict(model,example)!=predict(model,example): raise ValueError('Nondeterministic inference')
    (FOLDER/'example_request.json').write_text(json.dumps(example,indent=2)+'\n')
    (FOLDER/'example_prediction.json').write_text(json.dumps(predict(model,example),indent=2)+'\n')
    checks={'portable_prediction_rows':len(differences),'unsupported_district_rows_rejected':unsupported,'maximum_absolute_difference_t_per_ha':maximum,
            'deterministic_example':True,'operational_admission':False}
    (FOLDER/'export_validation.json').write_text(json.dumps(checks,indent=2)+'\n')
    baseline=report['selected_baseline'];selected=report['selected_model']
    scores=report['holdout_scores'];splits=report['splits']
    card=f'''# India NDVI yield model: completed research run

Status: **RESEARCH_ONLY — not enabled in Sage assessments**.

## Data

- CY-Bench v1.2 India district data: https://zenodo.org/records/13838912.
- Crops: maize and wheat. Geography: {report['district_count']} distinct CY-Bench district IDs in India.
- Aligned samples: {report['aligned_rows']:,} district/crop/harvest-year rows with usable pre-midseason NDVI.
- Targets: observed district yield in tonnes/hectare; inputs: NDVI, static soil/calendar, district ID, year, and prior yield history.
- Provenance: SHA-256 and archive file paths recorded in `data/training/cybench_india_v1_2/manifest.json`.

## Chronological evaluation

| Partition | Years | Rows |
| --- | --- | ---: |
| Initial fit | {min(splits['initial_training_years'])}–{max(splits['initial_training_years'])} | {splits['initial_training_rows']:,} |
| Candidate selection | {min(splits['validation_years'])}–{max(splits['validation_years'])} | {splits['validation_rows']:,} |
| Final fit | {min(splits['final_fit_years'])}–{max(splits['final_fit_years'])} | {splits['final_fit_rows']:,} |
| Untouched final holdout | {min(splits['holdout_years'])}–{max(splits['holdout_years'])} | {splits['holdout_rows']:,} |

Outcome availability uses a conservative assumed two-year delay. Validation feature histories are capped at {splits['historical_label_cap_for_validation']}; holdout histories at {splits['historical_label_cap_for_holdout']}. No held-out outcome is used as a feature for a later held-out year. NDVI stops seven days before the midseason assessment date. The reporting delays are assumptions; source publication timestamps are unknown.

## Results

| Predictor | Holdout MAE (t/ha) | Holdout RMSE (t/ha) |
| --- | ---: | ---: |
| Selected model: {selected} | {scores[selected]['mae_t_per_ha']:.6f} | {scores[selected]['rmse_t_per_ha']:.6f} |
| Preselected historical baseline: {baseline} | {scores[baseline]['mae_t_per_ha']:.6f} | {scores[baseline]['rmse_t_per_ha']:.6f} |

The selected model **does not beat the baseline in MAE**. The operational accuracy gate is not met. Keep this artifact for reproducibility and further research, not live prediction. This experiment does not establish weather/stage-response accuracy or credit-default accuracy.

`evaluation.json` contains every validation candidate, crop/state-code results, missingness, rejected-row counts and limitations. `model.json` is a portable trained ridge model. Its predictions agree with the training artifact on {len(differences):,} supported holdout rows (maximum difference {maximum:.3g} t/ha); an identical request returns identical output. The inference interface rejects {unsupported} held-out rows from districts absent from fitting. The evaluation scores above include those rows using the candidate pipeline's generic unknown-category behavior, so the evaluation population is broader than supported research inference.

## Remaining admission requirements

1. A new independent evaluation period for any future iteration, since this final holdout has now been inspected.
2. Source-backed mapping to Pune/Nashik and validated crop/season definitions for the intended deployment.
3. Verified data publication dates and predictor availability for strict as-of replay.
4. Aligned weather/forecast features and evaluation of any claimed stage-shock response.
5. Better-than-baseline performance for the supported crops/geographies, plus reviewed missing-data and uncertainty behavior.

No application code uses this trained artifact. The existing illustrative yield rules remain explicitly labeled. No calibrated prediction intervals are claimed, and 2026 extrapolation is rejected by the research inference tool.
'''
    (FOLDER/'MODEL_CARD.md').write_text(card,encoding='utf-8')
    package(FOLDER)
    print(json.dumps(checks,indent=2))

if __name__=='__main__': main()
