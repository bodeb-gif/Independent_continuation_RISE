"""Exploratory forward-time test of monthly ProQuest economic information.

Uses a specification saved before fitting, verified annual claims only, and
frozen industrial-production outcomes. No macro values enter model features.
"""
import argparse
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
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.preprocessing import StandardScaler

from proquest_descriptive import realized_outcome
from proquest_panel import FEATURES, build_panels, forecast_features, read_claims

OUT = Path("data/scored/proquest/monthly_information")
SPEC_PATH = OUT / "evaluation_spec.json"
CLASSES = ("fall", "flat", "rise")
MODELS = ("historical_base_rate", "coverage_only", "base_rate_plus_press")
PAIRS = (("base_rate_plus_press", "historical_base_rate"),
         ("base_rate_plus_press", "coverage_only"), ("coverage_only", "historical_base_rate"))


def load_spec(path=SPEC_PATH):
    spec = json.loads(path.read_text())
    if tuple(spec["press_features"]) != FEATURES or tuple(spec["class_order"]) != CLASSES:
        raise ValueError("Specification and feature/class definitions disagree")
    if spec["horizon_months"] != 6 or spec["flat_band_percent"] != 2.:
        raise ValueError("This experiment requires the specified six-month, 2% target")
    return spec, hashlib.sha256(path.read_bytes()).hexdigest()


def read_production():
    metadata = json.loads(Path("data/scored/proquest/descriptive/summary.json").read_text())["reference"]["general_business"]
    path = Path(metadata["file"])
    if hashlib.sha256(path.read_bytes()).hexdigest() != metadata["sha256"]:
        raise ValueError("Frozen industrial-production reference hash changed")
    data = pd.read_csv(path)
    series = pd.Series(pd.to_numeric(data.iloc[:, 1], errors="coerce").to_numpy(),
                       index=pd.PeriodIndex(pd.to_datetime(data.iloc[:, 0]), freq="M")).dropna()
    if not series.index.is_unique:
        raise ValueError("Duplicate industrial-production months")
    return series, metadata


def targets(origins, production, spec):
    rows = []
    for origin in origins:
        start = origin - 1
        end = start + spec["horizon_months"]
        if start < production.index.min():
            label, reason = None, "before industrial-production coverage"
        else:
            direction, _, reason = realized_outcome({"general_business": production}, "general_business", str(start), spec["horizon_months"])
            label = {"worsen": "fall", "flat": "flat", "improve": "rise"}.get(direction)
        change = 100 * (production[end] / production[start] - 1) if label is not None else np.nan
        rows.append({"origin": origin, "target_start": start, "target_end": end,
                     "label_available": end + spec["label_release_allowance_months"],
                     "target": label, "change_percent": change, "target_exclusion": reason})
    return pd.DataFrame(rows)


def training_mask(data, refit_origin):
    return (data.origin < refit_origin) & (data.label_available < refit_origin) & data.target.notna()


def preprocess(training, evaluation):
    """Imputation and scaling fitted exclusively on eligible training months."""
    train = training[list(FEATURES)].astype(float)
    test = evaluation[list(FEATURES)].astype(float)
    medians = train.median().fillna(0.)
    scaler = StandardScaler().fit(train.fillna(medians))
    train_scaled = scaler.transform(train.fillna(medians))
    test_scaled = scaler.transform(test.fillna(medians))
    train_missing = train.isna().astype(float).to_numpy()
    test_missing = test.isna().astype(float).to_numpy()
    params = pd.DataFrame({"feature": FEATURES, "median": medians.to_numpy(),
                           "mean": scaler.mean_, "scale": scaler.scale_})
    return (np.column_stack([train_scaled, train_missing]), np.column_stack([test_scaled, test_missing]),
            train_missing, test_missing, params)


def fit_forward(data, spec):
    predictions, refits, coefficients, preprocessing = [], [], [], []
    first, last = pd.Period(spec["evaluation_start"], "M"), pd.Period(spec["evaluation_end"], "M")
    for year in range(first.year, last.year + 1):
        origin = pd.Period(f"{year}-01", "M")
        training = data.loc[training_mask(data, origin)]
        evaluation = data[(data.origin >= max(first, origin)) & (data.origin <= min(last, origin + 11)) & data.target.notna()].copy()
        if evaluation.empty:
            continue
        y = training.target.map({label: i for i, label in enumerate(CLASSES)}).to_numpy()
        if set(y) != set(range(3)):
            raise ValueError(f"Training period before {origin} lacks an outcome class")
        counts = np.bincount(y, minlength=3)
        prior = (counts + 1.) / (len(y) + 3.)
        x_train, x_test, c_train, c_test, params = preprocess(training, evaluation)
        preprocessing.append(params.assign(refit_year=year))
        evaluation["refit_year"] = year
        evaluation["all_signals_observed"] = evaluation[list(FEATURES)].notna().all(axis=1)
        for i, label in enumerate(CLASSES):
            evaluation[f"historical_base_rate_{label}"] = prior[i]
        for name, train_x, test_x, feature_names in [
            ("coverage_only", c_train, c_test, [f"missing:{f}" for f in FEATURES]),
            ("base_rate_plus_press", x_train, x_test, list(FEATURES) + [f"missing:{f}" for f in FEATURES])]:
            model = LogisticRegression(C=spec["logistic_C"], solver=spec["logistic_solver"],
                                       max_iter=spec["logistic_max_iter"], random_state=spec["bootstrap_seed"])
            with warnings.catch_warnings():
                warnings.simplefilter("error", ConvergenceWarning)
                model.fit(train_x, y)
            probabilities = model.predict_proba(test_x)
            for index, code in enumerate(model.classes_):
                label = CLASSES[code]
                evaluation[f"{name}_{label}"] = probabilities[:, index]
                coefficients.append({"refit_year": year, "model": name, "class": label,
                                     "feature": "intercept", "coefficient": model.intercept_[index]})
                for feature, coefficient in zip(feature_names, model.coef_[index]):
                    coefficients.append({"refit_year": year, "model": name, "class": label,
                                         "feature": feature, "coefficient": coefficient})
        refits.append({"refit_year": year, "refit_origin": str(origin), "n_training_months": len(training),
                       "first_training_origin": str(training.origin.min()), "last_training_origin": str(training.origin.max()),
                       "latest_training_label_available": str(training.label_available.max()),
                       "purged_earlier_months": int(((data.origin < origin) & data.target.notna() & ~training_mask(data, origin)).sum()),
                       "n_evaluation_months": len(evaluation),
                       **{f"training_{label}": int(counts[i]) for i, label in enumerate(CLASSES)}})
        predictions.append(evaluation)
    return pd.concat(predictions, ignore_index=True), pd.DataFrame(refits), pd.DataFrame(coefficients), pd.concat(preprocessing, ignore_index=True)


def probabilities(data, model):
    p = data[[f"{model}_{label}" for label in CLASSES]].to_numpy(float)
    if not np.isfinite(p).all() or (p < 0).any() or not np.allclose(p.sum(axis=1), 1.):
        raise ValueError("Invalid forecast probabilities")
    return p


def losses(data, model):
    y = data.target.map({label: i for i, label in enumerate(CLASSES)}).to_numpy(int)
    p = probabilities(data, model)
    brier = ((p - np.eye(3)[y]) ** 2).sum(axis=1)
    logloss = -np.log(np.clip(p[np.arange(len(y)), y], 1e-15, 1.))
    return brier, logloss


def metrics(data, model):
    if data.empty:
        return {"n_months": 0}
    y = data.target.map({label: i for i, label in enumerate(CLASSES)}).to_numpy(int)
    p = probabilities(data, model)
    predicted = p.argmax(axis=1)
    brier, logloss = losses(data, model)
    fall = y == 0
    return {"n_months": len(y), "brier": brier.mean(), "log_loss": logloss.mean(),
            "accuracy": (predicted == y).mean(),
            "balanced_accuracy": np.mean([(predicted[y == c] == c).mean() for c in np.unique(y)]),
            "fall_auc": roc_auc_score(fall, p[:, 0]) if 0 < fall.sum() < len(y) else np.nan,
            "fall_ap": average_precision_score(fall, p[:, 0]) if fall.any() else np.nan,
            **{f"n_{label}": int((y == i).sum()) for i, label in enumerate(CLASSES)}}


def evaluation_tables(predictions, spec):
    rows = []
    groups = [("overall", "1950–2010", predictions),
              ("sensitivity", "Exclude 2007–2009 evaluation months", predictions[~predictions.origin.dt.year.between(2007, 2009)]),
              ("sensitivity", "All four press signals observed", predictions[predictions.all_signals_observed])]
    for start, end in spec["development_blocks"]:
        groups.append(("development_block", f"{start}–{end}", predictions[predictions.origin.dt.year.between(start, end)]))
    for period, span in [("decade", 10), ("five_year", 5)]:
        for start, group in predictions.groupby(predictions.origin.dt.year // span * span):
            groups.append((period, f"{start}–{min(start + span - 1, 2010)}", group))
    for kind, label, group in groups:
        for model in MODELS:
            rows.append({"grouping": kind, "period": label, "model": model, **metrics(group, model)})
    return pd.DataFrame(rows)


def paired_intervals(predictions, spec):
    rows = []
    for model, baseline in PAIRS:
        model_losses, baseline_losses = losses(predictions, model), losses(predictions, baseline)
        for metric, candidate, control in zip(("brier", "log_loss"), model_losses, baseline_losses):
            improvement = control - candidate
            for length in spec["block_lengths_years"]:
                codes = (predictions.origin.dt.year.to_numpy() - 1950) // length
                table = pd.DataFrame({"block": codes, "gain": improvement}).groupby("block").gain.agg(["sum", "count"])
                rng = np.random.default_rng(spec["bootstrap_seed"] + length)
                draws = rng.integers(0, len(table), (spec["bootstrap_draws"], len(table)))
                values = table["sum"].to_numpy()[draws].sum(axis=1) / table["count"].to_numpy()[draws].sum(axis=1)
                low, high = np.quantile(values, [.025, .975])
                rows.append({"model": model, "baseline": baseline, "metric": metric, "block_years": length,
                             "n_blocks": len(table), "improvement": improvement.mean(), "low": low, "high": high})
    return pd.DataFrame(rows)


def leave_blocks_out(predictions):
    rows = []
    for block in sorted((predictions.origin.dt.year // 5 * 5).unique()):
        sub = predictions[predictions.origin.dt.year // 5 * 5 != block]
        rows.append({"omitted_start": block, "omitted_end": min(block + 4, 2010), "n_months": len(sub),
                     "brier_improvement": (losses(sub, "historical_base_rate")[0] - losses(sub, "base_rate_plus_press")[0]).mean()})
    return pd.DataFrame(rows)


def calibration_table(predictions):
    rows = []
    for model in MODELS:
        for label in CLASSES:
            p = predictions[f"{model}_{label}"]
            bins = np.minimum((p * 10).astype(int), 9)
            for bucket, group in predictions.groupby(bins):
                rows.append({"model": model, "class": label, "bin": bucket, "n_months": len(group),
                             "mean_prediction": group[f"{model}_{label}"].mean(), "observed_share": group.target.eq(label).mean()})
    return pd.DataFrame(rows)


def save_figures(national, evaluated, predictions, calibration, out):
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
                         "axes.spines.top": False, "axes.spines.right": False})
    colors = {"historical_base_rate": "#718196", "coverage_only": "#c98b38", "base_rate_plus_press": "#087f83"}
    names = {"historical_base_rate": "Historical base rate", "coverage_only": "Coverage only", "base_rate_plus_press": "Base rate + press"}
    business = national[national.topic == "general_business"].copy()
    business["year"] = business.month.dt.year
    annual = business.groupby("year")[["net_direction", "disagreement", "n_papers"]].mean()
    fig, axes = plt.subplots(3, 1, figsize=(11, 7), sharex=True, constrained_layout=True)
    for ax, field, label in zip(axes, ["net_direction", "disagreement", "n_papers"],
                                ["Net direction", "Disagreement", "Observed papers"]):
        ax.plot(annual.index, annual[field], color="#087f83")
        ax.set_ylabel(label); ax.grid(alpha=.15)
    axes[0].axhline(0, color="#888", linewidth=.7)
    axes[0].set_title("National business forecasts: yearly means of monthly panels")
    axes[-1].set_xlabel("Print year · coverage is not newspaper attention")
    fig.savefig(out / "monthly_panel.png", dpi=160); plt.close(fig)
    fig, ax = plt.subplots(figsize=(10, 4.5))
    for model in MODELS:
        sub = evaluated[(evaluated.grouping == "decade") & (evaluated.model == model)]
        ax.plot(sub.period, sub.brier, marker="o", color=colors[model], label=names[model])
    ax.set(title="Six-month production direction: performance by forecast decade", ylabel="Multiclass Brier score (lower is better)")
    ax.legend(fontsize=9); ax.grid(alpha=.15); fig.tight_layout()
    fig.savefig(out / "decade_performance.png", dpi=160); plt.close(fig)
    table = evaluated[evaluated.grouping == "five_year"].pivot(index="period", columns="model", values="brier")
    gain = table.historical_base_rate - table.base_rate_plus_press
    fig, ax = plt.subplots(figsize=(11, 4.5))
    ax.bar(gain.index, gain, color=["#087f83" if x >= 0 else "#b6654a" for x in gain])
    ax.axhline(0, color="#444", linewidth=.8)
    ax.tick_params(axis="x", labelrotation=45)
    ax.set(title="Does the benefit persist across periods?", ylabel="Brier improvement over base rate\n(positive favors press signals)")
    fig.tight_layout(); fig.savefig(out / "five_year_improvement.png", dpi=160); plt.close(fig)
    fig, ax = plt.subplots(figsize=(6.5, 5.5))
    for model in MODELS:
        sub = calibration[(calibration.model == model) & (calibration["class"] == "fall")]
        ax.plot(sub.mean_prediction, sub.observed_share, "o-", color=colors[model], label=names[model])
    ax.plot([0, 1], [0, 1], "--", color="#aaa")
    ax.set(xlim=(0, 1), ylim=(0, 1), xlabel="Mean predicted probability", ylabel="Observed fraction falling",
           title="Calibration for a production fall greater than 2%")
    ax.legend(fontsize=9); fig.tight_layout(); fig.savefig(out / "calibration.png", dpi=160); plt.close(fig)


def make_report(tables, summary, out):
    def table(data):
        return '<div class="table">' + data.to_html(index=False, border=0, float_format=lambda x: f"{x:.4f}") + '</div>'
    def image(name):
        return f'<img alt="{name.replace("_", " ")}" src="data:image/png;base64,{base64.b64encode((out / name).read_bytes()).decode()}">'
    results = tables["metrics"]
    overall = results[results.grouping == "overall"].set_index("model")
    gain = overall.loc["historical_base_rate", "brier"] - overall.loc["base_rate_plus_press", "brier"]
    primary = tables["paired_intervals"].query("model == 'base_rate_plus_press' and baseline == 'historical_base_rate' and metric == 'brier' and block_years == 5").iloc[0]
    positive_blocks = summary["five_year_blocks_improved"]
    metrics_columns = ["period", "model", "n_months", "brier", "log_loss", "accuracy", "balanced_accuracy", "fall_auc", "fall_ap"]
    body = ["<h1>Do newspaper forecasts add economic information?</h1>",
            "<p class='subtitle'>Exploratory annual-refit evaluation · 1950–2010 · six-month industrial-production direction</p>",
            f"<p>Adding four newspaper signals changes the multiclass Brier score from "
            f"<strong>{overall.loc['historical_base_rate', 'brier']:.4f}</strong> to "
            f"<strong>{overall.loc['base_rate_plus_press', 'brier']:.4f}</strong>. "
            f"The improvement is <strong>{gain:+.4f}</strong> (positive is better), with a five-year-block interval of "
            f"<strong>{primary.low:+.4f} to {primary.high:+.4f}</strong>. "
            f"The press model improves on the base rate in <strong>{positive_blocks} of {summary['five_year_blocks']}</strong> five-year evaluation blocks.</p>",
            "<p>This tests future economic direction, rather than whether individual claims are correct. "
            "A base-rate comparison does not establish added value beyond an economic model using historically available macro data. "
            "All results are exploratory: this historical corpus has already informed earlier analyses.</p>",
            "<h2>1. A reusable monthly newspaper panel</h2>",
            f"<p>The panel contains {summary['panel_counts']['panel_claims']:,} readable national claims across four supported topics, "
            f"including claims whose horizons or eventual outcomes cannot be scored. The existing verified export has "
            f"{summary['panel_counts']['claims']:,} claims in total. "
            "Every article receives equal weight within its newspaper/topic/month; observed newspapers then receive equal weight. "
            "Identical stripped rows are retained. Empty newspaper-months have zero coverage and missing signal values, not artificial neutral forecasts.</p>",
            image("monthly_panel.png"),
            "<p>The paper panel includes positive, negative and flat shares, net direction, disagreement, one-month changes, and claim/article coverage. "
            "Positive means improving business/markets/employment; for prices it means rising prices, not good news. "
            "Disagreement is normalized three-category Gini impurity. Cross-paper dispersion is the population standard deviation of paper net directions. "
            "The model uses business forecasts only. Counts describe these exports, never overall press attention.</p>",
            "<h2>2. Outcome and information timing</h2>",
            "<p>A forecast is issued at the start of month t, using completed print months only. Its target is the change in monthly-average "
            "industrial production from t−1 to t+5: six monthly-index intervals. Changes above +2% are rises, below −2% are falls, and the rest "
            "are flat, including the threshold boundaries. This is a broad business proxy, not literal recession-onset prediction. "
            "The starting industrial-production value need not have been released at issuance; it is used only for retrospective outcome scoring.</p>",
            "<p>Training outcomes begin with forecast origin February 1919. Each January from 1950 through 2010, models refit on an expanding "
            "history, retaining only labels whose endpoint plus a three-month release allowance is strictly before that January. "
            "The fitted model then predicts the next 12 months as newspaper context arrives. No tuning uses evaluation outcomes. "
            "The economic series is a revised snapshot: the release allowance prevents obvious overlap, but cannot establish genuine historical "
            "vintage availability. This is a retrospective experiment using publication-dated press features.</p>",
            "<h2>3. Same months, three simple models</h2>",
            table(results[results.grouping == "overall"][metrics_columns]),
            "<p><strong>Historical base rate:</strong> earlier mature class frequencies with one pseudo-observation per class. "
            "<strong>Coverage only:</strong> multinomial ridge logistic regression using four feature-missingness flags. "
            "<strong>Base rate + press:</strong> multinomial ridge logistic regression with fitted class intercepts, the four press signals and "
            "the same missingness flags. The regression intercepts are fitted jointly with predictors rather than fixed to the smoothed base rate. "
            "Both regressions use C=1 with no parameter search; imputation medians and scaling are fitted on training months only.</p>",
            "<p>The four signals are prior-three-month net direction, its change versus the preceding three months among common papers, "
            "prior-three-month disagreement, and cross-paper dispersion. Signal windows require at least two observed months, two newspapers, "
            "and five articles. Direction changes require two common papers and adequate coverage in both windows. All outcome months remain "
            "in the primary evaluation; missing signals are imputed with training medians and flagged. Counts and newspaper identities are not predictors.</p>",
            f"<p>There are <strong>{len(tables['predictions']):,} evaluation months</strong>, one forecast per month, not a separate independent "
            "outcome per claim. Brier score sums squared probability errors across three classes (0–2, lower is better); log loss is also lower-is-better. "
            "Accuracy is the argmax class hit rate; balanced accuracy averages recalls over classes present in the evaluation subset. "
            "Fall AUC/AP use the predicted probability of a greater-than-2% fall.</p>",
            image("calibration.png"),
            "<h2>4. Stability across eras and crises</h2>",
            table(results[results.grouping == "development_block"][metrics_columns]),
            image("decade_performance.png"), image("five_year_improvement.png"),
            table(results[results.grouping == "sensitivity"][metrics_columns]),
            f"<p>Leaving each five-year block out of evaluation gives Brier improvements ranging from "
            f"{tables['leave_block_out'].brier_improvement.min():+.4f} to {tables['leave_block_out'].brier_improvement.max():+.4f}. "
            "The crisis check excludes 2007–2009 forecast origins from scoring. It does not refit models or erase that episode from later training. "
            "The complete-signal check likewise changes evaluation support, not fitted models. The 2010 block contains just one year.</p>",
            "<h2>Paired uncertainty and limits</h2>",
            table(tables["paired_intervals"].query("block_years == 5")),
            "<p>Intervals jointly resample forecast-year blocks across all models, preserving within-block overlapping targets. "
            "Two-, five-, and ten-year lengths, 2,000 draws each, are exported. They condition on fitted forecasts and describe historical variation; "
            "they are not fresh-holdout confirmation or complete uncertainty about model fitting, extraction errors, and query selection. "
            "Secondary comparisons are not adjusted for multiple testing.</p>",
            "<p>The selected downturn/recovery query, changing publication mix, machine label errors, stripped quotations, and broad production proxy "
            "limit interpretation. Equal-paper weights and common-paper changes reduce some composition effects but do not reconstruct missing articles. "
            "Printed content is the intended information source, but retrospective machine extraction can itself carry hindsight errors. "
            "No macro values, economic outcomes, recession labels, verifier prose, speaker identities, or retrospective annotations are model features. "
            "LOC and old crisis-window exports are excluded.</p>",
            "<h2>Reproduce and inspect</h2>",
            "<p><code>python src/proquest_information.py</code> uses the saved <code>evaluation_spec.json</code>. "
            "Dependencies are in <code>requirements-proquest-information.txt</code>. "
            "The output folder includes article and newspaper/topic/month panels, national monthly panels, "
            "all forecast features and outcomes, annual refit audits, preprocessing, model coefficients, monthly probabilities, "
            "losses, calibration, metrics and stability tables. Source/reference/code/specification hashes and versions are in <code>summary.json</code>. "
            "All source exports remain unchanged.</p>"]
    head = """<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>ProQuest monthly economic information</title><style>
body{font:16px/1.6 system-ui,sans-serif;color:#19313c;background:#f7f8fa;max-width:1120px;margin:40px auto;padding:0 24px 60px}
h1{font-size:34px;line-height:1.2}h2{margin-top:42px}.subtitle{color:#536874}img{width:100%;background:white;border-radius:8px;margin:16px 0}
.table{overflow-x:auto;background:white;border:1px solid #dce3e8;border-radius:8px}table{border-collapse:collapse;font-size:13px;width:100%}
td,th{padding:9px 12px;text-align:right;white-space:nowrap;border-bottom:1px solid #e5e9ed}th{background:#e8f1f0}td:first-child,th:first-child{text-align:left}
code{background:#e8edf0;padding:2px 4px}</style><main>"""
    (out / "report.html").write_text(head + "\n".join(body) + "</main></html>", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-only", action="store_true", help="Export the panel, features, and specification provenance without fitting")
    args = parser.parse_args()
    spec, spec_hash = load_spec()
    OUT.mkdir(parents=True, exist_ok=True)
    print("Building print-time panels from verified annual exports...", flush=True)
    claims, counts, source_hashes = read_claims()
    article, paper, national = build_panels(claims)
    origins = pd.period_range(spec["training_origins_start"], spec["evaluation_end"], freq="M")
    features = forecast_features(paper, national, origins)
    for name, frame in [("article_topic_month", article), ("newspaper_topic_month", paper), ("national_topic_month", national)]:
        frame.to_csv(OUT / f"{name}.csv.gz", index=False, compression={"method": "gzip", "mtime": 0})
    features.to_csv(OUT / "forecast_features.csv", index=False)
    (OUT / "panel_manifest.json").write_text(json.dumps({"spec_sha256": spec_hash, "counts": counts, "sources": source_hashes}, indent=2) + "\n")
    if args.build_only:
        print("Panel and print-time features saved; no outcomes loaded or models fitted.")
        return
    production, reference = read_production()
    data = features.merge(targets(origins, production, spec), on="origin", validate="one_to_one")
    data.to_csv(OUT / "forecast_dataset.csv", index=False)
    print("Fitting 61 annual expanding-window origins with matured labels...", flush=True)
    predicted, refits, coefficients, preprocessing = fit_forward(data, spec)
    for model in MODELS:
        predicted[f"{model}_brier"], predicted[f"{model}_log_loss"] = losses(predicted, model)
    evaluated = evaluation_tables(predicted, spec)
    intervals = paired_intervals(predicted, spec)
    calibration = calibration_table(predicted)
    tables = {"predictions": predicted, "annual_refits": refits, "coefficients": coefficients,
              "preprocessing": preprocessing, "metrics": evaluated, "paired_intervals": intervals,
              "leave_block_out": leave_blocks_out(predicted), "calibration": calibration}
    for name, frame in tables.items():
        frame.to_csv(OUT / f"{name}.csv", index=False)
    five = evaluated[evaluated.grouping == "five_year"].pivot(index="period", columns="model", values="brier")
    code = [Path("src") / name for name in ("proquest_information.py", "proquest_panel.py", "proquest_descriptive.py", "analyze_proquest.py", "score_predictions.py")]
    summary = {"spec_sha256": spec_hash, "panel_counts": counts, "sources": source_hashes, "reference": reference,
               "code_sha256": {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in code},
               "versions": {"python": platform.python_version(), **{name: version(name) for name in ("numpy", "pandas", "matplotlib", "scikit-learn")}},
               "n_evaluation_months": len(predicted), "n_refits": len(refits),
               "complete_signal_evaluation_months": int(predicted.all_signals_observed.sum()),
               "five_year_blocks": len(five), "five_year_blocks_improved": int((five.base_rate_plus_press < five.historical_base_rate).sum()),
               "target_exclusions": int(data.target.isna().sum()),
               "overall_metrics": evaluated[evaluated.grouping == "overall"].to_dict("records")}
    save_figures(national, evaluated, predicted, calibration, OUT)
    make_report(tables, summary, OUT)
    for path, digest in {**source_hashes, reference["file"]: reference["sha256"], str(SPEC_PATH): spec_hash}.items():
        if hashlib.sha256(Path(path).read_bytes()).hexdigest() != digest:
            raise ValueError(f"Input or specification changed during the run: {path}")
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n")
    print(evaluated[evaluated.grouping.isin(["overall", "sensitivity"])].to_string(index=False))
    print(intervals.query("metric == 'brier' and block_years == 5").to_string(index=False))
    print(f"Report: {OUT / 'report.html'}")


if __name__ == "__main__":
    main()
