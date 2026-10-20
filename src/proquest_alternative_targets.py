"""Matched payroll and real-GDP outcome sensitivities, not semantic corrections.

Uses archived FRED downloads in a derived folder. No current-vintage value is
a historical predictor. GDP is used only on quarter-end, whole-quarter horizons.
"""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from proquest_descriptive import load_reference, realized_outcome
from proquest_target_robustness import SOURCE, block_summary, cohort, digest, load_scored, weighted

REFERENCE = Path('data/scored/proquest/alternative_target_inputs_v1')
SPEC = {
    'date': '2026-10-19', 'status': 'Exploratory after inspecting historical scoring sensitivity; no benchmark promotion',
    'scope': 'Annual ProQuest 1900–2010, verified primary and raw sensitivity; non-NBER scored business/employment claims only',
    'cohorts': ['machine_stated_non_NBER', 'non_NBER'],
    'employment': 'Compare frozen UNRATE original bands, frozen UNRATE sign, freshly retrieved UNRATE sign, and PAYEMS sign on identical claims with all endpoints. Reverse UNRATE direction so improve means unemployment falls or payroll jobs rise. This assumes broad labor-market interpretation, not source-validated targets.',
    'general_business': 'Restrict publication month to March/June/September/December and horizon to multiples of three months. Compare frozen IP original bands, frozen IP sign, freshly retrieved IP sign, fresh IP quarterly-average sign and real GDP quarterly-level sign. IP quarterly averages require all three months. No interpolated GDP.',
    'unit_caution': 'Quarterly-average levels differ from monthly endpoint levels. Quarter-end publication-month restriction does not mean publication was on the last day. No annualization of GDP level ratios. Sign-only differences outside 1e-10 percentage points count, even economically tiny changes.',
    'references': 'New reference downloads retrieved together on 2026-10-19, frozen bytes and hashes. Keep original snapshots unchanged and report changes between frozen and refreshed original series separately. Assessment outcomes only, never historical inputs.',
    'weighting': 'Equal article within each source/cohort/topic on common support across all variants. Do not compare these rates directly to full-population results.',
    'uncertainty': 'Paired occupied publication-block bootstrap, 5000 draws, five years primary and 2/10 sensitivity; marginal conditional intervals only',
    'comparators': ['always_improve', 'always_flat', 'always_worsen'],
    'decision': 'Retain all outcomes and constant comparators. No automatic claim relabeling, new model fits, p-values or source validation.',
}


def read_reference(path, frequency='M'):
    frame = pd.read_csv(path)
    if frame.shape[1] != 2:
        raise ValueError('Expected date and one reference series')
    dates = pd.to_datetime(frame.iloc[:, 0])
    values = pd.to_numeric(frame.iloc[:, 1], errors='coerce')
    result = pd.Series(values.to_numpy(), index=pd.PeriodIndex(dates, freq=frequency))
    if not result.index.is_unique:
        raise ValueError('Repeated reference period')
    return result


def sign_change(series, start, end, reverse=False):
    first, last = series.get(start, np.nan), series.get(end, np.nan)
    if not np.isfinite(first) or not np.isfinite(last) or first <= 0:
        return None
    change = 100*(last/first-1)
    if reverse:
        change *= -1
    return 'improve' if change > 1e-10 else 'worsen' if change < -1e-10 else 'flat'


def quarter_mean(monthly):
    grouped = monthly.groupby(monthly.index.asfreq('Q'))
    means = grouped.mean()
    return means.where(grouped.count().eq(3))


def business_alignment(month, horizon):
    return month.month in [3, 6, 9, 12] and int(horizon) == horizon and horizon % 3 == 0


def score_alternatives(frame, old, fresh):
    qip = quarter_mean(fresh['INDPRO'])
    records = []
    for topic, month, horizon in frame[['topic', 'month', 'horizon_used']].drop_duplicates().itertuples(index=False, name=None):
        start = pd.Period(month, 'M'); end = start+int(horizon)
        row = dict(topic=topic, month=month, horizon_used=horizon)
        original, _, error = realized_outcome(old, topic, month, int(horizon))
        if error:
            raise ValueError('Original eligible outcome missing')
        row['frozen_original_band'] = original if topic == 'general_business' else {'up': 'worsen', 'down': 'improve', 'flat': 'flat'}[original]
        reverse = topic == 'employment'
        row['frozen_sign'] = sign_change(old[topic], start, end, reverse)
        row['refreshed_sign'] = sign_change(fresh['UNRATE' if reverse else 'INDPRO'], start, end, reverse)
        if reverse:
            row['alternative_sign'] = sign_change(fresh['PAYEMS'], start, end)
            row['aligned'] = True
        else:
            row['aligned'] = business_alignment(start, horizon)
            row['quarterly_ip_sign'] = sign_change(qip, start.asfreq('Q'), end.asfreq('Q')) if row['aligned'] else None
            row['alternative_sign'] = sign_change(fresh['GDPC1'], start.asfreq('Q'), end.asfreq('Q')) if row['aligned'] else None
        names = ['frozen_original_band', 'frozen_sign', 'refreshed_sign', 'alternative_sign']
        if not reverse:
            names += ['quarterly_ip_sign']
        row['eligible'] = row['aligned'] and all(row.get(n) is not None for n in names)
        row['exclusion'] = '' if row['eligible'] else 'not quarter-end whole-quarter horizon' if not row['aligned'] else 'missing paired reference endpoint'
        records.append(row)
    result = frame.merge(pd.DataFrame(records), on=['topic', 'month', 'horizon_used'], validate='many_to_one')
    if not result.frozen_original_band.eq(result.realized).all():
        raise ValueError('Frozen original labels failed to reproduce')
    if len(result) != len(frame):
        raise ValueError('Matched row count changed')
    return result


def analyze(frame):
    comparisons, agreement, support = [], [], []
    for source in ['verified', 'raw']:
        for cname in SPEC['cohorts']:
            pop = cohort(frame[frame.source_set.eq(source)], cname)
            for topic in ['general_business', 'employment']:
                before = pop[pop.topic.eq(topic)]
                sub = before[before.eligible].copy()
                key = dict(source_set=source, cohort=cname, topic=topic)
                support.append(dict(**key, before_claims=len(before), matched_claims=len(sub), matched_articles=sub.page_id.nunique(),
                                    first_year=int(sub.year.min()), last_year=int(sub.year.max()),
                                    alignment_exclusions=int((~before.aligned).sum()), endpoint_exclusions=int((before.aligned & ~before.eligible).sum())))
                variants = ['frozen_original_band', 'frozen_sign', 'refreshed_sign']
                if topic == 'general_business':
                    variants += ['quarterly_ip_sign']
                variants += ['alternative_sign']
                w = 1/sub.groupby('page_id').page_id.transform('size').to_numpy()
                for variant in variants:
                    changed = sub.copy()
                    changed['hit'] = changed.predicted_norm.eq(changed[variant]).astype(int)
                    for label in ['improve', 'flat', 'worsen']:
                        changed['fixed_baseline_hit'] = changed[variant].eq(label).astype(int)
                        for length in [2, 5, 10]:
                            summary, _ = block_summary(weighted(changed, 'article'), length)
                            comparisons.append(dict(**key, variant=variant, comparator='always_'+label, n_claims=len(sub), **summary))
                    for reference in ['frozen_sign', 'refreshed_sign'] + (['quarterly_ip_sign'] if topic == 'general_business' else []):
                        agreement.append(dict(**key, variant=variant, reference=reference,
                                              article_weighted_disagreement=float(np.average(sub[variant].ne(sub[reference]), weights=w))))
    return dict(comparisons=pd.DataFrame(comparisons), label_disagreement=pd.DataFrame(agreement), support=pd.DataFrame(support))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=Path('data/scored/proquest/alternative_targets_v1'))
    args = parser.parse_args(); out = args.out
    out.mkdir(parents=True, exist_ok=False)
    (out/'specification.json').write_text(json.dumps(SPEC, indent=2)+'\n')
    inputs = json.loads(Path('data/scored/proquest/target_robustness_v1/summary.json').read_text())['inputs_sha256']
    for name in ['manifest.json', 'paired_reference_manifest.json']:
        path = REFERENCE/name; inputs[str(path)] = digest(path)
        for source in json.loads(path.read_text())['sources']:
            inputs[source['file']] = source['sha256']
    for path, sha in inputs.items():
        if digest(path) != sha:
            raise ValueError(f'Changed input: {path}')
    frame = cohort(load_scored(SOURCE), 'non_NBER')
    frame = frame[frame.topic.isin(['general_business', 'employment'])]
    labels = pd.read_csv(SOURCE, usecols=['source_set', 'record_id', 'predicted_norm', 'realized'], dtype={'record_id': str})
    frame = frame.merge(labels, on=['source_set', 'record_id'], validate='one_to_one')
    # Shared vocabulary means improve = production/jobs rise or unemployment falls.
    for field in ['predicted_norm', 'realized']:
        mask = frame.topic.eq('employment')
        frame.loc[mask, field] = frame.loc[mask, field].map({'up': 'worsen', 'down': 'improve', 'flat': 'flat'})
    old, _ = load_reference()
    fresh = {sid: read_reference(REFERENCE/f'{sid}.csv', 'Q' if sid == 'GDPC1' else 'M') for sid in ['PAYEMS', 'GDPC1', 'INDPRO', 'UNRATE']}
    frame = score_alternatives(frame, old, fresh)
    frame.to_csv(out/'paired_labels_and_eligibility.csv.gz', index=False)
    tables = analyze(frame)
    for name, table in tables.items():
        table.to_csv(out/f'{name}.csv', index=False)
    primary = tables['comparisons'].query("source_set=='verified' and cohort=='machine_stated_non_NBER' and block_years==5")
    primary.to_csv(out/'primary_comparisons.csv', index=False)
    page = '<!doctype html><html lang="en"><meta charset="utf-8"><title>Alternative outcome benchmarks</title><style>body{font:16px/1.5 system-ui;max-width:1250px;margin:35px auto}td,th{padding:6px;border-bottom:1px solid #ddd}</style><h1>Alternative outcome benchmarks</h1><p>Exploratory common-support comparison, with all variants retained. These are different target definitions, not validated corrections. Source exports and original model targets are unchanged.</p><p>Employment alternative: monthly nonfarm payroll jobs; unemployment direction is reversed to a common improve/worsen vocabulary. General-business alternative: real GDP levels, restricted to quarter-end publication months and whole-quarter horizons. Quarterly IP means separate aggregation from series choice. Sign only counts even tiny changes. Fresh reference series were retrieved together; frozen versus refreshed original signs show snapshot revision sensitivity. No monthly GDP interpolation.</p>'
    for title, table in [('Support', tables['support']), ('Verified stated-horizon comparisons', primary), ('Outcome disagreement', tables['label_disagreement'].query("source_set=='verified' and cohort=='machine_stated_non_NBER'"))]:
        page += f'<h2>{title}</h2>'+table.to_html(index=False, float_format=lambda x: f'{x:.5f}')
    page += '<p>Five-year marginal intervals are conditional on recovered labels and definitions. No multiplicity-adjusted inference, p-values or benchmark selection. Quarterly averages are not monthly endpoints, payroll jobs are not unemployment, and GDP is not necessarily a claim’s intended business target. Different support prevents direct comparison with earlier all-claim headline rates. Raw sensitivity and 2/10-year blocks are retained in CSVs.</p><p>Sources: <a href="https://fred.stlouisfed.org/series/PAYEMS">BLS payroll employment via FRED</a>; <a href="https://fred.stlouisfed.org/series/GDPC1">BEA real GDP via FRED</a>. New references are outcome-only and never historical predictors.</p></html>'
    (out/'report.html').write_text(page)
    for path, sha in inputs.items():
        if digest(path) != sha:
            raise ValueError(f'Input changed: {path}')
    summary = dict(status='complete', original_outcomes_reproduced=True, model_fits=0, new_p_values=False,
                   inputs_sha256=inputs, code_sha256=digest(__file__),
                   imported_code_sha256={p: digest(p) for p in ['src/proquest_descriptive.py', 'src/proquest_target_robustness.py']},
                   outputs_sha256={str(p): digest(p) for p in out.iterdir() if p.is_file()})
    (out/'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    print(primary.query("comparator=='always_improve'")[['topic', 'variant', 'n_claims', 'hit_rate', 'fixed_baseline', 'gap_vs_fixed', 'low', 'high']].to_string(index=False))


if __name__ == '__main__':
    main()
