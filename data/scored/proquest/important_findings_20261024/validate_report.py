"""Independent source joins, exact-tail arithmetic and document-integrity checks."""
from pathlib import Path
import json,hashlib,sys,math,platform,importlib.metadata
import pandas as pd,numpy as np,fitz
from scipy.stats import hypergeom
ROOT=Path(__file__).resolve().parents[4];OUT=Path(__file__).resolve().parent
pair=json.loads((ROOT/'data/scored/proquest/reverify300_20261022/paired_comparison.json').read_text())
base={r['audit_id']:r for r in json.loads((ROOT/'data/scored/proquest/verification_pass_audit_20261022/paired_labels.json').read_text())}
exp={r['audit_id']:r for r in json.loads((ROOT/'data/scored/proquest/reverify300_20261022/categorical_export.json').read_text())['records']}
hist=[r for r in pair if r['sampling_frame']=='historical_1900_2010']
assert len(hist)==250 and len({r['audit_id'] for r in hist})==250
for r in hist:
 for field in ['machine','reviewer1','reviewer2','reviewer1_decision','reviewer2_decision']:assert r[field]==base[r['audit_id']][field]
 assert r['new_keep']==exp[r['audit_id']]['keep']
 assert r['new_status']==exp[r['audit_id']]['status']
res=json.loads((OUT/'verification_results.json').read_text())
for r in res['results']:
 tab=np.array(r['table']); n=int(tab.sum());valid=int(tab[:,0].sum());kept=int(tab[0].sum());observed=int(tab[0,0])
 support=np.arange(max(0,kept-(n-valid)),min(valid,kept)+1)
 probs=hypergeom.pmf(support,n,valid,kept);pobs=hypergeom.pmf(observed,n,valid,kept)
 exact=probs[probs<=pobs*(1+1e-10)].sum();assert abs(exact-r['fisher_p'])<1e-12
 assert r['valid_lost']+r['invalid_removed']==36
 assert abs((r['valid_after']/r['kept']-r['valid_before']/r['n'])-r['precision_gain'])<1e-12
summ=json.loads((ROOT/'data/scored/proquest/reverify300_20261022/summary.json').read_text())['groups']['historical_1900_2010']
for reviewer,r in [('reviewer1',res['results'][0]),('reviewer2',res['results'][2])]:
 s=summ[reviewer];assert r['kept']==s['kept_n'] and r['valid_after']==s['human_valid_retained_n'] and r['valid_lost']==s['human_valid_lost_n']
a=pd.read_csv(OUT/'accuracy_simultaneous.csv');t=pd.read_csv(OUT/'accuracy_tail_refinement.csv');assert len(a)==len(t)==15
z=a.merge(t,on=['topic','block_years']);assert ((z.simultaneous15_high<0)==(z.high<0)).all();assert ((z.simultaneous15_low>0)==(z.low>0)).all()
for topic in ['markets','prices']:assert (t[t.topic.eq(topic)].high<0).all()
sv=json.loads((OUT/'source_verification.json').read_text());assert len(sv['source_hashes'])==222
for p,h in sv['source_hashes'].items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h
pdf=fitz.open(OUT/'important_findings.pdf');assert len(pdf)==8
page_stats=[]
for i,p in enumerate(pdf):
 txt=p.get_text();assert len(txt)>1500 and '\ufffd' not in txt
 blocks=p.get_text('blocks');assert all(b[0]>=40 and b[2]<=573 and b[1]>=20 and b[3]<=780 for b in blocks)
 page_stats.append({'page':i+1,'characters':len(txt),'text_blocks_within_page':True})
expected=[('test_offline.log','ALL 97 CHECKS PASSED'),('test_scoring.log','33 passed, 0 failed'),('test_forecasts.log','33 passed, 0 failed')]
for name,end in expected:assert end in (OUT/name).read_text()
qa={'paired_source_join_n':250,'independent_hypergeometric_tail_checks':3,'saved_counts_reconciled':True,'all_15_refined_interval_classifications_agree':True,'all_222_original_exports_unchanged':True,'required_checks_passed':163,'pdf_pages':page_stats,'rendering':'PyMuPDF, Poppler unavailable; all eight pages visually inspected; final corrected chart checked separately','python':sys.version,'platform':platform.platform(),'versions':{x:importlib.metadata.version(x) for x in ['numpy','scipy','pandas','matplotlib','PyMuPDF']}}
(OUT/'quality_checks.json').write_text(json.dumps(qa,indent=2)+'\n');print(json.dumps({k:v for k,v in qa.items() if k not in ['pdf_pages','python','platform','versions']},indent=2))
