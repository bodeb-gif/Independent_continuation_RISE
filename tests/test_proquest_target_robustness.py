"""Pairing, population-specific weights, block sensitivity, and scope checks."""
from pathlib import Path
import sys
import tempfile
import unittest
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from proquest_target_robustness import weighted,block_summary,cohort,load_scored


def fixture():
    return pd.DataFrame(dict(year=[1900,1900,1905,1910,1915],page_id=['a','a','b','c','d'],
                             month=['1900-01','1900-01','1905-01','1910-01','1915-01'],
                             hit=[1,0,1,0,1],fixed_baseline_hit=[0,1,0,1,0],
                             basis=['NBER proxy','NBER proxy','INDPRO','INDPRO','INDPRO'],
                             horizon_basis=['stated','default','stated','default','stated']))


class TargetTests(unittest.TestCase):
    def test_article_weights_and_paired_gap(self):
        data=weighted(fixture(),'article')
        np.testing.assert_array_equal(data.mass,[.5,.5,1,1,1])
        result,omissions=block_summary(data,5,reps=100)
        self.assertAlmostEqual(result['gap_vs_fixed'],.25)
        self.assertEqual(len(omissions),4)
        # Equal predictors have exactly zero paired uncertainty regardless of accuracy.
        f=fixture();f['fixed_baseline_hit']=f.hit
        result,_=block_summary(weighted(f,'article'),5,reps=100)
        self.assertEqual(result['low'],0);self.assertEqual(result['high'],0)

    def test_cluster_duplication_does_not_change_article_estimate(self):
        f=fixture();expanded=pd.concat([f,f[f.page_id.eq('a')]],ignore_index=True)
        first,_=block_summary(weighted(f,'article'),5,reps=100)
        second,_=block_summary(weighted(expanded,'article'),5,reps=100)
        self.assertEqual(first,second)

    def test_recomputed_cohort_weights_and_insufficient_blocks(self):
        sub=cohort(fixture(),'machine_stated_non_NBER')
        self.assertEqual(sub.page_id.tolist(),['b','d'])
        result,_=block_summary(weighted(sub,'article'),5,reps=100)
        self.assertTrue(np.isnan(result['low']));self.assertEqual(result['valid_draws'],0)
        stated=cohort(fixture(),'machine_stated')
        self.assertEqual(weighted(stated,'article').mass.iloc[0],1.)

    def test_scope_and_source_address_validation(self):
        f=fixture();f['source_set']='verified';f['record_id']=[f'r{i}' for i in range(len(f))]
        f['date']=f.month+'-01';f['topic']='general_business';f['horizon_used']=12;f['scorable']=True
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'scores.csv';f.to_csv(p,index=False);self.assertEqual(len(load_scored(p)),5)
            f.loc[0,'year']=2011;f.to_csv(p,index=False)
            with self.assertRaisesRegex(ValueError,'scope'):load_scored(p)
            f.loc[0,'year']=1900;f.loc[0,'record_id']='r1';f.to_csv(p,index=False)
            with self.assertRaisesRegex(ValueError,'addresses'):load_scored(p)


if __name__=='__main__':unittest.main()
