"""Leakage boundaries and prespecified selection for forward-time development."""
from pathlib import Path
import sys
import tempfile
import unittest
import numpy as np
import pandas as pd
import torch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from proquest_rnn_development import development_labels,fold_masks,prepare_fold,fit_seed,select_candidate,CANDIDATES,REFERENCE
from proquest_rnn import ClaimGRU,train_gru
import contextlib
import io


def fixture():
    months=pd.period_range('1920-01','1996-12',freq='M'); n=len(months)
    return pd.DataFrame({'record_id':[f'r{i}' for i in range(n)],'page_id':[f'p{i}' for i in range(n)],
        'date':months.to_timestamp(),'month':months,'year':months.year,'scope':'national','topic':'general_business',
        'paper':'synthetic','voice':'author','confidence':'hedged','predicted_norm':np.where(np.arange(n)%2,'improve','worsen'),
        'horizon_basis':'stated','horizon_used':12,'hit':np.arange(n)%2,'scorable':True,'basis':'INDPRO'})


class DevelopmentTests(unittest.TestCase):
    def test_read_scope_ignores_later_outcomes(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'labels.csv'; frame=fixture(); frame.to_csv(path,index=False)
            first=development_labels(path)
            frame.loc[frame.year>=1995,'hit']=999
            frame.loc[frame.year>=1995,'paper']='FUTURE'
            frame.to_csv(path,index=False)
            pd.testing.assert_frame_equal(first,development_labels(path))
            self.assertEqual(first.year.max(),1994)

    def test_nested_purges_and_window_bounds(self):
        frame=fixture(); masks,availability,lower,stop=fold_masks(frame,'1965-01',20)
        self.assertEqual(str(lower),'1940-01'); self.assertEqual(str(stop),'1960-01')
        self.assertTrue((availability[masks['train']]<stop).all())
        self.assertTrue((availability[masks['stopping']]<pd.Period('1965-01')).all())
        self.assertTrue((availability[masks['assessment']]<pd.Period('1970-01')).all())
        self.assertTrue((frame.loc[masks['train'],'month']>=lower).all())
        self.assertTrue((np.sum(list(masks.values()),axis=0)<=1).all())

    def test_assessment_changes_cannot_change_fit_or_preprocessing(self):
        torch.set_num_threads(2)
        labels=fixture().query('year < 1995').copy()
        first=prepare_fold(labels,'1965-01',20)
        changed=labels.copy(); changed.loc[changed.year>=1965,'hit']=1-changed.loc[changed.year>=1965,'hit']
        changed.loc[changed.year>=1965,'paper']='ASSESSMENT_ONLY'
        second=prepare_fold(changed,'1965-01',20)
        for name in ['context_scaler','horizon_scaler']:
            np.testing.assert_array_equal(first['parameters'][name].mean_,second['parameters'][name].mean_)
        self.assertNotIn('ASSESSMENT_ONLY',second['parameters']['encoder'].categories_[1])
        config=next(c for c in CANDIDATES if c['id']=='gru8_standard_20')
        a,ha,ea=fit_seed(first,config,11,epochs=2); b,hb,eb=fit_seed(second,config,11,epochs=2)
        self.assertEqual(ha,hb); self.assertEqual(ea,eb)
        for key in a.state_dict(): torch.testing.assert_close(a.state_dict()[key],b.state_dict()[key],rtol=0,atol=0)
        # Saved configuration remains loadable by the existing inference model.
        compatible=ClaimGRU(first['sequence'].shape[-1],first['claim'].shape[-1],8)
        compatible.load_state_dict(a.state_dict())

    def test_selection_requires_consistency_and_complete_grid(self):
        rows=[]; chosen='gru8_standard_expanding'
        for config in CANDIDATES:
            for fold in range(4):
                value=.2 if config['id']==REFERENCE else .22
                if config['id']==chosen: value=[.19,.19,.19,.201][fold]
                # Very large improvement in just two eras cannot qualify.
                if config['id']=='gru8_strong_20': value=[.01,.01,.21,.21][fold]
                rows.append({'candidate':config['id'],'origin':str(fold),'brier':value})
        result,ranking=select_candidate(pd.DataFrame(rows)); self.assertEqual(result,chosen)
        self.assertFalse(ranking.set_index('candidate').loc['gru8_strong_20','qualifies'])
        with self.assertRaisesRegex(ValueError,'Incomplete'): select_candidate(pd.DataFrame(rows[:-1]))

    def test_reference_training_matches_original_implementation(self):
        torch.set_num_threads(2)
        data=prepare_fold(fixture().query('year < 1995'),'1965-01')
        config=next(c for c in CANDIDATES if c['id']==REFERENCE)
        model,_,epoch=fit_seed(data,config,11,epochs=2)
        masks={'train':data['masks']['train'],'validation':data['masks']['stopping']}
        with contextlib.redirect_stdout(io.StringIO()):
            original,_,old_epoch=train_gru(torch.from_numpy(data['sequence']),torch.from_numpy(data['claim']),
                torch.from_numpy(data['y']),torch.from_numpy(data['weights']),masks,11,epochs=2)
        self.assertEqual(epoch,old_epoch)
        for key in model.state_dict():
            torch.testing.assert_close(model.state_dict()[key],original.state_dict()[key],rtol=0,atol=0)


if __name__=='__main__': unittest.main()
