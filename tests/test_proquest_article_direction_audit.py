from pathlib import Path
import sys
import unittest
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from proquest_article_direction_audit import summarize


class ArticleDirectionTests(unittest.TestCase):
    def test_separate_horizons_do_not_create_direction_conflict(self):
        f=pd.DataFrame(dict(record_id=['a','b','c'],page_id='article',date='2000-01-01',topic='markets',basis='Shiller S&P',horizon_used=[6,12,6],predicted_norm=['improve','worsen','improve'],voice='expert'))
        g,t=summarize(f);self.assertEqual(len(g),2);self.assertEqual(t.multiple_direction_groups.iloc[0],0)
        f.loc[2,'predicted_norm']='worsen';g,t=summarize(f)
        self.assertEqual(t.multiple_direction_groups.iloc[0],1);self.assertEqual(g.n_claims.sum(),3)


if __name__=='__main__':unittest.main()
