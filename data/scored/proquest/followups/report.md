# ProQuest descriptive follow-ups

Annual machine-verified ProQuest claims only. No LOC analysis, old crisis-window files, or ML models.

## False alarms versus missed output declines

Among 108,535 production-scored business forecasts, 22.8% of worsening calls are followed by an output decline beyond 2%. The calls warn about 57.6% of actual declines; 42.4% are missed. The false-alarm rate among nondeclining outcomes is 47.3%.

A miss includes improve or flat calls when output actually falls. A false alarm includes a worsening call followed by growth or flat output. These are claim-level industrial-production declines over each forecast horizon, not a count of NBER recessions successfully predicted. Pre-1919 NBER proxy scores are excluded from this comparison.

Overall and claim-grounded horizon checks

| subset | n_claims | warning_precision | decline_recall | miss_rate | false_alarm_rate |
| --- | --- | --- | --- | --- | --- |
| Production, all eligible horizons | 108,535 | 22.8% | 57.6% | 42.4% | 47.3% |
| Production, claim-grounded horizons | 57,648 | 20.8% | 50.7% | 49.3% | 41.8% |

Publisher warning tradeoffs (at least 500 production-scored claims)

| paper | n_claims | warning_precision | decline_recall | false_alarm_rate |
| --- | --- | --- | --- | --- |
| Barron's | 7,847 | 24.4% | 38.7% | 33.0% |
| Boston Globe | 7,575 | 26.9% | 52.1% | 44.6% |
| Chicago Tribune | 12,391 | 20.4% | 55.9% | 49.1% |
| Christian Science Monitor | 2,148 | 16.4% | 60.9% | 50.3% |
| Los Angeles Times | 23,200 | 18.9% | 58.3% | 49.9% |
| New York Times | 23,617 | 28.1% | 55.5% | 45.8% |
| Wall Street Journal | 20,962 | 18.4% | 70.6% | 48.4% |
| Washington Post | 10,742 | 29.2% | 63.9% | 51.6% |

## Were warnings early?

Among 16 recessions with at least 30 directional forecasts in each phase, the event-weighted worsening share is 45.5% 7–12 months before onset, 53.1% 1–6 months before, and 50.9% in the first six recession months.

This uses national, readable improve/worsen business forecasts, including those with unscorable horizons. Recession starts come from the continuous USREC chronology, not the abandoned crisis-window exports. The graph includes event-months with at least 10 forecasts; the number of contributing events varies, so read its lower panel. Each claim is assigned to the nearest onset within 24 months before through 12 months after; no claim is counted at multiple onsets.

The phase comparison weights each matched event equally, requires 30 claims in every phase, and restricts pre-onset forecasts to expansion months and after-onset forecasts to recession months. These are worsening expectations, not necessarily literal recession predictions. Recession dating is retrospective and used only for descriptive outcomes, never to construct an ex-ante model feature.

Same-event warning comparison

| phase | event_equal_warning_share | n_events | n_claims |
| --- | --- | --- | --- |
| 7–12 months before | 45.5% | 16 | 5,666 |
| 1–6 months before | 53.1% | 16 | 7,540 |
| 0–5 months after | 50.9% | 16 | 15,751 |

## Consensus versus contrarians

Forecasts agreeing with a clear earlier other-paper consensus have a raw hit rate of 49.1%; contrarians have 29.5%. The matched agreement-minus-contrarian gap is +10.7 percentage points, comparing the same paper, publication month, topic, benchmark, horizon basis, and exact horizon. Each cell requires five agreement and five contrarian claims.

The five-year block-resampling interval for that gap is -16.1 to +29.2 percentage points. It crosses zero: the pooled advantage is unstable across historical periods and does not establish a consistently superior strategy.

Consensus uses only predictions in the preceding 90 calendar days, excluding the current date and the current paper. It requires at least 20 earlier claims from two other papers in the same topic, benchmark, horizon-basis and horizon-bucket group, with at least 60% backing one normalized direction. Flat is a valid direction. No future predictions or realized outcomes form consensus. A contrarian label is a descriptive comparison, not evidence that the speaker knew or opposed those other forecasts.

The disagreement diagnostic below restricts production forecasts to months retrospectively classified as expansion. It compares earlier agreement strength with an onset in the next 12 months. Publication months have equal weight within each group; a month can appear in more than one group. Topic, horizon and era composition can still differ, so these are descriptive associations. The month-weighted onset shares are very similar (20.6–21.4%); the apparent claim-weighted gradient largely disappears when heavily represented months receive less weight.

Prior-only consensus groups

| consensus | n_claims | hit_rate | fixed_baseline |
| --- | --- | --- | --- |
| Agrees with prior consensus | 56,794 | 49.1% | 45.7% |
| Contrarian | 28,090 | 29.5% | 51.3% |
| Insufficient peers | 35,824 | 39.9% | 53.0% |
| No clear consensus | 55,147 | 38.7% | 63.3% |

Earlier agreement strength and later recession onset

| prior_agreement | n_claims | n_months | recession_within_12_months_share | production_decline_share | month_equal_recession_share |
| --- | --- | --- | --- | --- | --- |
| At most 60% | 28,719 | 577 | 14.7% | 6.2% | 20.6% |
| 60–75% | 27,515 | 636 | 20.1% | 12.0% | 21.2% |
| Above 75% | 9,686 | 369 | 26.4% | 18.1% | 21.4% |

## Forecast horizon

For explicit numeric horizons, a matched 6-month versus 12-month comparison gives 35.2% versus 45.7% (-10.5 percentage points).

The chart excludes default and inferred horizons. The direct 6/12-month comparison uses the same papers, years, topics, and benchmarks, requires at least 10 claims for each horizon in each cell, and weights both horizons by the same overlap distribution. The 6-minus-12-month fixed-baseline gap is -19.2 percentage points; the forecast gap beyond that baseline is +8.7 points. Thus the higher raw 12-month hit rate does not establish better skill: the baseline advantage is larger. Horizon choice was not randomized, so differences are not causal.

Explicit-horizon results by topic

| topic | horizon_band | n_claims | hit_rate | fixed_baseline |
| --- | --- | --- | --- | --- |
| employment | 1–3 | 953 | 11.6% | 1.4% |
| employment | 4–6 | 2,479 | 29.6% | 9.7% |
| employment | 7–12 | 5,578 | 39.3% | 27.2% |
| employment | 13–24 | 250 | 46.0% | 50.0% |
| general_business | 1–3 | 4,307 | 17.9% | 11.8% |
| general_business | 4–6 | 16,886 | 35.6% | 37.0% |
| general_business | 7–12 | 31,502 | 45.4% | 59.9% |
| general_business | 13–24 | 1,105 | 42.3% | 71.9% |
| markets | 1–3 | 1,810 | 18.8% | 18.7% |
| markets | 4–6 | 3,764 | 35.5% | 49.5% |
| markets | 7–12 | 5,960 | 45.3% | 63.1% |
| markets | 13–24 | 271 | 48.3% | 73.4% |
| prices | 1–3 | 935 | 12.4% | 10.8% |
| prices | 4–6 | 2,981 | 36.5% | 64.1% |
| prices | 7–12 | 6,663 | 54.6% | 86.9% |
| prices | 13–24 | 249 | 55.0% | 95.6% |

## Publisher specialties and ranking stability

Among publisher/topic groups with at least 500 scored claims: Boston Globe has the highest raw employment rate (39.7%); Barron's has the highest raw markets rate (41.7%); Barron's has the highest raw general business rate (45.9%); Chicago Tribune has the highest raw prices rate (55.7%). These raw leaders are not baseline-relative skill rankings.

Raw topic hit rates answer which published calls came true most often. Coverage-adjusted gaps answer a narrower question: how a paper compared to other papers forecasting similar years, topics, benchmarks, horizon bases, and horizon buckets. The heatmap masks cells below 200 claims; rankings include publishers with at least 500 scored claims.

Each pairwise publisher comparison keeps only cells with at least 10 claims from both papers and uses harmonic-overlap weights for identical composition on both sides. The ranking averages each paper's gaps across available opponents with equal opponent weight; different pairs still have different shared coverage, so this is not a universal common-period tournament. Five-year block intervals for each pair are in publisher_pairwise_matched.csv; multiple comparisons are exploratory.

Coverage correction: the machine-verified Wall Street Journal claims begin in 1984, not 1960 as the first report stated. Chicago Tribune coverage ends in 2001. The earlier report and its generator have been corrected. Decade cells can cover only part of a decade: Chicago in the 2000s covers 2000–2001, and all 2010s cells cover 2010 only.

Actual coverage of scored claims

| paper | first_year | last_year | n_claims |
| --- | --- | --- | --- |
| Barron's | 1,921 | 2,010 | 13,721 |
| Boston Globe | 1,900 | 2,010 | 11,938 |
| Chicago Tribune | 1,900 | 2,001 | 20,040 |
| Christian Science Monitor | 1,980 | 2,010 | 3,497 |
| Los Angeles Times | 1,901 | 2,010 | 36,420 |
| New York Times | 1,900 | 2,010 | 37,036 |
| USA Today | 1,992 | 2,010 | 94 |
| Wall Street Journal | 1,984 | 2,010 | 35,927 |
| Washington Post | 1,900 | 2,010 | 17,182 |

Mean pairwise coverage-adjusted gaps

| paper | n_opponents | mean_pairwise_matched_gap | mean_gap_beyond_baseline |
| --- | --- | --- | --- |
| Barron's | 7 | 3.2% | 2.1% |
| Chicago Tribune | 7 | 0.8% | 0.4% |
| Boston Globe | 7 | 0.6% | 0.9% |
| Wall Street Journal | 7 | 0.5% | 0.9% |
| New York Times | 7 | 0.0% | 0.3% |
| Los Angeles Times | 7 | -0.6% | -0.2% |
| Washington Post | 7 | -1.3% | -1.1% |
| Christian Science Monitor | 7 | -3.0% | -3.3% |

## Who made the forecast?

Within matched paper/year/topic/benchmark/horizon cells, expert-attributed forecasts score 42.0%, versus 42.4% for journalists (-0.5 percentage points).

The five-year block interval for the expert-minus-journalist gap is -3.2 to +2.0 points, providing no clear separation in this comparison.

Speaker attribution is noisy. Names are normalized only for capitalization, punctuation, and spacing; initials, surname-only forms, titles, and similar names are not automatically merged. The listed names are attribution strings and may denote an institution. The attribution coverage table highlights strings with 100 scored claims, at least five distinct publication years, and at least two newspaper families. There are 58 sufficiently represented attribution strings. The alphabetized CSV provides coverage counts for later source-quote review; identities still need validation.

Experts versus journalists within matched cells, by publisher (at least 100 claims in each group)

| paper | left_claims_in_cells | right_claims_in_cells | left_matched_hit_rate | right_matched_hit_rate | matched_gap |
| --- | --- | --- | --- | --- | --- |
| Barron's | 1,628 | 355 | 52.9% | 56.7% | -3.7% |
| Boston Globe | 1,271 | 240 | 48.2% | 54.1% | -5.8% |
| Chicago Tribune | 3,177 | 401 | 36.0% | 34.5% | 1.5% |
| Los Angeles Times | 12,063 | 1,693 | 38.7% | 40.8% | -2.1% |
| New York Times | 9,317 | 1,517 | 45.2% | 48.9% | -3.7% |
| Wall Street Journal | 14,529 | 2,113 | 39.9% | 37.0% | 3.0% |
| Washington Post | 3,146 | 641 | 46.3% | 43.2% | 3.1% |

## Interpretation and reproducibility

All outcome rates reuse the first report's documented national-scope and benchmark rules. Market forecasts remain a provisional broad-stock-price proxy. Machine verification is not human validation, and stripped quotes prevent semantic rechecking and definitive deduplication locally. Claim counts are not independent trials. Equal-weight events, shared-cell comparisons, and block resampling reduce some confounding but do not make these observational results causal.

Run python src/proquest_followups.py from the repository root. Source and reference digests are recorded in summary.json. The saved outcome rows are checked one-to-one against every annual verified export before the analysis starts. LOC data, raw/unverified candidates, and old window shards are never loaded. No numerical confidence probabilities, ML model, or page-denominator attention rate is invented.
