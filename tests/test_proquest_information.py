"""Known-answer weighting, information timing, outcome, and model checks."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from proquest_panel import FEATURES, build_panels, forecast_features, read_claims, sign_label
from proquest_information import (CLASSES, MODELS, fit_forward, load_spec, metrics,
                                  paired_intervals, preprocess, targets, training_mask)


def claim(page, month="2000-01", paper="A", sign="positive", **edits):
    return {"page_id": page, "date": month + "-01", "month": pd.Period(month, "M"),
            "paper": paper, "topic": "general_business", "sign": sign, **edits}


def six_months():
    return pd.DataFrame([claim(f"{paper}-{month}", month=str(month), paper=paper)
                         for month in pd.period_range("2000-01", "2000-12", freq="M") for paper in ("A", "B")])


class InformationChecks(unittest.TestCase):
    def test_article_then_paper_weights_and_missing_months(self):
        records = [claim("a")] * 3 + [claim("b", sign="negative")]
        records += [claim(f"c{i}", paper="B") for i in range(10)]
        article, paper, national = build_panels(pd.DataFrame(records), pd.period_range("2000-01", "2000-02", freq="M"))
        business = national[national.topic == "general_business"].set_index("month")
        self.assertEqual(len(article), 12)
        self.assertEqual(business.loc["2000-01", "n_claims"], 14)
        self.assertAlmostEqual(business.loc["2000-01", "positive_share"], .75)
        self.assertAlmostEqual(business.loc["2000-01", "net_direction"], .5)
        self.assertEqual(business.loc["2000-02", "n_papers"], 0)
        self.assertTrue(np.isnan(business.loc["2000-02", "net_direction"]))
        self.assertTrue(np.isnan(business.loc["2000-02", "disagreement"]))

    def test_current_and_future_print_labels_cannot_change_features(self):
        records = six_months()
        calendar = pd.period_range("2000-01", "2000-12", freq="M")
        origin = pd.period_range("2000-07", "2000-07", freq="M")
        _, panel, national = build_panels(records, calendar)
        original = forecast_features(panel, national, origin)
        records.loc[records.month >= origin[0], "sign"] = "negative"
        records["hit"] = 1; records["scorable"] = False; records["verify_reason"] = "future knowledge"
        _, changed_panel, changed_national = build_panels(records, calendar)
        changed = forecast_features(changed_panel, changed_national, origin)
        pd.testing.assert_frame_equal(original, changed)
        self.assertEqual(original.latest_print_month.iloc[0], pd.Period("2000-06", "M"))
        self.assertEqual(original.net_direction_3m.iloc[0], 1.)

    def test_common_paper_change_ignores_entering_paper(self):
        records = six_months()
        entering = [claim(f"C-{m}", month=str(m), paper="C", sign="negative")
                    for m in pd.period_range("2000-04", "2000-06", freq="M")]
        records = pd.concat([records, pd.DataFrame(entering)], ignore_index=True)
        _, paper, national = build_panels(records, pd.period_range("2000-01", "2000-12", freq="M"))
        features = forecast_features(paper, national, pd.period_range("2000-07", "2000-07", freq="M"))
        self.assertAlmostEqual(features.net_change_common_papers.iloc[0], 0.)
        self.assertAlmostEqual(features.net_direction_3m.iloc[0], 1 / 3)

    def test_sparse_coverage_stays_missing(self):
        records = six_months().query("paper == 'A'")
        _, paper, national = build_panels(records, pd.period_range("2000-01", "2000-12", freq="M"))
        features = forecast_features(paper, national, pd.period_range("2000-07", "2000-07", freq="M"))
        self.assertTrue(features[list(FEATURES)].isna().all().all())

    def test_signs_do_not_call_inflation_good_news(self):
        self.assertEqual(sign_label({"topic": "prices", "price_direction": "up"}), "positive")
        self.assertEqual(sign_label({"topic": "employment", "unemployment_direction": "up"}), "negative")
        self.assertEqual(sign_label({"topic": "employment", "direction": "improve"}), "positive")

    def test_source_loader_ignores_horizon_outcome_and_annotations(self):
        row = {"schema_version": 2, "source": "proquest", "verify_reason": "valid", "page_id": "a",
               "date": "2000-01-01", "scope": "national", "topic": "general_business", "direction": "improve",
               "horizon_months": 999, "window": "crisis", "hit": 0, "scorable": False}
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for year in range(1900, 2011):
                (root / f"pred_proquest_economy_{year}.export.jsonl").write_text("")
            path = root / "pred_proquest_economy_2000.export.jsonl"
            path.write_text(json.dumps(row) + "\n" + json.dumps(row) + "\n")
            (root / "pred_proquest_economy_crash_1929.export.jsonl").write_text("not loaded")
            frame, counts, hashes = read_claims(root)
            self.assertEqual(len(frame), 2)
            self.assertEqual(counts["panel_claims"], 2)
            self.assertEqual(len(hashes), 111)
            self.assertEqual(set(frame.columns), {"page_id", "date", "month", "topic", "sign", "paper"})
            for invalid in [{**row, "source": "loc"}, {k: v for k, v in row.items() if k != "verify_reason"}]:
                path.write_text(json.dumps(invalid) + "\n")
                with self.assertRaisesRegex(ValueError, "Not an annual verified"):
                    read_claims(root)

    def test_six_month_target_boundary_and_maturity(self):
        spec, _ = load_spec()
        production = pd.Series([100., 102.], index=pd.PeriodIndex(["2000-01", "2000-07"], freq="M"))
        origins = pd.period_range("2000-02", "2000-02", freq="M")
        scored = targets(origins, production, spec).iloc[0]
        self.assertEqual(scored.target, "flat")
        self.assertEqual(scored.target_start, pd.Period("2000-01", "M"))
        self.assertEqual(scored.target_end, pd.Period("2000-07", "M"))
        self.assertEqual(scored.label_available, pd.Period("2000-10", "M"))
        production.iloc[1] = 110.
        self.assertEqual(targets(origins, production, spec).target.iloc[0], "rise")
        production.iloc[1] = 90.
        self.assertEqual(targets(origins, production, spec).target.iloc[0], "fall")
        self.assertIsNone(targets(origins, production.iloc[:1], spec).target.iloc[0])

    def test_purge_uses_strict_label_availability(self):
        data = pd.DataFrame({"origin": pd.PeriodIndex(["1999-04", "1999-05", "2000-01"], freq="M"),
                             "label_available": pd.PeriodIndex(["1999-12", "2000-01", "2000-09"], freq="M"),
                             "target": ["rise", "fall", "flat"]})
        self.assertEqual(training_mask(data, pd.Period("2000-01", "M")).tolist(), [True, False, False])

    def test_preprocessing_uses_training_only(self):
        train = pd.DataFrame({f: [1., 3., np.nan] for f in FEATURES})
        test = pd.DataFrame({f: [1e12, np.nan] for f in FEATURES})
        _, x_test, _, missing, params = preprocess(train, test)
        np.testing.assert_allclose(params["median"], 2.)
        np.testing.assert_allclose(params["mean"], 2.)
        np.testing.assert_allclose(x_test[1, :4], 0.)
        np.testing.assert_allclose(missing[1], 1.)

    def test_future_and_unmatured_labels_do_not_enter_refit(self):
        spec, _ = load_spec()
        spec = {**spec, "evaluation_start": "2000-01", "evaluation_end": "2000-12"}
        origins = pd.period_range("1990-01", "2000-12", freq="M")
        data = pd.DataFrame({"origin": origins, "label_available": origins + 8,
                             "target": [CLASSES[i % 3] for i in range(len(origins))],
                             **{f: np.sin(np.arange(len(origins)) / (i + 2)) for i, f in enumerate(FEATURES)}})
        first, refits, _, _ = fit_forward(data, spec)
        data.loc[data.label_available >= pd.Period("2000-01", "M"), "target"] = "fall"
        second, _, _, _ = fit_forward(data, spec)
        columns = [f"{m}_{c}" for m in MODELS for c in CLASSES]
        np.testing.assert_allclose(first[columns], second[columns])
        self.assertEqual(refits.latest_training_label_available.iloc[0], "1999-12")
        self.assertEqual(refits.purged_earlier_months.iloc[0], 8)

    def test_multiclass_metrics_known_answers(self):
        data = pd.DataFrame({"target": list(CLASSES)})
        for i, label in enumerate(CLASSES):
            data[f"perfect_{label}"] = np.eye(3)[:, i]
            data[f"uniform_{label}"] = 1 / 3
        self.assertEqual(metrics(data, "perfect")["brier"], 0.)
        self.assertEqual(metrics(data, "perfect")["accuracy"], 1.)
        self.assertAlmostEqual(metrics(data, "uniform")["brier"], 2 / 3)
        self.assertAlmostEqual(metrics(data, "uniform")["log_loss"], np.log(3))

    def test_joint_blocks_preserve_identical_forecasts(self):
        spec, _ = load_spec()
        data = pd.DataFrame({"origin": pd.period_range("1950-01", "2010-12", freq="M"),
                             "target": [CLASSES[i % 3] for i in range(732)]})
        for model in MODELS:
            for label in CLASSES:
                data[f"{model}_{label}"] = 1 / 3
        intervals = paired_intervals(data, {**spec, "bootstrap_draws": 100})
        np.testing.assert_allclose(intervals[["improvement", "low", "high"]], 0.)


if __name__ == "__main__":
    unittest.main()
