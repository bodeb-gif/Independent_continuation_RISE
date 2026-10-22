# Low-Cost Extraction of Economic Forecasts from Newspapers

## Human Validation, Measurement Sensitivity, and Predictive Applications

Draft outline prepared October 20, 2026. This outline develops the low-cost
extraction method as a main contribution alongside measurement findings and
economic applications. It preserves the [earlier outline](outline.md).

**Central question:** Can inexpensive language-model extraction produce useful
economic forecast data at scale, and how do extraction and interpretation
choices affect what we learn from those data?

**Evidence distinction:** The existing cost comparisons come from the separate
LOC extraction experiments. The 300 human reviews evaluate ProQuest claims.
Both belong in the paper, but costs and quality estimates must remain attributed
to their respective pipelines. LOC evidence serves extraction validation only;
LOC economic results and old crisis-window exports are not pooled into the
annual ProQuest analysis.

## 1. Introduction: making historical expectations affordable to study

Explain why newspaper forecasts are valuable: they record expectations,
uncertainty, and disagreement before outcomes occur. Extracting structured
forecasts manually across decades is labor-intensive.

Introduce three contributions:

- An inexpensive, reproducible approach to extracting structured economic claims.
- Human evidence about which extracted claims and fields are reliable.
- Evidence that target definitions and scoring choices substantially affect
  economic conclusions.

Present predictive modeling as an application of the resulting data. The paper's
contribution does not depend on establishing RNN superiority or predicting a
recession successfully.

## 2. Data and extraction pipeline

Describe the annual ProQuest historical corpus, **1900–2010**, and the separate
modern extension, **2011–2026**. Explain newspaper coverage, retrieval,
extraction, machine verification, and source-linked identifiers.

Walk through the extraction workflow:

1. Retrieve article text in the authorized source environment.
2. Extract candidate forecasts and structured labels.
3. Apply machine verification.
4. Preserve claim-level lineage and export permitted categorical data.
5. Apply explicit analysis-eligibility and outcome-maturity rules.

Explain the important fields: topic, direction, horizon, geographic scope,
speaker, confidence, and present conditions. Distinguish a genuine forecast
from commentary about current conditions.

**Proposed exhibit:** A pipeline diagram and corpus-flow table showing claims
retained, rejected, unsupported, and awaiting mature outcomes.

**Evidence:** [Historical analysis](../../docs/PROQUEST_ANALYSIS.md),
[modern intake receipt](../../data/scored/proquest/modern_export_20261020/README.md),
and [modern scope amendment](../../docs/publication/MODERN_ANALYSIS_AMENDMENT_20261020.md).

## 3. Extraction cost and quality: a central methods result

Give this a substantial main-text section.

The existing LOC development comparison records approximately **$27 projected
cost for 23,000 pages** using extraction plus self-verification, with **F1 0.636**,
versus approximately **$404 and F1 0.784** for the higher-quality configuration.
Those are historical projections based on measured token usage, evaluated
against a small **model-adjudicated reference**, not human gold. The reference
contains 16 pages and 52 claims; the accompanying boundary-case exercise contains
44 decisions. These are development results, not population-level quality
estimates or current price quotations.

The contribution is a demonstrated **cost–quality tradeoff**: considerably
cheaper configurations can retain useful extraction capability while accepting
measurable errors.

Include:

- Extraction and verification costs separately.
- Actual expenditure versus projected expenditure.
- Cost per 1,000 pages or articles, with units clearly identified.
- Precision, recall, and F1 where the reference supports them.
- Human review time, access costs, retries, and infrastructure as separate costs.

**Proposed exhibit:** A cost–quality comparison plot, with reference provenance
and measured-versus-projected costs visible in the caption.

**Before submission:** Reconcile the full ProQuest usage ledger. Avoid assigning
the LOC cost or F1 to the ProQuest pipeline. A direct comparison of cheaper and
more expensive extractors on a common human-annotated sample would strengthen
the affordability claim.

**Evidence:** [Extraction comparison](../../validation/gold_extraction/RESULTS.md),
[reference annotation protocol](../../validation/gold_extraction/PROTOCOL.md),
and [cost calculation code](../../validation/gold_extraction/cost_table.py).

## 4. Human validation: useful quality, with identifiable weaknesses

Describe **two human reviewers evaluating the same 300 claims**: 250 historical
and 50 modern, as confirmed by the author on October 22, 2026. The author
confirmed the first review was completed without AI assistance. Explain each
reviewer's documented label exposure; do not describe the entire design as fully
blinded. Inter-reviewer agreement has not yet been calculated. Reviewer 2
includes 171/250 historical and 33/50 modern candidates (204 include, 96 exclude).

Report the sampling designs separately. In the first reviewer's sample, **212 claims
were included, 87 excluded, and one unclear**. This pooled count describes the
reviewed sample; it is not a common-population validity estimate.

For the 35 modern claims included by the first reviewer, machine-label agreement is:

| Field | Agreement with human review |
| --- | ---: |
| Topic | 29/35 — 82.9% |
| Direction | 29/35 — 82.9% |
| Horizon | 26/35 — 74.3% |
| Scope | 24/35 — 68.6% |

Explain what useful extraction quality means operationally: relatively strong
agreement on some fields, with weaknesses that matter for downstream analysis.
Claim validity, field agreement, recall, and economic accuracy are different
quantities. Positive-candidate review does not establish recall. Preserve the
original batch's current-state coding limitation rather than pooling that field
across incompatible conventions.

**Proposed exhibit:** Validation results by period and field, plus representative
error categories.

**Evidence:** [Combined human-review status](../../data/scored/proquest/source_review_additional150_v1/human_review_status.html),
[additional-batch results](../../data/scored/proquest/source_review_additional150_v1/summary.json),
and [original-batch reconciliation](../../data/scored/proquest/source_review_150_v1/human_reconciliation_summary.json).

## 5. Measurement choices change the economic conclusions

Make this the principal empirical finding.

On **9,260 matched historical employment claims**, accuracy changes from
**34.2% to 43.2% to 57.6%** across the recorded original, duration-scaled, and
sign-only scoring rules. Payroll versus unemployment benchmarks disagree on
approximately **22%** of matched outcomes under the recorded weighting.

Explain the underlying distinctions:

- Employment growth versus falling unemployment.
- Slower growth versus declining output.
- Lower inflation versus falling prices.
- A broad outlook versus a dated endpoint forecast.

Compare each rule with its corresponding baseline on identical observations.
Higher measured accuracy alone cannot establish which interpretation is correct.
Use human source review to explain plausible interpretation errors without
claiming the entire corpus has been corrected or strictly validated.

**Proposed exhibit:** Matched-sample scoring comparisons, supported by
source-grounded examples that can be reproduced or displayed under the
applicable source-access terms.

**Evidence:** [Evidence map](../planning/evidence_map.md),
[exact historical evidence ledger](../../data/scored/proquest/writing_evidence_v1/facts.csv),
and [analysis specification](../../docs/publication/ANALYSIS_SPEC.md).

## 6. Predictive applications and modern generalization

Keep two tasks explicitly separate.

### 6.1 Predicting claim correctness

The frozen RNN achieves modern **AUC 0.738**, compared with **0.654** for the
metadata-plus-history logistic control, on 56,886 mature, supported claims.
Both political polarization and forecast disagreement together raise the
observed RNN AUC to **0.749**, with uncertain improvement. These two polarization
measures represent different constructs and remain separate inputs.

Highlight the primary RNN's topic differences:

| Topic | Modern AUC |
| --- | ---: |
| Prices | 0.906 |
| Markets | 0.788 |
| General business | 0.767 |
| Employment | 0.306 |

Topic-specific failure is an important result. Explain that the prediction
target is correctness under the documented scoring contract, not extraction
validity or recession probability. Report Brier scores, calibration, baselines,
and paired time-block uncertainty alongside AUC. Describe modern evaluation as
exploratory because prior outcome exposure remains undocumented.

### 6.2 Predicting aggregate downturns

Present aggregate economic forecasting as a separate application. Compare
newspaper-based probabilities with base-rate benchmarks and distinguish the
historical macro-benchmark exercise from the modern downturn exercise, which
does not yet supply a matched macro-only comparison.

Explain the limited number of independent recession events and overlapping
forecast horizons. The modern recession evaluation contains only one distinct
onset; paired block intervals do not establish the selected models' gains.

Place the dated 2026 forecast in a short demonstration box or appendix:
the selected models estimate **6.9% recession-onset risk** and **28.0%
industrial-production-decline risk** for September 2026–August 2027, using
newspaper coverage through August 2026. This is not an October-origin forecast
or an observed forecasting success. Candidate recession estimates vary, and the
selected production-decline estimate is essentially its historical base rate.

**Proposed exhibits:** Model comparison and topic-performance figure in the
main text; forecast timelines, full polarization ablations, and dated risk
estimates in the supplement.

**Evidence:** [Modern evaluation](../../data/scored/proquest/modern_analysis_v1/report.html),
[claim metrics](../../data/scored/proquest/modern_analysis_v1/claim_metrics.csv),
[downturn results](../../data/scored/proquest/modern_analysis_v1/downturn/summary.json),
and [historical macro-benchmark study](../../data/scored/proquest/macro_benchmark/report.html).

## 7. Discussion and conclusion

Develop the paper's practical message: inexpensive extraction can make
large-scale expectations research feasible, but useful economic measurement
requires targeted human review and explicit definitions of what counts as a
correct forecast.

Discuss coverage changes, extraction errors, limited recall evidence, revised
outcome data, and uncertainty in predictive gains. Avoid claiming a universal
extraction accuracy, a causal effect of polarization, or established RNN
superiority.

End with the most useful extensions: direct human evaluation of cheaper and
more expensive extractors on the same documents, complete cost accounting,
and prospective evaluation of frozen forecasts.

## Proposed emphasis

Give **extraction cost and human validation substantial space**, with measurement
sensitivity as the main economic finding and the RNN as a revealing application.
The affordability result is integral to the argument: it explains why the data
can be assembled at scale, while the validation and interpretation results
establish the conditions under which those data are useful.

The related-literature discussion should connect this contribution to historical
forecast interpretation, economic text measurement, and application-specific
validation. Use the [existing literature comparison](../references/literature.md)
as a starting point; its recorded inspection levels and remaining source checks
still apply.
