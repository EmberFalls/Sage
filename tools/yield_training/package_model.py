"""Package the locally trained ridge artifact as portable, inspectable JSON."""
import hashlib
import json
from pathlib import Path
import joblib

def package(folder):
    folder=Path(folder)
    report=json.loads((folder/'evaluation.json').read_text())
    if not report['selected_model'].startswith('ridge_'):
        raise ValueError('Portable export currently supports Ridge only')
    # Only deserialize the artifact produced by this training run, never arbitrary uploads.
    model=joblib.load(folder/'model.joblib')
    preprocessing=model.named_steps['features']
    numeric=preprocessing.named_transformers_['numeric']
    categories=preprocessing.named_transformers_['categories']
    fitted=model.named_steps['regressor']
    bundle={'schema_version':1,'model_version':report['model_version'],'status':'RESEARCH_ONLY',
            'operational_admission':False,'units':'t/ha','source_class':report['source_class'],
            'supported_crops':categories.categories_[1].tolist(),
            'supported_districts':categories.categories_[0].tolist(),
            'supported_evaluation_years':report['splits']['holdout_years'],
            'numeric_features':preprocessing.transformers_[1][2],
            'imputer_medians':numeric.named_steps['missing'].statistics_.tolist(),
            'scaler_means':numeric.named_steps['scale'].mean_.tolist(),
            'scaler_scales':numeric.named_steps['scale'].scale_.tolist(),
            'coefficients':fitted.coef_.tolist(),'intercept':float(fitted.intercept_),
            'limitations':report['limitations'],
            'holdout_scores':report['holdout_scores'],'data_source_record':report['dataset']['record']}
    (folder/'model.json').write_text(json.dumps(bundle,indent=2)+'\n',encoding='utf-8')
    files={path.name:hashlib.sha256(path.read_bytes()).hexdigest() for path in folder.iterdir() if path.is_file() and path.name!='artifact_manifest.json'}
    (folder/'artifact_manifest.json').write_text(json.dumps({'model_version':report['model_version'],'sha256':files},indent=2)+'\n')
    print(f'Portable JSON model packaged: {folder / "model.json"}')

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--model-dir',type=Path,default=Path('models/yield/india-ndvi-research-v1'))
    package(parser.parse_args().model_dir)
