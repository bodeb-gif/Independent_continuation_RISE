# Forward-time RNN development

October 19, 2026. A smaller GRU with a recent training window passed the improvement rule recorded before this experiment. It is a provisional development candidate, not a replacement for the frozen primary research model. This study used verified annual ProQuest publications before 1995; it did not re-evaluate 1995–2010 or use modern exports. Source validation remains deferred.

## Procedure fixed before fitting

The [specification](../../data/scored/proquest/rnn_development_v1/specification.json) compares eight configurations: hidden dimension 24 or 8; standard regularization (dropout 0.15, weight decay 0.001) or stronger regularization (0.35, 0.01); and expanding or 20-year training history. The reference uses 24 units, standard regularization, and expanding history. All configurations retain seeds 11, 29, and 47 and average their probabilities. The twelve-month context, claim features, article weighting, optimizer, and stopping rule are unchanged. Political and forecast polarization were not additional search dimensions; their existing four-arm results remain separate.

Development assessment blocks begin in 1965, 1970, 1975, and 1980 and each cover five publication years. At origin T, the preceding five years select the stopping epoch, and earlier years fit parameters. For the recent-window candidate, training covers T−25 through T−5 years. Scalers and categorical vocabularies fit training data only. Labels must mature, with the existing three-month allowance, strictly before the next stage; assessment labels must mature before their block ends. Articles cannot cross stages. Monthly context uses preceding complete months without outcome or verifier-prose inputs.

Selection uses equal-weight mean Brier loss across the four development blocks. An alternative must improve that mean by at least 0.002 and win at least three blocks; the qualifying candidate with the lowest mean wins. Only the selected configuration and reference then enter the 1985–1989 and 1990–1994 confirmation blocks. Promotion requires improvement in both and a mean gain of at least 0.002. These historical years were used in earlier project development, so confirmation is not a previously untouched holdout. There was no tuning after these confirmation results.

## Results

The selected configuration is **8 hidden units, standard regularization, and a 20-year training window**. All figures below are article-weighted Brier losses; lower is better. Multi-block means weight eras equally rather than pooling claims.

| Assessment | Reference | Selected candidate |
| --- | ---: | ---: |
| Four development blocks, mean | 0.19059 | 0.18086 |
| 1980–1984 development block | 0.22363 | 0.25825 |
| 1985–1989 confirmation | 0.16081 | 0.15770 |
| 1990–1994 confirmation | 0.16315 | 0.15712 |
| Two confirmation blocks, mean | 0.16198 | 0.15741 |

The candidate wins three of four development blocks and both later confirmation blocks. Confirmation mean Brier falls by 0.00457, approximately 2.8%. Classification accuracy barely changes: 81.66% to 81.56% in the first confirmation block, and 81.08% to 81.10% in the second. AUC improves in the first block and declines in the second. The improvement is in average probability loss, and the early-1980s deterioration is a material limitation.

The [full report](../../data/scored/proquest/rnn_development_v1/report.html) retains all eight configurations, fold results, and confirmation metrics. Selection and confirmation scores do not establish statistical significance. No new permutation p-value was calculated, and the original p=0.250 result is unchanged. The original five-year inference blocks were not shortened to obtain a desired result.

## Saved candidate and replication

The [selected bundle manifest](../../data/scored/proquest/rnn_development_v1/bundles/gru8_standard_20/bundle_manifest.json) identifies the configuration, three checkpoints, and preprocessing. Its final fit uses the 1970–1989 training window, with label-maturity purging, and stopping on eligible 1990–1994 claims. An expanding-history reference bundle is also saved. Their final `predictions.csv.gz` and `metrics.json` describe the stopping window, not independent assessment: the reference has Brier 0.12212 and the candidate 0.12499 there. Those stopping scores did not change the selection decision.

The [runner guide](../PROQUEST_RNN_RUNNER.md) explains inference and configuration-based retraining on replacement data. New settings can be loaded directly from the selected bundle manifest. This experiment fits only the baseline feature arm; the reusable runner can apply the settings to explicitly requested polarization arms in a separately recorded run.

The experiment made 114 neural fits. Its [summary and output hashes](../../data/scored/proquest/rnn_development_v1/summary.json) preserve the input snapshot, script hash, software versions, selection, and output provenance. Original frozen models and source exports remain unchanged. Running `python src/proquest_rnn_development.py` refuses to overwrite this version; preserve it when creating a later experiment.

Verification covered nested temporal purging, train-only preprocessing, exclusion of post-1994 data, invariance of fitted weights to assessment outcomes, exact reference-training equivalence, and the selection rule. Configuration-based retraining and checkpoint reload passed synthetic checks. The selected real bundle was also reloaded on 1990–1994 inputs and compared with its saved stopping predictions; [reproduction results](../../data/scored/proquest/rnn_development_v1_reload_check/reproduction.json). The required offline, scoring, and forecasts suites passed 97/33/33 checks; development and runner suites passed 5/6 tests.

Further changes should receive a new development specification. The next independent assessment needs a separately authorized evaluation with exposure documented; repeatedly revisiting the inspected historical test would not provide fresh confirmation. This experiment does not resolve source-label uncertainty or the use of revised outcome series.

## Gradual age weighting follow-up

Later on October 19, a fixed follow-up tested exponential training-weight half-lives of 10, 20, and 40 years in the 8-unit expanding-history model. All 36 fits used the same three seeds and four development blocks through 1984. This was motivated by previously inspected errors and is exploratory. No later confirmation or test predictions were evaluated.

Training article weights were multiplied by `2 ** (-age_years / half_life_years)`, with age measured from the start of the stopping window, then normalized to mean one. Stopping and assessment weights remained unchanged. Train-only preprocessing was kept identical to the unweighted expanding-history control, isolating the effect of weighting the fitting loss. See the [fixed specification](../../data/scored/proquest/rnn_age_weighting_v1/specification.json) and [complete results](../../data/scored/proquest/rnn_age_weighting_v1/report.html).

| Training weights | Mean development Brier | Worst-block Brier | Blocks improved over current candidate |
| --- | ---: | ---: | ---: |
| Current 20-year cutoff | 0.180864 | 0.258254 | — |
| 10-year half-life | 0.180495 | 0.235097 | 2 of 4 |
| 20-year half-life | 0.180110 | 0.222627 | 1 of 4 |
| 40-year half-life | 0.179436 | 0.211065 | 1 of 4 |
| Unweighted expanding history, 8 units | 0.183380 | 0.221764 | 2 of 4 |

The 40-year half-life lowered mean loss by 0.001427, about 0.79%, and reduced the early-1980s deterioration. It worsened each of the other three blocks. None passed the fixed requirement of at least 0.002 mean improvement and improvements in three blocks, alongside the worst-block and unweighted-control checks. **Retain the current candidate.** No new p-value was calculated and no final replacement bundle was fitted.

The runner now accepts an optional `half_life_years` configuration setting for future explicitly configured training, including its logistic controls. Omitting it preserves previous behavior. The [study summary](../../data/scored/proquest/rnn_age_weighting_v1/summary.json) records hashes, settings, and all retained outputs. Weight-concentration diagnostics are descriptive, not estimates of independent sample size. Three weighting/scope/selection tests, seven runner tests, five development tests, and the required 97/33/33 offline/scoring/forecast checks passed.
