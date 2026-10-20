# ProQuest new-data preparation and model handoff

The workflow now has explicit export-to-input, optional scoring, polarization-feature, and model-run commands. Current execution remains annual 1900–2010. Modern examples below describe a future, separately authorized run; no real modern exports have been processed or evaluated here.

## Preserve and reconcile new exports

Keep raw exports, verified exports, VM processing logs and reference snapshots separate and unchanged. The current [manifest template](../data/scored/proquest/modern_readiness/manifest_template.json) requires exact years, file hashes, stage counts, model/prompt provenance and prior-exposure documentation. Empty export rows do not establish processing success. Modern intake is read-only:

```bash
python src/proquest_modern_intake.py \
  --manifest path/to/completed_manifest.json --exports path/to/verified_modern_exports
```

Intake reconciliation does not authorize expanded analysis or establish an untouched holdout. Record the evaluation question, model/configuration, date boundaries, metrics and information timing before inspecting new outcomes. Source validation remains a separate scientific requirement.

## Prepare model inputs without outcomes

The historical example was run and all 274,070 normalized claims matched the existing inputs:

```bash
python src/proquest_prepare_inputs.py \
  --exports data/proquest/verified --first-year 1900 --last-year 2010 \
  --out data/scored/proquest/prepared_historical_next
```

`claims.csv.gz` contains only the runner's print-time columns. It retains unscorable context claims and repeated stripped labels, uses physical file-line addresses, and excludes verifier prose, retrospective annotations and outcome columns. Empty-record counts and input hashes are recorded in `manifest.json`.

For a later modern-only export directory, provide its actual contiguous year range, `--allow-new-years`, and `--manifest`. Use `--history data/scored/proquest/descriptive/scored_claims.csv.gz` to carry historical context forward. History is read through the feature whitelist; existing outcomes are not copied into prediction inputs. Overlapping publication dates or repeated record addresses are rejected instead of deduplicated. Changing extraction models/prompts is a measurement change that must be documented even if the schema matches.

## Score outcomes separately when mature

The same preparation command can add `--score --as-of YYYY-MM-DD --reference-dir path/to/frozen_references`, writing a different new output folder. References must have the documented filenames/schema used by `proquest_descriptive.load_reference`; stage and hash them before execution. The current reference snapshots do not automatically update to cover new years.

The scorer retains the original deterministic bands and horizon rules. It excludes future publication dates, unsupported claims, endpoints whose horizon plus three-month allowance has not matured, and missing reference months. Missing outcomes stay unscorable. The historical check reproduced all 175,855 scorable claims and their hits exactly; exclusion reason wording differs because the new adapter names maturity/reference gates explicitly.

Outcome scoring is separate from predictive feature construction. Revised endpoint references may be evaluation truth; they do not establish historical real-time label vintages. Preserve this distinction when designing any new training/evaluation protocol. Machine-labeled numeric horizons still do not establish source-supported strict eligibility.

## Rebuild the two polarization measures

```bash
python src/proquest_prepare_features.py \
  --claims data/scored/proquest/prepared_historical_next/claims.csv.gz \
  --rollcalls data/scored/proquest/polarization/rollcall_separation.csv.gz \
  --start 1900-01 --through 2010-12 \
  --out data/scored/proquest/prepared_features_next
```

This reproduced all 1,332 historical feature months. The command accepts explicit calendars and `--allow-new-years` for later execution. It reads no outcomes. Political polarization uses eligible House party vote separation over twelve months ending at t−2; forecast polarization uses the previous three complete print months with the existing article/paper support rules. Definitions and missingness rules are unchanged.

Future political inputs require an extended, provenance-checked rollcall separation table constructed with the existing `party_separation` function and its vote/member/date rules. The builder does not download new votes or infer complete voting coverage from the supplied rows. Do not treat a truncated voting file as proof that no votes occurred. Supply complete newspaper history and voting coverage before making later feature rows. Preserve the upstream manifests with the feature manifest.

## Predict, refit, and evaluate as separate operations

Use the [runner guide](PROQUEST_RNN_RUNNER.md) for complete arguments. `predict` applies a named saved bundle without reading outcomes. `train` takes scored prepared claims, explicit validation/test dates, a fixed seed list, and a new output directory. It writes fitted preprocessing, both logistic controls, checkpoints, split assignments, predictions and hashes. Source preparation and scoring do not silently launch either operation.

The original four-arm bundle remains `data/scored/proquest/polarization/claims`. The provisional development bundle is `data/scored/proquest/rnn_development_v1/bundles/gru8_standard_20` and contains only the baseline arm. Its `bundle_manifest.json` can be supplied as `--configuration` for a separately planned refit. Omit age decay; none of the tested decay variants passed the improvement rule. The runner can train explicitly requested polarization arms with that configuration, but those combinations have not been validated by the completed development study.

For a frozen external evaluation, use the preselected bundle and preserve prediction files before joining mature outcomes. If using a refitted model, its training and stopping periods must precede the evaluation period with the existing horizon purge. Do not repeatedly refit against inspected modern scores. `train` already reports its test metrics; choose all settings before invoking it. Give every run a new directory under `data/scored/proquest/` and preserve the original historical outputs.

The prepared table, feature table, reference snapshot, source/processing manifest, configuration, prior-exposure statement, software lock and run manifest form the handoff. Package permissions and public release are separate from this local research workflow.
