from pathlib import Path
import sys
import unittest
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from proquest_macro_claim_inputs import add_arm, feature_matrix, vintage_hits, ARMS
from proquest_vintages import VintageSeries, CORE_FEATURES


class MacroClaimTests(unittest.TestCase):
    def test_vintage_truth_and_strict_maturity(self):
        dates = pd.period_range('1980-01', '1981-01', freq='M')
        matrix = pd.DataFrame({'IPT81M1': np.linspace(100, 110, len(dates)),
                               'IPT81M2': np.linspace(100, 90, len(dates))}, index=dates)
        f = pd.DataFrame(dict(record_id=['a', 'b'], month=pd.PeriodIndex(['1980-01', '1980-04'], freq='M'),
                              horizon_used=[6, 6], predicted_norm=['improve', 'improve']))
        values = vintage_hits(f, VintageSeries('IPT', matrix), '1981-01', 'general_business')
        self.assertTrue(values.vintage_hit.isna().all())  # January vintage is not public at January start.
        values = vintage_hits(f, VintageSeries('IPT', matrix), '1981-02', 'general_business')
        self.assertEqual(values.vintage_hit.tolist(), [1, 1])
        matrix['IPT81M2'] = 9999
        repeated = vintage_hits(f, VintageSeries('IPT', matrix), '1981-02', 'general_business')
        pd.testing.assert_frame_equal(values, repeated)
        f.loc[1, 'horizon_used'] = 7  # Endpoint November + 3 months == February: not mature strictly before.
        self.assertTrue(pd.isna(vintage_hits(f, VintageSeries('IPT', matrix), '1981-02', 'general_business').vintage_hit.iloc[1]))

    def test_feature_alignment_and_train_only_scaling(self):
        f = pd.DataFrame(dict(topic=['general_business', 'employment', 'employment'], predicted_norm=['worsen', 'down', 'flat']))
        m = pd.DataFrame({name: [1., 2., 3.] for name in CORE_FEATURES})
        x = feature_matrix(f, m, ARMS['both'])
        self.assertEqual(x[0, ARMS['both'].index('production_alignment')], -1)
        self.assertEqual(x[1, ARMS['both'].index('unemployment_alignment')], -2)
        self.assertEqual(x[2, ARMS['both'].index('unemployment_alignment')], 0)
        data = {'frame': f, 'macro': m, 'claim': np.zeros((3, 2), dtype=np.float32),
                'masks': {'train': np.array([True, True, False])}}
        a, sa = add_arm(data, 'both')
        changed = dict(data, macro=m.copy()); changed['macro'].loc[2] = 9999
        b, sb = add_arm(changed, 'both')
        np.testing.assert_array_equal(sa.mean_, sb.mean_)
        np.testing.assert_array_equal(a['claim'][:2], b['claim'][:2])
        self.assertEqual(data['claim'].shape[1], 2)


if __name__ == '__main__':
    unittest.main()
