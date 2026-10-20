"""Prepare a separate modern evaluation; reconcile exports without scoring them.

This deliberately does not change the active 1900–2010 analysis loader.
Manifest paths are relative to an explicit export directory. No label deduplication.
"""
import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/scored/proquest/modern_readiness"
ANNUAL = re.compile(r"pred_proquest_economy_(\d{4})\.export\.jsonl")
SHA = re.compile(r"[0-9a-f]{64}")
COUNTS = ("retrieved_articles", "text_available_articles", "missing_text_articles",
          "extracted_articles", "extraction_failed_articles", "extraction_pending_articles",
          "raw_candidates", "accepted_claims", "rejected_claims", "verification_failed_claims",
          "verification_pending_claims", "export_records", "export_articles", "empty_records")


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def month_number(value):
    parsed = date.fromisoformat(value + "-01" if len(value) == 7 else value)
    return parsed.year * 12 + parsed.month - 1


def maturity_status(printed, horizon, as_of, reference_months):
    """Eligibility only; reference_months must be the target's actual observed months.

    Endpoint + three months must strictly precede as_of month. Full monthly
    reference coverage is deliberately conservative. No outcome is imputed.
    """
    start, now = month_number(printed), month_number(as_of)
    if type(horizon) is not int or not 1 <= horizon <= 24:
        return "unsupported_horizon"
    if date.fromisoformat(printed) > date.fromisoformat(as_of):
        return "future_publication"
    end = start + horizon
    if end + 3 >= now:
        return "unmatured"
    observed = {month_number(m) for m in reference_months}
    if not set(range(start, end + 1)).issubset(observed):
        return "reference_gap"
    return "eligible_for_deterministic_scoring"


def validate_manifest(manifest, export_directory):
    """Fail closed on incomplete lineage/counts; never infer success from empty rows."""
    def require(condition, message):
        if not condition:
            raise ValueError(message)

    require(manifest.get("schema_version") == 1, "Manifest schema must be 1")
    require(manifest.get("source") == "proquest", "Source must be ProQuest")
    require(manifest.get("export_set") == "verified", "Use verified modern exports")
    for key in ("run_id", "completed_at", "query", "coverage", "retrieval_limits", "extraction_model",
                "verification_model", "decoding_and_chunking", "processing_log_sha256"):
        require(isinstance(manifest.get(key), str) and manifest[key].strip(), f"Missing {key}")
    for key in ("extraction_prompt_sha256", "verification_prompt_sha256", "processing_log_sha256"):
        require(bool(SHA.fullmatch(manifest.get(key, ""))), f"Invalid {key}")
    exposure = manifest.get("prior_exposure", {})
    require(exposure.get("status") in ("none_reported", "exposed"), "Prior exposure must be documented")
    require(bool(exposure.get("statement")) and bool(exposure.get("recorded_at")), "Missing exposure statement/date")
    years = manifest.get("expected_years")
    require(isinstance(years, list) and bool(years), "Missing expected years")
    require(all(type(y) is int and 2011 <= y <= 9999 for y in years), "Only modern years >=2011")
    require(len(years) == len(set(years)), "Duplicate expected years")
    entries = manifest.get("files", [])
    require(isinstance(entries, list) and len(entries) == len(years), "Annual file count mismatch")
    root = Path(export_directory).resolve()
    seen = set(); summaries = []
    for entry in entries:
        year = entry.get("year")
        require(year in years and year not in seen, "Unexpected or duplicate file year")
        seen.add(year)
        name = entry.get("path", "")
        match = ANNUAL.fullmatch(name)
        require(match is not None and int(match[1]) == year, "Annual filename/year mismatch")
        path = (root / name).resolve()
        require(path.parent == root and path.is_file(), f"Missing or external export: {name}")
        require(entry.get("verification_status") == "complete", "Verification is not complete")
        require(entry.get("export_status") == "complete", "Export is not complete")
        require(digest(path) == entry.get("sha256"), f"Export hash mismatch: {name}")
        c = entry.get("counts", {})
        require(all(type(c.get(k)) is int and c[k] >= 0 for k in COUNTS), "Missing/invalid stage counts")
        require(c["retrieved_articles"] == c["text_available_articles"] + c["missing_text_articles"], "Text count flow mismatch")
        require(c["text_available_articles"] == c["extracted_articles"] + c["extraction_failed_articles"] + c["extraction_pending_articles"], "Extraction count flow mismatch")
        require(c["raw_candidates"] == sum(c[k] for k in ("accepted_claims", "rejected_claims", "verification_failed_claims", "verification_pending_claims")), "Claim count flow mismatch")
        require(not any(c[k] for k in ("extraction_pending_articles", "verification_pending_claims", "verification_failed_claims")), "Unresolved processing counts")
        if c["missing_text_articles"] or c["extraction_failed_articles"]:
            require(bool(entry.get("terminal_exclusions")), "Document terminal article exclusions")
        records = claims = empty = 0
        pages = set(); empty_pages = set(); claim_pages = set()
        for line_number, line in enumerate(path.read_text().splitlines(), 1):
            if not line.strip():
                continue
            row = json.loads(line)
            require(row.get("schema_version") == 2, f"Export schema at {name}:{line_number}")
            require(bool(row.get("page_id")), f"Missing article at {name}:{line_number}")
            page = str(row["page_id"]); pages.add(page); records += 1
            if row.get("no_predictions") is True:
                # Legacy empty rows can omit source/date. Counts still need VM lineage.
                require(row.get("source", "proquest") == "proquest", "Non-ProQuest empty record")
                if row.get("date"):
                    require(date.fromisoformat(row["date"]).year == year, "Empty date outside shard")
                empty += 1; empty_pages.add(page)
            else:
                require(row.get("source") == "proquest", "Non-ProQuest claim")
                require(date.fromisoformat(row["date"]).year == year, "Claim date outside shard")
                require(bool(row.get("verify_reason")), "Claim lacks verification marker")
                claims += 1; claim_pages.add(page)
        actual = {"export_records": records, "accepted_claims": claims,
                  "export_articles": len(pages), "empty_records": empty}
        require(all(c[k] == v for k, v in actual.items()), f"Export count mismatch: {name}")
        require(c["export_articles"] <= c["extracted_articles"], "Exports exceed extracted articles")
        require(bool(entry.get("nonexported_article_explanation")) or c["export_articles"] == c["extracted_articles"], "Explain extracted articles absent from export")
        summaries.append({"year": year, **actual, "articles_with_claims_and_empty_rows": len(empty_pages & claim_pages),
                          "sha256": entry["sha256"]})
    actual_files = {p.name for p in root.glob("*.jsonl") if ANNUAL.fullmatch(p.name)}
    require(actual_files == {e["path"] for e in entries}, "Export directory has unmanifested annual shards")
    return {"intake": "reconciled", "source_validation": "not_performed", "scoring": "not_performed",
            "fresh_holdout_claim": False, "prior_exposure": exposure, "files": summaries,
            "next_gate": "Activate separate modern scope; freeze data/reference hashes and verify print-time features before scoring"}


def prepare():
    OUT.mkdir(parents=True, exist_ok=True)
    spec = ROOT / "docs/publication/MODERN_EVALUATION.md"
    paths = [spec, Path(__file__), ROOT / "src/proquest_rnn.py", ROOT / "src/proquest_polarization.py",
             ROOT / "src/proquest_polarization_models.py", ROOT / "src/proquest_panel.py",
             ROOT / "src/proquest_descriptive.py", ROOT / "src/score_predictions.py",
             ROOT / "src/truth_data.py", ROOT / "src/proquest_information.py",
             ROOT / "src/proquest_macro_information.py", ROOT / "src/proquest_macro_benchmark.py",
             ROOT / "src/proquest_vintages.py"]
    saved = ROOT / "data/scored/proquest/polarization"
    expected = json.loads((saved / "output_manifest.json").read_text())["outputs_sha256"]
    expected.update(json.loads((saved / "claims_summary.json").read_text())["inputs_sha256"])
    for name, sha in expected.items():
        if digest(ROOT / name) != sha:
            raise ValueError(f"Saved historical input/output changed: {name}")
    paths += [saved / p for p in ("evaluation_spec.json", "claims_summary.json", "output_manifest.json",
                                  "claims/preprocessing_and_baselines.joblib", "claims/added_preprocessing.csv")]
    paths += [saved / f"claims/gru_{arm}_{seed}.pt" for arm in ("baseline", "political", "forecast", "both") for seed in (11,29,47)]
    frozen = {"prepared_date": "2026-10-19", "status": "Procedure and saved claim models frozen; modern data and exposure pending",
              "files_sha256": {str(p.relative_to(ROOT)): digest(p) for p in paths}}
    target = OUT / "model_freeze.json"
    if target.exists() and json.loads(target.read_text()) != frozen:
        raise ValueError("Freeze differs: retain the old freeze and document a dated amendment")
    target.write_text(json.dumps(frozen, indent=2) + "\n")
    template = {"schema_version": 1, "source": "proquest", "export_set": "verified", "expected_years": [],
                **{k: None for k in ("run_id", "completed_at", "query", "coverage", "retrieval_limits", "extraction_model", "verification_model", "decoding_and_chunking", "extraction_prompt_sha256", "verification_prompt_sha256", "processing_log_sha256")},
                "prior_exposure": {"status": "unknown", "statement": None, "recorded_at": None},
                "files": [], "file_entry_template": {"year": None, "path": None, "sha256": None,
                "verification_status": None, "export_status": None, "counts": {k: None for k in COUNTS},
                "terminal_exclusions": None, "nonexported_article_explanation": None}}
    template_path = OUT / "manifest_template.json"
    if not template_path.exists():
        template_path.write_text(json.dumps(template, indent=2) + "\n")
    print(target.relative_to(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--exports", type=Path)
    args = parser.parse_args()
    if args.prepare:
        if args.manifest or args.exports:
            parser.error("Use --prepare separately from intake")
        prepare()
    elif args.manifest and args.exports:
        print(json.dumps(validate_manifest(json.loads(args.manifest.read_text()), args.exports), indent=2))
    else:
        parser.error("Use --prepare, or --manifest FILE --exports DIRECTORY")


if __name__ == "__main__":
    main()
