"""Known-answer checks for the frozen-forecast diagnostic arithmetic."""
from pathlib import Path
import sys
import unittest

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from proquest_macro_diagnostics import (CLASSES, MODELS, error_tables, fit_diagnostics,
                                        month_errors, reconstructed_probabilities,
                                        revision_tables, score_arrays)


def coefficients():
    return pd.DataFrame([{"refit_year": 2000, "model": model, "class": label,
                          "feature": feature, "coefficient": value}
                         for model in ("macro_only", "macro_plus_press")
                         for label, slope in zip(CLASSES, [-1., 0., 1.])
                         for feature, value in [("intercept", 0.), ("x", slope)]])


class DiagnosticChecks(unittest.TestCase):
    def test_probability_scores_known_answers(self):
        brier, logloss = score_arrays(np.eye(3), CLASSES)
        np.testing.assert_allclose(brier, 0.)
        np.testing.assert_allclose(logloss, 0.)
        brier, logloss = score_arrays(np.ones((3, 3)) / 3, CLASSES)
        np.testing.assert_allclose(brier, 2 / 3)
        np.testing.assert_allclose(logloss, np.log(3))

    def test_class_and_period_contributions_add_to_overall_gap(self):
        data = pd.DataFrame({"origin": ["2000-01", "2000-02", "2005-01"],
                             "target": list(CLASSES), "refit_year": [2000, 2000, 2005],
                             "recent_base_rate_brier": 2 / 3, "recent_base_rate_log_loss": np.log(3)})
        for model in MODELS:
            for i, label in enumerate(CLASSES):
                data[f"{model}_{label}"] = 1 / 3 if model == "recent_base_rate" else [.05, .05, .9][i]
        errors = month_errors(data, "fixture")
        groups, _, components = error_tables(errors)
        for model in MODELS:
            frame = groups[groups.model == model]
            overall = frame[frame.grouping == "overall"].iloc[0]
            for group in ["actual_class", "five_year"]:
                sub = frame[frame.grouping == group]
                self.assertAlmostEqual(sub.brier_gap_contribution.sum(), overall.excess_brier)
                self.assertAlmostEqual(sub.log_loss_gap_contribution.sum(), overall.excess_log_loss)
            self.assertAlmostEqual(components[components.model == model].brier_component.sum(), overall.brier)

    def test_confidence_uses_predicted_class_and_includes_boundary(self):
        data = pd.DataFrame({"origin": ["2000-01", "2000-02"], "target": ["rise", "fall"],
                             "refit_year": 2000, "recent_base_rate_brier": 2 / 3,
                             "recent_base_rate_log_loss": np.log(3)})
        for model in MODELS:
            for label, p in zip(CLASSES, [.05, .05, .9]):
                data[f"{model}_{label}"] = p
        groups, confidence, _ = error_tables(month_errors(data, "fixture"))
        high = groups.query("grouping == 'confidence'")
        np.testing.assert_allclose(high.n_months, 2)
        np.testing.assert_allclose(high.mean_confidence, .9)
        np.testing.assert_allclose(high.accuracy, .5)
        self.assertEqual(set(confidence.bin), {">=90%"})

    def test_revision_summary_counts_first_use_once_and_excludes_unused(self):
        audit = pd.DataFrame({"origin": ["1990-01", "1990-01", "1990-02", "1990-03"],
                              "refit_year": [2001, 2000, 2000, 2000], "used": [True, True, True, False],
                              "training_target": ["flat", "rise", "flat", "fall"],
                              "training_change_percent": [1., 3., 0., -5.]})
        full = pd.DataFrame({"origin": ["1990-01", "1990-02", "1990-03"], "target": ["flat", "flat", "rise"],
                             "change_percent": [1., 0., 5.]})
        rows, first, summary, transitions = revision_tables(audit, full, "fixture")
        self.assertEqual(len(rows), 3)
        self.assertEqual(len(first), 2)
        self.assertEqual(first.set_index("origin").loc["1990-01", "training_target"], "rise")
        self.assertEqual(summary.query("basis == 'unique_origin'").changed_share.iloc[0], .5)
        self.assertEqual(transitions.n_origins.sum(), 2)
        self.assertAlmostEqual(summary.query("basis == 'unique_origin'").mean_absolute_growth_revision_pp.iloc[0], 1.)

    def test_saved_coefficients_reconstruct_softmax_with_feature_scaling(self):
        frame = pd.DataFrame({"x": [10., 12.]})
        params = pd.DataFrame({"feature": ["x"], "mean": [10.], "scale": [2.]})
        coef = coefficients().query("model == 'macro_only'")
        p, z, _, _ = reconstructed_probabilities(frame, params, coef)
        np.testing.assert_allclose(z[:, 0], [0., 1.])
        np.testing.assert_allclose(p[0], np.ones(3) / 3)
        expected = np.exp([-1., 0., 1.]); expected /= expected.sum()
        np.testing.assert_allclose(p[1], expected)

    def test_logit_contributions_and_training_labels_have_separate_roles(self):
        full = pd.DataFrame({"origin": ["1999-01", "1999-02"], "x": [-1., 1.], "target": ["rise", "fall"]})
        audit = pd.DataFrame({"origin": full.origin, "refit_year": 2000, "used": True,
                              "training_target": ["fall", "rise"]})
        params = pd.DataFrame([{"refit_year": 2000, "model": model, "feature": "x", "mean": 0., "scale": 1.}
                               for model in ("macro_only", "macro_plus_press")])
        coefs = coefficients()
        predicted = pd.DataFrame({"origin": ["2000-01"], "refit_year": [2000], "target": ["fall"], "x": [2.]})
        for model in ("macro_only", "macro_plus_press"):
            p, _, _, _ = reconstructed_probabilities(predicted, params[params.model == model], coefs[coefs.model == model])
            for i, label in enumerate(CLASSES):
                predicted[f"{model}_{label}"] = p[:, i]
        fit, shift, contributions = fit_diagnostics(predicted, audit, full, params, coefs, "fixture")
        self.assertTrue((fit.train_revised_log_loss > fit.train_vintage_log_loss).all())
        self.assertTrue(shift.outside_training_range.all())
        margin = contributions.groupby(["model", "origin"]).logit_margin_contribution.sum()
        np.testing.assert_allclose(margin, 4.)
        self.assertAlmostEqual(np.log(predicted.macro_only_rise.iloc[0] / predicted.macro_only_fall.iloc[0]), 4.)


if __name__ == "__main__":
    unittest.main()
