"""Check generated pilot boundaries; never create human responses."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from proquest_review import build, read_rows, SAFE_FIELDS


class ReviewTests(unittest.TestCase):
    def test_pack_blinding_and_hashes(self):
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder)
            manifest = build(ROOT, out)
            pack = json.loads((out / "pack.json").read_text())
            self.assertEqual(len(pack["records"]), 12)
            for row in pack["records"]:
                self.assertEqual(set(row), SAFE_FIELDS)
                self.assertEqual(row["mapping_status"], "pending")
            labels = (out / "comparison.json").read_bytes()
            self.assertEqual(hashlib.sha256(labels).hexdigest(), pack["comparison_sha256"])
            self.assertNotIn(labels.decode(), (out / "review.html").read_text())
            self.assertNotIn("realized", json.loads(labels)["records"][0])
            for name, expected in manifest["outputs_sha256"].items():
                self.assertEqual(hashlib.sha256((out/name).read_bytes()).hexdigest(), expected)

    def test_unexpected_fields_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder)/"bad.csv"
            p.write_text("audit_id,realized\na,rise\n")
            with self.assertRaisesRegex(ValueError,"Unexpected fields"):
                read_rows(p, SAFE_FIELDS)


if __name__ == "__main__":
    unittest.main()
