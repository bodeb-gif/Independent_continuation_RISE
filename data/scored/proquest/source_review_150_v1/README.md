# 150-claim source review

Completed 2026-10-20 (America/Chicago) inside the ProQuest TDM VM. All 150 sampled passages were recovered and reviewed in article context. The source corpus was not edited. Labels were frozen before generating this comparison.

VM directory: `/home/ec2-user/SageMaker/election_arm/source_review_150_v1/`

- `reviewed_labels.json`: frozen decisions, eleven categorical extraction fields, notes, timestamps, and sample identifiers.
- `reviewed_labels.jsonl`: all 150 decisions with the original sampled quotations.
- `comparison.json`: original GPT-4o-mini fields beside review fields, with exact-match indicators.
- `comparison.html`: readable report with all 150 expandable rows.
- `summary.json`, `METHOD.txt`, and `extraction_prompt.txt`: results, conventions, and extraction instructions.
- `sources.json`: recovered source material; remains inside the VM.

Notebook: `/home/ec2-user/SageMaker/election_arm/ProQuest_150_Labeling.ipynb`.

## Results

| Decision | Original 100 | Additional 50 | Total |
|---|---:|---:|---:|
| Include | 71 | 34 | 105 |
| Exclude | 28 | 16 | 44 |
| Unclear | 1 | 0 | 1 |

Candidate-inclusion precision against this review is 105/150 = 70.0%, with a 70.0–70.7% identification range depending on the unresolved case. Among resolved decisions it is 105/149 = 70.5%. This range is not a confidence interval. These results measure extraction inclusion and annotation agreement, not whether an economic forecast came true. Recall cannot be measured from this positive-candidate sample.

Exact primary-field agreement among 105 included claims:

| Field | Matches | Percent |
|---|---:|---:|
| topic | 90 | 85.7 |
| direction | 94 | 89.5 |
| price_direction | 77 | 73.3 |
| unemployment_direction | 89 | 84.8 |
| horizon_months | 66 | 62.9 |
| confidence | 75 | 71.4 |
| voice | 79 | 75.2 |
| speaker_name | 74 | 70.5 |
| scope | 65 | 61.9 |
| is_quoted_forecaster | 75 | 71.4 |
| current_state | 22 | 21.0 |

All eleven fields match on 1/105 included claims. Speaker-name comparison is literal; abbreviations count as differences. Secondary labels preserve compound forecasts and are not selected to maximize agreement. Excluded and unresolved rows have null categorical fields and are excluded from field-agreement denominators. Quotes remain the original sampled units, not a new exhaustive extraction of every sentence in each article.

**Interpretation correction (2026-10-20):** Inspection of the original prompt confirms that `current_state` must describe what the claim itself says about present conditions, with `na` when it says nothing. Review annotations sometimes used surrounding article conditions instead. The 22/105 current-state match count is therefore a mechanically correct comparison under mismatched coding conventions, not a valid estimate of model label accuracy. That field requires aligned re-labeling; the all-eleven-fields match count likewise must not be presented as overall model accuracy. Price/unemployment-direction agreement also includes `na` matches and should not be interpreted as accuracy restricted to applicable price/employment forecasts.

## Sample and interpretation

Retained the original SRS100, then sampled 50 additional claims without replacement from the remaining 175,743 eligible addresses using seed 20261020. The combined sample has 150 distinct claims from 149 articles. Its frame is 175,843 scored verified annual ProQuest economy candidates after exclusion of the 12 pilot claims, not the entire verified corpus. See `manifest.json` and `pack.json`. The original 100 had prior exposure to model labels during the earlier review; the additional 50 model labels were hidden until annotation was frozen. Do not describe the full 150 as blinded.

Review uses the original extraction schema. Horizon categories are coarse: approximately 4–8 months maps to 6, approximately 9–15 months maps to 12; annual next-year outlooks use 12. Shorter, longer, event-relative, or unspecified endpoints use `vague`, with exact timing recorded in notes. Direction follows the passage's economic framing; interest-rate direction reflects borrowing costs/bond prices, and price-direction denotes price levels rather than inflation-rate acceleration. Current/past descriptions, unresolved hypothetical policy scenarios, generic rules, and non-economic promises are excluded. These conventions should accompany any use of the labels.

## Verification and lineage

VM checks passed for all 150 unique IDs, all recovered article IDs/dates/quotes, unchanged recovered verified-file hashes, all included-label enum values, and 150 saved comparison rows. No source-code changes were made for this extension.

For two 1995 records (`verified:1995:3081`, `verified:1995:4138`), the VM shard had 17 appended records. Recovery proceeded only after proving that all original 5,814 canonical stripped rows remained an unchanged prefix of the 5,831-row shard. Prefix SHA256: `215292e177b650c49b5f823a2b8b44dc7e978d389ce24fa18618d3aa9040020a`. There was no replacement sampling or matching by labels. The original extraction prompt body was also checked against repository code (SHA256 `50e696907a48cb5a5015eb23c5b523fdf3c7c5528211fc2b8b69871de9029653`).

## Human-review confirmation, October 20, 2026

The author explicitly confirmed in this session that they completed **150**
claims (correcting their initial count of 100), edited the saved 150-claim
labels/comparison, and identify those files as their human validation. This is
an author attestation of human review of the existing artifacts; it does not
establish independent first-pass labels or remove prior AI/model-label exposure.
Earlier AI review remains part of the provenance.

Chrome inspection of the TDM VM confirmed the saved `reviewed_labels.json`,
`comparison.json`, `summary.json` and `METHOD.txt`; the displayed summary matches
the counts above, including original100 = 71/28/1 and additional50 = 34/16/0.
The existing current-state coding mismatch remains unresolved. Do not report
that field or the all-eleven-fields count as valid overall extraction accuracy.

The author approved the categorical export to ProQuest's documented results
channel, and upload succeeded. The author then supplied its complete 150-row
JSON in chat. `human_labels_received.json` preserves the normalized categorical
labels and source hashes; it omits row timestamps and is explicitly not a
byte-identical archive of the exported JSON. Full source passages and free-text
notes remain in TDM.

`human_comparison_reconciled.json` joins all 150 rows to the original source
addresses and machine labels. All dates, article IDs, source hashes, eleven
field-agreement counts and the 105/44/1 decision counts reconcile. See
`human_reconciliation_summary.json`. There are 149 distinct articles and no
modern claims in this sample. The current-state convention caveat still applies.
