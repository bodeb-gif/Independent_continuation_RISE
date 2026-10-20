import json
from pathlib import Path
import sys
import tempfile
import unittest
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from proquest_prepare_inputs import normalize,combine_history,attach_outcomes


class PreparationTests(unittest.TestCase):
    def test_labels_keep_repeated_rows_but_exclude_outcomes_and_prose(self):
        with tempfile.TemporaryDirectory() as temp:
            row=dict(schema_version=2,page_id='a',source='proquest',verify_reason='hindsight',date='2000-01-01',
                     scope='national',topic='general_business',direction='improve',horizon_months=6,voice='expert',
                     confidence='hedged',publisher='New York Times',hit=1,realized='improve',window='retrospective')
            p=Path(temp)/'pred_proquest_economy_2000.export.jsonl';p.write_text(json.dumps(row)+'\n\n'+json.dumps(row)+'\n')
            f,m=normalize(Path(temp),2000,2000)
            self.assertEqual(f.record_id.tolist(),['2000:1','2000:3']);self.assertEqual(len(f),2)
            self.assertFalse(set(f)&{'hit','realized','verify_reason','window'})
            self.assertEqual(f.horizon_used.tolist(),[6,6])
            with self.assertRaisesRegex(ValueError,'annual shards'):normalize(Path(temp),2000,2001)
            with self.assertRaisesRegex(ValueError,'Modern'):normalize(Path(temp),2011,2011)

    def test_maturity_and_reference_gaps_never_become_hits(self):
        f=pd.DataFrame([dict(record_id='a',date='2000-01-01',scope='national',topic='general_business',predicted_norm='improve',horizon_used=6)])
        idx=pd.period_range('2000-01','2000-07',freq='M');s=pd.Series([100,101,102,103,104,105,106],index=idx)
        result=attach_outcomes(f,{'general_business':s},'2000-10-01');self.assertFalse(result.scorable.iloc[0])
        result=attach_outcomes(f,{'general_business':s},'2000-11-01');self.assertEqual(result.hit.iloc[0],1)
        result=attach_outcomes(f,{'general_business':s.drop(idx[2])},'2000-11-01');self.assertEqual(result.unscorable_reason.iloc[0],'reference_gap')

    def test_history_overlap_rejected(self):
        from proquest_rnn_runner import REQUIRED
        f=pd.DataFrame([{k:'x' for k in REQUIRED}]);f['date']='2000-01-01'
        with self.assertRaisesRegex(ValueError,'overlaps'):combine_history(f,f)

    def test_modern_fixture_requires_reconciled_manifest(self):
        from test_proquest_modern_intake import IntakeTests
        fixture=IntakeTests();fixture.setUp();self.addCleanup(fixture.doCleanups)
        f,m=normalize(fixture.root,2011,2011,True,fixture.manifest)
        self.assertEqual(len(f),2);self.assertNotIn('hit',f)
        fixture.manifest['prior_exposure']['status']='unknown'
        with self.assertRaisesRegex(ValueError,'exposure'):normalize(fixture.root,2011,2011,True,fixture.manifest)


if __name__=='__main__':unittest.main()
