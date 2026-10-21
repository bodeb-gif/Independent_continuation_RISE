"""Separate exploratory monthly downturn targets; never reinterpret claim RNN scores.

Rules and candidate selection are in MODERN_ANALYSIS_AMENDMENT_20261020.md.
Only lagged press and observed-vote features enter classifiers. Revised economic
series supply retrospective labels, not predictor values.
"""
from pathlib import Path
import json
import warnings
import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.exceptions import ConvergenceWarning

from proquest_panel import FEATURES
from proquest_modern_analysis import OUT, AS_OF, binary_metrics, paired_blocks, digest, write_json, freeze_check

MODELS={'historical_base_rate':(), 'press':FEATURES,
        'press_political':FEATURES+('political_polarization',),
        'press_forecast':FEATURES+('forecast_polarization',),
        'press_both':FEATURES+('political_polarization','forecast_polarization')}
TARGETS={'recession_onset_12m':24,'production_decline_12m':3,'production_decline_gt2pct_12m':3}

def read_series(name):
    f=pd.read_csv(OUT/'reference'/f'fred_{name}.csv')
    s=pd.Series(pd.to_numeric(f.iloc[:,1],errors='coerce').to_numpy(),index=pd.PeriodIndex(f.iloc[:,0],freq='M')).dropna()
    if not s.index.is_unique:raise ValueError('Duplicate reference month')
    return s

def make_targets(origins,production,recession,name):
    rows=[];lag=TARGETS[name]
    for origin in origins:
        start,end=origin-1,origin+11
        values=(recession if name=='recession_onset_12m' else production).reindex(pd.period_range(start,end,freq='M'))
        target=np.nan;change=np.nan;onsets=[]
        if values.notna().all():
            if name=='recession_onset_12m':
                if not values.isin([0,1]).all():raise ValueError('Nonbinary recession reference')
                onsets=[str(values.index[i]) for i in range(1,len(values)) if values.iloc[i-1]==0 and values.iloc[i]==1]
                target=int(bool(onsets))
            elif values.iloc[0]>0:
                change=100*(values.iloc[-1]/values.iloc[0]-1)
                threshold=-2 if name=='production_decline_gt2pct_12m' else 0
                target=int(change<threshold and not np.isclose(change,threshold,atol=1e-10,rtol=1e-10))
        rows.append(dict(origin=origin,target=target,label_available=end+lag,target_start=start,target_end=end,
                         change_percent=change,onset_months=';'.join(onsets)))
    return pd.DataFrame(rows)

def training_rows(frame,refit):
    return frame[(frame.origin<refit)&(frame.label_available<refit)&frame.target.notna()].copy()

def fit_probability(train,evaluation,features):
    y=train.target.to_numpy(int)
    if not features:
        prior=(y.sum()+1)/(len(y)+2)
        return np.full(len(evaluation),prior),dict(prior=float(prior))
    if len(np.unique(y))<2:raise ValueError('Training requires two classes')
    x=train[list(features)].astype(float);z=evaluation[list(features)].astype(float)
    medians=x.median().fillna(0);scaler=StandardScaler().fit(x.fillna(medians))
    a=np.column_stack([scaler.transform(x.fillna(medians)),x.isna()])
    b=np.column_stack([scaler.transform(z.fillna(medians)),z.isna()])
    model=LogisticRegression(C=1.,solver='lbfgs',max_iter=2000,random_state=20261014)
    with warnings.catch_warnings():
        warnings.simplefilter('error',ConvergenceWarning);model.fit(a,y)
    return model.predict_proba(b)[:,list(model.classes_).index(1)],dict(model=model,features=features,medians=medians,scaler=scaler)

def rolling(frame,first,last,output=None,save_year=None):
    rows=[];audits=[]
    for year in range(first,last+1):
        refit=pd.Period(f'{year}-01','M');train=training_rows(frame,refit)
        test=frame[frame.origin.dt.year.eq(year)].copy()
        if len(train)<120 or test.empty:continue
        if train.label_available.max()>=refit:raise AssertionError('Immature training label')
        for model,features in MODELS.items():
            p,bundle=fit_probability(train,test,features)
            test[model]=p
            if output is not None and year==save_year:
                joblib.dump(dict(refit=str(refit),last_training_origin=str(train.origin.max()),
                    latest_training_label_available=str(train.label_available.max()),**bundle),output/f'{model}.joblib')
        audits.append(dict(year=year,n_training=len(train),positive_training_months=int(train.target.sum()),
            latest_training_origin=str(train.origin.max()),latest_training_label_available=str(train.label_available.max())))
        rows.append(test)
    return pd.concat(rows,ignore_index=True),pd.DataFrame(audits)

def choose_historical(predicted):
    # Caller supplies only pre-2011 predictions; no modern candidate selection.
    if (predicted.origin.dt.year>=2011).any():raise ValueError('Modern results in model selection')
    valid=predicted[predicted.target.notna() & (predicted.label_available<pd.Period('2011-01','M'))]
    scores=[dict(model=m,**binary_metrics(valid.target,valid[m])) for m in MODELS]
    best=min(range(len(scores)),key=lambda i:scores[i]['brier'])
    return scores[best]['model'],scores

def main():
    freeze_check();dest=OUT/'downturn'
    if dest.exists():raise ValueError('Downturn output exists; do not overwrite results')
    dest.mkdir()
    raw=pd.read_csv(OUT/'monthly_features.csv');raw['origin']=pd.PeriodIndex(raw.origin,freq='M')
    feature=raw[raw.origin>=pd.Period('1919-02','M')].copy()
    if feature.origin.duplicated().any():raise ValueError('Duplicate origin')
    production,recession=read_series('INDPRO'),read_series('USREC')
    summary={};all_metrics=[]
    for name in TARGETS:
        d=dest/name;d.mkdir()
        target=make_targets(feature.origin,production,recession,name)
        frame=feature.merge(target,on='origin',validate='one_to_one')
        # Historical candidate evaluation/selection happens before modern refits.
        historic,audit0=rolling(frame[frame.origin<pd.Period('2011-01','M')],1950,2010)
        selected,scores=choose_historical(historic)
        write_json(d/'selection_before_modern_evaluation.json',dict(selected=selected,historical_scores=scores,
            selection='Mature pre-2011 rolling origins only; already-inspected historical era, exploratory development'))
        historic.to_csv(d/'historical_predictions.csv',index=False)
        modern,audit=rolling(frame,2011,2026,d,save_year=2026)
        # Restrict evaluation to labels that have matured as of the run date.
        mask=modern.target.notna() & (modern.label_available<pd.Period(AS_OF,'M'))
        evaluated=modern[mask].copy();modern['evaluated_as_of']=mask
        modern.to_csv(d/'modern_predictions.csv',index=False)
        pd.concat([audit0,audit]).to_csv(d/'refit_audit.csv',index=False)
        frame[['origin','target','target_start','target_end','label_available','change_percent','onset_months']].to_csv(d/'outcomes.csv',index=False)
        metrics=[];cal=[];intervals=[];breakdown=[]
        for model in MODELS:
            result=dict(target=name,model=model,selected_pre2011=model==selected,**binary_metrics(evaluated.target,evaluated[model]))
            metrics.append(result);all_metrics.append(result)
            bins=np.minimum((evaluated[model]*10).astype(int),9)
            for b in range(10):
                g=evaluated[bins==b]
                if len(g):cal.append(dict(model=model,bin=b,n=len(g),predicted=float(g[model].mean()),observed=float(g.target.mean())))
            for period,g in evaluated.groupby((evaluated.origin.dt.year-2011)//5):
                breakdown.append(dict(model=model,block=int(period),**binary_metrics(g.target,g[model])))
            if model!='historical_base_rate':
                intervals.append(dict(a='historical_base_rate',b=model,**paired_blocks(evaluated.target.to_numpy(),evaluated.historical_base_rate.to_numpy(),evaluated[model].to_numpy(),evaluated.origin.dt.year.to_numpy())))
        pd.DataFrame(metrics).to_csv(d/'metrics.csv',index=False);pd.DataFrame(cal).to_csv(d/'calibration.csv',index=False)
        pd.DataFrame(breakdown).to_csv(d/'block_metrics.csv',index=False);write_json(d/'paired_intervals.json',intervals)
        latest=modern[modern.origin==pd.Period('2026-09','M')].iloc[0]
        distinct_onsets=sorted({x for value in evaluated.onset_months for x in str(value).split(';') if x})
        summary[name]=dict(selected_model=selected,latest_origin=str(latest.origin),forecast_window=['2026-09','2027-08'],
            latest_probability=float(latest[selected]),all_latest_probabilities={m:float(latest[m]) for m in MODELS},
            latest_recent_articles=int(latest.recent_articles),latest_recent_papers=int(latest.recent_papers),
            latest_observed_print_months=int(latest.recent_observed_months),latest_press_features_observed=int(latest[list(FEATURES)].notna().sum()),
            evaluated_months=len(evaluated),positive_months=int(evaluated.target.sum()),distinct_recession_onsets=distinct_onsets if name=='recession_onset_12m' else None,
            modern_evaluation_end=str(evaluated.origin.max()),training_label_lag_months=TARGETS[name],
            no_october_origin_forecast=True,revised_outcome_labels=True)
        print(name,selected,'latest',float(latest[selected]),'evaluated',len(evaluated),flush=True)
    pd.DataFrame(all_metrics).to_csv(dest/'all_metrics.csv',index=False)
    write_json(dest/'summary.json',summary)
    paths=[Path(__file__),OUT/'run_manifest.json',OUT/'monthly_features.csv',OUT/'reference/fred_INDPRO.csv',OUT/'reference/fred_USREC.csv']
    write_json(dest/'manifest.json',dict(inputs_sha256={str(p):digest(p) for p in paths},as_of=AS_OF,
        outputs_sha256={str(p):digest(p) for p in dest.rglob('*') if p.is_file()},frozen_files_unchanged=len(freeze_check()),
        limitation='Exploratory research forecast with lagged print-time features; revised labels and approximate release lags, not a real-time vintage validation.'))

if __name__=='__main__':main()
