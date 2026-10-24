"""Bounded post-hoc evidence checks; preserves source exports and saved results."""
from pathlib import Path
import json, hashlib, sys
import numpy as np
import pandas as pd
from scipy.stats import fisher_exact, binomtest
ROOT=Path(__file__).resolve().parents[4]
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'src'))
from proquest_target_robustness import load_scored, weighted
SEED=20261024

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def holm(ps):
 p=np.asarray(ps); order=np.argsort(p); result=np.empty(len(p)); result[order]=np.minimum(1,np.maximum.accumulate(p[order]*(len(p)-np.arange(len(p)))))
 return result

def boot_units(units,reps,seed,strata=None):
 rng=np.random.default_rng(seed); ans=[]
 groups=[units] if strata is None else [units[strata==s] for s in np.unique(strata)]
 for start in range(0,reps,1000):
  n=min(1000,reps-start); totals=np.zeros((n,units.shape[1]))
  for g in groups: totals+=g[rng.integers(len(g),size=(n,len(g)))].sum(1)
  ans.append(totals)
 return np.concatenate(ans)

inputs=[ROOT/'data/scored/proquest/reverify300_20261022/paired_comparison.json',ROOT/'data/scored/proquest/robustness/scored_claims.csv.gz',OUT/'specification.json']
before={str(p.relative_to(ROOT)):sha(p) for p in inputs}
rows=json.loads(inputs[0].read_text()); rows=[r for r in rows if r['sampling_frame']=='historical_1900_2010']
assert len(rows)==250 and len({r['audit_id'] for r in rows})==250
assert all(1900<=int(r['publication_date'][:4])<=2010 for r in rows)
assert sum(r['new_keep'] is not False for r in rows)==214
assert sum(r['new_status']=='unresolved' for r in rows)==1
rframe=pd.DataFrame({'article':[r['source_metadata']['page_id'] for r in rows], 'batch':[r['batch'] for r in rows], 'year':[int(r['publication_date'][:4]) for r in rows], 'keep':[int(r['new_keep'] is not False) for r in rows]})
assert rframe.article.nunique()==249
records=[]; sensitivities=[]; tests=[]
for i,(reviewer,unclear) in enumerate([('reviewer1',False),('reviewer1',True),('reviewer2',False)]):
 name=reviewer+('_unclear_'+str(unclear).lower() if reviewer=='reviewer1' else '')
 f=rframe.copy(); f['valid']=[int(r[reviewer+'_decision']=='include' or (unclear and r[reviewer+'_decision']=='unclear')) for r in rows]
 f['valid_kept']=f.valid*f.keep;f['mass']=1
 units=f.groupby('article',sort=True)[['mass','valid','keep','valid_kept']].sum()
 strata=f.groupby('article',sort=True).batch.first().to_numpy()
 def stats(t):
  return np.column_stack((t[:,3]/t[:,2]-t[:,1]/t[:,0],t[:,3]/t[:,1],t[:,1]/t[:,0],t[:,3]/t[:,2]))
 total=units.sum().to_numpy(); n,v,k,vk=map(int,total)
 sample=stats(boot_units(units.to_numpy(),50000,SEED+i,strata))
 lo,hi=np.quantile(sample,[.025,.975],axis=0)
 invalid_dropped=n-v-k+vk;valid_dropped=v-vk
 table=[[vk,k-vk],[v-vk,n-v-k+vk]]
 fp=float(fisher_exact(table,alternative='two-sided').pvalue)
 mp=float(binomtest(min(invalid_dropped,valid_dropped),invalid_dropped+valid_dropped,.5,alternative='two-sided').pvalue)
 rec=dict(scenario=name,n=n,articles=len(units),kept=k,valid_before=v,valid_after=vk,invalid_removed=invalid_dropped,valid_lost=valid_dropped,precision_before=v/n,precision_after=vk/k,precision_gain=vk/k-v/n,precision_gain_low=lo[0],precision_gain_high=hi[0],valid_retention=vk/v,retention_low=lo[1],retention_high=hi[1],before_low=lo[2],before_high=hi[2],after_low=lo[3],after_high=hi[3],fisher_p=fp,mcnemar_p=mp,table=table)
 records.append(rec)
 tests.extend([dict(scenario=name,test='precision_enrichment_fisher',p_value=fp),dict(scenario=name,test='net_classification_error_mcnemar',p_value=mp)])
 for length in [2,5,10]:
  u=f.groupby((f.year-1900)//length)[['mass','valid','keep','valid_kept']].sum()
  b=stats(boot_units(u.to_numpy(),20000,SEED+i+length)); a,z=np.quantile(b[:,0],[.025,.975])
  sensitivities.append(dict(scenario=name,kind='calendar_block',block_years=length,n_blocks=len(u),low=a,high=z))
 dup=f[f.article.duplicated(False)].index
 for j in dup:
  sub=f.drop(j);v=int(sub.valid.sum());k=int(sub.keep.sum());vk=int(sub.valid_kept.sum());n=len(sub)
  p=float(fisher_exact([[vk,k-vk],[v-vk,n-v-k+vk]]).pvalue)
  sensitivities.append(dict(scenario=name,kind='omit_one_shared_article_claim',omitted_id=rows[j]['audit_id'],fisher_p=p))
for r,p in zip(tests,holm([t['p_value'] for t in tests])): r['holm_6']=p;r['bonferroni_420_stress']=min(1,420*r['p_value'])
(OUT/'verification_results.json').write_text(json.dumps(dict(results=records,tests=tests,sensitivities=sensitivities),indent=2)+'\n')
pd.DataFrame(records).to_csv(OUT/'verification_effects.csv',index=False)
pd.DataFrame(tests).to_csv(OUT/'verification_tests.csv',index=False)
pd.DataFrame(sensitivities).to_csv(OUT/'verification_sensitivities.csv',index=False)
frame=load_scored(inputs[1]); frame=frame[frame.source_set.eq('verified')]
assert len(frame)==175855
accuracy=[]
for topic in ['general_business','markets','prices','employment','all_topics']:
 sub=frame if topic=='all_topics' else frame[frame.topic.eq(topic)]
 f=weighted(sub,'article')
 for length in [2,5,10]:
  u=f.groupby((f.year-1900)//length)[['mass','hit_sum','baseline_sum']].sum().to_numpy()
  b=boot_units(u,100000,SEED+length)
  dif=(b[:,1]-b[:,2])/b[:,0]
  q=np.quantile(dif,[.025,.975,.05/30,1-.05/30]); n,h,base=u.sum(0)
  accuracy.append(dict(topic=topic,block_years=length,n_blocks=len(u),n_claims=len(sub),n_articles=sub.page_id.nunique(),hit_rate=h/n,baseline_rate=base/n,gap=(h-base)/n,low95=q[0],high95=q[1],simultaneous15_low=q[2],simultaneous15_high=q[3]))
table=pd.DataFrame(accuracy)
old=pd.read_csv(ROOT/'data/scored/proquest/target_robustness_v1/primary_verified_topics.csv').set_index('topic')
for r in table.query('block_years==5 and topic!="all_topics"').itertuples(): assert abs(r.gap-old.loc[r.topic,'gap_vs_fixed'])<1e-12
assert all(sha(ROOT/p)==d for p,d in before.items())
table.to_csv(OUT/'accuracy_simultaneous.csv',index=False)
(OUT/'analysis_manifest.json').write_text(json.dumps(dict(inputs_sha256=before,code_sha256=sha(Path(__file__)),versions=dict(python=sys.version,numpy=np.__version__,pandas=pd.__version__),checks=dict(historical_n=250,unique_articles=249,verified_scores=175855,source_inputs_unchanged=True,old_point_estimates_reproduced=True)),indent=2)+'\n')
print(pd.DataFrame(records)[['scenario','precision_gain','precision_gain_low','precision_gain_high','valid_retention','fisher_p','mcnemar_p']].to_string(index=False))
print(pd.DataFrame(tests).to_string(index=False))
print(table[['topic','block_years','gap','simultaneous15_low','simultaneous15_high']].to_string(index=False))
