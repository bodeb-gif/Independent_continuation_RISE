"""Checks for joins, confidence and exact article-weighted loss attribution."""
from pathlib import Path
import sys
import unittest

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from proquest_rnn_audit import ARMS, attach_metadata, comparison_rows, selected_epoch, summarize


class AuditTests(unittest.TestCase):
    def test_subgroup_contributions_preserve_multi_topic_article_weights(self):
        frame = pd.DataFrame({"hit": [0, 1, 1], "page_id": ["a", "a", "b"],
                              "topic": ["prices", "markets", "prices"], "weight": [.5, .5, 1.]})
        for arm in ARMS:
            frame[f"gru_ensemble__{arm}"] = [.2, .6, .8] if arm == "baseline" else [.1, .5, .6]
        table = comparison_rows(frame, "topic", 2.)
        base = summarize(frame, "gru_ensemble__baseline", frame.weight.to_numpy())
        other = summarize(frame, "gru_ensemble__political", frame.weight.to_numpy())
        self.assertAlmostEqual(table.query("arm == 'political'").contribution_to_total_brier_increase.sum(), other["brier"] - base["brier"])
        self.assertEqual(table.query("arm == 'baseline' and group == 'prices'").article_mass.iloc[0], 1.5)

    def test_confidence_counts_both_predicted_classes(self):
        frame = pd.DataFrame({"hit": [1, 0, 0, 1], "p": [.95, .05, .95, .05], "page_id": list("abcd")})
        result = summarize(frame, "p", np.ones(4))
        self.assertEqual(result["high_confidence_claims"], 4)
        self.assertEqual(result["high_confidence_wrong_mass_share"], .5)
        self.assertEqual(result["high_confidence_accuracy"], .5)

    def test_validation_epoch_rule_ignores_train_loss_and_tiny_improvements(self):
        history = pd.DataFrame({"epoch": [3, 1, 2], "validation_weighted_loss": [.49995, .6, .5],
                                "train_weighted_loss": [.1, .3, .2]})
        self.assertEqual(selected_epoch(history), 2)

    def test_source_local_join_rejects_duplicates_and_different_outcomes(self):
        pred = pd.DataFrame({"record_id": ["verified/file:1"], "page_id": ["a"], "date": ["2000-01-01"], "hit": [1]})
        score = pred.assign(topic="prices", paper="paper", horizon_basis="stated", horizon_used=6,
                            predicted_norm=1, realized=1, basis="CPI", scorable=True)
        self.assertEqual(len(attach_metadata(pred, score)), 1)
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            attach_metadata(pred, pd.concat([score, score]))
        with self.assertRaisesRegex(ValueError, "mismatch"):
            attach_metadata(pred, score.assign(hit=0))
        with self.assertRaisesRegex(ValueError, "without a score"):
            attach_metadata(pred.assign(record_id="missing"), score)


if __name__ == "__main__":
    unittest.main()
