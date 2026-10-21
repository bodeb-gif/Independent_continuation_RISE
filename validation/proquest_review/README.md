# ProQuest review pilot

## In-workbench review (installed October 19, 2026)

Open `election_arm/ProQuest_Review_Offline.ipynb` in the TDM Jupyter workbench,
using `conda_python3`, and run all cells. The current session also has an
**Output View** tab displaying just the review form. Enter the actual reviewer
name, read each passage, answer, and save/lock before revealing machine labels.

Live checks recovered **12/12** original quote-bearing records and articles,
with each reconstructed export SHA-256 and article ID/date checked. Eight quotes
occur once verbatim in article text; four have no exact verbatim occurrence and
remain flagged for closer source inspection. This is retrieval evidence, not
human validation. The in-VM synthetic save/reopen/lock check passed; real human
event count was zero at handoff. The VM-only lineage report is
`source_review_pilot_tdm_v1/retrieval_check.json`.

Both `sample-2025.12.578` and `conda_python3` lacked the Python widget package.
The offline notebook therefore installs official PyPI `ipywidgets` 8.1.9,
`comm` 0.2.3 and `jupyterlab_widgets` 3.0.17 into the bundle's `widget_vendor/`.
It adds the frontend assets under the user's Jupyter labextensions directory
only when no existing user manager directory is present. It does not modify
analysis environment packages. Wheel hashes are in [offline_wheels.json](offline_wheels.json).
The original `ProQuest_Source_Review.ipynb` in the VM is the earlier version
without these dependencies; use **ProQuest_Review_Offline.ipynb** for review.

[ProQuest_Source_Review.ipynb](ProQuest_Source_Review.ipynb) is the uploadable
TDM Jupyter version. It embeds the review code and the unchanged twelve-record
pilot, with no article text, economic outcomes or human responses. This base
notebook requires widgets already available in the selected kernel. The offline
build described below is the version deployed and checked in this workbench.

Upload this one notebook into the ProQuest TDM Jupyter file browser and run its
cells with the existing Python kernel. It installs its bundled files under
`/home/ec2-user/SageMaker/election_arm/source_review_pilot_tdm_v1/` and opens
passages beside the questions. Existing files with different contents cause a
stop rather than an overwrite. It uses the workbench's `ipywidgets`; no extraction,
verification, model API call or new sample is run. If widgets are unavailable,
resolve the kernel environment before reviewing; do not silently switch to
model-generated judgments.

The source loader reconstructs `strip_for_export.py` output (drop `quote` and
`claim_text`, retain nonblank record order, default JSON serialization) and
requires its entire SHA-256 to match the frozen sampled export. This links the
export's physical row to the quote-bearing VM record's ordinal and records both
VM file hashes and physical locations. It does not match stripped labels, merge
duplicates, or select a sentence based on a label. The lineage assumes the
original stripping order was preserved; a different export format or changed
file requires investigation, not relaxed matching. Missing, conflicting, or
changed sources remain in the sample. Human mapping judgments start blank.

Enter your name, read the passage/context, answer, and **Save & lock first pass**.
Machine labels are revealed only after a unique mapping and a saved first pass.
Unresolved mappings require only mapping status, prior label exposure and a
reason. Drafts, immutable first passes, comparison drafts, comparisons and
corrections are saved in `responses/human_review.json` in the VM bundle directory.
Corrections append to the audit trail. Concurrent stale sessions cannot overwrite
newer saves. Elapsed time includes time away from the notebook. Blinding is a UI
workflow, not protection against deliberately opening the comparison file.

**Keep article text, responses, and the executed notebook inside TDM.** There is
no download/export button. Do not commit response files. A future derived-label
export must explicitly exclude source prose and free-text response fields.
Before handoff, check recovery counts for all twelve rows, confirm widgets render,
and test persistence with a separate synthetic fixture rather than filling real
pilot answers. No human validation has been completed by preparing this notebook.

Rebuild and test from the repository root:

```bash
python scripts/build_proquest_tdm_review.py
# For TDM's kernels without widgets, obtain the official wheels on the local
# machine, then package them; no Internet access is needed from the VM.
python scripts/build_proquest_tdm_review.py --wheel-directory /path/to/wheels --output /tmp/ProQuest_Review_Offline.ipynb
python tests/test_proquest_tdm_review.py
```

The offline builder needs one pure-Python wheel each for `ipywidgets`, `comm`,
and `jupyterlab_widgets`; use the versions/hashes above. Upload through AppStream
**My Files → Temporary Files**, then use Jupyter's upload button and choose
**Temporary Files** in the remote Windows picker. AppStream is a Windows desktop
hosting the browser; the Jupyter kernel/files are on the separate Linux SageMaker
machine. AppStream uploads must therefore be imported into Jupyter before use.
The Chrome extension needs file-URL access for local uploads. Transfer completion
can lag behind the browser accepting a file; verify the remote listing.

[ProQuest_Review_Checks.ipynb](ProQuest_Review_Checks.ipynb) reruns source linkage
and synthetic persistence checks inside TDM. It prints counts/addresses, never
quotes, and never writes synthetic answers to the real response store. Local
tests passed: 10 review tests, 2 original interface tests, and all 163 checks in
the three required main suites. The 30 frozen model/evaluation files were unchanged.

## Original standalone browser version

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
