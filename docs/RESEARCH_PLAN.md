# Research plan: historical economic forecasts in the newspaper record

Prepared September 18, 2026. This is a proposed work program, not a record of completed experiments or a preregistration of results already inspected.

**Objective:** produce a defensible paper on the accuracy and informational value of economic forecasts reported in a selected newspaper corpus, supported by human validation, credible economic scoring, and reproducible evaluation. Aim for a complete, mentor-reviewed manuscript this semester; continue journal revisions afterward if necessary.

**Working paper title:** *Economic Forecasts in the U.S. Newspaper Record: Measurement, Accuracy, and Predictive Information.* Narrow the title to the actual sampling population and supported findings when drafting.

The ambition is a substantial empirical paper plus a reusable extraction benchmark and research package. The order below reflects dependencies, not a limit on what Bode can accomplish. Additional experiments earn their place by resolving a scientific question. A null result is an acceptable outcome.

## 1. Scope, existing assets, and the contribution

Keep the annual verified ProQuest exports for 1900–2010 as the current primary corpus and the annual raw exports as the sensitivity corpus. Keep LOC exclusively for extraction validation. Exclude old crisis-window exports from analysis. Preserve source files and record source hashes. Do not merge identical stripped label rows without source-level evidence.

The 2011–2026 extraction is an extension in progress, not an existing analysis input. Admit it only after verification, provenance checks, a documented scope update, and outcome-maturity rules. The current `annual_files()` contract explicitly expects 1900–2010; extend it deliberately with tests rather than silently changing the meaning of existing reports.

Existing foundations:

| Asset | Starting point | Next improvement |
| --- | --- | --- |
| Corpus inventory | `src/analyze_proquest.py` | Article denominators, extraction status, lineage, extension manifest |
| Outcome scoring | `src/proquest_descriptive.py` | Validate semantic matches and distinguish precise targets from proxies |
| Descriptive comparisons | `src/proquest_followups.py` | Common support, dependence-aware uncertainty, validation sensitivity |
| Historical case study | `src/proquest_2008.py` | Source-audited examples and prospectively specified comparison episodes |
| Correctness model | `src/proquest_rnn.py` | Stronger controls, development folds, frozen modern evaluation |
| Extraction evaluation | `validation/gold_extraction/` | LOC model-reference comparison and single-annotator claim review |

The saved descriptive report contains 274,070 verified claims and 175,855 scorable claims. Those are corpus counts, not counts of independent economic outcomes. The current 40.8% correctness versus 53.6% fixed-baseline result is an observed development finding, not a hypothesis first proposed before seeing data.

Prepare a literature matrix with approximately 15–25 closely relevant papers: question, corpus, dates, sampling, annotation, forecast target, horizon, baseline, uncertainty, and the precise difference from this project. Historical newspaper forecasting has already been studied. Start with [Mathy and Stekler's business-press study](https://www2.gwu.edu/~forcpgm/2016-011.pdf) and [the study of forecasts surrounding the 1937–1938 recession](https://www2.gwu.edu/~forcpgm/2018-004.pdf). Follow their references and identify final published versions for the manuscript bibliography.

Proposed contribution: evaluate a much broader, systematically assembled record of explicit forecasts, quantify how extraction and interpretation affect apparent accuracy, and test whether newspaper information adds value beyond simple economic baselines. Establish novelty through the matrix; avoid an unsupported “first ever” claim.

**Deliverable:** two-page study concept, literature matrix, and a paragraph distinguishing this project from the nearest three papers.

## 2. Research questions and an analysis freeze

Use three linked questions, with the first two sufficient for a coherent paper:

1. **Measurement:** How reliably can the pipeline identify, interpret, and score forecasts, and how much do its errors change the substantive findings?
2. **Forecast accuracy:** Within the sampled corpus and supported forecast targets, how do published forecasts perform against simple alternatives on identical observations?
3. **Incremental information:** Does the newspaper record improve future-outcome or claim-correctness prediction beyond metadata, past outcome frequencies, and economic information available at the time?

Before new validation and modern outcome evaluation, save an analysis specification containing primary population, primary endpoint, weighting, exclusions, model candidates, tuning budget, folds, uncertainty method, and a short list of secondary comparisons. Timestamp it and log changes with reasons.

Call the existing historical analyses exploratory. The specification can constrain new work; it cannot retrospectively make earlier discovery confirmatory. Modern evaluation is also historical evaluation on previously unexamined records, not a live forecasting trial.

Proposed primary descriptive endpoint: equal-article mean difference in correctness between newspaper calls and the fixed-direction baseline, on the semantically supported, explicit-horizon subset, reported separately by target. Retain a pooled estimate only with explicit target weights. Also report the full legacy sample so that narrowing the analysis is visible.

A suggested primary modeling endpoint is article-weighted Brier-score improvement over a preselected strong baseline. Report log loss, calibration, average precision, and ROC-AUC as complementary measures. Freeze this choice before the new evaluation; explain that earlier development reports emphasized average precision.

## 3. Validation: LOC model comparison and LOC/ProQuest claim grading

**Chosen design:** compare GPT-4o-mini with DeepSeek on LOC, then have Bode personally grade approximately 500 extracted claims, including a small ProQuest sample. Human claim review remains the planned primary validation. A later request added a blinded **LOC page enumeration and recall setup**; its current 24-page packet is a pilot from a partial shard, with model-reference scoring prepared but no completed recall estimate. ProQuest recall and a second human annotator are not currently planned. See `validation/loc_review/README.md` for the packet, output contract, and human adjudication requirements.

The exercises provide different evidence:

| Exercise | Result to report |
| --- | --- |
| GPT-4o-mini versus DeepSeek on the same LOC inputs | Coverage relative to a model-generated reference, overlap, and model-specific candidates |
| Bode checks sampled claims against their LOC source context | Single-annotator assessment of forecast validity and field correctness on LOC |
| Bode grades a small sample of already extracted ProQuest claims | Direct assessment of claim validity, labels, and benchmark matching in the sampled analysis records; no recall measurement |

Report LOC model coverage, LOC human grading, and ProQuest human grading separately. The ProQuest sample supplies direct evidence about the graded claims in the analysis corpus; it does not identify forecasts missed by extraction. Neither human-grading exercise estimates absolute recall.

### 3.1 Run a matched model comparison

Recover the actual ProQuest extraction and verification prompts, schema, model identifiers, context limits, chunking/overlap, and truncation handling. Run GPT-4o-mini on LOC using the production settings as closely as possible. Run DeepSeek independently on the same text, without showing either model the other's outputs. Record exact versions and settings. Additional models and keyword baselines are optional, not prerequisites.

Choose a fixed LOC sample before comparing results, spanning available eras, newspapers, text lengths, and OCR quality. Include calm periods if readily available; otherwise document the cache's crisis-heavy coverage. The existing 16-page model-adjudicated reference remains development material. Keep any prompt-development pages separate from final evaluation pages. Model runs operate over complete selected inputs, but Bode does not have to enumerate every forecast in those inputs.

Use the same forecast definition and return source-anchored quotes. Preserve raw extraction and post-verification outputs so that removing true-looking candidates is visible. Log failed calls and truncated inputs separately from successful calls that return no forecasts.

### 3.2 Use DeepSeek as a reference, with the metric named accurately

Let D be the number of distinct DeepSeek candidate claims, G the number of GPT-4o-mini candidate claims, and M the number of one-to-one matches on the same input documents. Report:

- **GPT-4o-mini coverage relative to DeepSeek:** M / D.
- **Reciprocal coverage:** M / G, showing how much of GPT-4o-mini's output DeepSeek also found.
- Counts of shared, DeepSeek-only, and GPT-4o-mini-only candidates, including zero-output documents and failures.

When a denominator is zero, report the relevant metric as undefined rather than inventing a perfect or failed score. Deduplicate candidate repetitions only when source anchors establish that they are the same claim. This matching task does not authorize deduplicating stripped ProQuest labels.

“Recall against a DeepSeek-generated reference” is an acceptable explicitly qualified description of M / D. Do not call it measured true recall or claim to know DeepSeek's own recall. DeepSeek can miss real forecasts and propose false ones; GPT-4o-mini-only candidates are not automatically false positives. Human review of a sample can characterize these problems without finding everything both models missed.

Use source anchors and one-to-one matches, with a fixed matching rule and inspection of questionable matches. The existing evaluator uses token containment while parts of the old protocol describe Jaccard matching; reconcile that discrepancy before reusing its scores. Inspect a sample of matched and unmatched pairs within the human-review allocation. Shared words alone do not establish that two predictions are identical. Report sensitivity to reasonable matching thresholds if it materially changes the comparison.

### 3.3 Bode validates approximately 500 claims

Proposed allocation keeps the total near 500 claims rather than adding a new large workload:

| Component | Target | Purpose |
| --- | ---: | --- |
| LOC: probability sample of GPT-4o-mini's final accepted claims | 300 | Estimate accepted-claim validity and field correctness on LOC |
| LOC: diagnostic sample | 100 | Inspect DeepSeek-only candidates, verifier-rejected candidates, questionable matches, and ambiguous interpretations |
| ProQuest: probability sample of verified claims included in the scored analysis | 100 | Check whether the actual analyzed forecasts, labels, horizons, and benchmark mappings match their source articles |

Choose the 300 LOC and 100 ProQuest claims with documented random sampling within each source, spreading across eras and major claim types where possible. For ProQuest, sample the active annual 1900–2010 scored corpus and seek coverage across major newspapers without attempting a precise estimate for every subgroup. Record inclusion probabilities if using unequal strata and weight source-specific aggregate estimates accordingly. Keep the diagnostic 100 separate from population estimates. Avoid reviewing the same claim twice as two distinct examples. If a stratum has fewer candidates than allocated, review all available candidates and record the reallocation before grading.

The 100-claim ProQuest sample is a claim-grading audit, not a recall experiment: retrieve each sampled claim and its context, grade it, and move on. No empty-article sample, search for additional forecasts, or comparison of full-article extraction completeness is required. Its estimates apply to the sampled scored-claim population; they do not establish quality for excluded or unextracted forecasts. A small sample also cannot establish precise error rates for every paper and decade.

Pilot the rubric on a small separate batch before the final sample. For each sampled claim, Bode records:

1. Whether it is genuinely a future economic forecast, rather than a present/past description, advertisement, or unsupported fragment.
2. Topic and exact predicted variable, direction, geographic scope, and speaker/voice when supported.
3. Whether the horizon is explicit, inferable, or absent, and what time interval the text actually names.
4. Hedging and conditional language, with an unclear category when needed.
5. Whether the proposed benchmark matches the meaning of the claim, or is only a proxy.
6. An error category and short explanation when the extraction or label is wrong.

Show the quote with enough surrounding context and publication date to interpret it. Read more context only when needed; this is candidate review, not a page-wide search for missing forecasts. Where practical, hide model identity, automated field labels, and realized outcomes until Bode's interpretation is saved. The candidate span is necessarily supplied by the extraction process, so the review is not independent discovery of forecasts.

Bode is the sole human annotator. Report human-versus-model agreement and confusion matrices, not human-human inter-rater reliability. A small optional blind reread can check Bode's consistency, but is not a second independent reviewer and is not required. Keep original labels and any later revisions in the record rather than overwriting disagreements.

### 3.4 Keep the workflow lightweight

Use a local annotation queue or simple review file for LOC. For the 100 ProQuest claims, use a small notebook or existing VM workflow that retrieves a batch of sampled claim IDs and shows each quote with surrounding context. Save Bode's labels as the batch progresses; no dedicated app or full-document review interface is required. Keep source text in the permitted environment and export only authorized derived labels, IDs, and summaries. Preserve document IDs, sampling probabilities, automated labels, and Bode's labels separately so results can be recomputed.

Measure accepted-claim precision/validity separately on each source's probability sample and per-field correctness among valid forecasts. Also report the fraction of reviewed accepted claims that are usable with all required fields correct, since finding a real forecast with the wrong horizon still creates a scoring problem. Use document-clustered uncertainty where sample support permits and show denominators. Candidate validity estimates are relative to Bode's documented judgments, not an error-free human oracle.

For the diagnostic sample, report what the disagreements reveal: additional true-looking forecasts from DeepSeek, false suggestions, verifier deletions, semantic errors, or matching errors. Do not convert the diagnostic sample into an absolute recall estimate. Do not use LOC label-error rates as measured ProQuest error rates.

Avoid repeated prompt tuning against the final human sample. If it becomes development data, say so and keep any subsequent evaluation separate. This need not become a large annotation project: the core deliverables are the model-overlap table, roughly 500 single-annotator claim reviews, error examples, and a short limitations paragraph.

**Suggested manuscript wording:** “We compared GPT-4o-mini extraction with a DeepSeek-generated reference on LOC and conducted single-annotator claim grading on separate LOC and ProQuest samples. Human review assessed the validity and interpretation of extracted claims against source context. The model comparison measures coverage relative to DeepSeek; we did not measure absolute extraction recall.”

**Deliverables:** sampling manifest; exact model configurations; LOC matched/unmatched candidate table; Bode's labels and rubric; separate LOC and ProQuest claim/field-validity metrics; diagnostic error summary. No absolute-recall estimate or human-human inter-rater agreement claim is planned.

## 4. Fix the measurement contract

Create a variable dictionary that distinguishes the predicted quantity, transformation, reference period, endpoint/window, condition, geographic scope, and attribution. Use the production rubric, LOC examples, and the small ProQuest source-context audit to assess mappings. Distinguish directly checked interpretations from assumptions extrapolated to unaudited ProQuest claims; keep unsupported interpretations provisional. Add fields as derived annotations without altering original exports.

| Textual distinction | Required scoring treatment |
| --- | --- |
| Prices fall versus inflation slows | Price-level change versus change in inflation rate; do not collapse them |
| Employment rises versus unemployment falls | Different variables; map only when justified |
| Growth slows versus output falls | Growth-rate decline versus level decline |
| Recession occurs within a year versus output is lower in a year | Event-within-window versus endpoint target |
| GDP versus industrial production | Exact target where available; otherwise disclose and separate the proxy |
| Stock market versus bonds, yields, or a specific security | Asset-specific benchmark or exclusion; broad stock prices are not universal |
| “By December,” “next quarter,” “over the year” | Calendar endpoint, quarter, or interval, resolved from publication date |
| Conditional forecast | Assess under a separately specified condition rule or exclude from unconditional scoring |
| Prediction quoted from an earlier date | Record original forecast date if recoverable; otherwise flag/restrict |

Use three transparent analysis sets: **strict** (supported target and explicit horizon), **expanded** (documented inferences), and **legacy** (current rules reproduced). A numeric exported horizon does not prove that the original article stated it; audit the meaning of the exported field before calling it explicit. The strict set is more interpretable but may be selective, so describe how its article/paper/era composition differs.

Keep the pre-1919 NBER-state proxy separate from direct variable outcomes. For vague forecasts, report inability to assess a precise horizon rather than letting a default silently become part of the claim.

Audit monthly endpoint conventions: market monthly averages include post-publication days; calendar dates can shift the intended horizon; fixed change bands may mean different things over one versus twenty-four months. Preserve current bands as the legacy specification, then justify alternatives economically before comparing results. Do not choose bands because they maximize or minimize newspaper accuracy.

Create source-grounded known-answer examples and code tests for these distinctions. A synthetic test establishes correct implementation of the chosen rule, not that the rule captures an article's meaning.

**Deliverable:** measurement codebook, benchmark map, exclusion flowchart, source-audited example table, and strict/expanded/legacy results.

## 5. Audit sampling, coverage, duplication, and verification

Recover exact query strings and versions, databases, search dates, yearly/paper coverage, retrieval order, result caps, pagination, article counts, retries, and model failures. Distinguish no forecast, filtered-out forecast, unavailable text, parser failure, and unfinished processing. Reconcile raw articles absent from verified exports with the VM manifest.

The downturn/recovery search produces a selected corpus. Neither weighting nor additional model complexity can recover forecasts that were never eligible for retrieval without new assumptions or data.

High-value extension: collect a fixed probability sample of broader business/economic articles across selected newspaper-years, including calm periods, and compare it with the downturn/recovery query. Use a separately labeled sampling-sensitivity cohort and report its denominator. Do not quietly pool a new retrieval design with the primary historical series. If all-article denominators are unavailable, restrict any “attention” measure to its actual denominator, such as retrieved articles, and name it accordingly.

Investigate repeated exports, syndicated stories, and repeated quotations using source-level anchors in the VM. Different articles repeating the same forecast matter for exposure but may not be independent forecast decisions. Report exposure-weighted and unique-forecast results only when the latter can be established. Until then, retain stripped rows and use article/date clustering and transparent sensitivity checks.

Run the documented scorer on raw and verified sets using an explicit source adapter; the current scorer requires a verification field. Never fabricate that field to bypass validation. Pair raw and verified claims only when lineage supports it; otherwise report distributional comparisons and article-level changes. Estimate what verification removes by topic, direction, horizon, paper, and era.

**Deliverables:** corpus flow diagram; newspaper-by-year coverage heatmap; query and processing manifest; raw/verified comparison; duplication audit; sampling-sensitivity report if collected.

## 6. Establish baseline-relative historical findings

Complete these analyses in order, with the same eligible observations on both sides of every comparison:

1. Correctness, direction confusion matrices, and baseline gaps by target and horizon. Report article-weighted primary estimates and claim- and month-weighted sensitivities.
2. Temporal changes on common newspaper/target/horizon support; show how much of the pooled change reflects sample composition. Keep a full-sample view beside restricted panels.
3. False alarms and missed declines, distinguishing output declines from literal recession-onset forecasts. Use continuous chronology only for descriptive event alignment and outcomes.
4. Prior-only cross-paper consensus versus individual calls. Construct predictive histories from readable print-time claims, independent of whether future outcomes can eventually be scored. The current descriptive consensus input is outcome-eligible; audit that selection before reusing it for prediction.
5. Experts, officials, journalists, and hedging comparisons after source-field validation and composition adjustment. These are associations, not causal effects or numerical confidence calibration.
6. Publisher differences with shared coverage and partial pooling where useful. Report rank uncertainty and leave-one-era-out stability; avoid presenting incomparable pairwise overlaps as a universal league table.

Retain the fixed-direction baseline. Add an expanding-window majority direction by target/horizon, a flat/no-change baseline, and a persistence or trend baseline where observations available at publication support it. Estimate all learned choices on past data only. Different baseline families answer different questions; do not compare an outcome-direction baseline's raw accuracy with a correctness model's AUC.

Professional-survey comparison is an extension worth doing only when target, forecast date, horizon, evaluation period, and loss function can be aligned. Do not reuse historical LOC survey comparisons as evidence for ProQuest or compare heterogeneous pooled hit rates.

**Deliverable:** a compact set of descriptive findings whose interpretation remains stable—or whose instability is itself carefully explained—across the principal measurement and weighting checks.

## 7. Make inference reflect the actual information in the data

Report numbers of articles, publication months, unique target/month/horizon cells, and business cycles in addition to claims. Many claims share the same realized outcome; article weighting does not remove calendar dependence.

Use paired comparisons and resample time blocks jointly across papers. Account for overlapping outcome windows when choosing block lengths. Examine several prespecified plausible lengths, for example two, five, and ten years where the number of blocks permits, rather than selecting the interval that excludes zero. With few blocks, present wide intervals and episode-level results rather than implying high precision from claim counts. A mentor/statistician should review the dependence design.

Fit an optional hierarchical model for paper/topic/era differences to reduce noisy extreme rankings. Report its assumptions and uncertainty; it is not a cure for sample selection. Distinguish descriptive adjustment from causal identification.

Define families of secondary tests and apply an appropriate multiple-comparison procedure if making significance claims across many papers/topics/models. Present effect sizes and intervals even when results are not statistically distinguishable from zero.

Carry validation limitations into the conclusions. Summarize LOC label changes separately without pooling LOC into the ProQuest outcome analysis. On the 100 probability-sampled ProQuest claims, compare automated and human-reviewed interpretations and, where defensible, the corresponding correctness and baseline-gap contributions. Use sampling weights and show uncertainty; dropping invalid claims changes the eligible denominator and should be reported explicitly. Distinguish this direct audit evidence from broader hypothetical error-sensitivity scenarios. Do not apply a global F1-based adjustment, transfer LOC error rates to ProQuest, or infer errors among unextracted claims from this audit. Joint errors in horizon and direction matter.

Use a prespecified robustness grid covering sample definition, horizon basis, benchmark, change bands, article/month weighting, raw/verified set, and coverage restrictions. Summarize all planned specifications, including unfavorable ones. This is a map of assumption dependence, not a vote in which correlated specifications count as independent replications.

**Deliverable:** dependence-aware intervals, robustness matrix, validation-impact analysis, and an explicit statement of which conclusions remain uncertain.

## 8. Build a demanding predictive evaluation

Separate two targets:

- **Claim correctness:** estimate whether a particular published forecast will match its defined outcome.
- **Economic outcome:** estimate the future variable direction or event directly, then test whether adding newspaper information improves an economic baseline.

The second is a stronger test of incremental economic information. The first may succeed simply by learning that a particular direction is usually wrong in a given economic regime.

### Development and holdout structure

Treat all already inspected 1900–2010 results, including the old 1995–2010 test, as development evidence for subsequent model design. Use expanding chronological development folds with earlier inner validation. Provisional outer periods are 1950–1964, 1965–1979, 1980–1994, and 1995–2010; revise for target coverage and sample sizes before running the comparison. These folds describe historical stability, not a fresh independent confirmation.

At every origin, purge labels whose outcome endpoints or required release dates occur after training closes. Learn scalers, encoders, imputations, feature selection, calibration, and hyperparameters using only permitted training/development data. Keep article duplicates together and examine source-confirmed repeated forecasts across boundaries. Rolling-origin evaluation is described in [Forecasting: Principles and Practice](https://otexts.com/fpp3/tscv.html).

Default modern design: reserve all eligible 2011 onward outcomes for one frozen evaluation, provided they have not already been inspected for model selection. Log any prior exposure honestly. If modern development is necessary, designate an early segment for development and a later segment for final evaluation before viewing outcomes. Do not rotate through modern holdouts until a favorable one appears.

### Models and controls

| Model/control | Scientific purpose |
| --- | --- |
| Training prevalence and target/horizon base rates | Establish how much follows from outcome frequency |
| Metadata logistic regression | Reproduce the simple claim-level benchmark |
| Logistic regression with history | Test linear use of the same historical information |
| Regularized GAM or spline model | Allow interpretable nonlinearities without recurrence |
| Gradient-boosted trees | Strong nonlinear tabular baseline |
| Feed-forward network with flattened history | Match GRU inputs and roughly match capacity to isolate recurrence |
| Existing GRU ensemble | Test whether sequence structure contributes |
| Macro-only model | Establish performance from observable economic conditions |
| Macro plus press model | Test incremental newspaper information |
| Optional temporal convolution or small transformer | Test an additional sequence mechanism only after the matched controls |

Use comparable tuning budgets and the same eligible rows, folds, and metrics. Keep seed variation visible and use a predeclared ensemble; do not select the luckiest test seed. Prefer a bounded model search to a large architecture sweep that exhausts the available historical evidence.

Run ablations for metadata-only, history-only, no paper identity, no direction, no volume, no hedging, no voice, different lookbacks, normalized shares versus counts, and macro-only versus macro-plus-press. Time-order disruption within historical sequences can be a diagnostic control if carefully designed; it is not automatically a valid significance test.

Evaluate Brier score, log loss, calibration slope/intercept or reliability plots, AP, ROC-AUC, and prespecified decision thresholds. Report paired time-block uncertainty, performance by era and target, and whether a single crisis drives an apparent gain. Fit calibration using development data only. Explain contributions through held-out ablations and stable associations; do not interpret feature importance as causality.

For a monthly economic-outcome model, aggregate the press inputs at the monthly decision point and count outcomes at that level. Do not manufacture a large sample by repeating the same outcome for every article. Explicit recession-onset prediction should be a separately specified secondary task because the event count is small.

## 9. Real-time information and the modern extension

Separate retrospective realized outcomes from print-time predictor values and training-label availability. Revised reference data are reasonable for describing what ultimately happened, but a release lag applied to a revised series does not reconstruct what a forecaster knew.

Use vintage data for macro predictors and for label availability where recoverable. [ALFRED documents historical vintages and their limitations](https://alfred.stlouisfed.org/help), and the [FRED real-time API documentation](https://fred.stlouisfed.org/docs/api/fred/realtime_period.html) explains as-of retrieval. Where vintage coverage is missing, keep the analysis explicitly retrospective or perform a restricted vintage-supported evaluation. Do not claim full real-time feasibility for the entire century.

Freeze the modern cutoff date, available benchmark snapshot, and eligibility rule before calculating results. An observation enters a scored cohort only when its intended outcome window has finished and the necessary reference data exist. Report unscored/right-censored forecasts separately. Late 2025 and 2026 claims with long horizons will remain pending; their presence in the extraction corpus does not make them usable targets.

Report modern completeness by publication year and horizon. Short-horizon claims mature first, so apparent recent-year accuracy is compositionally selected. Include a mature-cohort comparison with a common maximum horizon where feasible.

Primary model option: freeze training using labels available at the initial modern origin, then evaluate sequentially with newly available press context but no outcome-driven retuning. Secondary option: a predeclared annual refit using only then-mature labels. Keep these results separate and label retrospective vintage limitations.

Check extraction-model hindsight as well: require evidence spans, forbid outcome information in extraction prompts, and audit whether obvious historical context changes labels. A model trained after the events can still infer historically famous outcomes. Date/name masking is a diagnostic on a suitable subset, not a replacement for publication-grounded annotation or a guarantee that memorization is removed.

**Deliverable:** modern extension manifest, maturity table, frozen evaluation specification, predictions saved before scoring, and versioned evaluation report.

## 10. High-value extensions after the foundations

These are substantial additional work streams, not requirements to squeeze into one manuscript. Select using scientific value and available evidence.

| Extension | Why it improves the project | Prerequisite and limitation |
| --- | --- | --- |
| Forecast revision panel | Study how the same forecaster updates after new information | Reliable speaker/entity IDs, original dates, repeated observations; changing speaker composition cannot establish revisions |
| Quotation and syndication network | Separate independent opinions from repeated dissemination | Source anchors and validated near-duplicate matching |
| Numerical forecast subset | Measure magnitude error and probabilistic calibration where actually stated | Exact variables/units and genuine probabilities; do not convert hedging into invented probabilities |
| Broader-query sampling experiment | Quantify how retrieval shapes conclusions | Explicit article sampling frame and denominators |
| Replication of a historical paper | Demonstrate agreement/disagreement with an established method on comparable source material | Match periods, outlets, and definitions; explain source differences |
| Source-text predictive model | Test whether wording adds information beyond metadata | Permitted in-VM processing and validated text provenance; embeddings may carry hindsight and are not automatically exportable |
| Forecast combination | Test whether press signals improve a simple macro or survey forecast | Common target/horizon and strictly past-only combination weights |
| Decision-value analysis | Translate forecast quality into a defined user's loss function | Prespecified costs and thresholds; retrospective stock-direction hits are not a trading strategy |
| New data release/benchmark paper | Make validated annotations and tools reusable | Human validation and a clearly defined independent contribution; avoid splitting one thin result into several papers |

A useful historical interpretation module would revisit 1929–1933, the 1970s, 2007–2009, and a modern shock/recovery episode using the same rules. Choose episodes before comparing their results; report failures of the proposed explanation. Source examples can explain mechanisms but do not establish a causal effect of media, incentives, or expertise.

## 11. Reproducibility and repository work

Make the current ProQuest study the README's main narrative and clearly archive older LOC outcome claims. Replace unsupported novelty statements and distinguish machine verification, model-generated reference labels, human consensus, and independent human annotation.

Proposed future outputs, created only when their corresponding work is done:

```text
docs/RESEARCH_PLAN.md                         this plan
docs/RESEARCH_SPECIFICATION.md                frozen decisions and amendments
docs/VALIDATION_PROTOCOL.md                   rubric and sampling/annotation protocol
docs/LITERATURE_MATRIX.md                     nearest work and contribution
validation/loc_forecasts_v2/                  permitted public-source validation artifacts
data/scored/proquest/research/validation/     permitted ProQuest grading results and error-sensitivity scenarios
data/scored/proquest/research/sampling/       coverage and selection reports
data/scored/proquest/research/scoring/        strict/expanded/legacy outcomes
data/scored/proquest/research/robustness/     dependence and specification analyses
data/scored/proquest/research/models/         folds, predictions, settings, manifests
data/scored/proquest/research/modern/         extension and maturity/evaluation outputs
```

Save code and data hashes, extraction prompt versions, dependencies, seeds, fold assignments, inclusion/exclusion reasons, frozen references, and per-observation predictions. Have another person reproduce key tables from a clean checkout with documented access requirements. A public package can reproduce permitted derived-data analyses without redistributing restricted source articles.

Use a working environment rather than the broken root `.venv`. After implementation changes, run the required main suites (`tests/test_offline.py`, `tests/test_scoring.py`, `tests/test_forecasts.py`) plus affected ProQuest suites. Add meaningful checks for corpus isolation, horizon parsing, semantic mappings, release-date eligibility, future-feature invariance, raw/verified lineage, and deterministic reproduction. Tests accompany implementation; this plan itself does not require model retraining.

## 12. Manuscript and publication package

Draft methods while doing validation so missing decisions become visible early. Build the paper around one central finding and its validity, not a catalog of every available plot.

Proposed main figures:

1. Corpus flow and coverage by newspaper/year.
2. Human validation, including error types and raw-versus-verified tradeoffs.
3. Target-specific accuracy relative to baselines on the strict and expanded samples.
4. Temporal stability, common-support comparisons, and dependence-aware uncertainty.
5. Modern incremental-information evaluation if supported; otherwise a well-motivated historical analysis.
6. Robustness and the effect of correcting measurement errors.

Tables: corpus/sample definitions, validated benchmark mapping, baseline/model comparison, and principal sensitivity estimates. Put extensive subgroup rankings and model variations in the supplement. Include source-audited illustrative forecasts, including failures, in a form permitted by access terms.

Write a data-availability statement, extraction/LLM-use statement, limitations, author-contribution statement, and reproducibility instructions. Agree on contributions and authorship with the original collaborators and mentor. Credit the summer collaboration and subsequent independent work accurately.

Use a mentor review and, if possible, one outside forecasting/economic-history methods review before submitting. Select the journal based on the final contribution and several recent comparable papers; verify current scope, submission requirements, data policy, costs, and preprint policy then. Professional forecasting journals are ambitious candidates; no specific acceptance probability or review deadline is assumed. Submit to one journal at a time unless its rules explicitly permit otherwise.

A preprint or working paper can make the finished work reviewable before journal acceptance, subject to coauthor agreement and the intended journal's policy. Describe it accurately as such. Keep the application milestone under your control: a completed, defensible manuscript and specific evidence of your role.

## 13. Semester execution plan

These are proposed milestones with Bode as the sole human annotator. Use the first week's small claim-review pilot to estimate hours and adjust sequencing. Collection, literature review, interface work, and writing can overlap; new outcome inspection must wait for the relevant freezes.

| Period | Main work | Concrete milestone |
| --- | --- | --- |
| Week 1 | Mentor meeting; literature map; production prompt/manifest recovery; local claim-review pilot | Written research question, contribution, rubric draft, and measured claim-review throughput |
| Week 2 | Revise rubric on pilot only; fix evaluation samples; set modern holdout rules; recover query denominators | Locked validation protocol and modern evaluation reservation |
| Weeks 3–4 | LOC model comparison; Bode grades about 400 LOC and 100 ProQuest claims | Model-reference coverage, separate source-specific grading results, initial error taxonomy |
| Weeks 4–5 | Finish validation; repair semantic scoring; raw/verified and sampling checks | Validation report and defensible strict-sample scoring contract |
| Weeks 5–7 | Recompute descriptive results; dependence/robustness work; model development folds | Stable tables or clearly diagnosed uncertainty; primary methods draft |
| Weeks 7–8 | Finish bounded model search and ablations; freeze final procedure | Saved model/specification hashes before modern evaluation |
| Weeks 8–9 | Evaluate eligible modern cohorts once; vintage checks; investigate failures without retuning the reported final test | Modern report, calibration, maturity and uncertainty tables |
| Weeks 9–11 | Draft manuscript/supplement; reproducibility pass; mentor and outside feedback | Complete paper and research package |
| Weeks 11–13 | Revise; finalize authorship and venue; submit if the paper meets its evidence claims | Submission or clearly labeled working paper; accurate application description |

Run longer extensions alongside this schedule only when they do not delay necessary validation. If an extension becomes the strongest contribution, explicitly revise the paper's scope and evaluation plan. Speed can come from automating repetitive work; human labels should remain insulated from model answers where practical, and unexamined outcome evaluation data should remain reserved.

## 14. Decision rules and the first ten tasks

Do not declare success using an arbitrary F1 cutoff. Judge whether the measured errors could plausibly explain or reverse the scientific conclusion. If they can, improve extraction/scoring, narrow the supported claim, or present the measurement problem as a result. A small audit with wide intervals may be inconclusive even when no obvious failure appears.

| Finding | Response |
| --- | --- |
| DeepSeek finds more candidates | Report model-reference coverage and use sampled human review to characterize disagreements |
| LOC performance is good | Report that result for LOC without treating it as measured ProQuest performance |
| Bode finds ambiguous horizons or forecast meaning | Preserve an unclear/unscorable category and document the interpretation rule |
| ProQuest grading exposes consequential errors, or plausible scenarios reverse the headline gap | Report direct audit evidence separately from hypothetical sensitivity and revise affected interpretations |
| Results depend on inferred horizons or proxy targets | Make that dependence explicit; use supported claims as the main population |
| GRU gains disappear under stronger controls or time blocks | Report that finding and emphasize the better-supported empirical contribution |
| Modern test contradicts historical development | Report the failure and explore explanations separately; later tuning requires another untouched evaluation |
| Absolute recall remains unknown | State the limitation and proceed with model-reference coverage and claim validity as the planned validation endpoints |

First tasks, in order:

1. Share this plan with the mentor: LOC model comparison plus single-annotator grading on LOC and a small ProQuest sample. The newer LOC recall packet is a pilot; decide whether independent page enumeration and adjudication will be added before reporting absolute recall.
2. Reserve modern outcomes from model selection and document any already viewed results.
3. Recover the actual extraction/verifier configurations and article-processing manifest from the VM.
4. Build the literature comparison and specify the primary empirical question.
5. Write the pilot rubric, including the target/horizon distinctions in Section 4.
6. Pilot local LOC grading and simple batch retrieval of existing ProQuest claims; measure review time per claim.
7. Fix the LOC comparison inputs and roughly 500-claim review allocation: 300 LOC probability-sampled, 100 LOC diagnostic, and 100 ProQuest probability-sampled claims.
8. Run GPT-4o-mini and DeepSeek separately; have Bode review sampled claims with model labels hidden where practical.
9. Measure reference-model coverage, accepted-claim validity, and field errors; document which interpretations remain provisional.
10. Freeze the main scoring and modeling specification before the modern evaluation, then execute the remaining work streams.

**Completion standard:** an informed reader can trace the sample, understand what each forecast was taken to mean, assess the extraction and scoring errors, reproduce the comparisons, and see where the evidence does or does not support generalization.
