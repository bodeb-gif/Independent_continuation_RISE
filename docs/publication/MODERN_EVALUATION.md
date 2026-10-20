# Separate modern evaluation: preparation specification

Prepared October 19, 2026, after historical results and the polarization extension were inspected. This freezes the procedure and identifies saved claim models for a possible 2011-onward evaluation. It is not a claim of preregistration, an untouched holdout, completed modern verification, or completed source validation.

The active analysis remains annual verified ProQuest 1900–2010, with raw exports as sensitivity material. No modern annual export was found in the local data directory during preparation. On October 19, the author confirmed verification is not finished. Exact modern years and counts remain unknown. The short reply to a combined completion/exposure question is not treated as a separate no-exposure declaration; prior exposure to modern model results still needs explicit documentation. The existing annual loader and original source exports are unchanged. This specification and the intake utility prepare a separate study; intake does not activate that study or score claims.

## Design fixed before modern scoring

The claim outcome is correctness against the existing deterministic target/horizon rules. Retain all eligible source-local rows, including repeated stripped labels unless claim-level evidence establishes duplication. Exclude unsupported topics/scopes/horizons and record reasons. Use the same target-specific reference definitions and thresholds as the historical analysis. Retrospective window annotations, verification prose, and realized outcomes never enter model features.

The primary RNN is the saved baseline three-seed GRU ensemble from the polarization comparison, with seeds 11, 29, and 47 averaged equally. It was trained before 1985 and selected on 1985–1994 validation data, with the existing label-maturity purges. Its 1995–2010 results have already been inspected. Preserve that fitted model and its preprocessing; no fitting, calibration adjustment, epoch selection, seed selection, or hyperparameter selection on modern observations. This tests transport of an older fitted model, not the best model that could be trained today.

Report the two saved claim logistic controls (metadata; metadata plus history) alongside it. Report all three polarization extensions for all three claim configurations as secondary comparisons. Retain baseline, political-only, forecast-only, and both, including unfavorable results. Do not pick the modern winner for the primary table. Added features remain scalar claim/head inputs with the saved training-only imputation, scaling, and missingness indicators. The 12-month RNN sequence and categorical encoding remain unchanged, including their handling of unseen categories.

The political measure retains its twelve complete months t−13 through t−2, t−1 buffer, actual-vote and support gates. Forecast polarization retains the preceding three complete months, newspaper/article aggregation, and support gates. The modern feature panel must include historical context before its first evaluation month. Prove that changing later publications or later votes does not change earlier features. Modern inputs can use information printed before each origin, but cannot borrow future newspaper coverage, verifier prose, or full-period scaling. Dated current reconstructions are not archival real-time vintages; disclose that limitation.

The ten monthly logistic configurations remain a separate task with their existing multiclass targets, control models, four arms, regularization, training-only selection rules, window lengths, and chronological refit schedule. Their historical pipeline estimates coefficients at each evaluation origin; it is not a single frozen final model. A later extension must reproduce saved historical baseline probabilities before running its fixed chronological procedure on modern origins, using only labels available before each origin. Freeze the implementation and selections; do not replace them with choices motivated by modern results. The current preparation does not execute that extension. Binary claim-correctness Brier and summed three-class monthly Brier must never be pooled.

## Corpus intake and processing reconciliation

Recover the VM manifest and processing logs before interpreting counts. Preserve exact years, run identifiers, timestamps/timezones, query and coverage, retrieval limits/order, extraction and verification model identifiers, prompt hashes, decoding/chunking configuration, log hashes, and export hashes. Record prior exposure separately: who saw which modern outcomes, model comparisons, or accuracy summaries, and when. “None reported” is an author statement, not proof of no exposure; disclosed exposure does not prevent descriptive evaluation but limits holdout claims. Unknown exposure fails the readiness check.

Use a separate directory containing exactly the declared modern verified annual shards. Do not copy modern shards into the historical verified directory. The [manifest template](../../data/scored/proquest/modern_readiness/manifest_template.json) deliberately contains unknowns and fails validation until populated from evidence. Copy its `file_entry_template` once per actual year into `files`, then supply `expected_years`. Paths are bare annual filenames and hashes are lowercase SHA-256.

The intake utility reconciles these stage counts:

| Unit | Required identity |
| --- | --- |
| Unique articles within annual run | Retrieved = text available + missing text |
| Unique articles with text | Text available = extracted + terminal extraction failures + extraction pending |
| Candidate claims | Raw candidates = accepted + rejected + verification failures + verification pending |
| Exported rows | Records = accepted claims + no-prediction records |

Retries are attempts, not additional unique articles or candidate claims in these denominators. Retain retry/attempt details in the hashed processing log. Pending extraction, pending verification, and unresolved verification failures prevent reconciliation. Missing text and terminal extraction failures need documented exclusions. Explain successfully extracted articles absent from the verified export; rejection of all claims is one possible explanation, not an inference from absence. No-prediction rows alone do not prove successful processing. The utility reports article overlap between claims and empty records without deleting either.

It also checks schema, source, annual dates, exact export counts, expected years, file hashes, and unmanifested annual shards. Verification prose is checked only as a marker of the verified export contract, never used as a feature or assessed for semantic correctness. A passing intake report establishes mechanical reconciliation against the supplied manifest; it does not establish query completeness, accuracy of upstream logs, claim validity, or a fresh holdout.

```bash
python src/proquest_modern_intake.py --prepare
python src/proquest_modern_intake.py --manifest /path/to/completed_manifest.json --exports /path/to/modern_verified
```

The first command hashes the specification, relevant implementations, saved preprocessing and twelve GRU checkpoints in [model_freeze.json](../../data/scored/proquest/modern_readiness/model_freeze.json). Re-running with changed files fails; preserve the original and record a dated amendment instead of silently replacing it. The saved polarization output manifest also binds historical monthly coefficients, training rows, and selections. The second command prints a read-only reconciliation report and never scores or trains. Keep its output with a hash of the supplied manifest when real intake occurs.

## Outcome maturity and reference freeze

Before scoring, record an explicit `as_of` date and freeze reference files, retrieval dates, revisions, hashes, and coverage by target. A numeric horizon must be an integer 1–24 months after the existing resolver. The print month plus horizon plus a conservative three-month release allowance must be strictly earlier than the `as_of` month. At `as_of=2026-10-19`, the latest nominally mature endpoint is June 2026. A three-month allowance does not prove a series was actually released; verify availability and reference coverage separately.

The readiness helper also requires observed reference months throughout the print-to-endpoint interval and excludes future print dates, missing endpoints/interior months, and unsupported horizons. It returns eligibility only, never a hit or a filled value. Apply it to the correct target series after horizon resolution; do not combine unrelated series' coverage. Mature by calendar but missing from the reference snapshot remains unscorable. Report exclusion counts separately and do not backfill missing outcomes with zero, predictions, or recession-window labels. Revised reference outcomes must be identified as revised, not advertised as real-time ground truth.

Save outcome and exclusion tables separately from feature construction. Before opening comparative modern results, bind actual export hashes, exact years, exposure statement, references, and the prepared model freeze in a dated run manifest. Modern data acquisition and reference updates may require a documented implementation amendment; preserve this preparation snapshot and disclose the change. Do not pool modern results into the historical paper's tables without an explicit scope change.

## Evaluation and reporting

For claim correctness, primary loss is binary Brier with equal total weight per eligible article. Report log loss, accuracy at the fixed 0.5 threshold, ROC AUC and average precision when both classes exist, fixed probability-bin calibration, and year/topic/horizon breakdowns with support. Compare arms on identical eligible rows; missing new inputs use their frozen missingness treatment. Preserve source-local identifiers in local prediction files. Unweighted claim results are a labeled sensitivity analysis.

Use paired loss differences, baseline minus added model, and five-year publication blocks anchored at 2011, with 2,000 block resamples and seed 20261014. Resample complete blocks and recompute the article-weighted loss difference from their retained rows. Report the number and size of blocks; intervals are descriptive when few blocks are available and do not capture extraction or model-selection uncertainty. Monthly models use their own origin-level losses and analogous time blocks. Retain sequential annual results so changing coverage and periods are visible. No random claim train/test split and no claim-level bootstrap implying independent monthly political signals.

The remaining execution dependencies are the completed exports and processing manifest, an exposure statement, explicit activation of a separate modern analysis scope, and a frozen reference/feature readiness check. Human source validation is deferred at the user's request and is not part of this preparation work. Any modern results produced before it remain conditional on machine labels and deterministic mappings.
