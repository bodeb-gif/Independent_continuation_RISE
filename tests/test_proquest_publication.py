"""Guard evidence freshness, sampling eligibility, and blinded pilot separation."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from proquest_publication import check_hashes, pilot_records, pilot_sample


class PublicationTests(unittest.TestCase):
    def test_changed_source_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "source"
            path.write_bytes(b"original")
            hashes = {"source": hashlib.sha256(b"original").hexdigest()}
            check_hashes(root, hashes)
            path.write_bytes(b"edited")
            with self.assertRaisesRegex(ValueError, "stale"):
                check_hashes(root, hashes)

    def test_sample_keeps_repeated_labels_excludes_unscored(self):
        rows = [{"record_id": f"1900:{i}", "scorable": "True", "topic": "prices"}
                for i in range(20)]
        rows.append({"record_id": "1900:99", "scorable": "False"})
        first, n = pilot_sample(rows)
        second, _ = pilot_sample(list(reversed(rows)))
        self.assertEqual(first, second)
        self.assertEqual(n, 20)
        self.assertEqual(len(first), 12)
        self.assertEqual(len({r["record_id"] for r in first}), 12)
        self.assertNotIn("1900:99", {r["record_id"] for r in first})
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            pilot_sample(rows + rows[:1])

    def test_mapping_checks_and_no_outcome_leakage(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            name = "data/proquest/verified/pred_proquest_economy_1900.export.jsonl"
            path = root / name
            path.parent.mkdir(parents=True)
            original = {"page_id": "p", "date": "1900-01-01", "topic": "prices",
                        "direction": "up", "scope": "national", "horizon_months": 6,
                        "horizon_hint": "stated", "verify_reason": "retrospective prose"}
            path.write_text("\n" + json.dumps(original) + "\n")
            scored = {k: str(v) for k, v in original.items()}
            scored.update(record_id="1900:2", publisher_original="Example",
                          basis="CPI", horizon_used="6.0", hit="1", realized="up")
            retrieval, labels = pilot_records(root, [scored], 100, {name: "hash"})
            self.assertEqual(retrieval[0]["source_line"], 2)
            self.assertEqual(retrieval[0]["pilot_inclusion_probability"], .01)
            for field in ("topic", "direction", "horizon_months", "verify_reason", "hit", "realized"):
                self.assertNotIn(field, retrieval[0])
            for field in ("hit", "realized", "verify_reason"):
                self.assertNotIn(field, labels[0])
            scored["page_id"] = "different"
            with self.assertRaisesRegex(ValueError, "mismatch"):
                pilot_records(root, [scored], 100, {name: "hash"})


if __name__ == "__main__":
    unittest.main()
