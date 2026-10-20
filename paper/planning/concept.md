# Economic forecasts in selected US newspapers

## Paper concept

Working title: *Economic Forecasts in Selected U.S. Newspapers, 1900–2010: Measurement, Accuracy, and Predictive Information.*

Economic forecasts reported in newspapers provide a record of expectations, but evaluating them requires decisions about what was predicted, when it was expected, and which outcome can test it. A forecast of slowing growth is different from a forecast of falling output; a reported quotation is different from an editorial position. This paper asks how those distinctions affect measured forecast performance and whether aggregated forecasts contain information beyond the available reconstructed macroeconomic information set.

The study has three questions. First, does source review support the pipeline's identification of forecasts and interpretation of their quantity, direction, scope, and horizon? Second, how do interpretable forecasts perform against a fixed-direction alternative on identical targets and horizons? Third, do monthly newspaper signals improve six-month industrial-production direction predictions beyond a selected simple macro model?

The population is the material returned by the ProQuest retrieval design, restricted to the annual 1900–2010 exports. The exact query, retrieval limits, and processing completeness still need a VM manifest. The machine-verified set contains 274,070 claims; current rules score 175,855. The 488,660 raw claims supply a sensitivity comparison. LOC provides separate extraction-validation evidence and contributes no economic estimates to this paper. Modern extraction is outside the active population.

## Proposed contribution

Historical business-press forecasts and long-run news-based macroeconomic information already have direct predecessors. The [literature comparison](../references/literature.md) places the project beside Mathy and Stekler, Mathy and Roatta, and Bybee and coauthors. Our proposed contribution is a source-audited account of how target and horizon interpretation change the apparent performance of explicit forecasts, coupled with a separate aggregate information test. Its value depends on measured interpretation errors and their consequences, rather than corpus size or the use of an LLM.

This contribution is conditional on the audit. If source matching cannot support reliable individual scoring, the paper must narrow its conclusions. If the validated sample is too small to resolve the effect of interpretation errors, it should report that uncertainty rather than imply corpus-wide correction. A descriptive measurement paper remains possible without a positive forecasting result, but requires a demonstrated substantive finding.

## Existing evidence and interpretation

Under current legacy rules, pooled correctness is 40.8%, versus 53.6% for the fixed-direction baseline. Giving each scorable article equal weight yields 40.9% correctness and a −12.7 percentage-point baseline gap. These comparisons concern the recovered claims under the documented proxies and horizon assumptions. They do not establish the skill of the whole press or the failure of every topic: the current employment comparison is favorable to newspaper calls, although its unemployment proxy needs source validation. Exact values and denominators are in the [evidence packet](../../data/scored/proquest/publication/evidence.json).

The monthly experiment evaluates 408 origins in 1977–2010. Adding newspaper signals reduces multiclass Brier loss from 0.6327 to 0.6228, an improvement of 0.0099. The paired five-year-block interval is −0.0637 to +0.0808. Excluding 2007–2009 evaluation months reverses the Brier improvement. Stable incremental predictive skill is therefore not established. The wide interval also cannot establish the absence of useful information. The monthly task predicts endpoint IP direction, not recession onset or the correctness of each source claim.

## Evidence needed for the paper

The agreed human-validation design starts with approximately 100 scored ProQuest claims reviewed by Bode, alongside separate LOC work. A twelve-record source-recovery pilot will refine the rubric before drawing that fixed probability sample. Human interpretation should precede machine-label comparison and outcome inspection. The audit must distinguish an authentic forecast from a jointly usable target, direction, and horizon. Unresolved source mappings remain unresolved and cannot be silently replaced by easier cases.

The main exhibits will connect corpus flow and newspaper coverage to source interpretation, legacy and strict descriptive estimates, matched predictive results, and stability/calibration. Current tables are placed in the [manuscript outline](../manuscript/outline.md). The strict set requires source evidence; exported numeric horizons alone cannot establish eligibility.

The preliminary route follows the publication plan's measurement emphasis and low-cost preference. Final venue choice follows validation and the contribution assessment. Near-term work requires source lineage, processing provenance, human review, and a documented access path. Authorship, venue, and final manuscript approval remain decisions for the authors and mentor.
