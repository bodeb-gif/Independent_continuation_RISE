from pathlib import Path
import sys
import unittest
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from proquest_human_rescore import DIRECTIONS, TOPICS, design_estimates, human_horizon, human_reason


def synthetic(n_frame=400, n_reviewed=80, seed=3):
    rng = np.random.default_rng(seed)
    frame = pd.DataFrame(dict(record_id=[str(i) for i in range(n_frame)], stratum='s', a=1.,
                              G=1, Y=rng.integers(0, 2, n_frame), B=rng.integers(0, 2, n_frame)))
    reviewed = frame.sample(n_reviewed, random_state=seed).rename(columns={'G': 'mG', 'Y': 'mY', 'B': 'mB'})
    return frame, reviewed


def pick(table, estimator, estimand):
    return table[(table.estimator == estimator) & (table.estimand == estimand)].iloc[0]


class HumanRescoreTests(unittest.TestCase):
    def test_horizon_rule_keeps_compatible_machine_months(self):
        self.assertEqual(human_horizon('6', '5', 5), 5)
        self.assertEqual(human_horizon('6', '3', 3), 6)
        self.assertEqual(human_horizon('12', '10', 10), 10)
        self.assertEqual(human_horizon('vague', '3', 3), 3)
        self.assertEqual(human_horizon('vague', 'vague', 24), 24)
        self.assertEqual(human_horizon('vague', '12', 12), 12)
        self.assertEqual(human_horizon('vague', '36', None), 12)
        self.assertEqual(human_horizon('6', '5', 5, 'human_codes'), 6)
        self.assertIsNone(human_horizon('vague', 'vague', 6, 'strict'))
        self.assertEqual(human_horizon('12', '10', 10, 'strict'), 10)
        self.assertIsNone(human_horizon(None, '6', 6))

    def test_reason_order_and_constants(self):
        self.assertEqual(human_reason('prices', 'foreign', 'up', 6), 'human scope foreign')
        self.assertEqual(human_reason('other', 'national', 'up', 6), 'human topic other')
        self.assertEqual(human_reason('prices', 'national', None, 6), 'human direction not scorable')
        self.assertIsNone(human_reason('prices', 'national', 'up', 6))
        try:
            import proquest_rnn
        except ImportError:
            self.skipTest('neural stack unavailable')
        self.assertEqual(TOPICS, proquest_rnn.TOPICS)
        self.assertEqual(DIRECTIONS, proquest_rnn.DIRECTIONS)

    def test_agreeing_labels_return_machine_census_without_error(self):
        frame, reviewed = synthetic()
        reviewed = reviewed.assign(G=reviewed.mG, Y=reviewed.mY, B=reviewed.mB)
        table = design_estimates(frame, reviewed, {'s': (len(frame), len(reviewed))})
        for estimand in ['accuracy', 'baseline_accuracy', 'gap_vs_fixed_baseline', 'share_scorable']:
            self.assertAlmostEqual(pick(table, 'dsl', estimand).estimate, pick(table, 'machine_only', estimand).estimate)
            self.assertAlmostEqual(pick(table, 'dsl', estimand).se, 0)

    def test_complete_review_returns_human_census(self):
        frame, _ = synthetic()
        reviewed = frame.rename(columns={'G': 'mG', 'Y': 'mY', 'B': 'mB'})
        rng = np.random.default_rng(9)
        reviewed = reviewed.assign(G=rng.integers(0, 2, len(frame)), Y=0, B=0)
        reviewed['Y'] = reviewed.G*rng.integers(0, 2, len(frame))
        reviewed['B'] = reviewed.G*rng.integers(0, 2, len(frame))
        table = design_estimates(frame, reviewed, {'s': (len(frame), len(frame))})
        truth = reviewed.Y.sum()/reviewed.G.sum()
        self.assertAlmostEqual(pick(table, 'dsl', 'accuracy').estimate, truth)
        self.assertAlmostEqual(pick(table, 'human_sample_only', 'accuracy').estimate, truth)
        self.assertAlmostEqual(pick(table, 'dsl', 'accuracy').se, 0)

    def test_srs_share_variance_matches_binomial_formula(self):
        frame, reviewed = synthetic(n_frame=1000, n_reviewed=50)
        rng = np.random.default_rng(4)
        reviewed = reviewed.assign(G=rng.integers(0, 2, len(reviewed)), Y=0, B=0)
        table = design_estimates(frame, reviewed, {'s': (1000, 50)})
        p = reviewed.G.mean()
        expected = np.sqrt((1-50/1000)*p*(1-p)/49)
        self.assertAlmostEqual(pick(table, 'human_sample_only', 'share_scorable').se, expected)


if __name__ == '__main__':
    unittest.main()
