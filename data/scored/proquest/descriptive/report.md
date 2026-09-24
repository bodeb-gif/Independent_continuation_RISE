# Machine-verified ProQuest forecasts: first descriptive analysis

Of 274,070 verified claims, 175,855 (64.2%) can be scored under the documented rules. The pooled hit rate is **40.8%**, compared with **53.6%** for a fixed-direction forecast evaluated on exactly the same claims. That baseline always predicts production and stock prices rise, consumer prices rise, and unemployment falls. It is a simple deterministic comparison, not a fitted model.

Claim-grounded horizons: 93,166 claims, 39.7% hit rate. Giving each article equal weight instead of each claim yields 40.9%.

## Interesting patterns

- Barron's has the highest raw rate (43.9%), followed closely by the Boston Globe (43.7%). All eight ranked papers trail the fixed-direction baseline on their own claim mix.
- Coverage adjustment changes the story. Barron's is about 2.3 percentage points above comparable other-paper forecasts, while the Wall Street Journal is about 0.1 point above them despite its low raw rate. The Journal's claims begin in 1984; this is one reason a full-century raw ranking can mislead.
- There is no steady upward trend. Pooled hit rates are 49.9% in the 1960s, 36.1% in both the 1980s and 1990s, and 42.7% in the 2000s. General-business-only rates show a similar mid-century peak and later decline, but the sampled publications and horizons still change.
- Assertive forecasts are correct 44.1% of the time, versus 38.1% for hedged forecasts. This association does not prove that confidence improves forecasting.
- Official voices have a 44.3% hit rate, journalists 41.3%, and quoted experts 40.0%. Expert attribution alone does not identify more successful forecasts in this sample.
- Upbeat business/market calls shrink from 67.7% of directional forecasts in the 1900s to 41.6% in the 2000s. This is the mix of scorable extracted forecasts, not a measure of all newspaper sentiment.

## Which papers had the highest hit rate?

| Paper | Scored claims | Hit rate | Fixed baseline | Gap (pp) |
| --- | ---: | ---: | ---: | ---: |
| Barron's | 13,721 | 43.9% | 56.7% | -12.8 |
| Boston Globe | 11,938 | 43.7% | 52.2% | -8.4 |
| New York Times | 37,036 | 42.7% | 53.0% | -10.3 |
| Chicago Tribune | 20,040 | 41.9% | 55.5% | -13.6 |
| Washington Post | 17,182 | 41.2% | 50.4% | -9.2 |
| Los Angeles Times | 36,420 | 38.9% | 52.5% | -13.6 |
| Christian Science Monitor | 3,497 | 38.6% | 59.3% | -20.7 |
| Wall Street Journal | 35,927 | 38.1% | 54.7% | -16.6 |

These are forecasts published by each paper, often quotations from outside experts. They do not measure the newspaper staff's own forecasting ability. Historical editions are merged by newspaper family. USA Today is retained in the data but excluded from the ranking when below 500 scored claims.

Publisher intervals in the figure resample nonoverlapping five-year publication blocks (1,500 draws). These account for some shared economic conditions but are descriptive, not evidence of a statistically significant ranking. The publisher CSVs also report equal-article weighting, claim-grounded horizons, a restricted 1960–2010 period (coverage still differs by paper), and a peer comparison within year/topic/benchmark/horizon basis/horizon bucket. Peer means exclude the paper itself and require at least 20 other-paper claims. The adjusted gap is an exploratory coverage adjustment, not a causal effect or ML model.

## Trends across decades

| Decade | Scored claims | Hit rate | Fixed baseline | Gap (pp) |
| --- | ---: | ---: | ---: | ---: |
| 1900.0 | 820.0 | 49.1% | 49.0% | +0.1 |
| 1910.0 | 939.0 | 42.0% | 52.5% | -10.5 |
| 1920.0 | 2,728.0 | 47.1% | 43.8% | +3.4 |
| 1930.0 | 11,778.0 | 48.1% | 51.3% | -3.2 |
| 1940.0 | 4,268.0 | 39.9% | 62.7% | -22.8 |
| 1950.0 | 5,712.0 | 46.5% | 60.6% | -14.1 |
| 1960.0 | 5,782.0 | 49.9% | 67.3% | -17.3 |
| 1970.0 | 19,505.0 | 46.4% | 52.7% | -6.3 |
| 1980.0 | 39,516.0 | 36.1% | 53.4% | -17.3 |
| 1990.0 | 39,446.0 | 36.2% | 66.6% | -30.4 |
| 2000.0 | 39,830.0 | 42.6% | 35.6% | +7.0 |
| 2010.0 | 5,531.0 | 39.7% | 77.8% | -38.1 |

2010 contains only one publication year. Early business forecasts use a recession-state proxy, whereas business forecasts from 1919 use industrial production. Employment enters only from 1948, prices from 1913. Do not read the pooled decade line as a clean test of improvement: benchmark and topic mix change.

## Topic, hedging, and forecast voice

| Topic | Scored claims | Hit rate | Fixed baseline | Gap (pp) |
| --- | ---: | ---: | ---: | ---: |
| prices | 22,531 | 46.4% | 75.2% | -28.8 |
| general_business | 109,582 | 40.9% | 53.1% | -12.1 |
| markets | 25,546 | 38.7% | 58.5% | -19.8 |
| employment | 18,196 | 36.2% | 23.5% | +12.7 |

| Confidence | Scored claims | Hit rate | Fixed baseline | Gap (pp) |
| --- | ---: | ---: | ---: | ---: |
| assertive | 79,608 | 44.1% | 53.8% | -9.7 |
| hedged | 96,236 | 38.1% | 53.5% | -15.4 |
| unclear | 11 | 45.5% | 72.7% | -27.3 |

| Voice | Scored claims | Hit rate | Fixed baseline | Gap (pp) |
| --- | ---: | ---: | ---: | ---: |
| expert | 130,927 | 40.0% | 54.0% | -14.0 |
| journalist | 15,089 | 41.3% | 51.7% | -10.4 |
| layperson | 1,458 | 38.1% | 51.8% | -13.6 |
| official | 27,273 | 44.3% | 52.9% | -8.5 |
| unclear | 969 | 43.7% | 55.2% | -11.6 |

Hedged vs assertive and voice differences are associations. Their topic, era, and horizon mixtures differ. No numerical confidence probabilities were extracted, so this analysis does not invent Brier scores from the hedging label.

## Sensitivity checks

| Specification | Scored claims | Hit rate | Fixed baseline | Gap (pp) |
| --- | ---: | ---: | ---: | ---: |
| Primary | 175,855 | 40.8% | 53.6% | -12.8 |
| Half change bands | 175,855 | 47.3% | 62.6% | -15.4 |
| Double change bands | 175,855 | 28.3% | 33.3% | -5.0 |
| Default horizon 6 months | 175,855 | 37.3% | 44.5% | -7.3 |
| Default horizon 24 months | 175,855 | 41.6% | 59.0% | -17.4 |
| Exclude market proxy scoring | 150,309 | 41.2% | 52.8% | -11.6 |

The sensitivity checks start with the primary eligible claims and recompute their outcomes under half/double change bands or a 6/24-month default for vague, uninferred horizons. Claims with no endpoint under an alternative are omitted. The last row drops the provisional market benchmark altogether. These checks assess rule dependence, not extraction validity.

## Scoring rules and limitations

Only explicit national scope and the four supported topics enter scoring. 'Other' and nonstandard topics are excluded. Forecast direction is compared to the change between the publication month and the horizon endpoint. A real change must exceed 2% for production, 1.5% for consumer prices, 0.5 percentage points for unemployment, or 5% for stock prices. Values exactly on a threshold count as flat. These are inherited research bands, not tuned on these results.

Positive integer horizons of 1–24 months are respected. Longer or malformed numeric horizons and unusable labels are excluded, rather than clipped or silently replaced. Vague horizons use the exported inference (6 or 24 months), or an explicit 12-month default. Before industrial production begins, business forecasts use whether at least half of the inclusive horizon window is in recession according to USREC; this is a weaker state proxy, explicitly labeled NBER proxy. Endpoint values must exist; no extrapolation or forward filling is used.

Market claims use Shiller's monthly-average nominal S&P Composite price series consistently across the whole corpus, excluding dividends. Broad market predictions are only approximate matches to this benchmark, especially claims about bonds or particular securities. Monthly averages also include days after the claim's publication date. Treat the market results as provisional topic-level proxy scoring; the exports lack quotes needed to identify the precise asset.

Realized outcomes use revised reference values, appropriate for retrospective scoring. This is not a real-time prediction model. Machine verification does not remove all extraction errors. Stripped quotes make semantic rechecking and definitive claim deduplication impossible locally; identical labels are retained. Claims share articles, dates, and macro outcomes. There is no LOC analysis, crisis-window dataset, fitted ML model, or claim-volume attention measure here.

### Excluded verified claims

- not explicitly US-national: 80,183
- topic has no defensible benchmark: 7,894
- no scorable direction: 3,176
- numeric horizon outside 1–24 months: 2,490
- outside benchmark coverage: 2,297
- unusable horizon label: 2,175

### Economic reference sources

- [INDPRO](https://fred.stlouisfed.org/series/INDPRO): 1919-01 through 2026-06. SHA-256 and snapshot provenance in summary.json.
- [CPIAUCNS](https://fred.stlouisfed.org/series/CPIAUCNS): 1913-01 through 2026-06. SHA-256 and snapshot provenance in summary.json.
- [UNRATE](https://fred.stlouisfed.org/series/UNRATE): 1948-01 through 2026-06. SHA-256 and snapshot provenance in summary.json.
- [USREC](https://fred.stlouisfed.org/series/USREC): 1854-12 through 2026-07. SHA-256 and snapshot provenance in summary.json.
- [Shiller S&P Composite nominal price P](https://shillerdata.com/): 1871-01 through 2026-09. SHA-256 and snapshot provenance in summary.json.
