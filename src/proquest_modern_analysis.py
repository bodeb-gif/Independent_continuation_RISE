"""Exploratory modern analysis authorized in the dated October 20 amendment.

Never changes the original frozen readiness gate, source exports or models.
Preparation and prediction do not use modern outcome columns as features.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil

import numpy as np
import pandas as pd
import torch
from sklearn.metrics import average_precision_score, roc_auc_score, log_loss

import proquest_descriptive as desc
import proquest_panel as panel
import proquest_polarization as pol
from proquest_prepare_inputs import normalize, combine_history, attach_outcomes
from proquest_rnn_runner import predict, read_labels, REQUIRED
from proquest_rnn import article_weights
from proquest_export_receipt import inspect_archive

BASE=Path('data/scored/proquest')
OUT=BASE/'modern_analysis_v1'
PACKAGE=Path('data/proquest/modern/20261020')
AS_OF='2026-10-20'
AMENDMENT=Path('docs/publication/MODERN_ANALYSIS_AMENDMENT_20261020.md')

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write_json(path,value):Path(path).write_text(json.dumps(value,indent=2,default=str,allow_nan=False)+'\n')
def freeze_check():
    frozen=json.loads((BASE/'modern_readiness/model_freeze.json').read_text())['files_sha256']
    for p,h in frozen.items():
        if digest(p)!=h:raise ValueError(f'Frozen artifact changed: {p}')
    return frozen

def modern_labels(package):
    """Explicit export-format adapter under the dated exploratory amendment."""
    _,receipt=inspect_archive(package/'source_archive.tar.xz')
    m=json.loads((package/'manifest.json').read_text())
    excluded={f"{r['year']}:{r['source_line']}" for r in m['exceptions']}
    rows=[];counts=Counter();exclusions=[]
    for e in m['files']:
        p=package/e['path']
        if digest(p)!=e['sha256']:raise ValueError('Imported export changed')
        for number,line in enumerate(p.read_text().splitlines(),1):
            if not line.strip():continue
            r=json.loads(line);rid=f"{e['year']}:{number}"
            if r.get('no_predictions') is True:
                counts['empty_rows_excluded']+=1;continue
            if rid in excluded:
                exclusions.append(dict(record_id=rid,page_id=str(r['page_id']),reason='default_kept_verification_exception'))
                continue
            h,b,_=desc.horizon(r)
            rows.append(dict(record_id=rid,page_id=str(r['page_id']),date=r['date'],scope=r.get('scope'),
                topic=r.get('topic'),paper=desc.paper_name(r.get('publisher') or r.get('newspaper_title')),
                voice=r.get('voice'),confidence=r.get('confidence'),predicted_norm=desc.predicted_norm(r),horizon_basis=b,horizon_used=h))
    frame=pd.DataFrame(rows)
    if frame.record_id.duplicated().any():raise ValueError('Duplicate source address')
    counts['claims_after_exception_exclusion']=len(frame);counts['verification_exceptions_excluded']=len(exclusions)
    return frame,pd.DataFrame(exclusions),dict(counts)

def make_panels(modern):
    f=modern[modern.scope.eq('national') & modern.topic.isin(panel.TOPICS)].copy()
    f['sign']=f.predicted_norm.map({'improve':'positive','up':'positive','worsen':'negative','down':'negative','flat':'flat'})
    jobs=f.topic.eq('employment');f.loc[jobs,'sign']=f.loc[jobs,'predicted_norm'].map({'down':'positive','up':'negative','flat':'flat'})
    f=f[f.sign.notna()];f['month']=pd.PeriodIndex(pd.to_datetime(f.date),freq='M')
    _,paper,national=panel.build_panels(f,pd.period_range('2011-01','2026-09',freq='M'))
    old=BASE/'monthly_information'
    frames=[]
    for name,new in [('newspaper_topic_month.csv.gz',paper),('national_topic_month.csv.gz',national)]:
        historical=pd.read_csv(old/name);historical['month']=pd.PeriodIndex(historical.month,freq='M')
        all_rows=pd.concat([historical,new],ignore_index=True)
        all_rows.to_csv(OUT/name,index=False,compression={'method':'gzip','mtime':0});frames.append(all_rows)
    paper,national=frames
    origins=pd.period_range('1900-01','2026-09',freq='M')
    support=panel.forecast_features(paper,national,origins)
    forecast=pol.forecast_months(national,support,origins)
    return support,forecast

def political_features():
    old=BASE/'polarization';cache=old/'source_cache'
    members=pd.read_csv(cache/'HSall_members.csv',usecols=['congress','chamber','icpsr','party_code'])
    calls=pd.read_csv(cache/'HSall_rollcalls.csv',usecols=['congress','chamber','rollnumber','date'])
    previous=pd.read_csv(old/'rollcall_separation.csv.gz');previous['date']=pd.to_datetime(previous.date)
    pieces=[previous];audits=[]
    for c in range(112,120):
        path=OUT/'reference/voteview'/f'H{c:03d}_votes.csv'
        if not path.exists():raise ValueError(f'Missing modern vote input: {path}')
        votes=pd.read_csv(path,usecols=['congress','chamber','rollnumber','icpsr','cast_code'])
        # Unlike stripped claims, member votes have an event/member identity.
        # Collapse only identical keyed casts; the frozen function still rejects
        # conflicting casts for a member/rollcall. Preserve the source CSV.
        repeats=int(votes.duplicated().sum())
        votes=votes.drop_duplicates()
        piece,audit=pol.party_separation(votes,members[members.congress.eq(c)],calls[calls.congress.eq(c)])
        pieces.append(piece);audits.append(dict(congress=c,identical_cast_repeats_excluded=repeats,**audit))
    all_calls=pd.concat(pieces,ignore_index=True)
    if all_calls.duplicated(['congress','chamber','rollnumber']).any():raise ValueError('Overlapping vote histories')
    all_calls.to_csv(OUT/'rollcall_separation.csv.gz',index=False,compression={'method':'gzip','mtime':0})
    write_json(OUT/'rollcall_audit.json',audits)
    return pol.political_months(all_calls,pd.period_range('1900-01','2026-09',freq='M'))

def prepare():
    frozen=freeze_check();OUT.mkdir(exist_ok=True,parents=True)
    if (OUT/'run_manifest.json').exists():raise ValueError('Prepared run already exists')
    modern,excluded,counts=modern_labels(PACKAGE)
    old,old_meta=normalize(Path('data/proquest/verified'),1900,2010)
    combined=combine_history(old,modern)
    combined.to_csv(OUT/'labels.csv.gz',index=False,compression={'method':'gzip','mtime':0})
    excluded.to_csv(OUT/'excluded_verification_exceptions.csv',index=False)
    support,forecast=make_panels(modern);political=political_features()
    feature=political.merge(forecast,on='origin',validate='one_to_one')
    feature.to_csv(OUT/'polarization_features.csv',index=False)
    support['origin']=support.origin.astype(str)
    support.merge(feature,on='origin',validate='one_to_one').to_csv(OUT/'monthly_features.csv',index=False)
    # Reuse the original outcome snapshots if the provider's CSV endpoint fails.
    ref=OUT/'reference';ref.mkdir(exist_ok=True)
    references=[]
    for name in ['fred_INDPRO.csv','fred_USREC.csv','fred_UNRATE.csv','fred_CPIAUCNS.csv','shiller_ie_data.xls']:
        target=ref/name
        source=Path('data/reference/proquest')/name
        provenance='Downloaded public snapshot in this run'
        if not target.exists():
            shutil.copyfile(source,target);provenance='Unchanged original local snapshot; not newly retrieved'
        references.append(dict(file=str(target),sha256=digest(target),provenance=provenance))
    tracked={str(p):digest(p) for p in [AMENDMENT,Path(__file__),PACKAGE/'manifest.json',*list((PACKAGE/'verified').glob('*.jsonl'))]}
    tracked.update(old_meta['inputs_sha256']);tracked.update(frozen)
    for p in list(ref.rglob('*'))+[BASE/'polarization/source_cache/HSall_members.csv',BASE/'polarization/source_cache/HSall_rollcalls.csv']:
        if p.is_file():tracked[str(p)]=digest(p)
    write_json(OUT/'run_manifest.json',dict(as_of=AS_OF,status='exploratory_modern_scope_activated',
        prior_modern_outcome_exposure='unknown; process-validation answer does not establish no exposure',
        end_to_end_intake_certified=False,counts=counts,reference_snapshots=references,
        primary='frozen GRU baseline ensemble',challenger='historically selected gru8_standard_20',
        latest_complete_print_month='2026-08',latest_monthly_origin='2026-09',inputs_sha256=tracked,
        feature_sha256={str(OUT/n):digest(OUT/n) for n in ['labels.csv.gz','monthly_features.csv','polarization_features.csv']}))
    print('Preparation complete',counts,flush=True)

def binary_metrics(y,p,w=None):
    y=np.asarray(y,int);p=np.asarray(p,float);w=np.ones(len(y)) if w is None else np.asarray(w,float)
    if not np.isfinite(p).all() or ((p<0)|(p>1)).any():raise ValueError('Invalid prediction')
    return dict(n=len(y),prevalence=float(np.average(y,weights=w)),brier=float(np.average((p-y)**2,weights=w)),
        log_loss=float(log_loss(y,p,sample_weight=w,labels=[0,1])),accuracy=float(np.average((p>=.5)==y,weights=w)),
        roc_auc=float(roc_auc_score(y,p,sample_weight=w)) if len(np.unique(y))==2 else None,
        average_precision=float(average_precision_score(y,p,sample_weight=w)) if len(np.unique(y))==2 else None)

def paired_blocks(y,a,b,years,weights=None,anchor=2011,draws=2000):
    """Loss of a minus loss of b, paired complete publication-time blocks."""
    w=np.ones(len(y)) if weights is None else np.asarray(weights)
    block=(np.asarray(years)-anchor)//5; unique=np.unique(block)
    delta=(np.asarray(a)-y)**2-(np.asarray(b)-y)**2
    sums=np.array([np.sum(w[block==k]*delta[block==k]) for k in unique])
    masses=np.array([np.sum(w[block==k]) for k in unique])
    rng=np.random.default_rng(20261014);ix=rng.integers(0,len(unique),(draws,len(unique)))
    values=sums[ix].sum(axis=1)/masses[ix].sum(axis=1)
    return dict(delta_brier_a_minus_b=float(np.average(delta,weights=w)),low=float(np.quantile(values,.025)),high=float(np.quantile(values,.975)),
        n_blocks=len(unique),block_sizes={str(int(k)):int(sum(block==k)) for k in unique},draws=draws)

def claim_evaluation():
    freeze_check();torch.set_num_threads(2)
    manifest=json.loads((OUT/'run_manifest.json').read_text())
    for p,h in {**manifest['inputs_sha256'],**manifest['feature_sha256']}.items():
        if digest(p)!=h:raise ValueError(f'Changed run input: {p}')
    labels=read_labels(OUT/'labels.csv.gz','2026-09',allow_new_years=True)
    primary=BASE/'polarization/claims';feature=OUT/'polarization_features.csv'
    # Exact old support reproduction, including all four polarization arms.
    old_labels=labels[labels.year<=2010].copy()
    reproduction,_=predict(primary,old_labels,BASE/'polarization/features.csv','1995-01','2010-12',list(pol_models_arms()))
    saved=pd.read_csv(primary/'test_predictions.csv.gz',dtype={'record_id':str,'page_id':str})
    joined=saved.merge(reproduction,on='record_id',suffixes=('_saved','_new'),validate='one_to_one')
    audits={}
    for c in [c for c in saved if c.startswith(('gru_','logistic_'))]:
        error=float(np.max(np.abs(joined[c+'_saved']-joined[c+'_new'])))
        if error>1e-5:raise ValueError(f'Historical reproduction failure: {c} {error}')
        audits[c]=error
    if len(joined)!=len(saved):raise ValueError('Historical support lost')
    write_json(OUT/'historical_reproduction.json',dict(rows=len(joined),maximum_probability_errors=audits))
    predictions,_=predict(primary,labels,feature,'2011-01','2026-09',list(pol_models_arms()))
    challenger,_=predict(BASE/'rnn_development_v1/bundles/gru8_standard_20',labels,None,'2011-01','2026-09',['baseline'])
    predictions=predictions.merge(challenger[['record_id','gru_ensemble__baseline']].rename(columns={'gru_ensemble__baseline':'gru8_historical_challenger'}),on='record_id',validate='one_to_one')
    # Predictions are saved before modern outcomes are attached/opened.
    predictions.to_csv(OUT/'claim_predictions.csv.gz',index=False,compression={'method':'gzip','mtime':0})
    modern=labels[labels.year>=2011].copy();modern['date']=modern.date.dt.strftime('%Y-%m-%d')
    desc.REF=OUT/'reference';series,refs=desc.load_reference()
    scored=attach_outcomes(modern,series,AS_OF)
    scored.to_csv(OUT/'claim_outcomes.csv.gz',index=False,compression={'method':'gzip','mtime':0})
    test=scored[scored.scorable].merge(predictions.drop(columns=['page_id','date','year']),on='record_id',validate='one_to_one')
    cols=[f'{model}__{arm}' for arm in pol_models_arms() for model in ['gru_ensemble','logistic_metadata','logistic_metadata_history']]+['gru8_historical_challenger']
    w=article_weights(test);y=test.hit.to_numpy(int)
    metrics=[];breakdowns=[];cal=[]
    for c in cols:
        metrics.append(dict(model=c,weighting='equal_article',**binary_metrics(y,test[c],w)))
        metrics.append(dict(model=c,weighting='equal_claim',**binary_metrics(y,test[c])))
        bins=np.minimum((test[c]*10).astype(int),9)
        for b in range(10):
            mask=bins==b
            if mask.any():cal.append(dict(model=c,bin=b,n=int(mask.sum()),predicted=float(np.average(test.loc[mask,c],weights=w[mask])),observed=float(np.average(y[mask],weights=w[mask]))))
        for group in ['year','topic','horizon_basis']:
            for value,g in test.groupby(group):
                breakdowns.append(dict(model=c,group=group,value=str(value),**binary_metrics(g.hit,g[c],article_weights(g))))
    pd.DataFrame(metrics).to_csv(OUT/'claim_metrics.csv',index=False)
    pd.DataFrame(breakdowns).to_csv(OUT/'claim_breakdowns.csv',index=False)
    pd.DataFrame(cal).to_csv(OUT/'claim_calibration.csv',index=False)
    paired=[]
    for c in cols:
        if c=='gru_ensemble__baseline':continue
        paired.append(dict(a='gru_ensemble__baseline',b=c,**paired_blocks(y,test['gru_ensemble__baseline'].to_numpy(),test[c].to_numpy(),test.year.to_numpy(),w)))
    write_json(OUT/'claim_paired_intervals.json',paired)
    summary=dict(scored_claims=len(test),scored_articles=test.page_id.nunique(),predicted_claims=len(predictions),
        exclusions=scored.unscorable_reason.fillna('scored').value_counts().to_dict(),references=refs,
        outcome='claim_correctness_not_downturn_probability',no_modern_fitting=True,model_freeze_unchanged=len(freeze_check()))
    write_json(OUT/'claim_summary.json',summary)
    print('CLAIM RESULTS',pd.DataFrame(metrics).query("weighting=='equal_article'")[['model','brier','roc_auc']].to_string(index=False),flush=True)

def pol_models_arms():return ('baseline','political','forecast','both')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('stage',choices=['prepare','claims']);a=p.parse_args()
    prepare() if a.stage=='prepare' else claim_evaluation()
