"""Sampling integrity, including pilot exclusion and physical-row retention."""
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from proquest_main_audit import select


class MainAuditTests(unittest.TestCase):
    def test_fixed_sample_excludes_pilot_and_unscorable(self):
        rows = [{"record_id": f"2000:{i}", "scorable": str(i != 9)}
                for i in range(10)]
        a, frame = select(rows, {"2000:0"}, 4)
        b, _ = select(list(reversed(rows)), {"2000:0"}, 4)
        self.assertEqual(a, b)
        self.assertEqual(len(frame), 8)
        self.assertEqual(len({r["record_id"] for r in a}), 4)
        self.assertFalse({"2000:0", "2000:9"} & {r["record_id"] for r in a})

    def test_identical_labels_keep_distinct_addresses(self):
        rows = [{"record_id": f"2000:{i}", "scorable": "True", "direction": "up"}
                for i in range(4)]
        sample, frame = select(rows, set(), 4)
        self.assertEqual(len(sample), 4)
        self.assertEqual(len(frame), 4)

    def test_invalid_frame_fails(self):
        row = {"record_id": "2000:1", "scorable": "True"}
        with self.assertRaises(ValueError):
            select([row, row], set(), 1)
        with self.assertRaises(ValueError):
            select([row], {"2000:2"}, 1)


if __name__ == "__main__":
    unittest.main()
