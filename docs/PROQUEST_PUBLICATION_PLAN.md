# ProQuest research publication plan

Prepared October 14, 2026. Journal policies and prices below were checked on that date and should be checked again before submission. This is a proposed publication program, not a record of completed validation or a preregistration.

**Recommendation:** develop one full empirical paper on the measurement, accuracy, and incremental information of economic forecasts reported in the selected ProQuest newspaper corpus. Journal of Computational Social Science is the strongest initial fit for a measurement-centered paper. Eastern Economic Journal is a plausible economics route. Journal of Business Cycle Research becomes attractive if the monthly forecasting question becomes the central contribution. None is an assured acceptance, and the current project still needs source-grounded validation before submission.

**Budget preference:** the author wants an inexpensive publication route. Prioritize journals with no mandatory APC and modest or no submission fees. Do not select optional paid open access. PLOS ONE and Cogent Economics & Finance are outside the default submission sequence unless a confirmed waiver or institutional funding covers the publication charge. No exact personal spending limit has been specified, and this plan does not authorize spending.

The publication case should rest on a useful, defensible measurement exercise and a substantive economic question. It should remain coherent if the incremental forecasting result stays small or uncertain. More model complexity is not the immediate priority.

## 1 Current position and the paper we can defend

The active corpus is the annual ProQuest export for 1900–2010: 274,070 machine-verified claims, with 175,855 scored under the current descriptive rules. The raw annual exports are a sensitivity set. LOC supports extraction validation only; its claims, outcomes, page denominators, and older crisis-window results do not enter ProQuest estimates.

“Machine-verified” must remain distinct from “human-validated.” The approximately 40,000 claims currently being verified should be described by their actual processing stage and source years. Their existence does not establish that 40,000 claims have received human review or that they belong to the present 1900–2010 analysis. Reconcile that queue with the publication manifest before changing any manuscript sample count.

The repo already supplies substantial analysis infrastructure. The latest benchmark gives the following results on the same 408 monthly origins in 1977–2010:

| Model | Multiclass Brier score | Log loss | Direction accuracy |
| --- | ---: | ---: | ---: |
| Recent historical class frequencies | 0.6443 | 1.0373 | 42.2% |
| Selected simple macro model | 0.6327 | 0.9989 | 35.8% |
| Same macro specification plus newspaper signals | 0.6228 | 0.9606 | 44.1% |

The incremental newspaper Brier improvement is 0.0099, with a paired five-year-block 95% interval of −0.0637 to +0.0808. Excluding 2007–2009 from evaluation reverses the Brier improvement: macro-only scores 0.6164 and macro plus newspapers 0.6214. That exclusion changes the evaluation subset; it does not remove crisis observations from all later model training. The short CPI extension has only 108 evaluation months and weak support for inference.

These results support an honest statement that the current historical experiment does not establish stable incremental forecasting skill. They do not establish that newspaper information has zero value. The uncertainty is too wide for that conclusion.

The Brier implementation sums squared probability errors across three classes, giving a range of 0–2; a uniform three-class forecast scores 2/3. It is not directly comparable to the binary correctness model's Brier score. A score of 0.6228 is about a 1.6% reduction relative to the 0.6327 macro benchmark, not a dramatic breakthrough. The manuscript should explain the score convention and emphasize matched baselines and uncertainty.

The descriptive 40.8% pooled hit rate versus 53.6% for the fixed-direction baseline is a different estimand. With equal article weights, verified accuracy is 40.9% and the baseline gap is −12.7 percentage points. Neither result establishes that the whole press was unskilled: query selection, target proxies, inferred horizons, and reported-versus-endorsed forecasts matter.

Internal evidence: [active analysis documentation](PROQUEST_ANALYSIS.md), [selected benchmark summary](../data/scored/proquest/macro_benchmark/summary.json), [selected benchmark report](../data/scored/proquest/macro_benchmark/report.html), and [raw versus verified report](../data/scored/proquest/robustness/report.html).

**Proposed working title:** *Economic Forecasts in Selected U.S. Newspapers, 1900–2010: Measurement, Accuracy, and Predictive Information.*

Use three research questions:

1. How accurately can the extraction and scoring procedure recover the meaning of published economic forecasts?
2. How do interpretable forecasts perform against simple alternatives on matched targets and horizons within the sampled corpus?
3. Do aggregated newspaper signals improve monthly economic predictions beyond the available historical macro information?

The first two can carry a focused paper if the third remains inconclusive. Keep the GRU correctness experiment, extensive publisher rankings, and many crisis illustrations in the supplement or a later research program unless they directly answer the central question. Claim correctness and future macroeconomic direction are different prediction tasks.

## 2 Establish the contribution against the closest research

The project cannot claim that historical press forecasts have never been evaluated. Mathy and Stekler studied contemporary business-press expectations during the Great Depression; Mathy and Roatta examined forecasts around the 1937–1938 recession. These are direct predecessors, not peripheral citations. Start with the [published Great Depression article](https://www.sciencedirect.com/science/article/pii/S0164070416301446) and the [1937–1938 working paper](https://www2.gwu.edu/~forcpgm/2018-004.pdf).

News-based macroeconomic information is also an established field. Bybee, Kelly, Manela, and Xiu's 2024 paper studies a large WSJ corpus, macroeconomic forecasting, and a historical extension reaching back to 1890. A long date range alone therefore cannot carry our novelty claim. Our potential distinction is the explicit forecast as the unit of measurement, its target and horizon, and the consequences of interpretation errors. See [Business News and Business Cycles](https://doi.org/10.1111/jofi.13377).

Shapiro, Sudhof, and Wilson provide a useful comparison for validating economic news sentiment against human judgments. Their measure is sentiment, whereas our intended object is an attributable forward-looking claim with an assessable outcome. See [Measuring News Sentiment](https://www.frbsf.org/research-and-insights/publications/working-papers/2020/03/measuring-news-sentiment/). Use [Gentzkow, Kelly, and Taddy's Text as Data](https://www.aeaweb.org/articles?id=10.1257%2Fjel.20181020) to situate the measurement design.

Build a matrix of roughly 15–25 closely relevant studies, prioritizing these direct comparisons. Columns should cover corpus and sampling, date range, forecast versus sentiment, annotation evidence, target/horizon, print-time availability, baselines, evaluation dependence, and reusable materials. Read full papers before making a detailed novelty claim; abstracts are sufficient only for initial screening.

The introduction needs a precise paragraph answering: what can a reader learn from this study that those papers do not already establish? Possible answers include systematic evidence about horizon and target mismatch, changes in apparent performance after source validation, or differences between individually inaccurate calls and useful aggregate signals. Each needs evidence. “We processed more claims with an LLM” is not enough by itself.

**Completion criterion:** the mentor and authors can identify the nearest three papers and state one substantive contribution without using “first ever,” corpus size alone, or unsupported claims about AI superiority.

## 3 Journal shortlist and realistic fit

“Plausible” below means a credible venue to prepare toward after the necessary work. It does not mean the present repository is submission-ready or that an acceptance probability is known. Venue assessments are judgments based on scope, format, and this project's evidence. They are not statements from editors.

| Journal | Assessment for this project | What the paper would need to emphasize |
| --- | --- | --- |
| Journal of Computational Social Science | Preferred first target for a measurement-centered full paper | Validated extraction, transparent measurement decisions, and a social-science finding that survives error analysis |
| Eastern Economic Journal | Plausible general economics target | A clear economic question, interpretable matched comparisons, and readable implications beyond the pipeline |
| Journal of Business Cycle Research | Plausible conditional specialist target | Monthly information content, credible real-time benchmarks, and what the results teach about economic fluctuations |
| Cogent Economics & Finance | Funding-only alternative; excluded from the default low-cost route | A complete empirical contribution with transparent limitations and reproducibility |
| PLOS ONE | Funding-only alternative; excluded from the default low-cost route | Strong measurement validity and technically sound inference, including an uncertain or negative result |
| Economics Bulletin | A possible short-paper route after substantial narrowing | One self-contained economic finding that fits its brief format |
| Historical Methods | Conditional methods route, not the default fallback | A transferable methodological innovation demonstrated through historical sources |
| International Journal of Forecasting | Stretch target for a later, stronger forecasting version | A compelling forecasting contribution, demanding controls, and credible evaluation/reproduction |

**Journal of Computational Social Science.** Its scope expressly includes economics, artificial intelligence, text analytics, and computational analysis of social phenomena. That aligns well with this project's combination of measurement and economic evaluation. My main concern would be whether the paper offers a substantive insight beyond using standard tools on a new corpus. [Official scope](https://link.springer.com/journal/42001/aims-and-scope).

The subscription publication route has no article processing charge (APC). Optional open access currently lists US$3,390, before applicable taxes. No-APC does not mean every possible ancillary charge has been ruled out; check the final submission conditions. [Publishing options](https://link.springer.com/journal/42001/how-to-publish-with-us).

**Eastern Economic Journal.** It welcomes empirical and methodological economics and explicitly values readability and general interest. A concise account of what the press record does and does not reveal about expectations could fit. The paper must explain economic relevance rather than make its software architecture the main result. [Official scope](https://link.springer.com/journal/41302/aims-and-scope).

Its submission fee is currently US$30 when at least one author is an Eastern Economic Association member, or US$90 otherwise; the latter includes a year's membership for the corresponding author. Final formatting includes an abstract of at most 100 words. [Author guidelines](https://link.springer.com/journal/41302/submission-guidelines). Subscription publication has no APC; optional open access currently lists US$3,290. [Publishing options](https://link.springer.com/journal/41302/how-to-publish-with-us).

**Journal of Business Cycle Research.** Its remit includes measuring, monitoring, and forecasting economic fluctuations and developing economic indicators. This is a direct subject fit for a paper centered on the monthly press signal. [Official scope](https://link.springer.com/journal/41549/aims-and-scope). A recent example, [Nowcasting GDP Through the Lens of Economic States](https://link.springer.com/article/10.1007/s41549-026-00130-9), incorporates news-based indicators into a forecasting study. That demonstrates audience relevance, not equivalent methodological strength or likely acceptance for our paper.

The strongest version for this journal would explain why explicit expectations differ from sentiment measures, confront the limited historical macro information set, and provide a useful conclusion even without significant forecast gains. Subscription publication has no APC; optional open access currently lists US$3,290. [Publishing options](https://link.springer.com/journal/41549/how-to-publish-with-us).

**Cogent Economics & Finance.** Its broad economics and finance scope includes empirical work and replication. It is a reasonable option for a careful applied study with modest claims. [Official journal page](https://www.tandfonline.com/journals/oaef). It publishes open access and may charge an APC; the official author page directs authors to its APC finder. Obtain an actual current quote and check institutional coverage before selecting it. Do not budget using an old advertised Cogent price. [Author information and fee guidance](https://www.tandfonline.com/action/journalInformation?journalCode=oaef&show=instructions).

**PLOS ONE.** It considers relevant social-science research and explicitly includes negative and null results. This makes it a possible destination if the strongest outcome is a validated measurement study with limited predictive gains. The evidence must still support the conclusions and be reproducible. [Publication criteria](https://journals.plos.org/plosone/s/criteria-for-publication).

The current standard article fee is US$2,477; institutional arrangements or assistance may reduce it. Fee assistance must be requested at submission. [Official fees](https://plos.org/fees/). Restricted third-party data are not an automatic exclusion: the policy requires a proper access statement and a route for other researchers to obtain the data, subject to its permitted restrictions. [Data availability policy](https://journals.plos.org/plosone/s/data-availability).

**Economics Bulletin.** Its peer-reviewed Notes, Comments, and Preliminary Results are limited to seven printed pages excluding tables, figures, and references under the current submission page. It could fit a sharply focused result about forecast scoring or incremental information, but the entire present project would be too diffuse. Its instructions also tell authors to wait at least four months before requesting a status update, so it should not be treated as a guaranteed fast route. [Submission instructions](https://www.accessecon.com/pubs/eb/default.aspx?page=Newsubmission). The mission describes free scientific communication, but confirm current author charges before treating that as a complete fee guarantee. [Mission](https://www.accessecon.com/pubs/eb/default.aspx?linkID=763&menu=2&page=content).

**Historical Methods.** This is a good subject match only if the contribution becomes methodological. Its scope expressly excludes research articles that merely apply established computational, spatial, and statistical methods. It seeks developed articles of approximately 7,000–10,000 text words and encourages reusable code and data. [Official scope and format](https://www.tandfonline.com/journals/vhim20/about-this-journal). A strong submission would need to demonstrate a general solution to historical forecast interpretation or validation, with evidence that other researchers could use it. Current fees would need separate confirmation before choosing this route.

**International Journal of Forecasting.** Its remit includes forecasting methods, applications, and evaluation. It also requires data/code sharing unless an acceptable exception applies and conducts reproducibility checks. [Society journal page](https://forecasters.org/ijf/). Treat it as a stretch because the present incremental result is uncertain, the benchmark information set is limited, and the years have been repeatedly examined. Stronger identification of measurement error or a genuinely unexamined evaluation could improve the case; a significant result is not the only possible contribution. Fees should be checked if this becomes the chosen venue.

**Student-journal alternative.** If undergraduate eligibility fits, Issues in Political Economy is an established undergraduate economics outlet. [Journal description](https://www.elon.edu/u/academics/business/ipe/). Its current regular deadline is January 30, 2027, for the summer 2027 volume; it requests faculty-sponsor information and an AI-use disclosure. [Submission instructions](https://www.elon.edu/u/academics/business/ipe/about-the-journal/journal-submissions/). Eligibility must be checked against the authors' actual status; a high-school affiliation is not automatically undergraduate eligibility. This is a different publication route from professional-journal peer review and should be described accurately.

The default strategy does not depend on a student journal or a large publication budget. No acceptance percentages are assigned: journal-wide rates would not estimate this manuscript's probability of acceptance.

## 4 Choose a submission route before writing the final draft

Use the evidence to select one of these routes after the validation pilot and literature comparison:

| Final emphasis | First submission | Next option after revision and a closed decision |
| --- | --- | --- |
| Computational measurement with economic findings | Journal of Computational Social Science, subscription route | Refocus for Eastern Economic Journal if the economic contribution fits |
| Economic interpretation of reported expectations | Eastern Economic Journal, subscription route | Journal of Business Cycle Research if the emphasis fits; Economics Bulletin only if a coherent shorter paper is possible and charges are confirmed |
| Monthly economic information and forecasting | Journal of Business Cycle Research, subscription route | Eastern Economic Journal, with a revised framing |
| General methodological innovation for historical sources | Historical Methods | Journal of Computational Social Science |

Do not send a paper through all eight journals mechanically. A rejection about unreliable labels requires better evidence; a rejection about audience fit may require a different introduction and emphasis. Neither is solved by replacing the journal name on the cover letter.

Before the first submission, read three to five recent papers in the selected journal and identify two that share the intended article type or empirical style. The single business-cycle example above is a starting point, not a completed content survey. Recheck length, anonymity, supplement, data, preprint, AI-use, and fee rules against the final journal. A concise presubmission inquiry may help resolve scope or restricted-data questions if the journal accepts them, but sending one is a separate action for the authors.

## 5 Make the existing validation work usable in a paper

The existing [research plan](RESEARCH_PLAN.md) records Bode as the sole human annotator, with approximately 500 claim reviews: 400 LOC claims across probability and diagnostic samples, plus 100 ProQuest claims. Preserve that agreed starting design. A second annotator and ProQuest page-wide recall study are possible strengthening steps, not assumed commitments or mandatory new workloads.

First establish what the ongoing 40,000-claim verification job actually supplies: machine verification, human claim review, or both; its population; its sampling; and the available source anchors. A large machine queue does not replace the smaller human audit. If substantial human work already exists, recover its records and assess their applicability before requesting more annotation.

For the ProQuest audit, each sampled row needs a stable source-local record address, article identifier, publication date, permitted source context, original machine labels, human interpretation, error category, and sampling probability. Current stripped labels cannot reliably identify the underlying forecast on their own. When multiple candidate passages fit, record an unresolved mapping instead of guessing.

Use a pilot batch to refine the rubric, then a separate fixed probability sample for reported error rates. Record whether the text is a forecast at all, its quantity, direction, geographic scope, horizon, condition, attribution, and whether the selected outcome measures its meaning. Hide machine answers and realized economic outcomes until the initial human interpretation is saved where practical.

Report accepted-claim validity, each field's correctness, and joint usability for scoring. A real forecast with a wrong horizon is not a fully valid scored observation. Keep diagnostic oversamples separate from population estimates unless inclusion probabilities support weighting. Use article-aware uncertainty and disclose the single-annotator design; do not report human-human agreement from model-human comparisons.

The 100-claim ProQuest audit is a reasonable starting audit, but it cannot precisely establish quality across every newspaper, decade, and topic. As a scale illustration, 100 independent random observations yield an approximate worst-case 95% margin of error of ±9.8 percentage points for a proportion; 400 yield ±4.9 points. Clustering and unequal sampling change those figures. They are planning arithmetic, not a mandate to review 400 or evidence that a particular error rate is acceptable.

Decide on any expansion after the pilot, using measured review time and the uncertainty relevant to the main conclusion. If the audit is too small to establish that a modest model gain survives plausible errors, keep that claim uncertain. Prioritize ProQuest evidence over accumulating more LOC agreement for a ProQuest paper.

Accepted-claim review measures validity among extracted candidates, not missed forecasts. If no ProQuest page enumeration is undertaken, explicitly leave absolute recall unknown and frame the study around recovered forecasts. A broader retrieval sample and independent enumeration would strengthen claims about completeness or the overall press, but are not prerequisites for a narrowly framed paper. A second model's output is a reference comparison, not ground truth.

**Completion criterion:** the paper can show direct ProQuest audit results with source-grounded judgments, honest uncertainty, and a clear account of which conclusions the audit can support. No arbitrary universal F1 threshold determines readiness.

## 6 Recover provenance and define the population

Obtain a VM manifest containing the exact queries and versions, databases, retrieval dates, paper/year coverage, retrieval limits and ordering, article counts at each stage, processing failures, retries, and unfinished jobs. Distinguish successful no-forecast results from unavailable text and failed calls. Recover the actual extraction and verification model identifiers, prompts, schema, chunking, context limits, and truncation rules.

The downturn/recovery query selects particular economic discussion. Weighting cannot reconstruct forecasts outside the search universe. Define the population as the eligible material returned under the documented retrieval design. Do not call claim volume “press attention” without the appropriate article denominator. If only retrieved-article denominators are recoverable, name that narrower denominator explicitly.

Produce a corpus flow table and paper-by-year coverage figure. Show that WSJ verified coverage begins in 1984 and Chicago Tribune scored coverage ends in 2001. Separate changes in coverage from changes in reported expectations. Use common-paper comparisons where supported rather than interpreting a changing publication mix as an economic shift.

Maintain raw and verified sets separately. Their comparison does not identify a causal effect of verification or a claim-retention rate without lineage. Preserve repeated stripped labels until source evidence establishes duplication. Syndicated or repeatedly quoted forecasts should be evaluated as a possible dependence problem when source anchors permit it; identical topic/direction labels are insufficient evidence.

**Completion criterion:** every main table has a defined population and reconciled denominator, and absent records are not silently interpreted as rejected or nonexistent forecasts.

## 7 Repair and document the measurement contract

Use a codebook to distinguish the intended forecast from the outcome proxy:

| Ambiguity | Required treatment |
| --- | --- |
| Output declines versus output growth slows | Distinguish level changes from growth-rate changes |
| Prices fall versus inflation falls | Separate deflation from disinflation |
| Employment rises versus unemployment falls | Do not assume the variables are interchangeable |
| General economic activity versus industrial production | State and separately evaluate the proxy assumption |
| Recession within a year versus lower production in a year | Separate event occurrence from endpoint direction |
| Broad equity prices versus a named asset, bond, or yield | Use a supported benchmark or exclude |
| Explicit date versus inferred/default horizon | Keep separate analysis sets and exclusion reasons |
| Conditional statement or quotation of an earlier forecast | Preserve the condition and original timing where recoverable |

Retain three transparent views: current legacy rules for comparability, an expanded set with documented inferences, and a strict set with semantically supported targets and horizons. Define eligibility without looking at whether a forecast was correct. A numeric exported horizon is not itself proof that the source stated it.

Report how the strict set changes the newspaper, era, and topic composition. Do not claim its findings automatically generalize to the excluded vague forecasts. Keep pre-1919 NBER-state proxy scoring separate from direct variable outcomes. Preserve uncertainty where source context cannot resolve the intended meaning.

The monthly six-month IP experiment is an aggregate signal test. It is not the same as grading every individual claim at its stated horizon. Explain why aggregating claims with different intended horizons could still be informative, and run a bounded horizon-composition sensitivity if source validation makes it feasible.

Keep deterministic economic outcomes, frozen references, and explicit endpoint conventions. Write source-grounded examples with expected scoring decisions and meaningful implementation tests for any repaired rule. Automated tests establish implementation consistency; they do not replace the semantic audit.

**Completion criterion:** a reader can take an example source passage and understand why it is included, what it predicts, when it is evaluated, and why the benchmark is appropriate.

## 8 Finish the analysis without an endless search for significance

Freeze a publication analysis specification now, explicitly recording the earlier exploration. Name the descriptive primary comparison and the monthly predictive primary comparison separately. Do not switch to the best-looking metric after the next rerun.

For the descriptive part, prefer target-specific, equal-article comparisons against the fixed-direction baseline on identical eligible observations. Show the pooled legacy result alongside the strict-sample estimate rather than hiding the sample change. Newspaper rankings and forecaster identities are secondary and require support for attribution and comparable coverage.

For the monthly part, retain matched forecast origins, vintage-aware macro inputs and training labels, training-only preprocessing and selection, and the recent-base-rate comparator. The latest selected benchmark is the current reference. Publish the earlier weak-benchmark results in the development record so readers can understand why the apparent newspaper improvement shrank.

Choose a small set of checks that each resolves a specific concern:

1. Source-validated versus original interpretation, with appropriate sampling weights and uncertainty.
2. Explicit versus inferred horizons and supported versus proxy targets.
3. Verified primary corpus versus raw sensitivity, without claiming causal verification effects.
4. Equal article, equal month, and stable-newspaper support where each answers a clear weighting question.
5. Era and crisis sensitivity, including the already observed 2007–2009 exclusion.
6. A modest alternative macro information set or more timely vintage construction only if the necessary historical information is available and its role is specified first.

A journal specialist may reasonably challenge quarterly unemployment/CPI snapshots that are older than the information available to contemporary forecasters. Either improve that timing on a supportable period or describe the benchmark as the available reconstructed information set. Do not equate beating it with beating the best professional forecasts. Optional comparisons with survey forecasts or published news indexes need compatible targets, release dates, and matched periods; their current revised series cannot automatically be used as historical predictors.

Account for overlapping outcome windows and common monthly shocks. Claim counts are not independent outcome counts. Report paired time-block uncertainty, block counts, and the fact that current intervals condition on saved predictions and omit model-selection and extraction uncertainty. With only two five-year CPI blocks, avoid strong claims from the bootstrap. A full pipeline uncertainty procedure may be useful if a reviewer-relevant inferential claim requires it; simply adding thousands of resamples cannot create additional historical episodes.

Keep unfavorable results, log loss, calibration, and class-specific performance visible. Zero forecasts above 90% confidence does not prove calibration. Better Brier does not guarantee better downturn ranking. Do not convert a wide interval into evidence of no economic effect; an equivalence claim would need a justified meaningful-effect margin and enough precision.

Evaluate annotation error impact on the audited population directly, then distinguish broader scenario analyses from measured corrections. Do not multiply every result by a global precision or F1 score. Horizon, direction, scope, and target errors can interact.

**Completion criterion:** the headline conclusion remains justified across the evidence actually collected, or the manuscript is narrowed to the dependence and uncertainty that the evidence establishes. A positive significant result is not a completion requirement.

## 9 Handle untouched evaluation and modern data honestly

All already examined 1900–2010 results are exploratory for subsequent specification choices. A file saved before the latest fit constrains that fit; it does not erase prior inspection. Do not relabel an old period an untouched test set.

A modern extension could provide a valuable separately reserved evaluation only if its outcomes have not already guided development. Document prior exposure, freeze the procedure before scoring, and use only mature outcomes. A retrospectively unexamined historical period is still not a live prospective forecasting trial.

The active analysis remains 1900–2010. Any 2011 onward extension requires an explicit scope update, verified imports, a completeness manifest, and revised date-contract tests. Keep it separate from the existing reports. Do not let an incomplete extraction queue silently expand the paper's population, and do not score long-horizon recent claims before outcomes mature.

Retrospective LLM extraction is a separate potential source of hindsight. Audit evidence spans, forbid outcome information in extraction instructions, and inspect whether famous historical events influence interpretation. Date/name masking on a suitable diagnostic subset may reveal sensitivity but cannot prove the absence of learned historical knowledge.

A first paper can be submitted without a modern extension if its contribution and exploratory status are clear. Do not make an uncertain collection timeline a permanent barrier to completing a valid historical paper. A failed modern replication, if undertaken, must be reported rather than used to start another search for a favorable holdout.

## 10 Resolve data access before designing a public release

Plan for two layers: a permitted public research package and restricted source material accessed through the authorized institution. Confirm the specific applicable agreement with the library or TDM administrator before uploading any new source material or assigning a public data license.

ProQuest's current TDM Studio supplemental terms distinguish derived data used for research and publication from citation/index records, which have separate redistribution restrictions; they also address export of LLMs trained on publisher content. The applicable institutional and underlying database terms still matter. This is why permission to use material for analysis is not a blanket public-release license. [Official TDM terms](https://about.proquest.com/en/about/supplemental-terms-of-use-tdm-studio/).

Make a field-level release inventory covering full text, excerpts, bibliographic records, identifiers, human labels, aggregated panels, prompts, fitted models, and macro snapshots. Record the basis for sharing or restricting each category. Confirm that even derived rows and embeddings are exportable before promising them. Keep source context in the permitted environment when necessary.

Aim to release code, documentation, synthetic fixtures, permitted derived results, and a clear reconstruction procedure. A restricted-data statement should identify the provider and dataset, explain access conditions, and state which analyses can be reproduced directly from the public package. Avoid an empty “available on request” promise if the authors cannot actually distribute the material.

This issue affects journal selection. For example, [PLOS ONE's third-party data policy](https://journals.plos.org/plosone/s/data-availability) provides a route for properly documented restrictions, while the [IJF policy](https://forecasters.org/ijf/) requires acceptable exceptions to sharing and a reproducibility check. Resolve compatibility before investing in that journal's final submission package.

**Completion criterion:** the authors can make a truthful data-availability statement and supply a viable reviewer/researcher access path without promising rights they do not control.

## 11 Manuscript and figure plan

Draft a full-paper version of approximately 7,000–9,000 main-text words before adapting to the selected journal's actual requirements. This is a working writing budget, not a claimed limit at every target. Use a technical supplement for details needed to reproduce the results.

| Part | Approximate words | Purpose |
| --- | ---: | --- |
| Introduction | 800–1,000 | Economic question, nearest work, precise contribution, restrained main findings |
| Historical context and related research | 700–900 | Explain the forecast record and how the study differs from sentiment and earlier historical studies |
| Corpus and human validation | 1,200–1,500 | Sampling, pipeline, coverage, direct audit evidence, limitations |
| Measurement and evaluation methods | 1,300–1,600 | Target/horizon rules, weighting, information timing, uncertainty |
| Results | 1,500–1,900 | Main descriptive comparison and incremental-information experiment |
| Robustness and interpretation | 900–1,200 | Error impact, coverage, era dependence, bounded alternative explanations |
| Conclusion | 300–500 | What was learned and the exact limits of generalization |

Prepare these main exhibits; combine related panels to avoid a paper overloaded with plots:

| Exhibit | Required content |
| --- | --- |
| Corpus and validation table | Article/claim counts at each stage, source years, exclusions, reviewed sample and inclusion rules |
| Coverage figure | Newspaper-year support and visible gaps; do not interpret raw claim volume as attention |
| Measurement table | Forecast examples, interpreted target/horizon, benchmark, and ambiguous or rejected cases |
| Descriptive performance figure | Target-specific newspaper-minus-baseline gaps, strict/expanded comparison, and uncertainty |
| Predictive results table | Identical forecast months, all three primary models, Brier/log loss/accuracy and incremental intervals |
| Stability and calibration figure | Performance by period, crisis sensitivity, reliability with sample support |

Put the full rubric, prompt/model configurations, validation sampling, confusion matrices, vintage/release audits, model-selection details, all planned robustness checks, and earlier exploratory model results in the supplement. Use at least one unfavorable example in the main text so the interpretation rules are concrete.

A suitable eventual abstract should state the selected corpus, validation design, exact task, main effect sizes with uncertainty, and contribution. Do not write “human-validated corpus” when only a sample was reviewed. Do not describe six-month IP direction as recession-onset prediction or quote extraction as the newspaper's own institutional belief.

## 12 Reproducibility and authorship

Create a versioned publication snapshot only after the final rerun. Preserve original exports and write new derived analysis under `data/scored/proquest/`. Include a manifest linking every manuscript number to an output file, script, source hash, and specification.

Provide a working environment specification, dependency versions, seeds, ordered commands, expected runtime/storage, and access instructions. Use a clean environment, not the broken root `.venv`. After code changes, run `tests/test_offline.py`, `tests/test_scoring.py`, `tests/test_forecasts.py`, and affected ProQuest suites. Have another person reproduce the main tables from documented inputs if possible; their role is reproducibility checking, not an assumed second annotation commitment.

Revise the README and publication-facing materials so old LOC findings and unsupported novelty language cannot be mistaken for current ProQuest evidence. Preserve the historical material as clearly labeled legacy work. The poster and old abstract are not a substitute for a new manuscript with the present population and methods.

Agree with the original collaborators and mentor on authorship, order, contributions, corresponding author, affiliations, acknowledgments, funding, and competing interests. The README lists Bode Bosell, Jeremy Liu, and Vincent Wang with equal contribution and identifies mentorship; the eventual statement should reflect actual contributions to the submitted paper, including subsequent work. Mentorship alone should not mechanically determine authorship or order.

Prepare an accurate account of AI use in extraction, verification, coding, analysis assistance, and writing where relevant to the chosen journal. Record tool/model versions and distinguish automated outputs from human judgments. All authors must be able to explain and take responsibility for the methods and findings. A code repository is not a substitute for that understanding.

If the study remains analysis of archival material, describe that scope accurately; do not invent an ethics approval. If later research collects participant data or evaluates people as research subjects, obtain the institution's determination for that additional design before collecting it.

## 13 Twelve week execution schedule

This is a proposed schedule beginning after the plan is adopted, assuming roughly 8–12 focused lead-researcher hours per week, continued source access, and timely collaborator feedback. It is an estimate for manuscript preparation, not a promise of journal acceptance. If source access or validation requires more time, move the manuscript date rather than weakening the evidence.

| Timing | Main work | Deliverable and decision |
| --- | --- | --- |
| Week 1 | Agree on paper question and preliminary journal route; inventory validation/40k queue; recover source manifest; compare nearest studies | Two-page concept, validation status, contribution paragraph, dependency list |
| Week 2 | Pilot source-context grading; finalize rubric and fixed audit sample; draft data-access inventory; record analysis decisions | Validation protocol and measurable review workload; decide whether the original ProQuest audit is sufficient |
| Weeks 3–4 | Complete planned audit; reconcile corpus/process counts; document semantic errors; draft data/methods | ProQuest audit report, corpus flow, codebook, concrete repair list |
| Weeks 5–6 | Implement necessary measurement repairs; run frozen comparisons and focused sensitivities; verify counts and timing | Publication tables with honest uncertainty; decide whether measurement, economics, or forecasting leads |
| Weeks 7–8 | Assemble full manuscript and supplement; complete literature comparison; obtain library guidance on sharing | Complete draft, literature matrix, data-availability draft, final venue shortlist of two |
| Weeks 9–10 | Mentor/coauthor review and, if available, outside methods review; independent reproduction | Comment-response log and reproducible main exhibits |
| Weeks 11–12 | Revise narrative and evidence; apply chosen journal format; finalize author approvals and submission files | Submission-ready package and a separately approved submission action |

Methods writing, literature work, journal reading, and environment preparation can continue while verification runs. Final accuracy claims must wait for the necessary validation and corrected analysis. A modern extension can run on a separate schedule if it is authorized and does not prevent completion of the historical paper.

If adopted in mid-October with these assumptions, a complete draft around late December or January is a reasonable planning target. For the journal process, reserve roughly 6–18 months as a planning allowance, with the possibility of longer after rejection or major revision. This is not a publisher-reported turnaround estimate. Advertised first-decision times often include desk rejections and should not be treated as publication promises.

Suggested responsibilities, to be agreed rather than presumed: Bode leads the question, source interpretation, and manuscript ownership; collaborators take defined analysis/review tasks; the mentor reviews the economic contribution and inferential claims; a library contact resolves the applicable sharing terms. Repository and drafting work can be assisted, but human annotation and author approval remain attributable human decisions.

## 14 Budget and submission package

The author's preference is an inexpensive route. Prioritize subscription publication at JCSS or Journal of Business Cycle Research, both of which list no APC, and retain Eastern Economic Journal with its separate US$30/US$90 submission fee. Check any other mandatory charges before committing. Subscription publication means readers or libraries pay for access; it does not mean the author must buy a journal subscription. Do not select optional paid open access. Check any applicable funding mandate, and do not assume a past summer affiliation automatically qualifies for an institutional open-access agreement.

PLOS ONE and Cogent Economics & Finance remain researched alternatives, not active default targets. Consider them only with confirmed coverage of the publication charge through institutional funding or a waiver. PLOS ONE requires assistance applications at submission; an application alone does not establish coverage, so resolve the funding process before pursuing that route. Cogent's applicable APC needs an actual quote. Keep source-access expenses, compute/API use, and optional conference travel separate from publication fees. Paid editing is not a prerequisite for a clear manuscript.

Prepare the following before any submission action:

- Final manuscript in the required format, anonymized where requested, plus a separate title page when required.
- Abstract, keywords, and appropriate subject/JEL classifications.
- Figures, tables, captions, accessible text where required, and a numbered supplement.
- Data/code availability statement and a permitted review package.
- Contribution, funding, conflicts, acknowledgments, ethics applicability, and AI-use statements.
- Coauthor agreement on the final version, author order, corresponding author, venue, and costs.
- A concise cover letter identifying the question, contribution relative to the nearest work, central result with its limits, and journal fit.
- Genuine reviewer suggestions if requested, screened for conflicts; never fabricated identities or contact details.

A useful cover-letter outline is: “We submit [title], which studies [precise question] using [defined corpus]. Relative to [nearest studies], the contribution is [demonstrated difference]. We find [effect and uncertainty]. The work fits [journal] because [specific scope connection]. Data access and reproducibility are described in [statement].” Complete the originality and exclusive-submission declarations only when they are true.

Submit to one journal at a time. Before a preprint, obtain coauthor agreement and check the intended journal's policy and data permissions. Label it as a working paper or preprint, not an accepted publication. A public preprint can provide a useful milestone under the authors' control, but does not substitute for peer review.

## 15 Respond to editorial decisions

For a desk rejection, distinguish lack of fit, insufficient novelty, and a substantive validity problem. Revise the appropriate part before trying the next venue. For external reviews, build a response table with each comment, the change or reasoned response, the manuscript location, and any analysis added.

Preserve the original submitted results when adding reviewer-requested analyses. Label post-review exploration honestly. Do not silently replace the primary endpoint with whichever new analysis looks strongest. If a review exposes a real error, correct every dependent table and conclusion and document the effect.

If a revised manuscript still cannot support a forecasting-superiority claim, retain the more limited result. If the data cannot support reliable scoring at all, a methods/error-analysis paper may be appropriate only if it offers a substantive, demonstrated lesson; uncertainty alone is not automatically a publishable contribution.

After acceptance, check proofs against the saved tables, archive only permitted materials, update citation information, and distinguish the accepted manuscript from the final published version according to the publisher's terms.

## 16 Readiness criteria and immediate work

The paper is ready to submit when all of the following are true:

- The contribution is distinct from the closest historical-forecast and news-information studies.
- The actual corpus and processing stages reconcile, including the status of the ongoing verification queue.
- Direct ProQuest human audit evidence supports the claims made, with single-annotator and recall limitations stated accurately.
- Forecast meaning, horizons, proxies, conditions, and exclusion rules are defensible and visible.
- Main comparisons use matching populations and information timing; dependence and repeated exploration are acknowledged.
- The headline survives the relevant audit and sensitivity evidence, or is narrowed to what that evidence supports.
- The paper explains both the small estimated predictive gain and its uncertainty, without claiming proven superiority or proven uselessness.
- Main tables can be regenerated in a working environment; permitted data access and release are documented.
- All authors approve the final manuscript, contributions, venue, and costs.

The next concrete work should be a **publication evidence package**, consisting of a two-page paper concept, a literature comparison centered on the nearest three studies, a reconciliation of the ProQuest validation/verification work, a source-linked review protocol, and a manuscript outline with existing result tables placed into it. Much of this can proceed while the verification job continues.

**Started October 14, 2026:** the [publication evidence package](publication/README.md) now contains an initial concept, closest-study comparison, local validation/provenance status, source-review protocol, analysis specification, and manuscript outline with saved tables. `src/proquest_publication.py` assembles hashed evidence and twelve pilot retrieval addresses under `data/scored/proquest/publication/`. Source context and human judgments remain pending; the main 100-claim probability sample is not yet drawn. This milestone does not establish completed validation or submission readiness.

Do not restart every earlier experiment or build another neural model to fill time. The highest-value work now is to make the interpretation, evidence, and contribution strong enough that an editor can see a coherent paper worth reviewing.
