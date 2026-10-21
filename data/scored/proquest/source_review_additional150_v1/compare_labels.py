"""Reproduce the source-free categorical comparison; no source interpretation."""
import csv
import hashlib
import html
import json
from collections import Counter
from pathlib import Path

B = Path(__file__).resolve().parent
ROOT = B.parents[3]
FIELDS = ['topic','direction','price_direction','unemployment_direction','horizon_months','confidence','voice','speaker_name','scope','is_quoted_forecaster','current_state']
MAPS = [dict(g='general_business',p='prices',e='employment',m='markets',o='other'),{'+':'improve','-':'worsen','=':'no_change','?':'unclear'},dict(u='up',d='down',s='stable',n='na'),dict(u='up',d='down',s='stable',n='na'),{'6':6,'12':12,'v':'vague'},dict(a='assertive',h='hedged'),dict(j='journalist',e='expert',o='official',l='layperson',u='unclear'),None,dict(n='national',r='regional',f='foreign',i='industry'),{'1':True,'0':False},dict(g='good',b='bad',m='mixed',n='na')]
def sha(b): return hashlib.sha256(b).hexdigest()
def canonical(obj): return json.dumps(obj,sort_keys=True,separators=(',',':')).encode()
def dump(name,obj): (B/name).write_text(json.dumps(obj,indent=2)+'\n')

def run():
    manifest=json.loads((B/'manifest.json').read_text())
    assert sha((B/'pack.json').read_bytes())==manifest['pack_sha256']
    pack=json.loads((B/'pack.json').read_text())['records']
    raw=(B/'categorical_labels.txt').read_text().splitlines()
    assert len(pack)==len(raw)==150
    assert len({r['audit_id'] for r in pack})==150
    assert not set(manifest['prior_ids_excluded']).intersection(r['audit_id'] for r in pack)
    originals={}; input_hashes={}
    for r in pack:
        path=r['source_path']
        if path in originals: continue
        b=(ROOT/path).read_bytes()
        assert sha(b)==r['source_sha256']==manifest['source_hashes'][path],path
        originals[path]=[json.loads(line) for line in b.splitlines()]
        input_hashes[path]=sha(b)
    reviewed=[]; pairs=[]
    for r,line in zip(pack,raw):
        x=line.split('|');assert int(x[0])==r['n']
        decision={'I':'include','E':'exclude','U':'unclear'}[x[1]]
        labels=dict.fromkeys(FIELDS)
        if decision=='include':
            assert len(x)==13
            labels={f:(m[v] if m else v) for f,m,v in zip(FIELDS,MAPS,x[2:])}
        else: assert len(x)==2
        row={k:r[k] for k in ['n','audit_id','date','page_id','source_sha256']}
        row.update(decision=decision,labels=labels)
        reviewed.append(row)
        original=originals[r['source_path']][r['source_line']-1]
        assert str(original['page_id'])==r['page_id'] and original['date']==r['date']
        machine={f:original.get(f) for f in FIELDS}
        agreement={f:(labels[f]==machine[f] if decision=='include' else None) for f in FIELDS}
        pairs.append(dict(**row,original_labels=machine,agreement=agreement,stratum=r['stratum'],inclusion_probability=r['inclusion_probability']))
    assert set(r['date'][:4] for r in reviewed if int(r['date'][:4])>2010)==set(map(str,range(2011,2027)))
    def stats(rows):
        inc=[r for r in rows if r['decision']=='include']
        return dict(n=len(rows),distinct_articles=len({r['page_id'] for r in rows}),decisions=dict(Counter(r['decision'] for r in rows)),inclusion_fraction=len(inc)/len(rows),field_agreement={f:dict(matches=sum(r['agreement'][f] for r in inc),denominator=len(inc),fraction=sum(r['agreement'][f] for r in inc)/len(inc)) for f in FIELDS},all_fields_match=sum(all(r['agreement'].values()) for r in inc))
    summary={'total':stats(pairs),'historical':stats(pairs[:100]),'modern':stats(pairs[100:]),'years':dict(sorted(Counter(r['date'][:4] for r in pairs).items())),'categorical_projection_sha256':sha(canonical(reviewed)),'original_labels_projection_sha256':sha(canonical([{'audit_id':r['audit_id'],'labels':r['original_labels']} for r in pairs])),'comparison':'Existing saved GPT-4o mini labels; no new model run','measurement':'Extraction inclusion and literal field agreement, not economic forecast accuracy or recall','source_context_reviewed_n':150,'source_recovered_n':150,'verbatim_quote_matches':87,'unresolved_n':0,'reviewer':'Codex','input_hashes':input_hashes,'categorical_input_sha256':sha((B/'categorical_labels.txt').read_bytes())}
    modern=pairs[100:]
    weights=[1/r['inclusion_probability'] for r in modern]
    included=[r for r in modern if r['decision']=='include']
    denom=sum(1/r['inclusion_probability'] for r in included)
    summary['modern_design_weighted']={'frame_n':sum(s['frame_n'] for k,s in manifest['strata'].items() if k!='historical'),'inclusion_fraction':sum(w for w,r in zip(weights,modern) if r['decision']=='include')/sum(weights),'field_agreement':{f:sum(r['agreement'][f]/r['inclusion_probability'] for r in included)/denom for f in FIELDS},'interpretation':'Inverse inclusion-probability ratio estimates for the retained modern candidate frame; point estimates only.'}
    summary['applicable_field_agreement']={f:{'matches':sum(r['agreement'][f] for r in pairs if r['decision']=='include' and r['labels'][f]!='na'),'denominator':sum(r['decision']=='include' and r['labels'][f]!='na' for r in pairs)} for f in ['price_direction','unemployment_direction']}
    dump('reviewed_labels_categorical.json',dict(schema='proquest-additional150-categorical-v1',reviewer='Codex',records=reviewed,canonical_sha256=summary['categorical_projection_sha256']))
    dump('comparison.json',dict(schema='proquest-additional150-comparison-v1',records=pairs))
    dump('summary.json',summary)
    with (B/'comparison.csv').open('w',newline='') as f:
        keys=['n','audit_id','date','page_id','stratum','decision','inclusion_probability']+[prefix+k for k in FIELDS for prefix in ['review_','original_','match_']]
        writer=csv.DictWriter(f,fieldnames=keys);writer.writeheader()
        for r in pairs:
            flat={k:r[k] for k in keys[:7]}
            for field in FIELDS:
                flat.update({prefix+field:r[group][field] for prefix,group in [('review_','labels'),('original_','original_labels'),('match_','agreement')]})
            writer.writerow(flat)
    lines=['# Additional 150-claim labeling comparison','',
        'Completed source-context labeling of 150 new ProQuest candidates: 100 historical and 50 modern, with every year from 2011 through 2026 represented. Compared against the original saved GPT-4o mini labels after freezing the new labels. No new GPT-4o mini run or economic-outcome scoring was performed.','',
        '| Sample | Reviewed | Include | Exclude | Unclear | Inclusion |','|---|---:|---:|---:|---:|---:|']
    for key in ['historical','modern','total']:
        s=summary[key];d=s['decisions'];lines.append(f"| {key.title()} | {s['n']} | {d.get('include',0)} | {d.get('exclude',0)} | {d.get('unclear',0)} | {100*s['inclusion_fraction']:.1f}% |")
    lines+=['','Exact agreement among included claims only:','','| Field | Historical | Modern | Combined sample |','|---|---:|---:|---:|']
    for field in FIELDS:
        values=[]
        for key in ['historical','modern','total']:
            s=summary[key]['field_agreement'][field];values.append(f"{s['matches']}/{s['denominator']} ({100*s['fraction']:.1f}%)")
        lines.append('| '+field+' | '+' | '.join(values)+' |')
    lines+=['',f"All eleven fields match on {summary['total']['all_fields_match']}/107 included claims. This is exact annotation agreement under the stated review conventions, not overall model accuracy.",'',
        '## Files and source evidence','',
        '- `comparison.csv` and `comparison.json`: all 150 decisions with original and review fields; excluded fields are null.',
        '- `reviewed_labels_categorical.json`: source-free categorical labels, keyed to the frozen export addresses.',
        '- `pack.json` and `manifest.json`: selection, inclusion probabilities, prior exclusions and source hashes.',
        '- `summary.json`: counts, field denominators, applicable-only price/unemployment comparisons, and modern design-weighted estimates.',
        '- In TDM: `election_arm/source_review_additional150_v1/` contains frozen labels, full reasoning, source passages and the readable comparison. Source prose and free-text notes remain there.','',
        '## Interpretation','',
        'The historical sample is SRS100 from 175,693 scored verified records after excluding the previous 150 and twelve pilot addresses. The modern sample draws four records each from 2011 and 2026 and three from every other modern year, from all retained verified candidates. Those frames differ: modern candidates need not have scorable outcomes. The unweighted combined figure describes these 150 sampled candidates only. No claim labels were deduplicated and no unavailable case was substituted.',
        f"The modern inverse-probability-weighted inclusion estimate is {100*summary['modern_design_weighted']['inclusion_fraction']:.1f}% across {summary['modern_design_weighted']['frame_n']:,} retained candidates. This is a point estimate; no uncertainty interval is asserted. The modern frame includes retained verification exceptions rather than silently dropping them.",'',
        'Every source record was recovered by ordered export reconstruction and source-article ID/date checks. Eighty-seven quotes occurred exactly once verbatim; the remaining passages were inspected in article context for OCR/quotation differences. Full-prefix hashing permits only unchanged frozen prefixes when a live VM shard has appended rows. The VM receipt records any such lineage exceptions.',
        'Labels follow the original extraction schema. Current-state labels use the sampled claim itself, not surrounding article conditions. Short, long, event-relative or unsupported horizons remain vague; approximately 4–8 months maps to six and 9–15 to twelve, with annual next-year outlooks coded twelve. Compound forecasts receive a documented primary interpretation, with secondary components retained in VM notes.',
        'Price direction concerns price levels, and employment growth does not automatically imply falling unemployment. Overall price/unemployment agreement includes many `na` matches; applicable-only denominators are provided separately. Speaker-name comparison is literal, so surnames, full names and group attributions can differ without implying different people. Source-grounded judgments can be debatable; paired records and VM notes support adjudication.',
        'These results measure inclusion and annotation agreement among extracted positive candidates. They do not establish recall, independent human agreement, or whether forecasts came true. Earlier reviews and source exports are unchanged.','']
    (B/'README.md').write_text('\n'.join(lines))
    table=''.join('<tr><th>'+html.escape(field)+'</th>'+''.join('<td>'+f"{summary[k]['field_agreement'][field]['matches']}/{summary[k]['field_agreement'][field]['denominator']} ({100*summary[k]['field_agreement'][field]['fraction']:.1f}%)"+'</td>' for k in ['historical','modern','total'])+'</tr>' for field in FIELDS)
    cards=[]
    for r in pairs:
        rows=''.join('<tr><td>'+f+'</td><td>'+html.escape(str(r['labels'][f]))+'</td><td>'+html.escape(str(r['original_labels'][f]))+'</td><td>'+('—' if r['agreement'][f] is None else '✓' if r['agreement'][f] else 'Different')+'</td></tr>' for f in FIELDS)
        cards.append(f"<details><summary>{r['n']}. {html.escape(r['audit_id'])} · {r['date']} · {r['decision']}</summary><table><tr><th>Field</th><th>Review</th><th>GPT-4o mini</th><th>Match</th></tr>{rows}</table></details>")
    page='<!doctype html><meta charset="utf-8"><title>150 additional ProQuest labels</title><style>body{font:16px/1.5 system-ui;max-width:1100px;margin:40px auto;padding:0 24px;color:#172b35}table{border-collapse:collapse;width:100%;margin:20px 0}th,td{padding:8px;text-align:left;border-bottom:1px solid #dce4e6}th{background:#eef4f5}details{padding:12px;border-bottom:1px solid #dce4e6}summary{cursor:pointer}a{color:#13677c}</style><h1>150 additional ProQuest labels</h1><p>100 historical · 50 modern · every year 2011–2026 represented</p><p><strong>107 included · 43 excluded · 0 unresolved</strong></p><p>Source-context labels frozen before comparison with existing GPT-4o mini labels. This measures extraction and annotation agreement, not economic forecast accuracy.</p><table><tr><th>Field</th><th>Historical</th><th>Modern</th><th>Combined sample</th></tr>'+table+'</table><p>Agreement uses included claims only. Combined percentages describe this sample; the historical and modern sampling frames differ. Literal speaker-name differences and NA matches require care. See <a href="README.md">methods</a> and <a href="comparison.csv">all paired labels (CSV)</a>.</p><h2>All 150 paired decisions</h2>'+''.join(cards)
    (B/'report.html').write_text(page)
    print(json.dumps({k:summary[k] for k in ['total','historical','modern','categorical_projection_sha256','original_labels_projection_sha256','applicable_field_agreement','modern_design_weighted']},indent=2))
if __name__=='__main__': run()
