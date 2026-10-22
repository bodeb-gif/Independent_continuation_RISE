"""Design-based correction of claim accuracy using the 300 human-reviewed claims.

Requested by the author on 2026-10-21. Reviewed claims are rescored with their
human categorical labels under the unchanged deterministic outcome rules, then
combined with the machine scores of every frame claim (design-based supervised
learning; prediction-powered inference). Uses no source text, fits no model and
changes no source export or frozen artifact. Historical and modern frames are
estimated separately and never pooled.
"""
import argparse
from collections import Counter
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import platform

import numpy as np
import pandas as pd

import proquest_descriptive as desc
from score_predictions import predicted_norm

BASE = Path('data/scored/proquest')
REVIEW1 = BASE/'source_review_150_v1'
REVIEW2 = BASE/'source_review_additional150_v1'
PILOT = BASE/'source_review_pilot_v1/pack.json'
HISTORICAL_SCORES = BASE/'descriptive/scored_claims.csv.gz'
HISTORICAL_REFERENCE = Path('data/reference/proquest')
MODERN = BASE/'modern_analysis_v1'
MODERN_PACKAGE = Path('data/proquest/modern/20261020')
HISTORICAL_EXPORTS = Path('data/proquest/verified')
AS_OF = '2026-10-20'
# Mirrors proquest_rnn.TOPICS/DIRECTIONS without importing the neural stack.
TOPICS = ['general_business', 'markets', 'prices', 'employment']
DIRECTIONS = ['improve', 'worsen', 'up', 'down', 'flat']
BASELINE = {'general_business': 'improve', 'markets': 'improve', 'prices': 'up', 'employment': 'down'}
ESTIMANDS = {'G': 'share_scorable', 'Y': 'accuracy', 'B': 'baseline_accuracy', 'D': 'gap_vs_fixed_baseline'}
VARIANTS = [
    dict(name='primary', horizon='compatible', unclear='not_genuine', weight='claim', subset='all'),
    dict(name='horizon_human_codes', horizon='human_codes', unclear='not_genuine', weight='claim', subset='all'),
    dict(name='horizon_strict', horizon='strict', unclear='not_genuine', weight='claim', subset='all'),
    dict(name='unclear_machine_labels', horizon='compatible', unclear='machine_labels', weight='claim', subset='all'),
    dict(name='label_concealed_only', horizon='compatible', unclear='not_genuine', weight='claim', subset='concealed'),
    dict(name='article_weighted', horizon='compatible', unclear='not_genuine', weight='article', subset='all'),
]
MODERN_VARIANTS = ['primary', 'horizon_human_codes', 'horizon_strict', 'article_weighted']
SPEC = {
    'date': '2026-10-21',
    'status': ('Exploratory measurement correction requested by the author. Written after field-level '
               'disagreement counts were inspected in session, before any human-label correctness was computed. '
               'No model fitting, source text, threshold search or change to frozen artifacts.'),
    'frames': {
        'historical': ('175,843 machine-scored verified 1900-2010 claims (175,855 scored minus the 12 pilot '
                       'records). The 250 reviewed claims are three sequential simple random samples without '
                       'replacement from this frame, hence one SRS of 250 (inclusion probability 250/175,843).'),
        'modern': ('91,118 retained 2011-2026 verified candidates, including 19 default-kept exceptions, '
                   'stratified by publication year with the recorded inclusion probabilities. Machine scores '
                   'are the saved modern_analysis_v1 outcomes; exceptions and unsupported or immature claims '
                   'have no machine score.'),
        'pooling': 'None. Frames have different designs, eligibility and outcome maturity.',
    },
    'human_outcome': ('Exclude means not a forecast. Include means the same deterministic rules are applied to '
                      'the human topic, direction, price direction, unemployment direction, scope and horizon. '
                      'Historical claims use the descriptive scorer; modern claims add the modern maturity and '
                      'reference-coverage rules as of 2026-10-20.'),
    'horizon_rules': {
        'compatible': ('Primary. Keep the machine horizon actually used when the human code is compatible with '
                       'the machine label under the review convention (6: machine 4-8 months; 12: 9-15; vague: '
                       'machine vague or numeric outside 4-15). Otherwise score the human code, with vague '
                       'receiving the inherited 12-month default.'),
        'human_codes': 'Sensitivity. Human codes only: 6, 12, and vague scored at 12 months.',
        'strict': 'Sensitivity. As compatible, but human-vague horizons are not scorable.',
    },
    'unclear': 'Primary counts the one unclear historical case as not a confirmed forecast; sensitivity scores it with machine labels.',
    'estimands': {
        'share_scorable': 'Share of frame claims that are genuine forecasts scorable under the human reading.',
        'accuracy': 'Correctness among those claims.',
        'baseline_accuracy': 'Target-specific always-improve comparator on the same claims and outcomes.',
        'gap_vs_fixed_baseline': 'Accuracy minus baseline accuracy, in proportion units.',
    },
    'estimators': {
        'machine_only': 'Census of saved machine scores over the frame; no interval because label error is unmodelled.',
        'machine_on_reviewed_sample': 'Machine scores restricted to the reviewed claims; shows sample luck.',
        'human_sample_only': 'Hajek ratio of inverse-probability weighted human scores on reviewed claims.',
        'dsl': ('Design-based correction: machine frame total plus inverse-probability weighted mean of '
                '(human minus machine) on reviewed claims, per total, then ratios.'),
    },
    'uncertainty': ('Stratified linearization variance with finite-population correction; normal 95% intervals. '
                    'They describe sampling of reviewed claims from a fixed frame with human labels taken as true. '
                    'They omit reviewer error, business-cycle generalization and outcome-definition uncertainty.'),
    'weighting': 'Claim weights primary. Article sensitivity weights each claim by 1/(frame claims in its article).',
    'subsets': 'Label-concealed sensitivity drops the 100 historical claims reviewed after machine-label exposure and treats the remaining 150 as an SRS of the same frame.',
    'decision': 'Report all variants and estimators. Do not relabel the frame, refit models or select a variant by results.',
}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, default=str, allow_nan=False)+'\n')


def human_horizon(code, machine_raw, machine_used, rule='compatible'):
    """Months used to score a human horizon code (6, 12 or vague), or None."""
    code = str(code)
    if code not in {'6', '12', 'vague'} or (rule == 'strict' and code == 'vague'):
        return None
    if rule != 'human_codes' and machine_used is not None:
        try:
            months = float(machine_raw)
        except (TypeError, ValueError):
            months = None
        if code == 'vague':
            compatible = str(machine_raw) == 'vague' or (months is not None and not 4 <= months <= 15)
        else:
            low, high = (4, 8) if code == '6' else (9, 15)
            compatible = months is not None and low <= months <= high
        if compatible:
            return int(machine_used)
    return 12 if code == 'vague' else int(code)


def supported(topic, scope, pred, months):
    return scope == 'national' and topic in TOPICS and pred in DIRECTIONS and months is not None


def human_reason(topic, scope, pred, months):
    """First failed eligibility condition under the human reading, if any."""
    if scope != 'national':
        return f'human scope {scope}'
    if topic not in TOPICS:
        return f'human topic {topic}'
    if pred not in DIRECTIONS:
        return 'human direction not scorable'
    if months is None:
        return 'human horizon not scorable'
    return None


class Scorer:
    """Deterministic outcome rules: descriptive (historical) or with modern maturity."""

    def __init__(self, reference, as_of=None):
        desc.REF = Path(reference)
        self.series, self.references = desc.load_reference()
        self.as_of = pd.Timestamp(as_of) if as_of else None
        self.observed = {k: set(v.dropna().index.asi8) for k, v in self.series.items()}
        self.outcome = lru_cache(maxsize=None)(self._outcome)

    def _outcome(self, topic, scope, pred, months, month):
        if self.as_of is None:
            if scope != 'national':
                return None, 'not explicitly US-national'
            if topic not in desc.BANDS:
                return None, 'topic has no defensible benchmark'
            if pred is None:
                return None, 'no scorable direction'
            if months is None:
                return None, 'unusable horizon'
            realized, _, error = desc.realized_outcome(self.series, topic, month, months)
            return realized, error
        # Mirrors proquest_prepare_inputs.attach_outcomes and proquest_rnn_runner.eligible.
        if not supported(topic, scope, pred, months):
            return None, 'unsupported_scope_topic_direction_or_horizon'
        start = pd.Period(month, 'M')
        end = start.ordinal+months
        target = 'recession' if topic == 'general_business' and start < self.series[topic].index.min() else topic
        if end+3 >= self.as_of.to_period('M').ordinal:
            return None, 'unmatured'
        if not set(range(start.ordinal, end+1)).issubset(self.observed[target]):
            return None, 'reference_gap'
        realized, _, error = desc.realized_outcome(self.series, topic, month, months)
        return realized, error

    def score(self, topic, scope, pred, months, date):
        pred = None if pred is None or (isinstance(pred, float) and np.isnan(pred)) else pred
        months = None if months is None or pd.isna(months) else int(months)
        if self.as_of is not None and supported(topic, scope, pred, months) and pd.Timestamp(date) > self.as_of:
            return dict(G=0, Y=0, B=0, reason='future_publication')
        realized, error = self.outcome(topic, scope, pred, months, str(date)[:7])
        if error is not None:
            return dict(G=0, Y=0, B=0, reason=error)
        return dict(G=1, Y=int(pred == realized), B=int(BASELINE[topic] == realized), reason='scored')


def load_reviews():
    """The 300 reviewed claims with machine and human categorical labels."""
    rows = []
    for r in json.loads((REVIEW1/'human_comparison_reconciled.json').read_text())['records']:
        rows.append(dict(audit_id=r['audit_id'], batch=r['batch'], stratum='historical',
                         decision=r['decision'], machine=r['machine'], human=r['human']))
    pack = {r['audit_id']: r for r in json.loads((REVIEW2/'pack.json').read_text())['records']}
    for r in json.loads((REVIEW2/'comparison.json').read_text())['records']:
        stratum = pack[r['audit_id']]['stratum']
        rows.append(dict(audit_id=r['audit_id'], stratum=stratum, decision=r['decision'],
                         batch='additional_historical' if stratum == 'historical' else 'additional_modern',
                         machine=r['original_labels'], human=r['labels']))
    if len(rows) != 300 or len({r['audit_id'] for r in rows}) != 300:
        raise ValueError('Expected 300 distinct reviewed claims')
    for r in rows:
        _, year, line = r['audit_id'].split(':')
        r.update(year=int(year), line=int(line), record_id=f'{year}:{line}',
                 frame='historical' if int(year) <= 2010 else 'modern')
    return rows


def attach_exports(rows):
    """Read each reviewed claim's export row and check its saved machine labels."""
    cache = {}
    for r in rows:
        folder = HISTORICAL_EXPORTS if r['frame'] == 'historical' else MODERN_PACKAGE/'verified'
        path = folder/f"pred_proquest_economy_{r['year']}.export.jsonl"
        if path not in cache:
            cache[path] = path.read_bytes().splitlines()
        row = json.loads(cache[path][r['line']-1])
        for field in ['topic', 'direction', 'price_direction', 'unemployment_direction', 'horizon_months', 'scope']:
            if str(row.get(field)) != str(r['machine'].get(field)):
                raise ValueError(f"Review machine label differs from export: {r['audit_id']} {field}")
        months, _, _ = desc.horizon(row)
        r.update(date=row['date'], page_id=str(row['page_id']), machine_raw_horizon=row.get('horizon_months'),
                 machine_horizon_used=months)
    return {str(p): digest(p) for p in cache}


def historical_frame(scorer):
    scores = pd.read_csv(HISTORICAL_SCORES, dtype={'record_id': str, 'page_id': str, 'horizon_months': str},
                         low_memory=False)
    pilot = {r['audit_id'] for r in json.loads(PILOT.read_text())['records']}
    frame = scores[scores.scorable & ~('verified:'+scores.record_id).isin(pilot)].copy()
    batch1 = {r['audit_id'] for r in json.loads((REVIEW1/'pack.json').read_text())['records']}
    later = sorted(frame.record_id[~('verified:'+frame.record_id).isin(batch1)])
    expected = json.loads((REVIEW2/'manifest.json').read_text())['historical_frame_addresses_sha256']
    if len(frame) != 175843 or hashlib.sha256(('\n'.join(later)+'\n').encode()).hexdigest() != expected:
        raise ValueError('Historical frame does not reproduce the sampling frame')
    checks = [scorer.score(r.topic, r.scope, r.predicted_norm, r.horizon_used, r.date)
              for r in frame.itertuples()]
    frame['G'] = [c['G'] for c in checks]
    frame['Y'] = [c['Y'] for c in checks]
    frame['B'] = [c['B'] for c in checks]
    mismatches = int((frame.G != 1).sum()+(frame.Y != frame.hit).sum()+(frame.B != frame.fixed_baseline_hit).sum())
    if mismatches:
        raise ValueError(f'Historical machine scores not reproduced: {mismatches}')
    frame['stratum'] = 'historical'
    return frame[['record_id', 'page_id', 'stratum', 'G', 'Y', 'B']], dict(frame_n=len(frame), reproduction_mismatches=0,
                                                                         frame_sha256_matches_sampling_manifest=True)


def modern_frame(scorer):
    outcomes = pd.read_csv(MODERN/'claim_outcomes.csv.gz', dtype={'record_id': str, 'page_id': str})
    checks = [scorer.score(r.topic, r.scope, r.predicted_norm, r.horizon_used, r.date)
              for r in outcomes.itertuples()]
    for k in 'GYB':
        outcomes[k] = [c[k] for c in checks]
    saved_hit = outcomes.hit.fillna(0).astype(int)
    mismatches = int((outcomes.G != outcomes.scorable.astype(int)).sum()+(outcomes.Y != saved_hit).sum())
    if mismatches:
        raise ValueError(f'Modern machine scores not reproduced: {mismatches}')
    manifest = json.loads((MODERN_PACKAGE/'manifest.json').read_text())
    exceptions = pd.DataFrame([dict(record_id=f"{e['year']}:{e['source_line']}", page_id=str(e['page_id']),
                                    G=0, Y=0, B=0) for e in manifest['exceptions']])
    frame = pd.concat([outcomes[['record_id', 'page_id', 'G', 'Y', 'B']], exceptions], ignore_index=True)
    frame['stratum'] = frame.record_id.str[:4]
    strata = json.loads((REVIEW2/'manifest.json').read_text())['strata']
    counts = frame.stratum.value_counts().to_dict()
    if any(counts.get(k) != v['frame_n'] for k, v in strata.items() if k != 'historical') or len(frame) != 91118:
        raise ValueError('Modern frame does not reproduce the sampling strata')
    return frame, dict(frame_n=len(frame), machine_scored=int(frame.G.sum()), reproduction_mismatches=0,
                       strata_match_sampling_manifest=True)


def rescore(rows, scorers, variant):
    out = []
    for r in rows:
        scorer = scorers[r['frame']]
        if r['decision'] == 'exclude' or (r['decision'] == 'unclear' and variant['unclear'] == 'not_genuine'):
            result = dict(G=0, Y=0, B=0, reason=f"human_{r['decision']}")
            topic = scope = pred = months = None
        else:
            labels = r['machine'] if r['decision'] == 'unclear' else r['human']
            topic, scope, pred = labels['topic'], labels['scope'], predicted_norm(labels)
            months = (r['machine_horizon_used'] if r['decision'] == 'unclear' else
                      human_horizon(labels['horizon_months'], r['machine_raw_horizon'], r['machine_horizon_used'],
                                    variant['horizon']))
            result = scorer.score(topic, scope, pred, months, r['date'])
            if result['reason'] != 'scored':
                result['reason'] = human_reason(topic, scope, pred, months) or result['reason']
        out.append(dict(audit_id=r['audit_id'], record_id=r['record_id'], frame=r['frame'], stratum=r['stratum'],
                        batch=r['batch'], decision=r['decision'], page_id=r['page_id'], human_topic=topic,
                        human_scope=scope, human_pred=pred, human_horizon_used=months,
                        human_G=result['G'], human_Y=result['Y'], human_B=result['B'], human_reason=result['reason']))
    return pd.DataFrame(out)


def variance(z, strata, sizes):
    total = 0.
    for stratum, values in z.groupby(strata):
        N, n = sizes[stratum]
        if n < 2:
            raise ValueError('Each stratum needs at least two reviewed claims')
        total += N**2*(1-n/N)*values.var(ddof=1)/n
    return total


def design_estimates(frame, reviewed, sizes):
    """Machine census, human-only Hajek and DSL ratio estimates with linearized SEs.

    frame: stratum, a, G, Y, B machine values for every frame claim.
    reviewed: stratum, a, human G/Y/B and machine mG/mY/mB for reviewed claims.
    sizes: stratum -> (frame N, reviewed n).
    """
    frame = frame.assign(D=frame.Y-frame.B)
    reviewed = reviewed.assign(D=reviewed.Y-reviewed.B, mD=reviewed.mY-reviewed.mB)
    d = reviewed.stratum.map(lambda s: sizes[s][0]/sizes[s][1]).astype(float)
    a, strata = reviewed.a, reviewed.stratum
    A = frame.a.sum()
    rows = []

    def add(estimator, x, value, z=None):
        se = float(np.sqrt(variance(z, strata, sizes))) if z is not None else None
        rows.append(dict(estimator=estimator, estimand=ESTIMANDS[x], estimate=float(value), se=se,
                         low=None if se is None else float(value-1.96*se),
                         high=None if se is None else float(value+1.96*se)))

    def ratios(estimator, totals, scores, denominator, scale):
        """totals: estimated totals; scores: per-claim linearization pieces; scale: share denominator."""
        add(estimator, 'G', totals['G']/denominator, None if scores is None else scale(scores))
        for x in 'YBD':
            value = totals[x]/totals['G']
            add(estimator, x, value, None if scores is None else (scores[x]-value*scores['G'])/totals['G'])

    machine = {x: (frame.a*frame[x]).sum() for x in 'GYBD'}
    ratios('machine_only', machine, None, A, None)
    for estimator, prefix in [('machine_on_reviewed_sample', 'm'), ('human_sample_only', '')]:
        scores = {x: a*reviewed[prefix+x] for x in 'GYBD'}
        totals = {x: (d*scores[x]).sum() for x in 'GYBD'}
        size = (d*a).sum()
        share = totals['G']/size
        ratios(estimator, totals, scores, size, lambda s, share=share, size=size: (s['G']-share*a)/size)
    residual = {x: a*(reviewed[x]-reviewed['m'+x]) for x in 'GYBD'}
    totals = {x: machine[x]+(d*residual[x]).sum() for x in 'GYBD'}
    ratios('dsl', totals, residual, A, lambda s: s['G']/A)
    return pd.DataFrame(rows)


def article_weights(frame):
    return 1/frame.groupby('page_id').record_id.transform('size')


def run_variant(variant, frame, rows, scorers, frame_name):
    rescored = rescore([r for r in rows if r['frame'] == frame_name], scorers, variant)
    if variant['subset'] == 'concealed':
        rescored = rescored[rescored.batch != 'original100']
    frame = frame.assign(a=article_weights(frame) if variant['weight'] == 'article' else 1.)
    machine = frame.set_index('record_id')[['a', 'G', 'Y', 'B']]
    reviewed = rescored.join(machine, on='record_id')
    if reviewed[['a', 'G']].isna().any().any():
        raise ValueError('Reviewed claim missing from frame')
    reviewed = reviewed.rename(columns={'G': 'mG', 'Y': 'mY', 'B': 'mB'}).rename(
        columns={'human_G': 'G', 'human_Y': 'Y', 'human_B': 'B'})
    N = frame.stratum.value_counts().to_dict()
    sizes = {s: (N[s], int(n)) for s, n in reviewed.stratum.value_counts().items()}
    table = design_estimates(frame, reviewed, sizes)
    table.insert(0, 'variant', variant['name'])
    table.insert(0, 'frame', frame_name)
    table['n_reviewed'] = len(reviewed)
    table['n_human_scorable'] = int(reviewed.G.sum())
    table['n_frame'] = len(frame)
    return table, reviewed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=BASE/'human_rescore_v1')
    out = parser.parse_args().out
    out.mkdir(parents=True, exist_ok=False)
    write_json(out/'specification.json', SPEC)
    inputs = {str(p): digest(p) for p in [REVIEW1/'human_comparison_reconciled.json', REVIEW1/'pack.json',
                                          REVIEW1/'manifest.json', REVIEW2/'comparison.json', REVIEW2/'pack.json',
                                          REVIEW2/'manifest.json', PILOT, HISTORICAL_SCORES,
                                          MODERN/'claim_outcomes.csv.gz', MODERN_PACKAGE/'manifest.json']}
    if inputs[str(REVIEW2/'pack.json')] != json.loads((REVIEW2/'manifest.json').read_text())['pack_sha256']:
        raise ValueError('Additional review pack changed')
    if inputs[str(REVIEW1/'pack.json')] != json.loads((REVIEW1/'manifest.json').read_text())['pack_sha256']:
        raise ValueError('Original review pack changed')
    for snapshot in json.loads((MODERN/'run_manifest.json').read_text())['reference_snapshots']:
        if digest(snapshot['file']) != snapshot['sha256']:
            raise ValueError(f"Modern reference changed: {snapshot['file']}")
    scorers = {'historical': Scorer(HISTORICAL_REFERENCE), 'modern': Scorer(MODERN/'reference', AS_OF)}
    for scorer in scorers.values():
        inputs.update({r['file']: r['sha256'] for r in scorer.references.values()})
    rows = load_reviews()
    inputs.update(attach_exports(rows))
    frames, checks = {}, {}
    frames['historical'], checks['historical'] = historical_frame(scorers['historical'])
    frames['modern'], checks['modern'] = modern_frame(scorers['modern'])
    tables, primary = [], {}
    for variant in VARIANTS:
        for name in ['historical', 'modern']:
            if name == 'modern' and variant['name'] not in MODERN_VARIANTS:
                continue
            table, reviewed = run_variant(variant, frames[name], rows, scorers, name)
            tables.append(table)
            if variant['name'] == 'primary':
                primary[name] = reviewed
    estimates = pd.concat(tables, ignore_index=True)
    estimates.to_csv(out/'estimates.csv', index=False)
    reviewed = pd.concat(primary.values(), ignore_index=True)
    reviewed.drop(columns=['a']).rename(columns={
        'G': 'human_scorable', 'Y': 'human_correct', 'B': 'human_baseline_correct', 'mG': 'machine_scorable',
        'mY': 'machine_correct', 'mB': 'machine_baseline_correct'}).to_csv(out/'reviewed_rescored.csv', index=False)
    diagnostics = {}
    for name, g in reviewed.groupby('frame'):
        status = pd.Series(np.where(g.G == 1, np.where(g.Y == 1, 'human_correct', 'human_incorrect'), g.human_reason),
                           name='human')
        machine = pd.Series(np.where(g.mG == 1, np.where(g.mY == 1, 'machine_correct', 'machine_incorrect'),
                                     'machine_unscored'), name='machine')
        table = pd.crosstab(machine, status)
        diagnostics[name] = dict(
            human_status={k: int(v) for k, v in Counter(status).items()},
            machine_by_human={m: {h: int(v) for h, v in row.items()} for m, row in table.iterrows()},
            both_scored_correctness_flips=int(((g.G == 1) & (g.mG == 1) & (g.Y != g.mY)).sum()),
            both_scored=int(((g.G == 1) & (g.mG == 1)).sum()))
    key = estimates[(estimates.variant == 'primary')]
    write_json(out/'summary.json', dict(
        specification_sha256=digest(out/'specification.json'), frame_checks=checks, diagnostics=diagnostics,
        primary={f: {e: json.loads(key[(key.frame == f) & (key.estimator == e)].set_index('estimand')
                                   [['estimate', 'low', 'high']].to_json(orient='index'))
                     for e in key.estimator.unique()} for f in key.frame.unique()},
        inputs_sha256=inputs, environment=dict(python=platform.python_version(), pandas=pd.__version__,
                                               numpy=np.__version__),
        outputs=['specification.json', 'estimates.csv', 'reviewed_rescored.csv', 'summary.json'],
        no_source_text=True, no_model_fitting=True, frozen_artifacts_unchanged=True))
    print(key[['frame', 'estimator', 'estimand', 'estimate', 'low', 'high']].round(4).to_string(index=False))


if __name__ == '__main__':
    main()
