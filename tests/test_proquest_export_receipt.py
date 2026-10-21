"""Receipt integrity tests using a tiny synthetic archive, never real quotes."""
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from proquest_export_receipt import inspect_archive, receive, sha


class ReceiptTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.claim = dict(schema_version=2, page_id='a', source='proquest',
                          date='2011-01-01', verify_reason='unjudged (kept by default)')
        self.empty = dict(schema_version=2, page_id='b', no_predictions=True)

    def archive(self, mutate=None, extra=None):
        data = ''.join(json.dumps(r)+'\n' for r in [self.claim, self.empty, self.empty]).encode()
        stage = dict(articles=3, candidates=2, retained=1, rejected=1, verification_default_kept=1)
        entry = dict(year=2011, set='verified', path='verified/pred_proquest_economy_2011.export.jsonl',
                     bytes=len(data), sha256=sha(data), records=3, claims=1,
                     min_date='2011-01-01', max_date='2011-01-01', stage_counts=stage)
        m = dict(schema='proquest-modern-export-v1', source='proquest', package_sets=['verified'],
                 years=[2011], files=[entry], totals=stage,
                 exceptions=[dict(audit_id='verified:2011:1', year=2011, source_line=1,
                                  page_id='a', reason=self.claim['verify_reason'])])
        if mutate:
            mutate(m)
        path = self.root/'source.tar.xz'
        with tarfile.open(path, 'w:xz') as t:
            for name, content in [('manifest.json', json.dumps(m).encode()), (entry['path'], data)]:
                member = tarfile.TarInfo(name); member.size = len(content)
                t.addfile(member, io.BytesIO(content))
            if extra:
                t.addfile(extra, io.BytesIO(b''))
        return path, data

    def test_preserves_duplicates_bytes_and_flags_gap_without_claiming_readiness(self):
        archive, data = self.archive()
        report = receive(archive, self.root/'received')
        self.assertEqual((self.root/'received/verified/pred_proquest_economy_2011.export.jsonl').read_bytes(), data)
        self.assertEqual(report['files'][0]['identical_empty_rows_beyond_first'], 1)
        self.assertEqual(report['files'][0]['stage_articles_without_export_rows'], 1)
        self.assertFalse(report['model_evaluation_ready'])
        with self.assertRaisesRegex(ValueError, 'already exists'):
            receive(archive, self.root/'received')

    def test_bad_hash_counts_and_exception_addresses(self):
        for mutate in [lambda m: m['files'][0].update(sha256='0'*64),
                       lambda m: m['files'][0].update(claims=2),
                       lambda m: m['exceptions'][0].update(source_line=2)]:
            with self.subTest(mutate=mutate):
                archive, _ = self.archive(mutate)
                with self.assertRaises(ValueError):
                    receive(archive, self.root/'bad')
                self.assertFalse((self.root/'bad').exists())

    def test_unsafe_unexpected_duplicate_or_link_member(self):
        for name in ['../escape', 'manifest.json', 'unexpected.json']:
            archive, _ = self.archive(extra=tarfile.TarInfo(name))
            with self.assertRaises(ValueError):
                inspect_archive(archive)
        link = tarfile.TarInfo('link'); link.type = tarfile.SYMTYPE; link.linkname = '/tmp'
        archive, _ = self.archive(extra=link)
        with self.assertRaises(ValueError):
            inspect_archive(archive)

    def test_rejects_source_prose_and_wrong_publication_year(self):
        self.claim['quote'] = 'synthetic test text'
        archive, _ = self.archive()
        with self.assertRaisesRegex(ValueError, 'Source text'):
            inspect_archive(archive)
        del self.claim['quote']; self.claim['date'] = '2010-01-01'
        archive, _ = self.archive()
        with self.assertRaisesRegex(ValueError, 'Date outside'):
            inspect_archive(archive)


if __name__ == '__main__':
    unittest.main()
