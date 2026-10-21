# Frozen 100-claim ProQuest sample

Selected October 19, 2026 at the author's request. The sample contains 100
scored machine-verified claims from 100 distinct articles. Simple random
sampling without replacement uses seed 20261019 and the 175,843 scored annual
verified records remaining after the original twelve pilot records are
excluded. Each frame record has inclusion probability 100/175,843.

The author requested proceeding before human pilot completion. `rubric.json`
records that amendment and identifies subsequent assistant interpretation as
**AI source review**, not human validation. The human pilot and its responses
are untouched. This sample covers scored extracted candidates, not the entire
274,070-claim verified corpus, excluded claims, or missed forecasts.

- `retrieval.csv` and `pack.json`: fixed source addresses, dates and article IDs.
- `comparison.json`: separate machine labels and benchmark names; no realized
  economic outcomes. Keep this hidden during initial source interpretation.
- `rubric.json`: review rules frozen for this audit.
- `manifest.json`: frame definition, seed, pilot exclusions and input/output hashes.
- `ProQuest_Main_AI_Audit.ipynb`: prepared notebook for source recovery inside
  the existing TDM workbench. Original quote/article recovery requires a full
  reconstructed-export hash match. It does not generate or save human judgments.
- `validation_status.json`: current completion status and verification results.

Local checks confirmed all 100 sampled source addresses, matching metadata,
unchanged annual source hashes, no pilot overlap and 100 distinct articles.
Three sampling tests and all 163 required main-suite checks passed. These checks
establish sampling and data integrity; they do not establish semantic validity.

Source-passage review has not yet been completed. Automatic approval review
blocked the notebook transfer to ProQuest TDM pending explicit user approval.
Keep the frozen sample unchanged when review resumes; retain unavailable or
ambiguous cases without replacement. Source prose and free-text judgments stay
inside TDM, in a separate AI response store. No source-validity rate is available.

Reproduce sampling into a new directory with a working Python environment:

```bash
python src/proquest_main_audit.py --output /tmp/proquest-main-audit-reproduction
python tests/test_proquest_main_audit.py
```

The builder refuses to overwrite an existing frozen sample. It rebuilds the
sampling artifacts; the prepared TDM notebook is retained separately.

## Subsequent review status, October 20, 2026

The historical pending-review statements above describe the original AI-audit
setup. The original 100 were subsequently retained in the expanded 150-claim
review. The author now confirms human review/editing of that expanded set. See
`../source_review_150_v1/README.md` and
`../source_review_150_v1/human_review_attestation_20261020.json` for current
status and limitations. The original frozen sample and AI rubric are unchanged.
