"""Matched forward-time production/unemployment inputs for claim models.

Exploratory four-arm ablation on previously explored 1975–1994 publications.
Historical macro vintages supply predictors AND training/stopping outcomes.
Revised outcomes are assessment-only. Original models are never overwritten.
"""
import argparse
import json
from pathlib import Path
import time

import joblib
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
import torch

from proquest_descriptive import BANDS
from proquest_rnn import article_weights, neural_probabilities
from proquest_rnn_development import (SOURCE, development_labels, digest, fit_controls,
                                     fit_seed, prepare_fold, SEEDS)
from proquest_rnn_permutation import scores
from proquest_vintages import CORE_FEATURES, load_archives, macro_features

ORIGINS = ['1975-01', '1980-01', '1985-01', '1990-01']
PRODUCTION = ['ip_growth_3m', 'ip_growth_6m', 'ip_growth_12m', 'ip_age_months', 'production_alignment']
JOBS = ['unemployment_level', 'unemployment_change_3m', 'unemployment_change_12m', 'unemployment_age_months', 'unemployment_alignment']
ARMS = {'none': [], 'production': PRODUCTION, 'unemployment': JOBS, 'both': PRODUCTION+JOBS}
CONFIG = {'id': 'gru8_standard_20', 'hidden': 8, 'dropout': .15, 'weight_decay': .001, 'window_years': 20}
SPEC = {
    'date': '2026-10-19', 'status': 'Exploratory matched input ablation; all four eras have prior exposure',
    'scope': 'Verified annual ProQuest national general-business and employment claims only; all model arrays exclude 1995 onward. Prior monthly press context may contain other supported topics, using print-time labels only.',
    'origins': ORIGINS, 'arms': ARMS, 'configuration': CONFIG, 'seeds': SEEDS,
    'support': 'Every arm/model uses identical eligible claim rows. Require all eight core macro fields and endpoint outcomes; no backfill or imputation. Earlier rows remain only in print-time context.',
    'features': 'Latest nonempty macro snapshot strictly before publication-month start. Changes stay within vintage. Include observation ages and topic-specific forecast-direction times own-target trend interactions. Monthly current macro scalars enter the claim head, not a reconstructed historical sequence.',
    'labels': 'Original bands (production +/-2 percent, unemployment +/-0.5 percentage points). Training labels from latest archive strictly before stopping-window start, stopping labels from latest archive strictly before assessment start. Endpoint+3 months must strictly precede its stage boundary. Revised assessment hits used only for scoring after fits.',
    'folds': 'Twenty-year fitting window ending five years before origin; five earlier years for stopping, next five for assessment, horizon+3-month purges at each boundary. Common support begins no earlier than 1965-12.',
    'models': ['8-unit GRU ensemble of all three seeds', 'metadata logistic C=1', 'metadata plus flattened press history logistic C=1', 'training prevalence'],
    'metrics': 'Article-weighted Brier and log loss, accuracy, AUC and AP, pooled and separately by topic; equal mean across four folds. Recompute topic article weights.',
    'decision': 'Display every arm. No hyperparameter search, promotion, new superiority p-values or 1995–2010 evaluation. Compare within this matched experiment, not directly to earlier whole-corpus RNN scores.',
    'limits': 'Machine interpretation remains unvalidated. Archive coverage is incomplete and quarterly unemployment vintages can be stale. Historical corpus selection and stopping-stage target revisions limit real-time reconstruction. Revised assessment truth differs from real-time training truth.',
}


def vintage_hits(frame, archive, cutoff, topic):
    vintage, snapshot = archive.snapshot(pd.Period(cutoff, 'M'))
    result = []
    for row in frame.itertuples():
        start = row.month; end = start+int(row.horizon_used)
        first = np.nan if snapshot is None else snapshot.get(start, np.nan)
        last = np.nan if snapshot is None else snapshot.get(end, np.nan)
        valid = end+3 < pd.Period(cutoff, 'M') and np.isfinite(first) and np.isfinite(last) and first > 0
        change = (last-first if topic == 'employment' else 100*(last/first-1)) if valid else np.nan
        band = BANDS[topic]
        up, down = ('up', 'down') if topic == 'employment' else ('improve', 'worsen')
        outcome = None if not valid else up if change > band and not np.isclose(change, band, rtol=1e-10, atol=1e-10) else down if change < -band and not np.isclose(change, -band, rtol=1e-10, atol=1e-10) else 'flat'
        result.append(dict(record_id=row.record_id, vintage_hit=np.nan if outcome is None else int(row.predicted_norm == outcome),
                           realized=outcome, label_vintage=vintage,
                           label_available_by=None if vintage is None else str(archive.dates[vintage].date()),
                           cutoff=str(cutoff), target_end=str(end)))
    return pd.DataFrame(result)


def prepare_common(labels, macro, archives, origin):
    labels = labels.copy()
    origin = pd.Period(origin, 'M'); stop = origin-60
    core = macro.set_index('origin')
    if not core.index.is_unique:
        raise ValueError('Duplicate macro month')
    common = core.index[np.isfinite(core[list(CORE_FEATURES)].to_numpy(float)).all(axis=1)]
    labels['scorable'] &= labels.topic.isin(['general_business', 'employment']) & labels.month.isin(common)
    audits = []
    for stage, low, cutoff in [('train', stop-240, stop), ('stopping', stop, origin)]:
        for topic, name in [('general_business', 'IPT'), ('employment', 'RUC')]:
            mask = labels.scorable & labels.topic.eq(topic) & (labels.month >= low) & (labels.month < cutoff)
            values = vintage_hits(labels[mask], archives[name], cutoff, topic)
            values['stage'] = stage
            values['original_revised_hit'] = labels.loc[mask, 'hit'].to_numpy()
            audits.append(values)
            labels.loc[mask, 'hit'] = values.vintage_hit.to_numpy()
            labels.loc[mask, 'scorable'] = values.vintage_hit.notna().to_numpy()
    data = prepare_fold(labels, str(origin), 20)
    audit = pd.concat(audits, ignore_index=True)
    data['macro'] = core.loc[pd.PeriodIndex(data['frame'].month)].reset_index(drop=True)
    for name in ['IPT', 'RUC']:
        available = pd.to_datetime(data['macro'][f'{name}_available_by'])
        if available.isna().any() or not (available.to_numpy() < data['frame'].month.dt.to_timestamp().to_numpy()).all():
            raise ValueError('Macro release is not strictly before the publication month')
    return data, audit


def feature_matrix(frame, macro, names):
    values = macro[list(CORE_FEATURES)].copy().reset_index(drop=True)
    direction = frame.predicted_norm.map({'improve': 1, 'worsen': -1, 'up': 1, 'down': -1, 'flat': 0}).to_numpy(float)
    values['production_alignment'] = values.ip_growth_6m.to_numpy()*direction*frame.topic.eq('general_business').to_numpy()
    values['unemployment_alignment'] = values.unemployment_change_3m.to_numpy()*direction*frame.topic.eq('employment').to_numpy()
    x = values[names].to_numpy(float)
    if not np.isfinite(x).all():
        raise ValueError('Missing current macro predictors')
    return x


def add_arm(data, arm):
    result = dict(data)
    names = ARMS[arm]
    scaler = None
    if names:
        raw = feature_matrix(data['frame'], data['macro'], names)
        scaler = StandardScaler().fit(raw[data['masks']['train']])
        result['claim'] = np.column_stack([data['claim'], scaler.transform(raw)]).astype('float32')
    return result, scaler


def bundle_probabilities(bundle, labels, macro, target):
    """Apply one saved exploratory fold bundle; no target outcomes are read."""
    from proquest_rnn_runner import prepare_inputs
    from proquest_rnn_development import DevelopmentGRU
    params = joblib.load(Path(bundle)/'preprocessing.joblib')
    sequence, claim = prepare_inputs(labels, target, params)
    current = macro.set_index('origin').loc[pd.PeriodIndex(target.month)].reset_index(drop=True)
    for name in ['IPT', 'RUC']:
        release = pd.to_datetime(current[f'{name}_available_by'])
        if release.isna().any() or not (release.to_numpy() < target.month.dt.to_timestamp().to_numpy()).all():
            raise ValueError('Unavailable macro inputs')
    if params['macro_features']:
        extra = params['macro_scaler'].transform(feature_matrix(target, current, params['macro_features']))
        claim = np.column_stack([claim, extra]).astype('float32')
    predictions = {}
    for name, model in params['logistic_models'].items():
        x = claim if name.startswith('logistic_metadata__') else np.column_stack([claim, sequence.reshape(len(claim), -1)])
        predictions[name.split('__')[0]] = model.predict_proba(x)[:, list(model.classes_).index(1)]
    ps = []
    for seed in SEEDS:
        saved = torch.load(Path(bundle)/f'gru_{seed}.pt', weights_only=False)
        model = DevelopmentGRU(sequence.shape[-1], claim.shape[-1], CONFIG['hidden'], CONFIG['dropout'])
        model.load_state_dict(saved['state_dict']); model.eval()
        ps.append(neural_probabilities(model, torch.from_numpy(sequence), torch.from_numpy(claim)))
    predictions['gru'] = np.mean(ps, axis=0)
    return predictions


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=Path('data/scored/proquest/macro_claim_inputs_v1'))
    args = parser.parse_args(); out = args.out
    out.mkdir(parents=True, exist_ok=False)
    (out/'specification.json').write_text(json.dumps(SPEC, indent=2)+'\n')
    started = time.monotonic()
    torch.set_num_threads(2); torch.use_deterministic_algorithms(True)
    prior = Path('data/scored/proquest/target_robustness_v1/summary.json')
    inputs = json.loads(prior.read_text())['inputs_sha256']
    inputs[str(SOURCE)] = json.loads(Path('data/scored/proquest/rnn/summary.json').read_text())['score_file_sha256']
    inputs.update(json.loads(Path('data/scored/proquest/modern_readiness/model_freeze.json').read_text())['files_sha256'])
    archives, sources, coverage = load_archives()
    inputs.update({s['path']: s['sha256'] for s in sources.values()})
    for path, sha in inputs.items():
        if digest(path) != sha:
            raise ValueError(f'Changed frozen input: {path}')
    labels = development_labels()
    macro = macro_features(archives, pd.period_range(labels.month.min(), '1994-12', freq='M'))
    macro.to_csv(out/'macro_availability.csv', index=False)
    coverage.to_csv(out/'archive_coverage.csv', index=False)
    metrics, counts, seed_metrics = [], [], []
    for origin in ORIGINS:
        data, audit = prepare_common(labels, macro, archives, origin)
        folder = out/origin; folder.mkdir()
        audit.to_csv(folder/'training_label_audit.csv.gz', index=False)
        frame = data['frame']; mask = data['masks']['assessment']
        split = frame[['record_id', 'page_id', 'date', 'topic', 'hit']].copy()
        for stage, m in data['masks'].items():
            split.loc[m, 'stage'] = stage
            counts.append(dict(origin=origin, stage=stage, n_claims=int(m.sum()), n_articles=frame.loc[m, 'page_id'].nunique()))
        split.to_csv(folder/'splits.csv.gz', index=False)
        prediction = frame.loc[mask, ['record_id', 'page_id', 'date', 'year', 'topic', 'hit']].copy()
        for arm in ARMS:
            fit, scaler = add_arm(data, arm)
            path = folder/arm; path.mkdir()
            controls = fit_controls(fit)
            parameters = dict(fit['parameters'], macro_features=ARMS[arm], macro_scaler=scaler, logistic_models=controls)
            joblib.dump(parameters, path/'preprocessing.joblib')
            probabilities = {}
            for name, model in controls.items():
                x = fit['claim'] if name.startswith('logistic_metadata__') else np.column_stack([fit['claim'], fit['sequence'].reshape(len(frame), -1)])
                probabilities[name.split('__')[0]] = model.predict_proba(x[mask])[:, list(model.classes_).index(1)]
            ps, histories = [], []
            for seed in SEEDS:
                model, history, best = fit_seed(fit, CONFIG, seed)
                histories += history
                torch.save(dict(state_dict=model.state_dict(), context_size=fit['sequence'].shape[-1], claim_size=fit['claim'].shape[-1],
                                configuration=CONFIG, added_features=ARMS[arm], seed=seed, best_epoch=best), path/f'gru_{seed}.pt')
                p = neural_probabilities(model, torch.from_numpy(fit['sequence'][mask]), torch.from_numpy(fit['claim'][mask]))
                ps.append(p)
                prediction[f'gru_seed_{seed}__{arm}'] = p
                seed_metrics.append(dict(origin=origin, arm=arm, seed=seed, best_epoch=best, **scores(fit['y'][mask], p, fit['weights'][mask])))
            probabilities['gru'] = np.mean(ps, axis=0)
            probabilities['prevalence'] = np.full(mask.sum(), np.average(fit['y'][fit['masks']['train']], weights=fit['weights'][fit['masks']['train']]))
            pd.DataFrame(histories).to_csv(path/'training_history.csv', index=False)
            # Exact saved-bundle reload check, with targets stripped of outcomes.
            target = frame.loc[mask].drop(columns=['hit', 'scorable', 'basis'])
            loaded = bundle_probabilities(path, labels, macro, target)
            for name, p in loaded.items():
                np.testing.assert_allclose(p, probabilities[name], rtol=0, atol=1e-7)
            for name, p in probabilities.items():
                prediction[f'{name}__{arm}'] = p
                for topic in ['all', 'general_business', 'employment']:
                    sub = np.ones(mask.sum(), dtype=bool) if topic == 'all' else frame.loc[mask, 'topic'].eq(topic).to_numpy()
                    target = frame.loc[mask].loc[sub]
                    metrics.append(dict(origin=origin, arm=arm, model=name, topic=topic, n_claims=len(target),
                                        **scores(fit['y'][mask][sub], p[sub], article_weights(target))))
            print(f'{origin} {arm}: GRU Brier {metrics[-6]["brier"]:.5f}', flush=True)
        prediction.to_csv(folder/'predictions.csv.gz', index=False)
        pd.DataFrame(metrics).to_csv(out/'fold_metrics.csv', index=False)
    table = pd.DataFrame(metrics)
    baseline = table.query("arm=='none'")[['origin', 'model', 'topic', 'brier']].rename(columns={'brier': 'baseline_brier'})
    paired = table.merge(baseline, on=['origin', 'model', 'topic'], validate='many_to_one')
    paired['brier_improvement'] = paired.baseline_brier-paired.brier
    paired.to_csv(out/'paired_fold_metrics.csv', index=False)
    aggregate = paired.groupby(['topic', 'model', 'arm']).agg(mean_brier=('brier', 'mean'), mean_improvement=('brier_improvement', 'mean'),
                    folds_improved=('brier_improvement', lambda v: int((v > 0).sum())), worst_fold_brier=('brier', 'max')).reset_index()
    aggregate.to_csv(out/'summary_metrics.csv', index=False)
    pd.DataFrame(counts).to_csv(out/'support.csv', index=False)
    pd.DataFrame(seed_metrics).to_csv(out/'seed_metrics.csv', index=False)
    body = '<!doctype html><html lang="en"><meta charset="utf-8"><title>Macro claim inputs</title><style>body{font:16px/1.5 system-ui;max-width:1200px;margin:35px auto}td,th{padding:7px;border-bottom:1px solid #ddd}</style><h1>Historical macro inputs for claim-correctness models</h1><p>Exploratory matched input comparison on previously explored 1975–1994 publications. Every arm uses the same business/employment claims, historical-vintage training/stopping targets and original scoring bands. Revised assessment truth is used only after fitting. This is not a comparison with the earlier whole-corpus scores. No model is promoted and no p-values are selected.</p>'
    body += aggregate.to_html(index=False, float_format=lambda x: f'{x:.6f}')
    body += '<p>Lower Brier is better; positive improvement favors adding inputs within that model. Equal mean over four eras; article weighting within era and topic. All three neural seeds retained. Input groups include vintage trend, observation age and forecast-direction alignment. Historical inputs become available only in late 1965, shortening early fitting windows. Source meanings remain provisional. All saved bundles reproduce their predictions when reloaded without outcome columns. See specification.json, availability, split and label audits for timing rules.</p></html>'
    (out/'report.html').write_text(body)
    for path, sha in inputs.items():
        if digest(path) != sha:
            raise ValueError(f'Input changed: {path}')
    summary = dict(status='complete', seconds=time.monotonic()-started, neural_fits=48, logistic_fits=32, promoted=False,
                   new_p_values=False, evaluation_1995_onward=False, bundle_reload_verified=True,
                   inputs_sha256=inputs, code_sha256=digest(__file__),
                   imported_code_sha256={f'src/{n}.py': digest(f'src/{n}.py') for n in ['proquest_rnn_development', 'proquest_rnn_runner', 'proquest_vintages', 'proquest_rnn_permutation']},
                   outputs_sha256={str(p): digest(p) for p in out.rglob('*') if p.is_file()})
    (out/'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    print(aggregate.query("topic=='all'").to_string(index=False))


if __name__ == '__main__':
    main()
