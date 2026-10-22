# One additional pass on the 300 human-reviewed ProQuest claims

The October 22, 2026 VM run completed all 300 API attempts, one per claim,
without retries: 256 keep, 43 drop, and one response that failed strict verdict
parsing (`ValueError`). Retaining that unresolved claim leaves 257 candidates.
All 300 responses identify `gpt-4o-mini-2024-07-18`.

[The report](report.html) now reproduces the comparison from the complete,
hash-verified [300-decision export](categorical_export.json). The user supplied
the export as pasted text. Restoring exactly one missing final newline produces
the exact SHA-256 recorded on the VM; see [the import receipt](import_receipt.json).
The [earlier VM observation](vm_observation.json) remains a dated screen
transcription and retains its then-pending transfer status for provenance.

[Paired JSON](paired_comparison.json) and [JSONL](paired_comparison.jsonl) contain
all 300 audit IDs, original machine labels, both human reviews, new keep/drop
decisions, and source retrieval metadata. No claims were deduplicated. Article
text and quotations remain on the VM. [Full metrics](summary.json) include
individual category precision/recall and confusion counts for every label.

## Results

| Frame | Human reference | Precision before | Precision after | Change, percentage points | Invalid removed | Valid lost |
| --- | --- | --- | --- | --- | --- | --- |
| Historical, 250 | Reviewer 1 | 70.8–71.2% | 77.6–78.0% | +6.77–6.84 | 25 | 11 |
| Historical, 250 | Reviewer 2 | 68.4% | 76.6% | +8.24 | 29 | 7 |
| Modern supplement, 50 | Reviewer 1 | 70.0% | 74.4% | +4.42 | 4 | 3 |
| Modern supplement, 50 | Reviewer 2 | 66.0% | 72.1% | +6.09 | 5 | 2 |
| All 300, descriptive only | Reviewer 1 | 70.7–71.0% | 77.0–77.4% | +6.38–6.43 | 29 | 14 |
| All 300, descriptive only | Reviewer 2 | 68.0% | 75.9% | +7.88 | 34 | 9 |

Reviewer 1 has one unclear human decision, retained after filtering. Bounds
assign that same decision either invalid or valid in both denominators. The
reviewers' disagreements remain intact. Neither is treated as adjudicated gold.

These candidates had already passed the original production verifier. This is
the effect of an **additional** filter on the existing reviewed sample, not an
estimate of the original production pass's effect. These are descriptive sample
proportions, not population-weighted estimates. Human-valid retention (93.4%
and 95.6%) is not recall over all forecasts in source articles. Historical and
modern frames remain separate; no LOC or old crisis-window claims enter.

## Specific labels

The extra pass did not relabel any claim. The following descriptive combined
figures are exact agreement conditional on each reviewer's inclusion decision:
Reviewer 1 has 212 included claims before and 198 after; Reviewer 2 has 204 and
195. Historical and modern results are reported separately in the full report.

| Field | Reviewer 1 before → after | Reviewer 2 before → after |
| --- | --- | --- |
| Topic | 87.3% → 87.9% | 88.7% → 88.7% |
| Direction | 86.3% → 86.4% | 87.3% → 87.7% |
| Price direction | 76.4% → 76.8% | 76.0% → 76.4% |
| Unemployment direction | 85.4% → 84.8% | 84.8% → 84.6% |
| Horizon, exact months | 66.5% → 65.7% | 71.1% → 70.3% |
| Confidence | 71.7% → 72.7% | 73.5% → 73.3% |
| Voice | 75.5% → 74.7% | 73.0% → 72.3% |
| Speaker name, exact | 67.9% → 67.2% | 59.8% → 60.0% |
| Scope | 65.1% → 65.7% | 66.7% → 66.7% |
| Quoted forecaster | 72.6% → 72.2% | 74.5% → 74.4% |
| Current state | 76.6% → 75.5% | 73.5% → 74.4% |

Filtering improves inclusion precision but does not consistently improve label
agreement. These changing-subset differences are not evidence of label
correction; on identical retained claims, agreement is unchanged. Literal NA
matches count toward field agreement; missing/uncertain fields receive no match
credit. Individual-category precision/recall uses resolved fields only, with
explicit support counts and undefined zero-support rates. These metrics assess
label assignment, not whether the economic prediction proved correct. Current
state for Reviewer 1 excludes the original batch's incompatible convention,
leaving denominators of 107 before and 102 after.

## Run and reproduction

`src/proquest_reverify300.py` prepares source-linked requests inside TDM and
requires `--run` to call the model. The run used the existing VM verifier prompt,
one candidate per call, temperature 0, and maximum 256 output tokens. Human
labels, realized outcomes, previous verdicts, and verifier prose were excluded
from prompts. Exclusive attempt files and a process lock prevent duplicate
attempts. Prompts, source text, and raw responses remain on the VM.

VM folder:
`/home/ec2-user/SageMaker/election_arm/gpt4omini_reverify300_20261022/`.
The prepared run notebook used the production environment's installed OpenAI
client after the default notebook kernel lacked that package; that failed
initialization made no model calls.

`validation/proquest_review/ProQuest_Compare300_20261022.ipynb` computed the
displayed comparison on the VM with frozen local human decisions joined by
exact ordered audit ID. It contains no model calls. Reproduce the complete local
comparison, including individual labels, with:

```bash
/tmp/bode-econ-audit-20261019/bin/python src/proquest_reverify_comparison.py \
  --export data/scored/proquest/reverify300_20261022/categorical_export.json
```

The comparator verifies the full 300-claim order, selection hash, saved baseline
input hashes, status/count consistency, and ordered prompt hashes before writing
`summary.json`, `paired_comparison.json`, `paired_comparison.jsonl`, and
`report.html`. It also verifies the export SHA-256 in `vm_observation.json` and
reproduces every field's pre-filter counts from the earlier audit. It makes no
API calls.

Validation: all ten focused runner/comparison tests passed, as did the main
offline/scoring/forecast suites (97/33/33 checks). Original source exports,
frozen human decisions, and production model outputs were not modified.
