"""Count multiple direction labels within article/target/horizon groups.

This is a unit-of-analysis diagnostic, not evidence of duplicate or false claims.
"""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from proquest_target_robustness import digest

SOURCE=Path('data/scored/proquest/descriptive/scored_claims.csv.gz')
OUT=Path('data/scored/proquest/article_direction_audit_v1')
KEYS=['page_id','date','topic','basis','horizon_used']


def summarize(frame):
    if frame.record_id.duplicated().any():raise ValueError('Repeated source addresses')
    if frame.groupby('page_id').date.nunique().gt(1).any():raise ValueError('Article dates conflict')
    groups=frame.groupby(KEYS).agg(n_claims=('record_id','size'),n_directions=('predicted_norm','nunique')).reset_index()
    same_voice=frame.groupby(KEYS+['voice'],dropna=False).predicted_norm.nunique().reset_index(name='directions_within_voice_category')
    same_voice=same_voice.groupby(KEYS).directions_within_voice_category.max().reset_index()
    groups=groups.merge(same_voice,on=KEYS,validate='one_to_one')
    linked=frame.merge(groups[KEYS+['n_directions']],on=KEYS,validate='many_to_one')
    rows=[]
    for topic,sub in linked.groupby('topic'):
        cells=groups[groups.topic.eq(topic)]
        weights=1/sub.groupby('page_id').page_id.transform('size')
        rows.append(dict(topic=topic,n_claims=len(sub),n_articles=sub.page_id.nunique(),n_groups=len(cells),
                         multiple_direction_groups=int(cells.n_directions.gt(1).sum()),
                         same_voice_category_multiple_groups=int(cells.directions_within_voice_category.gt(1).sum()),
                         article_weighted_claim_share_in_multiple_groups=float(np.average(sub.n_directions.gt(1),weights=weights))))
    return groups,pd.DataFrame(rows)


def main():
    if OUT.exists():raise ValueError('Preserve existing version')
    sha=digest(SOURCE)
    fields=['record_id',*KEYS,'predicted_norm','voice','scorable','year']
    f=pd.read_csv(SOURCE,usecols=fields,dtype={'page_id':str,'record_id':str})
    if not f.year.between(1900,2010).all() or not f.scorable.isin([True,False]).all():raise ValueError('Invalid annual scope')
    f=f[f.scorable].copy()
    groups,table=summarize(f);OUT.mkdir(parents=True)
    groups.to_csv(OUT/'article_target_horizon_groups.csv.gz',index=False,compression={'method':'gzip','mtime':0})
    table.to_csv(OUT/'topic_summary.csv',index=False)
    result=dict(status='Exploratory structural diagnostic; no deduplication or source judgments',n_claims=len(f),
                n_groups=len(groups),multiple_direction_groups=int(groups.n_directions.gt(1).sum()),
                group_definition=KEYS,interpretation='Different speakers, conditions, subtargets or extraction errors could explain multiple directions. Voice categories do not identify individual speakers. Source review is required to distinguish explanations.',
                inputs_sha256={str(SOURCE):sha},code_sha256=digest(__file__),
                outputs_sha256={str(p):digest(p) for p in OUT.iterdir() if p.is_file()})
    if digest(SOURCE)!=sha:raise ValueError('Input changed')
    (OUT/'summary.json').write_text(json.dumps(result,indent=2)+'\n');print(table.to_string(index=False))


if __name__=='__main__':main()
