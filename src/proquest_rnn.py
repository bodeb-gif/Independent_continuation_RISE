"""Chronological ProQuest claim-correctness experiment with a small GRU RNN.

No quotes are available locally. The recurrent input consists of earlier
monthly forecast distributions; the current claim supplies metadata only.
Run from the repository root after proquest_descriptive.py.
"""
import argparse
import base64
import copy
import hashlib
import html
import json
from pathlib import Path
import platform

import joblib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (average_precision_score, balanced_accuracy_score,
                             brier_score_loss, log_loss, roc_auc_score)
from sklearn.preprocessing import OneHotEncoder, StandardScaler
import torch
from torch import nn

from proquest_followups import load_claims

OUT = Path('data/scored/proquest/rnn')
TOPICS = ['general_business', 'markets', 'prices', 'employment']
DIRECTIONS = ['improve', 'worsen', 'up', 'down', 'flat']
CLAIM_CATEGORIES = ['topic', 'paper', 'voice', 'confidence', 'predicted_norm', 'horizon_basis']


def monthly_context(claims):
    """Features depend only on print-time labels, never outcome eligibility."""
    national = claims[(claims.scope == 'national') & claims.topic.isin(TOPICS) &
                      claims.predicted_norm.isin(DIRECTIONS)]
    months = pd.period_range(claims.month.min() - 12, claims.month.max(), freq='M')
    values = pd.DataFrame(index=months)
    for topic in TOPICS:
        group = national[national.topic == topic]
        counts = group.groupby(['month', 'predicted_norm']).size().unstack(fill_value=0)
        counts = counts.reindex(index=months, columns=DIRECTIONS, fill_value=0)
        total = counts.sum(axis=1)
        for direction in DIRECTIONS:
            values[f'{topic}:{direction}_share'] = counts[direction].div(total.replace(0, np.nan)).fillna(0)
        values[f'{topic}:log_claim_count'] = np.log1p(total)
        values[f'{topic}:observed'] = (total > 0).astype(float)
    return values


def sequence_indices(months, calendar, lookback=12):
    """Exactly lookback calendar months, ending before the publication month."""
    endpoints = calendar.get_indexer(pd.PeriodIndex(months, freq='M'))
    if (endpoints < lookback).any():
        raise ValueError('Calendar lacks the full preceding sequence')
    return endpoints[:, None] - np.arange(lookback, 0, -1)[None, :]


def chronological_splits(scored, validation_start='1985-01', test_start='1995-01', label_lag=3):
    """Purge unresolved training/validation horizons before the next stage."""
    if label_lag < 0:
        raise ValueError('Label lag must be nonnegative')
    val, test = pd.Period(validation_start, 'M'), pd.Period(test_start, 'M')
    if val >= test:
        raise ValueError('Validation must precede test')
    # Conservatively allow three additional calendar months for publication of
    # endpoint outcomes. Revised series are still not a real-time vintage audit.
    available = pd.PeriodIndex([m + int(h) + label_lag for m, h in zip(scored.month, scored.horizon_used)], freq='M')
    publication = pd.PeriodIndex(scored.month, freq='M')
    masks = {'train': (publication < val) & (available < val),
             'validation': (publication >= val) & (publication < test) & (available < test),
             'test': publication >= test}
    excluded = (~np.logical_or.reduce(list(masks.values()))).sum()
    for name, mask in masks.items():
        if not mask.any() or scored.loc[mask, 'hit'].nunique() != 2:
            raise ValueError(f'{name} needs observations of both outcome classes')
    page_sets = {name: set(scored.loc[mask, 'page_id']) for name, mask in masks.items()}
    for left, right in [('train', 'validation'), ('train', 'test'), ('validation', 'test')]:
        if page_sets[left] & page_sets[right]:
            raise ValueError('An article crosses a temporal split')
    return masks, available, int(excluded)


def article_weights(frame):
    weights = 1 / frame.groupby('page_id').page_id.transform('size').to_numpy()
    return weights / weights.mean()


def metrics(y, probabilities, weights=None):
    return {'average_precision': average_precision_score(y, probabilities, sample_weight=weights),
            'roc_auc': roc_auc_score(y, probabilities, sample_weight=weights),
            'brier_score': brier_score_loss(y, probabilities, sample_weight=weights),
            'log_loss': log_loss(y, probabilities, sample_weight=weights, labels=[0, 1]),
            'balanced_accuracy': balanced_accuracy_score(y, probabilities >= .5, sample_weight=weights),
            'positive_prevalence': np.average(y, weights=weights)}


class ClaimGRU(nn.Module):
    def __init__(self, context_size, claim_size, hidden=24):
        super().__init__()
        self.gru = nn.GRU(context_size, hidden, batch_first=True)
        self.head = nn.Sequential(nn.Linear(hidden + claim_size, 32), nn.ReLU(),
                                  nn.Dropout(.15), nn.Linear(32, 1))

    def forward(self, context, claim):
        _, hidden = self.gru(context)
        return self.head(torch.cat([hidden[-1], claim], dim=1)).squeeze(1)


def neural_probabilities(model, context, claim, batch=4096):
    model.eval()
    predictions = []
    with torch.no_grad():
        for start in range(0, len(claim), batch):
            predictions.append(model(context[start:start+batch], claim[start:start+batch]).sigmoid().numpy())
    return np.concatenate(predictions)


def train_gru(context, claim, y, weights, masks, seed, epochs=20, hidden=24):
    torch.manual_seed(seed)
    rng = np.random.default_rng(seed)
    model = ClaimGRU(context.shape[-1], claim.shape[-1], hidden)
    optimizer = torch.optim.AdamW(model.parameters(), lr=.001, weight_decay=.001)
    loss_function = nn.BCEWithLogitsLoss(reduction='none')
    training = np.flatnonzero(masks['train'])
    validation = np.flatnonzero(masks['validation'])
    best, best_state, stalled, history = np.inf, None, 0, []
    for epoch in range(1, epochs + 1):
        model.train()
        running, n = 0., 0
        for indexes in np.array_split(rng.permutation(training), int(np.ceil(len(training) / 1024))):
            optimizer.zero_grad()
            losses = loss_function(model(context[indexes], claim[indexes]), y[indexes])
            loss = (losses * weights[indexes]).mean()
            loss.backward(); nn.utils.clip_grad_norm_(model.parameters(), 1.); optimizer.step()
            running += loss.item() * len(indexes); n += len(indexes)
        probabilities = neural_probabilities(model, context[validation], claim[validation])
        validation_loss = log_loss(y[validation].numpy(), probabilities, sample_weight=weights[validation].numpy(), labels=[0, 1])
        history.append({'seed': seed, 'epoch': epoch, 'train_weighted_loss': running / n,
                        'validation_weighted_loss': validation_loss})
        print(f'Seed {seed}, epoch {epoch}: train={running/n:.4f}, validation={validation_loss:.4f}', flush=True)
        if validation_loss < best - .0001:
            best, best_state, stalled = validation_loss, copy.deepcopy(model.state_dict()), 0
            best_epoch = epoch
        else:
            stalled += 1
            if stalled >= 4:
                break
    model.load_state_dict(best_state)
    return model, history, best_epoch


def block_comparison(test, recurrent, baseline, draws=400):
    """Paired five-year publication-block resampling; descriptive uncertainty."""
    y = test.hit.to_numpy()
    weights = article_weights(test)
    blocks = test.year.to_numpy() // 5
    unique = np.unique(blocks)
    block_codes = np.searchsorted(unique, blocks)
    rng = np.random.default_rng(103)
    gaps = []
    for _ in range(draws):
        sampled = rng.choice(unique, len(unique), replace=True)
        multiplicities = np.bincount(np.searchsorted(unique, sampled), minlength=len(unique))[block_codes]
        w = weights * multiplicities
        eligible = w > 0
        if np.unique(y[eligible]).size < 2:
            continue
        gaps.append(average_precision_score(y[eligible], recurrent[eligible], sample_weight=w[eligible]) -
                    average_precision_score(y[eligible], baseline[eligible], sample_weight=w[eligible]))
    return {'n_blocks': len(unique), 'n_draws': len(gaps),
            'average_precision_gap': average_precision_score(y, recurrent, sample_weight=weights) - average_precision_score(y, baseline, sample_weight=weights),
            'block_interval_low': np.quantile(gaps, .025), 'block_interval_high': np.quantile(gaps, .975)}


def make_report(out, summary, results, history, predictions):
    test = results[(results.split == 'test') & (results.weighting == 'equal_article')]
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    colors = ['#d47835' if m.startswith('gru') else '#174e70' for m in test.model]
    for ax, column, title in zip(axes, ['average_precision', 'brier_score'], ['Average precision: higher is better', 'Brier score: lower is better']):
        ax.barh(test.model, test[column], color=colors)
        ax.set_title(title); ax.grid(axis='x', alpha=.15)
    fig.suptitle('Unseen 1995–2010 ProQuest claims · equal weight per article')
    fig.tight_layout(); fig.savefig(out / 'test_metrics.png', dpi=150, bbox_inches='tight'); plt.close(fig)
    fig, ax = plt.subplots(figsize=(9, 4.5))
    for seed, group in history.groupby('seed'):
        ax.plot(group.epoch, group.validation_weighted_loss, marker='o', label=f'Seed {seed}')
    ax.set_xlabel('Epoch'); ax.set_ylabel('Validation log loss'); ax.set_title('Early stopping uses 1985–1994 validation labels only')
    ax.legend(); ax.grid(alpha=.15); fig.tight_layout(); fig.savefig(out / 'learning_curves.png', dpi=150); plt.close(fig)
    model_names = ['logistic_metadata_history', 'gru_ensemble']
    fig, ax = plt.subplots(figsize=(7, 5))
    for name in model_names:
        p = predictions[name].to_numpy(); y = predictions.hit.to_numpy(); w = article_weights(predictions)
        bins = pd.cut(p, np.linspace(0, 1, 11), include_lowest=True)
        points = []
        for category in bins.categories:
            mask = bins == category
            if mask.sum() >= 30:
                points.append((np.average(p[mask], weights=w[mask]), np.average(y[mask], weights=w[mask])))
        points = np.array(points)
        ax.plot(points[:, 0], points[:, 1], 'o-', label=name)
    ax.plot([0, 1], [0, 1], '--', color='#888'); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    ax.set_xlabel('Predicted probability'); ax.set_ylabel('Observed correctness rate'); ax.set_title('Held-out calibration · equal article weight'); ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(out / 'calibration.png', dpi=150); plt.close(fig)
    methods = [
        f"Target: whether an eligible annual machine-verified ProQuest claim matches the first report's deterministic outcome rule. "
        f"{summary['eligible_claims']:,} benchmark-scored claims are eligible. Pre-1919 NBER-proxy scores are excluded; "
        'they depend on retrospectively dated recession states with unavailable real-time label dates.',
        'The GRU receives the previous 12 complete calendar months of national forecast distributions across four topics. '
        'Each topic supplies five normalized direction shares, log claim count, and an observed-coverage indicator. '
        'The current publication month is excluded. Context includes readable verified claims regardless of whether a future outcome can be scored. '
        'Log claim counts describe this sampled export, not newspaper attention or population article denominators.',
        'Current-claim inputs are topic, paper family, voice, hedging category, predicted direction, horizon basis, and numeric horizon. '
        'No quote text, speaker identities, realized outcomes, past hit rates, crisis annotations, verifier prose, NBER state, or macro reference value enters the model. '
        'A one-layer 24-unit GRU feeds a 32-unit head with 15% dropout. Three preset seeds are averaged; none is selected by test performance.',
        'Training publications precede 1985, validation publications span 1985–1994, and the final test spans 1995–2010. '
        'Training and validation labels are purged unless their endpoint plus a conservative three-month release allowance precedes the next split. '
        'All scalers, category vocabularies and logistic baselines are fitted on training data only. Validation log loss selects neural epochs. '
        'Earlier test-period forecast labels may enter later test histories, as they would become available in sequential use; test outcome labels never do.',
        'Every article receives equal total training weight; equal-article evaluation is primary and claim-weighted metrics are exported too. '
        'Logistic metadata plus flattened history is the main sequence-free baseline and receives the same past context. '
        'This comparison does not isolate recurrence from neural nonlinearity; a matched feed-forward neural control remains a future experiment. '
        'The constant baseline predicts the training correctness prevalence. Average precision summarizes the precision-recall curve; '
        'its no-skill reference is the evaluated subset prevalence. Brier score and log loss assess probability quality.',
        'This is one exploratory chronological holdout, not proof of durable forecasting skill. The four test publication blocks '
        'share overlapping outcome horizons and few business cycles. Frozen reference outcomes are revised historical series; the release '
        'allowance does not establish true vintage availability. Machine-verification and outcome matching still require human validation. '
        'Market claims remain a broad-stock-price proxy, and stripped exports cannot support definitive quote deduplication.',
        'Rebuild: python src/proquest_rnn.py after installing requirements-proquest-rnn.txt. Checkpoints, train-only preprocessing, '
        'split assignments, predictions, histories, source hashes and exact settings are saved alongside this report. '
        'Library references: https://docs.pytorch.org/docs/stable/generated/torch.nn.GRU.html and '
        'https://scikit-learn.org/stable/modules/generated/sklearn.metrics.average_precision_score.html.'
    ]
    gap = summary['gru_vs_history_logistic']
    result_text = (f"Held-out equal-article average-precision gap, GRU ensemble minus history logistic: {gap['average_precision_gap']:+.4f}. "
                   f"Descriptive five-year block interval: [{gap['block_interval_low']:+.4f}, {gap['block_interval_high']:+.4f}]. "
                   'The held-out result is reported as observed; it is not used to choose a different architecture.')
    display = test[['model', 'average_precision', 'roc_auc', 'brier_score', 'log_loss', 'balanced_accuracy', 'positive_prevalence']].copy()
    for col in display.columns[1:]: display[col] = display[col].map(lambda v: f'{v:.4f}')
    rows = ['# ProQuest GRU experiment', '', result_text, '', '| ' + ' | '.join(display.columns) + ' |', '| ' + ' | '.join(['---'] * len(display.columns)) + ' |']
    rows += ['| ' + ' | '.join(row) + ' |' for row in display.itertuples(index=False, name=None)]
    rows += ['', '## Methods and limits', '']
    for paragraph in methods: rows += [paragraph, '']
    (out / 'report.md').write_text('\n'.join(rows))
    blocks = ['<h1>ProQuest GRU experiment</h1>', '<p>' + html.escape(result_text) + '</p>', display.to_html(index=False, border=0)]
    for name in ['test_metrics.png', 'learning_curves.png', 'calibration.png']:
        blocks.append('<img src="data:image/png;base64,' + base64.b64encode((out/name).read_bytes()).decode() + '" alt="' + name + '">')
    blocks += ['<h2>Methods and limits</h2>'] + ['<p>' + html.escape(p) + '</p>' for p in methods]
    style = 'body{font:16px system-ui;line-height:1.6;max-width:1150px;margin:40px auto;padding:0 24px;color:#17364b}img{max-width:100%}table{font-size:13px;border-collapse:collapse}th,td{padding:9px;border-bottom:1px solid #ddd}'
    (out / 'report.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><title>ProQuest RNN experiment</title><style>'+style+'</style><body>'+''.join(blocks)+'</body></html>')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=OUT)
    parser.add_argument('--epochs', type=int, default=20)
    args = parser.parse_args()
    if not 1 <= args.epochs <= 100:
        raise ValueError('Use 1–100 epochs')
    out = args.out; out.mkdir(parents=True, exist_ok=True)
    torch.set_num_threads(2); torch.use_deterministic_algorithms(True)
    claims, metadata, digests = load_claims()
    scored = claims[claims.scorable & claims.basis.ne('NBER proxy')].copy().reset_index(drop=True)
    masks, availability, excluded = chronological_splits(scored)
    context_frame = monthly_context(claims)
    context_scaler = StandardScaler().fit(context_frame.loc[context_frame.index < pd.Period('1985-01', 'M')])
    scaled_context = context_scaler.transform(context_frame).astype('float32')
    indexes = sequence_indices(scored.month, context_frame.index)
    context_array = scaled_context[indexes]
    encoder = OneHotEncoder(handle_unknown='ignore', sparse_output=False, dtype=np.float32)
    categories = scored[CLAIM_CATEGORIES].fillna('missing')
    encoder.fit(categories.loc[masks['train']])
    horizon_scaler = StandardScaler().fit(scored.loc[masks['train'], ['horizon_used']])
    claim_array = np.column_stack([encoder.transform(categories), horizon_scaler.transform(scored[['horizon_used']])]).astype('float32')
    y_array = scored.hit.to_numpy(dtype='float32')
    weights_array = np.ones(len(scored), dtype='float32')
    for mask in masks.values(): weights_array[mask] = article_weights(scored.loc[mask])
    print('Split counts:', {name: int(mask.sum()) for name, mask in masks.items()}, 'purged:', excluded, flush=True)
    flat_history = context_array.reshape(len(scored), -1)
    features = {'logistic_metadata': claim_array,
                'logistic_metadata_history': np.column_stack([claim_array, flat_history])}
    predictions = {}; fitted = {}
    for name, x in features.items():
        model = LogisticRegression(C=1., max_iter=1500, random_state=0)
        model.fit(x[masks['train']], y_array[masks['train']], sample_weight=weights_array[masks['train']])
        predictions[name] = model.predict_proba(x)[:, 1]; fitted[name] = model
        print(f'{name} fitted.', flush=True)
    prevalence = np.average(y_array[masks['train']], weights=weights_array[masks['train']])
    predictions['constant_train_prevalence'] = np.full(len(scored), prevalence)
    context, claim = torch.from_numpy(context_array), torch.from_numpy(claim_array)
    y, weights = torch.from_numpy(y_array), torch.from_numpy(weights_array)
    histories, epochs = [], {}
    for seed in [11, 29, 47]:
        model, history, best_epoch = train_gru(context, claim, y, weights, masks, seed, args.epochs)
        histories.extend(history); epochs[str(seed)] = best_epoch
        predictions[f'gru_seed_{seed}'] = neural_probabilities(model, context, claim)
        torch.save({'state_dict': model.state_dict(), 'context_size': context.shape[-1],
                    'claim_size': claim.shape[-1], 'hidden_size': 24, 'seed': seed,
                    'best_epoch': best_epoch}, out / f'gru_seed_{seed}.pt')
    predictions['gru_ensemble'] = np.mean([predictions[f'gru_seed_{seed}'] for seed in [11, 29, 47]], axis=0)
    results = []
    for split, mask in masks.items():
        for name, probabilities in predictions.items():
            for weighting, w in [('claim', None), ('equal_article', weights_array[mask])]:
                results.append({'split': split, 'model': name, 'weighting': weighting, 'n_claims': int(mask.sum()),
                                'n_articles': scored.loc[mask, 'page_id'].nunique(), **metrics(y_array[mask], probabilities[mask], w)})
    results = pd.DataFrame(results); results.to_csv(out / 'metrics.csv', index=False)
    history = pd.DataFrame(histories); history.to_csv(out / 'training_history.csv', index=False)
    split_rows = scored[['record_id', 'page_id', 'date', 'horizon_used']].copy()
    split_rows['label_available_month_allowance'] = availability.astype(str); split_rows['split'] = 'purged'
    for name, mask in masks.items(): split_rows.loc[mask, 'split'] = name
    split_rows.to_csv(out / 'split_assignments.csv.gz', index=False, compression='gzip')
    test = scored.loc[masks['test']].copy()
    prediction_rows = test[['record_id', 'page_id', 'date', 'year', 'topic', 'paper', 'horizon_basis', 'hit']].copy()
    for name, probabilities in predictions.items(): prediction_rows[name] = probabilities[masks['test']]
    prediction_rows.to_csv(out / 'test_predictions.csv.gz', index=False, compression='gzip')
    subgroup = []
    for key in ['topic', 'paper', 'horizon_basis', 'decade']:
        for value, group in test.groupby(key):
            if len(group) < 100 or group.hit.nunique() < 2: continue
            local_weights = article_weights(group)
            for name in ['gru_ensemble', 'logistic_metadata_history']:
                subgroup.append({'grouping': key, 'group': str(value), 'model': name, 'n_claims': len(group),
                                 **metrics(group.hit.to_numpy(), predictions[name][group.index], local_weights)})
    pd.DataFrame(subgroup).to_csv(out / 'test_subgroups.csv', index=False)
    joblib.dump({'encoder': encoder, 'horizon_scaler': horizon_scaler, 'context_scaler': context_scaler,
                 'context_features': list(context_frame.columns), 'claim_categories': CLAIM_CATEGORIES,
                 'logistic_models': fitted, 'constant_prevalence': prevalence}, out / 'preprocessing_and_baselines.joblib')
    gap = block_comparison(test, predictions['gru_ensemble'][masks['test']], predictions['logistic_metadata_history'][masks['test']])
    facts = {'target': 'deterministically_scored_claim_correctness', 'verified_claims': len(claims),
             'eligible_claims': len(scored), 'excluded_NBER_proxy_claims': int((claims.scorable & claims.basis.eq('NBER proxy')).sum()),
             'split_counts': {k: int(v.sum()) for k, v in masks.items()}, 'purged_claims': excluded,
             'validation_start': '1985-01', 'test_start': '1995-01', 'label_lag_allowance_months': 3,
             'lookback_months': 12, 'hidden_units': 24, 'seeds': [11, 29, 47], 'maximum_epochs': args.epochs,
             'optimizer': 'AdamW', 'learning_rate': .001, 'weight_decay': .001, 'batch_size': 1024,
             'head_units': 32, 'dropout': .15, 'early_stop_patience': 4, 'gradient_clip_norm': 1.,
             'training_weighting': 'equal_total_weight_per_article', 'device': 'cpu',
             'selected_epochs': epochs, 'gru_vs_history_logistic': gap, 'reference': metadata['reference'],
             'verified_source_sha256': digests, 'code_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
             'score_file_sha256': hashlib.sha256(Path('data/scored/proquest/descriptive/scored_claims.csv.gz').read_bytes()).hexdigest(),
             'versions': {'python': platform.python_version(), 'torch': torch.__version__, 'numpy': np.__version__,
                          'pandas': pd.__version__, 'sklearn': __import__('sklearn').__version__}}
    (out / 'summary.json').write_text(json.dumps(facts, indent=2, default=lambda value: value.item() if isinstance(value, np.generic) else str(value)) + '\n')
    make_report(out, facts, results, history, prediction_rows)
    print(results[(results.split == 'test') & (results.weighting == 'equal_article')].to_string(index=False))
    print('GRU vs history logistic:', gap); print('Report:', out / 'report.html')


if __name__ == '__main__':
    main()
