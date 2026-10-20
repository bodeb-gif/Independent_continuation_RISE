"""Controlled polarization extensions of every active ProQuest predictive family.

Existing model modules and outputs are read, never overwritten. Saved macro
training rows preserve historical label vintages and training-only selection.
"""
import argparse
import json
from pathlib import Path
import platform
import time
import warnings

import joblib
import numpy as np
import pandas as pd
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from proquest_information import CLASSES, preprocess, training_mask
from proquest_macro_information import standardize
from proquest_panel import FEATURES as PRESS
from proquest_polarization import FEATURES, OUT, digest, load_features
from proquest_vintages import CORE_FEATURES, CPI_FEATURES

BASE = Path("data/scored/proquest")
ARMS = {"baseline": (), "political": FEATURES[:1], "forecast": FEATURES[1:], "both": FEATURES}
TRACKED = {}


def read(path):
    path = Path(path)
    TRACKED[str(path)] = digest(path)
    if path.suffix == ".json":
        return json.loads(path.read_text())
    frame = pd.read_csv(path)
    if "origin" in frame:
        frame["origin"] = pd.PeriodIndex(frame.origin, freq="M")
    if "label_available" in frame:
        frame["label_available"] = pd.PeriodIndex(frame.label_available, freq="M")
    return frame


def added_inputs(training, evaluation, names):
    """No evaluation-dependent imputation or scaling, including missing columns."""
    if not names:
        return np.empty((len(training), 0)), np.empty((len(evaluation), 0)), pd.DataFrame()
    train, test = training[list(names)].astype(float), evaluation[list(names)].astype(float)
    if np.isinf(train.to_numpy()).any() or np.isinf(test.to_numpy()).any():
        raise ValueError("Infinite polarization feature")
    medians = train.median().fillna(0.)
    scaler = StandardScaler().fit(train.fillna(medians))
    a = np.column_stack([scaler.transform(train.fillna(medians)), train.isna().astype(float)])
    b = np.column_stack([scaler.transform(test.fillna(medians)), test.isna().astype(float)])
    params = pd.DataFrame({"feature": names, "median": medians.to_numpy(),
                           "mean": scaler.mean_, "scale": scaler.scale_})
    return a, b, params


def model_fit(train_x, test_x, y, c, maximum=2000, weights=None):
    model = LogisticRegression(C=c, solver="lbfgs", max_iter=maximum, random_state=20261014)
    with warnings.catch_warnings():
        warnings.simplefilter("error", ConvergenceWarning)
        model.fit(train_x, y, sample_weight=weights)
    return model, model.predict_proba(test_x)


def observation_losses(y, p):
    if p.ndim == 1:
        return (p - y) ** 2, -(y * np.log(np.clip(p, 1e-15, 1)) + (1-y) * np.log(np.clip(1-p, 1e-15, 1)))
    return ((p - np.eye(3)[y]) ** 2).sum(axis=1), -np.log(np.clip(p[np.arange(len(y)), y], 1e-15, 1))


def performance(y, p, weights=None):
    loss, logloss = observation_losses(y, p)
    binary = p.ndim == 1
    pred = (p >= .5).astype(int) if binary else p.argmax(axis=1)
    positive = y if binary else (y == 0)
    score = p if binary else p[:, 0]
    return {"n": len(y), "brier": np.average(loss, weights=weights),
            "log_loss": np.average(logloss, weights=weights),
            "accuracy": np.average(pred == y, weights=weights),
            "auc": roc_auc_score(positive, score, sample_weight=weights) if len(np.unique(positive)) == 2 else np.nan,
            "average_precision": average_precision_score(positive, score, sample_weight=weights) if positive.sum() else np.nan}


def paired_interval(years, improvements, weights=None, draws=2000):
    """Resample time-block sums; weights stay paired across both models."""
    years = np.asarray(years, dtype=int)
    weights = np.ones(len(years)) if weights is None else np.asarray(weights)
    blocks = (years - years.min()) // 5
    unique = np.unique(blocks)
    sums = np.array([(improvements[blocks == b] * weights[blocks == b]).sum() for b in unique])
    mass = np.array([weights[blocks == b].sum() for b in unique])
    picks = np.random.default_rng(20261014).integers(0, len(unique), size=(draws, len(unique)))
    values = sums[picks].sum(axis=1) / mass[picks].sum(axis=1)
    return {"improvement": sums.sum() / mass.sum(), "low": np.quantile(values, .025),
            "high": np.quantile(values, .975), "n_blocks": len(unique), "block_years": 5}


def summarize(family, model, y, predictions, years, weights=None):
    results, intervals, calibration = [], [], []
    for arm, p in predictions.items():
        for scope, mask in [("overall", np.ones(len(y), dtype=bool)),
                            ("exclude_2007_2009", ~np.isin(years, [2007, 2008, 2009]))]:
            w = None if weights is None else weights[mask]
            results.append({"family": family, "model": model, "arm": arm, "scope": scope,
                            **performance(y[mask], p[mask], w)})
        if arm != "baseline":
            base_b, base_l = observation_losses(y, predictions["baseline"])
            aug_b, aug_l = observation_losses(y, p)
            for metric, delta in [("brier", base_b - aug_b), ("log_loss", base_l - aug_l)]:
                intervals.append({"family": family, "model": model, "arm": arm, "metric": metric,
                                  **paired_interval(years, delta, weights)})
        probs = p[:, None] if p.ndim == 1 else p
        for column in range(probs.shape[1]):
            truth = y if p.ndim == 1 else (y == column).astype(int)
            for bucket in range(10):
                mask = np.minimum((probs[:, column] * 10).astype(int), 9) == bucket
                if mask.any():
                    w = None if weights is None else weights[mask]
                    calibration.append({"family": family, "model": model, "arm": arm,
                                        "class": "correct" if p.ndim == 1 else CLASSES[column],
                                        "bin": bucket, "n": int(mask.sum()),
                                        "mean_probability": np.average(probs[mask, column], weights=w),
                                        "observed_rate": np.average(truth[mask], weights=w)})
    return results, intervals, calibration


def run_monthly(extra):
    all_metrics, all_intervals, all_calibration, audits = [], [], [], []
    destination = OUT / "monthly"
    destination.mkdir(exist_ok=True)
    for family in ["monthly_information", "macro_information/core", "macro_information/with_cpi",
                   "macro_benchmark/core", "macro_benchmark/with_cpi"]:
        selected = family.startswith("macro_benchmark")
        basic = family == "monthly_information"
        path = BASE / family
        spec = read(path.parent / "evaluation_spec.json" if not basic else path / "evaluation_spec.json")
        data_path = BASE / ("monthly_information" if basic else "macro_information") / "forecast_dataset.csv"
        data = read(data_path).merge(extra[["origin"] + list(FEATURES)], on="origin", how="left", validate="one_to_one")
        previous = read(path / "predictions.csv")
        config = None
        if not basic:
            labels = read(path / ("selected_training_rows.csv" if selected else "training_label_audit.csv"))
            if not selected:
                labels = labels[labels.used]
            else:
                config = read(path / "annual_refits.csv").set_index("refit_year")
        chunks, coefficients, parameters, training_audit = [], [], [], []
        models = ["coverage_only", "base_rate_plus_press"] if basic else ["macro_only", "macro_plus_press"]
        for year in sorted(previous.refit_year.unique()):
            old = previous[previous.refit_year.eq(year)].sort_values("origin")
            evaluation = data[data.origin.isin(old.origin)].sort_values("origin").copy()
            if evaluation.origin.tolist() != old.origin.tolist() or evaluation.target.tolist() != old.target.tolist():
                raise ValueError("Evaluation support/target changed")
            if basic:
                training = data[training_mask(data, pd.Period(f"{year}-01", "M"))].copy()
                training["training_target"] = training.target
                c = spec["logistic_C"]
            else:
                chosen = labels[labels.refit_year.eq(year)]
                training = data.drop(columns=["target"]).merge(chosen[["origin", "training_target"]], on="origin", validate="one_to_one").sort_values("origin")
                if len(training) != len(chosen):
                    raise ValueError("Training-row join dropped saved vintage labels")
                c = float(config.loc[year, "C"]) if selected else spec["logistic_C"]
            y = training.training_target.map({label: i for i, label in enumerate(CLASSES)}).to_numpy(int)
            training_audit.append(training[["origin", "training_target"]].assign(refit_year=year))
            result = evaluation[["origin", "target"]].copy()
            result["refit_year"] = year
            for control in (["historical_base_rate"] if basic else ["recent_base_rate"]):
                for label in CLASSES:
                    result[f"{control}_{label}"] = old[f"{control}_{label}"].to_numpy()
            for model_name in models:
                if basic:
                    a, b, ma, mb, _ = preprocess(training, evaluation)
                    if model_name == "coverage_only":
                        a, b = ma, mb
                        base_names = [f"missing:{f}" for f in PRESS]
                    else:
                        base_names = list(PRESS) + [f"missing:{f}" for f in PRESS]
                else:
                    if selected:
                        base_names = list(spec["macro_feature_sets"][config.loc[year, "feature_set"]])
                        if family.endswith("with_cpi"):
                            base_names.append(spec["additional_cpi_feature"])
                    else:
                        base_names = list(CORE_FEATURES + (CPI_FEATURES if family.endswith("with_cpi") else ()))
                    if model_name == "macro_plus_press":
                        base_names += list(PRESS)
                    a, b, _ = standardize(training, evaluation, base_names)
                for arm, names in ARMS.items():
                    at, bt, params = added_inputs(training, evaluation, names)
                    fit, p = model_fit(np.column_stack([a, at]), np.column_stack([b, bt]), y, c)
                    if arm == "baseline":
                        expected = old[[f"{model_name}_{label}" for label in CLASSES]].to_numpy()
                        error = float(np.max(np.abs(p - expected)))
                        if error > 1e-6:
                            raise ValueError(f"Baseline failed reproduction: {family} {model_name} {year}: {error}")
                        audits.append({"family": family, "model": model_name, "year": int(year),
                                       "n_training": len(training), "n_evaluation": len(evaluation), "max_probability_error": error})
                    if len(params):
                        parameters.append(params.assign(refit_year=year, model=model_name, arm=arm))
                    feature_names = base_names + list(names) + [f"missing:{f}" for f in names]
                    for i, label in enumerate(CLASSES):
                        result[f"{model_name}__{arm}__{label}"] = p[:, i]
                        coefficients.extend({"refit_year": int(year), "model": model_name, "arm": arm,
                                             "class": label, "feature": name, "coefficient": float(value)}
                                            for name, value in zip(["intercept"] + feature_names, np.r_[fit.intercept_[i], fit.coef_[i]]))
            chunks.append(result)
        predicted = pd.concat(chunks, ignore_index=True)
        y = predicted.target.map({label: i for i, label in enumerate(CLASSES)}).to_numpy(int)
        for model_name in models:
            probs = {arm: predicted[[f"{model_name}__{arm}__{label}" for label in CLASSES]].to_numpy() for arm in ARMS}
            m, ci, cal = summarize(family, model_name, y, probs, predicted.origin.dt.year.to_numpy())
            all_metrics += m; all_intervals += ci; all_calibration += cal
        dest = destination / family.replace("/", "_")
        dest.mkdir(exist_ok=True)
        predicted.to_csv(dest / "predictions.csv", index=False)
        pd.DataFrame(coefficients).to_csv(dest / "coefficients.csv", index=False)
        pd.concat(parameters, ignore_index=True).to_csv(dest / "added_preprocessing.csv", index=False)
        pd.concat(training_audit, ignore_index=True).to_csv(dest / "training_rows.csv", index=False)
        print(f"Completed four arms: {family}", flush=True)
    pd.DataFrame(audits).to_csv(destination / "baseline_reproduction.csv", index=False)
    return all_metrics, all_intervals, all_calibration


def run_claims(extra, maximum_epochs=20):
    import torch
    import proquest_rnn as rnn
    from proquest_followups import load_claims
    torch.set_num_threads(2)
    torch.use_deterministic_algorithms(True)
    claims, metadata, sources = load_claims()
    TRACKED.update(sources)
    scored = claims[claims.scorable & claims.basis.ne("NBER proxy")].copy().reset_index(drop=True)
    masks, availability, excluded = rnn.chronological_splits(scored)
    extra_index = extra.set_index("origin")
    values = extra_index.reindex(pd.PeriodIndex(scored.month, freq="M"))[list(FEATURES)].reset_index(drop=True)
    context_frame = rnn.monthly_context(claims)
    context_scaler = StandardScaler().fit(context_frame.loc[context_frame.index < pd.Period("1985-01", "M")])
    context_array = context_scaler.transform(context_frame).astype("float32")[rnn.sequence_indices(scored.month, context_frame.index)]
    encoder = OneHotEncoder(handle_unknown="ignore", sparse_output=False, dtype=np.float32)
    categories = scored[rnn.CLAIM_CATEGORIES].fillna("missing")
    encoder.fit(categories.loc[masks["train"]])
    horizon_scaler = StandardScaler().fit(scored.loc[masks["train"], ["horizon_used"]])
    original = np.column_stack([encoder.transform(categories), horizon_scaler.transform(scored[["horizon_used"]])]).astype("float32")
    y_array = scored.hit.to_numpy(dtype="float32")
    weights_array = np.ones(len(scored), dtype="float32")
    for mask in masks.values():
        weights_array[mask] = rnn.article_weights(scored.loc[mask])
    destination = OUT / "claims"
    destination.mkdir(exist_ok=True)
    test = scored.loc[masks["test"]].copy()
    output = test[["record_id", "page_id", "date", "year", "hit"]].copy()
    old = read(BASE / "rnn/test_predictions.csv.gz")
    if test.record_id.tolist() != old.record_id.tolist():
        raise ValueError("RNN evaluation support changed")
    histories, fitted, preprocessing, audits = [], {}, [], []
    context = torch.from_numpy(context_array)
    y, weights = torch.from_numpy(y_array), torch.from_numpy(weights_array)
    for arm, names in ARMS.items():
        _, added, params = added_inputs(values.loc[masks["train"]], values, names)
        claim_array = np.column_stack([original, added]).astype("float32")
        claim = torch.from_numpy(claim_array)
        if len(params):
            preprocessing.append(params.assign(arm=arm))
        for name in ["logistic_metadata", "logistic_metadata_history"]:
            x = claim_array if name == "logistic_metadata" else np.column_stack([claim_array, context_array.reshape(len(scored), -1)])
            model, p = model_fit(x[masks["train"]], x[masks["test"]], y_array[masks["train"]],
                                c=1., maximum=1500, weights=weights_array[masks["train"]])
            output[f"{name}__{arm}"] = p[:, 1]
            fitted[f"{name}__{arm}"] = model
            if arm == "baseline":
                error = float(np.max(np.abs(p[:, 1] - old[name])))
                if error > 1e-5:
                    raise ValueError(f"Claim baseline mismatch: {name} {error}")
                audits.append({"model": name, "max_probability_error": error})
            del x
        seed_predictions = []
        for seed in [11, 29, 47]:
            model, history, best = rnn.train_gru(context, claim, y, weights, masks, seed, epochs=maximum_epochs)
            histories.extend({"arm": arm, **row} for row in history)
            prediction = rnn.neural_probabilities(model, context[masks["test"]], claim[masks["test"]])
            seed_predictions.append(prediction)
            output[f"gru_seed_{seed}__{arm}"] = prediction
            torch.save({"state_dict": model.state_dict(), "context_size": context.shape[-1],
                        "claim_size": claim.shape[-1], "hidden_size": 24, "seed": seed,
                        "best_epoch": best, "arm": arm, "added_features": names}, destination / f"gru_{arm}_{seed}.pt")
        output[f"gru_ensemble__{arm}"] = np.mean(seed_predictions, axis=0)
        output.to_csv(destination / "test_predictions.csv.gz", index=False, compression={"method": "gzip", "mtime": 0})
        print(f"Completed claim arm: {arm}", flush=True)
    metrics, intervals, calibration = [], [], []
    for name in ["logistic_metadata", "logistic_metadata_history", "gru_ensemble"]:
        predictions = {arm: output[f"{name}__{arm}"].to_numpy() for arm in ARMS}
        m, ci, cal = summarize("claim_correctness", name, test.hit.to_numpy(int), predictions,
                               test.year.to_numpy(), rnn.article_weights(test))
        metrics += m; intervals += ci; calibration += cal
    pd.DataFrame(histories).to_csv(destination / "training_history.csv", index=False)
    pd.concat(preprocessing, ignore_index=True).to_csv(destination / "added_preprocessing.csv", index=False)
    pd.DataFrame(audits).to_csv(destination / "baseline_reproduction.csv", index=False)
    splits = scored[["record_id", "page_id", "date"]].copy()
    splits["split"] = "purged"
    for name, mask in masks.items():
        splits.loc[mask, "split"] = name
    splits["label_available"] = availability
    splits.to_csv(destination / "split_assignments.csv.gz", index=False, compression={"method": "gzip", "mtime": 0})
    joblib.dump({"encoder": encoder, "horizon_scaler": horizon_scaler, "context_scaler": context_scaler,
                 "added_preprocessing": pd.concat(preprocessing, ignore_index=True), "logistic_models": fitted,
                 "context_features": list(context_frame.columns), "claim_categories": rnn.CLAIM_CATEGORIES},
                destination / "preprocessing_and_baselines.joblib")
    return metrics, intervals, calibration


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", choices=["monthly", "claims"], required=True)
    args = parser.parse_args()
    start = time.monotonic()
    extra, manifest = load_features()
    TRACKED.update(manifest["inputs_sha256"])
    for name in ["evaluation_spec.json", "features.csv", "feature_manifest.json"]:
        TRACKED[str(OUT / name)] = digest(OUT / name)
    # Protect existing evidence and code; all new outputs live in polarization/.
    for directory in ["rnn", "monthly_information", "macro_information", "macro_benchmark"]:
        summary = read(BASE / directory / "summary.json")
        for key in ["inputs_sha256", "sources", "verified_source_sha256"]:
            TRACKED.update(summary.get(key, {}))
    for path in Path("src").glob("proquest*.py"):
        TRACKED[str(path)] = digest(path)
    for path, expected in TRACKED.items():
        if digest(path) != expected:
            raise ValueError(f"Changed input: {path}")
    result = run_monthly(extra) if args.task == "monthly" else run_claims(extra)
    for name, rows in zip(["metrics", "paired_intervals", "calibration"], result):
        pd.DataFrame(rows).to_csv(OUT / f"{args.task}_{name}.csv", index=False)
    for path, expected in TRACKED.items():
        if digest(path) != expected:
            raise ValueError(f"Input changed during run: {path}")
    summary = {"task": args.task, "status": "exploratory", "seconds": time.monotonic()-start,
               "inputs_sha256": TRACKED, "python": platform.python_version(),
               "versions": {name: __import__(name).__version__ for name in ["numpy", "pandas", "sklearn"]},
               "arms": ARMS, "metrics": result[0]}
    if args.task == "claims":
        import torch
        summary["versions"]["torch"] = torch.__version__
    (OUT / f"{args.task}_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(pd.DataFrame(result[0]).query("scope == 'overall'").to_string(index=False), flush=True)


if __name__ == "__main__":
    main()
