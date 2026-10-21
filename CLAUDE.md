# Repository guidance

Follow [AGENTS.md](AGENTS.md), the [research plan](docs/RESEARCH_PLAN.md), and
[active analysis guide](docs/PROQUEST_ANALYSIS.md). The active corpus is annual
ProQuest economy claims, 1900–2010, with verified exports primary and raw
exports as sensitivity. LOC remains extraction-validation and historical
reproduction material; do not pool its outcomes into ProQuest analyses.

## Working locations

- [Paper workspace](paper/README.md): existing outline, concept and literature.
- [Code index](src/README.md): active entry points grouped by purpose.
- [Results index](data/scored/proquest/README.md): evidence, experiments and checks.
- [Reproducibility](docs/PROQUEST_REPRODUCIBILITY.md): environment and rebuild.
- [Data handoff](docs/PROQUEST_DATA_HANDOFF.md): later-data preparation.

Keep source exports unchanged. Use deterministic outcomes, print-time features,
chronological evaluation and explicit maturity rules. Do not deduplicate stripped
claim labels without source evidence. Preserve unsuccessful experiments as part
of the evidence; distinguish them from superseded execution logs or exact copies.
The user reopened human source-validation preparation on October 19, 2026:
make review easy inside ProQuest TDM Studio. Modern exports were received on October 20 into `data/proquest/modern/20261020/`; evaluation readiness still awaits stage/provenance reconciliation and an exposure statement;
substantive manuscript drafting remains deferred.

## ProQuest TDM workbench memory

This is **ProQuest TDM Studio's browser Jupyter workbench**, not an SSH VM.
Open the workbench through `https://tdmstudio.proquest.com/home`.
The project is `/home/ec2-user/SageMaker/election_arm/`; annual article text is
`data/raw/proquest_economy_YYYY.jsonl`, quote-bearing verified claims are
`data/verified/pred_proquest_economy_YYYY.jsonl`. Full text stays inside TDM.
Do not download quotes or executed review notebooks into this repository.
Do not interrupt ongoing extraction/verification or launch duplicate jobs.

The detailed historical setup guide remains in Git:
`git show origin/proquest-tdm-integration:JeremysStuff/election_arm/PROQUEST_TDM_GUIDE.md`.
The workbench cannot pull from GitHub. AppStream's Windows desktop hosts the
browser; Jupyter files/kernel live on Linux SageMaker. Use AppStream My Files
upload, then Jupyter upload from the remote Windows Temporary Files folder.
The installed entry point is `election_arm/ProQuest_Review_Offline.ipynb`, kernel
`conda_python3`; a clean **Output View** tab was left open. The offline widget
packages are isolated inside `source_review_pilot_tdm_v1/widget_vendor/`.
Live checks recovered all 12 pilot sources (8 verbatim quote matches, 4 needing
closer source inspection); synthetic save/reopen/lock passed; no human responses
were entered. See [review setup](validation/proquest_review/README.md) for rebuild,
lineage checks, and the VM save location. Never download the executed notebook.

Run scripts from the repository root. Keep the flat source layout: entry points
use bare module imports, and saved models/manifests refer to existing paths.
Do not change frozen artifacts to accommodate housekeeping. Use the working
environment and version lock; the old repository `.venv` is broken.

After code changes run `tests/test_offline.py`, `tests/test_scoring.py` and
`tests/test_forecasts.py`, plus relevant ProQuest tests. Never run paid extraction
without authorization and a cost cap. Keep keys in ignored local configuration.

Earlier LOC methods and poster results remain in their existing documentation
and result folders. Their presence is historical context, not the active scope.

## October 20 receipt and human-review update

Modern 2011–2026 verified exports are preserved separately under
`data/proquest/modern/20261020/` (91,118 retained claims; 19 default-kept
exceptions). See `data/scored/proquest/modern_export_20261020/receipt.json`.
Do not activate scoring from transport integrity alone. The 2011 empty-row
repetition and 2,128 stage articles absent from exports need VM reconciliation.
All 30 frozen evaluation/model files remain unchanged.

The author confirms human review/editing of 150 claims in
`source_review_150_v1`, correcting the initial count of 100. Preserve earlier
AI exposure and current-state coding limitations. See that folder's dated human
attestation. The source-free export was approved and delivered; the author supplied all
150 rows in chat. Normalized labels and locally reconciled comparisons are
saved in the review folder. Do not export source prose or notes.

The author activated separate modern analysis on October 20 and requested both
12-month recession onset and production decline forecasts. See
`docs/publication/MODERN_ANALYSIS_AMENDMENT_20261020.md`. Empty rows and the 19
unresolved default-kept exceptions are excluded from derived model inputs;
source exports and frozen models remain unchanged. Prior modern outcome exposure
is unknown, so describe the evaluation as exploratory, not untouched holdout.
Claim correctness is not a recession probability. Forecasts from complete press
coverage have latest origin September 2026, using prints through August.

The completed run is `data/scored/proquest/modern_analysis_v1/report.html`.
Frozen claim RNN AUC is 0.7376 on 56,886 scored modern claims; employment AUC
is only 0.3064. Both-polarization AUC is 0.7486, but block intervals do not
establish improvement. Separate pre-2011-selected downturn models estimate
6.9% recession onset and 28.0% production decline for Sep 2026–Aug 2027;
only one distinct modern recession onset is evaluable. Treat these as research
estimates, not established calibrated risks. Preserve this completed run and
unfavorable sensitivities; do not retune on modern results and call them held out.

The author subsequently confirmed human validation of another 150 claims in
`source_review_additional150_v1`: 100 historical and 50 modern, all modern years
represented. Chrome verified the live canonical categorical hash matches the
local copy; original Codex labeling history remains documented. Combined human
review now covers 300 distinct claims (250 historical, 50 modern), with 212
included, 87 excluded, one unclear. See the additional batch's
`human_review_status.html` and `human_review_attestation_20261020.json`.
Do not describe this as independent blinded annotation or pool current-state
agreement across the original and additional batches. Frozen modern analysis
reports predate this update; their statement of no modern human sample is now
superseded by this separate review receipt. Model results were not changed.

Reviewer-attribution correction: the author clarified that AI only explained
context in a couple of situations; the author performed the human validation.
Use "human validation with limited AI contextual assistance," rather than
"human review of AI-assisted labels." Earlier Codex metadata describe artifact
history and do not establish who made the author's review decisions. Preserve
that history without overstating AI involvement. Blinding and a second human
reviewer remain unestablished.
