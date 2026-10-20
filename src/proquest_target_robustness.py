"""Paired baseline gaps by legacy target, with bounded time-block sensitivity.

Uses saved annual ProQuest scores. No new scoring, model fits, or source review.
"""
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

SOURCE = Path('data/scored/proquest/robustness/scored_claims.csv.gz')
OUT = Path('data/scored/proquest/target_robustness_v1')
TOPICS = ['general_business', 'markets', 'prices', 'employment']
COHORTS = ['all_legacy', 'non_NBER', 'machine_stated', 'machine_stated_non_NBER']
SPEC = {
    'date': '2026-10-19', 'status': 'Exploratory extension of already inspected descriptive results',
    'scope': 'Annual ProQuest 1900–2010; verified primary, raw sensitivity. No LOC or old crisis-window exports.',
    'estimand': 'Within each source set, cohort and topic, newspaper correctness minus fixed-direction correctness on identical rows and weights. Pooled all-topic summaries are separate estimands.',
    'cohorts': COHORTS,
    'cohort_meaning': 'Machine stated is horizon_basis==stated, not source-validated explicit timing. non_NBER excludes basis==NBER proxy, but does not establish semantic target compatibility or strict eligibility.',
    'weighting': 'Equal article within each source/cohort/topic is primary. Equal observed publication month is sensitivity. Recompute weights for each analysis population; never sum topic article counts into unique articles.',
    'uncertainty': '5000 paired nonoverlapping publication-block bootstrap draws; blocks anchored at 1900, five years primary, two and ten years sensitivity. Resample occupied blocks, summing weighted correct counts and denominator together before computing each ratio. Require at least four occupied blocks. 95% percentile intervals are marginal and conditional on recovered claims and fixed scoring.',
    'stability': 'Leave each occupied five-year publication block out once; report every remaining-sample gap and range. Never select exclusions by results.',
    'limits': 'Not sampling-representative of the press. Intervals omit extraction, interpretation, retrieval and scoring uncertainty; nonstationarity and cross-block overlapping outcomes limit interpretation. No multiplicity-adjusted significance claims, p-value selection or source-validated strict estimates.',
    'seed': 20261019, 'bootstrap_draws': 5000, 'block_lengths': [2, 5, 10],
}


def digest(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_scored(path):
    fields = ['source_set', 'record_id', 'page_id', 'date', 'year', 'topic', 'basis',
              'horizon_basis', 'horizon_used', 'scorable', 'hit', 'fixed_baseline_hit']
    frame = pd.read_csv(path, usecols=fields, dtype={'record_id':str, 'page_id':str})
    if not frame.source_set.isin(['raw','verified']).all() or not frame.year.between(1900,2010).all():
        raise ValueError('Outside annual ProQuest scope')
    if frame[['record_id','page_id','date','year']].isna().any().any() or frame.duplicated(['source_set','record_id']).any():
        raise ValueError('Invalid or repeated source-local addresses')
    dates = pd.to_datetime(frame.date)
    if not dates.dt.year.eq(frame.year).all() or frame.groupby(['source_set','page_id']).date.nunique().gt(1).any():
        raise ValueError('Inconsistent article dates')
    if not frame.scorable.isin([True,False]).all(): raise ValueError('Invalid eligibility flags')
    frame = frame[frame.scorable].copy()
    if not frame[['hit','fixed_baseline_hit']].isin([0,1]).all().all() or frame.basis.isna().any():
        raise ValueError('Invalid paired deterministic outcomes')
    if not frame.topic.isin(TOPICS).all(): raise ValueError('Unsupported scored topic')
    frame['month'] = frame.date.str[:7]
    return frame


def cohort(frame, name):
    mask = np.ones(len(frame), dtype=bool)
    if 'non_NBER' in name: mask &= frame.basis.ne('NBER proxy').to_numpy()
    if 'machine_stated' in name: mask &= frame.horizon_basis.eq('stated').to_numpy()
    if name not in COHORTS: raise ValueError('Unknown cohort')
    return frame.loc[mask]


def weighted(frame, weighting):
    if weighting not in ['article','month']: raise ValueError('Invalid weighting')
    key = 'page_id' if weighting == 'article' else 'month'
    out = frame[['year','hit','fixed_baseline_hit']].copy()
    out['mass'] = 1/frame.groupby(key).hit.transform('size').to_numpy()
    out['hit_sum'] = out.mass*out.hit
    out['baseline_sum'] = out.mass*out.fixed_baseline_hit
    return out


def block_summary(data, length, reps=5000, seed=20261019):
    values = data.groupby((data.year-1900)//length)[['mass','hit_sum','baseline_sum']].sum()
    total = values.sum().to_numpy(); hit, base = total[1:]/total[0]
    result = dict(block_years=length, n_blocks=len(values), hit_rate=hit, fixed_baseline=base,
                  gap_vs_fixed=hit-base, low=np.nan, high=np.nan, valid_draws=0)
    if len(values)>=4:
        draws = np.random.default_rng(seed+length).integers(len(values), size=(reps,len(values)))
        totals = values.to_numpy()[draws].sum(axis=1)
        gaps = (totals[:,1]-totals[:,2])/totals[:,0]
        result.update(low=float(np.quantile(gaps,.025)), high=float(np.quantile(gaps,.975)), valid_draws=reps)
    omissions = []
    if length==5 and len(values)>1:
        for block, row in values.iterrows():
            remaining = total-row.to_numpy()
            omissions.append(dict(omitted_start_year=int(1900+5*block),
                                  omitted_end_year=int(min(2010,1904+5*block)),
                                  gap_vs_fixed=float((remaining[1]-remaining[2])/remaining[0])))
    return result, omissions


def main():
    if OUT.exists(): raise ValueError('Output exists; preserve this version')
    OUT.mkdir(parents=True)
    (OUT/'specification.json').write_text(json.dumps(SPEC,indent=2)+'\n')
    meta_path=Path('data/scored/proquest/robustness/summary.json')
    meta=json.loads(meta_path.read_text())
    inputs={str(SOURCE):digest(SOURCE),str(meta_path):digest(meta_path),
            'data/scored/proquest/publication/legacy_verified_topics.csv':digest('data/scored/proquest/publication/legacy_verified_topics.csv')}
    inputs.update(meta['sources'])
    inputs.update({v['file']:v['sha256'] for v in meta['reference'].values()})
    for path,sha in inputs.items():
        if digest(path)!=sha: raise ValueError(f'Changed source/reference: {path}')
    frame=load_scored(SOURCE)
    for row in meta['corpus']:
        sub=frame[frame.source_set.eq(row['source_set'])]
        if len(sub)!=row['scorable_claims'] or sub.page_id.nunique()!=row['scorable_articles']:
            raise ValueError('Saved corpus counts changed')
    records=[]; omissions=[]; support=[]
    for source in ['verified','raw']:
        for name in COHORTS:
            pop=cohort(frame[frame.source_set.eq(source)],name)
            for topic in TOPICS+['all_topics']:
                sub=pop if topic=='all_topics' else pop[pop.topic.eq(topic)]
                if sub.empty: raise ValueError(f'Empty analysis population: {source}/{name}/{topic}')
                counts=dict(n_claims=len(sub),n_articles=sub.page_id.nunique(),n_months=sub.month.nunique(),
                            first_year=int(sub.year.min()),last_year=int(sub.year.max()))
                for weighting in ['article','month']:
                    key=dict(source_set=source,cohort=name,topic=topic,weighting=weighting)
                    data=weighted(sub,weighting)
                    for length in SPEC['block_lengths']:
                        result, left=block_summary(data,length,SPEC['bootstrap_draws'],SPEC['seed'])
                        records.append(dict(**key,**counts,**result))
                        omissions.extend(dict(**key,**item) for item in left)
                    blocks=data.groupby((data.year-1900)//5).agg(mass=('mass','sum'),n_claims=('mass','size'))
                    support.extend(dict(**key,start_year=int(1900+5*b),mass=float(r.mass),n_claims=int(r.n_claims)) for b,r in blocks.iterrows())
    table=pd.DataFrame(records); left=pd.DataFrame(omissions)
    primary=table.query("source_set=='verified' and cohort=='all_legacy' and weighting=='article' and block_years==5 and topic!='all_topics'")
    old=pd.read_csv('data/scored/proquest/publication/legacy_verified_topics.csv').set_index('topic')
    for row in primary.itertuples():
        for a,b in [('hit_rate','article_hit_rate'),('fixed_baseline','article_fixed_baseline'),('gap_vs_fixed','article_gap_vs_fixed')]:
            if not np.isclose(getattr(row,a),old.loc[row.topic,b],atol=1e-12,rtol=0):raise ValueError('Primary point estimate mismatch')
    table.to_csv(OUT/'comparisons.csv',index=False); left.to_csv(OUT/'leave_one_block_out.csv',index=False)
    pd.DataFrame(support).to_csv(OUT/'block_support.csv',index=False)
    primary.to_csv(OUT/'primary_verified_topics.csv',index=False)
    fig,ax=plt.subplots(figsize=(9,4.8),layout='constrained')
    for i,source in enumerate(['verified','raw']):
        t=table.query("cohort=='all_legacy' and weighting=='article' and block_years==5").query('source_set==@source').set_index('topic').loc[TOPICS]
        y=np.arange(4)+(i-.5)*.16
        ax.hlines(y,t.low*100,t.high*100,color=['#176b87','#b27639'][i],linewidth=2)
        ax.scatter(t.gap_vs_fixed*100,y,label='Verified primary' if i==0 else 'Raw sensitivity',color=['#176b87','#b27639'][i])
    ax.axvline(0,color='#777',linewidth=1)
    ax.set_yticks(np.arange(4),['Business / IP or NBER proxy','Markets / broad stock index','Prices / CPI level','Employment / unemployment rate'])
    ax.set_xlabel('Newspaper accuracy minus matched fixed baseline (percentage points)')
    ax.set_title('Legacy target comparisons: paired five-year-block 95% intervals')
    ax.legend(loc='best');fig.savefig(OUT/'target_gaps.png',dpi=180);plt.close(fig)
    html='<!doctype html><html lang="en"><meta charset="utf-8"><title>ProQuest target robustness</title><style>body{font:16px/1.5 system-ui;max-width:1200px;margin:40px auto;padding:20px}td,th{padding:6px;border-bottom:1px solid #ddd}.table{overflow:auto}img{max-width:100%}</style><h1>ProQuest target robustness</h1>'
    html+='<p>Paired descriptive newspaper-minus-baseline accuracy gaps. Verified annual 1900–2010 exports are primary; raw exports are sensitivity. No model fitting or source validation. Machine topics and horizons do not establish semantic correctness.</p><img src="target_gaps.png" alt="Topic accuracy gaps with paired block intervals">'
    for title,t in [('Verified primary topic comparisons',primary),('Verified cohort and weighting sensitivities',table.query("source_set=='verified' and block_years==5")),('All block lengths and raw sensitivity',table)]:
        html+=f'<h2>{title}</h2><div class="table">'+t.to_html(index=False,float_format=lambda x:f'{x:.5f}')+'</div>'
    html+='<p>Intervals use 5,000 paired block resamples and describe temporal variability conditional on the recovered corpus and fixed scoring. They are marginal, not simultaneous, and omit source interpretation uncertainty. Cross-block overlapping horizons, nonstationarity and selection limit inference. Machine-stated horizons are not human-validated horizons. Removing NBER proxy outcomes does not validate the remaining targets; employment versus unemployment is especially unresolved. Topic article counts overlap. Leave-one-block-out results and block support are saved separately. No p-values or new strict estimates are reported.</p></html>'
    (OUT/'report.html').write_text(html)
    for path,sha in inputs.items():
        if digest(path)!=sha: raise ValueError(f'Input changed: {path}')
    summary=dict(status='complete',primary_point_estimates_reconciled=True,model_fits=0,source_reviews=0,
                 inputs_sha256=inputs,code_sha256=digest(__file__),
                 versions=dict(numpy=np.__version__,pandas=pd.__version__,matplotlib=matplotlib.__version__),
                 outputs_sha256={str(p):digest(p) for p in OUT.iterdir() if p.is_file()})
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(primary[['topic','n_claims','n_articles','gap_vs_fixed','low','high','n_blocks']].to_string(index=False))


if __name__=='__main__':main()
