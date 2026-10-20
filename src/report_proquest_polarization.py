"""Render saved polarization comparisons without fitting or changing models."""
import html
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from proquest_polarization import OUT, digest

COLORS = {"political": "#b36b25", "forecast": "#167b85", "both": "#7154a1"}


def label(family, model):
    family = {"monthly_information": "Press experiment", "macro_information/core": "Original macro",
              "macro_information/with_cpi": "Original macro + CPI", "macro_benchmark/core": "Selected macro",
              "macro_benchmark/with_cpi": "Selected macro + CPI", "claim_correctness": "Claims"}[family]
    model = {"coverage_only": "coverage logistic", "base_rate_plus_press": "press logistic",
             "macro_only": "economy", "macro_plus_press": "economy + press",
             "logistic_metadata": "metadata logistic", "logistic_metadata_history": "history logistic",
             "gru_ensemble": "GRU ensemble"}[model]
    return f"{family}: {model}"


def table(frame):
    return '<div class="table">' + frame.to_html(index=False, border=0, float_format=lambda x: f"{x:.4f}") + '</div>'


def effect_figure(intervals, name):
    rows = intervals[intervals.metric.eq("brier")].copy()
    groups = rows[["family", "model"]].drop_duplicates().to_records(index=False).tolist()
    fig, ax = plt.subplots(figsize=(12, max(4, len(groups) * .78)))
    for i, (family, model) in enumerate(groups):
        for j, arm in enumerate(COLORS):
            r = rows[rows.family.eq(family) & rows.model.eq(model) & rows.arm.eq(arm)].iloc[0]
            y = i + (j-1)*.2
            ax.plot([r.low, r.high], [y, y], color=COLORS[arm], lw=1.5)
            ax.scatter(r.improvement, y, color=COLORS[arm], s=24, label=arm if i == 0 else None, zorder=3)
    ax.axvline(0, color="#444", lw=1)
    ax.set_yticks(range(len(groups)), [label(*g) for g in groups])
    ax.invert_yaxis()
    ax.set_xlabel("Baseline Brier − augmented Brier  (positive favors added features)")
    ax.set_title("Paired five-year-block 95% intervals; fitted forecasts held fixed")
    ax.legend(loc="best", frameon=False)
    ax.grid(axis="x", alpha=.2)
    fig.tight_layout()
    fig.savefig(OUT / name, dpi=160)
    plt.close(fig)


def main():
    frames = {task: pd.read_csv(OUT / f"{task}_metrics.csv") for task in ("monthly", "claims")}
    intervals = {task: pd.read_csv(OUT / f"{task}_paired_intervals.csv") for task in frames}
    feature = pd.read_csv(OUT / "features.csv")
    fig, axes = plt.subplots(2, 1, figsize=(12,6), sharex=True)
    for ax, field, title, color in zip(axes, ["political_polarization", "forecast_polarization"],
                                    ["Earlier House voting separation", "Earlier opposing business-forecast camps"],
                                    [COLORS["political"], COLORS["forecast"]]):
        ax.plot(pd.to_datetime(feature.origin), feature[field], color=color, lw=.8)
        ax.set(title=title, ylim=(0,1), ylabel="Index (0–1)")
        ax.grid(alpha=.2)
    fig.tight_layout(); fig.savefig(OUT / "feature_history.png", dpi=160); plt.close(fig)
    for task in frames:
        effect_figure(intervals[task], f"{task}_effects.png")
    core = frames["monthly"].query("family == 'macro_benchmark/core' and model == 'macro_plus_press' and scope == 'overall'").set_index("arm")
    gru = frames["claims"].query("model == 'gru_ensemble' and scope == 'overall'").set_index("arm")
    parts = ["<h1>Polarization in the ProQuest models</h1>",
             f"<p><strong>Adding both features worsens the two headline Brier results:</strong> selected macro plus newspapers rises from {core.loc['baseline','brier']:.4f} to {core.loc['both','brier']:.4f}; GRU claim correctness rises from {gru.loc['baseline','brier']:.4f} to {gru.loc['both','brier']:.4f}. Lower loss is better. The full comparisons and uncertainty follow; these results do not establish that polarization is intrinsically uninformative.</p>",
             "<p>Exploratory comparisons on annual verified ProQuest claims, 1900–2010. Every active learned model family receives two separate scalar inputs, each alone and together. Existing results remain unchanged. Constant class-frequency forecasts remain controls.</p>",
             "<h2>What the two features measure</h2>",
             '<p><strong>Political:</strong> earlier House Democratic–Republican differences in observed yes-vote shares. This is a legislative voting proxy, not the standard <a href="https://voteview.com/articles/party_polarization">Voteview NOMINATE party-mean gap</a> and not mass or affective polarization. Current career-based ideological estimates can use later votes, so they are excluded from predictive inputs. See <a href="https://voteview.com/articles/data_help_members">Voteview’s ideology documentation</a>.</p>',
             "<p>The political window uses twelve complete months ending two months before the prediction month, with one complete intervening month as a reporting buffer. Actual yea/nay votes only; at least five Democratic and five Republican voters per rollcall, and ten eligible rollcalls per window. Agenda and participation affect this proxy. Historical votes are reconstructed from the current database, not archived release vintages.</p>",
             "<p><strong>Forecast:</strong> mean 4 × positive share × negative share over the preceding three complete months of general-business forecasts. Equal-sized opposing camps score 1; absence of either camp scores 0. Equal article weights within newspaper and equal newspaper weights within month follow the existing panel. This differs from the existing three-class disagreement measure and does not measure newspaper political ideology.</p>",
             f"<p>Observed coverage: political {feature.political_polarization.notna().sum():,}/{len(feature):,} months; forecast {feature.forecast_polarization.notna().sum():,}/{len(feature):,}. Missing values use training-only median imputation plus a missingness flag; no evaluation rows are removed.</p>",
             '<img src="feature_history.png" alt="Monthly histories of two distinct polarization features">',
             "<h2>Comparison design</h2>",
             "<p>Baseline, political only, forecast only, and both use identical targets, training rows, evaluation observations, regularization and weights within each model. Saved training-only macro selections are reused. All logistic baseline refits must reproduce saved probabilities within tolerance. The GRU baseline and all extensions are rerun with seeds 11, 29 and 47 in the same environment; epochs are selected only by prior validation log loss. New scalar inputs enter the GRU head and both claim-logistic models; their existing twelve-month history remains identical.</p>",
             "<p>Binary claim Brier and three-class monthly Brier are different losses. Intervals resample five-year blocks while conditioning on fitted forecasts; they omit extraction and model-selection uncertainty. Multiple comparisons are exploratory. The short CPI study has only two blocks. A wide interval is not evidence of no effect.</p>"]
    for task, frame in frames.items():
        parts.append(f"<h2>{'Claim correctness' if task == 'claims' else 'Monthly economic direction'}</h2>")
        selected = frame[frame.scope.eq("overall")].copy()
        selected["Model"] = [label(f,m) for f,m in zip(selected.family,selected.model)]
        pivot = selected.pivot(index="Model", columns="arm", values="brier").reset_index()
        parts.append("<p>Brier loss, lower is better. Each row is a matched comparison.</p>")
        parts.append(table(pivot[["Model", "baseline", "political", "forecast", "both"]]))
        parts.append(f'<img src="{task}_effects.png" alt="Paired Brier improvement intervals across {task} models">')
        sensitivity = frame[frame.scope.eq("exclude_2007_2009")].copy()
        sensitivity["Model"] = [label(f,m) for f,m in zip(sensitivity.family,sensitivity.model)]
        parts.append("<h3>Excluding 2007–2009 evaluation observations</h3><p>This changes evaluation only; it does not remove crisis observations from later training histories.</p>")
        parts.append(table(sensitivity.pivot(index="Model",columns="arm",values="brier").reset_index()[["Model","baseline","political","forecast","both"]]))
        parts.append(f'<p>Full <a href="{task}_metrics.csv">metrics</a>, <a href="{task}_paired_intervals.csv">paired intervals</a>, and <a href="{task}_calibration.csv">calibration bins with sample counts</a>.</p>')
    parts += ["<h2>Reproducibility and interpretation</h2>",
              '<p><a href="evaluation_spec.json">Specification</a>; <a href="feature_manifest.json">feature provenance</a>; <a href="download_manifest.json">public source hashes</a>; <a href="monthly_summary.json">monthly run manifest</a>; <a href="claims_summary.json">claim run manifest</a>. The specification precedes these polarization fits, after inspection of earlier results. No modern claims or LOC outcomes enter.</p>',
              "<p>These are predictive associations, not causal estimates of polarization. Changes can reflect time trends, agenda, query selection and coverage. The features do not establish that newspapers become politically polarized or that polarization causes forecast errors. Human source validation remains unfinished.</p>"]
    style = '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>ProQuest polarization comparisons</title><style>body{font:16px/1.6 system-ui,sans-serif;max-width:1150px;margin:40px auto;padding:0 24px;color:#19313c}h1,h2{line-height:1.25}h2{margin-top:40px}img{width:100%}.table{overflow:auto}table{border-collapse:collapse;width:100%;font-size:14px}td,th{padding:8px 10px;border-bottom:1px solid #ddd;text-align:right}td:first-child,th:first-child{text-align:left}a{color:#087f83}</style><main>'
    (OUT / "report.html").write_text(style + "\n".join(parts) + "</main></html>")
    outputs = [p for p in OUT.rglob("*") if p.is_file() and "source_cache" not in p.parts and p.name != "output_manifest.json"]
    (OUT / "output_manifest.json").write_text(json.dumps({"outputs_sha256": {str(p): digest(p) for p in outputs},
                                                           "report_code_sha256": digest(__file__)},indent=2)+"\n")
    print(OUT / "report.html")


if __name__ == "__main__":
    main()
