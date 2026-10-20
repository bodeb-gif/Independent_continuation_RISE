# ProQuest analysis deep dive

October 19, 2026. The most consequential new finding is that the favorable employment comparison depends strongly on the fixed baseline and forecast horizon. This is exploratory analysis of already inspected historical data, with no source validation, modern evaluation, model selection, or replacement of the primary comparison.

## Employment performance depends on the comparator

Under existing article weighting and unemployment-rate scoring, employment forecasts are 36.68% correct. The original constant unemployment-decline baseline scores 22.96%, but a constant flat forecast scores 45.39%. The newspaper-minus-flat gap is −8.71 percentage points; its paired five-year-block interval is [−27.12, +4.44], so the full-sample comparison remains imprecise.

The horizon pattern is more pronounced among machine-labeled stated horizons:

| Employment horizon | Claims | Newspaper accuracy | Constant flat | Gap, percentage points | Five-year-block 95% interval |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1–6 months | 3,432 | 25.20% | 68.45% | −43.25 | [−64.37, −23.05] |
| 7–12 months | 5,578 | 39.65% | 40.51% | −0.86 | [−20.87, +12.23] |
| 13–24 months | 250 | 45.19% | 18.83% | +26.36 | [+11.32, +39.43] |

These are different populations, not a causal horizon effect. Long-horizon support is small, and the intervals are marginal exploratory summaries. Every constant direction, horizon bin and planned block length is retained in the [complete diagnostic report](../data/scored/proquest/direction_diagnostics_v1/report.html). The original comparator remains unchanged.

The result points to a measurement question: the fixed ±0.5 percentage-point unemployment band classifies many short-horizon outcomes as flat. A forecast about job levels, slowing employment growth, or a small unemployment change may not mean the same thing. We cannot choose among those explanations without source context. Improving the RNN cannot resolve that ambiguity.

## Neutral forecast labels are rare across all four topics

| Topic | Forecast labeled flat | Outcome scored flat |
| --- | ---: | ---: |
| General business | 2.31% | 26.06% |
| Markets | 4.02% | 19.65% |
| Prices | 7.44% | 21.01% |
| Employment | 2.10% | 45.39% |

Shares are article-weighted within topic. This is evidence of a mismatch between the distributions of recorded labels and scored outcomes. It does not identify its cause: retrieval selection, extraction conventions, directional statements about small changes, and genuine forecasting errors could all contribute. Flat means inside the existing outcome band, not literal zero change. Scoring bands were not changed in response.

## Warning usefulness differs from three-class accuracy

The diagnostic also examines the direction opposite the original fixed baseline. For business/IP, warnings occur in 50.21% of article-weighted observations but output declines occur in 19.95%. Warning precision is 23.21%, recall 58.39%, and the false-positive rate 48.16%. This combines some detection with many false alarms; it is not evidence of reliable recession prediction.

The [cost table](../data/scored/proquest/direction_diagnostics_v1/illustrative_costs.csv) retains illustrative missed-event/false-alarm cost ratios of 1, 2, 5, and 10 and compares forecasts with both always warning and never warning. Beating only one trivial rule is insufficient. The in-sample business break-even range against both rules is approximately 3.31–5.00, based on point estimates without utility uncertainty; this is not a recommended decision threshold. In the market sample the corresponding range is empty. These binary tasks differ from three-class correctness, and the price event is deflation rather than a universal adverse outcome.

## The unit of analysis needs care

The separate [article-direction audit](../data/scored/proquest/article_direction_audit_v1/summary.json) groups scored claims by article, publication date, topic, outcome basis and exact horizon. Of 122,648 groups, 12,354 contain more than one direction label. Such groups account for 12.83% of article-weighted business claims, 9.25% of market claims, 7.22% of price claims and 5.48% of employment claims.

Different speakers, conditions or narrower targets can legitimately produce different forecasts in one article. Extraction errors could also contribute. These counts do not establish contradictions or duplicate claims, and no rows were removed. Even matching voice categories do not establish the same speaker. This strengthens the need to distinguish forecasts reported by a newspaper from a single forecast endorsed by that newspaper.

## Further analysis priorities

### Benchmark choice and outcome interpretation sensitivity

The [completed benchmark experiment](../data/scored/proquest/benchmark_interpretation_v2/report.html)
holds claims and article weights fixed while varying both the outcome bands and
the constant-direction comparator. Its full specification was saved before
calculating the new results, after the earlier employment pattern had been
inspected; this is exploratory, not preregistered confirmatory evidence.
The original bands are compared with bands multiplied by horizon months/12
and a zero-band direction-only diagnostic. Every scenario and all three
constant directions are retained. No original targets, models or p-values changed.

The main comparison here uses machine-stated horizons and excludes NBER proxy
outcomes. This differs from the all-legacy population above. The following
are equal-article-weighted accuracies for the same 9,260 employment claims:

| Outcome definition | Forecast accuracy | Always unemployment falls | Always flat | Always unemployment rises |
| --- | ---: | ---: | ---: | ---: |
| Original bands | 34.2% | 20.1% | 50.6% | 29.4% |
| Duration-scaled bands | 43.2% | 27.2% | 35.2% | 37.6% |
| Direction only | 57.6% | 46.8% | 5.8% | 47.3% |

Duration scaling relabels 16.5% of article-weighted employment outcomes.
The forecast-minus-flat gap changes from −16.4 percentage points
(five-year-block 95% interval −34.9 to −1.5) to +8.0 points (−9.5 to +19.6).
Thus the overall advantage over the flat comparator remains uncertain under
duration scaling. For 1–6 month forecasts, accuracy changes from 25.2% to
49.9%, while the flat comparator falls from 68.4% to 26.2%. For 13–24 months,
forecast accuracy instead falls from 45.2% to 34.3%; that subgroup has only
250 claims. These are changes in the measurement rule, not better predictions
or causal horizon effects.

Business, market and price forecasts remain below the original fixed-direction
comparator under all three definitions, with negative five-year marginal
intervals. Under duration scaling, their respective gaps are −10.8, −17.0
and −33.4 points, compared with −8.9, −14.1 and −28.0 under the original
bands. Their absolute accuracy rises, but the comparator improves more.
Raw-export sensitivity gives the same signs for these comparisons. No
multiple-comparison-adjusted claim or new p-value is made.

The analysis decision is to retain the original benchmark as a historical
reference and display flat and opposite-direction comparators alongside it.
Do not select the weakest comparator or the best-looking band after observing
results. Duration scaling stays an explicit sensitivity scenario: linear
scaling is not established as the meaning of the source forecasts. Direction
only is a diagnostic that rewards even tiny measured moves. In particular,
the earlier short-horizon employment deficit against flat should now be
described as dependent on the flat-band definition, rather than as a stable
forecasting failure.

The remaining interpretation choices have distinct requirements:

| Question | Current treatment | What would justify changing it |
| --- | --- | --- |
| Literal direction or economically material movement? | All three band scenarios retained | A declared target definition supported by the forecast language |
| Employment levels or unemployment rate? | Existing unemployment proxy, explicitly provisional | Source target identification and a compatible outcome series |
| Price level or inflation rate? | Existing CPI-level outcome | Source language establishing level versus growth-rate prediction |
| General business and markets | Existing production and broad price-index proxies | Identification of the actual activity or asset target |
| RNN and logistic comparisons | Frozen correctness-probability task and matched controls | A separately specified target change, retraining all models on the same labels, then evaluation on genuinely unexposed data |

These sensitivities do not authorize semantic relabeling from stripped exports.
Source validation and modern evaluation remain deferred. The RNN's saved
probabilities estimate correctness under the original rule; scoring them against
new correctness labels without refitting would test target mismatch, not a
fair model improvement. Constant economic directions in this experiment are
also not substitutes for the RNN's probability-prediction controls.

Reproduce with the working environment (the script refuses an existing output):

```bash
MPLCONFIGDIR=/tmp/bode-econ-mpl /tmp/bode-econ-repro-20261019/bin/python \
  src/proquest_benchmark_interpretation.py \
  --out data/scored/proquest/benchmark_interpretation_new
```

The run reproduces all original outcomes exactly on 174,808 verified and
296,084 raw non-NBER scored rows, preserves every repeated claim, verifies the
12-month anchor, and checks frozen input/model hashes. Two focused tests and
the required offline/scoring/forecast suites passed (97/33/33 main checks).
The specification-only failed first execution is retained in
`benchmark_interpretation_v1/failure.json`; v2 is the completed result.

The most useful unresolved questions are whether the short-horizon employment pattern survives semantically matched targets, why neutral statements are scarce in the exports, and how often multiple directions refer to distinct speakers or conditions. Those questions require the source work currently deferred. A future audit could include separately labeled diagnostic cases alongside the probability sample; such cases must not enter population error rates as if randomly sampled, and no new sample has been drawn here.

Once actual modern inputs are available and their exposure is documented, assess the locked models and benchmark comparisons separately. For now, retain the complete historical findings and avoid another hyperparameter search. The new preparation tools and clean rebuild make these future analyses executable without modifying the frozen historical results.

## Additional macro inputs and alternative economic targets

The subsequent user-authorized [combined experiment review](../data/scored/proquest/benchmark_input_review_v1/report.html)
completes both tracks: [RNN/logistic input ablations](../data/scored/proquest/macro_claim_inputs_v1/report.html)
and [alternative outcome benchmarks](../data/scored/proquest/alternative_targets_v1/report.html).
All results remain exploratory. No original model, primary scoring definition,
polarization arm or permutation p-value was replaced.

### Historical macro inputs

Four arms add no macro inputs, production, unemployment, or both to matched
claim-correctness models. Inputs include within-vintage trends, observation
ages and own-topic forecast-direction interactions. These scalars enter the
current claim representation; preceding press distributions still supply the
RNN sequence. Each arm uses the same two-topic claims and an 8-unit GRU with
the previously chosen regularization/window, all three seeds, metadata
logistic C=1, and metadata-plus-history logistic C=1. There are 48 neural fits
and 32 logistic fits, plus a training-prevalence control.

The four assessment blocks start in 1975, 1980, 1985 and 1990, with five
earlier years for stopping and a preceding 20-year fitting window. All blocks
have prior exposure and are not fresh confirmation. Historical core macro
coverage begins in December 1965, so the first fitting sample has only 1,110
claims; the four assessment samples have 5,847, 14,984, 7,590 and 18,663 claims.
No 1995-onward model assessment was performed.

Unlike earlier claim-model development, training and stopping correctness is
recomputed using a historical snapshot available strictly before the relevant
stage boundary. Target endpoint plus three months must precede that boundary.
Macro inputs use a snapshot strictly before the publication month's start.
Revised assessment correctness is used after fits. All arms share this target
protocol; comparisons with previous whole-corpus scores would mix sample,
coverage and label-protocol changes. No modern/revised series was used as a
historical feature. Recorded historical versus revised correctness differs
for approximately 3.1–10.5% of usable claims across these stage/fold audits;
these are claim-weighted revision rates, not extraction-error rates.

| RNN input arm | Equal-era mean Brier, both topics | Business | Employment |
| --- | ---: | ---: | ---: |
| No macro inputs | 0.19920 | 0.19877 | 0.20592 |
| Production | 0.19102 | 0.18762 | 0.21453 |
| Unemployment | 0.21286 | 0.21332 | 0.21899 |
| Both | 0.20962 | 0.20903 | 0.22223 |

Production improves the RNN in two of four eras overall and three of four for
business claims. Its average pooled Brier gain is 0.00818 (4.1%), but it does
not establish stable superiority. All unemployment-input employment RNN
folds worsen; adding both groups worsens all employment folds too.
The metadata-only logistic model has lower pooled mean Brier (0.17432) than
every tested RNN arm. Production improves the history-logistic model's mean
Brier from 0.29865 to 0.26532, but worsens metadata logistic from 0.17432 to
0.18637. More macro information is not uniformly beneficial under these
fixed model specifications. No new hyperparameter search or promotion follows.

### Payroll jobs and real GDP as alternative outcomes

Fresh [BLS payroll employment](https://fred.stlouisfed.org/series/PAYEMS) and
[BEA real GDP](https://fred.stlouisfed.org/series/GDPC1) were retrieved into a
separate derived reference folder, together with matching production and
unemployment snapshots. Original reference bytes remain unchanged. These
downloads supply revised outcome sensitivities only. Frozen and freshly
retrieved original-series signs agree on the evaluated matched samples, so
the observed alternative-series disagreements are not explained by that
snapshot-refresh difference.

For the same 9,260 stated-horizon employment claims, sign-only payroll scoring
gives 55.1% accuracy versus 63.3% for jobs always rising. The gap is −8.2
percentage points, with a five-year marginal interval of −33.2 to +19.0:
neither superiority nor clear inferiority is established. Unemployment-sign
scoring on those rows gives 57.6% accuracy versus 46.8% for unemployment always
falling. Payroll and unemployment-based improvement labels disagree for
21.9% of article-weighted claims. They are different economic quantities;
the export alone cannot establish the intended one.

The GDP comparison uses 15,680 stated-horizon business claims from 1947–2010,
restricted to quarter-end publication months and horizons divisible by three,
with all reference endpoints observed. GDP is never interpolated monthly.
Quarterly-average production is an intermediate comparison to separate
frequency aggregation from series choice. Sign-only forecast accuracy is
57.2% against monthly production, 56.6% against quarterly-average production,
and 54.9% against GDP. Their always-improve comparators score 73.1%, 73.0%
and 86.6%, respectively. The GDP gap is −31.7 points (five-year marginal
interval −39.5 to −24.7). GDP and quarterly-production signs disagree for
14.3% of article-weighted claims. Raw-export sensitivity gives the same gap
signs. The quarterly averaging convention still requires semantic caution;
quarter-end publication month does not mean the article appeared on the last day.

### Reproduction and decision

Run from the repository root in the working environment, always with a new
output folder:

```bash
python src/proquest_macro_claim_inputs.py --out data/scored/proquest/macro_claim_inputs_new
python src/proquest_alternative_targets.py --out data/scored/proquest/alternative_targets_new
```

The alternative target script uses the frozen downloads and manifests under
`data/scored/proquest/alternative_target_inputs_v1/` and requires no network.
The macro script reads the existing Philadelphia Fed archives. Model bundles,
training-label audits, feature availability, split assignments, all seed
histories and predictions are saved. The separate report generator verifies
the completed v1 runs, recomputes all 192 model Brier estimates and 27 main
outcome comparisons independently, and checks 386 input/artifact hashes and
all 30 frozen original files. Four focused tests and the required main suites
passed (97/33/33 main checks).

Production information for business claims is the most promising input
candidate in this bounded experiment, but it still trails the simpler
metadata logistic control. Payroll/GDP outcomes clarify interpretation rather
than rescue accuracy. A defensible next input extension would investigate
more timely monthly labor-market vintages and topic-specific models under a
new fixed protocol; choosing another winner on these repeatedly inspected
eras cannot provide fresh confirmation. Source validation, modern assessment
and manuscript drafting remain deferred.
