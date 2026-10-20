"""Rebuild polarization for explicit prepared claims, dates and rollcall inputs.

Uses the frozen measurement definitions. Does not download voting data, score
claims, fit models, or establish completeness of supplied source coverage.
"""
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
from proquest_panel import TOPICS,build_panels,forecast_features
from proquest_polarization import political_months,forecast_months
from proquest_rnn_runner import read_labels,new_output,digest


def build(labels,rollcalls,start,through):
    origins=pd.period_range(start,through,freq='M')
    if not len(origins):raise ValueError('Empty feature date range')
    claims=labels[labels.scope.eq('national') & labels.topic.isin(TOPICS) & (labels.month<=origins.max())].copy()
    def sign(row):
        mapping={'down':'positive','up':'negative','flat':'flat'} if row.topic=='employment' else {
            'improve':'positive','up':'positive','worsen':'negative','down':'negative','flat':'flat'}
        return mapping.get(row.predicted_norm)
    claims['sign']=claims.apply(sign,axis=1);claims=claims[claims.sign.notna()]
    if claims.empty:raise ValueError('No readable national context claims')
    calendar=pd.period_range(min(claims.month.min(),origins.min()-3),origins.max(),freq='M')
    _,paper,national=build_panels(claims,calendar)
    votes=rollcalls.copy();votes['date']=pd.to_datetime(votes.date)
    keys=['congress','chamber','rollnumber']
    if votes[keys+['date','political_gap']].isna().any().any() or votes.duplicated(keys).any():raise ValueError('Invalid rollcall addresses')
    if not votes.chamber.eq('House').all() or not votes.political_gap.between(0,1).all():raise ValueError('Invalid rollcall separation values')
    support=forecast_features(paper,national,origins)
    return political_months(votes,origins).merge(forecast_months(national,support,origins),on='origin',validate='one_to_one')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--claims',type=Path,required=True)
    p.add_argument('--rollcalls',type=Path,required=True);p.add_argument('--start',required=True);p.add_argument('--through',required=True)
    p.add_argument('--allow-new-years',action='store_true');p.add_argument('--out',type=Path,required=True);args=p.parse_args()
    if pd.Period(args.start,'M').year<1900 or (pd.Period(args.through,'M').year>2010 and not args.allow_new_years):p.error('Historical scope is 1900–2010; later features need explicit --allow-new-years')
    inputs={str(path):digest(path) for path in [args.claims,args.rollcalls]}
    labels=read_labels(args.claims,args.through,args.allow_new_years)
    votes=pd.read_csv(args.rollcalls,usecols=['congress','chamber','rollnumber','date','political_gap'])
    features=build(labels,votes,args.start,args.through)
    out=new_output(args.out);features.to_csv(out/'features.csv',index=False)
    for path,sha in inputs.items():
        if digest(path)!=sha:raise ValueError('Input changed')
    metadata=dict(inputs_sha256=inputs,code_sha256=digest(__file__),
                  measurement_code_sha256={name:digest(name) for name in ['src/proquest_panel.py','src/proquest_polarization.py']},
                  output_sha256=digest(out/'features.csv'),months=len(features),outcomes_read=False,source_coverage='Must be established from input provenance; not inferred from row presence',
                  start=args.start,through=args.through)
    (out/'manifest.json').write_text(json.dumps(metadata,indent=2)+'\n');print(out)


if __name__=='__main__':main()
