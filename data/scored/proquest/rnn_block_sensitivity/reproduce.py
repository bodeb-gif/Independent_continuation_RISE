from pathlib import Path
import hashlib,itertools,json
import numpy as np
import pandas as pd

out=Path('data/scored/proquest/rnn_block_sensitivity'); out.mkdir(exist_ok=True)
paths=[Path('data/scored/proquest/polarization/claims/test_predictions.csv.gz'),Path('data/scored/proquest/rnn_permutation/paired_tests.csv')]
hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
spec={'date':'2026-10-19','status':'Post-hoc sensitivity prompted by concern about p=0.250; no primary-test replacement or significance-based selection','block_years':[1,2,3,4,5,8],'anchor_year':1995,'metric':'equal-article binary Brier','comparisons':['metadata logistic','metadata-history logistic'],'test':'Exhaustive blockwise sign swaps of weighted paired loss contributions, one-sided, ties included; same model-swap statistic as existing five-year test','limitations':'Smaller blocks can split overlapping forecast outcomes and shared economic regimes. These nominal conditional p-values do not establish independence or valid type-I error for any particular block length. No claim-level permutations. No fitting. Report every result; preserve existing five-year comparison.'}
(out/'specification.json').write_text(json.dumps(spec,indent=2)+'\n')
f=pd.read_csv(paths[0]); y=f.hit.to_numpy(); w=1/f.groupby('page_id').page_id.transform('size').to_numpy(); a=f.gru_ensemble__baseline.to_numpy()
assert f.year.between(1995,2010).all() and not f.record_id.duplicated().any()
rows=[]; contributions=[]; nulls=[]
for years in spec['block_years']:
 blocks=(f.year.to_numpy()-1995)//years
 unique=np.unique(blocks); k=len(unique)
 signs=2*((np.arange(2**k,dtype=np.uint32)[:,None]>>np.arange(k,dtype=np.uint32))&1).astype(float)-1
 for comparator,label in [('logistic_metadata__baseline','metadata logistic'),('logistic_metadata_history__baseline','metadata-history logistic')]:
  difference=(f[comparator].to_numpy()-y)**2-(a-y)**2
  mass=np.array([w[blocks==b].sum() for b in unique])
  weighted=np.array([(w[blocks==b]*difference[blocks==b]).sum() for b in unique])
  distribution=(signs@weighted)/w.sum(); observed=float(np.sum(weighted)/w.sum())
  assert np.isclose(observed,np.average(difference,weights=w))
  p=float(np.mean(distribution>=observed-1e-12))
  rows.append({'block_years':years,'blocks':k,'permutations':len(distribution),'comparison':label,'brier_improvement':observed,'nominal_one_sided_p':p,'minimum_possible_p':1/len(distribution),'positive_blocks':int((weighted>0).sum())})
  for block,total,weight in zip(unique,weighted,mass):
   mask=blocks==block
   contributions.append({'block_years':years,'comparison':label,'first_year':int(f.loc[mask,'year'].min()),'last_year':int(f.loc[mask,'year'].max()),'article_mass':weight,'brier_improvement':total/weight,'contribution_to_total_improvement':total/w.sum()})
  nulls.extend({'block_years':years,'comparison':label,'assignment':i,'brier_improvement':v} for i,v in enumerate(distribution))
result=pd.DataFrame(rows)
old=pd.read_csv(paths[1]).query("metric == 'brier'")
for label,comparison in [('metadata logistic','gru_vs_metadata'),('metadata-history logistic','gru_vs_history_logistic')]:
 assert result.query('block_years == 5 and comparison == @label').nominal_one_sided_p.iloc[0]==old.query('comparison == @comparison').p_one_sided.iloc[0]
result.to_csv(out/'scores.csv',index=False)
pd.DataFrame(contributions).to_csv(out/'block_contributions.csv',index=False)
pd.DataFrame(nulls).to_csv(out/'null_scores.csv.gz',index=False,compression={'method':'gzip','mtime':0})
view=result.pivot(index='block_years',columns='comparison',values='nominal_one_sided_p')
html='<!doctype html><html lang="en"><meta charset="utf-8"><title>RNN block length sensitivity</title><style>body{font:16px/1.6 system-ui;max-width:1000px;margin:40px auto;padding:20px}td,th{padding:10px;border-bottom:1px solid #ddd}table{border-collapse:collapse}</style><h1>RNN block length sensitivity</h1><p>Post-hoc checks of saved 1995–2010 predictions. All tested block lengths are reported. The original five-year comparison remains primary. Positive loss improvements favor the RNN; changing the block length does not change its fitted predictions or observed effect size.</p>'
html+=view.to_html(float_format=lambda v:f'{v:.5f}')
html+='<p>Values are nominal one-sided block-swap p-values, conditional on exchangeability assumptions. Blocks begin in 1995; the final block can be shorter. One-year blocks can split the 24-month outcome windows. Shorter blocks can increase apparent precision without supplying independent evidence. None is chosen on the basis of crossing 0.05. No source validation or modern evaluation was performed.</p><p>The full counts and contributions are in scores.csv and block_contributions.csv; exhaustive null statistics are in null_scores.csv.gz.</p></html>'
(out/'report.html').write_text(html)
for path,sha in hashes.items(): assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==sha
(out/'summary.json').write_text(json.dumps({'inputs_sha256':hashes,'code_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'five_year_reproduction':True,'model_fits':0,'outputs_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.is_file() and p.name!='summary.json'}},indent=2)+'\n')
print(result.to_string(index=False))
