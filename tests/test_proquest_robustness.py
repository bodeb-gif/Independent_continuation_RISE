"""Known-answer source, weighting, matching, and dependence checks; no network."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from proquest_descriptive import score_claims
from proquest_robustness import (article_changes, block_intervals, comparison,
                                composition_table, matched_cells, rates, weighted_rows)


def row(source_set="raw", **edits):
    return {"source_set": source_set, "page_id": "a", "record_id": "2000:1", "date": "2000-01-01",
            "paper": "Paper A", "year": 2000, "month": "2000-01", "topic": "general_business",
            "basis": "INDPRO", "horizon_basis": "stated", "horizon_used": 12,
            "hit": 1., "fixed_baseline_hit": 1., "scorable": True, **edits}


class RobustnessChecks(unittest.TestCase):
    def test_raw_adapter_is_explicit_and_preserves_scoring(self):
        claim = {"page_id": "a", "schema_version": 2, "source": "proquest", "date": "2000-01-01",
                 "scope": "national", "topic": "general_business", "direction": "improve",
                 "horizon_months": 12, "horizon_hint": "stated"}
        refs = {"general_business": pd.Series([100., 110.], index=pd.PeriodIndex(["2000-01", "2001-01"], freq="M")),
                "recession": pd.Series([0.], index=pd.PeriodIndex(["2000-01"], freq="M"))}
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for year in range(1900, 2011):
                (root / f"pred_proquest_economy_{year}.export.jsonl").write_text("")
            path = root / "pred_proquest_economy_2000.export.jsonl"
            path.write_text(json.dumps(claim) + "\n" + json.dumps(claim) + "\n")
            before = path.read_bytes()
            with self.assertRaisesRegex(ValueError, "Not a machine-verified"):
                score_claims(root, refs)
            raw = score_claims(root, refs, source_set="raw")
            self.assertEqual(len(raw), 2)  # Identical stripped labels are retained.
            self.assertEqual(raw.hit.tolist(), [1., 1.])
            self.assertEqual(path.read_bytes(), before)
            verified_claim = {**claim, "verify_reason": "hindsight prose", "window": "retrospective"}
            path.write_text(json.dumps(verified_claim) + "\n")
            verified = score_claims(root, refs)
            pd.testing.assert_frame_equal(raw.iloc[:1], verified)
            self.assertNotIn("verify_reason", raw)
            self.assertNotIn("window", verified)
            with self.assertRaisesRegex(ValueError, "Verified claim in raw"):
                score_claims(root, refs, source_set="raw")
            path.write_text(json.dumps({**claim, "source": "loc"}) + "\n")
            with self.assertRaisesRegex(ValueError, "Unexpected corpus"):
                score_claims(root, refs, source_set="raw")
            with self.assertRaisesRegex(ValueError, "Unknown ProQuest"):
                score_claims(root, refs, source_set="anything")

    def test_article_and_month_weights_have_known_answers(self):
        frame = pd.DataFrame([row(hit=0), row(hit=0), row(page_id="b", hit=1)])
        self.assertAlmostEqual(rates(weighted_rows(frame, "claim"))["hit_rate"], 1 / 3)
        self.assertAlmostEqual(rates(weighted_rows(frame))["hit_rate"], .5)
        frame.loc[2, "month"] = "2000-02"
        self.assertAlmostEqual(rates(weighted_rows(frame, "month"))["hit_rate"], .5)
        doubled = pd.concat([frame, frame[frame.page_id == "a"]], ignore_index=True)
        self.assertAlmostEqual(rates(weighted_rows(doubled))["hit_rate"], .5)

    def test_matching_removes_known_composition_difference(self):
        records = []
        for name, sizes in [("raw", (9, 1)), ("verified", (1, 9))]:
            for year, size, hit in zip([2000, 2001], sizes, [1., 0.]):
                records.extend(row(name, year=year, month=f"{year}-01", hit=hit, page_id=f"{year}-{i}") for i in range(size))
        frame = pd.DataFrame(records)
        pooled = comparison("pooled", weighted_rows(frame))
        self.assertAlmostEqual(pooled["delta_hit_rate"], -.8)
        cells, weights = matched_cells(frame, minimum=1)
        matched = comparison("matched", weights)
        self.assertEqual(len(cells), 2)
        self.assertAlmostEqual(matched["raw_hit_rate"], .5)
        self.assertAlmostEqual(matched["verified_hit_rate"], .5)
        self.assertAlmostEqual(matched["delta_hit_rate"], 0.)
        excluded, _ = matched_cells(frame, minimum=2)
        self.assertTrue(excluded.empty)

    def test_exact_month_matching_holds_baseline_constant(self):
        records = []
        for name, sizes in [("raw", (9, 1)), ("verified", (1, 9))]:
            for month, size, baseline in zip(["2000-01", "2000-02"], sizes, [1., 0.]):
                records.extend(row(name, month=month, fixed_baseline_hit=baseline, page_id=f"{month}-{i}") for i in range(size))
        frame = pd.DataFrame(records)
        _, year_weights = matched_cells(frame, minimum=1)
        self.assertAlmostEqual(comparison("year", year_weights)["delta_fixed_baseline"], -.8)
        _, month_weights = matched_cells(frame, exact_month=True, minimum=1)
        self.assertAlmostEqual(comparison("month", month_weights)["delta_fixed_baseline"], 0.)

    def test_joint_resampling_keeps_identical_overlapping_sets_identical(self):
        records = [row(name, year=year, hit=float(year % 3 == 0), page_id=str(year))
                   for name in ("raw", "verified") for year in range(1900, 2011)]
        intervals = block_intervals("identical", weighted_rows(pd.DataFrame(records)), reps=100)
        np.testing.assert_allclose(intervals[["verified_minus_raw", "low", "high"]], 0.)
        self.assertTrue((intervals.valid_draws == 100).all())

    def test_article_absence_is_not_zero_retention(self):
        frame = pd.DataFrame([row(page_id="missing"), row(page_id="shared"), row("verified", page_id="shared")])
        represented = {"raw": {"missing", "shared", "empty"}, "verified": {"shared", "empty"}}
        empty = {"raw": {"empty"}, "verified": {"empty"}}
        changes = article_changes(frame, represented, empty).set_index("page_id")
        self.assertTrue(np.isnan(changes.loc["missing", "claim_count_change"]))
        self.assertFalse(changes.loc["missing", "verified_represented"])
        self.assertEqual(changes.loc["empty", "claim_count_change"], 0)

    def test_composition_keeps_one_set_only_and_missing_categories(self):
        frame = pd.DataFrame({"source_set": ["raw", "raw", "verified"], "topic": ["x", None, "y"]})
        composition = composition_table(frame, "topic").set_index("category")
        self.assertEqual(composition.loc["<missing>", "raw_claims"], 1)
        self.assertTrue(np.isnan(composition.loc["y", "verified_raw_count_ratio"]))
        self.assertAlmostEqual(composition.raw_share.sum(), 1.)
        self.assertAlmostEqual(composition.verified_share.sum(), 1.)


if __name__ == "__main__":
    unittest.main()
