"""Train a new version or apply an existing ProQuest RNN bundle to prepared labels.

Inputs are CSV/CSV.gz prepared ProQuest label tables, not source text. Historical
defaults are guarded; future years require --allow-new-years. Every run needs a
new output directory. Prediction never requires or reads outcome columns.
"""
import argparse
import hashlib
import json
from pathlib import Path
import platform

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import OneHotEncoder, StandardScaler
import torch

from proquest_rnn import (ClaimGRU, CLAIM_CATEGORIES, TOPICS, DIRECTIONS, monthly_context,
                          sequence_indices, chronological_splits, article_weights,
                          neural_probabilities, train_gru)
from proquest_polarization_models import added_inputs
from proquest_rnn_permutation import ARMS, added_values, scores

REQUIRED = ['record_id','page_id','date','scope',*CLAIM_CATEGORIES,'horizon_used']


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_labels(path, through, allow_new_years=False, training=False):
    # Explicit usecols prevents verifier prose, annotations, and outcome columns
    # from even being read in prediction mode.
    fields=REQUIRED+(['hit','scorable','basis'] if training else [])
    frame=pd.read_csv(path,usecols=list(dict.fromkeys(fields)),dtype={'record_id':str,'page_id':str})
    frame['date']=pd.to_datetime(frame.date,errors='raise')
    if frame[['record_id','page_id','date']].isna().any().any() or frame.record_id.duplicated().any():
        raise ValueError('Missing addresses/dates or duplicate source-local record IDs')
    frame['month']=frame.date.dt.to_period('M'); frame['year']=frame.date.dt.year
    frame=frame[frame.month<=pd.Period(through,'M')].copy()
    if frame.empty: raise ValueError('No labels before requested endpoint')
    if frame.year.lt(1900).any() or (not allow_new_years and frame.year.gt(2010).any()):
        raise ValueError('Active scope is 1900–2010; future runs require explicit --allow-new-years')
    if frame.groupby('page_id').month.nunique().gt(1).any():
        raise ValueError('Article ID spans publication months')
    return frame


def eligible(frame):
    h=pd.to_numeric(frame.horizon_used,errors='coerce')
    return (frame.scope.eq('national') & frame.topic.isin(TOPICS) & frame.predicted_norm.isin(DIRECTIONS)
            & h.between(1,24) & h.eq(np.floor(h)))


def prepare_inputs(labels,target,parameters):
    context=monthly_context(labels)
    if list(context.columns)!=parameters['context_features']:
        raise ValueError('Context columns do not match saved bundle')
    sequence=parameters['context_scaler'].transform(context).astype('float32')[sequence_indices(target.month,context.index)]
    categories=target[parameters['claim_categories']].fillna('missing')
    claim=np.column_stack([parameters['encoder'].transform(categories),
                           parameters['horizon_scaler'].transform(target[['horizon_used']])]).astype('float32')
    return sequence,claim


def read_features(path,months):
    if path is None: return None
    features=pd.read_csv(path,usecols=['origin','political_polarization','forecast_polarization'])
    features['origin']=pd.PeriodIndex(features.origin,freq='M')
    if features.origin.duplicated().any(): raise ValueError('Duplicate polarization month')
    features=features.set_index('origin')
    if not pd.Index(months.unique()).isin(features.index).all():
        raise ValueError('Missing polarization month rows; use explicit NaN for unavailable measured inputs')
    result=features.reindex(months).reset_index(drop=True)
    values=result[['political_polarization','forecast_polarization']].to_numpy()
    if np.isinf(values).any() or ((values<0)|(values>1)).any():
        raise ValueError('Polarization values must be in [0,1] or NaN')
    return result


def new_output(path):
    path=Path(path)
    if path.exists(): raise ValueError('Output directory already exists; use a new versioned directory')
    if not path.resolve().is_relative_to(Path('data/scored/proquest').resolve()):
        raise ValueError('Derived runs must be under data/scored/proquest/')
    path.mkdir(parents=True)
    return path


def predict(bundle,labels,features_path,start,through,arms):
    manifest_path=bundle/'bundle_manifest.json'
    if manifest_path.exists():
        manifest=json.loads(manifest_path.read_text())
        for name,sha in manifest['bundle_sha256'].items():
            if digest(bundle/name)!=sha: raise ValueError(f'Bundle artifact changed: {name}')
    parameters=joblib.load(bundle/'preprocessing_and_baselines.joblib')
    target=labels[eligible(labels) & labels.month.between(pd.Period(start,'M'),pd.Period(through,'M'))].copy()
    if target.empty: raise ValueError('No eligible prediction rows')
    if labels.month.min()>target.month.min()-12:
        raise ValueError('Supply at least 12 months of preceding label history')
    context,claim=prepare_inputs(labels,target,parameters)
    features=read_features(features_path,target.month)
    if any(ARMS[a] for a in arms) and features is None: raise ValueError('Polarization arms require --features')
    rows=target[['record_id','page_id','date','year']].copy(); rows['date']=rows.date.dt.strftime('%Y-%m-%d')
    used=[bundle/'preprocessing_and_baselines.joblib']
    for arm in arms:
        names=ARMS[arm]; params=parameters['added_preprocessing']
        extra=added_values(features,params[params.arm.eq(arm)],names) if names else np.empty((len(target),0),dtype='float32')
        x=np.column_stack([claim,extra]).astype('float32')
        for name in ['logistic_metadata','logistic_metadata_history']:
            model=parameters['logistic_models'][f'{name}__{arm}']
            matrix=x if name=='logistic_metadata' else np.column_stack([x,context.reshape(len(x),-1)])
            rows[f'{name}__{arm}']=model.predict_proba(matrix)[:,list(model.classes_).index(1)]
        checkpoints=sorted(bundle.glob(f'gru_{arm}_*.pt'))
        if not checkpoints: raise ValueError(f'No saved checkpoints for {arm}')
        probabilities=[]
        for path in checkpoints:
            checkpoint=torch.load(path,map_location='cpu',weights_only=True)
            model=ClaimGRU(checkpoint['context_size'],checkpoint['claim_size'],checkpoint['hidden_size'])
            model.load_state_dict(checkpoint['state_dict'])
            p=neural_probabilities(model,torch.from_numpy(context),torch.from_numpy(x))
            rows[f"gru_seed_{checkpoint['seed']}__{arm}"]=p; probabilities.append(p); used.append(path)
        rows[f'gru_ensemble__{arm}']=np.mean(probabilities,axis=0)
    return rows,used


def training_configuration(path):
    value=json.loads(Path(path).read_text())
    value=value.get('candidate',value)
    config={key:value[key] for key in ['hidden','dropout','weight_decay','window_years']}
    if type(config['hidden']) is not int or not 1<=config['hidden']<=256:
        raise ValueError('Hidden size must be an integer from 1 to 256')
    if not 0<=config['dropout']<1 or not 0<=config['weight_decay']<=1:
        raise ValueError('Invalid dropout or weight decay')
    if config['window_years'] is not None and (type(config['window_years']) is not int or config['window_years']<1):
        raise ValueError('Training window must be null or a positive number of years')
    if 'half_life_years' in value:
        half_life=value['half_life_years']
        if isinstance(half_life,bool) or not isinstance(half_life,(int,float)) or not np.isfinite(half_life) or half_life<=0:
            raise ValueError('Half-life must be finite and positive')
        config['half_life_years']=half_life
    return config


def train(labels,features_path,validation_start,test_start,arms,seeds,epochs,out,as_of='2026-10-19',configuration=None):
    if not labels.scorable.isin([True,False]).all(): raise ValueError('scorable must be boolean')
    supported=eligible(labels) & labels.scorable & labels.basis.ne('NBER proxy')
    candidates=labels[supported].copy()
    mature=np.array([m+int(h)+3<pd.Period(as_of,'M') for m,h in zip(candidates.month,candidates.horizon_used)])
    target=candidates[mature].copy().reset_index(drop=True)
    if not target.hit.isin([0,1]).all(): raise ValueError('Training/evaluation needs binary mature deterministic hit labels')
    masks,availability,_=chronological_splits(target,validation_start,test_start)
    window=None if configuration is None else configuration['window_years']
    lower=None if window is None else pd.Period(validation_start,'M')-12*window
    if lower is not None:
        masks['train'] &= np.asarray(target.month>=lower)
        if target.loc[masks['train'],'hit'].nunique()!=2: raise ValueError('Training window needs both outcome classes')
    context=monthly_context(labels)
    fit_context=context.loc[context.index<pd.Period(validation_start,'M')]
    if lower is not None: fit_context=fit_context.loc[fit_context.index>=lower]
    parameters={'context_features':list(context.columns),'claim_categories':CLAIM_CATEGORIES,
                'context_scaler':StandardScaler().fit(fit_context),
                'encoder':OneHotEncoder(handle_unknown='ignore',sparse_output=False,dtype=np.float32).fit(target.loc[masks['train'],CLAIM_CATEGORIES].fillna('missing')),
                'horizon_scaler':StandardScaler().fit(target.loc[masks['train'],['horizon_used']])}
    sequence,claim=prepare_inputs(labels,target,parameters)
    features=read_features(features_path,target.month)
    if any(ARMS[a] for a in arms) and features is None: raise ValueError('Polarization arms require --features')
    weights=np.ones(len(target),dtype='float32')
    for mask in masks.values(): weights[mask]=article_weights(target[mask])
    if configuration and 'half_life_years' in configuration:
        from proquest_rnn_age_weighting import age_weighted_training
        weights=age_weighted_training(weights,target.month,masks['train'],validation_start,configuration['half_life_years'])
    y=target.hit.to_numpy(dtype='float32'); added=[]; models={}; histories=[]; results=[]
    prediction_rows=target.loc[masks['test'],['record_id','page_id','date','year','hit']].copy()
    for arm in arms:
        names=ARMS[arm]
        if names:
            _,extra,params=added_inputs(features.loc[masks['train']],features,names); added.append(params.assign(arm=arm))
        else: extra=np.empty((len(target),0))
        x=np.column_stack([claim,extra]).astype('float32')
        predictions={}
        for name in ['logistic_metadata','logistic_metadata_history']:
            matrix=x if name=='logistic_metadata' else np.column_stack([x,sequence.reshape(len(x),-1)])
            model=LogisticRegression(C=1.,max_iter=1500,solver='lbfgs')
            model.fit(matrix[masks['train']],y[masks['train']],sample_weight=weights[masks['train']])
            models[f'{name}__{arm}']=model
            predictions[name]=model.predict_proba(matrix[masks['test']])[:,list(model.classes_).index(1)]
            prediction_rows[f'{name}__{arm}']=predictions[name]
        probabilities=[]
        for seed in seeds:
            if configuration is None:
                model,history,best=train_gru(torch.from_numpy(sequence),torch.from_numpy(x),torch.from_numpy(y),torch.from_numpy(weights),masks,seed,epochs=epochs)
            else:
                from proquest_rnn_development import fit_seed
                fit_data={'sequence':sequence,'claim':x,'y':y,'weights':weights,
                          'masks':{'train':masks['train'],'stopping':masks['validation']}}
                model,history,best=fit_seed(fit_data,configuration,seed,epochs=epochs)
            histories.extend(dict(arm=arm,**r) for r in history)
            torch.save({'state_dict':model.state_dict(),'context_size':sequence.shape[-1],'claim_size':x.shape[-1],
                        'hidden_size':24 if configuration is None else configuration['hidden'],
                        'configuration':configuration,'seed':seed,'best_epoch':best,'arm':arm,'added_features':names},out/f'gru_{arm}_{seed}.pt')
            probability=neural_probabilities(model,torch.from_numpy(sequence[masks['test']]),torch.from_numpy(x[masks['test']]))
            probabilities.append(probability); prediction_rows[f'gru_seed_{seed}__{arm}']=probability
        predictions['gru_ensemble']=np.mean(probabilities,axis=0)
        prediction_rows[f'gru_ensemble__{arm}']=predictions['gru_ensemble']
        for name,p in predictions.items(): results.append({'arm':arm,'model':name,**scores(y[masks['test']],p,weights[masks['test']])})
    parameters['added_preprocessing']=pd.concat(added,ignore_index=True) if added else pd.DataFrame(columns=['arm','feature','median','mean','scale'])
    parameters['logistic_models']=models
    parameters['constant_prevalence']=float(np.average(y[masks['train']],weights=weights[masks['train']]))
    prediction_rows['constant_train_prevalence']=parameters['constant_prevalence']
    prediction_rows.to_csv(out/'test_predictions.csv.gz',index=False,compression={'method':'gzip','mtime':0})
    joblib.dump(parameters,out/'preprocessing_and_baselines.joblib')
    pd.DataFrame(histories).to_csv(out/'training_history.csv',index=False)
    pd.DataFrame(results).to_csv(out/'metrics.csv',index=False)
    split=target[['record_id','page_id','date']].copy(); split['split']='purged'; split['label_available']=availability.astype(str)
    for name,mask in masks.items(): split.loc[mask,'split']=name
    split.to_csv(out/'split_assignments.csv.gz',index=False)
    return {'arms':arms,'seeds':seeds,'validation_start':validation_start,'test_start':test_start,'as_of':as_of,'configuration':configuration,
            'unmatured_candidates':int((~mature).sum()),
            'split_counts':{name:int(mask.sum()) for name,mask in masks.items()},
            'bundle_sha256':{p.name:digest(p) for p in out.iterdir() if p.suffix in ('.pt','.joblib')}}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode',choices=['predict','train'])
    parser.add_argument('--claims',type=Path,required=True,help='Prepared ProQuest label CSV including all context claims')
    parser.add_argument('--features',type=Path)
    parser.add_argument('--bundle',type=Path,default=BASE_BUNDLE)
    parser.add_argument('--configuration',type=Path,help='Training settings JSON, or development bundle_manifest.json containing candidate settings')
    parser.add_argument('--start',default='1995-01'); parser.add_argument('--through',default='2010-12')
    parser.add_argument('--validation-start',default='1985-01'); parser.add_argument('--test-start',default='1995-01')
    parser.add_argument('--as-of',default='2026-10-19',help='Train only on outcome endpoints + 3 months strictly before this month')
    parser.add_argument('--arms',nargs='+',choices=list(ARMS),default=list(ARMS))
    parser.add_argument('--seeds',nargs='+',type=int,default=[11,29,47]); parser.add_argument('--epochs',type=int,default=20)
    parser.add_argument('--allow-new-years',action='store_true'); parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    if args.epochs<1 or len(args.seeds)!=len(set(args.seeds)) or len(args.arms)!=len(set(args.arms)):
        parser.error('Positive epochs and unique seeds/arms required')
    if not args.allow_new_years and pd.Period(args.through,'M').year>2010:
        parser.error('Future years require explicit --allow-new-years')
    if args.configuration and args.mode!='train': parser.error('--configuration is only for training; prediction uses the saved bundle')
    torch.set_num_threads(2); torch.use_deterministic_algorithms(True)
    labels=read_labels(args.claims,args.through,args.allow_new_years,args.mode=='train')
    inputs={str(args.claims):digest(args.claims)}
    if args.features: inputs[str(args.features)]=digest(args.features)
    configuration=training_configuration(args.configuration) if args.configuration else None
    if args.configuration: inputs[str(args.configuration)]=digest(args.configuration)
    out=new_output(args.out)
    if args.mode=='train':
        metadata=train(labels,args.features,args.validation_start,args.test_start,args.arms,args.seeds,args.epochs,out,args.as_of,configuration)
        (out/'bundle_manifest.json').write_text(json.dumps(metadata,indent=2)+'\n')
    else:
        predictions,used=predict(args.bundle,labels,args.features,args.start,args.through,args.arms)
        inputs.update({str(p):digest(p) for p in used})
        predictions.to_csv(out/'predictions.csv.gz',index=False,compression={'method':'gzip','mtime':0})
        metadata={'prediction_rows':len(predictions),'outcomes_read':False,'model_fits':0}
    for path,sha in inputs.items():
        if digest(path)!=sha: raise ValueError(f'Input changed during run: {path}')
    module_paths=['proquest_rnn.py','proquest_followups.py','proquest_polarization_models.py','proquest_rnn_permutation.py']
    if configuration: module_paths.append('proquest_rnn_development.py')
    if configuration and 'half_life_years' in configuration: module_paths.append('proquest_rnn_age_weighting.py')
    manifest={'status':'complete','mode':args.mode,'arguments':{k:str(v) if isinstance(v,Path) else v for k,v in vars(args).items()},
              'inputs_sha256':inputs,'code_sha256':digest(__file__),'metadata':metadata,
              'imported_code_sha256':{name:digest(Path(__file__).parent/name) for name in module_paths},
              'versions':{'python':platform.python_version(),'torch':torch.__version__,'numpy':np.__version__,'pandas':pd.__version__},
              'outputs_sha256':{p.name:digest(p) for p in out.iterdir() if p.is_file()}}
    (out/'run_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(out)


BASE_BUNDLE=Path('data/scored/proquest/polarization/claims')
if __name__=='__main__': main()
