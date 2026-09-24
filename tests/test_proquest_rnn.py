"""Known-answer temporal leakage, weighting, metric and neural checks."""
from pathlib import Path
import sys
import unittest

import numpy as np
import pandas as pd
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from proquest_rnn import (ClaimGRU, article_weights, block_comparison,
                          chronological_splits, metrics, monthly_context, sequence_indices)


class RNNChecks(unittest.TestCase):
    def test_current_and_future_months_cannot_enter_sequence(self):
        frame = pd.DataFrame({'month': pd.PeriodIndex(['2000-01', '2000-02', '2000-03'], freq='M'),
                              'scope': 'national', 'topic': 'general_business',
                              'predicted_norm': ['improve', 'worsen', 'worsen'],
                              'scorable': [True, True, False], 'hit': [0, 1, np.nan]})
        context = monthly_context(frame)
        indexes = sequence_indices(pd.PeriodIndex(['2000-02'], freq='M'), context.index)
        self.assertEqual(context.index[indexes[0, -1]], pd.Period('2000-01', 'M'))
        self.assertEqual(context.iloc[indexes[0, -1]]['general_business:improve_share'], 1)
        original = context.to_numpy()[indexes]
        frame.loc[1:, 'predicted_norm'] = 'improve'
        altered = monthly_context(frame).to_numpy()[indexes]
        np.testing.assert_equal(original, altered)
        frame['scorable'] = False; frame['hit'] = 1
        np.testing.assert_equal(altered, monthly_context(frame).to_numpy()[indexes])

    def test_empty_months_and_foreign_claims(self):
        frame = pd.DataFrame({'month': pd.PeriodIndex(['2000-01', '2000-03'], freq='M'),
                              'scope': ['national', 'global'], 'topic': 'markets',
                              'predicted_norm': ['improve', 'worsen']})
        context = monthly_context(frame)
        self.assertEqual(context.loc['2000-02', 'markets:observed'], 0)
        self.assertEqual(context.loc['2000-03', 'markets:log_claim_count'], 0)
        self.assertEqual(context.loc['2000-01', 'markets:log_claim_count'], np.log(2))

    def test_unresolved_labels_are_purged_before_boundaries(self):
        dates = ['1984-01', '1984-01', '1984-12', '1985-01', '1985-01',
                 '1994-12', '1995-01', '1995-01']
        frame = pd.DataFrame({'month': pd.PeriodIndex(dates, freq='M'), 'horizon_used': 6,
                              'hit': [0, 1, 1, 0, 1, 0, 0, 1], 'page_id': list('abcdefgh')})
        masks, available, excluded = chronological_splits(frame)
        self.assertEqual(np.flatnonzero(masks['train']).tolist(), [0, 1])
        self.assertEqual(np.flatnonzero(masks['validation']).tolist(), [3, 4])
        self.assertEqual(np.flatnonzero(masks['test']).tolist(), [6, 7])
        self.assertEqual(excluded, 2)
        self.assertTrue((available[masks['train']] < pd.Period('1985-01', 'M')).all())
        frame.loc[6, 'page_id'] = 'a'
        with self.assertRaisesRegex(ValueError, 'article crosses'):
            chronological_splits(frame)

    def test_each_article_gets_equal_total_weight(self):
        frame = pd.DataFrame({'page_id': ['a', 'a', 'a', 'b']})
        weights = article_weights(frame)
        self.assertEqual(weights[:3].sum(), weights[3])
        self.assertEqual(weights.mean(), 1)

    def test_constant_baseline_and_identical_block_models(self):
        y = np.array([0, 0, 0, 1])
        result = metrics(y, np.full(4, .25))
        self.assertEqual(result['average_precision'], .25)
        self.assertEqual(result['brier_score'], .1875)
        frame = pd.DataFrame({'year': [1995, 2000, 2005, 2010], 'hit': y, 'page_id': list('abcd')})
        probabilities = np.array([.2, .3, .1, .7])
        comparison = block_comparison(frame, probabilities, probabilities, draws=30)
        self.assertEqual(comparison['average_precision_gap'], 0)
        self.assertEqual(comparison['block_interval_low'], 0)
        self.assertEqual(comparison['block_interval_high'], 0)

    def test_gradients_reach_recurrent_weights(self):
        torch.manual_seed(31)
        model = ClaimGRU(context_size=3, claim_size=4, hidden=5)
        logits = model(torch.randn(6, 12, 3), torch.randn(6, 4))
        self.assertEqual(tuple(logits.shape), (6,))
        loss = torch.nn.functional.binary_cross_entropy_with_logits(logits, torch.tensor([0., 1., 0., 1., 0., 1.]))
        loss.backward()
        gradient = model.gru.weight_ih_l0.grad
        self.assertTrue(torch.isfinite(gradient).all())
        self.assertGreater(gradient.abs().sum().item(), 0)
        model.eval()
        replica = ClaimGRU(3, 4, 5).eval(); replica.load_state_dict(model.state_dict())
        context, claim = torch.randn(2, 12, 3), torch.randn(2, 4)
        torch.testing.assert_close(model(context, claim), replica(context, claim))


if __name__ == '__main__':
    unittest.main()
