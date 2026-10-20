# ProQuest review pilot

Open [the prepared interface](../../data/scored/proquest/source_review_pilot_v1/review.html)
in a browser. It contains the original 12 retrieval addresses, no source passages,
no economic outcomes and no human answers. The underlying
[rubric and sampling protocol](../../docs/publication/REVIEW_PROTOCOL.md) remains version 1.
This is preparation for review, not completed source validation.

## Review workflow

1. Retrieve the article in the authorized ProQuest environment and recover the
   original claim ID or source offsets through VM lineage. A physical export line
   is an address, not evidence of a uniquely identified passage. Record a locator,
   mapping reason and lineage. Do not inspect the machine-label file beforehand.
2. Enter the actual reviewer and any previous machine-label exposure. Interpret
   the source using the first-pass fields. Unknown target endpoints stay blank;
   use “unknown” for an unknown original forecast date. A context note can refer
   to evidence in the permitted environment rather than reproduce the passage.
3. Save and lock the first pass. For `ambiguous`, `unavailable` or `wrong_article`,
   only reviewer, mapping status, reason and blinding are required. Such records
   remain in the sample, are marked unassessable and do not open the comparison.
4. For unique mappings, load the adjacent
   [comparison.json](../../data/scored/proquest/source_review_pilot_v1/comparison.json)
   and explicitly reveal this record. Grade each field against the source, then
   benchmark compatibility and joint usability. Record an error category, or
   `none`, and a comparison note. Save the comparison. Outcomes are never shown.
5. Export review JSON frequently and before closing. Store human responses and
   any permitted source notes in your authorized working location, separately
   from generated artifacts. Do not commit source passages or response exports
   to this repository as part of interface preparation.

The interface saves drafts locally when the browser supports storage for local
files. It also saves partial comparison answers. A failed storage operation is
reported; exported JSON is the portable backup. Restore uses an empty browser
workspace/profile and rejects a different pack or rubric, unknown fields,
invalid categories and impossible review-stage ordering. Existing work cannot
be overwritten by import. Keep the generated HTML and comparison file together
when moving between authorized machines.

Locked answers have no overwrite control. Corrections append timestamped notes
with an actual reviewer; a later analysis must explicitly reconcile amendments.
This includes a mapping that becomes uniquely recoverable after an initial
unassessable decision. Exported records retain the original answer. Timestamps
are local device time; elapsed seconds include idle time and time away from the
record. They are not a precise measure of active annotation time.

The comparison JSON is a separate, readable file. UI gating reduces accidental
exposure; it cannot enforce blinding if the reviewer opens that file or a source
export independently. The local JSON is not a tamper-proof research database.
Keep dated backups and disclose prior exposure. No model-generated labels may
be entered as human judgments.

## Rebuild and checks

From the repository root, using a working Python environment:

```bash
python src/proquest_review.py
python tests/test_proquest_review.py
node tests/test_proquest_review.cjs
# Optional browser integration test: Playwright module and installed Chrome required.
node tests/test_proquest_review_browser.cjs
```

The builder verifies the sampled source hashes and article/date addresses, and
records input/output hashes in the generated manifest. `review.js` is the shared
state machine. `review.html` is the UI template; neither is a completed audit.
Browser tests use explicitly synthetic IDs in temporary files and isolated
profiles. They view the actual pilot only with empty answers.

After the pilot, assess retrieval feasibility and revise/freeze the rubric before
drawing the main sample. No main sample is drawn here; no pilot completion,
source validity rate, recall estimate or inter-annotator agreement is implied.
