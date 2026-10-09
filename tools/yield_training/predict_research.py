"""Dependency-free inference for the portable research model; no runtime admission."""
import argparse
from datetime import date, timedelta
import json
import math
from pathlib import Path

def predict(model, row):
    if row.get('crop') not in model['supported_crops']:
        raise ValueError('Unsupported crop')
    if row.get('adm_id') not in model['supported_districts']:
        raise ValueError('Unsupported or unmapped district')
    if int(row['year']) not in model['supported_evaluation_years']:
        raise ValueError('Year is outside the evaluated research window; do not extrapolate to 2026')
    as_of=date.fromisoformat(row['as_of'])
    latest=date.fromisoformat(row['latest_observation'])
    if latest>as_of-timedelta(days=7):
        raise ValueError('Observation crosses the assumed as-of availability cutoff')
    if latest<date.fromisoformat(row['sowing_assumption']):
        raise ValueError('Observation predates the declared season')
    if int(row['ndvi_count'])<3:
        raise ValueError('Insufficient pre-cutoff NDVI observations')
    transformed=[float(row['adm_id']==key) for key in model['supported_districts']]
    transformed.extend(float(row['crop']==key) for key in model['supported_crops'])
    for feature,median,mean,scale in zip(model['numeric_features'],model['imputer_medians'],model['scaler_means'],model['scaler_scales']):
        value=row.get(feature)
        # Only soil columns had a reviewed missing-data pathway during training.
        if value is None and feature not in ['awc','bulk_density','drainage_class']:
            raise ValueError(f'Missing required feature: {feature}')
        value=median if value is None else float(value)
        if not math.isfinite(value): raise ValueError(f'Non-finite feature: {feature}')
        if feature in ['ndvi_mean','ndvi_min','ndvi_max','ndvi_last'] and not -1<=value<=1:
            raise ValueError(f'Invalid NDVI range: {feature}')
        transformed.append((value-mean)/scale)
    if len(transformed)!=len(model['coefficients']): raise ValueError('Corrupt model dimensions')
    y=max(0,model['intercept']+sum(value*weight for value,weight in zip(transformed,model['coefficients'])))
    return {'yield_t_per_ha':y,'units':'t/ha','model_version':model['model_version'],
            'status':'RESEARCH_ONLY','operational_admission':False,'source_class':model['source_class'],
            'district_id':row['adm_id'],'crop':row['crop'],'as_of':row['as_of'],
            'uncertainty':{'status':'unavailable','reason':'No calibrated prediction intervals'},
            'limitations':model['limitations']}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--model',type=Path,default=Path('models/yield/india-ndvi-research-v1/model.json'))
    parser.add_argument('--request',type=Path,required=True)
    args=parser.parse_args()
    print(json.dumps(predict(json.loads(args.model.read_text()),json.loads(args.request.read_text())),indent=2))

if __name__=='__main__': main()
