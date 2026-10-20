"""Assemble a publication evidence packet from saved ProQuest results, offline.

Run from the repository root. Never fits models or changes source exports.
Review responses belong in a separate file: generated files may be rebuilt.
"""
import csv
import gzip
import hashlib
import json
from pathlib import Path
import random

from analyze_proquest import annual_files

ROOT = Path(__file__).resolve().parents[1]
BASE = Path("data/scored/proquest")
OUT = BASE / "publication"
SEED = 20261014


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def check_hashes(root, expected):
    for name, digest in expected.items():
        if sha256(root / name) != digest:
            raise ValueError(f"Saved evidence is stale: {name}")


def read_csv(path):
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8", newline="") as source:
        return list(csv.DictReader(source))


def write_csv(path, rows):
    with path.open("w", encoding="utf-8", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def pilot_sample(rows, n=12, seed=SEED):
    eligible = sorted((r for r in rows if r["scorable"] == "True"),
                      key=lambda r: r["record_id"])
    if len({r["record_id"] for r in rows}) != len(rows):
        raise ValueError("Duplicate source-local record addresses")
    return random.Random(seed).sample(eligible, n), len(eligible)


def pilot_records(root, sample, population, source_hashes):
    """Separate retrieval sheet from labels; neither includes realized outcomes."""
    retrieval, labels = [], []
    by_year = {}
    for row in sample:
        year, line = map(int, row["record_id"].split(":"))
        by_year.setdefault(year, {})[line] = row
    for year, wanted in sorted(by_year.items()):
        name = f"data/proquest/verified/pred_proquest_economy_{year}.export.jsonl"
        with (root / name).open(encoding="utf-8") as source:
            for line, text in enumerate(source, 1):
                if line not in wanted:
                    continue
                original, scored = json.loads(text), wanted[line]
                for field in ("page_id", "date", "topic", "direction", "scope",
                              "horizon_months", "horizon_hint"):
                    if str(original.get(field)) != scored[field]:
                        raise ValueError(f"Source/scored mismatch: {name}:{line}:{field}")
                address = f"verified:{year}:{line}"
                retrieval.append({"audit_id": address, "source_path": name,
                                  "source_sha256": source_hashes[name],
                                  "source_line": line, "page_id": original["page_id"],
                                  "date": original["date"],
                                  "publisher": scored["publisher_original"],
                                  "pilot_inclusion_probability": len(sample) / population,
                                  "source_locator": "", "mapping_status": "pending"})
                labels.append({"audit_id": address, **{k: original.get(k) for k in
                              ("topic", "direction", "scope", "confidence", "voice",
                               "horizon_months", "horizon_hint")},
                               "legacy_benchmark": scored["basis"],
                               "legacy_horizon_used": scored["horizon_used"]})
    if len(retrieval) != len(sample):
        raise ValueError("Missing pilot source record")
    return retrieval, labels


def build(root=ROOT):
    inputs = {}

    def load(name):
        path = BASE / name
        inputs[str(path)] = sha256(root / path)
        return (json.loads((root / path).read_text()) if path.suffix == ".json"
                else read_csv(root / path))

    robust = load("robustness/summary.json")
    macro = load("macro_benchmark/summary.json")
    desc = load("descriptive/summary.json")
    inv = load("inventory.json")
    for source in ("raw", "verified"):
        paths = annual_files(root / "data/proquest" / source)
        if {str(p.relative_to(root)) for p in paths} != {
            p for p in robust["sources"] if f"/{source}/" in p
        }:
            raise ValueError("Saved source manifest does not match annual inputs")
    expected = dict(robust["sources"])
    for group in (robust["code_sha256"], macro["inputs_sha256"], macro["code_sha256"]):
        for path, digest in group.items():
            if path in expected and expected[path] != digest:
                raise ValueError(f"Conflicting provenance: {path}")
            expected[path] = digest
    expected[str(BASE / "macro_benchmark/evaluation_spec.json")] = macro["spec_sha256"]
    for entry in robust["reference"].values():
        expected[entry["file"]] = entry["sha256"]
    check_hashes(root, expected)
    inputs.update(expected)

    scored = load("descriptive/scored_claims.csv.gz")
    sample, population = pilot_sample(scored)
    if len(scored) != desc["verified_claims"] or population != desc["scorable_claims"]:
        raise ValueError("Descriptive row count mismatch")
    corpus = load("robustness/corpus.csv")
    for row in corpus:
        for field in ("claims", "represented_articles"):
            if int(row[field]) != inv[row["source_set"]][field]:
                raise ValueError(f"Corpus count mismatch: {row['source_set']} {field}")
    verified = next(r for r in corpus if r["source_set"] == "verified")
    if int(verified["scorable_claims"]) != population:
        raise ValueError("Scorable count mismatch")
    topics = [r for r in load("robustness/outcomes_by_topic.csv") if r["source_set"] == "verified"]
    monthly = [r for r in load("macro_benchmark/core/metrics.csv")
               if r["grouping"] in {"overall", "sensitivity"}]
    intervals = load("macro_benchmark/core/paired_intervals.csv")
    interval = next(r for r in intervals if r["model"] == "macro_plus_press"
                    and r["baseline"] == "macro_only" and r["metric"] == "brier"
                    and r["block_years"] == "5")
    retrieval, labels = pilot_records(root, sample, population, robust["sources"])
    out = root / OUT
    out.mkdir(parents=True, exist_ok=True)
    products = {"corpus_flow.csv": corpus, "legacy_verified_topics.csv": topics,
                "monthly_core.csv": monthly, "pilot_retrieval.csv": retrieval,
                "pilot_machine_labels.csv": labels}
    for name, rows in products.items():
        write_csv(out / name, rows)
    evidence = {"status": "Exploratory saved results; human validation pending",
                "verified_claims": len(scored), "verified_scored_claims": population,
                "pooled_legacy_hit_rate": desc["hit_rate"],
                "pooled_legacy_baseline": desc["fixed_baseline"],
                "equal_article_comparison": robust["comparisons"][0],
                "monthly_core_brier_interval": interval,
                "pilot": {"seed": SEED, "n": len(sample), "population_n": population,
                          "design": "Simple random sample without replacement of scored verified records",
                          "purpose": "Source recovery and rubric development only",
                          "main_audit": "Not drawn; freeze after pilot; exclude pilot records",
                          "source_mapping": "Pending VM lineage/context; do not guess from labels"}}
    (out / "evidence.json").write_text(json.dumps(evidence, indent=2) + "\n")
    products["evidence.json"] = None
    for path in [Path("src/proquest_publication.py"), Path("data/proquest/source_manifest.json"),
                 Path("docs/publication/ANALYSIS_SPEC.md")]:
        inputs[str(path)] = sha256(root / path)
    manifest = {"package_version": 1, "prepared_date": "2026-10-14",
                "command": "python src/proquest_publication.py", "inputs_sha256": inputs,
                "outputs_sha256": {str(OUT / name): sha256(out / name) for name in products},
                "limitations": ["Saved output hashes anchor this packet; no model refit was performed.",
                                "Import manifest is not a VM processing-completeness manifest.",
                                "No completed human judgments are generated."]}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Publication packet: {out}; {population:,} scored claims; {len(sample)} pilot locators")


if __name__ == "__main__":
    build()
