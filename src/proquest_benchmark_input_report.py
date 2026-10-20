"""Verify and summarize the completed benchmark/input experiments offline."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from proquest_target_robustness import digest

MODELS = Path('data/scored/proquest/macro_claim_inputs_v1')
TARGETS = Path('data/scored/proquest/alternative_targets_v1')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=Path('data/scored/proquest/benchmark_input_review_v1'))
    args = parser.parse_args(); out = args.out
    out.mkdir(parents=True, exist_ok=False)
    inputs = {}
    for directory, code in [(MODELS, 'src/proquest_macro_claim_inputs.py'), (TARGETS, 'src/proquest_alternative_targets.py')]:
        path = directory/'summary.json'; manifest = json.loads(path.read_text())
        inputs[str(path)] = digest(path)
        inputs.update(manifest['inputs_sha256']); inputs.update(manifest['outputs_sha256'])
        inputs.update(manifest['imported_code_sha256']); inputs[code] = manifest['code_sha256']
    frozen = json.loads(Path('data/scored/proquest/modern_readiness/model_freeze.json').read_text())['files_sha256']
    inputs.update(frozen)
    for path, sha in inputs.items():
        if digest(path) != sha:
            raise ValueError(f'Changed artifact: {path}')
    metrics = pd.read_csv(MODELS/'fold_metrics.csv')
    revisions = []
    for origin, rows in metrics.groupby('origin'):
        pred = pd.read_csv(MODELS/origin/'predictions.csv.gz')
        if not pd.to_datetime(pred.date).dt.year.between(1975, 1994).all():
            raise ValueError('Unexpected assessment dates')
        for row in rows.itertuples():
            sub = pred if row.topic == 'all' else pred[pred.topic.eq(row.topic)]
            error = (sub[f'{row.model}__{row.arm}']-sub.hit)**2
            # Independent recomputation: mean claim loss per article, then average articles.
            direct = error.groupby(sub.page_id).mean().mean()
            np.testing.assert_allclose(direct, row.brier, rtol=1e-7, atol=1e-9)
        audit = pd.read_csv(MODELS/origin/'training_label_audit.csv.gz')
        for stage, sub in audit[audit.vintage_hit.notna()].groupby('stage'):
            if not (pd.to_datetime(sub.label_available_by) < pd.to_datetime(sub.cutoff)).all():
                raise ValueError('Training/stopping label unavailable at cutoff')
            if not (pd.PeriodIndex(sub.target_end, freq='M')+3 < pd.PeriodIndex(sub.cutoff, freq='M')).all():
                raise ValueError('Unmatured training/stopping label')
            revisions.append(dict(origin=origin, stage=stage, n_claims=len(sub),
                                  claim_weighted_correctness_revision_rate=float(sub.vintage_hit.ne(sub.original_revised_hit).mean())))
    paired = pd.read_csv(TARGETS/'paired_labels_and_eligibility.csv.gz')
    primary = pd.read_csv(TARGETS/'primary_comparisons.csv')
    for row in primary.itertuples():
        sub = paired[paired.source_set.eq('verified') & paired.horizon_basis.eq('stated') & paired.topic.eq(row.topic) & paired.eligible]
        news = sub.predicted_norm.eq(sub[row.variant]).groupby(sub.page_id).mean().mean()
        base = sub[row.variant].eq(row.comparator.removeprefix('always_')).groupby(sub.page_id).mean().mean()
        np.testing.assert_allclose([news, base, news-base], [row.hit_rate, row.fixed_baseline, row.gap_vs_fixed], rtol=0, atol=1e-12)
    revisions = pd.DataFrame(revisions)
    revisions.to_csv(out/'label_revision_audit.csv', index=False)
    fig, axes = plt.subplots(2, 2, figsize=(12, 8), layout='constrained')
    colors = {'none': '#555555', 'production': '#087e8b', 'unemployment': '#bf6930', 'both': '#9162a3'}
    labels = {'none': 'No macro inputs', 'production': 'Production', 'unemployment': 'Unemployment', 'both': 'Both'}
    for ax, topic, title in zip(axes[0], ['general_business', 'employment'], ['Business claims: RNN', 'Employment claims: RNN']):
        sub = metrics[metrics.model.eq('gru') & metrics.topic.eq(topic)]
        for arm in colors:
            t = sub[sub.arm.eq(arm)].sort_values('origin')
            ax.plot(t.origin.str[:4].astype(int), t.brier, marker='o', color=colors[arm], label=labels[arm])
        ax.set_title(title); ax.set_ylabel('Article-weighted Brier error (lower is better)')
        ax.set_xticks([1975, 1980, 1985, 1990]); ax.set_xlabel('Start of five-year assessment block')
    axes[0, 0].legend(fontsize=8)
    for ax, topic, variants, names in [
        (axes[1, 0], 'general_business', ['frozen_original_band', 'refreshed_sign', 'quarterly_ip_sign', 'alternative_sign'], ['Original IP bands', 'Monthly IP sign', 'Quarterly IP sign', 'GDP sign']),
        (axes[1, 1], 'employment', ['frozen_original_band', 'refreshed_sign', 'alternative_sign'], ['Original UNRATE bands', 'UNRATE sign (reversed)', 'Payroll jobs sign'])]:
        sub = primary[primary.topic.eq(topic) & primary.comparator.eq('always_improve')].set_index('variant').loc[variants]
        y = np.arange(len(sub))
        ax.hlines(y, sub.low*100, sub.high*100, color='#087e8b')
        ax.scatter(sub.gap_vs_fixed*100, y, color='#087e8b')
        ax.axvline(0, color='#777', linewidth=1)
        ax.set_yticks(y, names); ax.set_xlabel('Accuracy minus always-improve comparator (pp)')
        ax.set_title('Matched outcome definitions: '+('business' if topic == 'general_business' else 'employment'))
    fig.suptitle('Exploratory benchmark and input tests\nModel panels: 1975–1994; outcome panels: matched historical claims, five-year-block 95% intervals', fontsize=12)
    fig.savefig(out/'benchmark_inputs.png', dpi=170); plt.close(fig)
    aggregate = pd.read_csv(MODELS/'summary_metrics.csv')
    page = '''<!doctype html><html lang="en"><meta charset="utf-8"><title>Benchmark and input review</title>
<style>body{font:16px/1.5 system-ui;max-width:1200px;margin:35px auto;padding:20px}td,th{padding:6px;border-bottom:1px solid #ddd}img{max-width:100%}.table{overflow:auto}</style>
<h1>Benchmark and input review</h1>
<p>Both requested tracks are complete. No original scoring definitions, RNN bundles or p-values were replaced. Source validation and modern evaluation remain deferred.</p>
<p><strong>Inputs:</strong> Production features reduce the matched RNN's mean Brier error from 0.1992 to 0.1910, but improve only two of four eras overall. The gain concentrates in business claims: 0.1988 to 0.1876, improving three eras. Employment RNN error increases with production inputs and worsens in all four eras with unemployment inputs. The metadata-only logistic control still has the best mean loss among the tested pooled configurations (0.1743). This is an exploratory input comparison on a different sample and training-label protocol from earlier whole-corpus results, not independent confirmation.</p>
<p><strong>Outcomes:</strong> Payroll and unemployment directions disagree for 21.9% of article-weighted matched employment claims. With sign-only payroll scoring, accuracy is 55.1% versus 63.3% for jobs always rising; the paired gap interval includes zero. Matched business accuracy under GDP direction is 54.9% versus 86.6% for always rising. GDP changes the target and frequency; it does not validate the claims' meaning. Raw-export sensitivities have the same gap signs.</p>
<img src="benchmark_inputs.png" alt="Time-block RNN error by input group and paired accuracy gaps by outcome definition">
<p>All four input groups use identical claims, the same 8-unit GRU and three seeds, and matched logistic models. Training and stopping outcomes come from snapshots available before their cutoffs. Macro trends, observation ages and direction interactions use snapshots strictly before publication-month start. Revised truths are assessment-only. All 16 fold/arm bundles reload and reproduce predictions without outcome columns.</p>
<p>Outcome experiments keep original snapshots, retrieve alternative/reference snapshots together, avoid GDP interpolation and compare identical rows. Business GDP comparisons restrict publication months to quarter ends and horizons to whole quarters; neither condition establishes exact source timing. Five-year intervals are marginal and omit source interpretation and selection uncertainty.</p>'''
    for title, table in [('Equal-era mean model results', aggregate), ('Historical versus revised correctness labels', revisions)]:
        page += f'<h2>{title}</h2><div class="table">'+table.to_html(index=False, float_format=lambda x: f'{x:.6f}')+'</div>'
    page += '<p>The sensible candidate for further validation is production information for business claims. Unemployment features and an omnibus input combination do not warrant promotion here. Historical feature availability sharply limits early training: the first fold has 1,110 eligible claims. A future extension can test monthly unemployment/payroll vintages and topic-specific models, with its own fixed comparison and unexposed evaluation; these results alone do not justify further selection on the same eras.</p><p><a href="../macro_claim_inputs_v1/report.html">Input experiment</a> · <a href="../alternative_targets_v1/report.html">Outcome experiment</a></p></html>'
    (out/'report.html').write_text(page)
    summary = dict(status='complete', independent_model_brier_checks=len(metrics), independent_target_comparison_checks=len(primary),
                   frozen_files_verified=len(frozen), input_hashes_verified=len(inputs), inputs_sha256=inputs,
                   code_sha256=digest(__file__), outputs_sha256={str(p): digest(p) for p in out.iterdir() if p.is_file()})
    (out/'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    print({k: v for k, v in summary.items() if k not in ['inputs_sha256', 'outputs_sha256', 'code_sha256']})


if __name__ == '__main__':
    main()
