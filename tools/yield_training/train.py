"""Leakage-aware district yield research; never enables the operational predictor."""
import argparse
import hashlib
import json
import platform
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import ExtraTreesRegressor, RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

SEED = 20261009
EXPECTED_SHA = '5b2637058ca4aff2ef7c0e0f2f391bca712300d082693b585f489871fd91d520'
FEATURES = ['district', 'crop', 'year']

def metrics(actual, prediction):
    return {'mae_t_per_ha':float(mean_absolute_error(actual,prediction)),
            'rmse_t_per_ha':float(np.sqrt(mean_squared_error(actual,prediction))), 'rows':len(actual)}

def baseline(train, rows, kind):
    predictions=[]
    for row in rows.itertuples():
        group=train[(train.district==row.district)&(train.crop==row.crop)].sort_values('year')
        if group.empty: group=train[train.crop==row.crop].sort_values('year')
        if kind=='recent_median': group=group.tail(5)
        if kind=='trend' and len(group)>=5:
            years=group.year.to_numpy(dtype=float)
            coefs=np.polyfit(years-years.mean(),group.yield_t_per_ha,1)
            value=float(np.polyval(coefs,row.year-years.mean()))
        else: value=float(group.yield_t_per_ha.median())
        predictions.append(max(0.0,value))
    return np.array(predictions)

def candidates():
    def make(estimator):
        return Pipeline([('features',ColumnTransformer([
            ('categories',OneHotEncoder(handle_unknown='ignore',sparse_output=False),['district','crop']),
            ('year',StandardScaler(),['year'])])), ('regressor',estimator)])
    return {
        **{f'ridge_{alpha}':make(Ridge(alpha=alpha)) for alpha in [0.1,1,10,100]},
        **{f'random_forest_leaf_{leaf}':make(RandomForestRegressor(n_estimators=250,min_samples_leaf=leaf,random_state=SEED,n_jobs=2)) for leaf in [2,5,10]},
        **{f'extra_trees_leaf_{leaf}':make(ExtraTreesRegressor(n_estimators=250,min_samples_leaf=leaf,random_state=SEED,n_jobs=2)) for leaf in [2,5,10]},
    }

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--input',type=Path,required=True)
    parser.add_argument('--output',type=Path,default=Path('models/yield/maharashtra-district-research-v1'))
    args=parser.parse_args()
    digest=hashlib.sha256(args.input.read_bytes()).hexdigest()
    if digest != EXPECTED_SHA: raise ValueError('Unreviewed input checksum; review dataset before training')
    raw=pd.read_csv(args.input)
    for name in ['State_Name','District_Name','Season','Crop']: raw[name]=raw[name].str.strip()
    scoped=raw[(raw.State_Name=='Maharashtra') & (((raw.Crop=='Maize')&(raw.Season=='Kharif')) | ((raw.Crop=='Wheat')&(raw.Season=='Rabi')))].copy()
    missing=scoped.isna().sum().to_dict()
    valid=scoped.dropna(subset=['Area','Production','Crop_Year','District_Name'])
    valid=valid[(valid.Area>0)&(valid.Production>=0)].copy()
    valid['yield_t_per_ha']=valid.Production/valid.Area
    # Documented quality screen, fixed before inspecting validation/holdout errors.
    valid=valid[(valid.yield_t_per_ha>=0)&(valid.yield_t_per_ha<=15)]
    data=valid.rename(columns={'District_Name':'district','Crop':'crop','Crop_Year':'year'})[['district','crop','year','yield_t_per_ha']].sort_values(['year','crop','district']).reset_index(drop=True)
    if data.duplicated(['district','crop','year']).any(): raise ValueError('Duplicate district/crop/year targets')
    years=sorted(data.year.unique().tolist())
    if len(years)<14: raise ValueError('Not enough years for time-ordered splits')
    holdout_years=years[-3:]
    validation_years=years[-7:-4]
    # Two-year conservative assumed label delay. Publication dates are unknown;
    # these are research splits, not certified historical as-of replay.
    first_validation=int(min(validation_years)); first_holdout=int(min(holdout_years))
    initial=data[data.year<=first_validation-2]
    validation=data[data.year.isin(validation_years)]
    development=data[data.year<=first_holdout-2]
    holdout=data[data.year.isin(holdout_years)]
    models=candidates()
    validation_scores={}
    for kind in ['district_median','recent_median','trend']:
        validation_scores[kind]=metrics(validation.yield_t_per_ha,baseline(initial,validation,kind))
    for name, model in models.items():
        model.fit(initial[FEATURES],initial.yield_t_per_ha)
        validation_scores[name]=metrics(validation.yield_t_per_ha,np.maximum(0,model.predict(validation[FEATURES])))
    chosen=min(models,key=lambda name:validation_scores[name]['mae_t_per_ha'])
    chosen_baseline=min(['district_median','recent_median','trend'],key=lambda name:validation_scores[name]['mae_t_per_ha'])
    model=models[chosen]
    model.fit(development[FEATURES],development.yield_t_per_ha)
    prediction=np.maximum(0,model.predict(holdout[FEATURES]))
    reference=baseline(development,holdout,chosen_baseline)
    test_scores={chosen:metrics(holdout.yield_t_per_ha,prediction),chosen_baseline:metrics(holdout.yield_t_per_ha,reference)}
    improvement=1-test_scores[chosen]['mae_t_per_ha']/test_scores[chosen_baseline]['mae_t_per_ha']
    args.output.mkdir(parents=True,exist_ok=True)
    joblib.dump(model,args.output/'model.joblib')
    data.to_csv(args.output/'reviewed_rows.csv',index=False)
    predictions=holdout.copy();predictions['prediction_t_per_ha']=prediction;predictions['baseline_t_per_ha']=reference
    predictions.to_csv(args.output/'holdout_predictions.csv',index=False)
    report={
        'model_version':'maharashtra-district-research-v1','status':'RESEARCH_ONLY',
        'operational_admission':False,'source_class':'third_party_historical_yield_mirror_unverified',
        'input_sha256':digest,'source_url':None,
        'source_context':'Existing local crop_production mirror. Official OGD catalog documents district crop area (ha) and production (t); exact mirror origin and license are not verified.',
        'official_catalog':'https://www.data.gov.in/catalog/district-wise-season-wise-crop-production-statistics-0',
        'label':'production_tonnes / harvested_area_hectares','units':'t/ha','features':FEATURES,
        'excluded_features':['current-year Production','current-year Area','current-year Yield','future observations','synthetic weather','loan outcomes'],
        'geography':'Maharashtra district aggregate; Maize/Kharif and Wheat/Rabi',
        'districts':sorted(data.district.unique().tolist()),
        'input_scope_rows':len(scoped),'accepted_rows':len(data),'excluded_rows':len(scoped)-len(data),
        'missingness_before_filter':{k:int(v) for k,v in missing.items()},
        'splits':{'initial_training_years':sorted(initial.year.unique().tolist()),'validation_years':validation_years,
                  'final_fit_years':sorted(development.year.unique().tolist()),'holdout_years':holdout_years,
                  'initial_training_rows':len(initial),'validation_rows':len(validation),'final_fit_rows':len(development),'holdout_rows':len(holdout)},
        'validation_scores':validation_scores,'selected_model':chosen,'selected_baseline':chosen_baseline,
        'holdout_scores':test_scores,'holdout_mae_improvement_fraction':float(improvement),
        'passes_accuracy_gate':bool(improvement>=0.05),
        'seed':SEED,'dependencies':{'python':platform.python_version(),'scikit-learn':sklearn.__version__,'numpy':np.__version__,'pandas':pd.__version__,'joblib':joblib.__version__},
        'limitations':[
            'Historical baseline model only: no climate, NDVI, irrigation or soil response is learned.',
            'Not a farm-level yield forecast, default probability, or validated response to stage interventions.',
            'Mirror origin, release dates, district boundary history and redistribution license need verification.',
            'A two-year outcome availability lag is assumed, not source-verified.',
            'No calibrated prediction intervals. Results do not justify 2026 extrapolation.',
            'The latest three observed years are held out once; selection uses earlier validation years only.',
            'Even if the accuracy gate passes, data provenance and climate-feature admission remain unmet.'
        ],
        'holdout_by_crop':{crop:{chosen:metrics(group.yield_t_per_ha,group.prediction_t_per_ha),chosen_baseline:metrics(group.yield_t_per_ha,group.baseline_t_per_ha)} for crop,group in predictions.groupby('crop')}
    }
    (args.output/'evaluation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'selected_model':chosen,'selected_baseline':chosen_baseline,'holdout_scores':test_scores,'improvement':improvement,'status':report['status'],'samples':len(data),'splits':report['splits']},indent=2))

if __name__=='__main__': main()
