"""Writing extraction must fail rather than silently choose ambiguous rows."""
import csv
import hashlib
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from proquest_writing_evidence import assemble, select_row


class EvidenceTests(unittest.TestCase):
    def test_missing_or_duplicate_selector_fails(self):
        with self.assertRaises(ValueError): select_row([{'a':'b'}],{'a':'c'})
        with self.assertRaises(ValueError): select_row([{'a':'b'},{'a':'b'}],{'a':'b'})

    def test_ledger_matches_sources_and_retains_negative_arms(self):
        entries, inputs=assemble(ROOT)
        self.assertEqual(len(entries),12)
        self.assertEqual(len({e['id'] for e in entries}),12)
        for name,digest in inputs.items():
            self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(),digest)
        models=next(e for e in entries if e['id']=='E09')
        self.assertEqual(len(models['facts']),12)
        self.assertEqual({f['selector']['arm'] for f in models['facts']},{'none','production','unemployment','both'})
        for entry in entries:
            for fact in entry['facts']:
                if fact['source'].endswith('.csv'):
                    with (ROOT/fact['source']).open(newline='') as f:
                        matches=[r for r in csv.DictReader(f) if all(r[k]==v for k,v in fact['selector'].items())]
                    self.assertEqual(len(matches),1)
                    for key,value in fact['values'].items():self.assertEqual(matches[0][key],value)


if __name__=='__main__':unittest.main()
