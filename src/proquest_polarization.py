"""Build two distinct, backward-looking polarization features for ProQuest.

Public Voteview files are cached only with --download. No ProQuest source edits.
NOMINATE scores and fitted vote probabilities are never used as predictors.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import urllib.request

import numpy as np
import pandas as pd

from proquest_panel import forecast_features

OUT = Path("data/scored/proquest/polarization")
FEATURES = ("political_polarization", "forecast_polarization")


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def fetch(url, path):
    if not path.exists():
        with urllib.request.urlopen(url, timeout=120) as response:
            content = response.read()
        if not content.startswith(b"congress,"):
            raise ValueError(f"Unexpected Voteview CSV: {url}")
        temporary = path.with_suffix(".part")
        temporary.write_bytes(content)
        temporary.replace(path)
    return {"url": url, "path": str(path), "sha256": digest(path)}


def download():
    cache = OUT / "source_cache"
    cache.mkdir(parents=True, exist_ok=True)
    tasks = [(f"https://voteview.com/static/data/out/{kind}/HSall_{kind}.csv", cache / f"HSall_{kind}.csv")
             for kind in ("members", "rollcalls")]
    tasks += [(f"https://voteview.com/static/data/out/votes/H{c:03d}_votes.csv", cache / f"H{c:03d}_votes.csv")
              for c in range(55, 112)]
    with ThreadPoolExecutor(max_workers=4) as pool:
        sources = list(pool.map(lambda pair: fetch(*pair), tasks))
    (OUT / "download_manifest.json").write_text(json.dumps({
        "retrieved_date": "2026-10-14", "provider": "Voteview Congressional Roll-Call Votes Database",
        "sources": sources, "note": "Current historical reconstruction; not historical release vintages. Existing cached files retained."
    }, indent=2) + "\n")
    print(f"Cached {len(sources)} public Voteview files", flush=True)


def party_separation(votes, members, rollcalls, minimum_party_votes=5):
    """Mean-party yes-share distance on each dated House vote, range [0,1]."""
    keys = ["congress", "chamber", "icpsr"]
    members = members[keys + ["party_code"]].drop_duplicates()
    ambiguous = members.groupby(keys).party_code.nunique()
    bad = ambiguous[ambiguous > 1].reset_index()[keys]
    members = members.merge(bad.assign(ambiguous=True), on=keys, how="left")
    members = members[members.ambiguous.isna()].drop(columns="ambiguous")
    if votes.duplicated(keys + ["rollnumber"]).any():
        raise ValueError("Duplicate member vote")
    cast = votes[votes.chamber.eq("House") & votes.cast_code.isin([1, 6])].copy()
    cast = cast.merge(members, on=keys, how="left", validate="many_to_one")
    unmatched = int(cast.party_code.isna().sum())
    cast = cast[cast.party_code.isin([100, 200])].copy()
    cast["yes"] = cast.cast_code.eq(1).astype(int)
    vote_keys = ["congress", "chamber", "rollnumber"]
    grouped = cast.groupby(vote_keys + ["party_code"]).yes.agg(["mean", "size"]).unstack("party_code")
    grouped = grouped.reindex(columns=pd.MultiIndex.from_product([["mean", "size"], [100, 200]]))
    eligible = (grouped["size"] >= minimum_party_votes).all(axis=1)
    gap = (grouped["mean"][200] - grouped["mean"][100]).abs()
    result = pd.DataFrame({"political_gap": gap[eligible],
                           "democratic_votes": grouped["size"][100][eligible],
                           "republican_votes": grouped["size"][200][eligible]}).reset_index()
    dates = rollcalls[vote_keys + ["date"]]
    if dates.duplicated(vote_keys).any():
        raise ValueError("Duplicate rollcall date key")
    result = result.merge(dates, on=vote_keys, how="left", validate="one_to_one")
    result["date"] = pd.to_datetime(result.date, errors="coerce")
    missing_dates = int(result.date.isna().sum())
    return result.dropna(subset=["date"]), {
        "unmatched_or_ambiguous_member_casts": unmatched,
        "ambiguous_member_keys": len(bad), "missing_vote_dates": missing_dates,
        "votes_without_two_eligible_parties": int((~eligible).sum())}


def political_months(rollcalls, origins, minimum_rollcalls=10):
    rows = []
    for origin in origins:
        # Twelve full months ending at t-2; t-1 is a reporting buffer.
        start, stop = (origin - 13).start_time, (origin - 1).start_time
        window = rollcalls[rollcalls.date.ge(start) & rollcalls.date.lt(stop)]
        rows.append({"origin": str(origin), "political_polarization":
                     window.political_gap.mean() if len(window) >= minimum_rollcalls else np.nan,
                     "political_rollcalls": len(window),
                     "political_latest_vote": window.date.max(),
                     "political_window_start": start.date().isoformat(),
                     "political_window_stop_exclusive": stop.date().isoformat()})
    return pd.DataFrame(rows)


def forecast_months(national, support, origins):
    """Opposing forecast camps, separate from existing three-class impurity."""
    business = national[national.topic.eq("general_business")].copy()
    business["month"] = pd.PeriodIndex(business.month, freq="M")
    business = business.set_index("month")
    if not business.index.is_unique:
        raise ValueError("Duplicate national month")
    support = support.copy()
    support["origin"] = pd.PeriodIndex(support.origin, freq="M")
    support = support.set_index("origin")
    if not support.index.is_unique:
        raise ValueError("Duplicate support origin")
    rows = []
    for origin in origins:
        recent = business.reindex(pd.period_range(origin - 3, origin - 1, freq="M"))
        ok = origin in support.index and pd.notna(support.loc[origin, "disagreement_3m"])
        product = 4 * recent.positive_share * recent.negative_share
        value = product.mean() if ok else np.nan
        rows.append({"origin": str(origin), "forecast_polarization": value,
                     "forecast_latest_print_month": str(origin - 1),
                     "forecast_observed_months": int(product.notna().sum())})
    return pd.DataFrame(rows)


def build():
    manifest_path = OUT / "download_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    tracked = {r["path"]: r["sha256"] for r in manifest["sources"]}
    for path, expected in tracked.items():
        if digest(path) != expected:
            raise ValueError(f"Changed cached input: {path}")
    cache = OUT / "source_cache"
    members = pd.read_csv(cache / "HSall_members.csv", usecols=["congress", "chamber", "icpsr", "party_code"])
    rollcalls = pd.read_csv(cache / "HSall_rollcalls.csv", usecols=["congress", "chamber", "rollnumber", "date"])
    pieces, audits = [], []
    for c in range(55, 112):
        votes = pd.read_csv(cache / f"H{c:03d}_votes.csv", usecols=["congress", "chamber", "rollnumber", "icpsr", "cast_code"])
        piece, audit = party_separation(votes, members[members.congress.eq(c)], rollcalls[rollcalls.congress.eq(c)])
        pieces.append(piece); audits.append({"congress": c, **audit, "eligible_rollcalls": len(piece)})
    political = pd.concat(pieces, ignore_index=True)
    origins = pd.period_range("1900-01", "2010-12", freq="M")
    feature = political_months(political, origins)
    base = Path("data/scored/proquest/monthly_information")
    for name in ("national_topic_month.csv.gz", "newspaper_topic_month.csv.gz", "panel_manifest.json"):
        tracked[str(base / name)] = digest(base / name)
    panel_manifest = json.loads((base / "panel_manifest.json").read_text())
    for path, expected in panel_manifest["sources"].items():
        if digest(path) != expected:
            raise ValueError(f"ProQuest panel input changed: {path}")
    tracked.update(panel_manifest["sources"])
    national = pd.read_csv(base / "national_topic_month.csv.gz")
    paper = pd.read_csv(base / "newspaper_topic_month.csv.gz")
    for frame in (national, paper):
        frame["month"] = pd.PeriodIndex(frame.month, freq="M")
    support = forecast_features(paper, national, origins)
    forecast = forecast_months(national, support, origins)
    feature = feature.merge(forecast, on="origin", validate="one_to_one")
    for name in FEATURES:
        if not feature[name].dropna().between(0, 1).all():
            raise ValueError(f"Polarization outside [0,1]: {name}")
    political.to_csv(OUT / "rollcall_separation.csv.gz", index=False, compression={"method": "gzip", "mtime": 0})
    pd.DataFrame(audits).to_csv(OUT / "rollcall_audit.csv", index=False)
    feature.to_csv(OUT / "features.csv", index=False)
    summary = {"inputs_sha256": tracked, "code_sha256": digest(__file__),
               "spec_sha256": digest(OUT / "evaluation_spec.json"),
               "features_sha256": digest(OUT / "features.csv"),
               "months": len(feature), "observed_months": feature[list(FEATURES)].count().to_dict(),
               "political_measure": "House Democratic–Republican difference in observed yes shares; not DW-NOMINATE or mass/affective polarization",
               "timing": "Only earlier dated votes and print months; reconstructed from current historical data, not an archived real-time index"}
    (OUT / "feature_manifest.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({k: summary[k] for k in ("months", "observed_months")}), flush=True)


def load_features():
    manifest = json.loads((OUT / "feature_manifest.json").read_text())
    if digest(OUT / "features.csv") != manifest["features_sha256"]:
        raise ValueError("Polarization feature file changed")
    if digest(OUT / "evaluation_spec.json") != manifest["spec_sha256"]:
        raise ValueError("Polarization specification changed since feature build")
    frame = pd.read_csv(OUT / "features.csv")
    frame["origin"] = pd.PeriodIndex(frame.origin, freq="M")
    if not frame.origin.is_unique:
        raise ValueError("Duplicate polarization origins")
    return frame, manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download", action="store_true")
    args = parser.parse_args()
    if args.download:
        download()
    build()
