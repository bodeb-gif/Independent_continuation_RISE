from pathlib import Path
import sys
import unittest
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from proquest_direction_diagnostics import binary_costs,evaluate


class DirectionTests(unittest.TestCase):
    def fixture(self):
        return pd.DataFrame(dict(page_id=['a','b','c','d'],year=[1900,1905,1910,1915],topic='general_business',
                                 realized=['worsen','improve','worsen','flat'],predicted_norm=['worsen','worsen','improve','flat'],
                                 hit=[1,0,0,1],fixed_baseline_hit=[0,1,0,0]))
    def test_costs_match_direct_observation_losses(self):
        f=self.fixture();metrics,rows=binary_costs(f)
        for key in ['tp','fp','fn','tn']:self.assertEqual(metrics[key],.25)
        self.assertEqual(metrics['precision'],.5);self.assertEqual(metrics['recall'],.5)
        for row in rows:
            ratio=row['miss_to_false_alarm_cost']
            loss=np.mean([0,1,ratio,0]);self.assertEqual(row['forecast_loss'],loss)
            self.assertEqual(row['never_warn_loss']-loss,row['improvement_vs_never'])
            self.assertEqual(row['always_warn_loss']-loss,row['improvement_vs_always'])
    def test_comparators_leave_correctness_and_source_frame_unchanged(self):
        f=self.fixture();old=f.copy();rows=evaluate(f,dict(topic='general_business'),(5,))
        self.assertEqual(len(rows),3);self.assertTrue(all(r['hit_rate']==.5 for r in rows))
        pd.testing.assert_frame_equal(f,old)


if __name__=='__main__':unittest.main()
