from pathlib import Path
import sys
import unittest
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from proquest_alternative_targets import business_alignment, quarter_mean, sign_change


class AlternativeTargetTests(unittest.TestCase):
    def test_alignment_never_interpolates_quarters(self):
        self.assertTrue(business_alignment(pd.Period('2000-03', 'M'), 6))
        self.assertFalse(business_alignment(pd.Period('2000-02', 'M'), 6))
        self.assertFalse(business_alignment(pd.Period('2000-03', 'M'), 4))
        s = pd.Series([100., 110., 120., 130., 140.], index=pd.period_range('2000-01', periods=5, freq='M'))
        q = quarter_mean(s)
        self.assertEqual(q.iloc[0], 110)
        self.assertTrue(np.isnan(q.iloc[1]))
        self.assertIsNone(sign_change(q, q.index[0], q.index[1]))

    def test_unemployment_polarity_and_zero_change(self):
        months = pd.period_range('2000-01', periods=3, freq='M')
        jobs = pd.Series([100., 102., 102.], index=months)
        unemployment = pd.Series([6., 5., 5.], index=months)
        self.assertEqual(sign_change(jobs, months[0], months[1]), 'improve')
        self.assertEqual(sign_change(unemployment, months[0], months[1], reverse=True), 'improve')
        self.assertEqual(sign_change(jobs, months[1], months[2]), 'flat')


if __name__ == '__main__':
    unittest.main()
