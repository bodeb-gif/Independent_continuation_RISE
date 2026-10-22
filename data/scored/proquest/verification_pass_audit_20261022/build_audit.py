"""Compare existing source-free labels; no API calls or economic scoring.

Run from any directory with Python 3. VM benchmark observations are manually
transcribed in vm_observation.json; this script reproduces their arithmetic,
not the VM-only span matching. Frozen reviewer and source files are read-only.
"""
from collections import Counter
from pathlib import Path
import hashlib
import html
import json

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[3]
BASE = ROOT / 'data/scored/proquest'
FIELDS = ['topic', 'direction', 'price_direction', 'unemployment_direction',
          'horizon_months', 'confidence', 'voice', 'speaker_name', 'scope',
          'is_quoted_forecaster', 'current_state']
INPUTS = {}


def load(path):
    data = path.read_bytes()
    INPUTS[str(path.relative_to(ROOT))] = hashlib.sha256(data).hexdigest()
    return json.loads(data)


def keyed(rows):
    result = {r['audit_id']: r for r in rows}
    assert len(result) == len(rows), 'Duplicate audit ID'
    return result


def agreement(pairs):
    n = len(pairs)
    if not n:
        return {'n': 0, 'matches': 0, 'fraction': None, 'kappa': None}
    matches = sum(a == b for a, b in pairs)
    a, b = Counter(x for x, _ in pairs), Counter(y for _, y in pairs)
    expected = sum(a[k] * b[k] for k in set(a) | set(b)) / n**2
    return {'n': n, 'matches': matches, 'fraction': matches/n,
            'kappa': (matches/n-expected)/(1-expected) if expected < 1 else None}


def main():
    original = load(BASE/'source_review_150_v1/human_comparison_reconciled.json')['records']
    additional = load(BASE/'source_review_additional150_v1/comparison.json')['records']
    first = keyed(original + additional)
    second = keyed(load(BASE/'reviewer2_300_v1/reviewer2_labels_frozen.json'))
    metadata = load(BASE/'reviewer2_300_v1/sample_metadata.json')
    assert set(first) == set(second) == set(keyed(metadata)) and len(first) == 300
    manifest = load(BASE/'reviewer2_300_v1/manifest.json')
    for name, expected in manifest['sha256'].items():
        assert hashlib.sha256((BASE/'reviewer2_300_v1'/name).read_bytes()).hexdigest() == expected
    rows, cache = [], {}
    for meta in metadata:
        aid = meta['audit_id']
        a, b = first[aid], second[aid]
        old_batch = 'machine' in a
        machine, human = (a['machine'], a['human']) if old_batch else (a['original_labels'], a['labels'])
        source = ROOT/meta['source_path']
        if source not in cache:
            content = source.read_bytes()
            cache[source] = (hashlib.sha256(content).hexdigest(), content.decode().splitlines())
            INPUTS[meta['source_path']] = cache[source][0]
        digest, lines = cache[source]
        assert digest == meta['source_sha256']
        record = json.loads(lines[meta['source_line']-1])
        assert str(record['page_id']) == meta['page_id'] and record['date'] == meta['date']
        assert record.get('verify_reason') and 'kept by default' not in record['verify_reason']
        assert all(machine[f] == record.get(f) for f in FIELDS), aid
        rows.append({'audit_id': aid, 'sampling_frame': b['sampling_frame'],
                     'batch': meta['batch'], 'publication_date': meta['date'],
                     'reviewer1_decision': a['decision'], 'reviewer2_decision': b['decision'],
                     'saved_verifier_decision': 'keep', 'machine': machine,
                     'reviewer1': human, 'reviewer2': {f: b.get(f) for f in FIELDS},
                     'reviewer2_field_status': b.get('field_status', {}),
                     'reviewer1_current_state_incompatible': old_batch})
    groups = {}
    for frame in ['historical_1900_2010', 'modern_2011_2026', 'combined_descriptive_only']:
        subset = [r for r in rows if frame == 'combined_descriptive_only' or r['sampling_frame'] == frame]
        summary = {'n': len(subset), 'verified_keep_n': len(subset)}
        for who in ['reviewer1', 'reviewer2']:
            counts = Counter(r[who+'_decision'] for r in subset)
            n, inc, unknown = len(subset), counts['include'], counts['unclear']
            summary[who] = {'decisions': dict(counts),
                'accepted_candidate_precision_bounds': [inc/n, (inc+unknown)/n],
                'resolved_only_precision': inc/(n-unknown), 'resolved_n': n-unknown}
        pairs = [(r['reviewer1_decision'], r['reviewer2_decision']) for r in subset]
        summary['human_decision_agreement'] = agreement(pairs)
        summary['human_decision_agreement_resolved'] = agreement([(a,b) for a,b in pairs if a != 'unclear' and b != 'unclear'])
        summary['human_decision_confusion'] = [{'reviewer1':a, 'reviewer2':b, 'n':n} for (a,b),n in sorted(Counter(pairs).items())]
        summary['field_agreement'] = {}
        for left, right in [('machine','reviewer1'), ('machine','reviewer2'), ('reviewer1','reviewer2')]:
            humans = [x for x in [left,right] if x != 'machine']
            eligible = [r for r in subset if all(r[h+'_decision'] == 'include' for h in humans)]
            fields = {}
            for f in FIELDS:
                comparable = [r for r in eligible if not (f == 'current_state' and 'reviewer1' in humans and r['reviewer1_current_state_incompatible'])]
                # Missing/explicitly uncertain labels remain in the denominator,
                # but can never receive match credit (even two null values).
                unresolved = lambda r: r[left].get(f) is None or r[right].get(f) is None or ('reviewer2' in humans and f in r['reviewer2_field_status'])
                matches = sum(not unresolved(r) and r[left][f] == r[right][f] for r in comparable)
                fields[f] = {'eligible_included_n': len(eligible), 'denominator': len(comparable),
                             'matches': matches, 'missing_or_uncertain_n': sum(unresolved(r) for r in comparable),
                             'fraction': matches/len(comparable) if comparable else None,
                             'incompatible_convention_excluded_n': len(eligible)-len(comparable)}
            summary['field_agreement'][left+'_vs_'+right] = fields
        groups[frame] = summary
    vm = load(OUT/'vm_observation.json')
    benchmark = vm['development_benchmark']
    assert hashlib.sha256((ROOT/benchmark['local_identical_reference']).read_bytes()).hexdigest() == benchmark['reference_sha256']
    for arm in ['first_pass','second_pass']:
        r = benchmark[arm]
        r.update(precision=r['tp']/(r['tp']+r['fp']), recall=r['tp']/(r['tp']+r['fn']),
                 f1=2*r['tp']/(2*r['tp']+r['fp']+r['fn']))
    benchmark['precision_change_pp'] = 100*(benchmark['second_pass']['precision']-benchmark['first_pass']['precision'])
    benchmark['recall_change_pp'] = 100*(benchmark['second_pass']['recall']-benchmark['first_pass']['recall'])
    result = {'date_local':'2026-10-22', 'new_model_calls':0, 'groups':groups,
              'separate_loc_development_benchmark':benchmark, 'input_sha256':INPUTS,
              'notes':[
                  'All 300 ProQuest sample rows explicitly passed the saved verifier; no default-kept exceptions were found.',
                  'No sampled verifier rejects are available, so original ProQuest before/after precision gain is not identifiable from these 300.',
                  'A new verification call on the 300 survivors would measure an additional filter, not recover the original second-pass effect.',
                  'Human judgments remain separate and unadjudicated. Precision is reported against each reviewer, not against an invented consensus.',
                  'Historical and modern sampling frames differ; combined counts are descriptive only. No population weighting or confidence interval is implied.',
                  'Field agreement is literal; NA matches remain included. Missing or flagged uncertain fields receive no match credit. Original-batch reviewer1 current-state comparisons are excluded for incompatible conventions.',
                  'Field comparisons use each human reviewer\'s included claims; human-human field comparison uses their joint-included subset. These supports differ.',
                  'LOC benchmark evidence is extraction validation only and is never pooled with ProQuest. Exact production model deployments were not newly certified.']}
    (OUT/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
    (OUT/'paired_labels.json').write_text(json.dumps(rows,indent=2)+'\n')
    lines = ['<!doctype html><meta charset="utf-8"><title>ProQuest verification-pass audit</title>',
             '<style>body{font:16px/1.5 system-ui;max-width:1050px;margin:40px auto;padding:0 20px;color:#203543}table{border-collapse:collapse;width:100%}td,th{padding:9px;border-bottom:1px solid #ccd5dc;text-align:left}h2{margin-top:32px}</style>',
             '<h1>Existing-pass audit and reviewer comparison</h1><p>October 22, 2026. No new model calls.</p>',
             '<p>The existing 300 source-linked ProQuest claims all explicitly passed the original verifier. Saved machine labels were joined to both human reviews by audit ID.</p>',
             '<h2>ProQuest accepted-candidate precision</h2><table><tr><th>Sample</th><th>Reviewer 1</th><th>Reviewer 2</th><th>Human decision agreement</th></tr>']
    for frame,s in groups.items():
        a,b=s['reviewer1'],s['reviewer2']; lo,hi=a['accepted_candidate_precision_bounds']
        lines.append(f'<tr><td>{html.escape(frame)} (n={s["n"]})</td><td>{a["decisions"].get("include",0)}/{s["n"]}: {lo:.1%}–{hi:.1%}</td><td>{b["decisions"].get("include",0)}/{s["n"]}: {b["accepted_candidate_precision_bounds"][0]:.1%}</td><td>{s["human_decision_agreement"]["matches"]}/{s["n"]}</td></tr>')
    lines += ['</table><p>Reviewer 1 bounds classify the unresolved case both ways; they are not confidence intervals.</p>',
              '<h2>Separate LOC development benchmark</h2><p>Same 16-page, 52-claim model-adjudicated reference, verified by SHA-256. Existing VM outputs rescored; no new model calls.</p>',
              '<table><tr><th>Pass</th><th>TP / FP / FN</th><th>Precision</th><th>Recall</th><th>F1</th></tr>']
    for arm in ['first_pass','second_pass']:
        s=benchmark[arm]
        lines.append(f'<tr><td>{arm}</td><td>{s["tp"]} / {s["fp"]} / {s["fn"]}</td><td>{s["precision"]:.1%}</td><td>{s["recall"]:.1%}</td><td>{s["f1"]:.3f}</td></tr>')
    lines += ['</table><h2>Field agreement on included candidates</h2><p>Each column uses its own eligible subset. Asterisks identify excluded current-state conventions; uncertain values receive no match credit. NA matches are included.</p>']
    for frame, s in groups.items():
        comparisons = s['field_agreement']
        lines += [f'<h3>{html.escape(frame)}</h3><table><tr><th>Field</th><th>Machine vs reviewer 1</th><th>Machine vs reviewer 2</th><th>Reviewer 1 vs reviewer 2</th></tr>']
        for f in FIELDS:
            cells = []
            for stats in comparisons.values():
                v = stats[f]
                rate = f'{v["fraction"]:.1%}' if v['fraction'] is not None else 'unavailable'
                marker = '*' if v['incompatible_convention_excluded_n'] else ''
                cells.append(f'<td>{v["matches"]}/{v["denominator"]} ({rate}){marker}</td>')
            lines.append(f'<tr><td>{html.escape(f)}</td>'+''.join(cells)+'</tr>')
        lines.append('</table>')
    lines += ['<h2>Interpretation</h2><ul>']+[f'<li>{html.escape(n)}</li>' for n in result['notes']]+['</ul>',
              '<p>To estimate the original ProQuest verification gain, review a probability sample of pre-verification candidates that includes both retained and dropped claims, recover claim-level lineage in TDM, and compare precision before and after on that common sampling frame.</p>',
              '<p><a href="summary.json">Full metrics and field comparisons</a> · <a href="paired_labels.json">All 300 paired labels</a> · <a href="vm_observation.json">VM audit evidence</a></p>']
    (OUT/'report.html').write_text('\n'.join(lines)+'\n')
    print(json.dumps({k:{'n':v['n'],'human_agreement':v['human_decision_agreement']} for k,v in groups.items()},indent=2))


if __name__ == '__main__':
    main()
