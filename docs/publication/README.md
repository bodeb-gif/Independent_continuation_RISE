# ProQuest publication evidence package

Started October 14, 2026 under the [publication plan](../PROQUEST_PUBLICATION_PLAN.md). The first paper concerns recovered economic forecasts in the selected annual ProQuest corpus, 1900–2010. Existing estimates are exploratory; direct source validation remains the main dependency.

The existing writing now lives in the dedicated [paper workspace](../../paper/README.md).
This directory retains protocols and historical status records at their stable
paths, including the frozen modern-evaluation specification. Later findings
are collected in the [analysis deep dive](../PROQUEST_ANALYSIS_DEEP_DIVE.md).

| Material | Purpose |
| --- | --- |
| [Paper concept](../../paper/planning/concept.md) | Question, proposed contribution, scope, and evidence needed |
| [Literature comparison](../../paper/references/literature.md) | Fifteen studies with primary sources, construct distinctions and inspection levels |
| [Review interface guide](../../validation/proquest_review/README.md) | Prepared 12-record pilot, locked first pass, separate machine labels and portable responses |
| [Writing evidence map](../../paper/planning/evidence_map.md) | Proposed argument and exhibits with exact result provenance and dependencies |
| [Validation and provenance status](STATUS.md) | Reconcile local evidence with planned human work and the verification queue |
| [Source review protocol](REVIEW_PROTOCOL.md) | Retrieve the pilot, preserve blinding, grade meaning, and freeze the subsequent probability sample |
| [Analysis specification](ANALYSIS_SPEC.md) | Constrain subsequent publication work and record prior exploration |
| [Manuscript outline and tables](../../paper/manuscript/outline.md) | Existing draft; later analyses have not been incorporated |
| [Polarization extension](POLARIZATION.md) | Separate political and forecast measures tested across all 13 active predictive configurations |
| [RNN error and stability audit](RNN_AUDIT.md) | Saved-prediction diagnostics by year, topic, horizon, paper, and seed; no refitting |
| [Forward-time RNN development](RNN_DEVELOPMENT.md) | Fixed eight-configuration experiment, selected smaller recent-window GRU, and later-period confirmation |
| [RNN reuse and retraining](../PROQUEST_RNN_RUNNER.md) | Explicit data paths and time splits, portable bundles, prediction without outcome columns, and permutation diagnostics |
| [Modern evaluation preparation](MODERN_EVALUATION.md) | Frozen procedure and claim models, manifest contract, exposure and outcome-maturity gates |
| [Generated evidence](../../data/scored/proquest/publication/evidence.json) | Exact saved values underlying the draft |
| [Hash manifest](../../data/scored/proquest/publication/manifest.json) | Input, code, specification, and generated-output hashes |

Rebuild the derived packet from the repository root:

```bash
python3 src/proquest_publication.py
```

The builder uses only the standard library, checks recorded source/reference/code hashes, reconciles counts, copies the selected saved tables, and creates twelve reproducible pilot retrieval addresses. It does not refit models or overwrite original exports. The generated directory is `data/scored/proquest/publication/`. Keep completed human responses in a separate authorized location so rebuilding cannot erase them. Record that location and its version in the audit manifest when review begins.

The manuscript numbers below have not passed source-level human validation. The twelve pilot addresses are a preparation artifact; source passages and judgments have not been supplied. The final 100-claim probability sample has deliberately not been drawn before the pilot. The publication snapshot and manuscript remain works in progress.

Verification on October 14, 2026 used the working environment at `/tmp/bode-econ-robustness-20261013`, not the broken repository `.venv`. The required offline, scoring, and forecasts suites passed (97, 33, and 33 checks), as did the three new publication tests for stale-source rejection, sampling eligibility/reproducibility, and source matching/blinding. The builder completed against the actual corpus; package links, generated hashes, and topic-count reconciliation were also checked. These checks establish implementation consistency, not human validation.

Next steps are to resolve the pilot addresses against VM claim lineage, recover the retrieval/processing manifest, complete the pilot interpretations, and freeze the main audit rubric and sample. The literature matrix now covers 15 studies; remaining full-method and final-version checks are listed there. No submission, external contact, source upload, or paid action has been taken.

On October 19, the author deferred source validation while proceeding with the RNN audit and modern-evaluation preparation. The saved-prediction audit is complete: political-only deterioration in 2007–2009 appears across all three seeds and is concentrated in general-business claims; both features together have a different period pattern. The baseline remains the primary RNN. The modern procedure and intake checks are prepared; the author confirmed verification is still unfinished. No local modern exports or reconciled VM manifest are available and prior exposure remains undocumented. The source pilot and main human-review sample were left untouched. Required offline/scoring/forecast checks passed (97/33/33), as did four audit and six modern-intake tests, using `/tmp/bode-econ-audit-20261019`.
