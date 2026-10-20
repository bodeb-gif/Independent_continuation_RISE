# RNN error and stability audit

October 19, 2026. This audit uses saved predictions for 56,807 annual verified ProQuest claims, from 24,938 articles published in 1995–2010. No models were refitted and no source passages or human judgments were reviewed. The [full report](../../data/scored/proquest/rnn_audit/report.html) contains annual and calibration figures; the adjacent CSVs provide year, topic, paper, horizon, period, and seed results.

The baseline GRU remains the primary RNN comparison. Neither polarization measure, separately or together, improves its overall Brier score. The important qualification is that the extensions behave differently across periods.

| Saved ensemble | All test years | 2007–2009 | Outside 2007–2009 |
| --- | ---: | ---: | ---: |
| Baseline | 0.1929 | 0.1938 | 0.1924 |
| Political only | 0.2144 | 0.2684 | 0.1851 |
| Forecast only | 0.1997 | 0.2365 | 0.1797 |
| Both | 0.1991 | 0.1817 | 0.2086 |

Binary Brier loss; lower is better. Each test article has total weight one. Subgroups retain their portion of those original weights, so an article spanning topics is not counted as a whole article in every topic. Periods refer to publication years, not necessarily the entire forecast outcome window. The 2007–2009 cohort contains 19,950 claims from 8,777 articles, representing 35.2% of test article weight.

## What accounts for the deterioration

Political-only loss rises in 2007–2009 for all three seeds: +0.0827, +0.0813, and +0.0518 relative to the corresponding baseline seed. This result is not driven by one unlucky seed. Matching seed numbers does not guarantee identical initialization when input dimensions change, so it does not isolate a causal feature effect.

General-business forecasts are the largest contributor. In 2007–2009, their Brier loss rises from 0.1965 to 0.2976. That subgroup contributes +0.02125 to the full-test loss change, compared with the net overall increase of +0.02148. Employment and market forecasts also deteriorate in that period; prices improve. Improvements in earlier years offset some losses. These are exact weighted contributions, not a claim that this subgroup causes the deterioration.

The political-only ensemble distinguishes correct and incorrect claims much less clearly in 2007–2009. Its mean predicted correctness is 0.3732 for claims that were correct and 0.3339 for claims that were incorrect. The baseline means are 0.5034 and 0.2873. The political-only model also underpredicts the cohort's correctness rate: mean prediction 0.3535 versus observed 0.4989. This supports an account involving weaker separation and underprediction, rather than more extremely confident mistakes. At the symmetric 90% confidence threshold, its weighted share of incorrect predictions is zero, versus 0.0711% for baseline. Low extreme-error frequency does not imply good calibration.

Political-only loss rises in all three horizon buckets. The 7–12-month bucket contributes +0.01871 of the +0.02148 overall increase, largely because it holds most claims. The largest within-bucket increase is for 13–24 months (+0.03397), based on only 1,857 claims. Exported numeric or “stated” horizons remain machine labels; this audit does not establish that source text explicitly supports them.

The political input averages 1.86 training standard deviations above its training mean in 2007–2009, versus 0.93 outside those years. No test claim lies beyond three training standard deviations for either added scalar. This rules out gross three-standard-deviation extrapolation as a complete explanation; it does not rule out distribution change, interactions, agenda changes, or proxy limitations. All political-only runs selected epoch 3 using validation loss; the baseline selected epochs 4, 6, and 5. These records help describe training behavior without selecting new epochs from test outcomes.

Both features together have the reverse period pattern: improvement during 2007–2009, deterioration outside. Consequently, it would be inaccurate to say that every polarization extension fails specifically during the financial crisis. The overall evidence supports retaining all four arms as an exploratory comparison, with no additional tuning selected from these test years.

## Interpretation and reproduction

The existing paired five-year-block intervals remain the uncertainty analysis. The historical test spans only four such blocks, and its 2007–2009 subset cannot support precise independent-era inference. Subgroup tables are descriptive; no new significance or causal claim follows from them. All results remain conditional on the existing deterministic scoring and unvalidated claim mappings.

```bash
MPLCONFIGDIR=/tmp/bode-econ-mpl python src/proquest_rnn_audit.py
python tests/test_proquest_rnn_audit.py
```

The builder checks saved input/output hashes, joins on unique source-local record addresses, checks article/date/outcome agreement, reconciles ensemble means and previously reported metrics, and verifies that every subgroup partition adds to the overall loss difference. The [audit manifest](../../data/scored/proquest/rnn_audit/summary.json) records these checks and file hashes. Original exports and fitted-model artifacts are unchanged.

## Permutation diagnostics

The October 19 [permutation report](../../data/scored/proquest/rnn_permutation/report.html) adds diagnostics of the frozen models. The primary comparisons enumerate all 16 ways of swapping paired model predictions within four five-year publication blocks. Positive improvements below favor the GRU. These conditional tests assume blockwise model-label exchangeability, a stronger condition than equal mean loss; cross-block outcome dependence and few eras limit inference. They are not target-permutation tests proving learning versus chance. [Paired permutation methodology](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.permutation_test.html).

| Baseline GRU compared with | Brier improvement | One-sided permutation p | Holm p for two primary comparisons |
| --- | ---: | ---: | ---: |
| Metadata logistic | 0.02542 | 0.3125 | 0.5000 |
| Metadata plus history logistic | 0.04348 | 0.2500 | 0.5000 |
| Frozen training-prevalence control, secondary | 0.05084 | 0.1250 | — |

None establishes a stable superiority claim. Even the smallest possible unadjusted one-sided p-value with four blocks is 1/16 = 0.0625. The dates and models were already explored before these diagnostics, so results remain exploratory.

Input permutations show meaningful reliance on history. Across the 23 nonidentity permutations of four 48-month origin blocks, baseline GRU mean Brier rises from 0.19291 to 0.23162, an increase of 0.03871. Reversing the twelve monthly steps produces Brier 0.21645; 99 random step reorderings average 0.20525. Each retains the current claim metadata and the original outcomes. These diagnostics support reliance on history and order, but do not isolate architectural superiority to a nonrecurrent neural model.

In the combined model, mean Brier increases are +0.04694 for sequence permutation, +0.00222 for forecast polarization, and −0.00015 for political polarization. Political-only permutation likewise slightly improves mean loss (−0.00056). These are fitted-model dependence measures; correlated inputs and synthetic combinations prevent causal interpretations. The permutation quantiles describe variation across perturbations, not sampling confidence intervals. [Permutation importance interpretation](https://scikit-learn.org/stable/modules/permutation_importance).

The [reusable runner](../PROQUEST_RNN_RUNNER.md) now accepts explicit input paths, time splits, and versioned output folders for applying or retraining all four RNN arms and their logistic controls. Modern evaluation is deferred at the author's request; source validation remains untouched.
