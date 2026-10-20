# Reusing and retraining the ProQuest RNN

The runner accepts explicit input files, time splits, model bundles, and output folders. Use `predict` to apply saved models without outcomes or fitting. Use `train` to create a new fitted version with training-only preprocessing and validation-only epoch selection. Both support baseline, political-only, forecast-only, and combined inputs, with the two logistic controls alongside each GRU ensemble.

Modern evaluation is deferred at the author's request on October 19, 2026. The active corpus remains 1900–2010. The runner's future-year flag prepares a later explicitly configured run; no modern predictions or fits have been made.

The [data handoff](PROQUEST_DATA_HANDOFF.md) now includes annual-export normalization, optional mature-outcome scoring, and explicit-calendar polarization preparation. The [reproducibility guide](PROQUEST_REPRODUCIBILITY.md) records the locked environment, results inventory, and isolated rebuild.

## Environment

Use a working environment, not the broken repository `.venv`. The current checked environment is `/tmp/bode-econ-audit-20261019/bin/python`. From the repository root, a fresh environment can install `requirements-proquest-rnn.txt`. The saved models were built with PyTorch 2.14.0 and scikit-learn 1.9.1; the runner reproduces their predictions exactly using those versions. Preserve package versions and model files for exact replication. Python/scientific-library versions, input hashes, and code hashes are recorded with each run.

## Apply the current saved models

```bash
python src/proquest_rnn_runner.py predict \
  --claims data/scored/proquest/descriptive/scored_claims.csv.gz \
  --features data/scored/proquest/polarization/features.csv \
  --bundle data/scored/proquest/polarization/claims \
  --start 1995-01 --through 2010-12 \
  --out data/scored/proquest/rnn_runs/predictions_v1
```

This writes prediction probabilities and a run manifest in a new directory. Outcome columns are not read, even if present in the input. All four configurations and all saved seeds are used by default. `--arms baseline` applies only the baseline and does not require `--features`.

The historical reproduction produced exactly the same 56,807 rows and probabilities as the saved polarization run, including both logistic controls and all twelve GRU checkpoints. The [reproduction check](../data/scored/proquest/rnn_runner_check_v2/reproduction.json) records the comparison.

## Retrain a new version

```bash
python src/proquest_rnn_runner.py train \
  --claims data/scored/proquest/descriptive/scored_claims.csv.gz \
  --features data/scored/proquest/polarization/features.csv \
  --validation-start 1985-01 --test-start 1995-01 --through 2010-12 \
  --as-of 2026-10-19 --seeds 11 29 47 --epochs 20 \
  --out data/scored/proquest/rnn_runs/refit_v1
```

This is an explicit retraining command, not a prerequisite for prediction. It preserves the current model's structure, article weighting, logistic settings, three-month label allowance, and validation stopping rule. It saves checkpoints, preprocessing, logistic controls, split assignments, training histories, test predictions, metrics, and a hashed bundle manifest. Subsequent prediction can use the new folder as `--bundle`.

Training labels must come from deterministic scoring with documented references. Rows with nonbinary outcomes fail rather than being filled. The runner excludes endpoints whose horizon plus three-month allowance has not matured before `--as-of`; this calendar guard does not establish reference-series availability. Missing reference observations must remain unscorable upstream. The context scaler fits months before validation; category encoding, horizon scaling, added-feature imputation/scaling, and logistic models fit only the purged training rows. Validation selects epochs; test results never select seeds or settings.

The new training path was exercised on synthetic data with all four arms and one epoch/seed, then reloaded to reproduce its test predictions. A subsequent [forward-time development study](publication/RNN_DEVELOPMENT.md) fitted provisional historical candidates under a separate specification, without re-evaluating 1995–2010. Avoid using the historical test scores to choose new hyperparameters; record a separate development/evaluation plan for any substantive retraining study.

## Selected development configuration

The development study selected an 8-unit GRU, dropout 0.15, weight decay 0.001, and a 20-year fitting window. It improved both later historical confirmation blocks but remains provisional; those years have prior project exposure. The existing primary models remain frozen. To reproduce saved candidate probabilities on its stopping-period inputs:

```bash
python src/proquest_rnn_runner.py predict \
  --claims data/scored/proquest/descriptive/scored_claims.csv.gz \
  --bundle data/scored/proquest/rnn_development_v1/bundles/gru8_standard_20 \
  --arms baseline --start 1990-01 --through 1994-12 \
  --out data/scored/proquest/rnn_runs/development_candidate_predictions_v1
```

This is a reload check, not independent evaluation. The saved ensemble probabilities reproduced exactly for all 24,756 eligible stopping rows; the largest single-seed difference after CSV serialization was 1e-8. See the [reproduction record](../data/scored/proquest/rnn_development_v1_reload_check/reproduction.json).

For a separately planned retraining run, add this argument to `train`:

```text
--configuration data/scored/proquest/rnn_development_v1/bundles/gru8_standard_20/bundle_manifest.json
```

The runner reads the settings directly, hashes their source, and restricts fitting dates to the 20 years preceding `--validation-start`, with the usual label-maturity purge. Context scaling uses that fitting window; the input file should retain earlier history needed for twelve-month context. The same window applies to logistic controls. Epoch selection still uses only validation. Omitting `--configuration` retains the original 24-unit expanding-history defaults. A standalone JSON object with `hidden`, `dropout`, `weight_decay`, and `window_years` is also accepted; `null` means expanding history.

New data therefore require updated prepared inputs, explicit dates, and a new output directory, without source-code changes. The selected bundle currently contains only the baseline feature arm, so use `--arms baseline` for its predictions. Configuration-based training supports the four existing arms when the required feature file is supplied; no new polarization comparison was performed in this development experiment.

The [age-weighting follow-up](publication/RNN_DEVELOPMENT.md#gradual-age-weighting-follow-up) did not pass its improvement rule, so the current candidate is unchanged. For future experiments, configuration JSON may also include `"half_life_years": 20` (any finite positive number). This multiplies training article weights by exponential age decay measured from `--validation-start`, and normalizes training weights to mean one. It applies to the GRU and both logistic controls; validation and test weights, feature scaling, and the existing date-window setting are unchanged. Omit the key to disable decay. The setting and its source hash are retained in new bundles/run manifests; prediction uses saved checkpoints without applying further age weights.

## Input contract for new data

`--claims` is a prepared label CSV or `.csv.gz`, not an untouched annual JSONL export. Keep every relevant context claim, including claims without scoreable outcomes, and supply at least twelve months before the requested prediction start. Use the same normalization functions in `proquest_descriptive.py` for newspaper family, direction, and horizon. The existing descriptive score table already satisfies this contract.

| Columns | Meaning |
| --- | --- |
| `record_id`, `page_id`, `date` | Unique source-local claim address, article identifier, ISO publication date |
| `scope`, `topic`, `paper` | Print-time scope, topic, normalized newspaper family |
| `voice`, `confidence`, `predicted_norm` | Machine labels available from the printed claim |
| `horizon_basis`, `horizon_used` | Resolved horizon category and numeric months |
| `hit`, `scorable`, `basis` | Required only for training; deterministic outcome, eligibility boolean, reference basis |

Do not deduplicate identical stripped labels. Preserve unique record addresses tied to a source-file manifest. The runner rejects duplicate addresses and article IDs spanning publication months. It predicts only supported national topics/directions with integer horizons 1–24 months, but retains other relevant labels when constructing monthly context. Missing categorical values follow the saved encoder treatment; unseen categories use its existing unknown-category handling.

`--features` is a monthly CSV with `origin` (`YYYY-MM`), `political_polarization`, and `forecast_polarization`. Values must be in [0,1] or explicitly missing. Supply a row for every prediction/training month; missing entire month rows fail rather than being silently imputed. Construct these columns with the existing historical lag and support rules. The runner applies the saved transformations; it does not download votes, regenerate polarization measurements, or infer their timing from values alone. Keep the feature construction manifest alongside the file.

Retrospective annotations, verifier prose, and outcomes are excluded from model inputs by an explicit column list. For later data, first reconcile exports and extend the prepared label table and monthly feature table. Preserve complete historical context. Then change the paths, dates, and output folder; add `--allow-new-years` when intentionally extending beyond 2010. No source-code edits are needed for different date ranges. Retraining and scoring new outcome labels remain separate operations from constructing print-time features.

Every output directory must be new and under `data/scored/proquest/`. The runner refuses to overwrite an existing run. Prediction verifies hashes for bundles created by the runner. Existing legacy bundles remain supported, and their actual artifact hashes are recorded in the run manifest. Source exports and the existing model-freeze artifacts are not modified.

## Permutation diagnostics

The [permutation report](../data/scored/proquest/rnn_permutation/report.html) evaluates the existing frozen historical ensembles. Rebuild it with:

```bash
python src/proquest_rnn_permutation.py
python tests/test_proquest_rnn_permutation.py
python tests/test_proquest_rnn_runner.py
```

It reports conditional blockwise model-swap tests separately from input permutation importance. With only four five-year blocks, the paired test has 16 possible assignments. Monthly-input importance rearranges four 48-month origin blocks, preserving within-block order and season; it is a synthetic perturbation diagnostic, not an alternative deployable forecast. The full specification is saved before the diagnostic run and cannot be silently changed on a rerun.

## Separate historical macro-input experiment

`src/proquest_macro_claim_inputs.py` produces exploratory two-topic fold
bundles under `data/scored/proquest/macro_claim_inputs_v1/`. These extend the
claim head with historical production/unemployment scalars and use historical
vintage labels for fitting/stopping. They are **not** interchangeable with the
baseline/polarization bundles accepted by this CLI and are not promoted models.

The module's `bundle_probabilities(bundle, labels, macro, target)` applies a
saved fold bundle without reading target outcomes; every completed bundle
passed a reload comparison. It requires the same prepared print-time label
schema, complete preceding context, and a macro table indexed by monthly
`origin` with the eight `CORE_FEATURES` and audited availability fields. The
helper checks release dates against each publication month and applies the
saved scalers. Historical training is rerun with `--out NEW_DIRECTORY`.
Future use requires refreshed historical-vintage archives and a separately
specified evaluation window; current revised snapshots are not a valid
replacement. The earlier general data-handoff CLI remains unchanged.
