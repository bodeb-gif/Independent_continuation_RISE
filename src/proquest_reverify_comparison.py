"""Compare a single additional 300-claim verifier pass with both human reviews.

No API calls, source prose, outcome scoring, or relabeling. Reports finite-sample
precision changes, accepted-claim retention, and filtering losses separately by
reviewer and period. Unresolved model calls are retained conservatively.
"""
import argparse
from collections import Counter
import hashlib
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT/'data/scored/proquest'
FIELDS = ['topic', 'direction', 'price_direction', 'unemployment_direction',
          'horizon_months', 'confidence', 'voice', 'speaker_name', 'scope',
          'is_quoted_forecaster', 'current_state']


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def metrics(rows, reviewer):
    def count(subset):
        return dict(Counter(r[reviewer+'_decision'] for r in subset))
    kept = [r for r in rows if r['new_keep'] is not False]
    dropped = [r for r in rows if r['new_keep'] is False]
    before, after, removed = count(rows), count(kept), count(dropped)
    n, k = len(rows), len(kept)
    def precision(c, denom, uncertain):
        return (c.get('include',0)+uncertain*c.get('unclear',0))/denom if denom else None
    before_bounds = [precision(before,n,u) for u in [0,1]]
    after_bounds = [precision(after,k,u) for u in [0,1]]
    changes = [100*(a-b) for a,b in zip(after_bounds,before_bounds)] if k and n else []
    valid = before.get('include',0)
    fp = before.get('exclude',0)
    resolved_kept = after.get('include',0)+after.get('exclude',0)
    return {'n':n,'kept_n':k,'dropped_n':len(dropped), 'before':before,'after':after,
            'dropped':removed,'before_precision_bounds':before_bounds,
            'after_precision_bounds':after_bounds,
            'precision_change_pp_bounds':[min(changes),max(changes)] if changes else [None,None],
            'resolved_before_precision':valid/(valid+fp) if valid+fp else None,
            'resolved_after_precision':after.get('include',0)/resolved_kept if resolved_kept else None,
            'human_valid_retained_n':after.get('include',0),
            'human_valid_lost_n':removed.get('include',0),
            'human_valid_retention':after.get('include',0)/valid if valid else None,
            'human_invalid_removed_n':removed.get('exclude',0),
            'human_invalid_removal_fraction':removed.get('exclude',0)/fp if fp else None,
            'unresolved_human_retained_n':after.get('unclear',0)}


def field_metrics(rows, reviewer, field):
    """Literal agreement on human-included claims; resolved-only class metrics."""
    included = [r for r in rows if r[reviewer+'_decision']=='include']
    comparable = [r for r in included if not (field=='current_state' and
                  reviewer=='reviewer1' and r['reviewer1_current_state_incompatible'])]
    def unresolved(r):
        return (r['machine'].get(field) is None or r[reviewer].get(field) is None or
                (reviewer=='reviewer2' and field in r['reviewer2_field_status']))
    resolved = [r for r in comparable if not unresolved(r)]
    # JSON encoding preserves categorical types (e.g. boolean versus string).
    pairs = [(json.dumps(r['machine'][field]), json.dumps(r[reviewer][field])) for r in resolved]
    matches = sum(a==b for a,b in pairs)
    classes = []
    for label in sorted({v for pair in pairs for v in pair}):
        tp = sum(a==label and b==label for a,b in pairs)
        fp = sum(a==label and b!=label for a,b in pairs)
        fn = sum(a!=label and b==label for a,b in pairs)
        classes.append({'label':json.loads(label), 'tp':tp, 'fp':fp, 'fn':fn,
                        'human_support':tp+fn, 'predicted_n':tp+fp,
                        'precision':tp/(tp+fp) if tp+fp else None,
                        'recall':tp/(tp+fn) if tp+fn else None})
    return {'eligible_included_n':len(included), 'denominator':len(comparable),
            'matches':matches, 'fraction':matches/len(comparable) if comparable else None,
            'missing_or_uncertain_n':len(comparable)-len(resolved),
            'incompatible_convention_excluded_n':len(included)-len(comparable),
            'per_label_resolved_n':len(resolved), 'per_label':classes,
            'confusion_resolved':[{'machine':json.loads(a),'human':json.loads(b),'n':n}
                                  for (a,b),n in sorted(Counter(pairs).items())]}


def field_comparison(rows, reviewer):
    kept = [r for r in rows if r['new_keep'] is not False]
    result = {}
    for field in FIELDS:
        before, after = field_metrics(rows,reviewer,field), field_metrics(kept,reviewer,field)
        delta = (100*(after['fraction']-before['fraction'])
                 if before['fraction'] is not None and after['fraction'] is not None else None)
        result[field] = {'before':before,'after':after,'agreement_change_pp':delta,
                         'correct_labels_removed_n':before['matches']-after['matches'],
                         'nonmatching_or_uncertain_removed_n':
                             before['denominator']-after['denominator']-before['matches']+after['matches']}
    return result


def compare(export_path, out):
    export_path, out = Path(export_path), Path(out)
    export = json.loads(export_path.read_text())
    assert export['schema']=='proquest-reverify300-export-v1'
    assert export['source_text_exported'] is False and export['reason_prose_exported'] is False
    spec = export['specification']
    assert spec['model_requested']=='gpt-4o-mini' and spec['max_retries']==0
    assert spec['temperature']==0 and spec['max_tokens']==256
    assert spec['script_sha256']==digest(ROOT/'src/proquest_reverify300.py')
    assert spec['calls_per_claim_max']==1 and spec['human_labels_in_prompt'] is False
    observation_path=out/'vm_observation.json'
    if observation_path.exists():
        observation=json.loads(observation_path.read_text())
        assert digest(export_path)==observation['vm_export_sha256'], 'VM export checksum mismatch'
    metadata_path=BASE/'reviewer2_300_v1/sample_metadata.json'
    assert spec['metadata_sha256']==digest(metadata_path)
    metadata=json.loads(metadata_path.read_text())
    inputs=export['records']
    assert len(inputs)==300 and [r['n'] for r in inputs]==list(range(1,301))
    assert [r['audit_id'] for r in inputs]==[r['audit_id'] for r in metadata]
    assert export['attempted_n']==300 and all(r['status']!='not_attempted' for r in inputs), 'Pass is not complete'
    for r in inputs:
        assert r['status'] in ['judged','unresolved','attempted_unresolved']
        if r['status']=='judged':
            assert type(r['keep']) is bool and r['finish_reason']=='stop'
            assert r['response_model'].startswith('gpt-4o-mini'), 'Unexpected returned model'
        else:
            assert r['keep'] is None
    assert dict(Counter(r['status'] for r in inputs))==export['counts']
    assert sum(r['keep'] is True for r in inputs)==export['keep_n']
    assert sum(r['keep'] is False for r in inputs)==export['drop_n']
    if all(r.get('prompt_sha256') for r in inputs):
        h=hashlib.sha256(json.dumps([r['prompt_sha256'] for r in inputs]).encode()).hexdigest()
        assert h==spec['ordered_prompt_sha256'], 'Prompt order or content changed'
    prior=BASE/'verification_pass_audit_20261022'
    audit=json.loads((prior/'summary.json').read_text())
    for path, expected in audit['input_sha256'].items():
        assert digest(ROOT/path)==expected, 'Changed comparison input: '+path
    paired=json.loads((prior/'paired_labels.json').read_text())
    assert [r['audit_id'] for r in paired]==[r['audit_id'] for r in inputs]
    rows=[dict(old,new_keep=new['keep'],new_status=new['status'],source_metadata=meta)
          for old,new,meta in zip(paired,inputs,metadata)]
    groups, fields_by_group = {}, {}
    for frame in ['historical_1900_2010','modern_2011_2026','combined_descriptive_only']:
        subset=[r for r in rows if frame=='combined_descriptive_only' or r['sampling_frame']==frame]
        groups[frame]={who:metrics(subset,who) for who in ['reviewer1','reviewer2']}
        fields_by_group[frame]={who:field_comparison(subset,who) for who in ['reviewer1','reviewer2']}
        for who in ['reviewer1','reviewer2']:
            for field in FIELDS:
                baseline=audit['groups'][frame]['field_agreement']['machine_vs_'+who][field]
                calculated=fields_by_group[frame][who][field]['before']
                for key in ['matches','denominator','missing_or_uncertain_n','incompatible_convention_excluded_n']:
                    assert calculated[key]==baseline[key], 'Baseline label metric changed'
    agreed=[r for r in rows if r['reviewer1_decision']==r['reviewer2_decision'] and r['reviewer1_decision']!='unclear']
    usage=Counter()
    for r in inputs:
        for k,v in (r.get('usage') or {}).items():
            if type(v) is int:usage[k]+=v
    result={'schema':'proquest-reverify300-comparison-v1','groups':groups,
            'field_comparison':fields_by_group,
            'agreement_restricted_sensitivity':metrics(agreed,'reviewer1'),
            'judgment_counts':export['counts'],'api_attempts':export['attempted_n'],
            'returned_models':dict(Counter(r.get('response_model','unavailable') for r in inputs)),
            'token_usage':dict(usage), 'export_sha256':digest(export_path),
            'comparison_source_sha256':digest(__file__),
            'paired_baseline_sha256':digest(prior/'paired_labels.json'),
            'interpretation':[
                'One additional verification pass on the exact existing 300 accepted candidates. This estimates the additional filter\'s change on this sample.',
                'This is not the original production verifier\'s before/after effect, nor recall over all newspaper forecasts.',
                'Each human reviewer is a separate reference. Their disagreements are preserved; no consensus gold standard is invented.',
                'Historical and modern frames remain separate; combined results are descriptive counts for these 300, not population-weighted estimates.',
                'Bounds reflect the one unresolved human decision. Delta bounds use the same interpretation before and after, not independent endpoint subtraction.',
                'Any failed model attempts are retained in the conservative filter; successful-only results must not silently discard failures.',
                'The pass only filters candidates. Original extraction attributes are unchanged.',
                'Field agreement is conditional on each reviewer accepting the claim. Before and after supports differ; changes reflect selection, not corrected labels. On the same retained claims, labels and agreement are unchanged.',
                'Literal field agreement includes NA matches and gives missing/uncertain fields no match credit. Per-label precision/recall and confusion counts use only resolved comparable fields; these describe label assignment, not forecast truth or corpus recall.',
                'Reviewer 1 current-state comparisons exclude the original batch because its coding convention differs. Denominators and exclusions are reported for every field.',
                'Agreement-restricted sensitivity uses only claims on which both humans independently gave the same resolved inclusion decision; it is a selected subset, not adjudication.',
                'No confidence interval or statistical significance is inferred from the observed sample change.']}
    out.mkdir(parents=True,exist_ok=True)
    (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
    (out/'paired_comparison.json').write_text(json.dumps(rows,indent=2)+'\n')
    (out/'paired_comparison.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
    def bounds(v, percent=True):
        if v[0] is None:return 'undefined'
        fmt=lambda x:f'{100*x:.1f}%' if percent else f'{x:+.1f}'
        return fmt(v[0]) if abs(v[0]-v[1])<1e-10 else fmt(v[0])+' to '+fmt(v[1])
    page=['<!doctype html><meta charset="utf-8"><title>300-claim additional-pass comparison</title>',
          '<style>body{font:16px/1.5 system-ui;max-width:1150px;margin:40px auto;padding:0 22px;color:#203543}table{border-collapse:collapse;width:100%}td,th{padding:9px;border-bottom:1px solid #ccd5dc;text-align:left}h2{margin-top:30px}</style>',
          '<h1>One additional GPT-4o mini pass on the 300 reviewed claims</h1>',
          f'<p>{export["attempted_n"]} API attempts. Judgments: {html.escape(str(export["counts"]))}. Original claims and human decisions preserved.</p>']
    for frame,reviewers in groups.items():
        page.extend([f'<h2>{html.escape(frame)}</h2>',
            '<table><tr><th>Reference</th><th>Before precision</th><th>After precision</th><th>Change (pp)</th><th>Claims kept</th><th>Invalid removed</th><th>Valid lost</th></tr>'])
        for who,m in reviewers.items():
            page.append(f'<tr><td>{who}</td><td>{bounds(m["before_precision_bounds"])}</td><td>{bounds(m["after_precision_bounds"])}</td><td>{bounds(m["precision_change_pp_bounds"],False)}</td><td>{m["kept_n"]}/{m["n"]}</td><td>{m["human_invalid_removed_n"]}</td><td>{m["human_valid_lost_n"]}</td></tr>')
        page.append('</table>')
    page += ['<h2>Specific labels before and after filtering</h2>',
             '<p>Exact agreement with each human reviewer on that reviewer’s included claims. No labels were regenerated or corrected. Changes reflect which claims remain. NA matches are included; unresolved fields receive no match credit. Counts show the changing denominators. Current-state convention exclusions are recorded in the metrics.</p>']
    def rate(s):
        return f'{s["matches"]}/{s["denominator"]} ({s["fraction"]:.1%})' if s['fraction'] is not None else 'undefined'
    def number(v):
        return f'{v:.1%}' if v is not None else 'undefined'
    for frame,reviewers in fields_by_group.items():
        page += [f'<h3>{html.escape(frame)}</h3>', '<table><tr><th>Field</th><th>R1 before → after</th><th>Δ pp</th><th>R2 before → after</th><th>Δ pp</th></tr>']
        for field in FIELDS:
            cells=[]
            for who in ['reviewer1','reviewer2']:
                f=reviewers[who][field]
                delta=f'{f["agreement_change_pp"]:+.2f}' if f['agreement_change_pp'] is not None else 'undefined'
                cells.append(f'<td>{rate(f["before"])} → {rate(f["after"])}</td><td>{delta}</td>')
            page.append(f'<tr><td>{field}</td>'+''.join(cells)+'</tr>')
        page.append('</table>')
        for who in ['reviewer1','reviewer2']:
            page.append(f'<details><summary>Individual category precision and recall: {who}</summary><p>Resolved comparable fields only; conditional on human inclusion. Zero-support metrics are undefined. Speaker names and numeric horizons are exact categories.</p>')
            for field,f in reviewers[who].items():
                page.append(f'<details><summary>{field}</summary><table><tr><th>Stage</th><th>Label</th><th>Human support</th><th>TP / FP / FN</th><th>Precision</th><th>Recall</th></tr>')
                for stage in ['before','after']:
                    for c in f[stage]['per_label']:
                        page.append(f'<tr><td>{stage}</td><td>{html.escape(json.dumps(c["label"]))}</td><td>{c["human_support"]}</td><td>{c["tp"]} / {c["fp"]} / {c["fn"]}</td><td>{number(c["precision"])}</td><td>{number(c["recall"])}</td></tr>')
                page.append('</table></details>')
            page.append('</details>')
    page+=['<h2>Interpretation</h2><ul>']+[f'<li>{html.escape(s)}</li>' for s in result['interpretation']]+['</ul>',
           '<p><a href="summary.json">Exact metrics</a> · <a href="paired_comparison.json">All 300 paired decisions</a> · <a href="categorical_export.json">Original source-free VM export</a></p>']
    (out/'report.html').write_text('\n'.join(page)+'\n')
    print(json.dumps(groups['combined_descriptive_only'],indent=2))
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--export',type=Path,required=True)
    p.add_argument('--out',type=Path,default=BASE/'reverify300_20261022')
    args=p.parse_args()
    compare(args.export,args.out)
