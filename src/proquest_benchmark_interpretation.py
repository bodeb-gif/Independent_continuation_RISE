"""Bounded, exploratory outcome-band and comparator sensitivity; no refitting.

Run from the repository root. Original targets/models remain frozen. Changing
outcome labels is a measurement experiment, not a prediction improvement.
"""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from proquest_descriptive import BANDS, load_reference, realized_outcome
from proquest_direction_diagnostics import BASELINE, OPPOSITE, evaluate
from proquest_target_robustness import SOURCE, TOPICS, cohort, digest, load_scored

REGIMES = ('original', 'duration_scaled', 'sign_only')
SPEC = {
    'date': '2026-10-19',
    'status': 'Exploratory; motivated by previously inspected flat-label and employment results',
    'scope': 'Annual ProQuest 1900–2010, verified primary and raw sensitivity; saved scorable non-NBER rows only',
    'primary_cohort': 'machine_stated_non_NBER; machine timing is not source validated',
    'secondary_cohort': 'non_NBER, including assumed horizons',
    'regimes': {'original': 'Original endpoint bands independent of horizon',
                'duration_scaled': 'Original bands times horizon_months/12; linear scenario, not a validated semantic correction',
                'sign_only': 'Zero band, retaining original numerical boundary tolerance; even tiny nonzero changes count'},
    'bands_at_12_months': BANDS,
    'units': 'Employment: unemployment-rate percentage points; other topics: percentage change in level',
    'comparators': ['original_fixed', 'always_flat', 'always_opposite'],
    'weights': 'Equal article within each source/cohort/topic/horizon subset; identical rows and weights across regimes and comparators',
    'horizons': ['all', '1-6', '7-12', '13-24'],
    'uncertainty': 'Paired occupied calendar-block bootstrap, 5000 draws. Five years primary, 2/10 sensitivity for all horizons; horizon bins use five years. Marginal intervals conditional on scoring, not selection or interpretation uncertainty.',
    'decision': 'Retain every scenario; no winning threshold/baseline selected. No p-values, training, feature changes, primary target replacement or source review. RNN correctness probabilities cannot be compared with constant economic-direction forecasts as if the tasks were identical.',
}


def bands_for(regime, horizon):
    if regime not in REGIMES or not 1 <= horizon <= 24 or int(horizon) != horizon:
        raise ValueError('Unsupported regime or horizon')
    multiplier = {'original': 1., 'duration_scaled': horizon/12., 'sign_only': 0.}[regime]
    return {topic: value*multiplier for topic, value in BANDS.items()}


def relabel(frame, series):
    """One outcome per topic/month/horizon, retaining every source-local row."""
    if frame.basis.eq('NBER proxy').any():
        raise ValueError('NBER proxy has no endpoint band interpretation')
    keys = ['topic', 'month', 'horizon_used']
    outcomes = frame[keys].drop_duplicates().copy()
    for regime in REGIMES:
        labels = []
        for topic, month, horizon in outcomes[keys].itertuples(index=False, name=None):
            label, _, error = realized_outcome(series, topic, month, int(horizon), bands_for(regime, horizon))
            if error or label is None:
                raise ValueError(f'Previously eligible endpoint unavailable: {topic}/{month}/{horizon}')
            labels.append(label)
        outcomes[regime] = labels
    result = frame.merge(outcomes, on=keys, validate='many_to_one', sort=False)
    if len(result) != len(frame) or result.duplicated(['source_set', 'record_id']).any():
        raise ValueError('Changed matched population')
    if not result.original.eq(result.realized).all():
        raise ValueError('Original deterministic outcomes did not reproduce')
    if not result.predicted_norm.eq(result.original).astype(int).eq(result.hit).all():
        raise ValueError('Original correctness did not reproduce')
    at12 = result.horizon_used.eq(12)
    if not result.loc[at12, 'original'].eq(result.loc[at12, 'duration_scaled']).all():
        raise ValueError('Twelve-month anchor changed')
    return result


def analyze(frame):
    comparisons, transitions, movement = [], [], []
    for source in ['verified', 'raw']:
        for cname in ['machine_stated_non_NBER', 'non_NBER']:
            pop = cohort(frame[frame.source_set.eq(source)], cname)
            for topic in TOPICS:
                topic_rows = pop[pop.topic.eq(topic)]
                for hname, low, high in [('all', 1, 24), ('1-6', 1, 6), ('7-12', 7, 12), ('13-24', 13, 24)]:
                    # Assumed-horizon bins would conflate timing imputation and horizon effects.
                    if cname == 'non_NBER' and hname != 'all':
                        continue
                    sub = topic_rows[topic_rows.horizon_used.between(low, high)].copy()
                    if sub.empty:
                        continue
                    w = 1/sub.groupby('page_id').page_id.transform('size').to_numpy()
                    avg = lambda x: float(np.average(x, weights=w))
                    for regime in REGIMES:
                        key = dict(source_set=source, cohort=cname, topic=topic, horizon_months=hname, regime=regime)
                        changed = sub.copy()
                        changed['realized'] = changed[regime]
                        changed['hit'] = changed.predicted_norm.eq(changed.realized).astype(int)
                        comparisons += evaluate(changed, key, (2, 5, 10) if hname == 'all' else (5,))
                        delta_hit = changed.hit.to_numpy()-sub.hit.to_numpy()
                        old_base = sub.original.eq(BASELINE[topic]).astype(int).to_numpy()
                        new_base = sub[regime].eq(BASELINE[topic]).astype(int).to_numpy()
                        movement.append(dict(**key, n_claims=len(sub), n_articles=sub.page_id.nunique(),
                                             outcome_relabel_share=avg(sub.original.ne(sub[regime])),
                                             forecast_flat_share=avg(sub.predicted_norm.eq('flat')),
                                             outcome_flat_share=avg(sub[regime].eq('flat')),
                                             accuracy_change=avg(delta_hit), original_fixed_accuracy_change=avg(new_base-old_base),
                                             gap_vs_original_fixed_change=avg(delta_hit-(new_base-old_base))))
                        for old in [BASELINE[topic], 'flat', OPPOSITE[topic]]:
                            for new in [BASELINE[topic], 'flat', OPPOSITE[topic]]:
                                mask = sub.original.eq(old) & sub[regime].eq(new)
                                transitions.append(dict(**key, original_label=old, scenario_label=new,
                                                        n_claims=int(mask.sum()), article_weighted_share=avg(mask)))
    return {name: pd.DataFrame(rows) for name, rows in
            [('comparisons', comparisons), ('label_transitions', transitions), ('measurement_changes', movement)]}


def report(out, tables):
    table = tables['comparisons']
    primary = table.query("source_set=='verified' and cohort=='machine_stated_non_NBER' and horizon_months=='all' and block_years==5")
    primary.to_csv(out/'primary_comparisons.csv', index=False)
    fig, axes = plt.subplots(2, 2, figsize=(12, 8), layout='constrained')
    titles = ['Business / production', 'Markets / stock price', 'Prices / CPI level', 'Employment / unemployment rate']
    for ax, topic, title in zip(axes.flat, TOPICS, titles):
        sub = primary[primary.topic.eq(topic)]
        for j, rule in enumerate(['original_fixed', 'always_flat', 'always_opposite']):
            t = sub[sub.rule.eq(rule)].set_index('regime').loc[list(REGIMES)]
            y = np.arange(3)+(j-1)*.18
            color = ['#176b87', '#b27639', '#8058a5'][j]
            ax.hlines(y, t.low*100, t.high*100, color=color)
            ax.scatter(t.gap_vs_fixed*100, y, color=color, label=rule.replace('_', ' '), s=20)
        ax.axvline(0, color='#777', linewidth=1)
        ax.set_yticks(range(3), ['Original bands', 'Duration-scaled', 'Sign only'])
        ax.set_title(title)
        ax.set_xlabel('Forecast accuracy minus comparator (pp)')
    axes[0, 0].legend(fontsize=8)
    fig.suptitle('Exploratory measurement sensitivity: same claims, three outcome definitions\nVerified machine-stated horizons; paired five-year-block 95% intervals', fontsize=12)
    fig.savefig(out/'benchmark_interpretation.png', dpi=160)
    plt.close(fig)
    page = '''<!doctype html><html lang="en"><meta charset="utf-8"><title>Benchmark interpretation sensitivity</title>
<style>body{font:16px/1.5 system-ui;max-width:1300px;margin:35px auto;padding:20px}td,th{padding:6px;border-bottom:1px solid #ddd}.table{overflow:auto}img{max-width:100%}</style>
<h1>Benchmark choice and outcome interpretation</h1><p>Exploratory measurement experiment. All three outcome definitions and all three fixed-direction comparators are retained. No benchmark is selected by observed accuracy. Original labels, model predictions and p-values remain unchanged.</p>
<p>Primary population: verified annual 1900–2010 claims with machine-stated horizons and endpoint outcomes; NBER proxy rows excluded. Each article has equal total weight within each topic/horizon subset. Original endpoint bands are 2% production, 5% stock price, 1.5% CPI and 0.5 unemployment-rate percentage points. Duration scaling multiplies these by months/12; sign only counts any change outside numerical tolerance. Neither alternative is source-validated. All regimes use identical claims.</p>
<img src="benchmark_interpretation.png" alt="Accuracy gaps under all three measurement scenarios and fixed comparators">'''
    for title, t in [('All-horizon comparisons', primary), ('Measurement changes', tables['measurement_changes'].query("source_set=='verified' and cohort=='machine_stated_non_NBER'")), ('Horizon comparisons', table.query("source_set=='verified' and cohort=='machine_stated_non_NBER' and horizon_months!='all' and block_years==5"))]:
        page += f'<h2>{title}</h2><div class="table">'+t.to_html(index=False, float_format=lambda x: f'{x:.5f}')+'</div>'
    page += '<p>Intervals are marginal and conditional on scored labels; they omit retrieval, extraction, interpretation and selection uncertainty. Overlapping horizons and nonstationarity limit inference. Raw sensitivity and 2/10-year intervals are in the CSVs. Horizon groups have different composition. Employment versus unemployment, prices versus inflation, and exact market/production targets require source review. Better measured accuracy under another definition is not better prediction. RNNs predict correctness probabilities, a different task from the fixed economic-direction rules used here.</p></html>'
    (out/'report.html').write_text(page)
    print(primary[['topic', 'regime', 'rule', 'hit_rate', 'fixed_baseline', 'gap_vs_fixed', 'low', 'high']].to_string(index=False))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=Path('data/scored/proquest/benchmark_interpretation_v1'))
    args = parser.parse_args()
    if args.out.exists():
        raise ValueError('Preserve existing results; choose a new output directory')
    args.out.mkdir(parents=True)
    # Save the complete bounded specification before computing new results.
    (args.out/'specification.json').write_text(json.dumps(SPEC, indent=2)+'\n')
    prior = Path('data/scored/proquest/target_robustness_v1/summary.json')
    inputs = json.loads(prior.read_text())['inputs_sha256']
    inputs[str(prior)] = digest(prior)
    freeze = Path('data/scored/proquest/modern_readiness/model_freeze.json')
    inputs[str(freeze)] = digest(freeze)
    inputs.update(json.loads(freeze.read_text())['files_sha256'])
    for path, sha in inputs.items():
        if digest(path) != sha:
            raise ValueError(f'Input/frozen model changed: {path}')
    frame = cohort(load_scored(SOURCE), 'non_NBER')
    labels = pd.read_csv(SOURCE, usecols=['source_set', 'record_id', 'realized', 'predicted_norm'], dtype={'record_id': str})
    frame = frame.merge(labels, on=['source_set', 'record_id'], validate='one_to_one')
    series, references = load_reference()
    frame = relabel(frame, series)
    frame[['source_set', 'record_id', 'topic', 'month', 'horizon_used', 'predicted_norm', *REGIMES]].to_csv(args.out/'matched_labels.csv.gz', index=False)
    tables = analyze(frame)
    for name, table in tables.items():
        table.to_csv(args.out/f'{name}.csv', index=False)
    report(args.out, tables)
    for path, sha in inputs.items():
        if digest(path) != sha:
            raise ValueError(f'Input/frozen model changed: {path}')
    summary = dict(status='complete', original_labels_exactly_reproduced=True, twelve_month_anchor_verified=True,
                   n_matched_claims=frame.groupby('source_set').size().to_dict(), model_fits=0, new_p_values=False,
                   inputs_sha256=inputs, references=references, code_sha256=digest(__file__),
                   imported_code_sha256={p: digest(p) for p in ['src/proquest_target_robustness.py', 'src/proquest_direction_diagnostics.py', 'src/proquest_descriptive.py']},
                   versions={'numpy': np.__version__, 'pandas': pd.__version__, 'matplotlib': matplotlib.__version__},
                   outputs_sha256={str(p): digest(p) for p in args.out.iterdir() if p.is_file()})
    (args.out/'summary.json').write_text(json.dumps(summary, indent=2)+'\n')


if __name__ == '__main__':
    main()
