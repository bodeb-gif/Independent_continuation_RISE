import argparse,csv,gzip,hashlib,json,random
from pathlib import Path
root=Path(__file__).resolve().parents[4]
parser=argparse.ArgumentParser(description='Reproduce the frozen selection into a new directory.')
parser.add_argument('--output',type=Path,default=Path(__file__).resolve().parent)
out=parser.parse_args().output
if (out/'pack.json').exists() or (out/'manifest.json').exists():
 parser.error('Refusing to overwrite a frozen selection; pass --output with a new directory.')
out.mkdir(parents=True,exist_ok=True)
sha=lambda b:hashlib.sha256(b).hexdigest()
old=set()
for name in ('source_review_150_v1','source_review_pilot_v1'):
 old.update(r['audit_id'] for r in json.loads((root/'data/scored/proquest'/name/'pack.json').read_text())['records'])
with gzip.open(root/'data/scored/proquest/descriptive/scored_claims.csv.gz','rt') as f:
 frame=sorted((r['record_id'] for r in csv.DictReader(f) if r['scorable']=='True' and 'verified:'+r['record_id'] not in old))
rng=random.Random(2026102002); selected=rng.sample(frame,100)
chosen={}
for rid in selected:
 y,line=map(int,rid.split(':'));chosen.setdefault(y,[]).append(line)
records=[];strata={'historical':{'frame_n':len(frame),'sample_n':100}}; hashes={}
for y in range(1900,2027):
 p=root/(f'data/proquest/verified/pred_proquest_economy_{y}.export.jsonl' if y<=2010 else f'data/proquest/modern/20261020/verified/pred_proquest_economy_{y}.export.jsonl')
 b=p.read_bytes();lines=b.splitlines();rows=[json.loads(l) for l in lines]; h=sha(b)
 hashes[str(p.relative_to(root))]=h
 if y>2010:
  eligible=[i for i,r in enumerate(rows,1) if not r.get('no_predictions') and r.get('source')=='proquest']
  n=4 if y in (2011,2026) else 3
  chosen[y]=rng.sample(eligible,n);strata[str(y)]={'frame_n':len(eligible),'sample_n':n}
 for i in sorted(chosen.get(y,[])):
  r=rows[i-1];s='historical' if y<=2010 else str(y)
  records.append(dict(audit_id=f'verified:{y}:{i}',year=y,source_line=i,source_path=str(p.relative_to(root)),source_sha256=h,source_records=len(rows),page_id=str(r['page_id']),date=r['date'],publisher=r.get('publisher') or r.get('newspaper_title'),stratum=s,inclusion_probability=strata[s]['sample_n']/strata[s]['frame_n']))
for n,r in enumerate(records,1):r['n']=n
assert len(records)==150 and not old.intersection(r['audit_id'] for r in records)
pack={'schema':'proquest-additional150-v1','records':records}
(out/'pack.json').write_text(json.dumps(pack,indent=2)+'\n')
manifest=dict(seed=2026102002,n=150,prior_ids_excluded=sorted(old),strata=strata,source_hashes=hashes,pack_sha256=sha((out/'pack.json').read_bytes()),review_status='sample_frozen_source_review_pending',reviewer='Codex',comparison='Existing GPT-4o mini extraction labels; reveal after first-pass freeze',design='100 SRS historical scored verified candidates excluding prior 162 addresses; 50 modern retained verified candidates stratified by year (4 each 2011 and 2026, 3 each other year). Report strata separately; pooled unweighted estimates describe only sample.',current_state='Claim wording only; do not infer from surrounding article.',source_prose='Retained inside TDM',historical_frame_addresses_sha256=sha(('\n'.join(frame)+'\n').encode()))
(out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print({k:manifest[k] for k in ('n','seed','strata','historical_frame_addresses_sha256')})
