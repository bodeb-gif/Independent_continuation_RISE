"""Nested vintage selection must not consult final truth or outer future data."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from proquest_information import CLASSES
from proquest_macro_benchmark import (FEATURES, MODELS, candidates, choose_candidate, fit_study,
                                      inner_folds, load_spec, trainable, vintage_training, windowed)
from proquest_vintages import CORE_FEATURES, CPI_FEATURES, VintageSeries


def fixture():
    months = pd.period_range("1989-01", "2000-12", freq="M")
    levels = 100 + 15 * np.sin(np.arange(len(months)) / 7) + .1 * np.arange(len(months))
    matrix = pd.DataFrame({f"IPT{year % 100:02}M12": np.where(months <= pd.Period(f"{year}-11", "M"), levels, np.nan)
                           for year in range(1994, 2001)}, index=months)
    archive = VintageSeries("IPT", matrix)
    origins = pd.period_range("1990-01", "2000-12", freq="M")
    data = pd.DataFrame({"origin": origins, "target": [CLASSES[i % 3] for i in range(len(origins))],
                         "change_percent": np.arange(len(origins)),
                         **{f: np.cos(np.arange(len(origins)) / (i + 2)) for i, f in enumerate(CORE_FEATURES + CPI_FEATURES + FEATURES)}})
    spec = load_spec()
    study = {"name": "fixture", "training_start": "1990-01", "evaluation_start": "2000-01", "evaluation_end": "2000-12", "include_cpi": False}
    support = pd.period_range("2000-01", "2000-02", freq="M")
    return data, archive, spec, study, support


def training_context(data, archive, spec):
    features = data[["origin"] + list(CORE_FEATURES + CPI_FEATURES + FEATURES)]
    cache = {}
    def get_training(year):
        if year not in cache:
            cache[year] = vintage_training(features, pd.Period(f"{year}-01", "M"), archive, spec)[0]
        return cache[year]
    return features, get_training


class BenchmarkChecks(unittest.TestCase):
    def test_final_truth_and_future_vintage_cannot_change_selection_or_forecasts(self):
        data, archive, spec, study, support = fixture()
        first = fit_study(data, support, archive, spec, study)
        data["target"] = "fall"
        data["change_percent"] = 99999.
        archive.matrix["IPT00M12"] = np.arange(len(archive.matrix)) ** 2
        second = fit_study(data, support, archive, spec, study)
        for name in ["candidate_scores", "inner_predictions", "preprocessing", "coefficients"]:
            pd.testing.assert_frame_equal(first[name], second[name])
        columns = [f"{model}_{label}" for model in MODELS for label in CLASSES]
        np.testing.assert_allclose(first["predictions"][columns], second["predictions"][columns])

    def test_outer_feature_shock_cannot_change_selection_or_training_scaler(self):
        data, archive, spec, study, support = fixture()
        first = fit_study(data, support, archive, spec, study)
        data.loc[data.origin >= pd.Period("2000-01", "M"), list(CORE_FEATURES + FEATURES)] = 1e6
        second = fit_study(data, support, archive, spec, study)
        pd.testing.assert_frame_equal(first["candidate_scores"], second["candidate_scores"])
        pd.testing.assert_frame_equal(first["preprocessing"], second["preprocessing"])
        p = [f"macro_only_{label}" for label in CLASSES]
        self.assertFalse(np.allclose(first["predictions"][p], second["predictions"][p]))

    def test_inner_labels_use_inner_vintage_and_validation_is_mature_at_outer(self):
        data, archive, spec, _, _ = fixture()
        features, get_training = training_context(data, archive, spec)
        folds, _ = inner_folds(features, get_training(2000), 2000, get_training, spec)
        self.assertGreater(len(folds), 1)
        for year, train, validation in folds:
            refit = pd.Period(f"{year}-01", "M")
            self.assertTrue((train.origin + 8 < refit).all())
            self.assertEqual(set(train.label_vintage), {f"IPT{(year - 1) % 100:02}M12"})
            self.assertEqual(set(validation.label_vintage), {"IPT99M12"})
            self.assertTrue((validation.origin + 8 < pd.Period("2000-01", "M")).all())
            self.assertTrue(validation.origin.between(refit, refit + 11).all())
        self.assertEqual(folds[-1][2].origin.max(), pd.Period("1999-04", "M"))

    def test_candidates_share_validation_support_and_selection_minimizes_its_loss(self):
        data, archive, spec, study, _ = fixture()
        features, get_training = training_context(data, archive, spec)
        selected, _, scores, _, predictions = choose_candidate(features, get_training(2000), 2000, get_training, spec, study)
        expected = None
        for candidate, frame in predictions.groupby("candidate"):
            support = set(zip(frame.inner_year, frame.origin))
            expected = support if expected is None else expected
            self.assertEqual(support, expected)
            row = scores[scores.candidate == candidate].iloc[0]
            self.assertAlmostEqual(row.mean_validation_brier, frame.brier.mean())
            self.assertEqual(row.n_validation, len(frame))
        best = scores.loc[scores.selected, "mean_validation_brier"].iloc[0]
        self.assertAlmostEqual(best, scores.mean_validation_brier.min())
        self.assertEqual(selected["candidate"], scores.loc[scores.selected, "candidate"].iloc[0])

    def test_insufficient_validation_uses_predeclared_default_without_tuning(self):
        data, archive, spec, study, _ = fixture()
        spec = {**spec, "inner_validation": {**spec["inner_validation"], "minimum_validation_months": 999}}
        features, get_training = training_context(data, archive, spec)
        selected, reason, scores, _, predictions = choose_candidate(features, get_training(2000), 2000, get_training, spec, study)
        self.assertEqual(selected["candidate"], "production_C0.001_expanding")
        self.assertIn("fallback", reason)
        self.assertTrue(predictions.empty)
        self.assertFalse(scores.eligible.any())
        self.assertTrue(scores.mean_validation_brier.isna().all())

    def test_ties_prefer_small_feature_set_strong_penalty_and_expanding(self):
        data, archive, spec, study, _ = fixture()
        features, get_training = training_context(data, archive, spec)
        def uniform(training, validation, selected, c, config):
            return np.full((len(validation), 3), 1 / 3), pd.DataFrame(), pd.DataFrame()
        with patch("proquest_macro_benchmark.fit_regression", side_effect=uniform):
            selected, _, _, _, _ = choose_candidate(features, get_training(2000), 2000, get_training, spec, study)
        self.assertEqual(selected["candidate"], "production_C0.001_expanding")

    def test_recent_window_does_not_keep_an_old_class_for_convenience(self):
        training = pd.DataFrame({"origin": pd.period_range("1980-01", periods=150, freq="M"),
                                 "training_target": ["fall"] * 30 + ["flat", "rise"] * 60})
        selected = windowed(training.sample(frac=1, random_state=1), {"window": "recent_120"})
        self.assertEqual(len(selected), 120)
        self.assertEqual(selected.origin.min(), training.origin.iloc[30])
        self.assertFalse(trainable(selected, 60))
        self.assertTrue(trainable(training, 60))

    def test_combined_model_uses_macro_selected_training_window_and_scaling(self):
        data, archive, spec, study, support = fixture()
        result = fit_study(data, support, archive, spec, study)
        training = data.set_index("origin").loc[result["selected_training_rows"].origin]
        params = result["preprocessing"]
        for model, group in params.groupby("model"):
            means = training[group.feature].mean()
            np.testing.assert_allclose(group["mean"], means, atol=1e-12)
        macro = params[params.model == "macro_only"].set_index("feature")
        combined = params[params.model == "macro_plus_press"].set_index("feature")
        np.testing.assert_allclose(macro[["mean", "scale"]], combined.loc[macro.index, ["mean", "scale"]])
        self.assertEqual(set(combined.index) - set(macro.index), set(FEATURES))
        self.assertEqual(result["predictions"].origin.tolist(), support.tolist())

    def test_cpi_is_only_the_fixed_extra_macro_feature(self):
        _, _, spec, study, _ = fixture()
        choices = candidates(spec, {**study, "include_cpi": True})
        self.assertEqual(len(choices), 12)
        for choice in choices:
            self.assertEqual(choice["features"][-1], "cpi_change_12m")
            self.assertNotIn("unemployment_change_12m", choice["features"])
            self.assertTrue(set(choice["features"]).isdisjoint(FEATURES))


if __name__ == "__main__":
    unittest.main()
