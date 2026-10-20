"""Select a small vintage-macro benchmark inside chronological training folds.

Outer evaluation truth is attached only after fitting. Inner training labels
come from their own historical vintages; selection labels are known at the
outer refit. The saved specification precedes these fits, not all prior work.
"""
import base64
from importlib.metadata import version
import json
from pathlib import Path
import warnings

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression

from proquest_information import CLASSES, losses, metrics, probabilities
from proquest_macro_information import (COLORS, MODELS, NAMES, digest, evaluate,
                                        standardize, training_labels)
from proquest_panel import FEATURES
from proquest_vintages import CORE_FEATURES, CPI_FEATURES, load_archives

SOURCE = Path("data/scored/proquest/macro_information")
OUT = Path("data/scored/proquest/macro_benchmark")
SPEC_PATH = OUT / "evaluation_spec.json"


def load_spec():
    spec = json.loads(SPEC_PATH.read_text())
    if tuple(spec["class_order"]) != CLASSES or tuple(spec["press_features"]) != FEATURES:
        raise ValueError("Feature/class specification mismatch")
    if spec["horizon_months"] != 6 or spec["flat_band_percent"] != 2.:
        raise ValueError("Unexpected target definition")
    return spec


def candidates(spec, study):
    result = []
    for name, selected in spec["macro_feature_sets"].items():
        features = tuple(selected) + ((spec["additional_cpi_feature"],) if study["include_cpi"] else ())
        for c in spec["C_candidates"]:
            for window in spec["training_windows"]:
                result.append({"candidate": f"{name}_C{c:g}_{window}", "feature_set": name,
                               "features": features, "C": c, "window": window})
    return sorted(result, key=lambda x: (len(x["features"]), x["C"], x["window"] != "expanding"))


def windowed(training, candidate):
    training = training.sort_values("origin")
    return training.tail(120) if candidate["window"] == "recent_120" else training


def trainable(training, minimum):
    return len(training) >= minimum and set(training.training_target) == set(CLASSES)


def fit_regression(training, evaluation, features, c, spec):
    x_train, x_test, params = standardize(training, evaluation, features)
    y = training.training_target.map({label: i for i, label in enumerate(CLASSES)}).to_numpy(int)
    model = LogisticRegression(C=c, solver=spec["solver"], max_iter=spec["max_iter"], random_state=spec["bootstrap_seed"])
    with warnings.catch_warnings():
        warnings.simplefilter("error", ConvergenceWarning)
        model.fit(x_train, y)
    if list(model.classes_) != [0, 1, 2]:
        raise ValueError("Expected all three training classes")
    records = [{"class": label, "feature": feature, "coefficient": coefficient}
               for i, label in enumerate(CLASSES)
               for feature, coefficient in zip(("intercept",) + tuple(features), np.r_[model.intercept_[i], model.coef_[i]])]
    return model.predict_proba(x_test), params, pd.DataFrame(records)


def brier(p, target):
    y = pd.Series(target).map({label: i for i, label in enumerate(CLASSES)}).to_numpy(int)
    return ((p - np.eye(3)[y]) ** 2).sum(axis=1)


def vintage_training(data, refit, archive, spec):
    # data contains only origin and allowed features; no evaluation truth exists here.
    labels = training_labels(data, refit, archive, spec)
    usable = labels[labels.training_target.notna()]
    return data.merge(usable, on="origin", validate="one_to_one").sort_values("origin"), labels


def inner_folds(data, outer_training, outer_year, get_training, spec):
    config = spec["inner_validation"]
    folds, audit = [], []
    for year in range(outer_year - config["lookback_years"], outer_year):
        refit = pd.Period(f"{year}-01", "M")
        training = get_training(year)
        # This join supplies only labels already mature in the outer vintage.
        available = outer_training[["origin", "training_target", "label_vintage", "label_available_by"]]
        validation = data[data.origin.between(refit, refit + 11)].merge(available, on="origin", validate="one_to_one")
        reason = "" if trainable(training, config["minimum_training_months"]) else "insufficient training or missing class"
        if validation.empty:
            reason = "no mature outer-vintage validation labels"
        audit.append({"outer_year": outer_year, "inner_year": year, "n_training": len(training),
                      "n_validation": len(validation), "used": not reason, "exclusion": reason,
                      "training_label_vintage": training.label_vintage.iloc[0] if len(training) else None,
                      "validation_label_vintage": validation.label_vintage.iloc[0] if len(validation) else None,
                      "last_training_origin": str(training.origin.max()) if len(training) else None,
                      "last_validation_origin": str(validation.origin.max()) if len(validation) else None})
        if not reason:
            folds.append((year, training, validation))
    return folds, pd.DataFrame(audit)


def choose_candidate(data, outer_training, outer_year, get_training, spec, study):
    choices = candidates(spec, study)
    folds, fold_audit = inner_folds(data, outer_training, outer_year, get_training, spec)
    config = spec["inner_validation"]
    n_validation = sum(len(validation) for _, _, validation in folds)
    enough = len(folds) >= config["minimum_valid_refits"] and n_validation >= config["minimum_validation_months"]
    scores, predictions = [], []
    for choice in choices:
        valid = trainable(windowed(outer_training, choice), config["minimum_training_months"])
        valid = valid and all(trainable(windowed(train, choice), config["minimum_training_months"]) for _, train, _ in folds)
        reason = "" if valid else "candidate training window lacks history or a class"
        if not enough:
            reason = "insufficient inner validation history"
        total_loss = 0.
        if not reason:
            for inner_year, train, validation in folds:
                p, _, _ = fit_regression(windowed(train, choice), validation, choice["features"], choice["C"], spec)
                row_losses = brier(p, validation.training_target)
                total_loss += row_losses.sum()
                frame = validation[["origin", "training_target", "label_vintage", "label_available_by"]].copy()
                frame = frame.rename(columns={"training_target": "validation_target", "label_vintage": "validation_label_vintage",
                                              "label_available_by": "validation_label_available_by"})
                frame["outer_year"], frame["inner_year"], frame["candidate"] = outer_year, inner_year, choice["candidate"]
                frame["training_label_vintage"] = train.label_vintage.iloc[0]
                frame["brier"] = row_losses
                for i, label in enumerate(CLASSES):
                    frame[f"p_{label}"] = p[:, i]
                predictions.append(frame)
        scores.append({"outer_year": outer_year, **{key: choice[key] for key in ("candidate", "feature_set", "C", "window")},
                       "n_macro_features": len(choice["features"]), "eligible": not reason, "exclusion": reason,
                       "n_validation": n_validation, "n_inner_refits": len(folds),
                       "mean_validation_brier": total_loss / n_validation if not reason else np.nan})
    if enough:
        eligible = [r for r in scores if r["eligible"]]
        if not eligible:
            raise ValueError("No eligible candidate despite sufficient validation folds")
        best = min(r["mean_validation_brier"] for r in eligible)
        # choices/scores already follow the specification's deterministic tie order.
        selected = next(r["candidate"] for r in eligible if r["mean_validation_brier"] <= best + 1e-12)
        choice = next(c for c in choices if c["candidate"] == selected)
        reason = "selected on earlier validation months"
    else:
        choice = next(c for c in choices if c["feature_set"] == "production" and c["C"] == .001 and c["window"] == "expanding")
        reason = "fixed fallback: insufficient inner validation history"
    for row in scores:
        row["selected"] = row["candidate"] == choice["candidate"]
    return choice, reason, pd.DataFrame(scores), fold_audit, pd.concat(predictions, ignore_index=True) if predictions else pd.DataFrame()


def fit_study(dataset, support, archive, spec, study):
    allowed = list(CORE_FEATURES + CPI_FEATURES + FEATURES)
    data = dataset[["origin"] + allowed].copy()
    complete = list(CORE_FEATURES + FEATURES + (CPI_FEATURES if study["include_cpi"] else ()))
    data = data[(data.origin >= pd.Period(study["training_start"], "M")) & np.isfinite(data[complete].to_numpy(float)).all(axis=1)]
    support = pd.PeriodIndex(support, freq="M")
    if not set(support).issubset(set(data.origin)):
        raise ValueError("Original evaluation support is no longer complete")
    cache, label_cache = {}, {}
    def get_training(year):
        if year not in cache:
            cache[year], label_cache[year] = vintage_training(data, pd.Period(f"{year}-01", "M"), archive, spec)
        return cache[year]
    collections = {key: [] for key in ("predictions", "annual_refits", "candidate_scores", "inner_folds",
                                       "inner_predictions", "preprocessing", "coefficients", "selected_training_rows")}
    for year in sorted(set(support.year)):
        training = get_training(year)
        if not trainable(training, spec["inner_validation"]["minimum_training_months"]):
            raise ValueError(f"Untrainable outer refit: {study['name']} {year}")
        evaluation = data[data.origin.isin(support[support.year == year])].copy()
        choice, reason, scores, folds, inner_predictions = choose_candidate(data, training, year, get_training, spec, study)
        selected_training = windowed(training, choice)
        recent = training.tail(120).training_target
        prior = np.array([(recent.eq(label).sum() + 1) / (len(recent) + 3) for label in CLASSES])
        for i, label in enumerate(CLASSES):
            evaluation[f"recent_base_rate_{label}"] = prior[i]
        for model, features in [("macro_only", choice["features"]), ("macro_plus_press", choice["features"] + FEATURES)]:
            p, params, coefs = fit_regression(selected_training, evaluation, features, choice["C"], spec)
            for i, label in enumerate(CLASSES):
                evaluation[f"{model}_{label}"] = p[:, i]
            collections["preprocessing"].append(params.assign(refit_year=year, model=model))
            collections["coefficients"].append(coefs.assign(refit_year=year, model=model))
        evaluation["refit_year"] = year
        evaluation["selected_candidate"] = choice["candidate"]
        collections["predictions"].append(evaluation)
        collections["candidate_scores"].append(scores)
        collections["inner_folds"].append(folds)
        if len(inner_predictions):
            collections["inner_predictions"].append(inner_predictions)
        cols = ["origin", "training_target", "label_vintage", "label_available_by", "target_start", "target_end"]
        collections["selected_training_rows"].append(selected_training[cols].assign(refit_year=year))
        collections["annual_refits"].append(pd.DataFrame([{
            "refit_year": year, **{key: choice[key] for key in ("candidate", "feature_set", "C", "window")},
            "selection_reason": reason, "n_eligible_training": len(training), "n_selected_training": len(selected_training),
            "n_evaluation": len(evaluation), "label_vintage": training.label_vintage.iloc[0],
            "label_available_by": training.label_available_by.iloc[0],
            "first_training_origin": str(selected_training.origin.min()), "last_training_origin": str(selected_training.origin.max()),
            "n_inner_refits": int(folds.used.sum()), "n_validation": int(folds.loc[folds.used, "n_validation"].sum())}]))
        if year % 5 == 0 or year == min(support.year):
            print(f"  {study['name']} {year}: {choice['candidate']} ({reason})", flush=True)
    tables = {name: pd.concat(frames, ignore_index=True) if frames else pd.DataFrame() for name, frames in collections.items()}
    tables["training_label_audit"] = pd.concat([labels.assign(refit_year=year) for year, labels in sorted(label_cache.items())], ignore_index=True)
    # Only now attach final revised truth for retrospective evaluation.
    tables["predictions"] = tables["predictions"].merge(dataset[["origin", "target", "change_percent"]], on="origin", validate="one_to_one")
    return tables


def confidence_summary(predicted, version_name):
    rows = []
    for model in MODELS:
        p = probabilities(predicted, model)
        maximum = p.max(axis=1)
        correct = np.asarray(CLASSES)[p.argmax(axis=1)] == predicted.target
        high = maximum >= .9
        rows.append({"version": version_name, "model": model, "n_months": len(predicted), "n_confidence_ge_90": int(high.sum()),
                     "accuracy_ge_90": correct[high].mean() if high.any() else np.nan,
                     "mean_confidence_ge_90": maximum[high].mean() if high.any() else np.nan})
    return pd.DataFrame(rows)


def plot_and_report(tables, comparison, confidence, spec_hash):
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
    fig, axes = plt.subplots(1, 2, figsize=(11, 4), constrained_layout=True)
    for ax, study in zip(axes, tables):
        frame = comparison[(comparison.study == study) & (comparison.grouping == "overall")]
        for offset, version_name, alpha in [(-.18, "original", .4), (.18, "selected", 1.)]:
            values = frame[frame.version == version_name].set_index("model").loc[list(MODELS), "brier"]
            ax.bar(np.arange(3) + offset, values, .36, color=[COLORS[m] for m in MODELS], alpha=alpha, label=version_name)
        ax.set_xticks(range(3), ["Recent\nbase rate", "Economy\nonly", "Economy +\nnewspapers"])
        ax.set(title=study, ylabel="Brier score (lower is better)", ylim=(0, 1.05)); ax.legend()
    fig.savefig(OUT / "comparison.png", dpi=160); plt.close(fig)
    fig, axes = plt.subplots(2, 3, figsize=(12, 8), constrained_layout=True)
    for row, (study, frames) in enumerate(tables.items()):
        for col, label in enumerate(CLASSES):
            ax = axes[row, col]; ax.plot([0, 1], [0, 1], "--", color="#aaa")
            for model in MODELS:
                frame = frames["calibration"]
                frame = frame[(frame.model == model) & (frame["class"] == label)]
                ax.plot(frame.mean_prediction, frame.observed_share, color=COLORS[model], label=NAMES[model], alpha=.8)
                ax.scatter(frame.mean_prediction, frame.observed_share, color=COLORS[model], s=10 + .4 * frame.n_months)
            ax.set(title=f"{study} · {label}", xlim=(0, 1), ylim=(0, 1), xlabel="Mean predicted probability", ylabel="Observed share")
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="outside upper center", ncol=3, fontsize=9)
    fig.savefig(OUT / "calibration.png", dpi=160); plt.close(fig)
    def image(name):
        return '<img alt="' + name + '" src="data:image/png;base64,' + base64.b64encode((OUT / name).read_bytes()).decode() + '">'
    def table(frame):
        return '<div class="table">' + frame.to_html(index=False, border=0, float_format=lambda x: f"{x:.4f}") + '</div>'
    body = ["<h1>A simpler macro benchmark, selected using earlier data</h1>",
            "<p>Annual verified ProQuest claims, 1900–2010. Exploratory continuation after the original model's error audit.</p>",
            "<p><strong>Finding:</strong> the simpler benchmark lowers Brier and log loss in both studies and eliminates the earlier "
            "forecasts above 90% confidence. The incremental newspaper gain is smaller than in the original comparison. Its core "
            "interval includes no gain, and outside 2007–2009 the combined model has slightly worse Brier loss than economy-only. "
            "These results still do not establish reliable incremental newspaper skill.</p>",
            "<h2>Same months, original and selected models</h2>", image("comparison.png"),
            table(comparison.query("grouping == 'overall'")[["study", "version", "model", "n_months", "brier", "log_loss", "accuracy", "fall_auc"]]),
            "<p>The base rate is unchanged. Original models used eight macro predictors (eleven with CPI), C=1 and expanding history. "
            "The replacement chooses one or two macro predictors (two or three with CPI), stronger regularization and a training window "
            "using only data available before each forecast year. Differences are exploratory comparisons on already inspected periods.</p>"]
    for study, frames in tables.items():
        interval = frames["paired_intervals"].query("model == 'macro_plus_press' and baseline == 'macro_only' and metric == 'brier' and block_years == 5").iloc[0]
        body += [f"<h3>{study}: newspaper contribution</h3>",
                 f"<p>Adding newspapers improves Brier loss by {interval.improvement:+.4f}; paired five-year-block 95% interval "
                 f"[{interval.low:+.4f}, {interval.high:+.4f}], using {int(interval.n_blocks)} blocks. Positive means lower loss. "
                 "The combined model uses the macro-selected settings and identical training months, with four press signals added.</p>",
                 table(frames["paired_intervals"].query("metric == 'brier' and block_years == 5"))]
    body += ["<h2>Selection and information timing</h2>",
             "<p>Candidate feature sets are six-month production growth alone, or with the three-month unemployment-rate change. "
             "The CPI check appends 12-month inflation to both. C is 0.001, 0.01 or 0.1; smaller means stronger regularization. "
             "History is expanding or the latest 120 eligible mature months. This gives twelve candidates per study.</p>",
             "<p>Each January, consider the preceding five January refits. Fit each inner model using the production-label vintage "
             "available at that inner refit, with the three-month maturity allowance. Forecast its following calendar months. "
             "Score only months whose labels are mature and available by the outer January, using that outer vintage. Later revisions "
             "known by the outer refit may alter validation labels; final revised evaluation truth never enters selection.</p>",
             "<p>At least 60 training months and all three training classes are required per fit. Select the lowest mean Brier score "
             "on identical validation months, requiring at least 24 months from two inner refits. A candidate that cannot fit every "
             "eligible fold is unavailable. Ties prefer fewer features, smaller C, then expanding history. With inadequate validation, "
             "use the fixed production-only, C=0.001, expanding fallback (plus inflation in the CPI study). Scale within each fit's "
             "training data only. No imputation, clipping, class weighting or evaluation-set recalibration is used.</p>"]
    for study, frames in tables.items():
        refits = frames["annual_refits"]
        counts = refits.groupby(["feature_set", "C", "window", "selection_reason"]).size().rename("n_refits").reset_index()
        body += [f"<h3>{study}: selected configurations</h3>", table(counts),
                 table(refits[refits.selection_reason.str.contains("fallback")][["refit_year", "candidate", "n_validation", "n_inner_refits"]])]
    body += ["<h2>Calibration and confidence</h2>", image("calibration.png"), table(confidence),
             "<p>Class calibration uses fixed probability tenths; marker area increases with count. The confidence table covers "
             "forecasts with at least 90% on the predicted class. Empty groups are undefined. Improved loss or fewer extreme "
             "probabilities does not prove complete calibration, and small bins remain noisy.</p>",
             "<p><strong>Tradeoff:</strong> probability losses improve, but classification accuracy does not improve uniformly. "
             "CPI downturn ranking deteriorates substantially: fall AUC falls from 0.936 to 0.213 for economy-only, and from "
             "0.987 to 0.277 with newspapers. The short study remains a weak recession-discrimination benchmark despite avoiding "
             "its earlier extreme probability errors. Core fall AUC improves, so the effect is not uniform across histories.</p>",
             "<h2>Era and crisis stability</h2>"]
    for study, frames in tables.items():
        five = frames["metrics"].query("grouping == 'five_year'").pivot(index="period", columns="model", values="brier")
        five["newspaper_improvement"] = five.macro_only - five.macro_plus_press
        leave = frames["leave_block_out"].query("metric == 'brier'")
        body += [f"<h3>{study}</h3>", table(five.reset_index()),
                 table(frames["metrics"].query("grouping == 'sensitivity'")[["period", "model", "n_months", "brier", "log_loss", "accuracy"]]),
                 f"<p>Leaving one calendar five-year cell out gives newspaper Brier improvements from {leave.improvement.min():+.4f} "
                 f"to {leave.improvement.max():+.4f}. These are scoring exclusions; the models are not refitted.</p>"]
    body += ["<h2>Limits and reproduction</h2>",
             "<p>The primary result is incremental newspaper information beyond the selected macro benchmark. Intervals resample "
             "fixed forecasts in 2/5/10-year blocks; they do not rerun training or selection. Short CPI intervals have very few blocks "
             "and its ten-year interval has only one. They cannot support strong generalization claims. Overlapping target windows, "
             "historical revisions, stale quarterly snapshots and changing economic conditions remain limitations.</p>",
             "<p>The candidate family was motivated by previously inspected results. Inner time splits prevent direct future-label "
             "leakage within a refit, but do not make the historical evaluation an untouched holdout. Query selection, machine-extracted "
             "labels and missing quotations still require human validation. No LOC or old crisis-window claims are included.</p>",
             "<p>Run <code>python src/proquest_macro_benchmark.py</code> with <code>requirements-proquest-information.txt</code>. "
             "Original forecasts remain untouched. This directory contains specification, candidate scores, inner predictions, fold "
             "timing, vintage training-label audits, chosen training rows, coefficients, preprocessing, final probabilities and "
             "stability tables. Source, code and specification hashes are in summary.json.</p>",
             f"<p>Specification SHA-256: <code>{spec_hash}</code>.</p>"]
    head = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Selected vintage macro benchmark</title><style>body{font:16px/1.6 system-ui,sans-serif;max-width:1120px;margin:40px auto;padding:0 24px 60px;background:#f7f8fa;color:#19313c}h1{font-size:34px;line-height:1.2}h2{margin-top:40px}img{width:100%;background:white;margin:16px 0}.table{overflow-x:auto;background:white;border:1px solid #dce3e8;margin:16px 0}table{border-collapse:collapse;font-size:13px;width:100%}td,th{padding:8px 12px;text-align:right;white-space:nowrap;border-bottom:1px solid #e5e9ed}th{background:#e8f1f0}code{overflow-wrap:anywhere}</style><main>'''
    (OUT / "report.html").write_text(head + "\n".join(body) + "</main></html>")


def main():
    spec = load_spec()
    original = json.loads((SOURCE / "summary.json").read_text())
    tracked = {**original["inputs_sha256"], **original["code_sha256"], str(SPEC_PATH): digest(SPEC_PATH),
               str(SOURCE / "summary.json"): digest(SOURCE / "summary.json"),
               str(SOURCE / "forecast_dataset.csv"): digest(SOURCE / "forecast_dataset.csv")}
    for study in spec["studies"]:
        for name in ("predictions", "metrics"):
            path = SOURCE / study["name"] / f"{name}.csv"
            tracked[str(path)] = digest(path)
    for path, expected in tracked.items():
        if digest(path) != expected:
            raise ValueError(f"Input changed: {path}")
    archives, _, _ = load_archives()
    data = pd.read_csv(SOURCE / "forecast_dataset.csv")
    data["origin"] = pd.PeriodIndex(data.origin, freq="M")
    all_tables, comparisons, confidence = {}, [], []
    for study in spec["studies"]:
        name = study["name"]
        print(f"Selecting and fitting {name} with nested historical time splits...", flush=True)
        previous = pd.read_csv(SOURCE / name / "predictions.csv")
        previous["origin"] = pd.PeriodIndex(previous.origin, freq="M")
        tables = fit_study(data, previous.origin, archives["IPT"], spec, study)
        predicted = tables["predictions"]
        if predicted.origin.tolist() != previous.origin.tolist() or predicted.target.tolist() != previous.target.tolist():
            raise ValueError("Evaluation support/targets differ from original experiment")
        np.testing.assert_allclose(probabilities(predicted, "recent_base_rate"), probabilities(previous, "recent_base_rate"), atol=1e-12)
        for model in MODELS:
            predicted[f"{model}_brier"], predicted[f"{model}_log_loss"] = losses(predicted, model)
        tables.update(evaluate(predicted, spec, study))
        all_tables[name] = tables
        for version_name, frame in [("original", pd.read_csv(SOURCE / name / "metrics.csv")), ("selected", tables["metrics"])]:
            comparisons.append(frame.assign(study=name, version=version_name))
        confidence.extend([confidence_summary(previous, "original").assign(study=name), confidence_summary(predicted, "selected").assign(study=name)])
        dest = OUT / name
        dest.mkdir(exist_ok=True)
        for table_name, frame in tables.items():
            frame.to_csv(dest / f"{table_name}.csv", index=False)
        print(tables["metrics"].query("grouping == 'overall'").to_string(index=False), flush=True)
    comparison, confidence = pd.concat(comparisons, ignore_index=True), pd.concat(confidence, ignore_index=True)
    comparison.to_csv(OUT / "comparison.csv", index=False)
    confidence.to_csv(OUT / "confidence.csv", index=False)
    plot_and_report(all_tables, comparison, confidence, tracked[str(SPEC_PATH)])
    for path, expected in tracked.items():
        if digest(path) != expected:
            raise ValueError(f"Input changed during fitting: {path}")
    summary = {"spec_sha256": tracked[str(SPEC_PATH)], "inputs_sha256": tracked,
               "code_sha256": {str(Path(__file__).relative_to(Path.cwd())): digest(__file__)},
               "versions": {name: version(name) for name in ("numpy", "pandas", "matplotlib", "scikit-learn")},
               "overall_metrics": comparison.query("grouping == 'overall'").to_dict("records"),
               "fallback_years": {name: frame["annual_refits"].loc[frame["annual_refits"].selection_reason.str.contains("fallback"), "refit_year"].tolist() for name, frame in all_tables.items()}}
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n")
    print(f"Report: {OUT / 'report.html'}", flush=True)


if __name__ == "__main__":
    main()
