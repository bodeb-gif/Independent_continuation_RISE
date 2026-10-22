"""Synthetic, offline checks for the one-attempt ProQuest verification runner."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
import proquest_reverify300 as runner


class Checks(unittest.TestCase):
    def test_strict_verdict(self):
        self.assertFalse(runner.strict_verdict('[{"id":0,"keep":false}]'))
        self.assertTrue(runner.strict_verdict('```json\n[{"id":0,"keep":true}]\n```'))
        for raw in ['[{"id":0,"keep":"false"}]','[{"id":1,"keep":true}]',
                    '[{"id":false,"keep":true}]','[]','[{"id":0,"keep":true},{"id":0,"keep":false}]']:
            with self.assertRaises((ValueError,TypeError)):
                runner.strict_verdict(raw)

    def fixture(self, p):
        metadata = []
        for n in range(300):
            metadata.append({'audit_id':f'SYNTHETIC:{n}', 'date':'2000-01-01', 'publisher':'Synthetic'})
        (p/'reviewer2_300_v1').mkdir()
        data=json.dumps(metadata).encode()
        (p/'reviewer2_300_v1/sample_metadata.json').write_bytes(data)
        for batch,start in [('source_review_150_v1',0),('source_review_additional150_v1',150)]:
            (p/batch).mkdir()
            rows=[{'audit_id':f'SYNTHETIC:{n}', 'recovered':True, 'quote':f'Output will rise {n}',
                   'article':f'Synthetic article {n}', 'human_label':'MUST_NOT_REACH_MODEL'} for n in range(start,start+150)]
            (p/batch/'sources.json').write_text(json.dumps(rows))
        (p/'verify_gpt.py').write_text('# synthetic verifier\n')
        (p/'extract_gpt.py').write_text('# synthetic extractor\n')
        calls=[]
        client=SimpleNamespace()
        def request(**kwargs):
            calls.append(kwargs)
            self.assertNotIn('MUST_NOT_REACH_MODEL',str(kwargs))
            return SimpleNamespace(model='gpt-4o-mini', usage=None,
                model_dump=lambda:{'model':'gpt-4o-mini','synthetic':True},
                choices=[SimpleNamespace(finish_reason='stop',message=SimpleNamespace(content='[{"id":0,"keep":true,"reason":"synthetic prose"}]'))])
        def options(**kwargs):
            self.assertEqual(kwargs['max_retries'],0)
            return client
        client.with_options=options
        client.chat=SimpleNamespace(completions=SimpleNamespace(create=request))
        verify=SimpleNamespace(__file__=str(p/'verify_gpt.py'), VERIFY_PROMPT='synthetic',
            build_prompt=lambda page,claims:json.dumps({'page':page,'claims':claims}))
        extract=SimpleNamespace(__file__=str(p/'extract_gpt.py'),make_client=lambda args:(client,args.model))
        return data,calls,verify,extract

    def test_prepare_no_calls_resume_at_most_once_and_source_free_export(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);data,calls,verify,extract=self.fixture(p)
            with patch.object(runner,'METADATA_SHA',runner.sha(data)), patch.dict(sys.modules,verify_gpt=verify,extract_gpt=extract), patch.object(runner.time,'sleep'), contextlib.redirect_stdout(io.StringIO()):
                prepared=runner.run(p)
                self.assertEqual(calls,[])
                self.assertEqual(prepared['counts'],{'not_attempted':300})
                # Simulate an interrupted attempt whose network result is unknown.
                runner.dump_new(p/runner.RUN_NAME/'attempts/001.json',{'n':1})
                result=runner.run(p,True)
                self.assertEqual(len(calls),299)
                self.assertEqual(result['counts'],{'attempted_unresolved':1,'judged':299})
                again=runner.run(p,True)
                self.assertEqual(len(calls),299)
                self.assertEqual(again['attempted_n'],300)
                exported=json.dumps(again)
                self.assertNotIn('synthetic prose',exported)
                self.assertNotIn('Output will rise',exported)
                self.assertNotIn('MUST_NOT_REACH_MODEL',exported)

    def test_changed_sample_stops_before_connection(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);_,calls,verify,extract=self.fixture(p)
            with patch.object(runner,'METADATA_SHA','wrong'), patch.dict(sys.modules,verify_gpt=verify,extract_gpt=extract):
                with self.assertRaises(AssertionError):runner.run(p,True)
            self.assertEqual(calls,[])


if __name__=='__main__':
    unittest.main()
