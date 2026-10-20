# Political and forecast polarization

Exploratory extension requested October 14, 2026. Both measures have been tested separately and jointly across **13 active ProQuest model configurations**, including the GRU ensemble and its two logistic controls. Existing publication results and original model outputs remain intact. No LOC models or modern claims enter this extension.

The [full report](../../data/scored/proquest/polarization/report.html) contains all four arms, time-series charts, paired intervals, crisis-exclusion comparisons, calibration bins, source hashes, and model artifacts. The [specification](../../data/scored/proquest/polarization/evaluation_spec.json) was saved before these polarization fits, after earlier historical results had been examined.

## Available political indexes

| Measure | What it represents | Use here |
| --- | --- | --- |
| [Voteview party-mean ideological gap](https://voteview.com/articles/party_polarization) | Distance between Republican and Democratic first-dimension NOMINATE means, by chamber and Congress; long historical coverage | Established reference for legislative ideological polarization. Current historical estimates are not used as predictive features. |
| [V-Dem political polarization, v2cacamps](https://v-dem.net/documents/38/V-Dem_Codebook_v14.pdf) | Expert assessments of society divided into antagonistic political camps, including effects on social relationships | Different construct from congressional voting. Historical scores require a separate coverage and availability audit; not imported into these models. |
| Earlier House rollcall separation | Absolute difference in Democratic and Republican yes-vote shares, averaged over earlier recorded votes | Implemented political proxy, reconstructed from public Voteview records without fitted ideological scores. |

Voteview's current NOMINATE estimates summarize a member's career; its Nokken–Poole estimates are Congress-specific. Simply attaching the current career estimate to an old publication can therefore introduce later voting information. The implemented proxy uses only dated earlier votes and historical party identifiers, excluding NOMINATE coordinates and vote probabilities. This is a reconstructed predictor based on prior events, not a claim that our computed index was published historically. [Voteview member documentation](https://voteview.com/articles/data_help_members)

## Definitions and timing

**Political polarization** is the mean absolute Democratic–Republican yes-share difference across eligible House rollcalls. Use only actual yea/nay codes 1 and 6, at least five actual voters from each party per rollcall, and at least ten eligible rollcalls per window. Independents, nonvotes, paired/announced votes, and unresolved member-party mappings do not enter the two-party calculation. The source audit records exclusions. [Vote coding](https://voteview.com/articles/data_help_votes)

For an origin in month *t*, the political window covers twelve complete months from *t−13* through *t−2*. Month *t−1* is a reporting buffer. Dated votes are observations of publicly conducted legislative activity; current historical database curation is not equivalent to archived release vintages. The proxy measures realized partisan voting separation and is affected by agenda and participation; it is neither the standard ideological gap nor public affective polarization. [Rollcall date documentation](https://voteview.com/articles/data_help_rollcalls)

**Forecast polarization** is the average of `4 × positive_share × negative_share` over the three complete print months before the origin, using general-business claims. It is 1 for equally sized opposing camps and 0 when either camp is absent. Neutral forecasts reduce the available mass in opposing camps. This is a transparent constructed measure, not an externally validated index of newspaper political slant.

The forecast shares retain the existing panel's equal article weights within newspaper/topic/month and equal newspaper weights within month. Require at least two observed months, two papers, and five articles in the window. The existing normalized three-category disagreement and cross-paper dispersion remain in models that already use them: those summarize heterogeneity, while the new product isolates opposing directional camps. Both quantities can reflect mixed horizons, the selected query, and changing newspaper coverage rather than disagreement about an identical proposition.

Political coverage is 1,332/1,332 months in 1900–2010. Forecast coverage is 1,255/1,332. Missing new values receive training-only median imputation, a zero fallback if entirely unobserved in training, and a missingness indicator. No observations are dropped to improve comparability. In the claim models, both scalar features reflect conditions before the publication month and enter the GRU head and both logistic models; the existing twelve-month sequence is unchanged.

## Model comparisons

Each configuration has four arms: baseline, political only, forecast only, and both. The 13 configurations are three claim-correctness models; two monthly newspaper models; and macro-only/macro-plus-newspaper models for the original and selected specifications, each with core and CPI studies. Constant prevalence and historical/recent class-frequency controls remain feature-free.

Original splits, target definitions, training observations, weights, and regularization are retained. Selected macro candidates and training windows are reused from the saved training-only selection, without retuning for polarization. All 294 monthly logistic baseline refits reproduce saved probabilities to within 5.9×10⁻¹²; both claim logistic controls match to within 3.0×10⁻⁸. The GRU baseline and three extensions were rerun with the same three seeds, maximum 20 epochs, and validation-only early stopping. All runs finished.

| Configuration | Baseline Brier | Political only | Forecast only | Both |
| --- | ---: | ---: | ---: | ---: |
| Claim metadata logistic | 0.2183 | 0.2193 | 0.2184 | 0.2192 |
| Claim metadata plus history logistic | 0.2364 | 0.2468 | 0.2395 | 0.2541 |
| GRU ensemble | 0.1929 | 0.2144 | 0.1997 | 0.1991 |
| Selected macro plus newspapers, core | 0.6228 | 0.6564 | 0.6303 | 0.6644 |

Lower is better. Claim correctness uses binary Brier, whereas the monthly IP task sums errors over three classes; values across those tasks are not directly comparable. The claim test contains 56,807 claims in 1995–2010 with equal article evaluation weights; the selected core comparison uses 408 monthly origins in 1977–2010. Full values: [claim metrics](../../data/scored/proquest/polarization/claims_metrics.csv) and [monthly metrics](../../data/scored/proquest/polarization/monthly_metrics.csv).

For both features together, the selected macro-plus-newspaper Brier improvement is **−0.0416**, with paired five-year-block 95% interval **[−0.0788, −0.0186]**. For the GRU it is **−0.0062**, interval **[−0.0456, +0.0151]**. Positive improvement favors the added inputs. Some short CPI estimates improve slightly, but there are only two five-year blocks. All intervals condition on fitted forecasts and omit extraction/model-selection uncertainty; multiple exploratory comparisons are not multiplicity-adjusted. [Monthly intervals](../../data/scored/proquest/polarization/monthly_paired_intervals.csv), [claim intervals](../../data/scored/proquest/polarization/claims_paired_intervals.csv).

The present implementation does not improve the headline models. It should remain a reported extension rather than replacing the paper's established primary comparisons. This is not evidence that polarization has no economic relevance: proxy validity, slow time variation, functional form, and overlapping signals can matter. A predictive coefficient is not a causal effect, and thousands of claims sharing a monthly index do not provide thousands of independent political observations. No further tuning is selected from these evaluation results.

## Reproduction

Use a working environment with the existing ProQuest information and RNN requirements. The broken root `.venv` is not used.

```bash
python src/proquest_polarization.py --download
python src/proquest_polarization_models.py --task monthly
python src/proquest_polarization_models.py --task claims
python src/report_proquest_polarization.py
python tests/test_proquest_polarization.py
```

Omit `--download` to rebuild from the cached public files. The 59-file cache is about 367 MB and is ignored by Git; URLs and SHA-256 hashes are retained in the download manifest. Current upstream files may change, so an exact reproduction requires matching cached hashes. The successful model fits took approximately 6 seconds for the monthly comparisons and 63 seconds for the claim models in this environment; downloads and feature building are additional. Dependency versions are saved in the run manifests.

The new tests cover actual-vote eligibility, ambiguous parties, duplicate records, reporting-buffer boundaries, absence of future influence, opposing versus neutral forecast camps, missingness, training-only preprocessing, and paired uncertainty. Required offline/scoring/forecast tests and the affected ProQuest suites passed. Human source validation remains a separate unfinished task.
