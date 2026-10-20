"""Synthetic intake fixtures: no real modern claims or source review."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from proquest_modern_intake import COUNTS, digest, maturity_status, validate_manifest


class IntakeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / "pred_proquest_economy_2011.export.jsonl"
        # Identical stripped labels are retained as two distinct exported rows.
        row = dict(schema_version=2, page_id="a", source="proquest", date="2011-03-01", verify_reason="synthetic")
        self.path.write_text(json.dumps(row) + "\n" + json.dumps(row) + "\n")
        counts = dict.fromkeys(COUNTS, 0)
        counts.update(retrieved_articles=1, text_available_articles=1, extracted_articles=1,
                      raw_candidates=3, accepted_claims=2, rejected_claims=1, export_records=2, export_articles=1)
        self.manifest = dict(schema_version=1, source="proquest", export_set="verified", expected_years=[2011],
                             prior_exposure=dict(status="none_reported", statement="Synthetic fixture", recorded_at="2026-10-19"),
                             files=[dict(year=2011, path=self.path.name, sha256=digest(self.path),
                                         verification_status="complete", export_status="complete", counts=counts)])
        for key in ("run_id", "completed_at", "query", "coverage", "retrieval_limits", "extraction_model", "verification_model", "decoding_and_chunking"):
            self.manifest[key] = "synthetic"
        for key in ("extraction_prompt_sha256", "verification_prompt_sha256", "processing_log_sha256"):
            self.manifest[key] = "a" * 64

    def test_reconciles_without_dedup_or_claiming_holdout(self):
        result = validate_manifest(self.manifest, self.root)
        self.assertEqual(result["files"][0]["accepted_claims"], 2)
        self.assertFalse(result["fresh_holdout_claim"])
        self.assertEqual(result["scoring"], "not_performed")

    def test_requires_exposure_and_complete_count_flow(self):
        bad = copy.deepcopy(self.manifest)
        bad["prior_exposure"]["status"] = "unknown"
        with self.assertRaisesRegex(ValueError, "exposure"):
            validate_manifest(bad, self.root)
        bad = copy.deepcopy(self.manifest)
        bad["files"][0]["counts"]["verification_pending_claims"] = 1
        bad["files"][0]["counts"]["rejected_claims"] = 0
        with self.assertRaisesRegex(ValueError, "Unresolved"):
            validate_manifest(bad, self.root)
        bad["files"][0]["counts"]["raw_candidates"] = 4
        with self.assertRaisesRegex(ValueError, "flow mismatch"):
            validate_manifest(bad, self.root)

    def test_rejects_old_or_duplicate_years_and_extra_shards(self):
        for years in ([2010], [2011, 2011]):
            bad = copy.deepcopy(self.manifest); bad["expected_years"] = years
            with self.assertRaises(ValueError):
                validate_manifest(bad, self.root)
        (self.root / "pred_proquest_economy_2012.export.jsonl").write_text("")
        with self.assertRaisesRegex(ValueError, "unmanifested"):
            validate_manifest(self.manifest, self.root)

    def test_detects_tampering_and_wrong_date_even_with_new_hash(self):
        self.path.write_text(self.path.read_text().replace("2011-03", "2012-03"))
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            validate_manifest(self.manifest, self.root)
        self.manifest["files"][0]["sha256"] = digest(self.path)
        with self.assertRaisesRegex(ValueError, "date outside"):
            validate_manifest(self.manifest, self.root)

    def test_empty_exports_do_not_prove_extraction_success(self):
        self.path.write_text(json.dumps(dict(schema_version=2, page_id="a", no_predictions=True)) + "\n")
        entry = self.manifest["files"][0]; entry["sha256"] = digest(self.path)
        entry["counts"].update(raw_candidates=0, accepted_claims=0, rejected_claims=0, export_records=1, empty_records=1)
        self.assertEqual(validate_manifest(self.manifest, self.root)["files"][0]["empty_records"], 1)
        entry["counts"]["extracted_articles"] = 0
        entry["counts"]["extraction_pending_articles"] = 1
        with self.assertRaisesRegex(ValueError, "Unresolved"):
            validate_manifest(self.manifest, self.root)

    def test_maturity_strict_boundary_reference_gaps_and_invalid_horizons(self):
        references = [f"2025-{m:02d}" for m in range(1, 8)]
        self.assertEqual(maturity_status("2025-01-10", 6, "2025-10-19", references), "unmatured")
        self.assertEqual(maturity_status("2025-01-10", 6, "2025-11-01", references), "eligible_for_deterministic_scoring")
        self.assertEqual(maturity_status("2025-01-10", 6, "2025-11-01", references[:-1]), "reference_gap")
        self.assertEqual(maturity_status("2025-01-10", 6, "2025-11-01", references[:2] + references[3:]), "reference_gap")
        for horizon in (True, 0, 25, "6", None):
            self.assertEqual(maturity_status("2025-01-10", horizon, "2025-11-01", references), "unsupported_horizon")
        self.assertEqual(maturity_status("2025-11-10", 6, "2025-11-01", references), "future_publication")


if __name__ == "__main__":
    unittest.main()
