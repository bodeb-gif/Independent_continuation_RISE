# ProQuest source review protocol

Version 1, October 14, 2026. The pilot tests source recovery and interpretation. It supplies no population error estimate and no completed human labels.

## Pilot retrieval

The [retrieval sheet](../../data/scored/proquest/publication/pilot_retrieval.csv) contains twelve scored verified records selected by simple random sampling without replacement, seed 20261014, from the 175,855 current scored records. The [manifest](../../data/scored/proquest/publication/manifest.json) fixes the input hashes. Each address includes `verified`, year, and the physical one-based JSONL line number. Repeated stripped labels retain distinct addresses.

Use the article identifier in the authorized ProQuest environment to obtain context. Recover the original claim identifier or source offsets through VM lineage. File/line identifies an exported record; it does **not** identify a unique passage when the export lacks quotes. Do not select whichever article sentence happens to agree with the labels. Mark mapping `unique`, `ambiguous`, `unavailable`, or `wrong_article`, and retain the reason. Multiple plausible passages require `ambiguous` until source lineage resolves them.

The retrieval sheet contains no machine answers or realized outcomes. Machine labels are in a [separate comparison sheet](../../data/scored/proquest/publication/pilot_machine_labels.csv). An export line itself reveals machine labels; ideally a retrieval helper prepares passage context for Bode without sharing that line. If Bode must retrieve it personally, record any label exposure and describe the review as unblinded where appropriate. Article dates and historically familiar events can still reveal context; blinding does not remove historical knowledge.

## First human interpretation

Store human responses separately from generated outputs, with an audit ID, rubric version, actual reviewer, timestamp, review duration, permitted source locator, mapping status, and blinding status. Do not fill any judgment with an automated guess or use a model response as a human label.

Before revealing machine labels or economic outcomes, record:

| Field | Allowed interpretation |
| --- | --- |
| `is_forecast` | yes / no / unclear; a future economic proposition rather than a current or past description |
| `quantity` | Exact predicted quantity in plain language, or unclear |
| `change_type` | level / growth_rate / event_occurrence / other / unclear |
| `direction` | rise / fall / unchanged / unclear, relative to that quantity |
| `scope` | US_national / regional / foreign / firm_asset / unclear |
| `horizon_support` | explicit / inferable / absent / unclear; record source wording in the permitted environment |
| `target_start`, `target_end` | Source-supported dates or intervals; leave unknown rather than invent an endpoint |
| `condition` | unconditional / conditional / unclear, with the relevant condition |
| `attribution` | Source-supported speaker and reported versus endorsed voice, or unclear |
| `original_forecast_date` | If an earlier forecast is being quoted, preserve its original timing or mark unknown |
| `initial_note` | Evidence for the interpretation and unresolved ambiguity |

Save this first pass with its timestamp. Only then reveal the machine-label sheet and record each field's comparison as `correct`, `incorrect`, `unclear`, or `not_assessable`. Separately grade benchmark compatibility as `direct`, `proxy`, `mismatch`, or `unclear`, and joint scoring usability as `yes`, `no`, or `unclear`, with an error category. Do not reveal realized correctness until these decisions are saved.

## Measurement decisions

Synthetic examples below illustrate decisions; they are not quotations from the corpus.

| Example | Interpretation and scoring decision |
| --- | --- |
| “Industrial production will be lower in six months.” | Candidate direct IP level forecast with an explicit endpoint; confirm national scope and date conventions |
| “Output growth will slow next year.” | Growth-rate change, not necessarily falling output; exclude from an IP-level strict score |
| “Inflation will decline.” | Disinflation, not a falling CPI level; current CPI-level scoring is a mismatch |
| “Employment will rise by December.” | Employment quantity; falling unemployment is a proxy, not automatic direct equivalence |
| “There will be a recession within a year.” | Event occurrence; a six- or twelve-month IP endpoint does not directly test it |
| “If rates fall, business may recover.” | Conditional scenario; preserve the condition and do not assign an unconditional strict score |
| “Stocks will recover eventually.” | Broad-market interpretation and horizon unresolved; exclude from strict scoring |

Eligibility cannot depend on whether the forecast turned out to be correct. The default twelve-month horizon and pre-1919 NBER-state proxy remain visible legacy assumptions. A reviewer may find a valid forecast that cannot be scored against the available references.

## Main audit after the pilot

Measure retrieval success and review time, revise the rubric, and save its final version before drawing the main sample. Reconcile any existing human records first. Preserve the planned approximately 100 ProQuest reviews; no second annotator or full-page recall workload is assumed.

The proposed main design is simple random sampling without replacement from scored verified records excluding the twelve pilot records, with a newly recorded seed. With an unchanged frame, its size is 175,843 and inclusion probability is 100/175,843. Freeze the frame hashes and sample before reviewing. Any stratification or changed frame must be specified before selection with its actual inclusion probabilities. Do not silently replace unavailable sampled claims. The primary audit population excludes the pilot; report that scope and pilot findings separately.

Report sample size, distinct articles, mapping success, unassessable cases, genuine-forecast validity, field validity, and joint usability. Give both assessable-case estimates and all-sampled bounds treating unresolved cases as failures versus successes. Use article-aware uncertainty and the sampling design; do not report human-human agreement with one annotator. The audit estimates quality among scored extracted candidates, not missed forecasts, excluded claims, or the entire press. It cannot establish absolute recall.

For the audited observations, compare original and source-supported interpretations on identical eligible records and disclose exclusions; distinguish this measured effect from any broader error scenario. Freeze the weighting and error-impact implementation after the pilot and before revealing main-sample economic outcomes. Do not rescale corpus performance by a global validity percentage.

## October 19, 2026 author-requested sampling amendment

The author subsequently requested selecting and validating the 100-claim sample
in Chrome before human pilot completion. The
[frozen main sample](../../data/scored/proquest/source_review_main_v1/README.md)
uses the proposed design above: 100 of 175,843 scored verified records, excluding
all twelve pilot addresses, with new seed 20261019. It contains 100 distinct
articles. Source exports are unchanged.

This proceeds ahead of the original human-pilot sequence. Any assistant source
interpretations must be identified as AI review and stored separately from
human judgments. The planned human validation remains incomplete. The frozen
rubric records this amendment; local source-address checks passed, but passage
review is pending approval to transfer the prepared notebook into TDM.
