"""Portable bundle round trip, print-time inputs, scope and output protections."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
import numpy as np
import pandas as pd
import torch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from proquest_rnn_runner import read_labels,read_features,train,predict,new_output,training_configuration,ARMS


def fixture():
    months=pd.period_range('1978-01','2004-12',freq='M'); n=len(months)
    return pd.DataFrame({'record_id':[f'synthetic:{i}' for i in range(n)],'page_id':[f'a{i}' for i in range(n)],
        'date':months.to_timestamp(),'month':months,'year':months.year,'scope':'national','topic':'general_business',
        'paper':'synthetic','voice':'author','confidence':'hedged','predicted_norm':np.where(np.arange(n)%2,'improve','worsen'),
        'horizon_basis':'stated','horizon_used':6,'hit':np.arange(n)%2,'scorable':True,'basis':'INDPRO'})


class RunnerTests(unittest.TestCase):
    def test_predict_reader_does_not_require_or_read_outcomes(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'labels.csv'; frame=fixture().drop(columns=['hit','scorable','basis']); frame.to_csv(path,index=False)
            labels=read_labels(path,'2004-12')
            self.assertNotIn('hit',labels); self.assertEqual(len(labels),len(frame))
            frame['hit']='deliberately invalid outcome'; frame['verify_reason']='not a feature'; frame.to_csv(path,index=False)
            pd.testing.assert_frame_equal(labels,read_labels(path,'2004-12'))

    def test_future_years_require_explicit_scope_flag(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'labels.csv'; frame=fixture().iloc[:2].copy(); frame['date']=['2011-01-01','2011-02-01']; frame.to_csv(path,index=False)
            with self.assertRaisesRegex(ValueError,'Active scope'): read_labels(path,'2011-12')
            self.assertEqual(len(read_labels(path,'2011-12',True)),2)

    def test_new_outputs_cannot_replace_existing_runs(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(ValueError,'already exists'): new_output(temp)
            with self.assertRaisesRegex(ValueError,'under data/scored'): new_output(Path(temp)/'outside')

    def test_polarization_missing_month_is_not_silently_imputed(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'features.csv'
            pd.DataFrame({'origin':['2000-01'],'political_polarization':[np.nan],'forecast_polarization':[.5]}).to_csv(path,index=False)
            self.assertTrue(read_features(path,pd.Series(pd.PeriodIndex(['2000-01'],freq='M'))).political_polarization.isna().all())
            with self.assertRaisesRegex(ValueError,'Missing polarization month'): read_features(path,pd.Series(pd.PeriodIndex(['2000-02'],freq='M')))

    def test_all_arms_training_prediction_round_trip_and_future_invariance(self):
        torch.set_num_threads(2)
        with tempfile.TemporaryDirectory() as temp:
            out=Path(temp); labels=fixture(); features=out/'features.csv'
            pd.DataFrame({'origin':labels.month.astype(str),'political_polarization':.3+.1*np.sin(np.arange(len(labels))/12),
                          'forecast_polarization':.6+.1*np.cos(np.arange(len(labels))/12)}).to_csv(features,index=False)
            with contextlib.redirect_stdout(io.StringIO()):
                manifest=train(labels,features,'1988-01','1998-01',list(ARMS),[11],1,out)
            (out/'bundle_manifest.json').write_text(json.dumps(manifest))
            predictions,_=predict(out,labels.drop(columns=['hit','scorable','basis']),features,'1998-01','2004-12',list(ARMS))
            saved=pd.read_csv(out/'test_predictions.csv.gz')
            self.assertEqual(predictions.record_id.tolist(),saved.record_id.tolist())
            columns=[c for c in predictions if c.startswith(('gru_','logistic_'))]
            np.testing.assert_allclose(predictions[columns],saved[columns],atol=2e-6)
            changed=labels.copy(); changed.loc[changed.year>2001,'predicted_norm']='flat'
            before,_=predict(out,labels,features,'1998-01','2001-12',list(ARMS))
            after,_=predict(out,changed,features,'1998-01','2001-12',list(ARMS))
            pd.testing.assert_frame_equal(before,after)
            artifact=out/'gru_baseline_11.pt'; artifact.write_bytes(artifact.read_bytes()+b'tamper')
            with self.assertRaisesRegex(ValueError,'Bundle artifact changed'):
                predict(out,labels,features,'1998-01','2004-12',list(ARMS))

    def test_selected_configuration_refit_and_reload(self):
        torch.set_num_threads(2)
        with tempfile.TemporaryDirectory() as temp:
            out=Path(temp); source=out/'config.json'
            source.write_text(json.dumps({'candidate':{'hidden':8,'dropout':.15,'weight_decay':.001,'window_years':5}}))
            config=training_configuration(source)
            with contextlib.redirect_stdout(io.StringIO()):
                manifest=train(fixture(),None,'1988-01','1998-01',['baseline'],[11],1,out,configuration=config)
            splits=pd.read_csv(out/'split_assignments.csv.gz')
            self.assertTrue(splits.loc[splits.split.eq('train'),'date'].ge('1983-01-01').all())
            checkpoint=torch.load(out/'gru_baseline_11.pt',weights_only=True)
            self.assertEqual(checkpoint['hidden_size'],8)
            (out/'bundle_manifest.json').write_text(json.dumps(manifest))
            predictions,_=predict(out,fixture(),None,'1998-01','2004-12',['baseline'])
            expected=pd.read_csv(out/'test_predictions.csv.gz')
            np.testing.assert_allclose(predictions.gru_ensemble__baseline,expected.gru_ensemble__baseline,atol=2e-6)

    def test_age_weighted_configuration_refit_and_reload(self):
        torch.set_num_threads(2)
        with tempfile.TemporaryDirectory() as temp:
            out=Path(temp); source=out/'config.json'
            settings={'hidden':8,'dropout':.15,'weight_decay':.001,'window_years':None,'half_life_years':20}
            source.write_text(json.dumps(settings)); config=training_configuration(source)
            manifest=train(fixture(),None,'1988-01','1998-01',['baseline'],[11],1,out,configuration=config)
            self.assertEqual(manifest['configuration']['half_life_years'],20)
            (out/'bundle_manifest.json').write_text(json.dumps(manifest))
            predictions,_=predict(out,fixture(),None,'1998-01','2004-12',['baseline'])
            expected=pd.read_csv(out/'test_predictions.csv.gz')
            np.testing.assert_allclose(predictions.gru_ensemble__baseline,expected.gru_ensemble__baseline,atol=2e-6)
            for bad in [0,True,'20',float('inf')]:
                source.write_text(json.dumps(dict(settings,half_life_years=bad)))
                with self.assertRaises(ValueError):training_configuration(source)


if __name__=='__main__': unittest.main()
