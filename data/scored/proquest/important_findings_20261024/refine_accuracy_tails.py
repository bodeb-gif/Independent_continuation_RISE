"""Numerical precision audit of every fixed accuracy interval; no specification selection."""
from pathlib import Path
import sys,json
import numpy as np,pandas as pd
ROOT=Path(__file__).resolve().parents[4]; OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'src'))
from proquest_target_robustness import load_scored,weighted
(OUT/'tail_refinement_spec.json').write_text(json.dumps({'reason':'Market five-year simultaneous upper limit lies close to zero; refine every one of the same 15 intervals, retaining original results.','draws':1000000,'seed':20261025,'alpha_each':.05/15,'new_tests':0},indent=2)+'\n')
f=load_scored(ROOT/'data/scored/proquest/robustness/scored_claims.csv.gz');f=f[f.source_set.eq('verified')]; out=[]
for topic in ['general_business','markets','prices','employment','all_topics']:
 sub=f if topic=='all_topics' else f[f.topic.eq(topic)];w=weighted(sub,'article')
 for length in [2,5,10]:
  u=w.groupby((w.year-1900)//length)[['mass','hit_sum','baseline_sum']].sum().to_numpy(); rng=np.random.default_rng(20261025+length); values=[]
  for _ in range(1000):
   b=u[rng.integers(len(u),size=(1000,len(u)))].sum(1);values.append((b[:,1]-b[:,2])/b[:,0])
  q=np.quantile(np.concatenate(values),[.05/30,1-.05/30]);out.append(dict(topic=topic,block_years=length,low=q[0],high=q[1]))
t=pd.DataFrame(out);t.to_csv(OUT/'accuracy_tail_refinement.csv',index=False);print(t.to_string(index=False))
