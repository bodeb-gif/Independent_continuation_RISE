"""Known-answer checks for descriptive matching and historical consensus."""
from pathlib import Path
import sys
import unittest

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from proquest_followups import (assign_events, confusion_metrics, historical_consensus,
                               matched_pair, recession_starts, speaker_key)


class FollowupChecks(unittest.TestCase):
    def test_warning_denominators_and_flat_misses(self):
        rows = [('worsen', 'worsen'), ('worsen', 'flat'), ('flat', 'worsen'), ('improve', 'improve')]
        frame = pd.DataFrame(rows, columns=['predicted_norm', 'realized'])
        frame['page_id'] = ['a', 'b', 'c', 'd']
        result = confusion_metrics(frame)
        for key in ['true_warnings', 'false_alarms', 'missed_declines', 'true_nonwarnings']:
            self.assertEqual(result[key], 1)
        for key in ['warning_precision', 'decline_recall', 'miss_rate', 'false_alarm_rate']:
            self.assertEqual(result[key], .5)
        self.assertEqual(result['false_alarms_followed_by_flat'], 1)
        self.assertEqual(result['optimistic_among_actual_declines'], 0)

    def test_onset_and_single_event_assignment(self):
        rec = pd.Series([0, 1, 1, 0], index=pd.period_range('2000-01', periods=4, freq='M'))
        self.assertEqual(list(recession_starts(rec)), [pd.Period('2000-02', 'M')])
        starts = pd.PeriodIndex(['2000-02', '2000-04'], freq='M')
        frame = pd.DataFrame({'month': pd.PeriodIndex(['2000-03', '1990-01'], freq='M')})
        assigned = assign_events(frame, starts)
        self.assertEqual(len(assigned), 1)
        self.assertEqual(assigned.iloc[0].onset, '2000-02')  # Equal-distance tie: earlier onset.
        self.assertEqual(assigned.iloc[0].relative_month, 1)

    def test_consensus_excludes_self_same_day_future_and_outcomes(self):
        rows = []
        def add(date, paper, direction, number):
            rows.extend([{'date': pd.Timestamp(date), 'paper': paper, 'predicted_norm': direction,
                          'topic': 'general_business', 'basis': 'INDPRO', 'horizon_basis': 'stated',
                          'horizon_bucket': '1–6', 'hit': 0, 'realized': 'worsen'} for _ in range(number)])
        add('2000-01-01', 'B', 'improve', 10)
        add('2000-01-01', 'C', 'improve', 10)
        add('2000-01-01', 'A', 'worsen', 200)
        target = len(rows)
        add('2000-02-01', 'A', 'worsen', 1)
        add('2000-02-01', 'B', 'worsen', 300)
        add('2000-02-02', 'C', 'worsen', 300)
        frame = pd.DataFrame(rows)
        result = historical_consensus(frame)
        self.assertEqual(result.loc[target, 'consensus'], 'Contrarian')
        self.assertEqual(result.loc[target, 'prior_peer_claims'], 20)
        self.assertEqual(result.loc[target, 'prior_peer_papers'], 2)
        frame['hit'] = 1; frame['realized'] = 'improve'
        again = historical_consensus(frame)
        pd.testing.assert_series_equal(result.consensus, again.consensus)
        single_paper = historical_consensus(frame[frame.paper != 'C'])
        self.assertEqual(single_paper.loc[target, 'consensus'], 'Insufficient peers')

    def test_consensus_ninety_day_boundary(self):
        target_date = pd.Timestamp('2000-04-01')
        rows = []
        for offset in [90, 91]:
            for paper in ['B', 'C']:
                rows.append({'date': target_date - pd.Timedelta(days=offset), 'paper': paper,
                             'predicted_norm': 'improve' if offset == 90 else 'worsen'})
        rows.append({'date': target_date, 'paper': 'A', 'predicted_norm': 'improve'})
        frame = pd.DataFrame(rows).assign(topic='markets', basis='Shiller', horizon_basis='stated', horizon_bucket='1–6')
        result = historical_consensus(frame, minimum=2)
        self.assertEqual(result.iloc[-1].prior_peer_claims, 2)
        self.assertEqual(result.iloc[-1].consensus, 'Agrees with prior consensus')

    def test_shared_weights_correct_composition_reversal(self):
        rows = []
        for year, group, number, hits in [(2000, 'A', 100, 80), (2000, 'B', 10, 9),
                                          (2001, 'A', 10, 2), (2001, 'B', 100, 30)]:
            rows.extend([{'year': year, 'group': group, 'hit': int(i < hits), 'fixed_baseline_hit': 1}
                         for i in range(number)])
        frame = pd.DataFrame(rows)
        raw = frame.groupby('group').hit.mean()
        self.assertGreater(raw['A'], raw['B'])
        result, cells = matched_pair(frame, 'group', 'A', 'B', ['year'])
        self.assertEqual(len(cells), 2)
        self.assertAlmostEqual(result['left_matched_hit_rate'], .5)
        self.assertAlmostEqual(result['right_matched_hit_rate'], .6)
        self.assertAlmostEqual(result['matched_gap'], -.1)
        self.assertEqual(result['baseline_gap'], 0)

    def test_conservative_speaker_names(self):
        self.assertEqual(speaker_key(' Jane  Q. DOE '), 'jane q doe')
        self.assertNotEqual(speaker_key('Jane Doe'), speaker_key('Jane Q. Doe'))
        for value in [None, '', 'N.A.', 'Unknown', 'nan']:
            self.assertIsNone(speaker_key(value))


if __name__ == '__main__':
    unittest.main()
