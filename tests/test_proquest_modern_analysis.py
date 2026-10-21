import sys
from pathlib import Path
import unittest
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from proquest_modern_analysis import paired_blocks
from proquest_downturn import make_targets,training_rows,choose_historical,fit_probability
from proquest_panel import build_panels,forecast_features
from proquest_polarization import political_months,forecast_months

class ModernTests(unittest.TestCase):
    def test_onset_is_not_existing_recession_and_missing_month_is_not_negative(self):
        months=pd.period_range('1999-12','2001-01',freq='M')
        rec=pd.Series(0.,index=months);rec.iloc[0:3]=1
        prod=pd.Series(100.,index=months)
        t=make_targets([pd.Period('2000-01','M')],prod,rec,'recession_onset_12m')
        self.assertEqual(t.target.iloc[0],0)
        rec.loc['2000-08']=1
        t=make_targets([pd.Period('2000-01','M')],prod,rec,'recession_onset_12m')
        self.assertEqual(t.target.iloc[0],1);self.assertEqual(t.onset_months.iloc[0],'2000-08')
        rec.loc['2000-05']=np.nan
        self.assertTrue(make_targets([pd.Period('2000-01','M')],prod,rec,'recession_onset_12m').target.isna().all())

    def test_production_endpoints_and_strict_training_maturity(self):
        months=pd.period_range('1999-12','2000-12',freq='M');s=pd.Series(100.,index=months);s.iloc[-1]=99
        t=make_targets([pd.Period('2000-01','M')],s,s*0,'production_decline_12m')
        self.assertEqual(t.target.iloc[0],1);self.assertEqual(t.target_end.iloc[0],pd.Period('2000-12','M'))
        self.assertTrue(training_rows(t,pd.Period('2001-03','M')).empty)
        self.assertEqual(len(training_rows(t,pd.Period('2001-04','M'))),1)
        self.assertEqual(make_targets([pd.Period('2000-01','M')],s,s*0,'production_decline_gt2pct_12m').target.iloc[0],0)

    def test_selection_refuses_modern_results(self):
        with self.assertRaisesRegex(ValueError,'Modern'):
            choose_historical(pd.DataFrame({'origin':pd.PeriodIndex(['2011-01'],freq='M')}))

    def test_fitting_ignores_evaluation_targets_and_later_rows(self):
        train=pd.DataFrame({'target':[0,1]*12,'signal':np.arange(24,dtype=float)})
        test=pd.DataFrame({'signal':[3.,np.nan],'target':[0,1]})
        p,_=fit_probability(train,test,('signal',))
        test['target']=[1,0];test2=pd.concat([test,pd.DataFrame({'signal':[9999.],'target':[1]})],ignore_index=True)
        q,_=fit_probability(train,test2,('signal',));np.testing.assert_array_equal(p,q[:2])

    def test_future_prints_and_votes_cannot_change_earlier_features(self):
        rows=[]
        for month in pd.period_range('1999-01','2000-12',freq='M'):
            for paper in ['A','B']:
                for i in range(3):rows.append(dict(month=month,paper=paper,topic='general_business',page_id=f'{month}-{paper}-{i}',sign='positive' if i else 'negative'))
        claims=pd.DataFrame(rows);calendar=pd.period_range('1999-01','2000-12',freq='M');origins=pd.period_range('2000-01','2000-06',freq='M')
        def build(c):
            _,p,n=build_panels(c,calendar);f=forecast_features(p,n,origins)
            return f,forecast_months(n,f,origins)
        a,b=build(claims);claims.loc[claims.month>=pd.Period('2000-06','M'),'sign']='negative';c,d=build(claims)
        pd.testing.assert_frame_equal(a,c);pd.testing.assert_frame_equal(b,d)
        votes=pd.DataFrame({'date':pd.date_range('1999-01-01','2000-12-01',freq='7D'),'political_gap':.4})
        before=political_months(votes,origins);votes.loc[votes.date>='2000-06-01','political_gap']=.99
        pd.testing.assert_frame_equal(before,political_months(votes,origins))

    def test_paired_blocks_identical_predictions_have_zero_difference(self):
        y=np.array([0,1,0,1]);p=np.array([.2,.8,.3,.7]);r=paired_blocks(y,p,p,np.array([2011,2012,2016,2021]))
        self.assertEqual((r['delta_brier_a_minus_b'],r['low'],r['high']),(0,0,0));self.assertEqual(r['n_blocks'],3)

if __name__=='__main__':unittest.main()
