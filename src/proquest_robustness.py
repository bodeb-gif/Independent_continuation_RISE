"""Raw/verified sensitivity for annual ProQuest exports, 1900–2010.

Run from the repository root. Uses frozen local outcomes; no models or network.
Source rows are retained, never paired or deduplicated by stripped labels.
"""
import argparse
import base64
import hashlib
import html
from importlib.metadata import version
import json
from pathlib import Path
import platform

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from analyze_proquest import annual_files
from proquest_descriptive import BANDS, load_reference, score_claims

OUT = Path("data/scored/proquest/robustness")
SETS = ("raw", "verified")
METRICS = ("hit_rate", "fixed_baseline", "gap_vs_fixed")
CELL_KEYS = ["paper", "year", "topic", "basis", "horizon_basis", "horizon_used"]
SEED = 20261013


def source_manifest(base):
    """Include empty-record articles without treating export counts as sampling denominators."""
    hashes, represented, empty = {}, {}, {}
    for name in SETS:
        represented[name], empty[name] = set(), set()
        for path in annual_files(base / name):
            hashes[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
            for line in path.open(encoding="utf-8"):
                if not line.strip():
                    continue
                row = json.loads(line)
                if row.get("schema_version") != 2 or not row.get("page_id"):
                    raise ValueError(f"Invalid export record in {path}")
                page = str(row["page_id"])
                represented[name].add(page)
                if row.get("no_predictions"):
                    empty[name].add(page)
    return hashes, represented, empty


def prepare_scored(frame):
    result = frame.loc[frame.scorable].copy()
    result["month"] = result.date.str[:7]
    result["gap"] = result.hit - result.fixed_baseline_hit
    return result


def weighted_rows(scored, weighting="article"):
    """Each article/month has unit mass within the supplied analysis population."""
    out = scored.copy()
    if weighting == "claim":
        out["mass"] = 1.
    elif weighting in {"article", "month"}:
        key = "page_id" if weighting == "article" else "month"
        out["mass"] = 1. / out.groupby(["source_set", key]).hit.transform("size")
    else:
        raise ValueError(f"Unknown weighting: {weighting}")
    out["hit_sum"] = out.mass * out.hit
    out["baseline_sum"] = out.mass * out.fixed_baseline_hit
    return out


def rates(table):
    mass = table.mass.sum()
    hit = table.hit_sum.sum() / mass if mass else np.nan
    baseline = table.baseline_sum.sum() / mass if mass else np.nan
    return dict(hit_rate=hit, fixed_baseline=baseline, gap_vs_fixed=hit - baseline)


def comparison(name, weighted):
    result = {"comparison": name}
    for subset in SETS:
        for metric, value in rates(weighted[weighted.source_set == subset]).items():
            result[f"{subset}_{metric}"] = value
    for metric in METRICS:
        result[f"delta_{metric}"] = result[f"verified_{metric}"] - result[f"raw_{metric}"]
    return result


def block_intervals(name, weighted, reps=1500):
    """Jointly resample calendar blocks across sets and papers, retaining overlap.

    For matched comparisons, fixed common-cell weights are conditional on the
    observed support. These intervals describe historical variability, not a
    randomized verification effect or independent-claim sampling uncertainty.
    """
    rows = []
    for length in (2, 5, 10):
        data = weighted.assign(block=(weighted.year - 1900) // length)
        blocks = sorted(data.block.unique())
        index = pd.MultiIndex.from_product([blocks, SETS], names=["block", "source_set"])
        sums = data.groupby(["block", "source_set"])[["mass", "hit_sum", "baseline_sum"]].sum()
        values = sums.reindex(index, fill_value=0).to_numpy().reshape(len(blocks), 2, 3)
        point = comparison(name, weighted)
        intervals = np.full((3, 2), np.nan)
        valid_draws = 0
        if len(blocks) >= 4:
            rng = np.random.default_rng(SEED + length)
            draws = rng.integers(0, len(blocks), (reps, len(blocks)))
            totals = values[draws].sum(axis=1)
            ok = (totals[:, :, 0] > 0).all(axis=1)
            totals = totals[ok]
            valid_draws = len(totals)
            if valid_draws:
                hit = totals[:, :, 1] / totals[:, :, 0]
                baseline = totals[:, :, 2] / totals[:, :, 0]
                gaps = np.column_stack([hit[:, 1] - hit[:, 0], baseline[:, 1] - baseline[:, 0],
                                        (hit - baseline)[:, 1] - (hit - baseline)[:, 0]])
                intervals = np.quantile(gaps, [.025, .975], axis=0).T
        for metric, bounds in zip(METRICS, intervals):
            rows.append({"comparison": name, "metric": metric, "block_years": length,
                         "n_blocks": len(blocks), "valid_draws": valid_draws,
                         "verified_minus_raw": point[f"delta_{metric}"],
                         "low": bounds[0], "high": bounds[1]})
    return pd.DataFrame(rows)


def matched_cells(scored, *, exact_month=False, minimum=10):
    """Common composition, retaining every row and using article mass as the base.

    Within a cell, each source uses its own article-weighted mean. Both means
    then receive the same harmonic-overlap mass. Publication-month cells share
    the identical deterministic benchmark outcome; year cells need not.
    """
    keys = CELL_KEYS + (["month"] if exact_month else [])
    weighted = weighted_rows(scored)
    tables = []
    for name in SETS:
        sub = weighted[weighted.source_set == name]
        grouped = sub.groupby(keys, observed=True).agg(
            n_claims=("hit", "size"), n_articles=("page_id", "nunique"),
            mass=("mass", "sum"), hit_sum=("hit_sum", "sum"), baseline_sum=("baseline_sum", "sum"))
        tables.append(grouped.add_prefix(name + "_"))
    cells = tables[0].join(tables[1], how="inner").reset_index()
    cells = cells[(cells.raw_n_claims >= minimum) & (cells.verified_n_claims >= minimum)].copy()
    cells["overlap_mass"] = 2 * cells.raw_mass * cells.verified_mass / (cells.raw_mass + cells.verified_mass)
    rows = []
    for name in SETS:
        cells[f"{name}_hit_rate"] = cells[f"{name}_hit_sum"] / cells[f"{name}_mass"]
        cells[f"{name}_fixed_baseline"] = cells[f"{name}_baseline_sum"] / cells[f"{name}_mass"]
        rows.append(pd.DataFrame({"source_set": name, "year": cells.year,
                                 "mass": cells.overlap_mass,
                                 "hit_sum": cells.overlap_mass * cells[f"{name}_hit_rate"],
                                 "baseline_sum": cells.overlap_mass * cells[f"{name}_fixed_baseline"]}))
    if exact_month and not np.allclose(cells.raw_fixed_baseline, cells.verified_fixed_baseline):
        raise ValueError("Exact-month matching did not preserve benchmark outcomes")
    return cells, pd.concat(rows, ignore_index=True)


def composition_table(frame, key):
    data = frame.assign(category=frame[key].fillna("<missing>").astype(str))
    counts = data.groupby(["category", "source_set"]).size().unstack(fill_value=0).reindex(columns=SETS, fill_value=0)
    result = counts.rename(columns={name: f"{name}_claims" for name in SETS}).reset_index()
    for name in SETS:
        result[f"{name}_share"] = result[f"{name}_claims"] / result[f"{name}_claims"].sum()
    result["share_change_pp"] = 100 * (result.verified_share - result.raw_share)
    result["verified_raw_count_ratio"] = result.verified_claims / result.raw_claims.replace(0, np.nan)
    result.insert(0, "field", key)
    return result


def subgroup_outcomes(scored, key):
    records = []
    for value, group in scored.groupby(key, observed=True):
        for name in SETS:
            sub = group[group.source_set == name]
            row = {key: value, "source_set": name, "n_claims": len(sub), "n_articles": sub.page_id.nunique()}
            for weighting in ("claim", "article"):
                row.update({f"{weighting}_{k}": v for k, v in rates(weighted_rows(sub, weighting)).items()})
            records.append(row)
    return pd.DataFrame(records)


def article_changes(frame, represented, empty):
    """Pair only article IDs; file/line IDs and label tuples are not claim lineage."""
    tables = []
    for name in SETS:
        sub = frame[frame.source_set == name]
        if (sub.groupby("page_id")[["date", "paper"]].nunique() > 1).any().any():
            raise ValueError("An article ID maps to conflicting dates or papers")
        table = sub.groupby("page_id").agg(n_claims=("record_id", "size"), n_scorable=("scorable", "sum"),
                                            date=("date", "first"), paper=("paper", "first"))
        table = table.reindex(sorted(represented[name]))
        table[["n_claims", "n_scorable"]] = table[["n_claims", "n_scorable"]].fillna(0).astype(int)
        table["represented"] = True
        table["has_empty_record"] = table.index.isin(empty[name])
        tables.append(table.add_prefix(name + "_"))
    result = tables[0].join(tables[1], how="outer").rename_axis("page_id").reset_index()
    for name in SETS:
        for field in ("represented", "has_empty_record"):
            result[f"{name}_{field}"] = result[f"{name}_{field}"].eq(True)
    for key in ("date", "paper"):
        both = result[f"raw_{key}"].notna() & result[f"verified_{key}"].notna()
        if not result.loc[both, f"raw_{key}"].eq(result.loc[both, f"verified_{key}"]).all():
            raise ValueError(f"Conflicting article {key} between exports")
    # Missing export representation is not asserted to mean zero retained claims.
    result["claim_count_change"] = result.verified_n_claims - result.raw_n_claims
    return result


def save_figures(composition, decades, coverage, out):
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
                         "axes.spines.top": False, "axes.spines.right": False})
    colors = {"raw": "#60758a", "verified": "#147a72"}
    fig, ax = plt.subplots(figsize=(9, 4.4))
    table = composition[composition.field == "horizon_hint"].sort_values("category")
    y = np.arange(len(table))
    for i, name in enumerate(SETS):
        ax.barh(y + (i - .5) * .32, table[f"{name}_share"] * 100, height=.32, label=name.title(), color=colors[name])
    ax.set_yticks(y, table.category.str.replace("_", " "))
    ax.set_xlabel("Share of all exported claims (%)")
    ax.set_title("Raw and verified claims have different horizon mixes")
    ax.legend(); fig.tight_layout(); fig.savefig(out / "horizon_mix.png", dpi=160); plt.close(fig)
    fig, ax = plt.subplots(figsize=(10, 4.4))
    for name in SETS:
        sub = decades[decades.source_set == name]
        ax.plot(sub.decade, sub.article_gap_vs_fixed * 100, marker="o", label=name.title(), color=colors[name])
    ax.axhline(0, color="#666", linewidth=.8)
    ax.set(xlabel="Publication decade (2010 is one year)", ylabel="Accuracy minus fixed baseline (pp)",
           title="Baseline-relative performance, equal article weights within decade")
    ax.legend(); fig.tight_layout(); fig.savefig(out / "decade_gaps.png", dpi=160); plt.close(fig)
    papers = sorted(coverage.paper.unique())
    fig, axes = plt.subplots(2, 1, figsize=(12, 7.5), sharex=True, constrained_layout=True)
    vmax = np.log10(1 + coverage.n_claims.max())
    for name, ax in zip(SETS, axes):
        grid = coverage[coverage.source_set == name].pivot(index="paper", columns="year", values="n_claims")
        grid = grid.reindex(index=papers, columns=range(1900, 2011), fill_value=0).fillna(0)
        im = ax.imshow(np.log10(1 + grid), aspect="auto", vmin=0, vmax=vmax, cmap="Blues")
        ax.set_yticks(range(len(papers)), papers, fontsize=8)
        ax.set_title(name.title() + " exported claims")
    axes[-1].set_xticks(range(0, 111, 10), range(1900, 2011, 10))
    axes[-1].set_xlabel("Publication year")
    fig.colorbar(im, ax=axes, label="log10(1 + claims); zero means no exported claims", shrink=.8)
    fig.savefig(out / "coverage.png", dpi=160); plt.close(fig)


def report_html(tables, out):
    def table(frame):
        return '<div class="table">' + frame.to_html(index=False, border=0, float_format=lambda v: f"{v:,.3f}") + '</div>'
    def figure(name, alt):
        encoded = base64.b64encode((out / name).read_bytes()).decode()
        return f'<img alt="{html.escape(alt)}" src="data:image/png;base64,{encoded}">'
    comparisons = tables["comparisons"]
    primary = comparisons.set_index("comparison").loc["All scorable, equal article"]
    matched = comparisons.set_index("comparison").loc["Shared month cells"]
    horizon_mix = tables["composition"][tables["composition"].field == "horizon_hint"].set_index("category")
    month_ci = tables["block_intervals"].query(
        "comparison == 'Shared month cells' and metric == 'gap_vs_fixed' and block_years == 5").iloc[0]
    topic_table = tables["outcomes_by_topic"][["topic", "source_set", "n_claims", "article_hit_rate", "article_gap_vs_fixed"]].copy()
    topic_table[["article_hit_rate", "article_gap_vs_fixed"]] *= 100
    topic_table.columns = ["Topic", "Set", "Scored claims", "Article-weighted accuracy %", "Baseline gap pp"]
    brief = comparisons[["comparison", "raw_hit_rate", "verified_hit_rate", "raw_gap_vs_fixed", "verified_gap_vs_fixed", "delta_gap_vs_fixed"]].copy()
    brief.iloc[:, 1:] *= 100
    brief.columns = ["Comparison", "Raw accuracy %", "Verified accuracy %", "Raw baseline gap pp", "Verified baseline gap pp", "Gap change pp"]
    ci = tables["block_intervals"]
    ci = ci[(ci.block_years == 5) & (ci.metric == "gap_vs_fixed")][["comparison", "verified_minus_raw", "low", "high"]].copy()
    ci.iloc[:, 1:] *= 100
    body = ["<h1>How much does verification change the results?</h1>",
            "<p class='subtitle'>Annual ProQuest economy exports · 1900–2010 · raw sensitivity versus primary machine-verified set</p>",
            f"<p>With equal article weights, raw accuracy is <strong>{primary.raw_hit_rate:.1%}</strong> and verified accuracy is "
            f"<strong>{primary.verified_hit_rate:.1%}</strong>. Their gaps against the fixed-direction baseline are "
            f"<strong>{primary.raw_gap_vs_fixed * 100:+.1f}</strong> and <strong>{primary.verified_gap_vs_fixed * 100:+.1f} percentage points</strong>. "
            f"After matching exact publication-month cells, the verified-minus-raw baseline-gap difference is "
            f"<strong>{matched.delta_gap_vs_fixed * 100:+.1f} points</strong>.</p>",
            "<p>These are comparisons of exported datasets, not a causal estimate of verification quality. Raw candidates can be false forecasts. "
            "Machine verification is not human validation. Existing query selection and benchmark limitations apply to both sets.</p>",
            "<h2>What this first comparison tells us</h2>",
            f"<p>The exported sets differ in composition: explicitly stated horizon labels rise from "
            f"{horizon_mix.loc['stated', 'raw_share']:.1%} to {horizon_mix.loc['stated', 'verified_share']:.1%}. "
            "The aggregate accuracy result should therefore be read alongside its corresponding baseline and the matched comparisons. "
            f"The month-matched difference has a five-year-block interval of {month_ci.low * 100:+.2f} to "
            f"{month_ci.high * 100:+.2f} percentage points. "
            + ("This interval crosses zero, so a stable performance difference between these exports is not established.</p>"
               if month_ci.low <= 0 <= month_ci.high else
               "This interval does not cross zero, but remains a descriptive historical comparison.</p>"),
            "<h2>Corpus and scoring coverage</h2>", table(tables["corpus"]),
            "<p>Represented articles include empty records and are not the total number of retrieved or eligible newspaper articles. "
            "Absence from the verified export cannot distinguish filtering from unfinished or failed processing without the VM manifest. "
            "The local inputs end in 2010; work still being verified elsewhere is not included.</p>",
            table(tables["exclusions"]),
            figure("coverage.png", "Claim counts by newspaper and year for raw and verified exports"),
            "<h2>Composition changes</h2>", figure("horizon_mix.png", "Raw and verified horizon shares"),
            table(tables["composition"][tables["composition"].field == "horizon_hint"]),
            "<p>Count ratios are not claim-level retention rates: the exports lack a unique claim identifier and original quotations. "
            "The CSVs additionally compare topic, direction, normalized direction, scope, voice, confidence, newspaper, decade, and numeric horizon labels. "
            "Original horizon hints describe export composition; scoring uses the existing resolved-horizon rules, which prioritize valid numeric horizons.</p>",
            "<h2>Accuracy and the baseline</h2>", table(brief),
            "<p>Every baseline is evaluated on the same observations and with the same weights as the associated forecast accuracy. "
            "The fixed baseline predicts production and stocks rise, consumer prices rise, and unemployment falls. "
            "The CSV contains both baseline accuracies as well as the gaps.</p>",
            table(topic_table),
            "<p>Topic-specific weights give each article with scorable claims in that topic equal total weight. "
            "An article can appear in multiple topic rows; these rows do not sum to independent samples.</p>",
            figure("decade_gaps.png", "Decade baseline gaps with equal article weights"),
            "<h2>Shared composition</h2>", table(tables["matched_support"]),
            "<p>Year cells match newspaper, publication year, topic, benchmark, resolved horizon basis, and exact horizon in months, "
            "requiring at least 10 claims per set. Month cells additionally match publication month and require five claims per set. "
            "No cells match on forecast direction or correctness. Article weights start as one divided by the number of scorable claims "
            "in the article in each set. Cell means use these weights; both sets then receive the same harmonic-overlap cell mass "
            "(2 × raw mass × verified mass / total mass). This changes the target population to shared support. "
            "Month cells share identical realized outcomes and baseline values; year cells can still differ in within-year timing. "
            "Matched cells and their claim counts are exported for inspection. The unadjusted/matched difference is not a causal decomposition.</p>",
            "<h2>Historical variability</h2>", table(ci),
            "<p>The table shows verified-minus-raw baseline-gap changes and 95% percentile intervals, in percentage points, from 1,500 "
            "joint resamples of five-year publication blocks anchored at 1900. Two- and ten-year alternatives appear in block_intervals.csv. "
            "Sets and newspapers are resampled together because they overlap and share economic outcomes. Matched cell weights and support "
            "are held fixed. These intervals describe variation across the observed history; they do not resolve query selection, "
            "annotation errors, or all dependence from overlapping outcome windows. They are not adjusted for multiple comparisons.</p>",
            "<h2>Scoring and reproducibility</h2>",
            "<p>The explicit raw source adapter uses the same deterministic scorer as verified claims, without inventing a verification field. "
            "Only national claims in four supported topics are scored. Horizons must resolve to 1–24 months; vague horizons use the documented "
            "6/12/24-month rules. Flat bands are 2% for industrial production, 5% for stock prices, 1.5% for CPI, and 0.5 percentage points "
            "for unemployment. Pre-1919 business claims use the existing NBER proxy and are excluded in a separate sensitivity. "
            "Prices versus inflation, output versus growth, unemployment versus employment, and individual assets versus a broad index "
            "remain semantic limitations without source quotes. Frozen revised references describe realized outcomes; no print-time economic model is fitted.</p>",
            "<p>Source exports are unchanged; identical label rows are retained. LOC and old crisis-window exports are excluded. "
            "Verifier prose and retrospective window annotations do not enter outputs or comparisons. "
            "scored_claims.csv.gz uses (source_set, record_id) as a unique source-local address, never as cross-set claim lineage. "
            "article_changes.csv pairs only source article IDs and leaves absent-set counts missing. The manifest records source, reference, "
            "code hashes and dependency versions; exclusions.csv records one precedence-ordered exclusion reason per unscored row.</p>",
            "<p>Rebuild from the repository root: <code>python src/proquest_robustness.py</code>. "
            "Dependencies: <code>requirements-proquest.txt</code>. All tables and figures are stored beside this standalone report.</p>"]
    document = """<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>ProQuest raw versus verified robustness</title><style>
body{font:16px/1.6 system-ui,sans-serif;color:#19313c;background:#f7f8fa;max-width:1120px;margin:40px auto;padding:0 24px 60px}
h1{font-size:34px;line-height:1.2}h2{margin-top:42px}p{max-width:1000px}.subtitle{color:#536874}
img{width:100%;background:white;border-radius:8px;margin:16px 0}.table{overflow-x:auto;background:white;border:1px solid #dce3e8;border-radius:8px}
table{border-collapse:collapse;font-size:13px;width:100%}td,th{padding:9px 12px;text-align:right;white-space:nowrap;border-bottom:1px solid #e5e9ed}
th{background:#e8f1f0}td:first-child,th:first-child{text-align:left}code{background:#e8edf0;padding:2px 4px}</style><main>"""
    (out / "report.html").write_text(document + "\n".join(body) + "</main></html>", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, default=Path("data/proquest"))
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()
    # Never allow generated files to land inside source exports.
    if args.out.resolve().is_relative_to(args.base.resolve()):
        raise ValueError("Output directory must be separate from source exports")
    args.out.mkdir(parents=True, exist_ok=True)
    hashes, represented, empty = source_manifest(args.base)
    refs, reference = load_reference()
    frames = []
    for name in SETS:
        print(f"Scoring {name} annual exports...", flush=True)
        data = score_claims(args.base / name, refs, source_set=name)
        data["source_set"] = name
        data["page_id"] = data.page_id.astype(str)
        frames.append(data)
    frame = pd.concat(frames, ignore_index=True)
    if frame.duplicated(["source_set", "record_id"]).any():
        raise ValueError("Repeated source-local record address")
    scored = prepare_scored(frame)
    print("Building composition, article, and matched comparisons...", flush=True)
    articles = article_changes(frame, represented, empty)
    corpus = []
    for name in SETS:
        all_rows, eligible = frame[frame.source_set == name], scored[scored.source_set == name]
        corpus.append({"source_set": name, "claims": len(all_rows), "represented_articles": len(represented[name]),
                       "claim_articles": all_rows.page_id.nunique(), "scorable_claims": len(eligible),
                       "scorable_articles": eligible.page_id.nunique(), "unscorable_claims": len(all_rows) - len(eligible),
                       "publication_months": eligible.month.nunique(),
                       "outcome_cells": len(eligible[["topic", "basis", "month", "horizon_used"]].drop_duplicates())})
    common = set(scored[scored.source_set == "raw"].page_id) & set(scored[scored.source_set == "verified"].page_id)
    specs = [("All scorable, equal article", weighted_rows(scored)),
             ("All scorable, equal claim", weighted_rows(scored, "claim")),
             ("All scorable, equal month", weighted_rows(scored, "month")),
             ("Common scorable articles", weighted_rows(scored[scored.page_id.isin(common)])),
             ("Stated horizons, equal article", weighted_rows(scored[scored.horizon_basis == "stated"])),
             ("Exclude NBER proxy, equal article", weighted_rows(scored[scored.basis != "NBER proxy"]))]
    tables, supports = {}, []
    for label, exact, minimum in [("year", False, 10), ("month", True, 5)]:
        cells, weights = matched_cells(scored, exact_month=exact, minimum=minimum)
        tables[f"matched_{label}_cells"] = cells
        specs.append((f"Shared {label} cells", weights))
        supports.append({"matching": label, "minimum_claims_per_set": minimum, "n_cells": len(cells),
                         **{f"{name}_claims": int(cells[f"{name}_n_claims"].sum()) for name in SETS},
                         **{f"{name}_scorable_share": cells[f"{name}_n_claims"].sum() / len(scored[scored.source_set == name]) for name in SETS}})
    composition = pd.concat([composition_table(frame, key) for key in
                            ("paper", "year", "decade", "topic", "direction", "predicted_norm", "scope",
                             "horizon_hint", "horizon_months", "confidence", "voice")], ignore_index=True)
    tables.update(corpus=pd.DataFrame(corpus), article_changes=articles, composition=composition,
                  comparisons=pd.DataFrame([comparison(name, data) for name, data in specs]),
                  block_intervals=pd.concat([block_intervals(name, data) for name, data in specs], ignore_index=True),
                  matched_support=pd.DataFrame(supports))
    excluded = frame[~frame.scorable]
    tables["exclusions"] = excluded.groupby(["source_set", "unscorable_reason"]).size().rename("n_claims").reset_index()
    for key in ("paper", "decade", "year", "topic", "horizon_basis", "direction"):
        tables[f"outcomes_by_{key}"] = subgroup_outcomes(scored, key)
    coverage = frame.groupby(["source_set", "paper", "year"]).agg(n_claims=("record_id", "size"), n_articles=("page_id", "nunique")).reset_index()
    tables["coverage"] = coverage
    for name, table in tables.items():
        table.to_csv(args.out / f"{name}.csv", index=False)
    frame.to_csv(args.out / "scored_claims.csv.gz", index=False, compression={"method": "gzip", "mtime": 0})
    save_figures(composition, tables["outcomes_by_decade"], coverage, args.out)
    report_html(tables, args.out)
    # Confirm source/reference stability across the run before publishing the manifest.
    for path, digest in {**hashes, **{r["file"]: r["sha256"] for r in reference.values()}}.items():
        if hashlib.sha256(Path(path).read_bytes()).hexdigest() != digest:
            raise ValueError(f"Input changed during analysis: {path}")
    code = [Path("src") / name for name in ("proquest_robustness.py", "proquest_descriptive.py", "analyze_proquest.py", "score_predictions.py")]
    manifest = {"scope": "Annual ProQuest 1900–2010; verified primary, raw sensitivity", "sources": hashes,
                "reference": reference, "code_sha256": {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in code},
                "versions": {"python": platform.python_version(), **{name: version(name) for name in ("numpy", "pandas", "matplotlib", "xlrd")}},
                "rules": {"bands": BANDS, "primary_weighting": "equal scorable article", "seed": SEED,
                          "block_lengths_years": [2, 5, 10], "bootstrap_draws": 1500,
                          "year_cell_minimum": 10, "month_cell_minimum": 5},
                "raw_articles_absent_from_verified": len(represented["raw"] - represented["verified"]),
                "verified_articles_absent_from_raw": len(represented["verified"] - represented["raw"]),
                "common_scorable_articles": len(common), "corpus": corpus,
                "comparisons": tables["comparisons"].to_dict("records")}
    (args.out / "summary.json").write_text(json.dumps(manifest, indent=2, allow_nan=False) + "\n")
    print(tables["comparisons"].to_string(index=False))
    print(f"Report: {args.out / 'report.html'}")


if __name__ == "__main__":
    main()
