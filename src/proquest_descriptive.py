"""Score and describe annual machine-verified ProQuest forecasts, without ML.

Run from the repo root using pandas, numpy, matplotlib and xlrd.
All output paths are separate from the historical LOC analysis.
"""
import argparse
import base64
from functools import lru_cache
import hashlib
import html
import json
from pathlib import Path
import re

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from analyze_proquest import annual_files
from score_predictions import predicted_norm

REF = Path("data/reference/proquest")
OUT = Path("data/scored/proquest/descriptive")
BANDS = {"general_business": 2., "markets": 5., "prices": 1.5, "employment": .5}


def paper_name(title):
    text = str(title).lower()
    for fragment, name in [("wall street journal", "Wall Street Journal"),
                           ("new york times", "New York Times"),
                           ("los angeles times", "Los Angeles Times"),
                           ("chicago", "Chicago Tribune"),
                           ("washington post", "Washington Post"),
                           ("boston", "Boston Globe"),
                           ("barron", "Barron's"),
                           ("christian science monitor", "Christian Science Monitor"),
                           ("usa today", "USA Today")]:
        if fragment in text:
            return name
    return str(title)


def horizon(row):
    """Honor positive integer 1–24 month horizons; never clip malformed labels."""
    value = str(row.get("horizon_months", "")).strip()
    try:
        number = float(value)
        if np.isfinite(number) and number.is_integer() and 1 <= number <= 24:
            return int(number), "stated", None
        return None, None, "numeric horizon outside 1–24 months"
    except ValueError:
        pass
    if value != "vague":
        return None, None, "unusable horizon label"
    hint = row.get("horizon_hint")
    if hint not in {"default", "inferred_short", "inferred_long"}:
        return None, None, "unusable horizon hint"
    return {"default": 12, "inferred_short": 6, "inferred_long": 24}[hint], hint, None


def realized_outcome(series, topic, month, months, bands=None):
    bands = bands or BANDS
    start, end = pd.Period(month, freq="M"), pd.Period(month, freq="M") + months
    values = series[topic]
    if topic == "general_business" and start < values.index.min():
        rec = series["recession"].reindex(pd.period_range(start, end, freq="M"))
        if rec.isna().any():
            return None, None, "outside NBER proxy coverage"
        return ("worsen" if rec.mean() >= .5 else "improve"), "NBER proxy", None
    if start not in values.index or end not in values.index:
        return None, None, "outside benchmark coverage"
    first, last = values.loc[start], values.loc[end]
    if pd.isna(first) or pd.isna(last) or first == 0:
        return None, None, "missing benchmark endpoint"
    change = last - first if topic == "employment" else 100 * (last / first - 1)
    up, down = ("up", "down") if topic in {"prices", "employment"} else ("improve", "worsen")
    above = change > bands[topic] and not np.isclose(change, bands[topic], rtol=1e-10, atol=1e-10)
    below = change < -bands[topic] and not np.isclose(change, -bands[topic], rtol=1e-10, atol=1e-10)
    realized = up if above else down if below else "flat"
    basis = {"general_business": "INDPRO", "markets": "Shiller S&P", "prices": "CPI", "employment": "UNRATE"}[topic]
    return realized, basis, None


def load_reference():
    series, metadata = {}, {}
    for topic, sid in [("general_business", "INDPRO"), ("prices", "CPIAUCNS"),
                       ("employment", "UNRATE"), ("recession", "USREC")]:
        path = REF / f"fred_{sid}.csv"
        frame = pd.read_csv(path)
        values = pd.to_numeric(frame.iloc[:, 1], errors="coerce")
        months = pd.PeriodIndex(pd.to_datetime(frame.iloc[:, 0]), freq="M")
        series[topic] = pd.Series(values.to_numpy(), index=months).dropna()
        metadata[topic] = {"series": sid, "source": f"https://fred.stlouisfed.org/series/{sid}",
                           "file": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                           "coverage": [str(series[topic].index.min()), str(series[topic].index.max())],
                           "snapshot": "Existing local FRED cache; original retrieval date unavailable"}
    path = REF / "shiller_ie_data.xls"
    frame = pd.read_excel(path, sheet_name="Data", header=None)
    dates = pd.to_numeric(frame.iloc[:, 0], errors="coerce")
    prices = pd.to_numeric(frame.iloc[:, 1], errors="coerce")
    ok = dates.notna() & prices.notna() & (dates >= 1871) & (dates < 2100)
    dates, prices = dates[ok], prices[ok]
    years = np.floor(dates).astype(int)
    months = np.rint((dates - years) * 100).astype(int)
    assert months.between(1, 12).all()
    idx = pd.PeriodIndex([f"{y}-{m:02d}" for y, m in zip(years, months)], freq="M")
    series["markets"] = pd.Series(prices.to_numpy(), index=idx)
    assert series["markets"].index.is_unique
    metadata["markets"] = {"series": "Shiller S&P Composite nominal price P",
                            "source": "https://shillerdata.com/", "downloaded": "2026-09-16",
                            "file": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                            "coverage": [str(idx.min()), str(idx.max())],
                            "notes": "Monthly average price, excluding dividends; one consistent series across the corpus"}
    return series, metadata


def score_claims(directory, series, *, source_set="verified"):
    """Apply identical outcome rules with an explicit raw sensitivity adapter.

    Existing callers remain verified-only. Raw inputs must be requested by name;
    no verification field is fabricated, and verifier prose never enters scores.
    Record IDs are source-local file/line addresses, not cross-set claim IDs.
    """
    if source_set not in {"verified", "raw"}:
        raise ValueError(f"Unknown ProQuest source set: {source_set}")
    @lru_cache(maxsize=None)
    def outcome(topic, month, months):
        return realized_outcome(series, topic, month, months)

    rows = []
    for path in annual_files(directory):
        with path.open() as source:
            for line_number, line in enumerate(source, 1):
                if not line.strip():
                    continue
                claim = json.loads(line)
                if claim.get("no_predictions"):
                    continue
                if claim.get("source") != "proquest" or claim.get("schema_version") != 2:
                    raise ValueError(f"Unexpected corpus: {path}:{line_number}")
                if source_set == "verified" and "verify_reason" not in claim:
                    raise ValueError(f"Not a machine-verified claim: {path}:{line_number}")
                if source_set == "raw" and "verify_reason" in claim:
                    raise ValueError(f"Verified claim in raw sensitivity input: {path}:{line_number}")
                printed = pd.Timestamp(claim["date"])
                assert printed.year == int(path.name.split('_')[-1].split('.')[0])
                months, hb, error = horizon(claim)
                topic = claim.get("topic")
                pred = predicted_norm(claim)
                realized, basis = None, None
                if claim.get("scope") != "national":
                    error = "not explicitly US-national"
                elif topic not in BANDS:
                    error = "topic has no defensible benchmark"
                elif pred is None:
                    error = "no scorable direction"
                elif not error:
                    realized, basis, error = outcome(topic, str(printed.to_period("M")), months)
                baseline = {"general_business": "improve", "markets": "improve", "prices": "up", "employment": "down"}.get(topic)
                rec = series["recession"].get(printed.to_period("M"), np.nan)
                rows.append({"record_id": f"{printed.year}:{line_number}",
                             "page_id": claim["page_id"], "date": printed.date().isoformat(),
                             "year": printed.year, "decade": printed.year // 10 * 10,
                             "publisher_original": claim.get("publisher") or claim.get("newspaper_title"),
                             "paper": paper_name(claim.get("publisher") or claim.get("newspaper_title")),
                             **{k: claim.get(k) for k in ["topic", "scope", "direction", "confidence", "voice", "horizon_months", "horizon_hint"]},
                             "horizon_used": months, "horizon_basis": hb,
                             "predicted_norm": pred, "realized": realized, "basis": basis,
                             "scorable": error is None, "unscorable_reason": error,
                             "hit": int(pred == realized) if error is None else np.nan,
                             "fixed_baseline_hit": int(baseline == realized) if error is None else np.nan,
                             "recession_at_print": rec})
    return pd.DataFrame(rows)


def add_comparisons(scored):
    scored = scored.copy()
    scored["skill_vs_fixed"] = scored["hit"] - scored["fixed_baseline_hit"]
    scored["horizon_bucket"] = pd.cut(scored["horizon_used"], [0, 6, 12, 24], labels=["1–6", "7–12", "13–24"]).astype(str)
    keys = ["year", "topic", "basis", "horizon_basis", "horizon_bucket"]
    overall = scored.groupby(keys)["hit"].transform("sum")
    n_overall = scored.groupby(keys)["hit"].transform("size")
    own = scored.groupby(keys + ["paper"])["hit"].transform("sum")
    n_own = scored.groupby(keys + ["paper"])["hit"].transform("size")
    peers = n_overall - n_own
    scored["peer_hit_rate"] = ((overall - own) / peers).where(peers >= 20)
    scored["peer_adjusted_gap"] = scored["hit"] - scored["peer_hit_rate"]
    return scored


def block_interval(group, reps=1500):
    blocks = group.groupby(group["year"] // 5)["hit"].agg(["sum", "count"])
    if len(blocks) < 4:
        return np.nan, np.nan
    rng = np.random.default_rng(20260916)
    draws = rng.integers(0, len(blocks), size=(reps, len(blocks)))
    rates = blocks["sum"].to_numpy()[draws].sum(axis=1) / blocks["count"].to_numpy()[draws].sum(axis=1)
    return tuple(np.quantile(rates, [.025, .975]))


def summary(frame, key, intervals=False):
    rows = []
    for value, group in frame.groupby(key, observed=True):
        row = {key: value, "n_claims": len(group), "n_articles": group["page_id"].nunique(),
               "first_year": group["year"].min(), "last_year": group["year"].max(),
               "hit_rate": group["hit"].mean(),
               "fixed_baseline": group["fixed_baseline_hit"].mean(),
               "gap_vs_fixed": group["skill_vs_fixed"].mean(),
               "article_equal_weight_hit_rate": group.groupby("page_id")["hit"].mean().mean(),
               "peer_adjusted_gap": group["peer_adjusted_gap"].mean(),
               "peer_comparable_claims": group["peer_adjusted_gap"].notna().sum()}
        if intervals:
            row["block_ci_low"], row["block_ci_high"] = block_interval(group)
        rows.append(row)
    return pd.DataFrame(rows)


def sensitivities(scored, series):
    rows = []
    for name, multiplier, default in [("Primary", 1., 12), ("Half change bands", .5, 12),
                                       ("Double change bands", 2., 12), ("Default horizon 6 months", 1., 6),
                                       ("Default horizon 24 months", 1., 24)]:
        @lru_cache(maxsize=None)
        def outcome(topic, month, months):
            return realized_outcome(series, topic, month, months,
                                    {k: v * multiplier for k, v in BANDS.items()})[0]
        actual = [outcome(row.topic, row.date[:7], default if row.horizon_basis == "default" else int(row.horizon_used))
                  for row in scored.itertuples()]
        actual = pd.Series(actual, index=scored.index)
        ok = actual.notna()
        fixed = scored.topic.map({"general_business": "improve", "markets": "improve", "prices": "up", "employment": "down"})
        rows.append({"specification": name, "n_claims": int(ok.sum()),
                     "hit_rate": (scored.loc[ok, "predicted_norm"] == actual[ok]).mean(),
                     "fixed_baseline": (fixed[ok] == actual[ok]).mean()})
    no_market = scored[scored.topic != "markets"]
    rows.append({"specification": "Exclude market proxy scoring", "n_claims": len(no_market),
                 "hit_rate": no_market.hit.mean(), "fixed_baseline": no_market.fixed_baseline_hit.mean()})
    result = pd.DataFrame(rows)
    result["gap_vs_fixed"] = result.hit_rate - result.fixed_baseline
    return result


def save_figures(tables, scored, out):
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11,
                         "axes.spines.top": False, "axes.spines.right": False,
                         "figure.facecolor": "white", "axes.titleweight": "bold"})
    figures = []
    def save(fig, name):
        fig.savefig(out / name, dpi=160, bbox_inches="tight")
        plt.close(fig); figures.append(name)
    ranked = tables["publishers"].query("n_claims >= 500").sort_values("hit_rate")
    fig, ax = plt.subplots(figsize=(10, 5))
    positions = np.arange(len(ranked))
    ax.errorbar(ranked.hit_rate * 100, positions,
                xerr=np.vstack([(ranked.hit_rate - ranked.block_ci_low).clip(lower=0), (ranked.block_ci_high - ranked.hit_rate).clip(lower=0)]) * 100,
                fmt="o", color="#174e70", capsize=4, label="Forecast hit rate with 5-year block interval")
    ax.scatter(ranked.fixed_baseline * 100, positions, marker="x", color="#d47835", label="Fixed-direction baseline on the same claims")
    ax.set_yticks(positions, [f"{p}  (n={n:,})" for p, n in zip(ranked.paper, ranked.n_claims)])
    ax.set_xlabel("Correct forecasts (%)"); ax.set_title("Publisher ranking depends on coverage and era")
    ax.legend(fontsize=8, loc="lower right"); ax.grid(axis="x", alpha=.2)
    save(fig, "publishers.png")
    adjusted = ranked.sort_values("peer_adjusted_gap")
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.barh(adjusted.paper, adjusted.peer_adjusted_gap * 100,
            color=np.where(adjusted.peer_adjusted_gap >= 0, "#174e70", "#d47835"))
    ax.axvline(0, color="#778", linewidth=1)
    ax.set_xlabel("Hit-rate gap versus comparable other-paper forecasts (percentage points)")
    ax.set_title("Publisher differences shrink after a coverage adjustment")
    ax.grid(axis="x", alpha=.2); save(fig, "publisher_adjustment.png")
    fig, ax = plt.subplots(figsize=(10, 4.8))
    for name, color in [("decades", "#174e70"), ("decades_grounded", "#738b32")]:
        table = tables[name]
        ax.plot(table.decade, table.hit_rate * 100, "o-", color=color,
                label="All scorable claims" if name == "decades" else "Claim-grounded horizons only")
    table = tables["decades"]
    ax.plot(table.decade, table.fixed_baseline * 100, "x--", color="#d47835", label="Fixed-direction baseline")
    ax.set_ylabel("Correct forecasts (%)"); ax.set_xlabel("Publication decade (2010 is one year)")
    ax.set_title("Forecast performance across the annual ProQuest corpus")
    ax.legend(fontsize=9); ax.grid(alpha=.2)
    save(fig, "decades.png")
    fig, ax = plt.subplots(figsize=(10, 5))
    groups = scored.groupby(["decade", "topic"])["hit"].agg(["mean", "size"]).reset_index()
    for topic, group in groups.groupby("topic"):
        group = group[group["size"] >= 50]
        ax.plot(group.decade, group["mean"] * 100, "o-", label=topic.replace('_', ' ').title())
    ax.set_ylabel("Correct forecasts (%)"); ax.set_xlabel("Publication decade (2010 is one year)")
    ax.set_title("Topic-specific trends reveal changes hidden by pooled rates")
    ax.legend(fontsize=9); ax.grid(alpha=.2); save(fig, "topics_over_time.png")
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.8))
    for ax, key, label in [(axes[0], "confidence", "Hedging"), (axes[1], "voice", "Attributed forecast voice")]:
        table = tables[key].query("n_claims >= 100").sort_values("hit_rate")
        ax.barh(table[key], table.hit_rate * 100, color="#174e70")
        for i, row in enumerate(table.itertuples()):
            ax.text(row.hit_rate * 100 + .7, i, f"{row.hit_rate:.1%} · n={row.n_claims:,}", va="center", fontsize=8)
        ax.set_xlim(0, 85); ax.set_xlabel("Correct forecasts (%)"); ax.set_title(label)
    fig.suptitle("Descriptive differences; topic and era mix can explain them", fontsize=12)
    fig.tight_layout(); save(fig, "hedging_and_voice.png")
    fig, ax = plt.subplots(figsize=(10, 4.8))
    nat = scored[scored.topic.isin(["general_business", "markets"])]
    optimism = nat.groupby("decade")["direction"].agg(lambda d: (d == "improve").sum() / d.isin(["improve", "worsen"]).sum())
    ax.plot(optimism.index, optimism * 100, "o-", color="#174e70")
    ax.axhline(50, color="#999", linestyle="--", linewidth=1)
    ax.set_ylabel("Upbeat business/market forecasts (%)")
    ax.set_xlabel("Publication decade (2010 is one year)"); ax.set_title("The optimism/pessimism mix changed over time")
    ax.grid(alpha=.2); save(fig, "optimism.png")
    return figures


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--claims-dir", type=Path, default=Path("data/proquest/verified"))
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    series, metadata = load_reference()
    claims = score_claims(args.claims_dir, series)
    scored = add_comparisons(claims[claims.scorable])
    claims.to_csv(args.out / "scored_claims.csv.gz", index=False, compression="gzip")
    tables = {"publishers": summary(scored, "paper", True),
              "publishers_grounded": summary(scored[scored.horizon_basis != "default"], "paper", True),
              "publishers_common_period": summary(scored[scored.year.between(1960, 2010)], "paper", True),
              "decades": summary(scored, "decade", True),
              "decades_grounded": summary(scored[scored.horizon_basis != "default"], "decade", True),
              "yearly": summary(scored, "year"), "topics": summary(scored, "topic"),
              "confidence": summary(scored, "confidence"), "voice": summary(scored, "voice"),
              "horizons": summary(scored, "horizon_basis"),
              "economic_state": summary(scored.assign(economic_state=np.where(scored.recession_at_print == 1, "Recession at print", "Expansion at print")), "economic_state")}
    for name, table in tables.items():
        table.to_csv(args.out / f"{name}.csv", index=False)
    reasons = claims[~claims.scorable].unscorable_reason.value_counts()
    reasons.rename_axis("reason").rename("n_claims").to_csv(args.out / "exclusions.csv")
    robustness = sensitivities(scored, series)
    robustness.to_csv(args.out / "sensitivity.csv", index=False)
    scored.groupby(["year", "topic"])["hit"].agg(["mean", "size"]).to_csv(args.out / "year_topic.csv")
    scored.groupby(["paper", "topic"])["hit"].agg(["mean", "size"]).to_csv(args.out / "publisher_topic.csv")
    figures = save_figures(tables, scored, args.out)
    ranking = tables["publishers"].query("n_claims >= 500").sort_values("hit_rate", ascending=False)
    topics = tables["topics"].sort_values("hit_rate", ascending=False)
    confidence = tables["confidence"].set_index("confidence")
    voices = tables["voice"].set_index("voice")
    barrons_gap = ranking.set_index("paper").loc["Barron's", "peer_adjusted_gap"]
    journal_gap = ranking.set_index("paper").loc["Wall Street Journal", "peer_adjusted_gap"]
    optimism_sample = scored[scored.topic.isin(["general_business", "markets"])]
    optimism = optimism_sample.groupby("decade")["direction"].agg(
        lambda d: (d == "improve").sum() / d.isin(["improve", "worsen"]).sum())
    optimism.rename("upbeat_share_directional_business_markets").to_csv(args.out / "optimism_by_decade.csv")
    total = {"verified_claims": len(claims), "scorable_claims": len(scored),
             "hit_rate": scored.hit.mean(), "fixed_baseline": scored.fixed_baseline_hit.mean(),
             "grounded_claims": int((scored.horizon_basis != "default").sum()),
             "grounded_hit_rate": scored[scored.horizon_basis != "default"].hit.mean(),
             "article_equal_weight_hit_rate": scored.groupby("page_id").hit.mean().mean(),
             "input_directory": str(args.claims_dir), "reference": metadata,
             "rules": {"bands": BANDS, "max_horizon_months": 24, "default_horizon_months": 12,
                       "inferred_short_months": 6, "inferred_long_months": 24,
                       "scope": "explicit national only", "rank_minimum_claims": 500}}
    (args.out / "summary.json").write_text(json.dumps(total, indent=2) + "\n")
    def md_table(table, key):
        lines = [f"| {key.replace('_', ' ').title()} | Scored claims | Hit rate | Fixed baseline | Gap (pp) |",
                 "| --- | ---: | ---: | ---: | ---: |"]
        for _, row in table.iterrows():
            lines.append(f"| {row[key]} | {row.n_claims:,} | {row.hit_rate:.1%} | {row.fixed_baseline:.1%} | {row.gap_vs_fixed * 100:+.1f} |")
        return "\n".join(lines)
    report = ["# Machine-verified ProQuest forecasts: first descriptive analysis", "",
              f"Of {len(claims):,} verified claims, {len(scored):,} ({len(scored)/len(claims):.1%}) can be scored under the documented rules. "
              f"The pooled hit rate is **{scored.hit.mean():.1%}**, compared with **{scored.fixed_baseline_hit.mean():.1%}** "
              "for a fixed-direction forecast evaluated on exactly the same claims. "
              "That baseline always predicts production and stock prices rise, consumer prices rise, and unemployment falls. "
              "It is a simple deterministic comparison, not a fitted model.", "",
              f"Claim-grounded horizons: {total['grounded_claims']:,} claims, {total['grounded_hit_rate']:.1%} hit rate. "
              f"Giving each article equal weight instead of each claim yields {total['article_equal_weight_hit_rate']:.1%}.", "",
              "## Interesting patterns", "",
              f"- Barron's has the highest raw rate ({ranking.iloc[0].hit_rate:.1%}), followed closely by the Boston Globe "
              f"({ranking[ranking.paper == 'Boston Globe'].iloc[0].hit_rate:.1%}). All eight ranked papers trail the fixed-direction baseline on their own claim mix.",
              f"- Coverage adjustment changes the story. Barron's is about {barrons_gap * 100:.1f} "
              "percentage points above comparable other-paper forecasts, "
              f"while the Wall Street Journal is about {journal_gap * 100:.1f} "
              "point above them despite its low raw rate. "
              f"The Journal's claims begin in {claims[claims.paper == 'Wall Street Journal'].year.min()}; "
              "this is one reason a full-century raw ranking can mislead.",
              "- There is no steady upward trend. Pooled hit rates are 49.9% in the 1960s, 36.1% in both the 1980s and 1990s, "
              "and 42.7% in the 2000s. General-business-only rates show a similar mid-century peak and later decline, "
              "but the sampled publications and horizons still change.",
              f"- Assertive forecasts are correct {confidence.loc['assertive', 'hit_rate']:.1%} of the time, versus "
              f"{confidence.loc['hedged', 'hit_rate']:.1%} for hedged forecasts. This association does not prove that confidence improves forecasting.",
              f"- Official voices have a {voices.loc['official', 'hit_rate']:.1%} hit rate, journalists "
              f"{voices.loc['journalist', 'hit_rate']:.1%}, and quoted experts {voices.loc['expert', 'hit_rate']:.1%}. "
              "Expert attribution alone does not identify more successful forecasts in this sample.",
              f"- Upbeat business/market calls shrink from {optimism.loc[1900]:.1%} of directional forecasts in the 1900s "
              f"to {optimism.loc[2000]:.1%} in the 2000s. This is the mix of scorable extracted forecasts, not a measure of all newspaper sentiment.", "",
              "## Which papers had the highest hit rate?", "", md_table(ranking, "paper"), "",
              "These are forecasts published by each paper, often quotations from outside experts. "
              "They do not measure the newspaper staff's own forecasting ability. Historical editions are merged by newspaper family. "
              "USA Today is retained in the data but excluded from the ranking when below 500 scored claims.", "",
              "Publisher intervals in the figure resample nonoverlapping five-year publication blocks (1,500 draws). "
              "These account for some shared economic conditions but are descriptive, not evidence of a statistically significant ranking. "
              "The publisher CSVs also report equal-article weighting, claim-grounded horizons, a restricted 1960–2010 period (coverage still differs by paper), "
              "and a peer comparison within year/topic/benchmark/horizon basis/horizon bucket. "
              "Peer means exclude the paper itself and require at least 20 other-paper claims. "
              "The adjusted gap is an exploratory coverage adjustment, not a causal effect or ML model.", "",
              "## Trends across decades", "", md_table(tables["decades"], "decade"), "",
              "2010 contains only one publication year. Early business forecasts use a recession-state proxy, "
              "whereas business forecasts from 1919 use industrial production. Employment enters only from 1948, prices from 1913. "
              "Do not read the pooled decade line as a clean test of improvement: benchmark and topic mix change.", "",
              "## Topic, hedging, and forecast voice", "", md_table(topics, "topic"), "",
              md_table(tables["confidence"], "confidence"), "", md_table(tables["voice"].query("n_claims >= 100"), "voice"), "",
              "Hedged vs assertive and voice differences are associations. Their topic, era, and horizon mixtures differ. "
              "No numerical confidence probabilities were extracted, so this analysis does not invent Brier scores from the hedging label.", "",
              "## Sensitivity checks", "", md_table(robustness, "specification"), "",
              "The sensitivity checks start with the primary eligible claims and recompute their outcomes under half/double change bands "
              "or a 6/24-month default for vague, uninferred horizons. Claims with no endpoint under an alternative are omitted. "
              "The last row drops the provisional market benchmark altogether. These checks assess rule dependence, not extraction validity.", "",
              "## Scoring rules and limitations", "",
              "Only explicit national scope and the four supported topics enter scoring. 'Other' and nonstandard topics are excluded. "
              "Forecast direction is compared to the change between the publication month and the horizon endpoint. "
              "A real change must exceed 2% for production, 1.5% for consumer prices, 0.5 percentage points for unemployment, "
              "or 5% for stock prices. Values exactly on a threshold count as flat. These are inherited research bands, not tuned on these results.", "",
              "Positive integer horizons of 1–24 months are respected. Longer or malformed numeric horizons and unusable labels are excluded, "
              "rather than clipped or silently replaced. Vague horizons use the exported inference (6 or 24 months), or an explicit 12-month default. "
              "Before industrial production begins, business forecasts use whether at least half of the inclusive horizon window is in recession "
              "according to USREC; this is a weaker state proxy, explicitly labeled NBER proxy. "
              "Endpoint values must exist; no extrapolation or forward filling is used.", "",
              "Market claims use Shiller's monthly-average nominal S&P Composite price series consistently across the whole corpus, "
              "excluding dividends. Broad market predictions are only approximate matches to this benchmark, especially claims about bonds "
              "or particular securities. Monthly averages also include days after the claim's publication date. "
              "Treat the market results as provisional topic-level proxy scoring; the exports lack quotes needed to identify the precise asset.", "",
              "Realized outcomes use revised reference values, appropriate for retrospective scoring. This is not a real-time prediction model. "
              "Machine verification does not remove all extraction errors. Stripped quotes make semantic rechecking and definitive claim deduplication "
              "impossible locally; identical labels are retained. Claims share articles, dates, and macro outcomes. "
              "There is no LOC analysis, crisis-window dataset, fitted ML model, or claim-volume attention measure here.", "",
              "### Excluded verified claims", ""]
    report += [f"- {reason}: {count:,}" for reason, count in reasons.items()]
    report += ["", "### Economic reference sources", ""]
    report += [f"- [{data['series']}]({data['source']}): {data['coverage'][0]} through {data['coverage'][1]}. "
               f"SHA-256 and snapshot provenance in summary.json." for data in metadata.values()]
    (args.out / "report.md").write_text("\n".join(report) + "\n")
    style = "body{font:16px system-ui,sans-serif;color:#17364b;max-width:1100px;margin:40px auto;padding:0 24px;line-height:1.55}h1{font-size:32px}h2{margin-top:42px}table{border-collapse:collapse;width:100%;font-size:14px}td,th{padding:9px;border-bottom:1px solid #dce5ec;text-align:right}td:first-child,th:first-child{text-align:left}img{width:100%;margin:22px 0}p{max-width:1000px}small{color:#607482}"
    # Build the standalone report from the same markdown paragraphs and tables.
    blocks, table_lines = [], []
    images = {name: f'<img alt="{name.replace("_", " ").replace(".png", "")}" src="data:image/png;base64,{base64.b64encode((args.out/name).read_bytes()).decode()}">' for name in figures}
    section_images = {"Which papers had the highest hit rate?": ["publishers.png", "publisher_adjustment.png"],
                      "Trends across decades": ["decades.png", "topics_over_time.png", "optimism.png"],
                      "Topic, hedging, and forecast voice": ["hedging_and_voice.png"]}
    def flush_table():
        if not table_lines:
            return
        body = []
        for i, line in enumerate(table_lines):
            if i == 1:
                continue
            tag = "th" if i == 0 else "td"
            body.append("<tr>" + "".join(f"<{tag}>{html.escape(cell.strip())}</{tag}>" for cell in line.strip('|').split('|')) + "</tr>")
        blocks.append("<table>" + "".join(body) + "</table>"); table_lines.clear()
    for line in report:
        for part in line.split('\n'):
            if part.startswith('|'):
                table_lines.append(part); continue
            flush_table()
            if part.startswith('#'):
                level = len(part) - len(part.lstrip('#'))
                blocks.append(f"<h{level}>{html.escape(part[level:].strip())}</h{level}>")
                blocks.extend(images[name] for name in section_images.get(part[level:].strip(), []))
            elif part:
                escaped = html.escape(part)
                escaped = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', escaped)
                escaped = re.sub(r'\[([^\]]+)\]\((https?://[^)]+)\)', r'<a href="\2">\1</a>', escaped)
                blocks.append(f"<p>{escaped}</p>")
    flush_table()
    (args.out / "report.html").write_text('<!doctype html><html lang="en"><meta charset="utf-8"><title>ProQuest forecast analysis</title><style>'+style+'</style><body>'+''.join(blocks)+'</body></html>')
    print(json.dumps({k: v for k, v in total.items() if k not in {"reference", "rules"}}, indent=2))
    print(ranking[["paper", "n_claims", "hit_rate", "fixed_baseline", "peer_adjusted_gap"]].to_string(index=False))
    print(f"Report: {args.out / 'report.html'}")


if __name__ == "__main__":
    main()
