# ProQuest analysis code index

Run entry points from the repository root in a working environment described
in [the reproducibility guide](../docs/PROQUEST_REPRODUCIBILITY.md). The old
root `.venv` is broken. Files retain their original import paths because saved
models, tests and provenance manifests refer to them.

| Workstream | Entry points |
| --- | --- |
| Inventory and deterministic scoring | `analyze_proquest.py`, `proquest_descriptive.py`, `proquest_robustness.py` |
| Descriptive follow-ups | `proquest_followups.py`, `proquest_2008.py`, `proquest_target_robustness.py` |
| Interpretation and benchmarks | `proquest_direction_diagnostics.py`, `proquest_article_direction_audit.py`, `proquest_benchmark_interpretation.py`, `proquest_alternative_targets.py` |
| Aggregate economic prediction | `proquest_panel.py`, `proquest_information.py`, `proquest_vintages.py`, `proquest_macro_information.py`, `proquest_macro_benchmark.py`, `proquest_macro_diagnostics.py` |
| RNN and logistic claim models | `proquest_rnn.py`, `proquest_rnn_runner.py`, `proquest_rnn_development.py`, `proquest_rnn_age_weighting.py`, `proquest_macro_claim_inputs.py` |
| Polarization | `proquest_polarization.py`, `proquest_polarization_models.py`, `report_proquest_polarization.py` |
| Model diagnostics | `proquest_rnn_audit.py`, `proquest_rnn_permutation.py`, `proquest_benchmark_input_report.py` |
| Intake and reproducibility | `proquest_prepare_inputs.py`, `proquest_prepare_features.py`, `proquest_modern_intake.py`, `proquest_reproducibility.py` |
| Publication evidence assembly | `proquest_publication.py` |

Read each script's specification before execution. Most versioned experiments
refuse to overwrite an existing output; use their `--out` option where
supported. New source claims belong in the intake workflow, not in derived
result files. Earlier LOC scripts remain for historical reproduction and
extraction validation only.

`proquest_review.py` builds the fixed 12-record blinded pilot interface from
existing retrieval addresses; see [the review guide](../validation/proquest_review/README.md).
`proquest_writing_evidence.py` assembles a traceable writing ledger from saved
result rows, without refitting models or interpreting sources.
