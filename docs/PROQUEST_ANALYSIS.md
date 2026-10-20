# ProQuest-only analysis

The active analysis corpus is the annual ProQuest economy export, 1900–2010.
Use `data/proquest/verified/` as the primary machine-filtered set and
`data/proquest/raw/` for extraction/filter sensitivity checks. Both contain
111 annual shards, copied unchanged from `proquest-tdm-integration` at `774b68f`.
Older crisis-window exports are excluded.

LOC pages and claims are for extraction validation only. Existing LOC results
and models on main describe a previous corpus; they are not ProQuest results.
Do not use LOC claims, scores, page denominators, or fitted artifacts in this analysis.

From the repository root, start with:

```bash
python3 src/analyze_proquest.py
# Optional: assemble the verified claims for a later scoring run.
python3 src/analyze_proquest.py --export-claims
```

Reports go into `data/scored/proquest/`. The assembled JSONL omits empty
records, retrospective window annotations, and verifier prose. All original
exports remain unchanged. Identical exported labels are counted but retained:
the exports omit quotes and lack a unique claim identifier, so labels alone
cannot prove that two forecasts are duplicates.

## First descriptive outcome analysis

The descriptive entry point scores only the annual machine-verified set:

```bash
pip install -r requirements-proquest.txt
python src/proquest_descriptive.py
python tests/test_proquest_descriptive.py
```

The first run scored 175,855 of 274,070 verified claims. The pooled hit rate
is 40.8%, versus 53.6% for a fixed-direction baseline on the same topic/horizon
mix. No ML models were fitted to the corpus. Read
`data/scored/proquest/descriptive/report.html` for charts, exclusions,
publisher comparisons, horizon subsets, and scoring sensitivity. The report's
methods section documents the actual rules; the old LOC results are not reused.

References are frozen in `data/reference/proquest/`: existing local FRED
snapshots for production, CPI, unemployment, and USREC, plus the public Shiller
S&P Composite workbook downloaded 2026-09-16 from `https://shillerdata.com/`.
Reference hashes and coverage are recorded in the result's `summary.json`.
Shiller is used consistently for market claims across the entire period; it
is a provisional broad-market proxy, not an exact match to every asset forecast.

The script excludes nonnational/unsupported-topic claims, accepts positive
integer numeric horizons of 1–24 months, rejects invalid/longer horizons, and
reports default versus claim-grounded horizons separately. It retains every
eligible label row and reports equal-article weighting as a sensitivity check.
Publisher rankings merge historical editions and include only papers with at
least 500 scored claims. They are descriptive; topic/era mix still matters.
The fixed baseline predicts production/stocks/prices rise and unemployment
falls. It is not a learned model or a claim that rising prices are good news.

Future refinements can resolve excluded labels and improve semantic matching
between claims and benchmark series using the in-VM source quotes.

## Descriptive follow-ups

```bash
python src/proquest_followups.py
python tests/test_proquest_followups.py
```

The standalone `data/scored/proquest/followups/report.html` covers false alarms
and missed industrial-production declines, warning timing around recession
starts, consensus versus contrarians, stated horizons, publisher specialties,
coverage-adjusted comparisons and decade stability, and forecast voice.
Speaker-attribution coverage is exported alphabetically for later identity and
source-quote review. Individual forecasters are not assigned accuracy rankings.

The script validates saved outcome rows one-to-one against all annual verified
exports and verifies frozen reference hashes. Historical consensus uses only
outcome-eligible forecasts from other papers in the preceding 90 days,
excluding the current date. It requires 20 earlier claims from two other
papers and matches topic, benchmark, horizon basis, and horizon bucket.
No realized outcome is used to form consensus. Its accuracy comparison matches
the same paper, publication month, topic, benchmark, horizon basis, and exact
horizon, requiring five claims in each group. Exact matches share the same
benchmark outcome and fixed-direction baseline.

Publisher and voice comparisons use shared year/topic/benchmark/horizon-basis/
horizon-bucket cells, requiring ten claims from each group. Six-versus-twelve-
month comparisons use explicitly stated horizons in shared paper/year/topic/
benchmark cells. Harmonic-overlap weights give both groups the same cell mix.
Five-year block resampling describes historical variability; claims are not
independent observations, and intervals are not corrected for multiple tests.
Publisher pairwise averages use different shared coverage for each opponent,
so the resulting order is descriptive, not a universal common-period ranking.

Warning timing uses the continuous frozen USREC chronology, rather than any
old crisis-window claims. Each directional national business forecast is
assigned to at most one nearby recession onset. The phase comparison includes
the same 16 events with at least 30 forecasts in each phase, equally weighted,
with pre-onset expansion months and post-onset recession months. This measures
worsening expectations, not necessarily explicit recession predictions.
The disagreement/onset diagnostic is also retrospective and descriptive.

Coverage correction: Wall Street Journal verified claims begin in 1984;
Chicago Tribune scored coverage ends in 2001. The first report's earlier
1960 start-year statement for the Journal has been corrected in its generator
and generated files.

Do not infer sampling attention from claims alone; obtain ProQuest article
denominators from the VM. Train/evaluate models by time blocks, never random
claims, and use only information available at the forecast date as features.

Machine-verified labels still need extraction validation. Gold/LOC agreement
is validation evidence, not another analysis corpus or human recall estimate.

## Raw-versus-verified robustness

```bash
python src/proquest_robustness.py
python tests/test_proquest_robustness.py
```

The standalone `data/scored/proquest/robustness/report.html` compares the two
annual export sets with the same frozen economic references and deterministic
scoring rules. Verified claims remain the primary corpus; raw claims enter only
this sensitivity analysis. The shared scorer defaults to verified-only input;
its explicit `source_set="raw"` adapter accepts raw candidates without inventing
verification fields. Source-local record addresses are qualified by source set.

The report includes corpus/exclusion counts, newspaper/year coverage, label
composition, article-level count changes, accuracy and baseline gaps by topic,
paper, decade, direction and horizon basis. Equal scorable-article weighting is
primary; equal claim/month weights, common scorable articles, stated horizons,
and removal of the early NBER proxy are separate sensitivities.

Shared cells match newspaper, publication year, topic, benchmark, horizon basis,
and exact horizon, requiring ten claims per set. A stricter publication-month
comparison requires five per set and holds the deterministic outcome and fixed
baseline constant. Both use the same harmonic-overlap distribution of article
mass. The report exports matched cells and coverage, rather than extrapolating
to unsupported groups. Joint two-, five-, and ten-year block resampling retains
raw/verified dependence; matched support and cell weights are held fixed.

These are descriptive export comparisons, not causal verification effects or
claim-level retention estimates. Identical stripped labels are retained; claims
are not paired without lineage. Missing articles are not assumed rejected or
fully processed. Article denominators and processing status still require the
VM manifest. No human validation or modern extension is assumed complete.
Source, reference and code hashes are saved in `summary.json`; all source
exports remain unchanged. This report fits no predictive models.

The first comparison scores 298,319 raw and 175,855 verified claims. With equal
article weights, accuracy is 41.7% versus 40.9%, and the respective fixed-baseline
gaps are -13.5 versus -12.7 percentage points. Exact-month matching covers 65.6%
of raw and 66.1% of verified scorable claims; its verified-minus-raw gap is
-0.37 points (five-year-block interval: -1.44 to +0.56). The aggregate shortfall
against the baseline appears in both sets; this comparison does not establish
a stable accuracy difference or a causal effect of verification. Newly scored
verified rows reproduce the existing descriptive scores.

## Monthly economic-information experiment

```bash
pip install -r requirements-proquest-information.txt
python src/proquest_information.py --build-only  # panel/features, no outcome loading or fitting
python src/proquest_information.py
python tests/test_proquest_information.py
```

`data/scored/proquest/monthly_information/report.html` covers the monthly panel,
six-month industrial-production target, fixed model comparison, and stability
checks. `evaluation_spec.json` was saved before fitting this experiment. Earlier
1900–2010 results were already inspected, so this is exploratory historical
development, not a new holdout or a preregistration of the whole project.

The reusable panel contains 182,817 readable national direction claims across
business, markets, prices and employment. It includes claims whose horizons or
eventual outcomes cannot be scored. Articles receive equal weight within each
newspaper/topic/month, then observed newspapers receive equal weight. Missing
months have missing signals, not neutral forecasts. Counts describe export
coverage, not population press attention. Direction changes compare papers
represented in both adjacent three-month windows.

At the start of month t, features use completed print months through t−1. The
target is INDPRO monthly-average change from t−1 to t+5, with the existing ±2%
flat band. The starting economic value is an outcome component, not an input.
Training origins start in February 1919. Annual expanding refits in January
1950–2010 admit only outcomes whose endpoint plus three months is strictly
before the refit origin. Imputation/scaling use training data only. These
release allowances do not recreate historical vintages of the revised series.

The comparison uses 732 forecast months and three models: smoothed historical
class frequencies, a missing-coverage-only logistic control, and multinomial
ridge logistic regression adding four press signals. The signals are recent
net direction, common-paper direction change, disagreement and cross-paper
dispersion. C=1 is fixed; no hyperparameters are selected using evaluation
results. No macro values, outcome eligibility, retrospective annotations,
speaker identities or verifier prose enter the predictors. Each month receives
equal evaluation weight, rather than repeating its outcome for every claim.

The first run's multiclass Brier score improves from 0.6397 to 0.5739 (lower is
better); direction accuracy rises from 48.1% to 55.6%. The paired five-year-block
Brier improvement interval is [0.0214, 0.1144]. Improvement appears in 10 of 13
five-year blocks and persists when 2007–2009 evaluation months are omitted
(Brier 0.6307 versus 0.5698). It is uneven: the 1950–1964 development block
slightly worsens, and 1995–1999 is a negative five-year block. The coverage-only
control remains close to the base rate. All 732 evaluation months have complete
signals under the specified coverage rule.

Paired two-, five-, and ten-year block intervals condition on fitted forecasts.
Decade, development-block, leave-one-five-year-block-out, and crisis-exclusion
results are exported. Scoring exclusions do not remove those episodes from
later training or refit the models. The 2010 block contains one year. This test
does not establish incremental value beyond a vintage macroeconomic model or
prove individual forecaster skill. Query selection, semantic proxies,
retrospective extraction, and revised outcomes still limit interpretation.

The folder includes article/paper/national panels, features, targets, annual
refit audits, preprocessing, coefficients, monthly probabilities and losses,
calibration, metrics, charts, and source/reference/code/specification hashes.
Source exports remain unchanged; LOC and old crisis-window exports are excluded.

## Vintage macro baseline and incremental newspaper information

```bash
pip install -r requirements-proquest-information.txt
python src/proquest_vintages.py       # offline with the saved source workbooks
python src/proquest_macro_information.py
python tests/test_proquest_macro_information.py
```

The standalone `data/scored/proquest/macro_information/report.html` adds a
historical macro benchmark, using original Philadelphia Fed real-time workbooks
saved under its `reference/` directory. `proquest_vintages.py --fetch` downloads
missing workbooks and documentation; existing source workbooks stay unchanged.
The prior monthly panel is required; `proquest_information.py --build-only`
rebuilds it without fitting the earlier experiment.

The availability audit finds production vintages from November 1962,
unemployment from 1965Q4, and nonempty CPI vintages from 1994Q3. Earlier CPI
headers contain no data. First-of-month forecasts select the latest earlier
snapshot; production uses a conservative month-end availability bound and the
quarterly series use the documented midquarter date. Observation age is recorded
and used as a predictor. Growth is always computed within a single vintage,
avoiding index-rebasing artifacts; no revised observations fill historical gaps.
These reconstructed snapshots are a defensible historical benchmark, but the
quarterly unemployment/CPI series can be older than information actually
published monthly.

The core comparison uses 408 identical evaluation months, 1977–2010. Eight
macro predictors describe production growth, unemployment and observation ages.
The combined model adds the four existing print-time newspaper signals. Both
are multinomial ridge logistic regressions with C=1 and training-only scaling.
Each January, all three models share the same eligible training months. Training
labels come from the production vintage available at that refit, with the same
six-month ±2% target and a three-month maturity allowance; unavailable endpoints
are excluded. Final revised production is used only for evaluation truth.
The recent base rate uses the latest 120 eligible mature months with Laplace
smoothing. No tuning uses these evaluation outcomes.

| Core model, 1977–2010 | Brier ↓ | Log loss ↓ | Accuracy |
| --- | ---: | ---: | ---: |
| Recent base rate | 0.6443 | 1.0373 | 42.2% |
| Economy only | 0.6672 | 1.0882 | 39.7% |
| Economy + newspapers | 0.6249 | 1.0552 | 49.8% |

The incremental newspaper Brier improvement is **0.0422**, with a paired
five-year-block 95% interval **[−0.0681, +0.1452]**. Six of eight calendar
five-year cells improve, but 1995–1999 and 2000–2004 worsen. Excluding 2007–2009,
Brier scores are 0.6201, 0.6675 and 0.6391 respectively: the combined model
still beats economy-only but loses to the recent base rate. The macro-only
model is weak, and the combined model does not beat the base rate on overall
log loss. These results do not establish reliable incremental forecasting skill.

The CPI-inclusive check evaluates 108 common months, 2002–2010. The saved
specification initially targeted 2001–2010; its 2001 training sample had no
fall outcomes, so the three-class fit stopped before producing predictions.
`implementation_note.json` documents excluding 2001 for all models, recorded
after the first core fit and before CPI predictions. The original specification
is preserved. CPI Brier scores are 0.6897 (base rate), 0.9216 (economy only),
and 0.7721 (combined). Better downturn ranking does not compensate for poor
calibration: both regressions lose to the base rate. Different training histories
prevent interpreting core-versus-CPI differences as the isolated effect of CPI.

The report includes class calibration, era and crisis checks, leave-one-block-out
scores, and paired 2/5/10-year intervals. The short CPI history has only two
five-year bootstrap blocks and one ten-year block; the latter interval is
degenerate and uninformative. All intervals condition on fitted forecasts.
Source hashes, vintage selections, missing-input support, per-refit training
labels, preprocessing, coefficients and probabilities are exported. The study
remains exploratory, with selected-query and machine-label limitations; human
ProQuest validation is still needed. Original claim exports remain unchanged.

## Macro model error audit

```bash
python src/proquest_macro_diagnostics.py
python tests/test_proquest_macro_diagnostics.py
```

`data/scored/proquest/macro_diagnostics/report.html` diagnoses the saved macro
forecasts without fitting or recalibrating anything. It decomposes model losses
relative to the recent base rate by realized class and five-year period, checks
confidence against accuracy, reconstructs training fit from saved coefficients,
measures feature extrapolation, and compares historical training labels with
final revised outcomes. These are post-hoc diagnostics, not a new holdout.

Flat outcomes drive the economy-only model's net Brier disadvantage. Their
contribution is +0.0760 in the core study, partly offset by −0.0508 on rises
and −0.0023 on falls, yielding the overall +0.0229 gap. In the CPI study,
flat outcomes contribute +0.2607 of the net +0.2320 disadvantage. Contributions
are summed group loss differences divided by all evaluation months; they add
exactly to the overall gap.

The core economy-only model made 21 forecasts with at least 90% confidence,
averaging 93.2% confidence but only 38.1% accuracy (8 correct). The CPI model
also made 21 such forecasts, averaging 97.8% confidence with 9.5% accuracy
(2 correct). Adding newspapers improves some results but leaves substantial
overconfidence. Counts are small and target windows overlap.

The January 2002 CPI fit used only 80 training months. Its in-sample vintage-label
log loss was 0.3679, compared with 11.6261 during 2002. In September 2002, a
1.3-point unemployment increase over 12 months was 6.45 training standard
deviations above the mean. That feature contributed 13.03 of the 17.34
rise-versus-flat logit margin: the model assigned almost certain rise to an
eventual flat outcome. This is a coefficient decomposition, not a causal claim.
The large fit/evaluation gap is consistent with overfitting and distribution
change; the audit cannot identify their separate contributions.

Comparing one first-used label per distinct training origin with final revised
truth changes 82/521 core classes (15.7%) and 36/176 CPI classes (20.5%).
“First-used” means first included refit in this experiment, not first release.
Annual revision tables avoid treating repeated appearances of the same origin
as independent observations. Revised labels are used only for this diagnostic,
never fed back into the saved models.

The next benchmark should test simpler feature sets and stronger regularization
using forward-time splits inside each training window, then reassess newspaper
gains. Calibration must use earlier out-of-sample predictions. The current audit
does not select or fit that replacement. Original claims, macro sources,
evaluation rules and forecasts remain unchanged; provenance hashes, monthly
errors, class/period contributions, feature shifts, logit terms and revision
audits are exported alongside the report.

## Simpler macro benchmark with training-only selection

```bash
python src/proquest_macro_benchmark.py
python tests/test_proquest_macro_benchmark.py
```

`data/scored/proquest/macro_benchmark/report.html` completes the replacement
benchmark and repeats the newspaper comparison on the original 408 core and
108 CPI evaluation months. Its specification was saved before these fits,
after the earlier results and error audit were examined. This remains
exploratory historical development.

The twelve macro candidates combine production growth alone or production
growth plus the three-month unemployment change, C in {0.001, 0.01, 0.1},
and expanding or latest-120-month eligible training history. CPI adds its
12-month inflation feature to each candidate. At every January refit, the
prior five January origins supply inner forward-time folds. Each inner model
uses its own historical label vintage and training-only scaling. Validation
labels must be mature and available in the outer January vintage; final
revised evaluation truth never enters selection.

All eligible candidates share the same validation months. Selection minimizes
their mean multiclass Brier loss, requiring 24 validation months across at
least two inner refits. Otherwise a fixed production-only, C=0.001, expanding
default applies, with inflation appended for CPI. CPI uses this fallback in
2002–2004; every core year has sufficient validation. The newspaper model adds
the four existing signals with the macro-selected settings and exactly the
same training rows. The recent base-rate comparator is unchanged.

| Selected model, core 1977–2010 | Brier ↓ | Log loss ↓ | Accuracy |
| --- | ---: | ---: | ---: |
| Recent base rate | 0.6443 | 1.0373 | 42.2% |
| Economy only | 0.6327 | 0.9989 | 35.8% |
| Economy + newspapers | 0.6228 | 0.9606 | 44.1% |

The core macro-only model improves on its original Brier 0.6672 and log loss
1.0882, and now beats the recent base rate on both probability losses.
Adding newspapers gives a smaller Brier improvement of 0.0099, with a paired
five-year-block 95% interval [−0.0637, +0.0808]. Five of eight calendar cells
improve. Excluding 2007–2009, macro-only Brier is 0.6164 versus 0.6214 with
newspapers: the incremental Brier benefit does not survive that check.
Log loss outside the crisis is 0.9626 versus 0.9578, a small newspaper gain.

CPI Brier improves from 0.9216 to 0.6626 for macro-only and from 0.7721 to
0.6588 with newspapers; the unchanged recent base rate is 0.6897. No selected
model in either study makes a forecast above 90% confidence. This removes the
extreme errors seen earlier, but does not prove good calibration. There is a
material tradeoff: CPI fall AUC declines from 0.936 to 0.213 for macro-only
and from 0.987 to 0.277 with newspapers. Accuracy does not improve uniformly.
The short CPI study is still weak for downturn discrimination.

The report includes original-versus-selected metrics, confidence and class
calibration, selected/fallback configurations, crisis and era results, and
paired intervals. CPI has only two five-year bootstrap blocks and one ten-year
block, so those intervals cannot justify strong inference. All intervals
condition on fitted forecasts and omit model-selection uncertainty. Original
data and forecasts remain unchanged. Candidate scores, inner probabilities,
fold timing, vintage labels, selected training rows, preprocessing, coefficients
and final predictions are exported for audit. Reliable incremental newspaper
skill is still not established; repeated evaluation on these historical years
cannot substitute for human label validation or an untouched evaluation set.

## VM daily-quota waiting

Copy `scripts/proquest_enable_quota_wait.py` into the VM's `election_arm`
folder, then apply it there:

```bash
"$PY" proquest_enable_quota_wait.py
```

It backs up and syntax-checks the existing `run_corpus_economy.sh`, then makes
both extraction and verification wait on exit code 2 (daily quota exhausted).
The runner waits 3,600 seconds and retries the same stage/year from saved
progress, repeating until a retry succeeds. It does not assume a reset timezone
or bypass the quota. Other errors retain the runner's existing handling.
`QUOTA_RETRY_SECONDS` can change the interval (integer seconds, minimum 60).

For the modern extension, launch the patched runner from `election_arm`:

```bash
PYTHONUNBUFFERED=1 nohup bash run_corpus_economy.sh \
  2011 2012 2013 2014 2015 2016 2017 2018 \
  2019 2020 2021 2022 2023 2024 2025 2026 \
  > moderndayreal.log 2>&1 &
```

The patch affects subsequent launches, not an already-running job. Run one
pipeline at a time. A terminal disconnect is supported by `nohup`, but stopping
the VM still stops the process. This installer has been prepared locally; it
does not connect to or modify the remote VM. Modern claims must still finish
verification and be exported/imported before they become analysis inputs.

## 2008 crisis and 2009 reversal

```bash
python src/proquest_2008.py
```

The standalone `data/scored/proquest/crisis_2008/report.html` audits publication
cohorts around the financial crisis, with three charts, direction confusion
tables, quarterly timing, exact-horizon composition matching, sensitivity
checks and frozen-reference endpoint examples. Only annual verified claims
enter this descriptive analysis; it fits no model.

Pooled correctness rises from 41.8% in 2007 (2,330 scored claims) to 64.3% in
2008 (9,065), then falls to 36.6% in 2009 (8,555). Business and employment drive
the 2008 rise; price correctness falls to 15.1%. Business worsening calls are
97.9% correct in 2008 but 2.4% correct in 2009. These are horizon-direction
hits, not evidence of predicting the recession's onset. The 2008 peak persists
with equal article weights, grounded horizons, common publishers and tested
alternative thresholds/default horizons.

The query selects downturn/recovery language, quotes have been stripped, and
claims share articles and monthly outcomes. Revised endpoint references,
publication-year/outcome-year differences and broad topic proxies limit
interpretation. Aggregate shifts do not establish that particular forecasters
changed or maintained their views. Reported topic contributions are arithmetic
identities, not causal effects or estimates of individual skill.

## First RNN experiment

```bash
pip install -r requirements-proquest-rnn.txt
python src/proquest_rnn.py
python tests/test_proquest_rnn.py
```

`data/scored/proquest/rnn/report.html` presents a small GRU predicting whether
an individual forecast matches the documented deterministic outcome rule.
It uses claim metadata and the preceding 12 complete months of machine-verified
national forecast patterns. The original quotes are absent, so this is a
temporal metadata model, not a text model. No LOC claims, crisis-window exports,
verifier prose, speaker identities, macro values or realized outcome features
enter the model. Readable verified claims with unscorable outcomes can still
contribute print-time context. Pre-1919 NBER-proxy scores are excluded as targets.

Training publications precede 1985, validation spans 1985–1994, and testing
spans 1995–2010. Outcomes must reach their horizon endpoint plus a conservative
three-month release allowance before the next split; 7,743 unresolved labels
are purged. This yields 70,722 training, 39,536 validation and 56,807 test claims.
The release allowance prevents obvious overlap but does not establish true
historical vintage availability: the benchmark series are revised snapshots.
Categories and scaling are learned only from the training period. Neural epoch
selection uses validation log loss; three preset seeds form an ensemble.

Each article receives equal total training weight. Primary evaluation also
weights articles equally, with claim-weighted results exported separately.
Baselines are constant training prevalence, logistic metadata, and logistic
metadata plus flattened historical inputs. The ensemble's test average
precision is 0.6833 versus 0.5958 for history logistic and 0.5788 for metadata
logistic; its Brier score is 0.1929 versus 0.2364 and 0.2183, respectively.
The five-year-block average-precision gap interval versus history logistic is
[-0.1912, +0.2102], so a stable improvement is not established. This comparison
also cannot separate the effect of recurrence from neural nonlinearity.

The folder contains three `.pt` state-dict checkpoints, train-only preprocessing
and logistic baselines, split assignments, test predictions, subgroup metrics,
training histories and a hash/version manifest. Models are exploratory research
artifacts; future tuning should use forward-time development folds rather than
repeatedly choosing configurations against this already observed test period.

## Political and forecast polarization extension

The author-requested [polarization extension](publication/POLARIZATION.md)
tests two separate backward-looking inputs across all 13 active predictive
configurations, including the GRU and its logistic controls. Each has baseline,
political-only, forecast-only, and combined arms. Existing model outputs remain
unchanged; this is exploratory work on the same annual 1900–2010 population.

The political proxy measures earlier Democratic–Republican House voting
separation, with a one-complete-month reporting buffer. It avoids current
career-based NOMINATE estimates that can incorporate later votes. The forecast
measure is the preceding-three-month mean of four times the positive and
negative general-business shares; it distinguishes opposing camps from the
existing three-category disagreement measure. Missingness and preprocessing
use training data only. Neither measure establishes newspaper political slant.

```bash
python src/proquest_polarization.py --download
python src/proquest_polarization_models.py --task monthly
python src/proquest_polarization_models.py --task claims
python src/report_proquest_polarization.py
python tests/test_proquest_polarization.py
```

The [report](../data/scored/proquest/polarization/report.html) contains all
comparisons, source/timing audits, calibration, and paired intervals. Adding
both measures worsens selected core macro-plus-press Brier from 0.6228 to
0.6644 and GRU Brier from 0.1929 to 0.1991. The corresponding improvement
intervals are [−0.0788, −0.0186] and [−0.0456, +0.0151]. Binary and multiclass
Brier are separate estimands. Short CPI results are mixed and have only two
five-year blocks. These findings do not justify replacing the primary models
or concluding that polarization has no economic relevance.

## Saved RNN audit and modern preparation

The [RNN audit](publication/RNN_AUDIT.md) analyzes saved probabilities without
new fits. Run `python src/proquest_rnn_audit.py` to rebuild its report and
year/topic/horizon/paper/seed tables in `data/scored/proquest/rnn_audit/`.
Subgroup contributions retain the full-test article weights and reconcile
exactly to the overall loss differences. Source validation is deferred.

The [modern preparation specification](publication/MODERN_EVALUATION.md)
defines a separate prospective execution procedure and documents prior
historical exploration. `python src/proquest_modern_intake.py --prepare`
records a model/specification hash freeze and a deliberately incomplete VM
manifest template in `data/scored/proquest/modern_readiness/`. The utility
can reconcile supplied modern exports and stage counts but never scores them.
Modern data, processing records, and prior-exposure documentation remain
pending. This does not change the active 1900–2010 analysis scope.

Modern evaluation was subsequently deferred at the author's request. The
[reusable RNN runner](PROQUEST_RNN_RUNNER.md) provides `predict` and `train`
commands with explicit input files, chronological splits, and new output
folders. It reproduces the saved historical predictions exactly and excludes
outcome columns from prediction input. The [permutation diagnostics](../data/scored/proquest/rnn_permutation/report.html)
find reliance on history/order, but conditional five-year-block permutation
p-values of 0.3125 and 0.2500 do not establish GRU superiority to its logistic
controls. See the linked guide for input contracts and future-data usage.

The subsequent [forward-time development experiment](publication/RNN_DEVELOPMENT.md)
selected an 8-unit GRU with a 20-year training window from a fixed eight-setting
grid. It improved three of four pre-1985 development blocks and both later
confirmation blocks; confirmation mean Brier fell from 0.16198 to 0.15741.
Early-1980s loss worsened. The saved candidate is provisional and reusable via
the runner's `--configuration` option. No 1995–2010 results were re-evaluated,
no permutation threshold was optimized, and original frozen models remain
unchanged. Previously explored historical confirmation years do not constitute
a fresh holdout.

## Topic accuracy gaps and paired uncertainty

October 19, 2026: `src/proquest_target_robustness.py` adds paired uncertainty
around the existing descriptive newspaper-minus-fixed-baseline gaps. The
[analysis report](../data/scored/proquest/target_robustness_v1/report.html)
uses saved annual ProQuest scores without rescoring claims or fitting models.
It reconciles the verified topic point estimates exactly to the existing
evidence table. Source validation, modern evaluation, and manuscript work
remain deferred.

With equal total weight per article within each topic, the primary five-year
publication-block 95% percentile intervals are:

| Legacy topic | Accuracy gap, percentage points | 95% interval | Occupied blocks |
| --- | ---: | ---: | ---: |
| General business | −12.37 | [−22.59, −2.09] | 23 |
| Markets | −19.59 | [−30.47, −7.01] | 23 |
| Prices | −28.57 | [−34.40, −20.15] | 21 |
| Employment | +13.73 | [+0.94, +26.32] | 14 |

Business, market, and price gaps have intervals below zero for all three
planned block lengths (2, 5, and 10 years). Employment intervals include zero
with two- and ten-year blocks, so the five-year result alone should not support
a stable superiority claim. Its unemployment-rate proxy also requires source
interpretation. These marginal intervals do not adjust for multiple comparisons.

The all-topic article-weighted gap is −12.70 points, with a five-year interval
of [−21.67, −3.46]. Restricting to machine-labeled stated horizons changes the
population and gives −9.45 points [−16.74, −2.22]; this is not a strict or
source-validated subset. Removing NBER proxy outcomes gives −12.82 points
[−21.98, −3.58]. All-topic and within-topic weighting are different estimands.

Every topic retains its point-estimate direction after each individual
five-year block is removed. The report retains raw-export sensitivity, equal
month weights, machine-stated and non-NBER subsets, all block lengths, and
every leave-one-block-out estimate. No exclusion or block length was selected
to improve a p-value; no new p-values were calculated.

Intervals use 5,000 paired resamples of occupied calendar blocks anchored at
1900, retaining newspaper and baseline correctness together. They describe
temporal variability conditional on the recovered corpus and fixed scoring.
Nonstationarity, overlapping outcomes across block boundaries, retrieval
selection, and unmeasured source-interpretation error limit inference.

Run in a working environment:

```bash
python src/proquest_target_robustness.py
python tests/test_proquest_target_robustness.py
```

The builder refuses an existing output folder. Its specification, input/source/
reference hashes, complete comparison tables, block support, figure, and output
hashes are retained under `data/scored/proquest/target_robustness_v1/`. Four
new checks cover paired uncertainty, article weighting, subset weights, and
scope/address rejection. Required offline/scoring/forecast checks passed
97/33/33. Original exports and model artifacts remain unchanged.

## Reproducibility handoff and analysis deep dive

The [reproducibility guide](PROQUEST_REPRODUCIBILITY.md) identifies primary,
exploratory, superseded and unpromoted results and documents the isolated
rebuild. The [data handoff](PROQUEST_DATA_HANDOFF.md) supplies commands for
export normalization, optional mature-outcome scoring, polarization features,
and later model application/refitting. Historical normalization reproduces
274,070 claims, deterministic scoring reproduces 175,855 eligible outcomes,
and the polarization adapter reproduces all 1,332 historical feature months.

The [analysis deep dive](PROQUEST_ANALYSIS_DEEP_DIVE.md) documents a material
comparator/horizon sensitivity: employment forecasts beat the original
unemployment-decline baseline but have lower observed accuracy than an
always-flat rule, especially at 1–6 month machine-stated horizons. Neutral
forecast labels are much rarer than neutral scored outcomes across topics.
An article-direction audit retains and counts multiple direction labels within
the same article/topic/outcome/horizon groups without calling them duplicates
or contradictions. These checks make source interpretation more consequential;
they do not establish its correctness. Primary comparisons and scoring rules
remain unchanged, and no new superiority p-values were computed.

The subsequent [benchmark interpretation experiment](../data/scored/proquest/benchmark_interpretation_v2/report.html)
tests original, duration-scaled and direction-only outcome bands on identical
claims against all three constant directions. Short-horizon employment's
comparison with flat reverses under duration scaling; the business, market
and price deficits against the original fixed direction persist. These are
exploratory measurement sensitivities, not improved model predictions or
validated corrections. See the deep dive for the decision table and rerun
command; the original RNN targets and p-values remain unchanged.

The [additional benchmark/input review](../data/scored/proquest/benchmark_input_review_v1/report.html)
adds matched production/unemployment inputs to the RNN and both logistic
controls, using historical-vintage fitting/stopping labels. Production helps
the RNN mainly for business claims; metadata-only logistic remains stronger
overall in this experiment. Separate payroll and GDP outcome sensitivities
show that employment's apparent advantage depends on which labor-market
quantity is scored. Every arm and benchmark is retained, without promotion.
See the deep dive for matched populations, timing, uncertainty and commands.
