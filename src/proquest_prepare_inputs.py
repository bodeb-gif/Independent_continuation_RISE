"""Prepare print-time RNN inputs from explicit annual verified exports.

Outcome scoring is opt-in and uses frozen references and maturity checks.
Modern shards require a separately authorized scope flag and reconciled manifest.
"""
import argparse
from functools import lru_cache
import json
from pathlib import Path

import numpy as np
import pandas as pd

from analyze_proquest import ANNUAL
import proquest_descriptive as descriptive
from proquest_modern_intake import validate_manifest
from proquest_rnn_runner import REQUIRED, digest, eligible, new_output


def normalize(exports, first_year, last_year, allow_new_years=False, manifest=None):
    if first_year<1900 or last_year<first_year:raise ValueError('Invalid year range')
    if last_year>2010:
        if not allow_new_years or first_year<2011 or manifest is None:
            raise ValueError('Modern preparation requires separate modern-only exports, scope flag, and manifest')
        if sorted(manifest.get('expected_years',[]))!=list(range(first_year,last_year+1)):
            raise ValueError('Manifest years differ from requested years')
        validate_manifest(manifest,exports)
    paths=sorted(p for p in Path(exports).glob('*.jsonl') if ANNUAL.fullmatch(p.name))
    if {int(ANNUAL.fullmatch(p.name)[1]) for p in paths}!=set(range(first_year,last_year+1)):
        raise ValueError('Missing or unexpected annual shards')
    rows=[];inputs={};empty=0
    for path in paths:
        inputs[str(path)]=digest(path);year=int(ANNUAL.fullmatch(path.name)[1])
        for line_number,line in enumerate(path.read_text().splitlines(),1):
            if not line.strip():continue
            row=json.loads(line)
            if row.get('schema_version')!=2 or not row.get('page_id'):raise ValueError('Invalid export schema/address')
            if row.get('source','proquest')!='proquest':raise ValueError('Wrong corpus')
            if row.get('date') and pd.Timestamp(row['date']).year!=year:raise ValueError('Date outside shard')
            if row.get('no_predictions') is True:empty+=1;continue
            if row.get('source')!='proquest' or 'verify_reason' not in row:raise ValueError('Unverified claim')
            date=pd.Timestamp(row['date'])
            if pd.isna(date) or date.year!=year:raise ValueError('Invalid date')
            horizon,basis,_=descriptive.horizon(row)
            rows.append(dict(record_id=f'{year}:{line_number}',page_id=str(row['page_id']),date=date.date().isoformat(),
                             scope=row.get('scope'),topic=row.get('topic'),paper=descriptive.paper_name(row.get('publisher') or row.get('newspaper_title')),
                             voice=row.get('voice'),confidence=row.get('confidence'),predicted_norm=descriptive.predicted_norm(row),
                             horizon_basis=basis,horizon_used=horizon))
    frame=pd.DataFrame(rows,columns=list(dict.fromkeys(REQUIRED)))
    if frame.empty:raise ValueError('No claims')
    if frame.groupby('page_id').date.nunique().gt(1).any():raise ValueError('Conflicting article dates')
    return frame,dict(inputs_sha256=inputs,empty_records=empty,claim_rows=len(frame),source_validation='not_performed')


def combine_history(history,new):
    fields=list(dict.fromkeys(REQUIRED))
    old=history[fields].copy()
    if old.date.max()>=new.date.min():raise ValueError('History overlaps new publication dates')
    frame=pd.concat([old,new],ignore_index=True)
    if frame.record_id.duplicated().any():raise ValueError('Repeated source addresses; never deduplicate')
    if frame.groupby('page_id').date.nunique().gt(1).any():raise ValueError('Conflicting article dates')
    return frame


def attach_outcomes(frame,series,as_of):
    """Calendar maturity and actual reference coverage; no guessed outcomes."""
    out=frame.copy();supported=eligible(frame)
    as_of_date=pd.Timestamp(as_of);as_of_month=as_of_date.to_period('M').ordinal
    observed={name:set(values.dropna().index.asi8) for name,values in series.items()}
    @lru_cache(maxsize=None)
    def outcome(topic,month,horizon):
        start=pd.Period(month,'M');end=start.ordinal+horizon
        target='recession' if topic=='general_business' and start<series[topic].index.min() else topic
        if end+3>=as_of_month:return None,None,'unmatured'
        if not set(range(start.ordinal,end+1)).issubset(observed[target]):return None,None,'reference_gap'
        return descriptive.realized_outcome(series,topic,month,horizon)
    rows=[]
    for i,row in frame.iterrows():
        hit=np.nan;basis=None;reason='unsupported_scope_topic_direction_or_horizon'
        if supported.loc[i]:
            if pd.Timestamp(row.date)>as_of_date:reason='future_publication'
            else:
                realized,basis,error=outcome(row.topic,row.date[:7],int(row.horizon_used))
                reason=error or '';hit=float(row.predicted_norm==realized) if error is None else np.nan
        rows.append(dict(hit=hit,scorable=bool(pd.notna(hit)),basis=basis,unscorable_reason=reason))
    return pd.concat([out.reset_index(drop=True),pd.DataFrame(rows)],axis=1)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--exports',type=Path,required=True);p.add_argument('--first-year',type=int,required=True);p.add_argument('--last-year',type=int,required=True)
    p.add_argument('--allow-new-years',action='store_true');p.add_argument('--manifest',type=Path);p.add_argument('--history',type=Path)
    p.add_argument('--score',action='store_true');p.add_argument('--as-of');p.add_argument('--reference-dir',type=Path)
    p.add_argument('--out',type=Path,required=True);args=p.parse_args()
    if args.score and (not args.as_of or not args.reference_dir):p.error('--score needs --as-of and --reference-dir')
    if not args.score and (args.as_of or args.reference_dir):p.error('Scoring arguments require --score')
    manifest=json.loads(args.manifest.read_text()) if args.manifest else None
    frame,metadata=normalize(args.exports,args.first_year,args.last_year,args.allow_new_years,manifest)
    if args.manifest:metadata['inputs_sha256'][str(args.manifest)]=digest(args.manifest)
    if args.history:
        history=pd.read_csv(args.history,usecols=list(dict.fromkeys(REQUIRED)),dtype={'record_id':str,'page_id':str})
        frame=combine_history(history,frame);metadata['inputs_sha256'][str(args.history)]=digest(args.history)
    metadata.update(scoring=args.score,as_of=args.as_of,prepared_rows=len(frame))
    if args.score:
        descriptive.REF=args.reference_dir
        series,refs=descriptive.load_reference();frame=attach_outcomes(frame,series,args.as_of)
        metadata['references']=refs;metadata['scorable_rows']=int(frame.scorable.sum())
        metadata['inputs_sha256'].update({r['file']:r['sha256'] for r in refs.values()})
    out=new_output(args.out);frame.to_csv(out/'claims.csv.gz',index=False,compression={'method':'gzip','mtime':0})
    for path,sha in metadata['inputs_sha256'].items():
        if digest(path)!=sha:raise ValueError(f'Input changed: {path}')
    metadata.update(code_sha256=digest(__file__),normalization_code_sha256=digest(Path(descriptive.__file__)),
                    prepared_sha256=digest(out/'claims.csv.gz'),outcome_columns_absent=not args.score)
    (out/'manifest.json').write_text(json.dumps(metadata,indent=2)+'\n');print(out)


if __name__=='__main__':main()
