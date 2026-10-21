# Validation and provenance status

## Current update — October 20, 2026

This update supersedes the pending human-review and modern-export status in
the dated historical entries below. Historical source files and all 30 frozen
model/protocol artifacts remain unchanged.

- **Human validation:** 300 distinct claims across 299 articles: 250 historical
  and 50 modern. Decisions are 212 include, 87 exclude and one unclear. The author
  performed the validation, using AI for contextual explanations in a couple
  of situations. Earlier artifact metadata are retained without attributing the
  author's decisions to AI. Blinding and a second human reviewer are not
  established. See the [review status](../../data/scored/proquest/source_review_additional150_v1/human_review_status.html).
- **Modern extraction evidence:** all years 2011–2026 appear in the 50-claim
  modern sample; 35 are included, with direction agreement of 29/35 among
  included claims. The design-weighted inclusion estimate is 73.4%; unweighted
  sample inclusion is 70.0%. These assess extraction, not recall or forecasting
  performance. Historical and modern sampling frames differ.
- **Modern export:** 91,118 retained claims imported unchanged. All 33,071 empty
  records and 19 default-kept verification exceptions are excluded from primary
  analysis inputs. Processing metadata gaps and undocumented prior outcome
  exposure remain; the full original readiness gate is not certified.
- **Exploratory modern evaluation:** 56,886 mature, supported claims from 23,775
  articles. Frozen RNN AUC 0.7376 versus 0.6545 for metadata-plus-history logistic;
  both-polarization RNN AUC 0.7486. Employment AUC is only 0.3064. Paired block
  intervals do not establish the main model improvements; no new permutation
  significance claim is made. See the [dated amendment](MODERN_ANALYSIS_AMENDMENT_20261020.md)
  and [completed analysis](../../data/scored/proquest/modern_analysis_v1/report.html).
- **Separate downturn forecasts:** the pre-2011-selected models estimate 6.9%
  recession onset and 28.0% industrial-production decline for September 2026–
  August 2027, using prints through August 2026. Modern recession evaluation
  contains only one distinct onset, improvements have intervals crossing zero,
  and the production estimate is essentially its historical base rate. These
  are exploratory research probabilities, not a strong downturn call.
- **Export receipt:** the additional 150 labels were submitted successfully
  through ProQuest. The returned user attachment matches all 87,510 export bytes.
  No article text or free-text notes were exported.
- **Pre-commit checks:** 191 checks passed across the three main suites and five
  intake/review/modern suites; one optional widget test was skipped. Source-free
  review notebooks have no executed outputs. Frozen artifacts and completed
  modern output hashes were verified.

The modern report predates the additional review batch; its statement that no
modern claims appear in the human sample is superseded by the review status
above. Preserve its model results as the completed dated run.

## Earlier status history

Age-weighting follow-up, October 19: three fixed decay rates were tested on development periods through 1984. The best mean Brier fell from 0.180864 to 0.179436 but improved only one of four blocks, failing the preset rule. The current candidate is retained. [Full follow-up](RNN_DEVELOPMENT.md#gradual-age-weighting-follow-up). No later evaluation or new permutation p-value was produced.

Latest October 19 update: [forward-time RNN development](RNN_DEVELOPMENT.md) selected an 8-unit GRU with a 20-year fitting window. It passed the prespecified rule on both later historical confirmation blocks, lowering their mean Brier from 0.16198 to 0.15741. The candidate is provisional, with worse early-1980s performance; confirmation is exploratory because these years have prior project exposure. No 1995–2010 re-evaluation or new significance claim was made. Original frozen models remain unchanged, and source validation and modern evaluation remain deferred.

Local repository audit, October 14, 2026. Planned reviews, prepared packets, machine verification, and completed human judgments are separate stages.

October 19 update: the [RNN saved-prediction audit](RNN_AUDIT.md) is complete and [modern-evaluation preparation](MODERN_EVALUATION.md) is ready. The author confirmed modern verification is not yet finished. No modern annual exports were found locally; exact coverage/counts and prior result exposure remain unconfirmed. The author requested continuing this work while deferring source validation. No additional source retrieval, human grading, or main-review sampling was performed.

Later October 19 update: the author confirmed only 1900–2010 is available and deferred modern evaluation. The [permutation diagnostics](../../data/scored/proquest/rnn_permutation/report.html) are complete. The [reusable model runner](../PROQUEST_RNN_RUNNER.md) supports applying existing models and training new versions from explicit prepared-data paths. The historical exports reconcile byte-for-byte against both downloaded annual archives and all 222 recorded import hashes; [reconciliation details](../../data/scored/proquest/export_reconciliation/summary.json). Upstream processing completion still cannot be inferred from these exported rows.

| Evidence | What is established locally | What remains unresolved |
| --- | --- | --- |
| Annual import | `data/proquest/source_manifest.json` identifies source commit `774b68fb202955a83ebc035fc63b01ead725cc82` and 222 raw/verified file entries with Git blob IDs | This is import provenance, not retrieval completeness or a record of successful VM processing |
| Raw exports | 488,660 claims in 111 annual shards; 156,435 represented article IDs | Missing, failed, retried, truncated, or unexported source material requires VM status |
| Verified exports | 274,070 claims; 146,720 represented article IDs, including 105,604 with claims | “Verified” means machine-filtered; it does not imply human review |
| Empty records | Both sets contain 41,116 no-prediction records | These labels do not by themselves establish that upstream calls all succeeded |
| Article overlap | 9,715 raw article IDs absent from verified exports; zero in the other direction | Absence cannot be interpreted as rejection without processing lineage |
| Legacy scoring | 175,855 verified claims, 76,851 scorable articles; 98,215 unscorable claims | Semantic correctness of target/horizon mapping needs source context |
| Planned human work | Research plan proposes 400 LOC reviews and 100 ProQuest reviews by Bode | A target count is not a completed count |
| LOC packet | Prepared 120 candidates on 62 pages, drawn from 239 candidates linked to a partial local text set; separate 24-page recall pilot | Prepared packets are not completed judgments; neither estimates ProQuest validity |
| Historical handgrading | `validation/handgrade_newspapers/` includes historical labels and model/consensus material; the Bode-named CSV contains LOC links and some filled fields | Cannot relabel these as the planned ProQuest audit or infer reviewer identity from a filename |
| ProQuest human review | No completed ProQuest source-linked judgment file identified in the local validation directories | Human review may exist elsewhere; recover it before treating the planned 100 as new work |
| Modern verification queue | Bode reports on October 14, 2026 that the VM is still running and is close to finishing verification of modern claims | Exact years, counts, failures, export status, and reconciliation with the plan's roughly 40,000 figure still require the VM manifest; this is not evidence of completed human review |
| Publication pilot | Twelve reproducible source-local record addresses prepared | Context retrieval, unambiguous mapping, and human judgments pending |

Counts are reconciled in the [generated corpus table](../../data/scored/proquest/publication/corpus_flow.csv). They describe exported records and represented article IDs, not all searched pages or the universe of newspaper reporting. Raw/verified counts do not identify a claim-retention rate without claim lineage.

## VM manifest request

Recover an existing manifest where possible. For each run, record run ID, date/time and timezone, source database, exact query and query version, newspaper/year coverage, retrieval order and limits, eligible/retrieved article counts, available-text counts, successful extraction counts, successful empty outputs, errors, retries, truncation, verification completion, and export completion. Counts should reconcile within stages and preserve unfinished statuses.

Record extraction and verification model identifiers, prompts and hashes, schema, decoding settings, chunk sizes/overlap, context limits, and truncation rules. The import commit does not establish the model configuration that produced each run. For source mapping, supply an in-environment join from export set/file/line/hash to original claim identifier and passage offsets, not merely article ID and matching labels.

When modern verification finishes, preserve the run logs and recover the years, raw candidate denominator, completed/pending/failed counts, model/prompt versions, and export manifest. Reconcile the actual totals with the plan's approximate 40,000 figure and identify any overlap with existing imports. Keep 2011 onward outside the active analysis even if that queue completes. Before any separately authorized modern evaluation, document prior exposure, freeze its procedure, and apply outcome-maturity rules.

## Access inventory

| Field category | Current treatment | Evidence required before release |
| --- | --- | --- |
| Article text and excerpts | Retrieve in the authorized source environment | Applicable institutional/database permission for any proposed export |
| Bibliographic records and identifiers | Pilot locators remain local; no public upload | Applicable terms for identifiers and citation records |
| Machine and human labels | Internal research evidence; preserve lineage | Permission for derived rows and a disclosure plan for source associations |
| Aggregated results and panels | Local derived analysis | Review the intended public fields against the applicable agreement |
| Prompts, code, and synthetic fixtures | Prepare for reproducibility | Check source content embedded in prompts/fixtures and record software licenses |
| Fitted models and macro snapshots | Existing local artifacts | Confirm applicable provider permissions and reconstruction options |

This is a work inventory, not a legal determination or a public data license. The author/library contact must establish the applicable access and sharing basis. No new source material has been uploaded as part of this package.
