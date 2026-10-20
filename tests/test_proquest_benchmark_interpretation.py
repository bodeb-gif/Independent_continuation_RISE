from pathlib import Path
import sys
import unittest
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from proquest_benchmark_interpretation import bands_for, relabel
from proquest_descriptive import BANDS, realized_outcome


class InterpretationTests(unittest.TestCase):
    def test_anchor_units_and_boundary(self):
        self.assertEqual(bands_for('duration_scaled', 12), BANDS)
        self.assertEqual(bands_for('duration_scaled', 6)['employment'], .25)
        series = {'employment': pd.Series([5., 5.25, 5.5], index=pd.PeriodIndex(['2000-01', '2000-07', '2001-01'], freq='M'))}
        self.assertEqual(realized_outcome(series, 'employment', '2000-01', 6, bands_for('duration_scaled', 6))[0], 'flat')
        self.assertEqual(realized_outcome(series, 'employment', '2000-01', 6, bands_for('sign_only', 6))[0], 'up')
        with self.assertRaises(ValueError):
            bands_for('duration_scaled', 6.5)

    def test_matching_preserves_repeated_claims_and_rejects_changed_truth(self):
        f = pd.DataFrame(dict(source_set=['verified']*3, record_id=['a', 'b', 'c'],
                              topic=['employment']*3, month=['2000-01']*3, horizon_used=[6, 6, 12],
                              basis=['UNRATE']*3, realized=['flat', 'flat', 'up'],
                              predicted_norm=['up', 'flat', 'up'], hit=[0, 1, 1]))
        original = f.copy()
        series = {'employment': pd.Series([5., 5.4, 6.], index=pd.PeriodIndex(['2000-01', '2000-07', '2001-01'], freq='M'))}
        result = relabel(f, series)
        self.assertEqual(result.record_id.tolist(), ['a', 'b', 'c'])
        self.assertEqual(result.duration_scaled.tolist(), ['up', 'up', 'up'])
        np.testing.assert_array_equal(result.predicted_norm.eq(result.duration_scaled), [True, False, True])
        pd.testing.assert_frame_equal(f, original)
        f.loc[0, 'realized'] = 'up'
        with self.assertRaisesRegex(ValueError, 'did not reproduce'):
            relabel(f, series)


if __name__ == '__main__':
    unittest.main()
