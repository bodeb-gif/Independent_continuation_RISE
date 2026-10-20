"""Prespecified forward-time GRU development, using publications before 1995 only.

The inspected 1995–2010 test is never evaluated or used for selection. Existing
models/specifications remain unchanged. New bundles support the RNN runner.
"""
import copy
import hashlib
import itertools
import json
from pathlib import Path
import platform
import time

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss
from sklearn.preprocessing import OneHotEncoder, StandardScaler
import torch
from torch import nn

from proquest_rnn import CLAIM_CATEGORIES, monthly_context, sequence_indices, article_weights, neural_probabilities
from proquest_rnn_runner import REQUIRED, eligible
from proquest_rnn_permutation import scores

OUT=Path('data/scored/proquest/rnn_development_v1')
SOURCE=Path('data/scored/proquest/descriptive/scored_claims.csv.gz')
REFERENCE='gru24_standard_expanding'
SEEDS=[11,29,47]
CANDIDATES=[]
for hidden,strong,window in itertools.product([24,8],[False,True],[None,20]):
    CANDIDATES.append({'id':f"gru{hidden}_{'strong' if strong else 'standard'}_{window or 'expanding'}",
                       'hidden':hidden,'dropout':.35 if strong else .15,
                       'weight_decay':.01 if strong else .001,'window_years':window})
SPEC={
    'date':'2026-10-19','status':'Exploratory model development after earlier historical results were inspected',
    'inputs':'Annual verified ProQuest prepared labels only; all model arrays and context exclude publication dates >=1995-01. No LOC, raw sensitivity, or crisis-window exports.',
    'candidate_grid':CANDIDATES,'seeds':SEEDS,'reference':REFERENCE,
    'features':'Unchanged baseline GRU metadata and preceding 12 complete monthly contexts. No polarization feature selection in this experiment. Existing four-arm polarization results remain intact.',
    'development_origins':['1965-01','1970-01','1975-01','1980-01'],
    'confirmation_origins':['1985-01','1990-01'],
    'fold_protocol':'At origin T: fit on publications before T-5 years, use T-5 through T-1 years for stopping, and assess the next five publication years. Label endpoint+3 months must strictly precede the next stage boundary, including the end of the assessment block. A 20-year window restricts fitting dates relative to the stopping-window start. Context scalers use only months in that fitting window; claim scalers and vocabularies use only eligible fitting rows.',
    'training':{'epochs_max':20,'patience':4,'improvement':.0001,'batch_size':1024,'learning_rate':.001,'head_units':32,'gradient_clip':1.,'early_stopping':'weighted validation log loss'},
    'selection':'Equal mean of four development-fold ensemble Brier losses. Alternative must beat the rolling reference by >=0.002 on that mean and improve in >=3 of 4 folds. Among qualifying alternatives choose lowest mean, then lowest worst-fold loss, then smaller hidden dimension, then ID. Otherwise retain reference. No seed selection.',
    'confirmation':'After selection, fit only selected and reference configurations on the two later folds. No tuning after reading them. Promote only if selected improves in both folds and mean Brier improves >=0.002. Otherwise retain old baseline. These years were previously used in historical development, so this is not an untouched holdout.',
    'controls':'Metadata logistic and metadata plus flattened history logistic, C=1, on each fitting-window variant. Descriptive controls, not new candidates selected by held-out results.',
    'final_bundle':'Fit selected and reference candidates before 1990 with stopping on 1990–1994, purged at 1995. Save provisional baseline-arm bundles for the existing runner without evaluating 1995–2010. Existing production/research bundles are never replaced.',
    'limitations':'Fixed candidate search reduces flexibility but does not remove prior exploration, revised outcomes, source-label uncertainty, or dependence between folds. Do not optimize a p-value or claim significance from selection scores.'
}


def digest(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def development_labels(path=SOURCE):
    fields=list(dict.fromkeys(REQUIRED+['hit','scorable','basis']))
    parts=[]
    for chunk in pd.read_csv(path,usecols=fields,dtype={'record_id':str,'page_id':str},chunksize=25000):
        # Filter before making any model target or covariate arrays.
        chunk=chunk[chunk.date.lt('1995-01-01')].copy()
        if len(chunk): parts.append(chunk)
    frame=pd.concat(parts,ignore_index=True)
    frame['date']=pd.to_datetime(frame.date); frame['month']=frame.date.dt.to_period('M'); frame['year']=frame.date.dt.year
    if frame.record_id.duplicated().any() or frame.year.lt(1900).any() or frame.year.ge(1995).any():
        raise ValueError('Unexpected development scope or duplicate record addresses')
    if frame[['record_id','page_id','date']].isna().any().any(): raise ValueError('Missing source addresses')
    if not frame.scorable.isin([True,False]).all(): raise ValueError('Invalid eligibility flags')
    if frame.groupby('page_id').month.nunique().gt(1).any(): raise ValueError('Article spans months')
    return frame


def fold_masks(frame,origin,window_years=None,final=False):
    origin=pd.Period(origin,'M'); stop=origin-60; end=origin+60
    availability=pd.PeriodIndex([m+int(h)+3 for m,h in zip(frame.month,frame.horizon_used)],freq='M')
    lower=pd.Period('1900-01','M') if window_years is None else stop-window_years*12
    masks={'train':np.asarray((frame.month>=lower)&(frame.month<stop)&(availability<stop)),
           'stopping':np.asarray((frame.month>=stop)&(frame.month<origin)&(availability<origin))}
    if not final: masks['assessment']=np.asarray((frame.month>=origin)&(frame.month<end)&(availability<end))
    for name,mask in masks.items():
        if not mask.any() or frame.loc[mask,'hit'].nunique()!=2: raise ValueError(f'Insufficient classes in {name} at {origin}')
    sets=[set(frame.loc[mask,'page_id']) for mask in masks.values()]
    if any(a&b for a,b in itertools.combinations(sets,2)): raise ValueError('Article crosses stages')
    return masks,availability,lower,stop


def prepare_fold(labels,origin,window_years=None,final=False):
    frame=labels[eligible(labels)&labels.scorable&labels.basis.ne('NBER proxy')].copy().reset_index(drop=True)
    if not frame.hit.isin([0,1]).all(): raise ValueError('Nonbinary deterministic outcome')
    masks,availability,lower,stop=fold_masks(frame,origin,window_years,final)
    selected=np.logical_or.reduce(list(masks.values()))
    frame=frame[selected].reset_index(drop=True); availability=availability[selected]
    masks={name:mask[selected] for name,mask in masks.items()}
    # Keep only context available up to the end of this fold.
    last=pd.Period(origin,'M')-1 if final else pd.Period(origin,'M')+59
    context=monthly_context(labels[labels.month<=last])
    fit_context=context.loc[(context.index>=lower)&(context.index<stop)]
    # Match the original padded calendar on expanding fits.
    if window_years is None: fit_context=context.loc[context.index<stop]
    parameters={'context_features':list(context.columns),'claim_categories':CLAIM_CATEGORIES,
                'context_scaler':StandardScaler().fit(fit_context),
                'encoder':OneHotEncoder(handle_unknown='ignore',sparse_output=False,dtype=np.float32).fit(frame.loc[masks['train'],CLAIM_CATEGORIES].fillna('missing')),
                'horizon_scaler':StandardScaler().fit(frame.loc[masks['train'],['horizon_used']]),
                'added_preprocessing':pd.DataFrame(columns=['arm','feature','median','mean','scale'])}
    sequence=parameters['context_scaler'].transform(context).astype('float32')[sequence_indices(frame.month,context.index)]
    claim=np.column_stack([parameters['encoder'].transform(frame[CLAIM_CATEGORIES].fillna('missing')),
                           parameters['horizon_scaler'].transform(frame[['horizon_used']])]).astype('float32')
    weights=np.ones(len(frame),dtype='float32')
    for mask in masks.values(): weights[mask]=article_weights(frame[mask])
    return {'frame':frame,'masks':masks,'availability':availability,'parameters':parameters,
            'sequence':sequence,'claim':claim,'y':frame.hit.to_numpy(dtype='float32'),'weights':weights}


class DevelopmentGRU(nn.Module):
    def __init__(self,context_size,claim_size,hidden=24,dropout=.15):
        super().__init__()
        self.gru=nn.GRU(context_size,hidden,batch_first=True)
        self.head=nn.Sequential(nn.Linear(hidden+claim_size,32),nn.ReLU(),nn.Dropout(dropout),nn.Linear(32,1))
    def forward(self,context,claim):
        _,h=self.gru(context)
        return self.head(torch.cat([h[-1],claim],dim=1)).squeeze(1)


def fit_seed(data,config,seed,epochs=20):
    torch.manual_seed(seed); rng=np.random.default_rng(seed)
    context=torch.from_numpy(data['sequence']); claim=torch.from_numpy(data['claim'])
    y=torch.from_numpy(data['y']); w=torch.from_numpy(data['weights'])
    model=DevelopmentGRU(context.shape[-1],claim.shape[-1],config['hidden'],config['dropout'])
    optimizer=torch.optim.AdamW(model.parameters(),lr=.001,weight_decay=config['weight_decay'])
    loss_fn=nn.BCEWithLogitsLoss(reduction='none')
    training=np.flatnonzero(data['masks']['train']); validation=np.flatnonzero(data['masks']['stopping'])
    best=np.inf; state=None; stalled=0; history=[]; best_epoch=None
    for epoch in range(1,epochs+1):
        model.train(); loss_sum=0
        for idx in np.array_split(rng.permutation(training),int(np.ceil(len(training)/1024))):
            optimizer.zero_grad(); loss=(loss_fn(model(context[idx],claim[idx]),y[idx])*w[idx]).mean()
            loss.backward(); nn.utils.clip_grad_norm_(model.parameters(),1.); optimizer.step()
            loss_sum+=loss.item()*len(idx)
        p=neural_probabilities(model,context[validation],claim[validation])
        value=log_loss(data['y'][validation],p,sample_weight=data['weights'][validation],labels=[0,1])
        history.append({'seed':seed,'epoch':epoch,'train_loss':loss_sum/len(training),'stopping_log_loss':value})
        if value<best-.0001: best=value; state=copy.deepcopy(model.state_dict()); best_epoch=epoch; stalled=0
        else: stalled+=1
        if stalled>=4: break
    model.load_state_dict(state); model.eval()
    return model,history,best_epoch


def fit_controls(data):
    models={}
    for name in ['logistic_metadata','logistic_metadata_history']:
        x=data['claim'] if name=='logistic_metadata' else np.column_stack([data['claim'],data['sequence'].reshape(len(data['y']),-1)])
        model=LogisticRegression(C=1.,solver='lbfgs',max_iter=1500)
        mask=data['masks']['train']; model.fit(x[mask],data['y'][mask],sample_weight=data['weights'][mask])
        models[f'{name}__baseline']=model
    return models


def save_split(data,path):
    frame=data['frame'][['record_id','page_id','date']].copy(); frame['label_available']=data['availability'].astype(str)
    for stage,mask in data['masks'].items(): frame.loc[mask,'stage']=stage
    frame.to_csv(path,index=False,compression={'method':'gzip','mtime':0})


def run_candidate(data,config,path,final=False):
    path.mkdir(parents=True,exist_ok=True); histories=[]; ps=[]; seed_metrics=[]
    mask=data['masks']['stopping' if final else 'assessment']
    for seed in SEEDS:
        model,history,best=fit_seed(data,config,seed)
        histories+=history
        torch.save({'state_dict':model.state_dict(),'context_size':data['sequence'].shape[-1],
                    'claim_size':data['claim'].shape[-1],'hidden_size':config['hidden'],'dropout':config['dropout'],
                    'seed':seed,'best_epoch':best,'arm':'baseline','added_features':[],'configuration':config},path/f'gru_baseline_{seed}.pt')
        p=neural_probabilities(model,torch.from_numpy(data['sequence'][mask]),torch.from_numpy(data['claim'][mask])); ps.append(p)
        seed_metrics.append({'seed':seed,'selected_epoch':best,**scores(data['y'][mask],p,data['weights'][mask])})
    p=np.mean(ps,axis=0)
    prediction=data['frame'].loc[mask,['record_id','page_id','date','year','hit']].copy()
    for seed,prob in zip(SEEDS,ps): prediction[f'gru_seed_{seed}__baseline']=prob
    prediction['gru_ensemble__baseline']=p
    prediction.to_csv(path/'predictions.csv.gz',index=False,compression={'method':'gzip','mtime':0})
    pd.DataFrame(histories).to_csv(path/'training_history.csv',index=False)
    pd.DataFrame(seed_metrics).to_csv(path/'seed_metrics.csv',index=False)
    result={'candidate':config['id'],'n_claims':int(mask.sum()),'n_articles':prediction.page_id.nunique(),
            **scores(data['y'][mask],p,data['weights'][mask])}
    (path/'metrics.json').write_text(json.dumps(result,indent=2)+'\n')
    print(f"Completed {path}: Brier {result['brier']:.5f}",flush=True)
    return result


def select_candidate(results):
    table=results.pivot(index='candidate',columns='origin',values='brier')
    if table.isna().any().any() or len(table)!=len(CANDIDATES) or table.shape[1]!=4:
        raise ValueError('Incomplete candidate comparison')
    base=table.loc[REFERENCE]; rows=[]
    for config in CANDIDATES:
        values=table.loc[config['id']]; gain=base-values
        rows.append({'candidate':config['id'],'mean_brier':values.mean(),'worst_brier':values.max(),
                     'mean_improvement':gain.mean(),'folds_improved':int((gain>0).sum()),'hidden':config['hidden'],
                     'qualifies':bool(config['id']!=REFERENCE and gain.mean()>=.002 and (gain>0).sum()>=3)})
    ranking=pd.DataFrame(rows).sort_values(['mean_brier','worst_brier','hidden','candidate'])
    candidates=ranking[ranking.qualifies]
    choice=candidates.candidate.iloc[0] if len(candidates) else REFERENCE
    return choice,ranking


def main():
    torch.set_num_threads(2); torch.use_deterministic_algorithms(True)
    if OUT.exists(): raise ValueError('Development output exists; preserve it and use a new study version')
    OUT.mkdir(parents=True)
    (OUT/'specification.json').write_text(json.dumps(SPEC,indent=2)+'\n')
    frozen=json.loads(Path('data/scored/proquest/modern_readiness/model_freeze.json').read_text())['files_sha256']
    for path,sha in frozen.items():
        if digest(path)!=sha: raise ValueError(f'Frozen original changed: {path}')
    prior=json.loads(Path('data/scored/proquest/rnn/summary.json').read_text())
    if digest(SOURCE)!=prior['score_file_sha256']: raise ValueError('Historical score snapshot changed')
    source_hash=digest(SOURCE); labels=development_labels(); started=time.monotonic(); results=[]; controls=[]
    for origin in SPEC['development_origins']:
        for window in [None,20]:
            data=prepare_fold(labels,origin,window); parent=OUT/'development'/origin/(str(window) if window else 'expanding'); parent.mkdir(parents=True)
            save_split(data,parent/'split_assignments.csv.gz')
            models=fit_controls(data); params=dict(data['parameters'],logistic_models=models)
            joblib.dump(params,parent/'preprocessing_and_baselines.joblib')
            mask=data['masks']['assessment']
            for name,model in models.items():
                x=data['claim'] if name.startswith('logistic_metadata__') else np.column_stack([data['claim'],data['sequence'].reshape(len(data['y']),-1)])
                p=model.predict_proba(x[mask])[:,list(model.classes_).index(1)]
                controls.append({'origin':origin,'window_years':window or 'expanding','model':name,**scores(data['y'][mask],p,data['weights'][mask])})
            for config in [c for c in CANDIDATES if c['window_years']==window]:
                result=run_candidate(data,config,parent/config['id']); results.append(dict(origin=origin,**result))
                pd.DataFrame(results).to_csv(OUT/'development_metrics.csv',index=False)
    selected,ranking=select_candidate(pd.DataFrame(results))
    ranking.to_csv(OUT/'development_ranking.csv',index=False); pd.DataFrame(controls).to_csv(OUT/'logistic_controls.csv',index=False)
    decision={'selected':selected,'selection_completed_before_confirmation':True,'primary_test_1995_2010_used':False}
    (OUT/'selection.json').write_text(json.dumps(decision,indent=2)+'\n')
    print(f'Selected before confirmation: {selected}',flush=True)
    confirmation=[]
    for origin in SPEC['confirmation_origins']:
        for name in dict.fromkeys([REFERENCE,selected]):
            config=next(c for c in CANDIDATES if c['id']==name); data=prepare_fold(labels,origin,config['window_years'])
            path=OUT/'confirmation'/origin/name
            result=run_candidate(data,config,path); save_split(data,path/'split_assignments.csv.gz')
            confirmation.append(dict(origin=origin,**result))
            pd.DataFrame(confirmation).to_csv(OUT/'confirmation_metrics.csv',index=False)
    confirmation=pd.DataFrame(confirmation)
    table=confirmation.pivot(index='candidate',columns='origin',values='brier'); gain=table.loc[REFERENCE]-table.loc[selected]
    decision.update(confirmation_mean_improvement=float(gain.mean()),confirmation_folds_improved=int((gain>0).sum()),
                    promote=bool(selected!=REFERENCE and gain.mean()>=.002 and (gain>0).all()))
    (OUT/'selection.json').write_text(json.dumps(decision,indent=2)+'\n')
    for name in dict.fromkeys([REFERENCE,selected]):
        config=next(c for c in CANDIDATES if c['id']==name); data=prepare_fold(labels,'1995-01',config['window_years'],final=True)
        path=OUT/'bundles'/name; run_candidate(data,config,path,final=True)
        models=fit_controls(data); parameters=dict(data['parameters'],logistic_models=models)
        parameters['constant_prevalence']=float(np.average(data['y'][data['masks']['train']],weights=data['weights'][data['masks']['train']]))
        joblib.dump(parameters,path/'preprocessing_and_baselines.joblib'); save_split(data,path/'split_assignments.csv.gz')
        manifest={'candidate':config,'arms':['baseline'],'seeds':SEEDS,'fit_before':'1990-01','stopping_end_exclusive':'1995-01',
                  'status':'Provisional development bundle; no 1995–2010 evaluation; original artifacts unchanged',
                  'promoted_by_confirmation':bool(decision['promote'] and name==selected),
                  'bundle_sha256':{p.name:digest(p) for p in path.iterdir() if p.suffix in ('.pt','.joblib')}}
        (path/'bundle_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    report(ranking,pd.DataFrame(results),confirmation,decision)
    for path,sha in frozen.items():
        if digest(path)!=sha: raise ValueError('Original frozen artifact changed')
    if digest(SOURCE)!=source_hash: raise ValueError('Input changed')
    summary={'status':'complete','decision':decision,'seconds':time.monotonic()-started,'source_sha256':source_hash,
             'code_sha256':digest(__file__),'prior_artifacts_verified_unchanged':True,'latest_input_month':str(labels.month.max()),
             'model_fits':len(results)*3+len(confirmation)*3+len(dict.fromkeys([REFERENCE,selected]))*3,
             'versions':{'python':platform.python_version(),'torch':torch.__version__,'numpy':np.__version__,'pandas':pd.__version__},
             'outputs_sha256':{str(p):digest(p) for p in OUT.rglob('*') if p.is_file() and p.name!='summary.json'}}
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(decision,indent=2),flush=True)


def report(ranking,development,confirmation,decision):
    html='''<!doctype html><html lang="en"><meta charset="utf-8"><title>Forward time RNN development</title><style>body{font:16px/1.6 system-ui;max-width:1100px;margin:40px auto;padding:20px}td,th{padding:8px;border-bottom:1px solid #ddd}.table{overflow:auto}</style><h1>Forward time RNN development</h1><p>All model arrays exclude 1995 onward. Eight prespecified configurations, three retained seeds, four development folds, then two later confirmation folds. Prior historical exploration means this is not a fresh holdout. No p-value selection or source validation.</p>'''
    html+=f"<p>Selected: {decision['selected']}. Later mean Brier improvement: {decision['confirmation_mean_improvement']:.5f}. Passed promotion rule: {decision['promote']}.</p>"
    for title,table in [('Development ranking',ranking),('Development by fold',development),('Later confirmation',confirmation)]:
        html+=f'<h2>{title}</h2><div class="table">'+table.to_html(index=False,border=0,float_format=lambda v:f'{v:.5f}')+'</div>'
    html+='<p>Lower Brier is better. Selection weights the four eras equally; every era uses equal article weights. A candidate must improve mean Brier by at least 0.002 and win three development folds. Promotion requires improvement in both later folds and at least 0.002 mean improvement. Epochs use an earlier stopping window, never the assessment block. Provisional bundles are compatible with proquest_rnn_runner.py predict --arms baseline. The existing baseline and all polarization arms remain unchanged.</p></html>'
    (OUT/'report.html').write_text(html)


if __name__=='__main__': main()
