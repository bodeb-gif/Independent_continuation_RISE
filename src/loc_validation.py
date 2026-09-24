"""Build a local LOC claim reviewer and a blinded page packet for recall review.

LOC material is validation evidence only; none of these commands score economic
outcomes or add LOC claims to the ProQuest analysis corpus.
"""

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import random
import re


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CLAIMS = ROOT / "data/claims/claims_monthly.jsonl"
TEMPLATE = ROOT / "validation/loc_review/review_template.html"
GENERATED = ROOT / "validation/loc_review/generated"
TOKENS = re.compile(r"[a-z0-9]+")


def jsonl(path):
    with Path(path).open(encoding="utf-8") as handle:
        for number, line in enumerate(handle, 1):
            if line.strip():
                try:
                    yield number, json.loads(line)
                except json.JSONDecodeError as error:
                    raise ValueError(f"{path}:{number}: {error}") from error


def read_pages(paths):
    if not paths:
        raise ValueError("Pass at least one --pages JSONL file containing LOC OCR pages.")
    pages = {}
    for path in paths:
        for number, row in jsonl(path):
            page_id = row.get("page_id")
            if not page_id or not isinstance(row.get("ocr_text"), str):
                raise ValueError(f"{path}:{number}: expected page_id and ocr_text")
            old = pages.get(page_id)
            if old and old["ocr_text"] != row["ocr_text"]:
                raise ValueError(f"Conflicting OCR for page {page_id}")
            pages[page_id] = row
    return pages


def locate_quote(text, quote):
    """Return a locator span and match type for a quote in page OCR.

    OCR often inserts line breaks or punctuation within a phrase. A missing
    full span may still have an exact partial anchor. Partial anchors are
    visibly marked as such and never treated as proof that the quote is real.
    """
    def compact(value):
        chars, offsets = [], []
        for i, char in enumerate(value):
            if char.isalnum():
                chars.append(char.casefold())
                offsets.append(i)
        return "".join(chars), offsets

    haystack, offsets = compact(text)
    needle, _ = compact(quote or "")
    if len(needle) < 12:
        return None, "none"
    start = haystack.find(needle)
    if start >= 0:
        return [offsets[start], offsets[start + len(needle) - 1] + 1], "exact"
    # Search fixed anchors, then extend each hit in both directions. This is
    # linear-ish in the quote length and keeps the display deterministic.
    best = (0, -1)
    width = 24
    for qpos in range(0, max(1, len(needle) - width + 1), 8):
        anchor = needle[qpos:qpos + width]
        if len(anchor) < width:
            continue
        hpos = haystack.find(anchor)
        while hpos >= 0:
            left_q, left_h = qpos, hpos
            right_q, right_h = qpos + width, hpos + width
            while left_q and left_h and needle[left_q - 1] == haystack[left_h - 1]:
                left_q -= 1; left_h -= 1
            while right_q < len(needle) and right_h < len(haystack) and needle[right_q] == haystack[right_h]:
                right_q += 1; right_h += 1
            if right_h - left_h > best[1] - best[0]:
                best = (left_h, right_h)
            hpos = haystack.find(anchor, hpos + 1)
    if best[1] - best[0] >= max(30, min(80, len(needle) // 4)):
        return [offsets[best[0]], offsets[best[1] - 1] + 1], "partial"
    return None, "none"


def unit_id(page_id, line_number):
    return "loc_" + hashlib.sha256(f"{page_id}\0{line_number}".encode()).hexdigest()[:20]


def write_jsonl(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def file_sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_claim_review(args):
    pages = read_pages(args.pages)
    eligible = []
    for number, row in jsonl(args.claims):
        page_id = row.get("page_id")
        if page_id in pages and row.get("quote"):
            eligible.append((number, row))
    if not eligible:
        raise ValueError("No claim page IDs match the supplied LOC pages.")
    eligible_count = len(eligible)
    if args.n < 0:
        raise ValueError("--n must be nonnegative; 0 selects every matched claim")
    if args.n:
        eligible = random.Random(args.seed).sample(eligible, min(args.n, eligible_count))
    eligible.sort(key=lambda pair: (pair[1].get("date") or "", pair[0]))

    items, manifest, selected_pages = [], [], {}
    for line_number, claim in eligible:
        page_id = claim["page_id"]
        page = pages[page_id]
        selected_pages[page_id] = {
            "ocr_text": page["ocr_text"],
            "source_page_id": page.get("source_page_id") or "",
        }
        identifier = unit_id(page_id, line_number)
        span, span_kind = locate_quote(page["ocr_text"], claim["quote"])
        items.append({
            "unit_id": identifier,
            "page_id": page_id,
            "date": claim.get("date") or page.get("date") or "",
            "publisher": claim.get("publisher") or page.get("publisher") or "",
            "quote": claim["quote"],
            "span": span,
            "span_kind": span_kind,
        })
        manifest.append({
            "unit_id": identifier, "page_id": page_id,
            "claim_source": str(args.claims), "claim_line": line_number,
            "page_source": str(args.pages),
            "selection_probability_among_matched_claims": len(eligible) / eligible_count,
            "machine_labels": {k: v for k, v in claim.items() if k not in
                               {"quote", "page_id", "date", "publisher", "source_text_type"}},
        })

    build_id = hashlib.sha256("\n".join(item["unit_id"] for item in items).encode()).hexdigest()[:12]
    payload = {"build_id": build_id, "reviewer": args.reviewer,
               "items": items, "pages": selected_pages}
    embedded = json.dumps(payload, ensure_ascii=False).replace("<", "\\u003c")
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(TEMPLATE.read_text(encoding="utf-8").replace("__REVIEW_DATA__", embedded), encoding="utf-8")
    write_jsonl(output.with_suffix(".manifest.jsonl"), manifest)
    print(f"Review: {output} ({len(items)} claims on {len(selected_pages)} pages; "
          f"{sum(i['span'] is None for i in items)} quote spans need manual location)")
    print(f"Machine-label sidecar: {output.with_suffix('.manifest.jsonl')}")
    if eligible_count != len(items):
        print(f"Sampled {len(items)} of {eligible_count} claims linked to supplied pages.")
    print("The local page set may be partial; this sample is not a full-corpus estimate.")


def sample_recall(args):
    pages = read_pages(args.pages)
    if args.n <= 0:
        raise ValueError("--n must be positive")
    page_ids = sorted(pages)
    if args.n > len(page_ids):
        raise ValueError(f"Requested {args.n} pages, but only {len(page_ids)} are available")
    chosen = sorted(random.Random(args.seed).sample(page_ids, args.n))
    packet = [{k: pages[page_id].get(k) for k in
               ("page_id", "date", "publisher", "source_page_id", "ocr_text")}
              for page_id in chosen]
    write_jsonl(args.out, packet)
    digest = hashlib.sha256("\n".join(page_ids).encode()).hexdigest()
    manifest = {"purpose": "LOC extraction recall model-reference packet",
                "population_label": args.population_label,
                "input_paths": [str(p) for p in args.pages],
                "available_pages": len(page_ids), "sampled_pages": len(chosen),
                "selection_probability_within_supplied_pages": len(chosen) / len(page_ids),
                "seed": args.seed, "sorted_page_ids_sha256": digest,
                "sampled_page_ids": chosen,
                "source_sha256": {str(path): file_sha256(path) for path in args.pages},
                "model_predictions_in_packet": False}
    manifest_path = Path(args.out).with_suffix(".manifest.json")
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Blinded recall packet: {args.out} ({len(chosen)}/{len(pages)} supplied pages)")
    print(f"Sampling manifest: {manifest_path}")
    print("Any recall estimate is relative to independently reviewed page labels.")


def overlap(a, b):
    a, b = set(TOKENS.findall((a or "").lower())), set(TOKENS.findall((b or "").lower()))
    if min(len(a), len(b)) < 4:
        return 0.0
    return len(a & b) / min(len(a), len(b))


def match_claims(reference, extracted, threshold=0.7):
    pairs = [(overlap(r.get("quote"), e.get("quote")), ri, ei)
             for ri, r in enumerate(reference) for ei, e in enumerate(extracted)]
    taken_r, taken_e, matched = set(), set(), []
    for score, ri, ei in sorted(pairs, reverse=True):
        if score < threshold:
            break
        if ri not in taken_r and ei not in taken_e:
            taken_r.add(ri); taken_e.add(ei); matched.append((ri, ei, score))
    return matched, [i for i in range(len(reference)) if i not in taken_r], [i for i in range(len(extracted)) if i not in taken_e]


def score_recall(args):
    packet = {r["page_id"]: r for _, r in jsonl(args.packet)}
    if not packet:
        raise ValueError("Empty page packet")
    references = {}
    for _, row in jsonl(args.reference):
        page_id = row.get("page_id")
        if page_id not in packet or page_id in references or not isinstance(row.get("claims"), list):
            raise ValueError("Reference needs exactly one {page_id, claims: [...]} row per sampled page")
        references[page_id] = row["claims"]
    if set(references) != set(packet):
        raise ValueError(f"Reference missing {len(set(packet) - set(references))} sampled pages")
    extracted = defaultdict(list)
    for _, row in jsonl(args.claims):
        if row.get("page_id") in packet and row.get("quote"):
            extracted[row["page_id"]].append(row)
    totals = {"matched": 0, "reference_only": 0, "extractor_only": 0}
    details = []
    for page_id in packet:
        refs, preds = references[page_id], extracted[page_id]
        pairs, missed, extra = match_claims(refs, preds, args.threshold)
        totals["matched"] += len(pairs)
        totals["reference_only"] += len(missed)
        totals["extractor_only"] += len(extra)
        details.append({"page_id": page_id, "date": packet[page_id].get("date"),
                        "reference_claims": len(refs), "extractor_claims": len(preds),
                        "matched": len(pairs), "reference_only": len(missed),
                        "extractor_only": len(extra),
                        "matches": [{"reference_index": ri, "extractor_index": ei, "overlap": score}
                                    for ri, ei, score in pairs]})
    denom = totals["matched"] + totals["reference_only"]
    totals["coverage_relative_to_reference"] = totals["matched"] / denom if denom else None
    totals["reference_kind"] = args.reference_kind
    totals["sampled_pages"] = len(packet)
    result = {"summary": totals, "pages": details,
              "warning": "A model-generated reference is not human-verified absolute recall."}
    out = Path(args.out);out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(totals, indent=2))
    print(f"Per-page matches: {out}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    review = commands.add_parser("claim-review", help="build human claim-label review HTML")
    review.add_argument("--pages", type=Path, action="append", required=True)
    review.add_argument("--claims", type=Path, default=DEFAULT_CLAIMS)
    review.add_argument("--n", type=int, default=120, help="0 = all linked claims")
    review.add_argument("--seed", type=int, default=20260924)
    review.add_argument("--reviewer", default="bode")
    review.add_argument("--out", type=Path, default=GENERATED / "loc_claim_review.html")
    review.set_defaults(func=build_claim_review)
    recall = commands.add_parser("sample-recall", help="sample OCR pages without extractor outputs")
    recall.add_argument("--pages", type=Path, action="append", required=True)
    recall.add_argument("--n", type=int, default=24)
    recall.add_argument("--seed", type=int, default=20260924)
    recall.add_argument("--population-label", required=True, help="e.g. partial shard pilot or complete monthly corpus")
    recall.add_argument("--out", type=Path, default=GENERATED / "recall_pages.jsonl")
    recall.set_defaults(func=sample_recall)
    score = commands.add_parser("score-recall", help="compare page enumeration with LOC extracted claims")
    score.add_argument("--packet", type=Path, required=True)
    score.add_argument("--reference", type=Path, required=True)
    score.add_argument("--claims", type=Path, default=DEFAULT_CLAIMS)
    score.add_argument("--reference-kind", choices=["model", "human_adjudicated"], required=True)
    score.add_argument("--threshold", type=float, default=0.7)
    score.add_argument("--out", type=Path, default=GENERATED / "recall_comparison.json")
    score.set_defaults(func=score_recall)
    args = parser.parse_args()
    try:
        args.func(args)
    except (OSError, ValueError) as error:
        parser.exit(2, f"{error}\n")


if __name__ == "__main__":
    main()
