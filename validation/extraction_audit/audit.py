"""Audit an extraction run: human precision plus two-model recall agreement.

Two quantities, two costs, so two samples:

  PRECISION (human). For a stratified sample of 500--700 claims emitted by the
  production model, a person marks whether each is a real scorable forecast.
  This is the only human-validation estimate in this audit.

  RECALL AGREEMENT (AI-assisted). On the same stratified 150-page sample,
  gpt-4o-mini and Gemini Flash independently extract claims, each using the
  ProQuest extraction prompt and its double-pass check. `agreement` reports how
  many Gemini claims gpt-4o-mini also found, and the reverse coverage. It is
  *not* a human recall estimate: agreement can miss errors shared by the two
  models. Do not call it recall validation or combine it with human precision
  into an F1 score.

Both samples are DECADE-STRATIFIED. The earlier era audit measured verified-set
precision at 63% pre-1940 vs 80% after, so a single pooled number would hide the
largest effect in the pipeline.

WORKS ON BOTH ARMS. --pages/--claims take a file or a glob:
  LOC (Mac):     --pages data/pages.jsonl
                 --claims data/claims/claims_monthly.jsonl
  ProQuest (VM): --pages 'data/raw/proquest_economy_*.jsonl'
                 --claims 'data/predictions/pred_proquest_economy_[0-9][0-9][0-9][0-9].jsonl'

IN THE VM the page text and quotes may not be exported. Only score's summary
JSON -- counts and rates, no text -- is safe to take out.

Usage:
    python audit.py pages  --pages <spec> --n 150 --out loc_audit
    python audit.py claims --claims <spec> --n 700 --out loc_audit
    #   ... fill the verdict column in loc_audit/claims.csv with y / n
    #   ... run both extractors on ONLY the pages listed in manifest.json
    python audit.py agreement --claims <gpt4o_mini.jsonl> \\
        --reference-claims <gemini_flash.jsonl> --out loc_audit
    python audit.py score  --claims <spec> --out loc_audit
"""
import argparse
import csv
import glob
import json
import math
import random
import re
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path

SEED = 20260910
MATCH = 0.60          # normalized similarity above which two quotes are "the same"


def load(spec):
    paths = sorted(glob.glob(spec)) if any(c in spec for c in "*?[") else [spec]
    if not paths:
        raise SystemExit(f"no files match {spec!r}")
    out = []
    for p in paths:
        with open(p, encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return out


def decade(rec):
    d = rec.get("date") or ""
    return f"{d[:3]}0s" if len(d) >= 4 and d[:4].isdigit() else None


def stratify(items, n, rng):
    """Round-robin across decades so no decade dominates and small ones survive."""
    by = defaultdict(list)
    for it in items:
        dec = decade(it)
        if dec:
            by[dec].append(it)
    for dec in by:
        rng.shuffle(by[dec])
    decs = sorted(by)
    picked, i = [], 0
    while len(picked) < n:
        moved = False
        for dec in decs:
            if len(picked) >= n:
                break
            if i < len(by[dec]):
                picked.append((dec, by[dec][i]))
                moved = True
        if not moved:
            break
        i += 1
    return picked


def norm(s):
    return re.sub(r"[^a-z0-9 ]+", "", (s or "").lower())


def same(a, b):
    """Same forecast? True when the two quotes share a contiguous run covering
    MATCH of the shorter one. A prefix test would wrongly fuse two different
    forecasts that open with the same formula ("Business will improve during
    the coming year..."), which is common in this prose."""
    a, b = norm(a), norm(b)
    if len(a) < 15 or len(b) < 15:
        return False
    m = SequenceMatcher(None, a, b).find_longest_match(0, len(a), 0, len(b))
    return m.size >= 20 and m.size / min(len(a), len(b)) >= MATCH


def wilson(k, n, z=1.96):
    if n == 0:
        return (float("nan"), 0.0, 1.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (p, max(0.0, c - h), min(1.0, c + h))


def one_to_one_matches(left, right):
    """Return one greedy, one-to-one quote match for a page.

    A single broad quote must not get credit for multiple narrower quotes from
    the other extractor. This is particularly important for model agreement:
    duplicate extraction is not independent evidence of recall.
    """
    used = set()
    matches = []
    for left_i, left_quote in enumerate(left):
        right_i = next((i for i, right_quote in enumerate(right)
                        if i not in used and same(left_quote, right_quote)), None)
        if right_i is not None:
            used.add(right_i)
            matches.append((left_i, right_i))
    return matches


def update_result(out, key, value):
    """Merge a result section so `agreement` and `score` can run in either order."""
    path = out / "result.json"
    try:
        result = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except json.JSONDecodeError:
        result = {}
    result[key] = value
    path.write_text(json.dumps(result, indent=2), encoding="utf-8")


def cmd_pages(args):
    rng = random.Random(args.seed)
    pages = load(args.pages)
    picked = stratify(pages, args.n, rng)
    if not picked:
        raise SystemExit("no dated pages found")
    out = Path(args.out)
    (out / "pages").mkdir(parents=True, exist_ok=True)

    manifest, counts, chars = [], defaultdict(int), 0
    for i, (dec, p) in enumerate(sorted(picked, key=lambda x: (x[1].get("date") or "")), 1):
        pid = str(p.get("page_id"))
        text = p.get("ocr_text") or p.get("text") or ""
        chars += len(text)
        counts[dec] += 1
        fn = out / "pages" / f"{i:04d}_{p.get('date','nodate')}.txt"
        fn.write_text(
            f"# page_id: {pid}\n# date: {p.get('date')}\n"
            f"# publisher: {p.get('publisher') or p.get('newspaper_title') or ''}\n"
            f"# chars: {len(text)}\n"
            f"# --- write one row in found.csv for EVERY forecast below ---\n\n{text}\n",
            encoding="utf-8")
        manifest.append({"n": i, "page_id": pid, "date": p.get("date"),
                         "decade": dec, "n_chars": len(text), "file": fn.name})

    (out / "manifest.json").write_text(json.dumps(
        {"kind": "pages", "seed": args.seed, "n": len(manifest),
         "source": args.pages, "pages": manifest}, indent=2), encoding="utf-8")

    found = out / "found.csv"
    if not found.exists():
        with open(found, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(["page_id", "quote"])

    print(f"{len(manifest)} pages -> {out}/pages/   ({chars:,} chars to read)")
    for dec in sorted(counts):
        print(f"  {dec}  {counts[dec]:>4}")
    print(f"\nRead each file. For EVERY forecast you find, add a row to {found}:")
    print("    page_id,quote")
    print("Pages with no forecasts: add nothing -- they still count, via manifest.json.")
    print(f"Estimated reading time: {chars/20000*20/60:.1f} hours at ~20 min per 20k chars.")


def cmd_claims(args):
    rng = random.Random(args.seed + 1)
    claims = [c for c in load(args.claims)
              if c.get("quote") and not c.get("no_predictions")]
    picked = stratify(claims, args.n, rng)
    if not picked:
        raise SystemExit("no dated claims with quotes found")
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    rows = list(range(len(picked)))
    rng.shuffle(rows)
    counts = defaultdict(int)
    with open(out / "claims.csv", "w", newline="", encoding="utf-8") as f, \
         open(out / "claims_key.csv", "w", newline="", encoding="utf-8") as g:
        w, k = csv.writer(f), csv.writer(g)
        w.writerow(["id", "quote", "direction", "topic", "scope", "verdict"])
        k.writerow(["id", "decade", "page_id"])
        for new_id, idx in enumerate(rows):
            dec, c = picked[idx]
            counts[dec] += 1
            w.writerow([new_id, c.get("quote", ""), c.get("direction", ""),
                        c.get("topic", ""), c.get("scope", ""), ""])
            k.writerow([new_id, dec, c.get("page_id", "")])

    print(f"{len(picked)} claims -> {out}/claims.csv")
    for dec in sorted(counts):
        print(f"  {dec}  {counts[dec]:>5}")
    print("\nFill `verdict`: y = real forward-looking scorable forecast, n = not.")
    print("Do not open claims_key.csv while marking.")


def cmd_agreement(args):
    """Compare two independent extractor runs on the page sample in manifest."""
    out = Path(args.out)
    manifest_path = out / "manifest.json"
    if not manifest_path.exists():
        raise SystemExit("agreement requires the 150-page manifest; run `pages` first")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    dec_of = {str(p["page_id"]): p["decade"] for p in manifest["pages"]}
    page_ids = set(dec_of)

    def quotes_by_page(spec):
        quotes = defaultdict(list)
        for claim in load(spec):
            page_id = str(claim.get("page_id"))
            quote = claim.get("quote")
            if page_id in page_ids and quote and not claim.get("no_predictions"):
                quotes[page_id].append(quote)
        return quotes

    primary = quotes_by_page(args.claims)
    reference = quotes_by_page(args.reference_claims)
    primary_by_decade = defaultdict(lambda: [0, 0])
    reference_by_decade = defaultdict(lambda: [0, 0])
    total_primary = total_reference = total_matches = 0
    unmatched_reference = []

    for page_id, dec in dec_of.items():
        primary_quotes = primary[page_id]
        reference_quotes = reference[page_id]
        matches = one_to_one_matches(primary_quotes, reference_quotes)
        matched_primary = {i for i, _ in matches}
        matched_reference = {i for _, i in matches}
        n_matches = len(matches)

        # Primary coverage of the reference is the requested pseudo-recall.
        reference_by_decade[dec][0] += n_matches
        reference_by_decade[dec][1] += len(reference_quotes)
        # Reverse coverage makes asymmetric extractor behavior visible.
        primary_by_decade[dec][0] += n_matches
        primary_by_decade[dec][1] += len(primary_quotes)
        total_primary += len(primary_quotes)
        total_reference += len(reference_quotes)
        total_matches += n_matches
        unmatched_reference.extend((page_id, q[:90]) for i, q in enumerate(reference_quotes)
                                   if i not in matched_reference)

    def rates(tally):
        rows, matched, total = {}, 0, 0
        for dec in sorted(tally):
            k, n = tally[dec]
            p, lo, hi = wilson(k, n)
            rows[dec] = {"matched": k, "n": n, "rate": p, "ci": [lo, hi]}
            matched += k
            total += n
        p, lo, hi = wilson(matched, total)
        return rows, {"matched": matched, "n": total, "rate": p, "ci": [lo, hi]}

    reference_rows, reference_all = rates(reference_by_decade)
    primary_rows, primary_all = rates(primary_by_decade)
    print("=== TWO-MODEL RECALL AGREEMENT (not human recall validation) ===")
    print(f"  sampled pages: {len(page_ids)}")
    print(f"  {args.label} claims: {total_primary}   {args.reference_label} claims: {total_reference}")
    print(f"\n  {args.label} coverage of {args.reference_label} claims")
    print(f"  {'decade':<9}{'matched':>9}{'reference':>11}{'coverage':>10}   95% CI")
    for dec in sorted(reference_rows):
        row = reference_rows[dec]
        print(f"  {dec:<9}{row['matched']:>9}{row['n']:>11}{row['rate']:>10.3f}   "
              f"[{row['ci'][0]:.3f}, {row['ci'][1]:.3f}]")
    print(f"  {'ALL':<9}{reference_all['matched']:>9}{reference_all['n']:>11}"
          f"{reference_all['rate']:>10.3f}   [{reference_all['ci'][0]:.3f}, {reference_all['ci'][1]:.3f}]")
    print(f"\n  reverse: {args.reference_label} covers {primary_all['matched']}/{primary_all['n']} "
          f"{args.label} claims = {primary_all['rate']:.3f} "
          f"[{primary_all['ci'][0]:.3f}, {primary_all['ci'][1]:.3f}]")
    if unmatched_reference:
        print(f"\n  {len(unmatched_reference)} {args.reference_label} claims were not matched; first 10:")
        for page_id, quote in unmatched_reference[:10]:
            print(f"    [{page_id}] {quote}")

    update_result(out, "model_recall_agreement", {
        "caveat": "AI-assisted model agreement, not human recall validation.",
        "sampled_pages": len(page_ids),
        "primary_label": args.label,
        "reference_label": args.reference_label,
        "primary_coverage_of_reference": {"overall": reference_all,
                                             "by_decade": reference_rows},
        "reference_coverage_of_primary": {"overall": primary_all,
                                             "by_decade": primary_rows},
    })
    print(f"\nwrote {out}/result.json  (numbers only -- safe to export)")


def cmd_score(args):
    out = Path(args.out)
    res = {}

    # ---- precision, from the claim sheet -------------------------------------
    cp = out / "claims.csv"
    if cp.exists():
        key = {r["id"]: r["decade"] for r in csv.DictReader(open(out / "claims_key.csv"))}
        tally = defaultdict(lambda: [0, 0])
        for r in csv.DictReader(open(cp)):
            v = (r.get("verdict") or "").strip().lower()
            if v not in ("y", "n"):
                continue
            dec = key.get(r["id"], "?")
            tally[dec][0] += (v == "y")
            tally[dec][1] += 1
        print("=== PRECISION (of claims the model emitted) ===")
        print(f"  {'decade':<9}{'real':>6}{'n':>6}{'prec':>8}   95% CI")
        tk = tn = 0
        for dec in sorted(tally):
            k, n = tally[dec]
            tk += k; tn += n
            p, lo, hi = wilson(k, n)
            print(f"  {dec:<9}{k:>6}{n:>6}{p:>8.3f}   [{lo:.3f}, {hi:.3f}]")
        p, lo, hi = wilson(tk, tn)
        print(f"  {'ALL':<9}{tk:>6}{tn:>6}{p:>8.3f}   [{lo:.3f}, {hi:.3f}]")
        res["precision"] = {"real": tk, "n": tn, "rate": p, "ci": [lo, hi],
                            "by_decade": {d: {"real": v[0], "n": v[1]} for d, v in tally.items()}}
    else:
        print("(no claims.csv -- skipping precision)")

    # ---- recall, from the annotated pages ------------------------------------
    mp = out / "manifest.json"
    fp = out / "found.csv"
    if mp.exists() and fp.exists():
        man = json.loads(mp.read_text())
        dec_of = {p["page_id"]: p["decade"] for p in man["pages"]}
        ids = set(dec_of)
        human = defaultdict(list)
        for r in csv.DictReader(open(fp)):
            if (r.get("quote") or "").strip():
                human[str(r["page_id"]).strip()].append(r["quote"])
        model = defaultdict(list)
        for c in load(args.claims):
            pid = str(c.get("page_id"))
            if pid in ids and c.get("quote") and not c.get("no_predictions"):
                model[pid].append(c["quote"])

        rec = defaultdict(lambda: [0, 0])    # decade -> [matched, total_human]
        pre = defaultdict(lambda: [0, 0])    # decade -> [matched, total_model]
        misses = []
        for pid, dec in dec_of.items():
            hq, mq = human.get(pid, []), model.get(pid, [])
            for q in hq:
                hit = any(same(q, m) for m in mq)
                rec[dec][0] += hit; rec[dec][1] += 1
                if not hit:
                    misses.append((pid, q[:90]))
            for m in mq:
                pre[dec][0] += any(same(m, q) for q in hq); pre[dec][1] += 1

        print("\n=== RECALL (of forecasts you found on the sampled pages) ===")
        print(f"  {'decade':<9}{'found':>7}{'human':>7}{'recall':>8}   95% CI")
        tk = tn = 0
        for dec in sorted(rec):
            k, n = rec[dec]
            tk += k; tn += n
            p, lo, hi = wilson(k, n)
            print(f"  {dec:<9}{k:>7}{n:>7}{p:>8.3f}   [{lo:.3f}, {hi:.3f}]")
        p, lo, hi = wilson(tk, tn)
        print(f"  {'ALL':<9}{tk:>7}{tn:>7}{p:>8.3f}   [{lo:.3f}, {hi:.3f}]")
        res["recall"] = {"found": tk, "human": tn, "rate": p, "ci": [lo, hi],
                         "by_decade": {d: {"found": v[0], "human": v[1]} for d, v in rec.items()}}

        pk = sum(v[0] for v in pre.values()); pn = sum(v[1] for v in pre.values())
        p2, lo2, hi2 = wilson(pk, pn)
        print(f"\n  page-based precision cross-check: {pk}/{pn} = {p2:.3f} [{lo2:.3f}, {hi2:.3f}]")
        print("  (independent of the claim sheet -- the two should agree)")
        res["precision_pagebased"] = {"real": pk, "n": pn, "rate": p2, "ci": [lo2, hi2]}

        if "precision" in res and res["precision"]["n"] and tn:
            pr, rc = res["precision"]["rate"], p
            if pr + rc:
                print(f"\n  F1 = {2*pr*rc/(pr+rc):.3f}")
                res["f1"] = 2 * pr * rc / (pr + rc)
        if misses:
            print(f"\n  {len(misses)} missed forecasts; first 10:")
            for pid, q in misses[:10]:
                print(f"    [{pid}] {q}")
    else:
        print("\n(no manifest.json / found.csv -- skipping recall)")

    for key, value in res.items():
        update_result(out, key, value)
    print(f"\nwrote {out}/result.json  (numbers only -- safe to export)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("pages", "claims", "agreement", "score"):
        p = sub.add_parser(name)
        p.add_argument("--out", default="audit_out")
        p.add_argument("--seed", type=int, default=SEED)
        if name in ("pages",):
            p.add_argument("--pages", required=True)
            p.add_argument("--n", type=int, default=150)
        if name in ("claims",):
            p.add_argument("--claims", required=True)
            p.add_argument("--n", type=int, default=700,
                           help="human precision sample size (use 500--700)")
        if name == "agreement":
            p.add_argument("--claims", required=True,
                           help="production gpt-4o-mini extraction output")
            p.add_argument("--reference-claims", required=True,
                           help="independent Gemini Flash extraction output")
            p.add_argument("--label", default="gpt-4o-mini")
            p.add_argument("--reference-label", default="Gemini Flash")
        if name == "score":
            p.add_argument("--claims", required=True)
    a = ap.parse_args()
    {"pages": cmd_pages, "claims": cmd_claims, "agreement": cmd_agreement,
     "score": cmd_score}[a.cmd](a)
