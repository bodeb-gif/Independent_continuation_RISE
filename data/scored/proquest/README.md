# ProQuest results index

All active results use annual ProQuest claims from 1900–2010. Verified exports
are primary and raw exports are sensitivity. Directory names and versioned
artifacts are preserved because code and manifests reference their paths.
The [analysis guide](../../../docs/PROQUEST_ANALYSIS.md) explains methods;
the [paper workspace](../../../paper/README.md) indexes writing and exhibits.

## Descriptive and aggregate evidence

| Directory | Role |
| --- | --- |
| [descriptive](descriptive/report.html) | Original deterministic scores |
| [robustness](robustness/report.html) | Verified/raw and composition comparisons |
| [target_robustness_v1](target_robustness_v1/report.html) | Paired temporal uncertainty for original targets |
| [followups](followups/report.html) | Historical consensus, warnings and publisher/voice comparisons |
| [crisis_2008](crisis_2008/report.html) | Annual-corpus subset, not old crisis-window exports |
| [macro_benchmark](macro_benchmark/report.html) | Selected aggregate benchmark; stable incremental gains not established |
| [macro_information](macro_information/report.html) | Earlier richer macro benchmark and historical vintage archives |
| [monthly_information](monthly_information/report.html) | Earlier class-frequency comparison |
| [macro_diagnostics](macro_diagnostics/report.html) | Aggregate-model diagnostics |

## Interpretation experiments

| Directory | Role |
| --- | --- |
| [direction_diagnostics_v1](direction_diagnostics_v1/report.html) | All constant directions, horizons and warning costs |
| [article_direction_audit_v1](article_direction_audit_v1/summary.json) | Multiple labels retained within article/target groups |
| [benchmark_interpretation_v2](benchmark_interpretation_v2/report.html) | Completed outcome-band sensitivity |
| [alternative_targets_v1](alternative_targets_v1/report.html) | Payroll and GDP outcome sensitivity |
| [alternative_target_inputs_v1](alternative_target_inputs_v1/manifest.json) | Frozen outcome-only downloads; not historical predictors |
| [benchmark_input_review_v1](benchmark_input_review_v1/report.html) | Combined benchmark/input findings and independent checks |

`benchmark_interpretation_v1` retains the specification and failure record from
the first execution. It is not a completed result. No interpretation experiment
automatically replaces original targets or establishes source validity.

## Models and development

| Directory | Role |
| --- | --- |
| [rnn](rnn/report.html) | Frozen original correctness model |
| [polarization](polarization/) | Separate political/forecast arms, retained without promotion |
| [rnn_audit](rnn_audit/) | Saved-prediction diagnostics |
| [rnn_permutation](rnn_permutation/report.html) | Model swaps and synthetic input perturbations |
| [rnn_block_sensitivity](rnn_block_sensitivity/) | Retained block-length sensitivity |
| [rnn_development_v1](rnn_development_v1/report.html) | Provisional smaller recent-window candidate |
| [rnn_age_weighting_v1](rnn_age_weighting_v1/) | Failed fixed improvement rule; all candidates retained |
| [macro_claim_inputs_v1](macro_claim_inputs_v1/report.html) | Matched historical macro-input ablations; no promotion |

## Provenance and handoff

[source_review_pilot_v1](source_review_pilot_v1/review.html) is the prepared
12-record review interface, with machine labels in a separate file and no human
judgments. [writing_evidence_v1](writing_evidence_v1/report.html) indexes 12
proposed writing claims/exhibits with exact source rows, hashes and limitations.
Neither directory contains a new source audit or model experiment.

`export_reconciliation/` records source matching. `modern_readiness/` holds the
original model freeze and deferred evaluation procedure. `publication/` is the
older evidence packet, not the manuscript folder. `prepared_*_check_v1/`
contains historical checks of the future-data adapters.

`reproducibility_v5/` is the completed broader rebuild.
`results_inventory_v2/` audits the collection before cleanup. These are dated
snapshots, not automatically updated status pages. The superseded v1–v4 rebuild
directories and v1 inventory were retired; their execution outcomes and recovery
information are retained in [the cleanup record](repository_cleanup_v1/report.html).

`rnn_runner_check_v2/`, `rnn_development_v1_reload_check/`, and
`rnn_development_diagnostics_v1/` are auxiliary checks, not independent studies.
The first `rnn_runner_check/` was retired after verifying its predictions were
byte-identical to v2. Scientific experiments, including unsuccessful candidates,
remain intact so exploratory choices stay visible.
