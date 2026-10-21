"""Freeze the requested 100-claim ProQuest audit; never create human judgments.

The main frame follows REVIEW_PROTOCOL.md: scored verified annual records minus
the twelve pilot addresses. Source review is performed separately inside TDM.
"""
import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import random

from analyze_proquest import annual_files
from proquest_publication import read_csv, pilot_records, sha256, write_csv

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/scored/proquest/source_review_main_v1"
SEED = 20261019


def select(rows, pilot_ids, n=100, seed=SEED):
    ids = [r["record_id"] for r in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate record addresses")
    eligible = {r["record_id"] for r in rows if r["scorable"] == "True"}
    if not pilot_ids <= eligible:
        raise ValueError("Pilot is not contained in the scored frame")
    frame = sorted((r for r in rows if r["scorable"] == "True"
                    and r["record_id"] not in pilot_ids), key=lambda r: r["record_id"])
    if len(frame) < n:
        raise ValueError("Insufficient eligible records")
    return random.Random(seed).sample(frame, n), frame


def build(out=OUT):
    out = Path(out)
    if out.exists():
        raise FileExistsError("Preserve the frozen audit; output already exists")
    scored_path = ROOT / "data/scored/proquest/descriptive/scored_claims.csv.gz"
    pilot_path = ROOT / "data/scored/proquest/publication/pilot_retrieval.csv"
    source_manifest = ROOT / "data/scored/proquest/robustness/summary.json"
    expected = json.loads(source_manifest.read_text())["sources"]
    sources = {}
    for path in annual_files(ROOT / "data/proquest/verified"):
        name = str(path.relative_to(ROOT))
        sources[name] = sha256(path)
        if sources[name] != expected[name]:
            raise ValueError("Source changed: " + name)
    rows = read_csv(scored_path)
    pilot = {r["audit_id"].removeprefix("verified:") for r in read_csv(pilot_path)}
    if len(pilot) != 12:
        raise ValueError("Expected twelve pilot exclusions")
    sample, frame = select(rows, pilot)
    if len(frame) != 175843:
        raise ValueError("Unexpected main frame size")
    retrieval, labels = pilot_records(ROOT, sample, len(frame), sources)
    for row in retrieval:
        row["inclusion_probability"] = row.pop("pilot_inclusion_probability")
    rubric = {
        "version": "2026-10-19-main-ai-v1",
        "reviewer_type": "AI",
        "human_validation_complete": False,
        "authorization": "Author requested selecting and validating 100 claims in Chrome.",
        "amendment": (
            "Proceed with the proposed main probability design before completion of "
            "the human pilot, as requested on 2026-10-19. This is a separately "
            "identified AI source audit, not the planned human validation. The "
            "human pilot and human response store remain untouched."
        ),
        "source_protocol": "docs/publication/REVIEW_PROTOCOL.md",
        "first_pass": [
            "mapping_status", "is_forecast", "quantity", "change_type", "direction",
            "scope", "horizon_support", "target_start", "target_end", "condition",
            "attribution", "original_forecast_date", "initial_note", "blinding",
        ],
        "comparison": [
            "topic", "direction", "scope", "confidence", "voice", "horizon_months",
            "horizon_hint", "benchmark", "joint_usability", "error_category",
        ],
        "decisions": [
            "Recover exact ordered source lineage by full reconstructed export hash.",
            "Inspect original quote and article context; absent quotes need source inspection.",
            "Record first interpretation before revealing machine labels.",
            "Do not reveal realized economic outcomes.",
            "Retain every unavailable or ambiguous sampled record without replacement.",
            "Growth-rate forecasts do not directly imply level changes.",
            "Conditions and unsupported horizons prevent strict unconditional scoring.",
            "Broad GDP/business, employment/unemployment and index-specific targets may be proxies.",
            "Save AI judgments separately; never enter them into human_review.json.",
            "Keep source prose and free-text judgments in the authorized TDM environment.",
        ],
        "estimation": (
            "Claim-weighted validity among this scored-candidate frame only; report "
            "assessable denominators and all-sample unresolved bounds. Cluster any "
            "uncertainty by article. No recall, human agreement, economic error "
            "correction or corpus-wide rescaling follows from this AI audit."
        ),
    }
    inputs = {str(p.relative_to(ROOT)): sha256(p) for p in [
        scored_path, pilot_path, source_manifest,
        ROOT / "docs/publication/REVIEW_PROTOCOL.md", Path(__file__),
    ]}
    out.mkdir(parents=True)
    # Freeze interpretation rules before writing the selected sample.
    (out / "rubric.json").write_text(json.dumps(rubric, indent=2) + "\n")
    write_csv(out / "retrieval.csv", retrieval)
    comparison = {"schema": "proquest-main-labels-v1", "records": labels}
    (out / "comparison.json").write_text(json.dumps(comparison, indent=2) + "\n")
    pack = {
        "schema": "proquest-main-ai-v1", "rubric": rubric["version"],
        "records": retrieval, "comparison_sha256": sha256(out / "comparison.json"),
    }
    pack["pack_id"] = hashlib.sha256(json.dumps(pack, sort_keys=True).encode()).hexdigest()
    (out / "pack.json").write_text(json.dumps(pack, indent=2) + "\n")
    frame_bytes = "".join("verified:" + r["record_id"] + "\n" for r in frame).encode()
    manifest = {
        "status": "Sample frozen; source review pending; no human validation",
        "seed": SEED, "rng": "Python random.Random.sample",
        "sampling_order": "lexicographic record_id",
        "design": "Simple random sampling without replacement",
        "frame_n": len(frame), "n": len(sample),
        "frame_addresses_sha256": hashlib.sha256(frame_bytes).hexdigest(),
        "excluded_pilot_ids": sorted("verified:" + p for p in pilot),
        "inclusion_probability": len(sample) / len(frame),
        "distinct_articles": len({r["page_id"] for r in retrieval}),
        "years": dict(sorted(Counter(r["date"][:4] for r in retrieval).items())),
        "publishers": dict(Counter(r["publisher"] for r in retrieval)),
        "inputs_sha256": inputs, "sources_sha256": sources,
        "pack_id": pack["pack_id"],
        "outputs_sha256": {p.name: sha256(p) for p in out.iterdir() if p.is_file()},
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({k: manifest[k] for k in
                      ("status", "seed", "frame_n", "n", "distinct_articles", "pack_id")}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUT)
    build(parser.parse_args().output)
