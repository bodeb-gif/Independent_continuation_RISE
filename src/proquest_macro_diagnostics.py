"""Post-hoc error audit of frozen ProQuest vintage-macro forecasts.

No fitting, recalibration, predictor selection, or source edits. Revised labels
are joined only to diagnose revisions after the original forecasts were saved.
"""
import base64
import hashlib
from importlib.metadata import version
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from proquest_information import CLASSES, probabilities
from proquest_macro_information import COLORS, MODELS, NAMES

SOURCE = Path("data/scored/proquest/macro_information")
OUT = Path("data/scored/proquest/macro_diagnostics")
SPEC = {
    "status": "Post-hoc descriptive diagnosis of already inspected historical forecasts; no new holdout or fitted model",
    "studies": ["core", "with_cpi"], "high_confidence_threshold": .9, "large_feature_z_threshold": 3.,
    "confidence_bins": [0., .5, .6, .7, .8, .9, 1.0000001], "worst_months_per_model": 10,
    "comparisons": "Frozen economy-only and economy-plus-newspaper forecasts versus recent base rate on identical months",
    "loss_decomposition": "Class/period contribution = sum(model loss minus base-rate loss in group) / all evaluation months; contributions add to the overall gap",
    "revisions": "Compare labels actually used at each annual refit with final revised outcomes. Report each refit separately and one first-used row per distinct training origin. First use is not first release.",
    "feature_shift": "Standardize using saved training parameters; compare with observed training range. A large z-score is descriptive, not a hypothesis test or a causal effect.",
    "training_fit": "Reconstruct training probabilities from saved coefficients, using the exact original eligible training months and vintage labels. In-sample fit is optimistic and is not validation.",
    "forbidden_actions": ["refit models", "calibrate on evaluation outcomes", "use revised labels as features", "modify original exports"]
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def score_arrays(p, target):
    y = pd.Series(target).map({c: i for i, c in enumerate(CLASSES)}).to_numpy(int)
    return ((p - np.eye(3)[y]) ** 2).sum(axis=1), -np.log(np.clip(p[np.arange(len(y)), y], 1e-15, 1.))


def month_errors(predicted, study):
    records = []
    for model in MODELS:
        p = probabilities(predicted, model)
        top = np.asarray(CLASSES)[p.argmax(axis=1)]
        brier, logloss = score_arrays(p, predicted.target)
        frame = predicted[["origin", "target", "refit_year"]].copy()
        frame["study"], frame["model"] = study, model
        frame["predicted_class"], frame["confidence"] = top, p.max(axis=1)
        frame["correct"] = top == predicted.target
        frame["brier"], frame["log_loss"] = brier, logloss
        frame["excess_brier"] = brier - predicted.recent_base_rate_brier
        frame["excess_log_loss"] = logloss - predicted.recent_base_rate_log_loss
        for i, label in enumerate(CLASSES):
            frame[f"p_{label}"] = p[:, i]
        records.append(frame)
    return pd.concat(records, ignore_index=True)


def error_tables(errors):
    groups, confidence, class_calibration = [], [], []
    for (study, model), frame in errors.groupby(["study", "model"], sort=False):
        year = frame.origin.str[:4].astype(int)
        subsets = [("overall", "all", frame)]
        subsets += [("actual_class", label, sub) for label, sub in frame.groupby("target")]
        subsets += [("five_year", f"{block}–{min(block + 4, 2010)}", sub) for block, sub in frame.groupby(year // 5 * 5)]
        subsets += [("confidence", ">=90%", frame[frame.confidence >= SPEC["high_confidence_threshold"]])]
        for grouping, label, sub in subsets:
            groups.append({"study": study, "model": model, "grouping": grouping, "group": label,
                           "n_months": len(sub), "share_of_months": len(sub) / len(frame),
                           "brier": sub.brier.mean(), "log_loss": sub.log_loss.mean(),
                           "accuracy": sub.correct.mean(), "mean_confidence": sub.confidence.mean(),
                           "excess_brier": sub.excess_brier.mean(), "excess_log_loss": sub.excess_log_loss.mean(),
                           "brier_gap_contribution": sub.excess_brier.sum() / len(frame),
                           "log_loss_gap_contribution": sub.excess_log_loss.sum() / len(frame)})
        bins = pd.cut(frame.confidence, SPEC["confidence_bins"], right=False,
                      labels=["<50%", "50–60%", "60–70%", "70–80%", "80–90%", ">=90%"])
        for bucket, sub in frame.groupby(bins, observed=True):
            confidence.append({"study": study, "model": model, "bin": str(bucket), "n_months": len(sub),
                               "mean_confidence": sub.confidence.mean(), "accuracy": sub.correct.mean(),
                               "confidence_minus_accuracy": sub.confidence.mean() - sub.correct.mean()})
        for label in CLASSES:
            p = frame[f"p_{label}"]
            observed = frame.target.eq(label)
            class_calibration.append({"study": study, "model": model, "class": label, "n_months": len(frame),
                                      "observed_share": observed.mean(), "mean_probability": p.mean(),
                                      "probability_bias": p.mean() - observed.mean(),
                                      "brier_component": ((p - observed.astype(float)) ** 2).mean()})
    return pd.DataFrame(groups), pd.DataFrame(confidence), pd.DataFrame(class_calibration)


def revision_tables(audit, full, study):
    used = audit[audit.used].copy()
    joined = used.merge(full[["origin", "target", "change_percent"]], on="origin", validate="many_to_one")
    if joined.target.isna().any():
        raise ValueError("Missing revised outcome for a used training origin")
    joined["study"] = study
    joined["class_changed"] = joined.training_target != joined.target
    joined["growth_revision_pp"] = joined.change_percent - joined.training_change_percent
    joined["absolute_growth_revision_pp"] = joined.growth_revision_pp.abs()
    joined["vintage_distance_to_boundary_pp"] = (joined.training_change_percent.abs() - 2.).abs()
    first = joined.sort_values(["refit_year", "origin"]).drop_duplicates("origin").copy()
    summaries = []
    for basis, name, frame in [("unique_origin", "first use in this experiment", first)] + [
            ("annual_refit", str(year), group) for year, group in joined.groupby("refit_year")]:
        summaries.append({"study": study, "basis": basis, "refit": name, "n_training_origins": len(frame),
                          "changed_classes": int(frame.class_changed.sum()), "changed_share": frame.class_changed.mean(),
                          "mean_absolute_growth_revision_pp": frame.absolute_growth_revision_pp.mean(),
                          **{f"vintage_{c}_share": frame.training_target.eq(c).mean() for c in CLASSES},
                          **{f"revised_{c}_share": frame.target.eq(c).mean() for c in CLASSES}})
    transitions = first.groupby(["training_target", "target"]).size().rename("n_origins").reset_index().assign(study=study)
    return joined, first, pd.DataFrame(summaries), transitions


def reconstructed_probabilities(frame, params, coefs):
    params = params.set_index("feature")
    features = params.index.tolist()
    z = (frame[features].to_numpy(float) - params["mean"].to_numpy()) / params["scale"].to_numpy()
    coefficients = coefs.pivot(index="class", columns="feature", values="coefficient").loc[list(CLASSES)]
    logits = z @ coefficients[features].to_numpy().T + coefficients["intercept"].to_numpy()
    exp = np.exp(logits - logits.max(axis=1, keepdims=True))
    return exp / exp.sum(axis=1, keepdims=True), z, coefficients, features


def fit_diagnostics(predicted, audit, full, params, coefs, study):
    fit, shift, contributions = [], [], []
    indexed = full.set_index("origin")
    for year, evaluation in predicted.groupby("refit_year"):
        labels = audit[(audit.refit_year == year) & audit.used].sort_values("origin")
        training = indexed.loc[labels.origin].copy()
        for model in ("macro_only", "macro_plus_press"):
            prep = params[(params.refit_year == year) & (params.model == model)]
            coef = coefs[(coefs.refit_year == year) & (coefs.model == model)]
            train_p, _, _, _ = reconstructed_probabilities(training, prep, coef)
            test_p, z, coefficients, features = reconstructed_probabilities(evaluation, prep, coef)
            np.testing.assert_allclose(test_p, probabilities(evaluation, model), atol=1e-12)
            vintage_loss = score_arrays(train_p, labels.training_target)
            revised_train_loss = score_arrays(train_p, training.target)
            evaluation_loss = score_arrays(test_p, evaluation.target)
            fit.append({"study": study, "model": model, "refit_year": year, "n_training": len(training),
                        "n_evaluation": len(evaluation), "train_vintage_brier": vintage_loss[0].mean(),
                        "train_vintage_log_loss": vintage_loss[1].mean(),
                        "train_revised_brier": revised_train_loss[0].mean(), "train_revised_log_loss": revised_train_loss[1].mean(),
                        "evaluation_brier": evaluation_loss[0].mean(), "evaluation_log_loss": evaluation_loss[1].mean(),
                        **{f"training_{c}_share": labels.training_target.eq(c).mean() for c in CLASSES},
                        **{f"evaluation_{c}_share": evaluation.target.eq(c).mean() for c in CLASSES}})
            for j, feature in enumerate(features):
                lo, hi = training[feature].min(), training[feature].max()
                for i, row in enumerate(evaluation.itertuples()):
                    value = getattr(row, feature)
                    shift.append({"study": study, "model": model, "refit_year": year, "origin": row.origin,
                                  "feature": feature, "value": value, "training_min": lo, "training_max": hi,
                                  "z": z[i, j], "absolute_z": abs(z[i, j]),
                                  "outside_training_range": bool(value < lo - 1e-10 or value > hi + 1e-10),
                                  "large_z": bool(abs(z[i, j]) > SPEC["large_feature_z_threshold"])})
            for i, row in enumerate(evaluation.itertuples()):
                predicted_class = CLASSES[test_p[i].argmax()]
                difference = coefficients.loc[predicted_class] - coefficients.loc[row.target]
                terms = np.r_[difference["intercept"], z[i] * difference[features].to_numpy()]
                # Linear contributions add exactly to the predicted-vs-true logit margin.
                margin = float(terms.sum())
                for feature, contribution in zip(["intercept"] + features, terms):
                    contributions.append({"study": study, "model": model, "refit_year": year, "origin": row.origin,
                                          "predicted_class": predicted_class, "target": row.target,
                                          "correct": predicted_class == row.target, "feature": feature,
                                          "logit_margin_contribution": contribution, "total_logit_margin": margin})
    return pd.DataFrame(fit), pd.DataFrame(shift), pd.DataFrame(contributions)


def figures(tables):
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
                         "axes.spines.top": False, "axes.spines.right": False})
    fig, axes = plt.subplots(1, 2, figsize=(11, 4), constrained_layout=True)
    for ax, study in zip(axes, SPEC["studies"]):
        for model in MODELS:
            sub = tables["confidence_bins"].query("study == @study and model == @model")
            ax.plot(sub.mean_confidence, sub.accuracy, color=COLORS[model], label=NAMES[model], alpha=.75)
            ax.scatter(sub.mean_confidence, sub.accuracy, color=COLORS[model], s=15 + sub.n_months)
        ax.plot([.3, 1], [.3, 1], "--", color="#999")
        ax.set(xlim=(.3, 1.02), ylim=(-.02, 1.02), xlabel="Mean confidence in predicted class", ylabel="Actual accuracy", title=study)
    axes[0].legend(fontsize=8)
    fig.savefig(OUT / "confidence_accuracy.png", dpi=160); plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4), constrained_layout=True)
    for ax, study in zip(axes, SPEC["studies"]):
        sub = tables["error_groups"].query("study == @study and grouping == 'actual_class'")
        for offset, model in [(-.18, "macro_only"), (.18, "macro_plus_press")]:
            values = sub[sub.model == model].set_index("group").loc[list(CLASSES), "brier_gap_contribution"]
            ax.bar(np.arange(3) + offset, values, .36, label=NAMES[model], color=COLORS[model])
        ax.axhline(0, color="#777", lw=1); ax.set_xticks(range(3), CLASSES)
        ax.set(title=study, xlabel="Realized outcome", ylabel="Contribution to Brier gap versus base rate")
    axes[0].legend(fontsize=8)
    fig.savefig(OUT / "class_loss_contributions.png", dpi=160); plt.close(fig)
    fig, axes = plt.subplots(2, 1, figsize=(11, 7), constrained_layout=True)
    for ax, study in zip(axes, SPEC["studies"]):
        frame = tables["annual_fit"].query("study == @study and model == 'macro_only'")
        for field, label, color in [("train_vintage_log_loss", "Training fit (vintage labels)", "#8494a5"),
                                    ("train_revised_log_loss", "Same training probabilities, revised labels", "#087f83"),
                                    ("evaluation_log_loss", "Forecast-year evaluation", "#c18b36")]:
            ax.plot(frame.refit_year, frame[field], label=label, color=color)
        ax.set(title=study, xlabel="Annual refit year", ylabel="Economy-only log loss")
    axes[0].legend(fontsize=8)
    fig.savefig(OUT / "training_evaluation_loss.png", dpi=160); plt.close(fig)


def report(tables, findings):
    def table(frame):
        return '<div class="table">' + frame.to_html(index=False, border=0, float_format=lambda x: f"{x:.4f}") + '</div>'
    def image(name):
        return '<img alt="' + name.replace('_', ' ') + '" src="data:image/png;base64,' + base64.b64encode((OUT / name).read_bytes()).decode() + '">'
    groups = tables["error_groups"]
    body = ["<h1>Why the macro benchmark struggles</h1>",
            "<p>Post-hoc audit of the frozen ProQuest forecasts. Core: 1977–2010 (408 months). With CPI: 2002–2010 (108 months). "
            "No models were fitted or calibrated for this audit.</p>",
            "<p><strong>Main finding:</strong> probability errors on flat outcomes drive the economy-only model's disadvantage. "
            "High-confidence forecasts are often wrong, and the short CPI training history produces extreme extrapolation. "
            "Training-label revisions occur, but this audit does not identify them as the cause of the forecasting losses.</p>",
            "<h2>1. Flat outcomes drive the baseline gap</h2>", image("class_loss_contributions.png"),
            table(groups.query("grouping == 'actual_class' and model == 'macro_only'")[["study", "group", "n_months", "brier", "excess_brier", "brier_gap_contribution"]]),
            "<p>Positive values mean worse loss than the recent base rate. Each class contribution is its summed excess loss divided "
            "by all evaluation months, so the three contributions add to the overall gap. These are groups by realized outcome, "
            "not individual probability components. Flat means production changes within ±2% over six months; it is not literal zero growth.</p>",
            table(tables["class_calibration"][["study", "model", "class", "observed_share", "mean_probability", "probability_bias"]]),
            "<h2>2. Confidence exceeds accuracy</h2>", image("confidence_accuracy.png"),
            table(groups.query("grouping == 'confidence'")[["study", "model", "n_months", "mean_confidence", "accuracy", "log_loss"]]),
            "<p>The table isolates forecasts with at least 90% probability on the predicted class. Zero-count rows are intentionally "
            "undefined. Chart bins are fixed before this diagnostic run; dot area increases with the count. Above the diagonal would "
            "mean underconfidence, below means overconfidence. Bin estimates are descriptive and can be noisy. Overlapping six-month "
            "targets mean months are not independent replications.</p>",
            "<h2>3. Short training history and extrapolation</h2>", image("training_evaluation_loss.png"),
            "<p>Training curves reconstruct the saved model on its own training months. Their advantage is expected and does not "
            "measure honest validation performance. The revised-label curve changes only the scoring label, holding probabilities "
            "and months fixed. A large training/evaluation gap is compatible with overfitting, distribution change, or both.</p>",
            table(tables["annual_fit"].query("study == 'with_cpi' and model == 'macro_only'")[["refit_year", "n_training", "train_vintage_log_loss", "train_revised_log_loss", "evaluation_log_loss", "training_flat_share", "evaluation_flat_share"]]),
            table(tables["feature_shift_summary"].sort_values(["study", "model", "large_z_months"], ascending=[True, True, False]).groupby(["study", "model"], sort=False).head(3)),
            "<p>Feature shifts use that year's saved training mean and scale. We flag |z| &gt; 3 and values outside the training "
            "range; neither flag is a normal-distribution assumption, a causal estimate or an automatic exclusion rule.</p>"]
    example = findings["cpi_example"]
    body += [f"<p><strong>Concrete example: {example['origin']}.</strong> The economy-only model assigned rise probability "
             f"{example['rise_probability']:.8f}, but the revised outcome was {example['target']}. The unemployment 12-month change "
             f"was {example['unemployment_change_12m']:.2f} percentage points, {example['z']:.2f} training standard deviations above "
             f"its training mean. That feature contributed {example['logit_margin_contribution']:.2f} of the "
             f"{example['total_logit_margin']:.2f} rise-versus-flat logit margin. This is an exact coefficient decomposition, "
             "not a causal explanation of the economy.</p>",
             "<h2>4. Historical labels do change</h2>",
             table(tables["revision_summary"].query("basis == 'unique_origin'")[["study", "n_training_origins", "changed_classes", "changed_share", "mean_absolute_growth_revision_pp"]]),
             "<p>Each row above uses one first-used label per distinct training origin, compared with final revised truth. "
             "First use means the first included refit in this experiment, not the first published estimate. A separate CSV gives "
             "every annual refit. Pooling all refit rows would repeatedly count the same historical outcomes and overweight long-lived "
             "training observations. Changes in growth rates are measured in percentage points.</p>",
             table(tables["revision_transitions"]),
             "<p>Revisions near the ±2% boundary can switch a class even when the change in growth is small. Revisions and moving "
             "class proportions complicate learning, but these descriptive counts cannot establish how much loss they caused. "
             "No revised training labels have been fed back into the original models.</p>",
             "<h2>5. Where the losses occur</h2>",
             table(groups.query("grouping == 'five_year' and model == 'macro_only'")[["study", "group", "n_months", "brier", "log_loss", "brier_gap_contribution", "log_loss_gap_contribution"]]),
             table(tables["worst_months"].query("model == 'macro_only'")[["study", "rank", "origin", "target", "predicted_class", "confidence", "log_loss", "excess_log_loss"]]),
             "<p>Worst months are ranked by economy-only log loss within each study, after outcomes were observed. They are diagnostic "
             "examples, not a newly selected test sample. The companion CSV includes all models and the full error table retains every month.</p>",
             "<h2>Implications for the next benchmark</h2>",
             "<p>Prioritize a small macro predictor set, stronger regularization candidates and forward-time validation within each "
             "training window. Compare expansion/rolling histories only through that same training-only procedure. Assess calibration "
             "using earlier out-of-sample predictions; do not recalibrate on these evaluation years. Keep the original base rate and "
             "identical evaluation support. Then test the incremental newspaper contribution. The short CPI sample should remain a "
             "sensitivity check, with its short history and missing 2001 training class explicit.</p>",
             "<p>These recommendations are motivated by an already inspected sample. A later model comparison on these years remains "
             "exploratory, even with proper internal time splits. Human validation, selected-query coverage, quarterly vintage staleness "
             "and the broad production target remain separate limitations. No LOC or crisis-window claims are added.</p>",
             "<h2>Reproduce and inspect</h2>",
             "<p><code>python src/proquest_macro_diagnostics.py</code>, with the existing information-model dependencies. "
             "The source forecasts remain in <code>data/scored/proquest/macro_information/</code>. This folder contains month errors, "
             "additive loss decompositions, confidence bins, class probabilities, annual training/evaluation diagnostics, feature shifts, "
             "logit contributions, revision rows and transitions, and provenance hashes. All original inputs are checked before and "
             "after the audit. No new model or calibration was fitted.</p>"]
    head = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ProQuest macro model error audit</title><style>
body{font:16px/1.6 system-ui,sans-serif;max-width:1120px;margin:40px auto;padding:0 24px 60px;background:#f7f8fa;color:#19313c}
h1{font-size:34px;line-height:1.2}h2{margin-top:40px}img{width:100%;background:white;margin:16px 0;border-radius:8px}
.table{overflow-x:auto;background:white;border:1px solid #dce3e8;margin:16px 0}table{border-collapse:collapse;font-size:13px;width:100%}
td,th{padding:8px 12px;text-align:right;white-space:nowrap;border-bottom:1px solid #e5e9ed}th{background:#e8f1f0}code{overflow-wrap:anywhere}</style><main>'''
    (OUT / "report.html").write_text(head + "\n".join(body) + "</main></html>")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    source_summary = json.loads((SOURCE / "summary.json").read_text())
    tracked = {**source_summary["inputs_sha256"], **source_summary["code_sha256"],
               str(SOURCE / "summary.json"): sha(SOURCE / "summary.json")}
    paths = [SOURCE / "forecast_dataset.csv"]
    paths += [SOURCE / study / f"{name}.csv" for study in SPEC["studies"]
              for name in ("predictions", "preprocessing", "coefficients", "training_label_audit")]
    tracked.update({str(path): sha(path) for path in paths})
    for path, expected in tracked.items():
        if sha(path) != expected:
            raise ValueError(f"Input changed since the source experiment: {path}")
    (OUT / "diagnostic_spec.json").write_text(json.dumps(SPEC, indent=2) + "\n")
    full = pd.read_csv(SOURCE / "forecast_dataset.csv")
    collections = {key: [] for key in ("month_errors", "revision_rows", "first_used_revisions", "revision_summary", "revision_transitions", "annual_fit", "feature_shifts", "logit_contributions")}
    for study in SPEC["studies"]:
        print(f"Auditing frozen {study} forecasts...", flush=True)
        predicted, params, coefs, audit = [pd.read_csv(SOURCE / study / f"{name}.csv")
                                         for name in ("predictions", "preprocessing", "coefficients", "training_label_audit")]
        collections["month_errors"].append(month_errors(predicted, study))
        for key, frame in zip(("revision_rows", "first_used_revisions", "revision_summary", "revision_transitions"), revision_tables(audit, full, study)):
            collections[key].append(frame)
        for key, frame in zip(("annual_fit", "feature_shifts", "logit_contributions"), fit_diagnostics(predicted, audit, full, params, coefs, study)):
            collections[key].append(frame)
    tables = {key: pd.concat(frames, ignore_index=True) for key, frames in collections.items()}
    for key, frame in zip(("error_groups", "confidence_bins", "class_calibration"), error_tables(tables["month_errors"])):
        tables[key] = frame
    shifts = tables["feature_shifts"]
    tables["feature_shift_summary"] = shifts.groupby(["study", "model", "feature"], sort=False).agg(
        n_months=("origin", "size"), large_z_months=("large_z", "sum"), outside_training_range_months=("outside_training_range", "sum"),
        max_absolute_z=("absolute_z", "max")).reset_index()
    worst = tables["month_errors"].sort_values("log_loss", ascending=False).groupby(["study", "model"], sort=False).head(SPEC["worst_months_per_model"]).copy()
    worst["rank"] = worst.groupby(["study", "model"]).cumcount() + 1
    tables["worst_months"] = worst.sort_values(["study", "model", "rank"])
    example = tables["month_errors"].query("study == 'with_cpi' and model == 'macro_only' and origin == '2002-09'").iloc[0]
    feature = shifts.query("study == 'with_cpi' and model == 'macro_only' and origin == '2002-09' and feature == 'unemployment_change_12m'").iloc[0]
    term = tables["logit_contributions"].query("study == 'with_cpi' and model == 'macro_only' and origin == '2002-09' and feature == 'unemployment_change_12m'").iloc[0]
    findings = {"cpi_example": {"origin": example.origin, "target": example.target, "rise_probability": example.p_rise,
                               "unemployment_change_12m": feature.value, "z": feature.z,
                               "logit_margin_contribution": term.logit_margin_contribution, "total_logit_margin": term.total_logit_margin},
                "first_used_revisions": tables["revision_summary"].query("basis == 'unique_origin'").to_dict("records"),
                "high_confidence": tables["error_groups"].query("grouping == 'confidence' and n_months > 0").to_dict("records")}
    for name, frame in tables.items():
        frame.to_csv(OUT / f"{name}.csv", index=False)
    figures(tables)
    report(tables, findings)
    for path, expected in tracked.items():
        if sha(path) != expected:
            raise ValueError(f"Input changed during diagnosis: {path}")
    summary = {"specification": SPEC, "inputs_sha256": tracked, "code_sha256": {str(Path(__file__).relative_to(Path.cwd())): sha(__file__)},
               "versions": {name: version(name) for name in ("numpy", "pandas", "matplotlib")}, "findings": findings}
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n")
    print(tables["error_groups"].query("grouping == 'confidence'")[["study", "model", "n_months", "mean_confidence", "accuracy"]].to_string(index=False))
    print(tables["revision_summary"].query("basis == 'unique_origin'").to_string(index=False))
    print(f"Report: {OUT / 'report.html'}")


if __name__ == "__main__":
    main()
