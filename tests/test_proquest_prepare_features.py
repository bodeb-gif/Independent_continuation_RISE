from pathlib import Path
import sys
import unittest
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from proquest_prepare_features import build


class FeaturePreparationTests(unittest.TestCase):
    def fixture(self):
        rows=[]
        for month in pd.period_range('1998-01','2001-12',freq='M'):
            for paper in ['a','b']:
                for j in range(3):rows.append(dict(page_id=f'{month}:{paper}:{j}',month=month,scope='national',topic='general_business',paper=paper,predicted_norm='improve' if j else 'worsen'))
        votes=pd.DataFrame(dict(congress=106,chamber='House',rollnumber=range(36),date=pd.date_range('1998-01-01',periods=36,freq='MS'),political_gap=.4))
        return pd.DataFrame(rows),votes
    def test_future_claims_votes_and_outcomes_do_not_change_past_features(self):
        f,v=self.fixture();a=build(f,v,'2000-01','2000-06')
        f.loc[f.month>=pd.Period('2000-06'),'predicted_norm']='flat';f['hit']=999;f['verify_reason']='hindsight'
        v.loc[v.date>=pd.Timestamp('2000-05-01'),'political_gap']=.99
        b=build(f,v,'2000-01','2000-06');pd.testing.assert_frame_equal(a,b)
        self.assertAlmostEqual(a.forecast_polarization.iloc[0],8/9)
    def test_duplicate_rollcalls_are_rejected(self):
        f,v=self.fixture()
        with self.assertRaisesRegex(ValueError,'rollcall'):build(f,pd.concat([v,v.iloc[:1]]),'2000-01','2000-06')


if __name__=='__main__':unittest.main()
