# ProQuest publication analysis specification

Version 1, October 14, 2026. This specification constrains subsequent publication work. It was written after inspecting the existing 1900–2010 results and is **not a preregistration or an untouched evaluation design**. Changes require a dated reason and identification of affected exhibits.

## Population and measurement

Use only annual verified ProQuest exports for 1900–2010, with annual raw exports as a sensitivity set. Preserve source rows, including repeated stripped labels. LOC remains extraction validation only. Retrospective annotations and verifier prose are never model features. No modern extension is admitted by this specification.

Maintain legacy, expanded, and strict views. The legacy rules remain those saved in `descriptive/summary.json`. An expanded interpretation must state its inference. Strict eligibility requires source-supported forecast status, national scope, exact quantity, direction, benchmark compatibility, and explicit horizon that the deterministic endpoint rule can represent. Source evidence must distinguish level from growth, price level from inflation, employment from unemployment, and recession events from IP endpoints. Unresolved conditions, original timing, or source mapping prevent strict inclusion. Decide eligibility before inspecting correctness. A numeric machine horizon is insufficient.

## Primary comparisons

The descriptive primary endpoint is the newspaper-minus-fixed-baseline correctness difference, separately by supported target, with equal total weight per article within target. Both predictions use identical eligible records and deterministic outcomes. Show the legacy comparison alongside the strict result and report composition changes. The audited subset supports an audited-population analysis; it does not establish strict eligibility for every unreviewed claim. No strict estimate is currently available.

The predictive primary endpoint is macro-only minus macro-plus-newspapers multiclass Brier loss on the same 408 monthly origins in 1977–2010, using the saved selected macro benchmark. Positive values favor newspapers. Brier is the sum of squared errors over three classes, range 0–2. Retain recent class frequencies as a comparator. Report log loss, accuracy, class-specific discrimination, and calibration regardless of sign. The short CPI extension is secondary.

Preserve the selected benchmark's twelve candidates, annual training-only forward selection, historical label vintages, input timing, and saved folds as defined by [its specification](../../data/scored/proquest/macro_benchmark/evaluation_spec.json). No additional models or tuning are introduced here. Feature values must be available at print time; realized outcomes and retrospective verifier explanations are excluded. Revised macro values are permissible evaluation truth, not historical training inputs.

## Dependence and bounded checks

Use paired time blocks for economic comparisons; five years is primary, with two and ten years secondary. Report actual block counts and overlapping outcome windows. Existing predictive intervals condition on saved predictions and omit extraction and model-selection uncertainty. The main Brier interval has seven blocks; the CPI extension has only two five-year blocks.

Retain six bounded checks: source-validated interpretation; explicit versus inferred horizons and direct versus proxy outcomes; raw sensitivity; equal article/month and common-paper support; era and the already observed 2007–2009 evaluation exclusion; and a limited alternative macro information set only if historical availability can be documented before fitting. No such new macro variant is authorized by a favorable result alone.

The source audit reports field validity and joint usability, with unresolved mapping and missing context visible. Use documented sampling probabilities and article-aware uncertainty; do not treat claims from one article as independent reviews or apply a global F1 correction to all economic estimates. Review the error-impact procedure after the pilot, before main audit outcomes are revealed, and record that amendment.

## Development record

Earlier descriptive, follow-up, crisis, RNN, monthly-information, macro-information, diagnostics, robustness, and selected-benchmark results were already inspected. The selected macro benchmark replaces a weaker original comparator whose results remain in the supplement. The 2007–2009 exclusion was already examined and reverses the Brier gain. None of these years can be relabeled an untouched test period.

Version 1 introduces evidence assembly and a source-retrieval pilot only. It changes no scorer, fitted model, source export, or historical result.

## October 14 polarization amendment

Following the author's explicit request to test both political and forecast polarization across the active models, add the separately specified [polarization extension](../../data/scored/proquest/polarization/evaluation_spec.json). Its four fixed arms preserve prior comparisons and use only earlier dated voting and newspaper information. The standard current career-based NOMINATE index is excluded as a historical predictor. This extension is exploratory, leaves the original primary results intact, and introduces no modern claims. See [completed comparisons and interpretation](POLARIZATION.md); do not select further variants from the observed evaluation results.
