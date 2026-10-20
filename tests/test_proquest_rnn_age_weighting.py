"""Training-only decay, temporal scope, and fixed selection safeguards."""
import sys
from pathlib import Path
import tempfile
import unittest
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from proquest_rnn_age_weighting import age_weighted_training, load_labels, selection, CANDIDATES, ORIGINS, INCUMBENT, CONTROL
from test_proquest_rnn_development import fixture


class AgeWeightingTests(unittest.TestCase):
    def test_half_life_article_mass_and_untouched_evaluation(self):
        months=pd.PeriodIndex(['1950-01','1960-01','1960-01','1971-01'],freq='M')
        weights=np.array([1., .5, .5, .75],dtype=np.float32)
        result=age_weighted_training(weights,months,[True,True,True,False],'1970-01',10)
        self.assertAlmostEqual(float(result[1:3].sum()/result[0]),2.)
        self.assertAlmostEqual(float(result[:3].mean()),1.)
        self.assertEqual(result[3],weights[3])
        np.testing.assert_array_equal(weights,[1.,.5,.5,.75])
        for bad in [0,-1,float('nan'),float('inf'),True]:
            with self.assertRaises(ValueError):age_weighted_training(weights,months,[True,True,True,False],'1970-01',bad)

    def test_later_outcomes_cannot_enter_study(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'labels.csv'; f=fixture();f.to_csv(p,index=False);a=load_labels(p)
            f.loc[f.year>=1985,'hit']=999;f.loc[f.year>=1985,'paper']='LATER';f.to_csv(p,index=False)
            pd.testing.assert_frame_equal(a,load_labels(p))
            self.assertEqual(a.year.max(),1984)

    def test_fixed_rule_rejects_inconsistent_gain(self):
        rows=[]
        for name in [INCUMBENT,CONTROL,*[c['id'] for c in CANDIDATES]]:
            for i,origin in enumerate(ORIGINS):
                value=.2 if name==INCUMBENT else .21
                if name=='gru8_age_10':value=[.01,.01,.22,.22][i]
                if name=='gru8_age_20':value=[.19,.19,.19,.2][i]
                rows.append(dict(candidate=name,origin=origin,brier=value))
        selected,ranking=selection(pd.DataFrame(rows))
        self.assertEqual(selected,'gru8_age_20')
        self.assertFalse(ranking.set_index('candidate').loc['gru8_age_10','qualifies'])
        with self.assertRaises(ValueError):selection(pd.DataFrame(rows[:-1]))


if __name__=='__main__':unittest.main()
