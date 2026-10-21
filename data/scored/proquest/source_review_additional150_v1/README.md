# Additional 150-claim labeling comparison

## Human-review confirmation, October 20, 2026

The author now confirms human validation of this additional 150-claim batch.
Read-only Chrome checks of the saved ProQuest files verify that all categorical
labels match this local copy. The author clarified that they performed the human
validation and used AI only to explain context in a couple of situations.
Describe this as human validation with limited contextual assistance. Earlier
Codex metadata remain as artifact history, not evidence that AI made the human
review decisions. Blinding and a second independent human reviewer were not
established. See `human_review_attestation_20261020.json` and
[the combined 300-claim status](human_review_status.html). All source hashes and
150 addresses were checked locally, field comparisons recomputed, and zero
claim overlap with the original 150 confirmed. The combined total is 250
historical plus 50 modern claims: 212 included, 87 excluded and one unclear.
This supplies modern extraction evidence, not economic forecast validation.

The additional 150 categorical records were exported through ProQuest's results
channel as `human_validation_additional150_20261020.json` (87,510 bytes).
Upload success was visibly confirmed; email delivery has not been checked.
The local copy has the same byte-level SHA256 as the prepared VM export. See
`export_receipt_20261020.json` and `export_submission_20261020.jpg`. Source prose
and free-text notes remain in TDM.

## Original comparison

Completed source-context labeling of 150 new ProQuest candidates: 100 historical and 50 modern, with every year from 2011 through 2026 represented. Compared against the original saved GPT-4o mini labels after freezing the new labels. No new GPT-4o mini run or economic-outcome scoring was performed.

| Sample | Reviewed | Include | Exclude | Unclear | Inclusion |
|---|---:|---:|---:|---:|---:|
| Historical | 100 | 72 | 28 | 0 | 72.0% |
| Modern | 50 | 35 | 15 | 0 | 70.0% |
| Total | 150 | 107 | 43 | 0 | 71.3% |

Exact agreement among included claims only:

| Field | Historical | Modern | Combined sample |
|---|---:|---:|---:|
| topic | 66/72 (91.7%) | 29/35 (82.9%) | 95/107 (88.8%) |
| direction | 60/72 (83.3%) | 29/35 (82.9%) | 89/107 (83.2%) |
| price_direction | 55/72 (76.4%) | 30/35 (85.7%) | 85/107 (79.4%) |
| unemployment_direction | 61/72 (84.7%) | 31/35 (88.6%) | 92/107 (86.0%) |
| horizon_months | 49/72 (68.1%) | 26/35 (74.3%) | 75/107 (70.1%) |
| confidence | 55/72 (76.4%) | 22/35 (62.9%) | 77/107 (72.0%) |
| voice | 57/72 (79.2%) | 24/35 (68.6%) | 81/107 (75.7%) |
| speaker_name | 43/72 (59.7%) | 27/35 (77.1%) | 70/107 (65.4%) |
| scope | 49/72 (68.1%) | 24/35 (68.6%) | 73/107 (68.2%) |
| is_quoted_forecaster | 56/72 (77.8%) | 23/35 (65.7%) | 79/107 (73.8%) |
| current_state | 55/72 (76.4%) | 27/35 (77.1%) | 82/107 (76.6%) |

All eleven fields match on 6/107 included claims. This is exact annotation agreement under the stated review conventions, not overall model accuracy.

## Files and source evidence

- `comparison.csv` and `comparison.json`: all 150 decisions with original and review fields; excluded fields are null.
- `reviewed_labels_categorical.json`: source-free categorical labels, keyed to the frozen export addresses.
- `pack.json` and `manifest.json`: selection, inclusion probabilities, prior exclusions and source hashes.
- `summary.json`: counts, field denominators, applicable-only price/unemployment comparisons, and modern design-weighted estimates.
- In TDM: `election_arm/source_review_additional150_v1/` contains frozen labels, full reasoning, source passages and the readable comparison. Source prose and free-text notes remain there.

## Interpretation

The historical sample is SRS100 from 175,693 scored verified records after excluding the previous 150 and twelve pilot addresses. The modern sample draws four records each from 2011 and 2026 and three from every other modern year, from all retained verified candidates. Those frames differ: modern candidates need not have scorable outcomes. The unweighted combined figure describes these 150 sampled candidates only. No claim labels were deduplicated and no unavailable case was substituted.
The modern inverse-probability-weighted inclusion estimate is 73.4% across 91,118 retained candidates. This is a point estimate; no uncertainty interval is asserted. The modern frame includes retained verification exceptions rather than silently dropping them.

Every source record was recovered by ordered export reconstruction and source-article ID/date checks. Eighty-seven quotes occurred exactly once verbatim; the remaining passages were inspected in article context for OCR/quotation differences. Full-prefix hashing permits only unchanged frozen prefixes when a live VM shard has appended rows. The VM receipt records any such lineage exceptions.
Labels follow the original extraction schema. Current-state labels use the sampled claim itself, not surrounding article conditions. Short, long, event-relative or unsupported horizons remain vague; approximately 4–8 months maps to six and 9–15 to twelve, with annual next-year outlooks coded twelve. Compound forecasts receive a documented primary interpretation, with secondary components retained in VM notes.
Price direction concerns price levels, and employment growth does not automatically imply falling unemployment. Overall price/unemployment agreement includes many `na` matches; applicable-only denominators are provided separately. Speaker-name comparison is literal, so surnames, full names and group attributions can differ without implying different people. Source-grounded judgments can be debatable; paired records and VM notes support adjudication.
These results measure inclusion and annotation agreement among extracted positive candidates. They do not establish recall, independent human agreement, or whether forecasts came true. Earlier reviews and source exports are unchanged.
