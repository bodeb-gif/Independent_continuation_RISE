Yes—there is a plausible publication here. I would change the sequence slightly: finish verification while starting human validation and freezing the research design now, then run the final analysis. You already have enough exploratory results to choose a focused question.
My recommended path is a conference presentation at the International Symposium on Forecasting or IC2S2, followed by a journal submission to the Journal of Computational Social Science. A stronger forecasting result could justify aiming at the International Journal of Forecasting.
I reviewed main, the ProQuest branch and its runbook, the validation materials, scoring code, and recession-model code. I could inspect the local artifacts, but not the unfinished corpus inside ProQuest.
What the repo says about your starting point
You have substantial infrastructure: extraction, deterministic scoring, professional-forecaster benchmarks, monthly indices, and several modeling approaches. The ProQuest runbook describes a continuous 1900–2010 corpus of roughly 146,000 articles, which could substantially improve the older LOC analysis.
Three findings should shape the next stage:
- Human validation is still the main missing evidence. The 16-page/52-claim extraction benchmark is explicitly model-annotated. Your newer [audit plan](/Users/bodebosell/Documents/GitHub/datascience-rise-practicum/validation/extraction_audit/README.md) correctly distinguishes model agreement from human recall.
- Forecast horizons deserve more attention than model complexity. In the committed LOC data, 9,899 of 14,251 scored claims—69.5%—use a default horizon. That does not establish the ProQuest rate, but it makes horizon quality a priority.
- The backtests need another methodological pass. The recession model’s [forward-testing function (line 122)](/Users/bodebosell/Documents/GitHub/datascience-rise-practicum/more_model_images/make_broad_vs_attention_figure.py:122) trains on every earlier year even though its labels look 12 months ahead. Some training outcomes therefore extend into the test period.
These are fixable. They also explain why “finish data → try more ML” would miss the highest-value work.
The paper I would aim to write
A useful working title is:
A Century of Economic Forecasts in the American Press: Accuracy, Updating, and Information Beyond Economic News

Its central question would be:
Do explicit forecasts reported in newspapers contain information about future economic conditions beyond current conditions and ordinary economic news?

This framing gives you a clear contribution. Existing research already builds a 170-year economic sentiment series from historical newspapers, and Business News and Business Cycles demonstrates predictive information in news attention. Your opportunity is the record of specific, attributable, forward-looking claims with identifiable targets and horizons. Historical sentiment research, Business News and Business Cycles.
I would avoid building the paper around “nobody has ever studied this” or “newspapers are only 50% accurate.” The first needs a much fuller literature review; the second depends heavily on the outcome definition and relevant baseline.
Realistic venues
The assessments below are my judgment about fit after the work described here, not estimates of acceptance probability.
Venue	My assessment	What your submission should emphasize
International Symposium on Forecasting	Best first conference target.	Forecast evaluation, turning points, matched professional benchmarks, and honest out-of-sample results.
IC2S2	Strong conference target for an abstract/poster.	How expectations circulate through newspapers, whose forecasts get reported, and how expectations adjust.
Journal of Computational Social Science	My first journal choice. Its scope explicitly includes economic phenomena, text analytics, and AI.	A validated measurement pipeline supporting a substantive finding about expectations or media.
FinNLP workshop	Realistic for a focused methods/dataset paper.	Historical forecast extraction, temporal interpretation, OCR robustness, and human evaluation. An ordinary classifier comparison would be less compelling.
Digital Scholarship in the Humanities	Plausible if you develop the historical interpretation.	Changes in economic discourse and forecasting authority, supported by close reading and quantitative evidence.
International Journal of Forecasting	Ambitious stretch target.	A convincing contribution to forecast evaluation or incremental predictive information, with strong benchmarks and reproducibility.


Timing, checked September 14, 2026: ISF 2027 is scheduled for June 20–23 in Paphos, and its current site lists March 7 for abstracts. That is a useful planning target. IC2S2’s 2026 meeting has passed; monitor its next call. FinNLP 2026 submissions have closed. Computational Humanities Research is another good fit, but even its January 2027 meeting had an August 14, 2026 deadline, so that cycle is already closed. ISF dates, ISF deadlines, CHR call.
What I would do with the data
I would build one main paper around the first two analyses below, adding the third only if the data supports it.
1. Measure forecast skill under defensible comparisons.
   Estimate performance by target, horizon, era, and position around economic turning points. Compare forecasts against “predict the usual direction,” persistence, and a simple macroeconomic forecasting model.
   Compare newspapers with Livingston/SPF only on overlapping dates, comparable targets, and matched horizons. Similar overall hit rates across different periods do not establish similar forecasting ability.
   Treat forecasts quoted in newspapers as forecasts conveyed by the press. Distinguish the journalist from the quoted economist, official, or businessperson.
2. Test whether explicit forecasts add information beyond ordinary news.
   This is the most promising centerpiece. Compare:
   Model	Information available
   Baseline	Economic conditions available at publication
   News model	Baseline + economic-news attention and sentiment
   Forecast model	News model + explicit forecast direction, disagreement, and specificity
   
   
   Evaluate future industrial-production growth as well as recession onset. Continuous growth gives you variation beyond the small number of recessions, although overlapping horizons still create dependence.
   A valuable result could be that forecasts add information—or that ordinary coverage contains useful signals while explicit predictions add little. Both answer a meaningful question.
3. Study how expectations adjust as conditions change.
   Measure whether forecasts shift promptly after deterioration or recovery, whether quoted experts move earlier than journalists, and whether disagreement rises before the average forecast changes.
   Use monthly publisher panels and illustrative articles. Treat these as associations unless you develop a credible causal design.
   An especially interesting extension: distinguish genuinely independent predictions from repeated wire stories or repeated quotations. Ten papers repeating one economist are ten instances of dissemination, but only one underlying forecast. That distinction could strengthen both the statistics and the media interpretation.
I would postpone elaborate narrative categories, individual forecaster rankings, and large neural prediction models. They require additional validation or repeated observations and could distract from the main contribution.
A concrete plan while verification finishes
Stage	Work	Deliverable / condition for moving on
Now: research design	Choose one primary question, outcomes, horizons, baselines, and time splits. Record which findings you already explored.	A dated analysis plan; new ProQuest holdout results remain unseen.
Now: corpus audit	Inventory articles and claims by month, publisher, source, extraction version, and verification status. Record failures separately from articles containing no forecasts.	Coverage table, sampling description, and missingness report.
During verification: human validation	Pilot the rubric, then annotate both whole documents and sampled claims. Examine verifier rejects.	Precision, recall, field agreement, and error analysis with uncertainty.
After verification: measurement freeze	Finalize scoring rules, exclusions, deduplication, and the primary analysis subset.	Versioned dataset and data dictionary.
Following 3–5 weeks	Run descriptive analysis, matched benchmarks, and a small prespecified model ladder.	Main figures and held-out performance tables.
Following 2–4 weeks	Run sensitivity checks, write the paper, and assemble reproduction materials.	Mentor-reviewed manuscript and conference abstract.


Those durations are planning estimates; annotation effort and your remaining quota-limited verification work determine the actual schedule.
For validation, I suggest this starting design:
- Pilot: two people independently annotate about 20–30 articles, then resolve rubric ambiguities.
- Held-out document sample: approximately 100–150 articles/pages, spanning eras, publishers, OCR quality, and economic conditions. Humans identify every eligible forecast, including documents with none. This measures missed forecasts.
- Claim audit: approximately 500–700 retained claims, checking forecast validity, direction, target, scope, attribution, and horizon.
- Reject audit: approximately 100–200 rejected candidates, to learn what verification removes incorrectly.
These are starting budgets, not universal sufficiency thresholds. Use the pilot’s forecast density and clustering to refine them. Oversampled strata need appropriate weighting in overall estimates.
Keep “is a forecast” separate from “is scorable.” A genuine regional forecast with no suitable outcome series is still a successful extraction. Otherwise, the evaluation rewards the extractor for discarding valid but difficult claims.
Two-model agreement can help identify difficult cases. It cannot establish recall when both models miss the same forecast.
The methodological upgrades that matter most
First, validate the meaning of the scoring rules. Unit tests establish that code implements a rule; they do not establish that the rule measures the statement correctly. For example, the current [scorer (line 198)](/Users/bodebosell/Documents/GitHub/datascience-rise-practicum/src/truth_data.py:198) sometimes substitutes NBER recession status for missing stock-market outcomes. I would keep those proxy scores out of the primary stock-forecast analysis.
Also distinguish:
- “Output will fall” from “growth will slow.”
- “A recession will begin within a year” from “the economy will be in recession a year from now.”
- Explicit horizons from inferred or default horizons.
- Unconditional predictions from statements contingent on something happening.
Make clearly grounded targets and horizons the primary accuracy sample; show broader samples as sensitivity analyses.
Second, make the prediction experiment honest about time. At each training cutoff, use only claims whose outcome windows have finished and whose labels would be available. Fit preprocessing and tune models using earlier data only. Use time-block uncertainty estimates and account for duplicated stories.
Publication lags on revised macro data are insufficient for a strict real-time claim. Use historical vintages where available, such as the Philadelphia Fed’s datasets; identify the early-period analysis as retrospective where equivalent vintages are unavailable. Philadelphia Fed real-time data.
Third, use a small model ladder. Start with simple baselines, regularized regression, and one boosting model. Add text features only for a specified hypothesis. For “will this claim be right?”, include a baseline that predicts the economic outcome from macro data and compares that prediction with the claim’s direction. Otherwise, the model may simply learn that optimistic claims tend to succeed during expansions.
Report Brier score or log loss for model probabilities, suitable regression errors for growth, and recession detection versus false alarms. Newspaper optimism shares and hedging labels are not automatically probabilities, so they do not by themselves support probability-calibration claims.
Fourth, make the dataset reusable. Preserve document identifiers, source versions, annotation instructions, outcome mappings, duplicate groups, and all denominators. Your ProQuest runbook places text-dependent work inside the VM; plan to release permitted derived data and reproducible scripts, with a separate public-text validation set where possible.
My immediate priority would be three deliverables: a frozen analysis plan, a human annotation pilot, and a month-by-publisher coverage report. Those can all advance while verification runs. They will determine whether the final project supports a strong historical measurement paper, an incremental forecasting paper, or both.