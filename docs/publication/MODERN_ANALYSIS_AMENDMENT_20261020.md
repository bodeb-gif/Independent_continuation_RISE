# Modern analysis activation — October 20, 2026

The author explicitly authorized analyzing the received modern exports, applying
existing models, ignoring empty 2011 records as model inputs, and developing
separate 12-month recession-onset and industrial-production-decline forecasts.
This activates a separate modern study; historical tables and frozen artifacts
remain unchanged. All empty rows are excluded from model inputs, not only 2011.
The original files retain their bytes and source-line addresses. The cause of
the repeated empty rows is not established.

This dated amendment is written before comparative modern model results are
opened. The supplied export manifest passes transport checks but is not the
frozen readiness manifest. Full processing-flow/log/model provenance remains
incomplete. Analysis is exploratory and conditional on received exports; it is
not certified end-to-end intake or an untouched holdout. The author's response
about prior validation refers to the extraction process, not an explicit
statement of no prior exposure to modern outcomes. Exposure remains unknown.
The 19 default-kept verification exceptions are excluded from primary inputs
and retained in an explicit exclusion table. No other label deduplication occurs.
Historical human review is supporting process evidence, not direct validation
of the 2011–2026 population.

## Claim correctness

Retain the frozen baseline GRU three-seed ensemble as primary, its two logistic
controls and every polarization arm as secondary. Also report the previously
selected historical `gru8_standard_20` development bundle as a clearly labeled
challenger, without selecting models on modern results. Reproduce saved
historical probabilities before applying models. Keep all learned parameters
unchanged. Outcomes use the original deterministic rules and a three-month
maturity allowance as of 2026-10-20, with newly frozen reference snapshots.
Article-weighted Brier is primary; report other metrics, calibration and
breakdowns. Paired uncertainty uses complete five-year blocks anchored at 2011,
2,000 draws, seed 20261014. These intervals have few independent blocks.

## Separate downturn targets

The claim RNN predicts whether an extracted forecast is correct; its output is
not a recession probability. Build separate monthly binary logistic models from
the existing print-time newspaper/polarization features for the requested tasks:

- Recession onset: any transition from USREC=0 to 1 in months t through t+11.
  An existing recession at t-1 is not a new onset. Use a conservative 24-month
  endpoint-to-training allowance for retrospective recession dating.
- Production decline: INDPRO at t+11 below t-1 (12 monthly intervals); the main
  definition is any decline, with a greater-than-2% decline reported separately.
  Use a three-month endpoint-to-training allowance. Full reference coverage is
  required; unresolved targets are not filled or used to train.

Compare an expanding Laplace-smoothed event base rate and four ridge logistic
variants: press alone, press plus political polarization, press plus forecast
polarization, and press plus both. Reuse existing four press features, support
rules, lagged polarization definitions and training-only median imputation,
scaling and missingness indicators. C=1; no modern tuning. Annual January refits
use only mature prior labels. Choose the primary candidate on pre-2011 rolling
Brier (1950–2010, training origins from 1919 where coverage permits), then retain
that choice through modern evaluation and the latest forecast. Report all
comparators even if the historical base rate wins. Revised outcome series and
current vote reconstructions are not archived real-time vintages; no revised
macro values enter predictor features. These exploratory targets are new,
not a preexisting validated recession forecasting model.

The modern corpus ends September 1, 2026; use complete print months through
August for the latest September 2026 origin, covering September 2026–August
2027. This is a dated research forecast, not a current October-origin forecast.
Do not claim an October-origin forecast without September corpus completeness.
Report recent support and probabilities, not certainty about a future recession.
The number of distinct recession onsets matters more than the count of
correlated monthly labels, and overlapping 12-month outcomes are dependent.

Preparation findings before comparative scoring: public FRED CSV requests
returned HTTP 404, so unchanged existing local snapshots are frozen for this
run (INDPRO/CPI/UNRATE through June 2026; USREC through July; Shiller through
September). Those cover the claim endpoint maturity cutoff. Voteview Congress
115 contains 36 exactly repeated keyed casts with identical vote codes and no
conflicts. Count each keyed cast once in the derived vote feature and record the
exclusion count. Conflicting keyed casts still fail. No ProQuest claim labels
are deduplicated, and no frozen implementation is edited.
