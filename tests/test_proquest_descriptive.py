"""Known-answer checks for ProQuest scoring and corpus isolation; no network."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from proquest_descriptive import add_comparisons, horizon, paper_name, realized_outcome, score_claims


class ProQuestChecks(unittest.TestCase):
    def test_horizons(self):
        self.assertEqual(horizon({"horizon_months": 3}), (3, "stated", None))
        self.assertEqual(horizon({"horizon_months": "vague", "horizon_hint": "inferred_long"}), (24, "inferred_long", None))
        self.assertEqual(horizon({"horizon_months": "vague", "horizon_hint": "default"}), (12, "default", None))
        for invalid in [0, 36, "na", "9-12", 1.5]:
            self.assertIsNotNone(horizon({"horizon_months": invalid, "horizon_hint": "default"})[2])

    def test_editions(self):
        self.assertEqual(paper_name("New York Times  (1857-1922)"), "New York Times")
        self.assertEqual(paper_name("New York Times (2008-)"), "New York Times")
        self.assertEqual(paper_name("Boston Daily Globe (1872-1922)"), "Boston Globe")

    def test_threshold_and_missing_endpoint(self):
        values = pd.Series([100., 102.], index=pd.PeriodIndex(["2000-01", "2000-04"], freq="M"))
        self.assertEqual(realized_outcome({"general_business": values}, "general_business", "2000-01", 3)[0], "flat")
        self.assertEqual(realized_outcome({"general_business": values}, "general_business", "2000-01", 2)[2], "outside benchmark coverage")
        self.assertEqual(realized_outcome({"markets": values}, "markets", "2001-01", 3)[2], "outside benchmark coverage")

    def test_comparator_excludes_own_paper(self):
        frame = pd.DataFrame([{"year": 2000, "topic": "general_business", "basis": "INDPRO",
                               "horizon_basis": "stated", "horizon_used": 6, "paper": paper,
                               "hit": hit, "fixed_baseline_hit": 1}
                              for paper, hit in [("A", 1), ("B", 0)] for _ in range(20)])
        compared = add_comparisons(frame)
        self.assertEqual(compared[compared.paper == "A"].peer_hit_rate.iloc[0], 0)
        self.assertEqual(compared[compared.paper == "B"].peer_hit_rate.iloc[0], 1)
        self.assertEqual(compared.peer_adjusted_gap.mean(), 0)

    def test_known_outcomes_and_exclusions(self):
        months = pd.period_range("2000-01", "2002-12", freq="M")
        constant = pd.Series(100., index=months)
        production = constant.copy(); production.loc["2000-04"] = 110.
        stocks = constant.copy(); stocks.loc["2000-04"] = 90.
        employment = pd.Series(5., index=months); employment.loc["2000-04"] = 6.
        recession = pd.Series(0., index=pd.period_range("1900-01", "2002-12", freq="M"))
        recession.loc["1900-02":"1900-04"] = 1
        refs = {"general_business": production, "markets": stocks, "prices": constant,
                "employment": employment, "recession": recession}
        base = {"page_id": "one", "schema_version": 2, "source": "proquest", "verify_reason": "yes",
                "date": "2000-01-01", "publisher": "Wall Street Journal", "scope": "national",
                "topic": "general_business", "direction": "improve", "horizon_months": 3,
                "horizon_hint": "default"}
        variants = [{}, {"topic": "markets", "direction": "worsen"},
                    {"topic": "employment", "direction": "worsen"},
                    {"topic": "prices", "price_direction": "stable"},
                    {"scope": "global"}, {"topic": "other"},
                    {"horizon_months": 36}, {"date": "1900-01-01", "direction": "worsen"}]
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for year in range(1900, 2011):
                (root / f"pred_proquest_economy_{year}.export.jsonl").write_text("")
            for edits in variants:
                row = {**base, **edits}
                path = root / f"pred_proquest_economy_{row['date'][:4]}.export.jsonl"
                with path.open("a") as file:
                    file.write(json.dumps(row) + "\n")
            (root / "pred_proquest_economy_crash_1929.export.jsonl").write_text("invalid JSON; must be ignored")
            frame = score_claims(root, refs)
            self.assertEqual(len(frame), 8)
            self.assertEqual(frame.hit.dropna().tolist(), [1, 1, 1, 1, 1])
            self.assertEqual(frame.scorable.sum(), 5)
            self.assertEqual(frame.iloc[0].basis, "NBER proxy")
            self.assertEqual(frame.iloc[1].horizon_used, 3)
            # Raw or LOC rows cannot enter the analysis, even in an annual-named shard.
            for row in [{k: v for k, v in base.items() if k != "verify_reason"}, {**base, "source": "loc"}]:
                (root / "pred_proquest_economy_2000.export.jsonl").write_text(json.dumps(row) + "\n")
                with self.assertRaises(ValueError):
                    score_claims(root, refs)


if __name__ == "__main__":
    unittest.main()
