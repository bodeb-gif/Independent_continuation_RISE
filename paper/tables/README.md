# Paper table index

These links identify the canonical tables and their roles. The older manuscript
outline does not incorporate every later sensitivity result.

The [writing evidence map](../planning/evidence_map.md) assigns proposed exhibit
roles. Its [machine-readable ledger](../../data/scored/proquest/writing_evidence_v1/ledger.json)
records exact row selectors, hashes, metrics and limitations for 12 evidence entries.

| Table | Role |
| --- | --- |
| [Corpus flow](../../data/scored/proquest/publication/corpus_flow.csv) | Existing publication evidence snapshot |
| [Original topic scores](../../data/scored/proquest/publication/legacy_verified_topics.csv) | Legacy deterministic scoring, not source-validated estimates |
| [Aggregate macro comparison](../../data/scored/proquest/publication/monthly_core.csv) | Macro forecasting task, separate from claim correctness |
| [Target uncertainty](../../data/scored/proquest/target_robustness_v1/primary_verified_topics.csv) | Paired baseline gaps under original scoring |
| [Band and comparator sensitivity](../../data/scored/proquest/benchmark_interpretation_v2/primary_comparisons.csv) | Exploratory matched outcome-definition comparison |
| [Alternative economic targets](../../data/scored/proquest/alternative_targets_v1/primary_comparisons.csv) | Payroll and GDP sensitivity on explicitly matched support |
| [Macro-input model comparison](../../data/scored/proquest/macro_claim_inputs_v1/summary_metrics.csv) | Equal-era mean losses; no model promotion |
| [Historical label revisions](../../data/scored/proquest/benchmark_input_review_v1/label_revision_audit.csv) | Historical-vintage versus revised correctness, not extraction error |

Consult each result folder's specification and support tables before combining
numbers: samples, outcome definitions, periods and weighting differ. Retain
negative results and uncertainty when selecting eventual paper exhibits.
