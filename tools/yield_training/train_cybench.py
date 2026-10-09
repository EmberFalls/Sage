"""Train a retrospective India district yield model with pre-midseason NDVI.

This research artifact is separate from Sage's operational illustrative rules.
"""
import argparse
from datetime import date, timedelta
import hashlib
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import ExtraTreesRegressor, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

SEED=20261009
NUMERIC=['year','season_days','sos_day','ndvi_mean','ndvi_max','ndvi_min','ndvi_std','ndvi_last','ndvi_slope','ndvi_count','awc','bulk_density','drainage_class','history_median','history_recent_median','history_trend']
FEATURES=['adm_id','crop']+NUMERIC

def scores(actual,predicted):
    return {'rows':len(actual),'mae_t_per_ha':float(mean_absolute_error(actual,predicted)),
            'rmse_t_per_ha':float(np.sqrt(mean_squared_error(actual,predicted)))}

def read_verified(folder, name, manifest):
    entry=next((item for item in manifest['files'] if item['name']==name),None)
    if not entry: raise ValueError(f'File has no pinned source manifest: {name}')
    path=folder/name
    if hashlib.sha256(path.read_bytes()).hexdigest()!=entry['sha256']: raise ValueError(f'Checksum mismatch: {name}')
    return pd.read_csv(path)

def build_features(folder):
    manifest=json.loads((folder/'manifest.json').read_text())
    rows=[]; historical=[]; rejects={'missing_calendar':0,'invalid_yield':0,'missing_ndvi_before_cutoff':0,'duplicate_yield':0}
    source_rows=0
    for crop in ['maize','wheat']:
        target=read_verified(folder,f'yield_{crop}_IN.csv',manifest)
        source_rows+=len(target)
        calendar=read_verified(folder,f'crop_calendar_{crop}_IN.csv',manifest).set_index('adm_id')
        if not calendar.index.is_unique: raise ValueError('Duplicate district crop calendar')
        soil=read_verified(folder,f'soil_{crop}_IN.csv',manifest).set_index('adm_id')
        ndvi=read_verified(folder,f'ndvi_{crop}_IN.csv',manifest)
        ndvi['date']=pd.to_datetime(ndvi.date.astype(str),format='%Y%m%d',errors='raise')
        ndvi=ndvi.dropna(subset=['ndvi'])
        ndvi=ndvi[(ndvi.ndvi>=-1)&(ndvi.ndvi<=1)]
        if ndvi.duplicated(['adm_id','date']).any(): raise ValueError('Duplicate NDVI district/date records')
        observations={key:group.sort_values('date') for key,group in ndvi.groupby('adm_id')}
        if target.duplicated(['adm_id','harvest_year']).any(): raise ValueError('Duplicate yield district/year labels')
        for row in target.to_dict('records'):
            year=int(row['harvest_year']); y=float(row['yield'])
            if not np.isfinite(y) or not 0<y<=15:
                rejects['invalid_yield']+=1;continue
            historical.append({'adm_id':row['adm_id'],'crop':crop,'year':year,'yield_t_per_ha':y})
            if row['adm_id'] not in calendar.index:
                rejects['missing_calendar']+=1;continue
            cal=calendar.loc[row['adm_id']]
            if not np.isfinite(cal.sos) or not np.isfinite(cal.eos):
                rejects['missing_calendar']+=1;continue
            start_doy=int(np.floor(cal.sos));end_doy=int(np.ceil(cal.eos))
            if not (1<=start_doy<=366 and 1<=end_doy<=366):
                rejects['missing_calendar']+=1;continue
            end=date(year,1,1)+timedelta(days=end_doy-1)
            start=date(year-(start_doy>end_doy),1,1)+timedelta(days=start_doy-1)
            season_days=(end-start).days+1
            as_of=start+timedelta(days=(season_days-1)//2)
            cutoff=as_of-timedelta(days=7)
            group=observations.get(row['adm_id'])
            if group is None:
                rejects['missing_ndvi_before_cutoff']+=1;continue
            visible=group[(group.date>=pd.Timestamp(start))&(group.date<=pd.Timestamp(cutoff))]
            if len(visible)<3:
                rejects['missing_ndvi_before_cutoff']+=1;continue
            values=visible.ndvi.to_numpy(dtype=float)
            days=(visible.date-pd.Timestamp(start)).dt.days.to_numpy(dtype=float)
            soil_row=soil.loc[row['adm_id']] if row['adm_id'] in soil.index else {}
            features={'adm_id':row['adm_id'],'crop':crop,'year':year,'yield_t_per_ha':y,
                      'sowing_assumption':start.isoformat(),'harvest_assumption':end.isoformat(),'as_of':as_of.isoformat(),
                      'latest_observation':visible.date.max().date().isoformat(),
                      'season_days':season_days,'sos_day':start_doy,
                      'ndvi_mean':float(values.mean()),'ndvi_max':float(values.max()),'ndvi_min':float(values.min()),
                      'ndvi_std':float(values.std()),'ndvi_last':float(values[-1]),'ndvi_count':len(values),
                      'ndvi_slope':float(np.polyfit(days,values,1)[0])}
            features.update({key:float(soil_row.get(key,np.nan)) for key in ['awc','bulk_density','drainage_class']})
            rows.append(features)
    return pd.DataFrame(rows),pd.DataFrame(historical),manifest,{'source_yield_rows':source_rows,'rejected_rows':rejects}

def add_history(data, history, cap):
    result=data.copy()
    records=[]
    for row in data.itertuples():
        available=history[(history.crop==row.crop)&(history.year<=min(int(row.year)-2,cap))]
        group=available[available.adm_id==row.adm_id].sort_values('year')
        if group.empty: group=available.sort_values('year')
        if group.empty: raise ValueError('No historical yield baseline before assessment year')
        median=float(group.yield_t_per_ha.median())
        recent=float(group.tail(5).yield_t_per_ha.median())
        if len(group)>=5 and group.year.nunique()>=3:
            x=group.year.to_numpy(dtype=float); y=group.yield_t_per_ha.to_numpy(dtype=float)
            trend=max(0,float(np.polyval(np.polyfit(x-x.mean(),y,1),row.year-x.mean())))
        else: trend=median
        records.append((median,recent,trend))
    result[['history_median','history_recent_median','history_trend']]=records
    return result

def models():
    def model(regressor):
        return Pipeline([('features',ColumnTransformer([
            ('categories',OneHotEncoder(handle_unknown='ignore',sparse_output=False),['adm_id','crop']),
            ('numeric',Pipeline([('missing',SimpleImputer(strategy='median')),('scale',StandardScaler())]),NUMERIC)])),('regressor',regressor)])
    return {**{f'ridge_{alpha}':model(Ridge(alpha=alpha)) for alpha in [1,10,100]},
            **{f'random_forest_leaf_{leaf}':model(RandomForestRegressor(n_estimators=180,min_samples_leaf=leaf,max_features=0.7,random_state=SEED,n_jobs=2)) for leaf in [5,15]},
            **{f'extra_trees_leaf_{leaf}':model(ExtraTreesRegressor(n_estimators=180,min_samples_leaf=leaf,max_features=0.7,random_state=SEED,n_jobs=2)) for leaf in [5,15]}}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--data',type=Path,default=Path('data/training/cybench_india_v1_2'))
    parser.add_argument('--output',type=Path,default=Path('models/yield/india-ndvi-research-v1'))
    args=parser.parse_args()
    data,history,manifest,intake=build_features(args.data)
    args.output.mkdir(parents=True,exist_ok=True)
    data.to_csv(args.output/'aligned_features.csv',index=False)
    years=sorted(data.year.unique().tolist())
    if len(years)<14: raise ValueError('Insufficient aligned years for holdout')
    test_years=years[-3:]; validation_years=years[-7:-4]
    train_cap=int(min(validation_years))-2; final_cap=int(min(test_years))-2
    training=add_history(data[data.year<=train_cap],history,train_cap)
    validation=add_history(data[data.year.isin(validation_years)],history,train_cap)
    development=add_history(data[data.year<=final_cap],history,final_cap)
    holdout=add_history(data[data.year.isin(test_years)],history,final_cap)
    alternatives=models()
    validation_scores={key:scores(validation.yield_t_per_ha,validation[key]) for key in ['history_median','history_recent_median','history_trend']}
    print(f'Aligned {len(data)} rows; fitting {len(alternatives)} candidates',flush=True)
    for name,model in alternatives.items():
        model.fit(training[FEATURES],training.yield_t_per_ha)
        validation_scores[name]=scores(validation.yield_t_per_ha,np.maximum(0,model.predict(validation[FEATURES])))
        print(name,validation_scores[name],flush=True)
    selected=min(alternatives,key=lambda key:validation_scores[key]['mae_t_per_ha'])
    selected_baseline=min(['history_median','history_recent_median','history_trend'],key=lambda key:validation_scores[key]['mae_t_per_ha'])
    winner=alternatives[selected]
    winner.fit(development[FEATURES],development.yield_t_per_ha)
    prediction=np.maximum(0,winner.predict(holdout[FEATURES]))
    baseline_prediction=holdout[selected_baseline].to_numpy()
    model_scores=scores(holdout.yield_t_per_ha,prediction); baseline_scores=scores(holdout.yield_t_per_ha,baseline_prediction)
    improvement=1-model_scores['mae_t_per_ha']/baseline_scores['mae_t_per_ha']
    exported=holdout.copy();exported['prediction_t_per_ha']=prediction;exported['baseline_t_per_ha']=baseline_prediction
    exported.to_csv(args.output/'holdout_predictions.csv',index=False)
    joblib.dump(winner,args.output/'model.joblib')
    history[history.year<=final_cap].to_csv(args.output/'baseline_history.csv',index=False)
    report={'model_version':'india-ndvi-research-v1','status':'RESEARCH_ONLY','operational_admission':False,
            'source_class':'CY-Bench real historical district yields and MODIS NDVI; retrospective research',
            'dataset':manifest,'source_statistics':'https://github.com/WUR-AI/AgML-CY-Bench/tree/main/data_preparation/crop_statistics_IN',
            'license_context':'ICRISAT India yield source card specifies CC BY 4.0; respect constituent source terms.',
            'geography':'India administrative districts by CY-Bench adm_id; no verified mapping to Sage demo borrowers',
            'units':'t/ha','features':FEATURES,'prediction_horizon':'midseason, with assumed 7-day NDVI availability lag',
            'intake':intake,'aligned_rows':len(data),'district_count':int(data.adm_id.nunique()),
            'missing_numeric_features':{key:int(data[key].isna().sum()) for key in NUMERIC if key in data},
            'splits':{'initial_training_years':sorted(training.year.unique().tolist()),'validation_years':validation_years,
                      'final_fit_years':sorted(development.year.unique().tolist()),'holdout_years':test_years,
                      'initial_training_rows':len(training),'validation_rows':len(validation),'final_fit_rows':len(development),'holdout_rows':len(holdout),
                      'historical_label_cap_for_validation':train_cap,'historical_label_cap_for_holdout':final_cap},
            'validation_scores':validation_scores,'selected_model':selected,'selected_baseline':selected_baseline,
            'holdout_scores':{selected:model_scores,selected_baseline:baseline_scores},
            'holdout_mae_improvement_fraction':float(improvement),'passes_accuracy_gate':bool(improvement>=0.05),
            'seed':SEED,'dependencies':{'sklearn':sklearn.__version__,'numpy':np.__version__,'pandas':pd.__version__,'joblib':joblib.__version__},
            'holdout_by_crop':{crop:{selected:scores(group.yield_t_per_ha,group.prediction_t_per_ha),selected_baseline:scores(group.yield_t_per_ha,group.baseline_t_per_ha)} for crop,group in exported.groupby('crop')},
            'holdout_by_state_code':{code:{selected:scores(group.yield_t_per_ha,group.prediction_t_per_ha),selected_baseline:scores(group.yield_t_per_ha,group.baseline_t_per_ha)} for code,group in exported.groupby(exported.adm_id.str.split('-').str[1])},
            'limitations':[
                'Retrospective district estimates; not farm-level, production-approved, or calibrated credit probabilities.',
                'Calendar is a static WorldCereal-derived crop-season estimate, not dated district sowing observations.',
                'Dataset/calendar/soil versions may postdate historical forecast origins; historical publication times are unknown.',
                'NDVI has a fixed assumed 7-day availability lag, not verified publication timestamps.',
                'Yields have an assumed two-year reporting lag; held-out labels never enter validation or holdout features.',
                'Weather, forecast, irrigation and stage-shock effects are not learned by this NDVI model.',
                'No prediction intervals or empirical interval coverage are claimed.',
                '2026 temporal extrapolation and Maharashtra/Pune borrower matching require further validation.',
                'Latest three years evaluated once after model selection on earlier validation years.'
            ]}
    (args.output/'evaluation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'selected_model':selected,'selected_baseline':selected_baseline,'holdout_scores':report['holdout_scores'],'improvement':improvement,'splits':report['splits'],'status':'RESEARCH_ONLY'},indent=2),flush=True)

if __name__=='__main__': main()
