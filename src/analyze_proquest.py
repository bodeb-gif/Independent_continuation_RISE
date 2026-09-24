"""Inventory the annual ProQuest corpus; optionally export claims for scoring.

Run from the repository root: python src/analyze_proquest.py
No LOC claims or old episode shards are loaded. No dependencies or network.
"""

import argparse
from collections import Counter
from datetime import date
import hashlib
import json
from pathlib import Path
import re


ANNUAL = re.compile(r"^pred_proquest_economy_(\d{4})\.export\.jsonl$")
# Retrospective annotations and verifier prose are not forecast features.
ANNOTATIONS = {"window", "window_kind", "cycle", "verify_reason"}
LABELS = ("topic", "direction", "scope", "confidence", "voice", "horizon_hint")


def annual_files(directory):
    paths = sorted(p for p in Path(directory).glob("*.jsonl")
                   if ANNUAL.fullmatch(p.name))
    years = {int(ANNUAL.fullmatch(p.name)[1]) for p in paths}
    expected = set(range(1900, 2011))
    if years != expected:
        raise ValueError(f"Annual corpus mismatch in {directory}: "
                         f"missing={sorted(expected - years)}, "
                         f"unexpected={sorted(years - expected)}")
    return paths


def inventory(directory, export=None):
    paths = annual_files(directory)
    counts, labels = Counter(), {k: Counter() for k in LABELS}
    decades, publishers, seen = Counter(), Counter(), set()
    pages, empty_pages, claim_pages = set(), set(), set()
    dates = []
    output = None
    if export:
        export.parent.mkdir(parents=True, exist_ok=True)
        output = export.open("w", encoding="utf-8")
    try:
        for path in paths:
            year = int(ANNUAL.fullmatch(path.name)[1])
            with path.open(encoding="utf-8") as source:
                for number, line in enumerate(source, 1):
                    if not line.strip():
                        continue
                    row = json.loads(line)
                    if row.get("schema_version") != 2:
                        raise ValueError(f"Unexpected schema: {path}:{number}")
                    if not row.get("page_id"):
                        raise ValueError(f"Missing article ID: {path}:{number}")
                    page = str(row["page_id"])
                    pages.add(page)
                    counts["records"] += 1
                    if row.get("no_predictions"):
                        counts["no_prediction_records"] += 1
                        empty_pages.add(page)
                        continue
                    if row.get("source") != "proquest":
                        raise ValueError(f"Unexpected source: {path}:{number}")
                    claim_pages.add(page)
                    counts["claims"] += 1
                    printed = date.fromisoformat(row["date"])
                    if printed.year != year:
                        raise ValueError(f"Date outside shard: {path}:{number}")
                    dates.append(printed.isoformat())
                    decades[str(year // 10 * 10)] += 1
                    publishers[row.get("publisher") or row.get("newspaper_title") or "unknown"] += 1
                    for key in LABELS:
                        labels[key][str(row.get(key))] += 1
                    horizon = str(row.get("horizon_months", ""))
                    if horizon not in {"6", "12", "24", "vague"}:
                        counts["horizons_outside_current_scorer_contract"] += 1
                    if row.get("scope") == "national":
                        counts["national_claims"] += 1
                        if row.get("horizon_hint") != "default":
                            counts["national_nondefault_horizon_claims"] += 1
                    clean = {k: v for k, v in row.items() if k not in ANNOTATIONS}
                    serialized = json.dumps(clean, sort_keys=True, ensure_ascii=False)
                    digest = hashlib.sha256(serialized.encode()).digest()
                    if digest in seen:
                        counts["identical_exported_label_rows"] += 1
                    seen.add(digest)
                    if output:
                        output.write(serialized + "\n")
    finally:
        if output:
            output.close()
    result = {
        "files": len(paths), "years": [1900, 2010],
        "claim_date_range": [min(dates), max(dates)],
        **counts, "represented_articles": len(pages),
        "articles_with_claims": len(claim_pages),
        "articles_with_no_prediction_records": len(empty_pages),
        "articles_with_both_claims_and_empty_records": len(empty_pages & claim_pages),
        "labels": {k: dict(c.most_common()) for k, c in labels.items()},
        "claims_by_decade": dict(sorted(decades.items())),
        "claims_by_publisher": dict(publishers.most_common()),
    }
    return result, pages


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, default=Path("data/proquest"))
    parser.add_argument("--out", type=Path, default=Path("data/scored/proquest"))
    parser.add_argument("--export-claims", action="store_true",
                        help="Also write verified_claims.jsonl for the scorer; rows are not deduplicated")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    raw, raw_pages = inventory(args.base / "raw")
    verified, verified_pages = inventory(
        args.base / "verified",
        args.out / "verified_claims.jsonl" if args.export_claims else None)
    result = {"raw": raw, "verified": verified,
              "raw_articles_not_represented_in_verified": len(raw_pages - verified_pages),
              "verified_articles_not_represented_in_raw": len(verified_pages - raw_pages)}
    (args.out / "inventory.json").write_text(json.dumps(result, indent=2) + "\n")
    lines = ["# ProQuest annual corpus inventory", "",
             "Only annual ProQuest exports enter this report. LOC and old crisis-window files are excluded.", "",
             "| Set | Annual files | Claims | Represented articles | National claims |",
             "| --- | ---: | ---: | ---: | ---: |"]
    for name, data in [("Raw", raw), ("Machine-verified", verified)]:
        lines.append(f"| {name} | {data['files']} | {data['claims']:,} | "
                     f"{data['represented_articles']:,} | {data['national_claims']:,} |")
    lines += ["", "Both sets span 1900–2010 with no missing annual shards.", "",
              f"Raw article IDs absent from verified exports: {len(raw_pages - verified_pages):,}. "
              "These counts cannot establish extraction or verification completeness without an in-VM article manifest.", "",
              "## Verified claim counts by decade", "",
              "| Decade | Claims |", "| --- | ---: |"]
    lines += [f"| {d} | {n:,} |" for d, n in verified["claims_by_decade"].items()]
    lines += ["", "## Analysis readiness", "",
              f"- {verified.get('identical_exported_label_rows', 0):,} verified rows share identical exported labels. "
              "They are retained: stripped quotes mean distinct forecasts can have identical labels.",
              f"- {verified['labels']['horizon_hint'].get('default', 0):,} verified claims have default horizons; "
              "report these separately from claim-grounded horizons.",
              f"- {verified.get('horizons_outside_current_scorer_contract', 0):,} verified horizons fall outside "
              "the current scorer's 6/12/24/vague vocabulary. Resolve these before scoring rather than silently defaulting them.",
              "- Score only national, supported-topic forecasts against the appropriate economic series. "
              "The existing scope gate permits some unexpected labels; tighten it before a full run.",
              "- The current stock index ends in 1968. Later market claims need a documented benchmark.",
              "- Machine verification is a filter, not human validation. LOC is reserved for extraction validation.",
              "- Attention requires a ProQuest article sampling denominator. Do not substitute LOC page counts.",
              "- No hit rate or model result has been computed by this inventory.", ""]
    (args.out / "inventory.md").write_text("\n".join(lines))
    print("\n".join(lines[:10]))
    print(f"\nReport: {args.out / 'inventory.md'}")


if __name__ == "__main__":
    main()
