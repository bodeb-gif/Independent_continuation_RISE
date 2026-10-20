"""Forward-time comparison of vintage macro data with added ProQuest signals.

Run proquest_vintages.py first. Rules are saved in evaluation_spec.json before
fitting; source exports and original vintage workbooks are never rewritten.
"""
import base64
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import platform
import warnings

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from proquest_information import CLASSES, losses, metrics, read_production, targets
from proquest_panel import FEATURES
from proquest_vintages import CORE_FEATURES, CPI_FEATURES, OUT, load_archives, macro_features

SPEC_PATH = OUT / "evaluation_spec.json"
PANEL = Path("data/scored/proquest/monthly_information")
MODELS = ("recent_base_rate", "macro_only", "macro_plus_press")
PAIRS = (("macro_plus_press", "macro_only"), ("macro_only", "recent_base_rate"),
         ("macro_plus_press", "recent_base_rate"))
NAMES = {"recent_base_rate": "Recent base rate", "macro_only": "Economy only", "macro_plus_press": "Economy + newspapers"}
COLORS = {"recent_base_rate": "#8494a5", "macro_only": "#c18b36", "macro_plus_press": "#087f83"}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_spec():
    spec = json.loads(SPEC_PATH.read_text())
    for key, expected in [("macro_features", CORE_FEATURES), ("additional_cpi_features", CPI_FEATURES),
                          ("press_features", FEATURES), ("class_order", CLASSES)]:
        if tuple(spec[key]) != expected:
            raise ValueError(f"Specification and code disagree: {key}")
    if spec["horizon_months"] != 6 or spec["flat_band_percent"] != 2.:
        raise ValueError("Expected six-month target with 2% flat band")
    return spec, digest(SPEC_PATH)


def training_labels(data, refit_origin, archive, spec):
    """Labels known at refit; never reads data.target (final evaluation truth)."""
    vintage, snapshot = archive.snapshot(refit_origin)
    if vintage is None:
        raise ValueError("No industrial-production snapshot before refit")
    records = []
    for origin in data.loc[data.origin < refit_origin, "origin"]:
        start, end = origin - 1, origin + spec["horizon_months"] - 1
        mature = end + spec["label_release_allowance_months"] < refit_origin
        first, last = snapshot.get(start, np.nan), snapshot.get(end, np.nan)
        available = np.isfinite(first) and np.isfinite(last) and first > 0
        change = 100 * (last / first - 1) if available else np.nan
        label = None
        if mature and available:
            band = spec["flat_band_percent"]
            # Floating-point arithmetic must not move exact threshold endpoints.
            label = "rise" if change > band + 1e-10 else "fall" if change < -band - 1e-10 else "flat"
        records.append({"origin": origin, "training_target": label, "training_change_percent": change,
                        "label_vintage": vintage, "label_available_by": str(archive.dates[vintage].date()),
                        "target_start": start, "target_end": end, "mature": mature,
                        "endpoints_in_vintage": bool(available),
                        "exclusion": "unmatured" if not mature else "missing vintage endpoints" if not available else ""})
    return pd.DataFrame(records)


def standardize(training, evaluation, features):
    train, test = training[list(features)].to_numpy(float), evaluation[list(features)].to_numpy(float)
    if not np.isfinite(train).all() or not np.isfinite(test).all():
        raise ValueError("Common-support features must all be finite")
    scaler = StandardScaler().fit(train)
    parameters = pd.DataFrame({"feature": features, "mean": scaler.mean_, "scale": scaler.scale_})
    return scaler.transform(train), scaler.transform(test), parameters


def fit_study(data, archive, spec, study):
    macro = tuple(CORE_FEATURES) + (tuple(CPI_FEATURES) if study["include_cpi"] else ())
    features = macro + FEATURES
    first, last = pd.Period(study["evaluation_start"], "M"), pd.Period(study["evaluation_end"], "M")
    data = data[data.origin >= pd.Period(study["training_start"], "M")].copy()
    data["inputs_available"] = np.isfinite(data[list(features)].to_numpy(float)).all(axis=1)
    support = data[["origin", "inputs_available", "target"]].copy()
    support["in_evaluation_window"] = support.origin.between(first, last)
    support["evaluated"] = support.in_evaluation_window & support.inputs_available & support.target.notna()
    support["refit_exclusion"] = ""
    predictions, refits, coefficients, preprocessing, label_audits = [], [], [], [], []
    for year in range(first.year, last.year + 1):
        refit = pd.Period(f"{year}-01", "M")
        labels = training_labels(data, refit, archive, spec)
        labels = labels.merge(data[["origin", "inputs_available"]], on="origin", validate="one_to_one")
        labels["used"] = labels.training_target.notna() & labels.inputs_available
        label_audits.append(labels.assign(refit_year=year))
        training = data.merge(labels[["origin", "training_target", "used"]], on="origin", validate="one_to_one")
        training = training[training.used].sort_values("origin")
        evaluation = data[data.origin.between(max(first, refit), min(last, refit + 11)) &
                          data.inputs_available & data.target.notna()].copy()
        if len(training) < study["minimum_training_months"]:
            raise ValueError(f"Insufficient training history: {study['name']} {year}, n={len(training)}")
        if evaluation.empty:
            continue
        y = training.training_target.map({label: i for i, label in enumerate(CLASSES)}).to_numpy(int)
        if set(y) != {0, 1, 2}:
            # Documented in implementation_note.json; the entire year is removed
            # for every model, based exclusively on the refit's training history.
            omitted = support.origin.between(refit, refit + 11)
            support.loc[omitted, "evaluated"] = False
            support.loc[omitted, "refit_exclusion"] = "training history lacks a class"
            label_audits[-1].loc[label_audits[-1].used, "exclusion"] = "refit skipped: training history lacks a class"
            label_audits[-1]["used"] = False
            refits.append({"refit_year": year, "refit_origin": str(refit), "n_training_months": len(training),
                           "n_evaluation_months": 0, "exclusion": "training history lacks a class",
                           **{f"training_{label}": int((y == i).sum()) for i, label in enumerate(CLASSES)}})
            continue
        recent = y[-spec["recent_window_months"]:]
        prior = (np.bincount(recent, minlength=3) + 1.) / (len(recent) + 3.)
        evaluation["refit_year"] = year
        for i, label in enumerate(CLASSES):
            evaluation[f"recent_base_rate_{label}"] = prior[i]
        for name, selected in [("macro_only", macro), ("macro_plus_press", features)]:
            train_x, test_x, params = standardize(training, evaluation, selected)
            preprocessing.append(params.assign(refit_year=year, model=name))
            model = LogisticRegression(C=spec["logistic_C"], solver=spec["logistic_solver"],
                                       max_iter=spec["logistic_max_iter"], random_state=spec["bootstrap_seed"])
            with warnings.catch_warnings():
                warnings.simplefilter("error", ConvergenceWarning)
                model.fit(train_x, y)
            p = model.predict_proba(test_x)
            for i, code in enumerate(model.classes_):
                label = CLASSES[code]
                evaluation[f"{name}_{label}"] = p[:, i]
                for feature, coefficient in zip(("intercept",) + selected, np.r_[model.intercept_[i], model.coef_[i]]):
                    coefficients.append({"refit_year": year, "model": name, "class": label,
                                         "feature": feature, "coefficient": coefficient})
        refits.append({"refit_year": year, "refit_origin": str(refit), "n_training_months": len(training),
                       "first_training_origin": str(training.origin.min()), "last_training_origin": str(training.origin.max()),
                       "label_vintage": labels.label_vintage.iloc[0], "label_available_by": labels.label_available_by.iloc[0],
                       "unmatured_months": int((~labels.mature).sum()),
                       "mature_missing_vintage_endpoints": int((labels.mature & ~labels.endpoints_in_vintage).sum()),
                       "missing_input_months": int((~labels.inputs_available).sum()), "n_evaluation_months": len(evaluation),
                       "recent_base_rate_months": len(recent),
                       **{f"training_{label}": int((y == i).sum()) for i, label in enumerate(CLASSES)}})
        predictions.append(evaluation)
    return {"predictions": pd.concat(predictions, ignore_index=True), "annual_refits": pd.DataFrame(refits),
            "coefficients": pd.DataFrame(coefficients), "preprocessing": pd.concat(preprocessing, ignore_index=True),
            "training_label_audit": pd.concat(label_audits, ignore_index=True), "support_audit": support}


def evaluate(predictions, spec, study):
    groups = [("overall", f"{predictions.origin.min()} to {predictions.origin.max()}", predictions),
              ("sensitivity", "Exclude 2007–2009", predictions[~predictions.origin.dt.year.between(2007, 2009)])]
    for kind, length in [("decade", 10), ("five_year", 5)]:
        for block, group in predictions.groupby(predictions.origin.dt.year // length * length):
            groups.append((kind, f"{group.origin.min()} to {group.origin.max()}", group))
    rows = [{"grouping": kind, "period": period, "model": model, **metrics(frame, model)}
            for kind, period, frame in groups for model in MODELS]
    intervals = []
    for model, baseline in PAIRS:
        for metric, candidate, control in zip(("brier", "log_loss"), losses(predictions, model), losses(predictions, baseline)):
            gain = control - candidate
            for length in spec["block_lengths_years"]:
                codes = (predictions.origin.dt.year.to_numpy() - pd.Period(study["evaluation_start"], "M").year) // length
                blocks = pd.DataFrame({"block": codes, "gain": gain}).groupby("block").gain.agg(["sum", "count"])
                rng = np.random.default_rng(spec["bootstrap_seed"] + length)
                draws = rng.integers(0, len(blocks), (spec["bootstrap_draws"], len(blocks)))
                values = blocks["sum"].to_numpy()[draws].sum(axis=1) / blocks["count"].to_numpy()[draws].sum(axis=1)
                low, high = np.quantile(values, [.025, .975])
                intervals.append({"model": model, "baseline": baseline, "metric": metric, "block_years": length,
                                  "n_blocks": len(blocks), "improvement": gain.mean(), "low": low, "high": high})
    calibration = []
    for model in MODELS:
        for label in CLASSES:
            bins = np.minimum((predictions[f"{model}_{label}"] * 10).astype(int), 9)
            for bucket, group in predictions.groupby(bins):
                calibration.append({"model": model, "class": label, "bin": bucket, "n_months": len(group),
                                    "mean_prediction": group[f"{model}_{label}"].mean(), "observed_share": group.target.eq(label).mean()})
    leave = []
    cells = predictions.origin.dt.year // 5 * 5
    for cell in sorted(cells.unique()):
        sub = predictions[cells != cell]
        for metric, candidate, control in zip(("brier", "log_loss"), losses(sub, "macro_plus_press"), losses(sub, "macro_only")):
            leave.append({"omitted_start": cell, "omitted_end": min(cell + 4, 2010), "n_months": len(sub),
                          "metric": metric, "improvement": (control - candidate).mean()})
    return {"metrics": pd.DataFrame(rows), "paired_intervals": pd.DataFrame(intervals),
            "calibration": pd.DataFrame(calibration), "leave_block_out": pd.DataFrame(leave)}


def figures(tables):
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
                         "axes.spines.top": False, "axes.spines.right": False})
    studies = list(tables)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4), constrained_layout=True)
    for ax, study in zip(axes, studies):
        overall = tables[study]["metrics"].query("grouping == 'overall'").set_index("model")
        for i, model in enumerate(MODELS):
            value = overall.loc[model, "brier"]
            ax.bar(i, value, color=COLORS[model]); ax.text(i, value + .012, f"{value:.3f}", ha="center")
        ax.set_xticks(range(3), ["Recent\nbase rate", "Economy\nonly", "Economy +\nnewspapers"])
        ax.set_ylim(0, 1.08); ax.axhline(2 / 3, ls=":", color="#777", label="Uniform probabilities")
        ax.set_title(f"{study}: {int(overall.n_months.iloc[0])} common months"); ax.set_ylabel("Brier score (lower is better)")
        ax.legend(fontsize=8)
    fig.savefig(OUT / "model_comparison.png", dpi=160); plt.close(fig)
    fig, axes = plt.subplots(2, 3, figsize=(12, 8), constrained_layout=True)
    for row, study in enumerate(studies):
        cal = tables[study]["calibration"]
        for col, label in enumerate(CLASSES):
            ax = axes[row, col]
            ax.plot([0, 1], [0, 1], "--", color="#bbb")
            for model in MODELS:
                frame = cal[(cal.model == model) & (cal["class"] == label)]
                ax.plot(frame.mean_prediction, frame.observed_share, color=COLORS[model], alpha=.7)
                ax.scatter(frame.mean_prediction, frame.observed_share, s=10 + frame.n_months * .4,
                           color=COLORS[model], label=NAMES[model])
            ax.set(xlim=(0, 1), ylim=(0, 1), xlabel="Mean predicted probability", ylabel="Observed share",
                   title=f"{study} · {label}")
            if row == col == 0:
                ax.legend(fontsize=8)
    fig.savefig(OUT / "calibration.png", dpi=160); plt.close(fig)
    fig, axes = plt.subplots(2, 1, figsize=(11, 7), constrained_layout=True)
    for ax, study in zip(axes, studies):
        cells = tables[study]["metrics"].query("grouping == 'five_year'").pivot(index="period", columns="model", values="brier")
        gain = cells.macro_only - cells.macro_plus_press
        ax.bar(range(len(gain)), gain, color=["#087f83" if g > 0 else "#c26b4c" for g in gain])
        ax.axhline(0, color="#555", lw=1)
        ax.set_xticks(range(len(gain)), [x.replace(" to ", "\n") for x in gain.index], fontsize=8)
        ax.set_ylabel("Brier improvement from newspapers"); ax.set_title(study)
    fig.savefig(OUT / "five_year_improvement.png", dpi=160); plt.close(fig)


def report(tables, summary):
    def table(frame):
        return '<div class="table">' + frame.to_html(index=False, border=0, float_format=lambda x: f"{x:.4f}") + '</div>'
    def image(name):
        return '<img alt="' + name.replace('_', ' ') + '" src="data:image/png;base64,' + base64.b64encode((OUT / name).read_bytes()).decode() + '">'
    body = ["<h1>Do newspapers add information beyond the economy?</h1>",
            "<p>Annual verified ProQuest economy claims, 1900–2010. Exploratory forward-time evaluation with historical macro vintages.</p>",
            "<p><strong>Finding:</strong> adding newspapers lowers average core Brier loss, but the block interval includes no gain. "
            "The economy-only model itself performs worse than the recent base rate. Adding newspapers beats that base rate on Brier "
            "but not log loss, and loses to it on both losses outside 2007–2009. This does not establish reliable incremental forecasting skill.</p>",
            "<h2>Results on identical months</h2>", image("model_comparison.png")]
    for study, frames in tables.items():
        primary = frames["paired_intervals"].query("model == 'macro_plus_press' and baseline == 'macro_only' and metric == 'brier' and block_years == 5").iloc[0]
        body += [f"<h3>{study}</h3>", table(frames["metrics"].query("grouping == 'overall'")),
                 f"<p>Newspapers change Brier loss by an improvement of <strong>{primary.improvement:+.4f}</strong> relative to economy-only. "
                 f"The paired five-year-block 95% interval is [{primary.low:+.4f}, {primary.high:+.4f}] across {primary.n_blocks} blocks. "
                 "Positive improvement means lower loss. Intervals condition on these fitted forecasts.</p>"]
    body += ["<h2>Availability audit and timing</h2>", table(pd.read_csv(OUT / "vintage_coverage.csv")),
             "<p>The source workbooks retain original bytes and hashes. Production snapshots begin November 1962; unemployment starts "
             "1965Q4. CPI has empty earlier columns: its first nonempty snapshot is 1994Q3. These produce first usable forecast origins "
             "December 1965 for the core inputs and September 1994 with CPI. Historical snapshots are reconstructed from publications; "
             "this archive is not a guarantee of perfect original real-time measurement.</p>",
             "<p>At the first of each month, choose the latest nonempty vintage strictly earlier than issuance. Production's month-end "
             "bound conservatively follows that month's release. Quarterly unemployment/CPI snapshots use February/May/August/November 15. "
             "Use each snapshot's last observed month and record its age. Changes are calculated within a vintage, so index rebasing "
             "cannot create spurious cross-vintage growth. No revised values fill gaps.</p>",
             "<p>Core predictors are production growth over 3/6/12 months, unemployment level and 3/12-month changes, and observation ages. "
             "The shorter check adds CPI 3/12-month growth and its age. Quarterly unemployment and CPI can lag information actually "
             "published monthly, making this a conservative, incomplete macro benchmark rather than the best possible forecaster.</p>",
             "<h2>Outcome, models, and eligibility</h2>",
             "<p>Target: the final revised production change from t−1 to t+5; above +2% is rise, below −2% fall, otherwise flat. "
             "The starting month's level need not be known at issuance: it is an outcome endpoint, never an input at t. Every January "
             "refit instead computes training labels within its latest available production vintage. Endpoint plus three months must "
             "precede refit; both endpoints must exist. Historical coverage gaps are excluded and exported in the training-label audit.</p>",
             "<p>All three models use identical eligible training and evaluation months within each study. Eight core macro variables "
             "(eleven with CPI) are compared with those same inputs plus four newspaper signals: prior-three-month net direction, "
             "common-paper direction change, disagreement, and cross-paper dispersion. Newspaper observations end in t−1. Equal article "
             "weights within paper/topic/month and equal paper weights form the panel. Missing inputs exclude a month for every model; "
             "no imputation or outcome-based feature selection. Prior panel coverage thresholds remain fixed.</p>",
             "<p>The recent base rate uses the latest 120 eligible mature training months, with one pseudo-observation per class. Both "
             "regressions are multinomial ridge logistic models, C=1, with training-only standardization and no tuning. Refit annually "
             "on an expanding eligible history; core evaluation starts 1977 with at least 120 training months, CPI evaluation starts "
             "2001 with at least 60. Different training histories mean CPI/core differences do not isolate the contribution of CPI.</p>",
             "<p><strong>Documented implementation deviation:</strong> the January 2001 CPI training sample has 48 rise, 20 flat and zero fall labels. "
             "Its three-class fit stopped before making predictions. We excluded that year for all three models, leaving 108 common months "
             "in 2002–2010. This rule was recorded after the first core results, before any CPI predictions; see implementation_note.json. "
             "The original specification is preserved. The core comparison is unchanged.</p>",
             "<h2>Calibration</h2>", image("calibration.png"),
             "<p>Fixed tenths bins for each class; dot area increases with bin count. Sparse high-probability bins are noisy. No "
             "calibration is fitted on evaluation outcomes. Brier sums three squared probability errors (range 0–2, uniform 2/3); "
             "log loss is also lower-is-better. Neither accuracy nor calibration is substituted for the primary probability-loss test.</p>",
             "<p>The CPI regressions have high probability losses, both worse than their recent-base-rate comparator. Adding newspapers "
             "improves that weak macro fit but does not make it a good probability forecast. High fall AUC is not evidence of calibration: "
             "ranking can be good while probabilities are badly wrong. After excluding 2007–2009, the CPI evaluation contains no fall "
             "outcomes, so fall AUC/AP are undefined. We retain the preset model rather than tuning against these results.</p>",
             "<h2>Era and crisis stability</h2>", image("five_year_improvement.png")]
    for study, frames in tables.items():
        leave = frames["leave_block_out"].query("metric == 'brier'")
        body += [f"<h3>{study}</h3>", table(frames["metrics"].query("grouping == 'decade' or grouping == 'sensitivity'")),
                 f"<p>Leaving one calendar five-year cell out gives newspaper Brier improvements from {leave.improvement.min():+.4f} "
                 f"to {leave.improvement.max():+.4f}. Exclusions change scoring only; models retain those periods in later training. "
                 "Boundary cells can be partial, including 2010 alone.</p>", table(frames["paired_intervals"])]
    body += ["<h2>Interpretation and limits</h2>",
             "<p>The primary question is the incremental newspaper gain over the vintage macro model, not its gain over a constant "
             "baseline. Paired blocks preserve overlap within blocks, but finite boundaries, few long blocks, overlapping targets "
             "and conditioning on fitted models limit uncertainty estimates. The ten-year CPI interval has only one block and is "
             "degenerate; it supplies no useful uncertainty estimate. Two/five-year results are also based on few blocks. Secondary "
             "comparisons are unadjusted for multiplicity.</p>",
             "<p>These periods have already been explored. Rules were frozen before these fits, not before all historical analysis. "
             "Machine-extracted labels, missing quotes, a downturn/recovery query, changing paper coverage and a broad production "
             "proxy remain limitations. Human validation remains essential. No speaker identity, verifier prose, retrospective "
             "window annotation, LOC claims, or old crisis exports enter the inputs. Results do not establish causation.</p>",
             "<h2>Reproduction and sources</h2>",
             "<p><code>python src/proquest_vintages.py</code> then <code>python src/proquest_macro_information.py</code>; install "
             "<code>requirements-proquest-information.txt</code>. The first source download uses <code>proquest_vintages.py --fetch</code>. "
             "The existing monthly panel is required; rebuild it with <code>proquest_information.py --build-only</code>. "
             "This directory contains frozen rules, original public workbooks and documentation, source hashes, all vintage "
             "selection/feature audits, training labels, eligibility, annual refits, scaling, coefficients, predictions and metrics. "
             "Source hashes are checked before and after fitting; source exports remain unchanged.</p>",
             f"<p>Specification SHA-256: <code>{summary['spec_sha256']}</code>.</p>",
             '<p>Philadelphia Fed: <a href="https://www.philadelphiafed.org/surveys-and-data/real-time-data-research/ipt">production archive</a>, '
             '<a href="https://www.philadelphiafed.org/surveys-and-data/real-time-data-research/ruc">unemployment archive</a>, '
             '<a href="https://www.philadelphiafed.org/surveys-and-data/real-time-data-research/cpi">CPI archive</a>. '
             'Direct workbook and documentation URLs and download dates are in <code>reference/download_manifest.json</code>.</p>']
    head = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Vintage macro and newspaper information</title><style>
body{font:16px/1.6 system-ui,sans-serif;color:#19313c;background:#f7f8fa;max-width:1120px;margin:40px auto;padding:0 24px 60px}
h1{font-size:34px;line-height:1.2}h2{margin-top:40px}img{width:100%;background:white;border-radius:8px;margin:16px 0}
.table{overflow-x:auto;background:white;border:1px solid #dce3e8}table{border-collapse:collapse;font-size:13px;width:100%}
td,th{padding:9px 12px;text-align:right;white-space:nowrap;border-bottom:1px solid #e5e9ed}th{background:#e8f1f0}
code{overflow-wrap:anywhere;background:#e8edf0}</style><main>'''
    (OUT / "report.html").write_text(head + "\n".join(body) + "</main></html>")


def main():
    spec, spec_hash = load_spec()
    print("Checking inputs and building historical vintage features...", flush=True)
    panel_manifest = json.loads((PANEL / "panel_manifest.json").read_text())
    tracked = {**panel_manifest["sources"], str(SPEC_PATH): spec_hash,
               str(OUT / "implementation_note.json"): digest(OUT / "implementation_note.json"),
               str(PANEL / "forecast_features.csv"): digest(PANEL / "forecast_features.csv"),
               str(PANEL / "panel_manifest.json"): digest(PANEL / "panel_manifest.json")}
    for path, expected in tracked.items():
        if digest(path) != expected:
            raise ValueError(f"Input hash changed: {path}")
    archives, sources, coverage = load_archives()
    manifest = json.loads((OUT / "reference/download_manifest.json").read_text())
    for name, source in sources.items():
        if source["sha256"] != manifest[name]["sha256"]:
            raise ValueError("Vintage source differs from download manifest")
        tracked[source["path"]] = source["sha256"]
    press = pd.read_csv(PANEL / "forecast_features.csv")
    press["origin"] = pd.PeriodIndex(press.origin, freq="M")
    origins = pd.period_range("1950-01", "2010-12", freq="M")
    macro = macro_features(archives, origins)
    production, reference = read_production()
    tracked[reference["file"]] = reference["sha256"]
    data = macro.merge(press[["origin"] + list(FEATURES)], on="origin", validate="one_to_one")
    data = data.merge(targets(origins, production, spec), on="origin", validate="one_to_one")
    data.to_csv(OUT / "forecast_dataset.csv", index=False)
    tables = {}
    for study in spec["studies"]:
        name = study["name"]
        print(f"Fitting {name}: {study['evaluation_start']} to {study['evaluation_end']}...", flush=True)
        frames = fit_study(data, archives["IPT"], spec, study)
        predicted = frames["predictions"]
        for model in MODELS:
            predicted[f"{model}_brier"], predicted[f"{model}_log_loss"] = losses(predicted, model)
        frames.update(evaluate(predicted, spec, study))
        tables[name] = frames
        destination = OUT / name
        destination.mkdir(exist_ok=True)
        for table_name, frame in frames.items():
            frame.to_csv(destination / f"{table_name}.csv", index=False)
        print(frames["metrics"].query("grouping == 'overall' or grouping == 'sensitivity'").to_string(index=False), flush=True)
        print(frames["paired_intervals"].query("model == 'macro_plus_press' and baseline == 'macro_only' and metric == 'brier'").to_string(index=False), flush=True)
    code = [Path("src") / name for name in ("proquest_macro_information.py", "proquest_vintages.py", "proquest_information.py",
                                           "proquest_panel.py", "proquest_descriptive.py", "analyze_proquest.py", "score_predictions.py")]
    summary = {"spec_sha256": spec_hash, "inputs_sha256": tracked, "macro_sources": sources, "evaluation_reference": reference,
               "code_sha256": {str(path): digest(path) for path in code},
               "versions": {"python": platform.python_version(), **{name: version(name) for name in ("numpy", "pandas", "matplotlib", "scikit-learn")}},
               "studies": {name: {"n_evaluation_months": len(frames["predictions"]),
                                   "excluded_evaluation_months": int((frames["support_audit"].in_evaluation_window & ~frames["support_audit"].evaluated).sum()),
                                   "overall_metrics": frames["metrics"].query("grouping == 'overall'").to_dict("records")}
                           for name, frames in tables.items()}}
    figures(tables)
    report(tables, summary)
    for path, expected in tracked.items():
        if digest(path) != expected:
            raise ValueError(f"Input changed during analysis: {path}")
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n")
    print(f"Report: {OUT / 'report.html'}", flush=True)


if __name__ == "__main__":
    main()
