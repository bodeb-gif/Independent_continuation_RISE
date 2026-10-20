"""Exploratory age-weighting study on previously inspected pre-1985 development data."""
import json
from pathlib import Path
import platform
import time

import joblib
import numpy as np
import pandas as pd
import torch

from proquest_rnn_development import (SOURCE, SEEDS, digest, prepare_fold,
                                     run_candidate, save_split)
from proquest_rnn_runner import REQUIRED

OUT = Path('data/scored/proquest/rnn_age_weighting_v1')
PRIOR = Path('data/scored/proquest/rnn_development_v1')
INCUMBENT = 'gru8_standard_20'
CONTROL = 'gru8_standard_expanding'
ORIGINS = ['1965-01', '1970-01', '1975-01', '1980-01']
CANDIDATES = [dict(id=f'gru8_age_{h}', hidden=8, dropout=.15, weight_decay=.001,
                   window_years=None, half_life_years=h) for h in [10, 20, 40]]
SPEC = {
    'date': '2026-10-19',
    'status': 'Adaptive exploratory follow-up motivated by inspected development errors; not independent confirmation',
    'candidates': CANDIDATES, 'seeds': SEEDS, 'origins': ORIGINS,
    'scope': 'Verified annual ProQuest only; discard publications from 1985 onward before model arrays. Baseline feature arm only.',
    'weights': 'Training article weights multiplied by 2**(-age_months/(12*half_life_years)), with age measured from the stopping-window start. Normalize resulting training weights to mean one. Same-month articles share the age factor. Stopping and assessment weights remain unchanged.',
    'preprocessing': 'Expanding-history train-only scalers and vocabulary unchanged from gru8_standard_expanding; decay affects the fitting loss only. No observation truncation or feature changes.',
    'evaluation': 'Same four five-year development folds, nested five-year stopping windows, horizon+3 month purges, and training settings as development_v1. Reuse hash-verified saved incumbent and unweighted control predictions; assess identical claim IDs.',
    'selection': 'Qualify only if equal-fold mean Brier improves over incumbent by >=0.002, at least three of four folds improve, worst-fold loss is no worse than incumbent, and mean loss beats the same-size expanding control. Choose lowest mean then worst fold then ID. Otherwise retain incumbent. No seed or p-value selection.',
    'later_data': 'No 1985–1994 confirmation fitting/evaluation and no 1995–2010 test evaluation. No new final production bundle or automatic replacement. No new p-values.',
}


def age_weighted_training(weights, months, train_mask, cutoff, half_life_years):
    """Apply recency only to training, preserving its overall loss scale."""
    if isinstance(half_life_years, bool) or not np.isfinite(half_life_years) or half_life_years <= 0:
        raise ValueError('Half-life must be finite and positive')
    result = np.asarray(weights, dtype=np.float32).copy()
    mask = np.asarray(train_mask, dtype=bool)
    if not mask.any():
        raise ValueError('No training observations')
    ages = pd.Period(cutoff, 'M').ordinal - pd.PeriodIndex(months, freq='M')[mask].asi8
    if (ages <= 0).any():
        raise ValueError('Training publications must precede cutoff')
    values = result[mask].astype(float) * np.exp2(-ages / (12 * half_life_years))
    if not np.isfinite(values).all() or (values <= 0).any():
        raise ValueError('Invalid or underflowed training weights')
    result[mask] = values / values.mean()
    return result


def load_labels(path=SOURCE):
    fields = list(dict.fromkeys(REQUIRED + ['hit', 'scorable', 'basis']))
    parts = []
    for chunk in pd.read_csv(path, usecols=fields, dtype={'record_id': str, 'page_id': str}, chunksize=25000):
        parts.append(chunk[chunk.date.lt('1985-01-01')].copy())
    frame = pd.concat(parts, ignore_index=True)
    frame['date'] = pd.to_datetime(frame.date)
    frame['month'] = frame.date.dt.to_period('M'); frame['year'] = frame.date.dt.year
    if frame.empty or frame.year.lt(1900).any() or frame.year.ge(1985).any():
        raise ValueError('Invalid development coverage')
    if frame[['record_id', 'page_id', 'date']].isna().any().any() or frame.record_id.duplicated().any():
        raise ValueError('Invalid claim addresses')
    if frame.groupby('page_id').month.nunique().gt(1).any():
        raise ValueError('Article spans months')
    if not frame.scorable.isin([True, False]).all():
        raise ValueError('Invalid eligibility flags')
    return frame


def selection(results):
    table = results.pivot(index='candidate', columns='origin', values='brier')
    expected = {INCUMBENT, CONTROL, *[c['id'] for c in CANDIDATES]}
    if set(table.index) != expected or set(table.columns) != set(ORIGINS) or table.isna().any().any():
        raise ValueError('Incomplete comparison')
    rows = []
    for name, values in table.iterrows():
        gain = table.loc[INCUMBENT] - values
        qualifies = (name not in [INCUMBENT, CONTROL] and gain.mean() >= .002
                     and (gain > 0).sum() >= 3 and values.max() <= table.loc[INCUMBENT].max()
                     and values.mean() < table.loc[CONTROL].mean())
        rows.append(dict(candidate=name, mean_brier=values.mean(), worst_brier=values.max(),
                         improvement_over_incumbent=gain.mean(), folds_improved=int((gain > 0).sum()),
                         qualifies=bool(qualifies)))
    ranking = pd.DataFrame(rows).sort_values(['mean_brier', 'worst_brier', 'candidate'])
    qualified = ranking[ranking.qualifies]
    return (qualified.iloc[0].candidate if len(qualified) else INCUMBENT), ranking


def main():
    if OUT.exists():
        raise ValueError('Preserve existing results; create a new study version')
    OUT.mkdir(parents=True)
    (OUT/'specification.json').write_text(json.dumps(SPEC, indent=2)+'\n')
    started = time.monotonic()
    torch.set_num_threads(2); torch.use_deterministic_algorithms(True)
    prior = json.loads((PRIOR/'summary.json').read_text())
    frozen = json.loads(Path('data/scored/proquest/modern_readiness/model_freeze.json').read_text())['files_sha256']
    inputs = {str(SOURCE): prior['source_sha256'], str(PRIOR/'summary.json'): digest(PRIOR/'summary.json')}
    inputs.update(prior['outputs_sha256']); inputs.update(frozen)
    for path, sha in inputs.items():
        if digest(path) != sha: raise ValueError(f'Changed prior input: {path}')
    labels = load_labels()
    results = pd.read_csv(PRIOR/'development_metrics.csv')
    results = results[results.candidate.isin([INCUMBENT, CONTROL])].to_dict('records')
    weight_audit = []
    for origin in ORIGINS:
        original = prepare_fold(labels, origin)
        mask = original['masks']['train']; cutoff = pd.Period(origin, 'M')-60
        assessment = original['frame'].loc[original['masks']['assessment'], 'record_id'].tolist()
        for window, name in [('20', INCUMBENT), ('expanding', CONTROL)]:
            old = pd.read_csv(PRIOR/'development'/origin/window/name/'predictions.csv.gz')
            if old.record_id.tolist() != assessment: raise ValueError('Assessment rows changed')
        for config in CANDIDATES:
            data = dict(original)
            data['weights'] = age_weighted_training(original['weights'], original['frame'].month,
                                                   mask, cutoff, config['half_life_years'])
            path = OUT/'development'/origin/config['id']
            result = run_candidate(data, config, path)
            results.append(dict(origin=origin, **result))
            save_split(data, path/'split_assignments.csv.gz')
            joblib.dump(data['parameters'], path/'preprocessing.joblib')
            audit = data['frame'].loc[mask, ['record_id', 'page_id', 'date']].copy()
            audit['base_weight'] = original['weights'][mask]; audit['fit_weight'] = data['weights'][mask]
            audit.to_csv(path/'training_weights.csv.gz', index=False, compression={'method':'gzip', 'mtime':0})
            mass = audit.groupby('page_id').fit_weight.sum().to_numpy()
            weight_audit.append(dict(origin=origin, candidate=config['id'], training_articles=len(mass),
                                     kish_effective_articles=float(mass.sum()**2/(mass**2).sum())))
            pd.DataFrame(results).to_csv(OUT/'metrics.csv', index=False)
    selected, ranking = selection(pd.DataFrame(results))
    ranking.to_csv(OUT/'ranking.csv', index=False)
    pd.DataFrame(weight_audit).to_csv(OUT/'weight_audit.csv', index=False)
    decision = dict(selected=selected, qualifies=selected != INCUMBENT, status='Exploratory development only; no independent confirmation',
                    new_model_fits=36, later_periods_evaluated=False, new_p_values=False)
    (OUT/'decision.json').write_text(json.dumps(decision, indent=2)+'\n')
    report = '<!doctype html><html lang="en"><meta charset="utf-8"><title>RNN age weighting</title><style>body{font:16px/1.5 system-ui;margin:40px;max-width:1150px}td,th{padding:6px;border-bottom:1px solid #ddd}</style><h1>RNN age weighting</h1>'
    report += '<p>Exploratory follow-up on previously examined development data through 1984. Fixed 10, 20, and 40-year half-lives; loss weights change only during fitting. No later confirmation or test evaluation, and no new p-values.</p>'
    report += f'<p>Decision: {selected}. Passed improvement rule: {decision["qualifies"]}.</p>'
    for title, table in [('Ranking', ranking), ('Every development fold', pd.DataFrame(results)), ('Training weight concentration', pd.DataFrame(weight_audit))]:
        report += f'<h2>{title}</h2>'+table.to_html(index=False, float_format=lambda x:f'{x:.5f}')
    report += '<p>Kish effective article counts describe weight concentration; they are not independent sample sizes or adjustments for temporal dependence.</p></html>'
    (OUT/'report.html').write_text(report)
    for path, sha in inputs.items():
        if digest(path) != sha: raise ValueError(f'Changed input: {path}')
    code_paths = [Path(__file__), Path('src/proquest_rnn_development.py'), Path('src/proquest_rnn_runner.py')]
    summary = dict(decision=decision, seconds=time.monotonic()-started, latest_input_month=str(labels.month.max()),
                   inputs_sha256=inputs, code_sha256={str(p):digest(p) for p in code_paths},
                   versions=dict(python=platform.python_version(), torch=torch.__version__, numpy=np.__version__, pandas=pd.__version__),
                   outputs_sha256={str(p):digest(p) for p in OUT.rglob('*') if p.is_file()})
    (OUT/'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    print(ranking.to_string(index=False), flush=True)
    print(json.dumps(decision), flush=True)


if __name__ == '__main__': main()
