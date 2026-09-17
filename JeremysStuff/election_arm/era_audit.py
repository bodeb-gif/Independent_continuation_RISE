"""Does verify_gpt.py's strictness drift with era, or does the corpus?

The keep rate climbs monotonically from ~45% (1900s-30s) to ~58% (1960s). Two
explanations with different consequences:

  A. THE CORPUS CHANGES. Early business prose is idiomatic and OCR-noisier, the
     extractor over-collects more, and the judge correctly rejects more. The
     filter is fine and the drift is a fact about newspapers.
  B. THE INSTRUMENT DRIFTS. The KEEP/DROP prompt was lifted word-for-word from
     main's verify_claims.py, calibrated on 1900-1963 LOC pages. If it transfers
     better to mid-century prose, later claims survive for reasons that have
     nothing to do with the press -- and every trend in the final series is
     partly a trend in the filter.

WHY NOT THE GOLD SET. validation/gold_extraction/ is 16 LOC pages, 4 per era
bucket, 16 gold claims, all Chronicling America regionals. Four claims per era
cannot resolve a 13-point difference, and they are the wrong corpus: LOC
regionals are not ProQuest's WSJ/NYT/Tribune. Running the judge over them
measures something real, but not this.

WHAT THIS DOES INSTEAD. A stratified BLIND audit of the judge's own decisions on
the actual ProQuest corpus. Four cells -- era (pre/post split year) x verdict
(kept/dropped) -- sampled year-balanced so the 1930s (41k claims) cannot drown
out the 1900s (3.5k). You read the quotes without seeing the year or the
machine's verdict, and mark each one. Scoring then reports, per era:

    false-drop rate = share of DROPPED claims you judged real forecasts
    false-keep rate = share of KEPT claims you judged not forecasts

If false-drop is materially higher pre-1940, the judge is over-strict early
(explanation B). If both error rates are flat across eras, the keep-rate drift
is the corpus (explanation A) and can be reported as a finding rather than a
caveat.

RUNS IN THE VM. The sample file contains article text and MUST NOT be exported.
Only era_audit_result.json -- counts and rates, no text -- is safe to take out.

Usage:
    python era_audit.py sample --n 50            # writes sample + key
    #   ... fill the `verdict` column in era_audit/sample.csv with y / n ...
    python era_audit.py score                    # rates, CIs, era comparison
"""
import argparse
import csv
import json
import math
import random
import re
from collections import defaultdict
from pathlib import Path

SHARD_RE = re.compile(r"^pred_proquest_economy_(\d{4})\.jsonl$")
SEED = 0


def load_cell(verified_dir, dropped):
    """year -> [record]. `dropped` picks the .dropped.jsonl side."""
    out = defaultdict(list)
    for path in sorted(Path(verified_dir).glob("pred_proquest_economy_[0-9][0-9][0-9][0-9].jsonl")):
        year = SHARD_RE.match(path.name).group(1)
        target = Path(str(path) + ".dropped.jsonl") if dropped else path
        if not target.exists():
            continue
        with open(target) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                # A page the extractor found nothing on is not a judged claim.
                if rec.get("no_predictions") or not rec.get("quote"):
                    continue
                out[year].append(rec)
    return out


def draw(by_year, years, n, rng):
    """Year-balanced: round-robin across years so one huge year cannot dominate."""
    pools = {y: rng.sample(by_year[y], len(by_year[y])) for y in years if by_year.get(y)}
    picked, i = [], 0
    while len(picked) < n and pools:
        for y in list(pools):
            if not pools[y]:
                del pools[y]
                continue
            if i < len(pools[y]):
                picked.append((y, pools[y][i]))
                if len(picked) >= n:
                    break
        i += 1
        if i > 10000:
            break
    return picked


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (p, max(0.0, c - h), min(1.0, c + h))


def two_prop_z(k1, n1, k2, n2):
    if min(n1, n2) == 0:
        return float("nan")
    p = (k1 + k2) / (n1 + n2)
    se = math.sqrt(p * (1 - p) * (1 / n1 + 1 / n2))
    return (k1 / n1 - k2 / n2) / se if se else float("nan")


def cmd_sample(args):
    rng = random.Random(args.seed)
    kept = load_cell(args.verified, dropped=False)
    dropped = load_cell(args.verified, dropped=True)
    years = sorted(set(kept) | set(dropped))
    if not years:
        raise SystemExit(f"no verified shards in {args.verified}")
    early = [y for y in years if int(y) < args.split]
    late = [y for y in years if int(y) >= args.split]
    print(f"years {years[0]}-{years[-1]}   early {len(early)}   late {len(late)}")

    rows, key = [], []
    for era, ys in (("early", early), ("late", late)):
        for verdict, pool in (("kept", kept), ("dropped", dropped)):
            got = draw(pool, ys, args.n, rng)
            print(f"  {era:<5} {verdict:<7} drew {len(got):>4} (asked {args.n})")
            for year, rec in got:
                rows.append(rec)
                key.append((era, verdict, year))

    order = list(range(len(rows)))
    rng.shuffle(order)                       # blind: no era or verdict ordering
    out = Path(args.dir)
    out.mkdir(parents=True, exist_ok=True)

    with open(out / "sample.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "quote", "direction", "topic", "scope", "verdict"])
        for new_id, idx in enumerate(order):
            r = rows[idx]
            w.writerow([new_id, r.get("quote", ""), r.get("direction", ""),
                        r.get("topic", ""), r.get("scope", ""), ""])
    with open(out / "key.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "era", "machine", "year"])
        for new_id, idx in enumerate(order):
            era, verdict, year = key[idx]
            w.writerow([new_id, era, verdict, year])

    print(f"\nwrote {out}/sample.csv  ({len(rows)} items) and {out}/key.csv")
    print("\nFill the `verdict` column in sample.csv:")
    print("   y = a real, forward-looking, scorable economic forecast")
    print("   n = not one (report of the present, retrospective, ad, headline-only,")
    print("       regional/foreign scope, too vague to score)")
    print("Do NOT open key.csv until you are done -- it holds the answers.")
    print("*** sample.csv contains article text. It must not leave the VM. ***")


def cmd_score(args):
    out = Path(args.dir)
    marks = {}
    with open(out / "sample.csv") as f:
        for row in csv.DictReader(f):
            v = (row.get("verdict") or "").strip().lower()
            if v in ("y", "yes", "1", "true"):
                marks[row["id"]] = True
            elif v in ("n", "no", "0", "false"):
                marks[row["id"]] = False
    key = {}
    with open(out / "key.csv") as f:
        for row in csv.DictReader(f):
            key[row["id"]] = (row["era"], row["machine"])

    unfilled = len(key) - len(marks)
    if unfilled:
        print(f"warning: {unfilled} of {len(key)} rows unmarked; scoring the rest\n")

    # false drop: machine said drop, human said real. false keep: the reverse.
    tally = defaultdict(lambda: [0, 0])   # (era, machine) -> [errors, n]
    for i, human in marks.items():
        if i not in key:
            continue
        era, machine = key[i]
        err = (machine == "dropped" and human) or (machine == "kept" and not human)
        tally[(era, machine)][0] += int(err)
        tally[(era, machine)][1] += 1

    result = {"n_marked": len(marks), "n_total": len(key), "cells": {}}
    print(f"{'era':<6}{'machine':<9}{'errors':>8}{'n':>6}{'rate':>8}   95% CI")
    for era in ("early", "late"):
        for machine in ("dropped", "kept"):
            k, n = tally[(era, machine)]
            p, lo, hi = wilson(k, n)
            label = "false-drop" if machine == "dropped" else "false-keep"
            print(f"{era:<6}{machine:<9}{k:>8}{n:>6}{p:>8.3f}   [{lo:.3f}, {hi:.3f}]  {label}")
            result["cells"][f"{era}_{machine}"] = {"errors": k, "n": n, "rate": p,
                                                   "ci_lo": lo, "ci_hi": hi}

    print()
    for machine in ("dropped", "kept"):
        ke, ne = tally[("early", machine)]
        kl, nl = tally[("late", machine)]
        z = two_prop_z(ke, ne, kl, nl)
        name = "false-drop" if machine == "dropped" else "false-keep"
        d = (ke / ne - kl / nl) if ne and nl else float("nan")
        print(f"{name}: early {ke}/{ne} vs late {kl}/{nl}   diff {d:+.3f}   z = {z:+.2f}")
        result[f"{machine}_era_diff"] = {"diff": d, "z": z}
    zd = result["dropped_era_diff"]["z"]
    print()
    if zd != zd:                                  # nan
        print("VERDICT: not enough marked rows to compare eras.")
    elif abs(zd) < 1.96:
        print("VERDICT: no evidence the judge is harsher early (|z| < 1.96).")
        print("  The keep-rate drift is the CORPUS, not the instrument. Report it")
        print("  as a finding; pooled analysis is defensible.")
    elif zd > 0:
        print("VERDICT: the judge drops significantly more real forecasts EARLY.")
        print("  The instrument drifts. Keep-rate by era is a confound, not a")
        print("  finding -- report rates per decade and re-run era comparisons on")
        print("  --set raw as well as --set verified.")
    else:
        print("VERDICT: the judge drops significantly more real forecasts LATE.")
        print("  Unexpected given the keep-rate trend -- inspect before reporting.")
    n_cell = min(v["n"] for v in result["cells"].values())
    if n_cell < 100:
        print(f"\n  POWER: {n_cell} rows in the smallest cell resolves differences of")
        print("  roughly 20 points, not 10. A null here is weak evidence; re-run with")
        print("  --n 150 before concluding the instrument is clean.")

    with open(out / "result.json", "w") as f:
        json.dump(result, f, indent=2)
    print(f"\nwrote {out}/result.json  (numbers only -- safe to export)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("sample", "score"):
        p = sub.add_parser(name)
        p.add_argument("--dir", default="era_audit")
        if name == "sample":
            p.add_argument("--verified", default="data/verified")
            p.add_argument("--n", type=int, default=50, help="items per cell (4 cells)")
            p.add_argument("--split", type=int, default=1940, help="first year of the late era")
            p.add_argument("--seed", type=int, default=SEED)
    args = ap.parse_args()
    (cmd_sample if args.cmd == "sample" else cmd_score)(args)
