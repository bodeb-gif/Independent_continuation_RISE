"""Known-answer checks for the LOC validation reviewer and recall packet."""

import json
from pathlib import Path
from types import SimpleNamespace
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from loc_validation import build_claim_review, locate_quote, match_claims, sample_recall, score_recall, write_jsonl


class LOCValidationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.pages = self.base / "pages.jsonl"
        self.claims = self.base / "claims.jsonl"
        write_jsonl(self.pages, [
            {"page_id": "p1", "date": "1900-01-01", "publisher": "Paper A",
             "ocr_text": "The economy will improve next year. Jobs may decline."},
            {"page_id": "p2", "date": "1910-01-01", "publisher": "Paper B",
             "ocr_text": "Today's weather is sunny. There are no forecasts here."},
            {"page_id": "p3", "date": "1920-01-01", "publisher": "Paper C",
             "ocr_text": "Exports will increase greatly next year."},
        ])
        write_jsonl(self.claims, [
            {"page_id": "p1", "date": "1900-01-01", "publisher": "Paper A",
             "quote": "The economy will improve next year.", "topic": "general_business", "direction": "improve"},
            {"page_id": "p3", "date": "1920-01-01", "publisher": "Paper C",
             "quote": "Exports will increase greatly next year.", "direction": "improve"},
            {"page_id": "outside", "quote": "Forecast outside supplied pages", "direction": "worsen"},
        ])

    def test_quote_locator_is_explicit_about_exact_partial_and_missing(self):
        text = "Business\nconditions, will improve next year!"
        span, kind = locate_quote(text, "Business conditions will improve next year")
        self.assertEqual(kind, "exact")
        self.assertEqual(text[span[0]:span[1]], text[:-1])
        span, kind = locate_quote(text, "Business conditions will improve next year in the whole country")
        self.assertEqual(kind, "partial")
        self.assertIn("Business", text[span[0]:span[1]])
        self.assertEqual(locate_quote(text, "unrelated forecast of prices"), (None, "none"))

    def test_review_separates_hidden_machine_labels_from_embedded_ocr(self):
        output = self.base / "review.html"
        args = SimpleNamespace(pages=[self.pages], claims=self.claims, n=0, seed=7,
                               reviewer="bode", out=output)
        build_claim_review(args)
        html = output.read_text()
        self.assertIn("The economy will improve next year", html)
        self.assertIn("Paper A", html)
        self.assertNotIn("machine_labels", html)
        manifest = [json.loads(line) for line in output.with_suffix(".manifest.jsonl").read_text().splitlines()]
        self.assertEqual(len(manifest), 2)
        self.assertTrue(all(row["selection_probability_among_matched_claims"] == 1 for row in manifest))
        self.assertEqual(manifest[0]["machine_labels"]["direction"], "improve")
        self.assertEqual(len({row["unit_id"] for row in manifest}), 2)

    def test_recall_packet_includes_zero_claim_page_and_no_predictions(self):
        output = self.base / "packet.jsonl"
        args = SimpleNamespace(pages=[self.pages], n=3, seed=5,
                               population_label="synthetic test", out=output)
        sample_recall(args)
        rows = [json.loads(line) for line in output.read_text().splitlines()]
        self.assertEqual({r["page_id"] for r in rows}, {"p1", "p2", "p3"})
        self.assertNotIn("claims", rows[0])
        manifest = json.loads(output.with_suffix(".manifest.json").read_text())
        self.assertEqual(manifest["selection_probability_within_supplied_pages"], 1)
        self.assertFalse(manifest["model_predictions_in_packet"])

    def test_one_to_one_matching_and_complete_reference_gate(self):
        reference = [{"quote": "The economy will improve next year."},
                     {"quote": "Markets will fall rapidly next year."}]
        extracted = [{"quote": "economy will improve next year"},
                     {"quote": "economy will improve next year"}]
        pairs, missed, extra = match_claims(reference, extracted)
        self.assertEqual((len(pairs), len(missed), len(extra)), (1, 1, 1))

        packet = self.base / "packet.jsonl"
        write_jsonl(packet, [{"page_id": "p1", "date": "1900-01-01", "ocr_text": "text"},
                             {"page_id": "p2", "date": "1900-01-02", "ocr_text": "text"}])
        labels = self.base / "reference.jsonl"
        write_jsonl(labels, [{"page_id": "p1", "claims": reference}])
        args = SimpleNamespace(packet=packet, reference=labels, claims=self.claims,
                               reference_kind="model", threshold=.7, out=self.base / "result.json")
        with self.assertRaisesRegex(ValueError, "missing 1 sampled pages"):
            score_recall(args)
        write_jsonl(labels, [{"page_id": "p1", "claims": reference},
                             {"page_id": "p2", "claims": []}])
        score_recall(args)
        result = json.loads(args.out.read_text())
        self.assertEqual(result["summary"]["matched"], 1)
        self.assertEqual(result["summary"]["reference_only"], 1)
        self.assertEqual(result["summary"]["coverage_relative_to_reference"], .5)
        self.assertEqual(result["summary"]["reference_kind"], "model")


if __name__ == "__main__":
    unittest.main()
