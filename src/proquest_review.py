"""Build the fixed, blinded ProQuest pilot. No source interpretation or sampling.

Standard-library only. The comparison file is deliberately separate from the UI.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RETRIEVAL = "data/scored/proquest/publication/pilot_retrieval.csv"
LABELS = "data/scored/proquest/publication/pilot_machine_labels.csv"
DEFAULT_OUT = "data/scored/proquest/source_review_pilot_v1"
SAFE_FIELDS = {"audit_id", "source_path", "source_sha256", "source_line", "page_id",
               "date", "publisher", "pilot_inclusion_probability", "source_locator", "mapping_status"}
LABEL_FIELDS = {"audit_id", "topic", "direction", "scope", "confidence", "voice",
                "horizon_months", "horizon_hint", "legacy_benchmark", "legacy_horizon_used"}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_rows(path, fields):
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if set(reader.fieldnames or []) != fields:
            raise ValueError(f"Unexpected fields: {path}")
        rows = list(reader)
    if len({r["audit_id"] for r in rows}) != len(rows):
        raise ValueError("Duplicate audit ID")
    return rows


def build(root=ROOT, out=None):
    out = out or root / DEFAULT_OUT
    records = read_rows(root / RETRIEVAL, SAFE_FIELDS)
    labels = read_rows(root / LABELS, LABEL_FIELDS)
    if len(records) != 12 or {r["audit_id"] for r in records} != {r["audit_id"] for r in labels}:
        raise ValueError("Expected the original twelve pilot records")
    inputs = {p: digest(root / p) for p in (RETRIEVAL, LABELS,
              "docs/publication/REVIEW_PROTOCOL.md", "src/proquest_review.py",
              "validation/proquest_review/review.html", "validation/proquest_review/review.js")}
    # Verify addresses without copying any source labels into the review pack.
    for row in records:
        source = root / row["source_path"]
        if digest(source) != row["source_sha256"]:
            raise ValueError(f"Changed source: {source}")
        inputs[row["source_path"]] = row["source_sha256"]
        with source.open() as handle:
            raw = next((json.loads(line) for n, line in enumerate(handle, 1)
                        if n == int(row["source_line"])), None)
        if not raw or str(raw["page_id"]) != row["page_id"] or raw["date"] != row["date"]:
            raise ValueError("Source address mismatch")
    comparison = (json.dumps({"schema": "proquest-pilot-labels-v1", "records": labels},
                              indent=2) + "\n").encode()
    pack = {"schema": "proquest-pilot-v1", "rubric": "2026-10-14-v1",
            "records": records, "comparison_sha256": hashlib.sha256(comparison).hexdigest()}
    pack["pack_id"] = hashlib.sha256(json.dumps(pack, sort_keys=True).encode()).hexdigest()
    html = (root / "validation/proquest_review/review.html").read_text()
    html = html.replace("/* REVIEW_CORE */", (root / "validation/proquest_review/review.js").read_text())
    html = html.replace("/* REVIEW_PACK */", json.dumps(pack).replace("<", "\\u003c"))
    out.mkdir(parents=True, exist_ok=True)
    (out / "review.html").write_text(html)
    (out / "comparison.json").write_bytes(comparison)
    (out / "pack.json").write_text(json.dumps(pack, indent=2) + "\n")
    manifest = {"pack_id": pack["pack_id"], "status": "Prepared; no human judgments",
                "inputs_sha256": inputs,
                "outputs_sha256": {p.name: digest(p) for p in
                    (out / "review.html", out / "comparison.json", out / "pack.json")}}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / DEFAULT_OUT)
    args = parser.parse_args()
    print(json.dumps(build(out=args.output), indent=2))
