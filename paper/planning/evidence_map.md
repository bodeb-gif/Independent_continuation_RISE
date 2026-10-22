# Evidence map for writing

October 20 update: this October 19 evidence map remains the historical analysis
inventory. Its pending source-validation and modern-data entries are superseded
by the [current evidence status](../../docs/publication/STATUS.md): 300 author-reviewed
claims (250 historical and 50 modern) and a separate exploratory modern model
evaluation are now available. The author confirmed on October 21 that the first human validation was completed
without AI assistance. See the [human review receipt](../../data/scored/proquest/source_review_additional150_v1/human_review_status.html)
and [modern results](../../data/scored/proquest/modern_analysis_v1/report.html).
Neither the new sample nor the modern model results resolves all source-measurement
uncertainty or establishes RNN superiority. No manuscript prose is added here.

Prepared October 19, 2026. This is a writing plan and evidence inventory, not
manuscript prose. The [older manuscript outline](../manuscript/outline.md) predates
several analyses and should not supply final numbers without this reconciliation.

The working question is: **How do interpretation and scoring choices change
what we conclude about economic forecasts reported in historical newspapers?**
The economic applications ask whether those forecasts add information beyond
simple directional or macroeconomic benchmarks. The current evidence supports
measurement sensitivity and uncertain predictive gains; it does not establish
source validity or RNN superiority.

Use the [evidence browser](../../data/scored/proquest/writing_evidence_v1/report.html),
[structured ledger](../../data/scored/proquest/writing_evidence_v1/ledger.json) and
[exact facts](../../data/scored/proquest/writing_evidence_v1/facts.csv). Each fact
has its source path, SHA256 and unique row selector or JSON path. Rebuild with
`python src/proquest_writing_evidence.py`; this reads existing results and does
not refit models or choose a new preferred benchmark.

## Proposed argument and exhibits

| Writing section | Evidence IDs and exhibit | What can be said now | What remains dependent on validation |
| --- | --- | --- | --- |
| Data and scope | E01; Table 1 corpus flow | 274,070 verified extracted claims, 175,855 scored; annual ProQuest 1900–2010 | Source validity, retrieval success and processing denominators. “Verified” is a machine-filter status. |
| Measurement contract | E02; Table 2 original scores | Original article-weighted accuracy 40.90%, fixed-direction benchmark 53.60% | Whether target, direction and horizon match the actual source forecast; these are conditional legacy scores. |
| Outcome interpretation | E03; Figure 1 and Table 3 | On 9,260 matched employment claims, original / duration-scaled / sign-only accuracies are 34.23% / 43.19% / 57.64%. The flat benchmark changes too. | Which rule is appropriate. Showing sensitivity is not grounds to select the highest accuracy. |
| Alternative real-world targets | E04–E05; Table 4 | Payroll versus unemployment labels disagree about 21.95%; GDP versus quarterly IP about 14.33%, under the recorded matched-support weights. | Which quantity the source actually forecast. Neither disagreement is an extraction-error rate. |
| Economic usefulness | E06–E07; Table 5 with crisis exclusion beside the main estimate | Aggregate six-month IP Brier improves by 0.0099; interval −0.0637 to +0.0808. Removing 2007–2009 reverses the Brier ranking. | Source-supported aggregation and independent generalization; neither gain nor absence of gain is established precisely. |
| Source audit | E11; reserve Table 6 without fabricated cells | A fixed 12-record pilot and a prepared review interface | Actual human evidence. After pilot/rubric freeze, draw the planned main sample; report unresolved cases and all-sampled bounds. |
| RNN and polarization | E08, E12; Appendix A | Original RNN Brier 0.1929; primary paired permutation p-values 0.3125 and 0.2500, Holm 0.50. Separate polarization inputs do not improve its average Brier. | No claim of 0.05 significance, causal polarization effects or a validated extraction pipeline. |
| Input ablations | E09–E10; Appendix B | Matched historical RNN mean Brier falls from 0.1992 to 0.1910 with production, but metadata logistic without macro inputs scores 0.1743. Keep all four input arms. | No promotion or fresh test: the four 1975–1994 eras were already exposed. |

Proposed table and figure numbers are organizational placeholders. Final
publication exhibits still need layout, captions and journal requirements.
Canonical [tables](../tables/README.md) and [figures](../figures/README.md) stay in
their existing result folders; do not create independent copies of their numbers.

## Keep the three prediction tasks distinct

| Task | Prediction and unit | Appropriate comparator | Score and interpretation |
| --- | --- | --- | --- |
| Reported economic forecast | Claim direction against a chosen real-world endpoint | Fixed economic direction on identical claims/targets; all constant comparators in sensitivity results | Directional accuracy; benchmark-minus/forecast-minus signs must be stated |
| Claim-correctness model | Probability that the legacy scorer will mark a claim correct | Metadata logistic, history logistic and prevalence on identical claims and eras | Binary Brier 0–1, AUC, calibration; not the probability that the extraction is semantically valid |
| Aggregate macro forecast | Monthly probabilities of IP falling, flat or rising at six months | Macro-only and recent base-rate models on identical forecast months | Summed three-class Brier 0–2; not directly comparable with binary Brier |

Article weighting, publication-time dependence, overlapping outcome horizons and
revised versus historical-vintage labels belong in each methods description.
Exploratory block-bootstrap intervals are conditional on the scoring contract;
they do not cover uncertainty about semantic interpretation or all researcher
choices. The four-block permutation test has only 16 assignments, so even its
minimum exact one-sided p-value is 0.0625. Shorter blocks cannot be selected to
manufacture a significance threshold.

## How the audit enters the paper

The [review interface guide](../../validation/proquest_review/README.md) implements
the existing [review protocol](../../docs/publication/REVIEW_PROTOCOL.md). The
pilot establishes retrieval feasibility and reveals rubric ambiguity. It is
not a corpus-level validity estimate. The later main audit estimates quality
among scored extracted candidates, not missed forecasts or the whole press.

For the main sample, preserve mapping failures and exclusions, record genuine
forecast validity, field validity and joint usability, and compare original
with source-supported scoring on identical eligible records. This connects the
measurement argument to observed evidence. Do not multiply corpus accuracy by
a global validity percentage or treat LOC extraction validation as ProQuest
source validation. One annotator supplies no human-human agreement estimate.

## Literature placement and claims to avoid

The [15-study comparison](../references/literature.md) places Mathy–Stekler and
Mathy–Roatta nearest the historical interpretation question; Bybee et al.,
Balke–Petersen and Barbaglia et al. nearest the incremental-information question;
and Shapiro et al., Grimmer–Stewart and Croushore–Stark nearest validation and
timing. These are literature comparisons, not head-to-head model evaluations.

The paper should not claim the first historical newspaper forecast study, the
first long-run text index, a superior RNN, a causal effect of polarization, or
validated source-level forecast error rates. Political polarization, forecast
disagreement, negative sentiment and economic policy uncertainty are different
constructs. The two existing polarization measures remain separate.

## Remaining evidence dependencies

| Dependency | Unlocks | Current status |
| --- | --- | --- |
| Authorized article context and VM claim lineage for the 12 pilot records | Human interpretation and retrieval feasibility | Prepared interface; no source judgments entered |
| Pilot completion, rubric freeze and main-sample draw | Main ProQuest validity estimates and audited scoring effects | Deferred; do not silently replace inaccessible observations |
| VM processing logs, denominators and export lineage | Coverage and selection accounting | Export reconciliation alone does not establish processing completeness |
| New annual exports and exposure declaration | Frozen modern evaluation | Existing corpus ends in 2010; do not manufacture a modern result |
| Final-version and remaining full-method literature checks | Submission-ready citations and defensible contribution wording | 15 studies compared; inspection level recorded per entry |

Negative and inconclusive results stay with their favorable counterparts. The
candidate-tuning reports remain documented in the results index, but do not
replace the original model's evaluation. Drafting can follow this map once the
user resumes manuscript work; no new paper text is written here.
