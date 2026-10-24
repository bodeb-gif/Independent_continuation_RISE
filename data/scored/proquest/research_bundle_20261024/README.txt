PROQUEST RESEARCH RESULTS — OCTOBER 24, 2026

This bundle preserves the complete research outputs in four result directories,
including analysis code, model forecasts/checkpoints, references, specifications,
figures, test logs, source-review preparation, and hash manifests.

The archive contains 15,055 files. Python bytecode and OS metadata are excluded.
The original annual ProQuest exports are unchanged and are not duplicated here.
The archive was checked file by file against the local research directories.

READ THE RESULTS
  discovery_report.html       Full ten-hour investigation
  block_length_report.html    Requested one-year/six-month block sensitivity

These are self-contained browsing copies. Artifact links become available after
extracting the archive; the canonical reports remain unchanged inside it.

EXTRACT (run from the repository root)
  tar -xf data/scored/proquest/research_bundle_20261024/proquest_research_20261024.tar.xz

VERIFY THE ARCHIVE (run from this bundle directory)
  shasum -a 256 -c proquest_research_20261024.tar.xz.sha256

Extracted directories are ignored by Git so that thousands of model checkpoints
stay out of the change list. The compressed archive is the versioned backup.
Existing local result directories are preserved. Extract into a separate checkout
if you want to compare files without replacing local copies.

INTERPRETATION
The ten-hour investigation added 136 questions to 68 earlier tests. Related
employment-information associations pass the original 204-test screen, but their
significance is sensitive to temporal-dependence assumptions and source labels
still require validation. No tested ML forecasting gain passes the pooled
correction. Shorter inference blocks strengthen nominal GRU evidence without
establishing a corrected discovery. The forecast horizon stays six months.
The three required software suites passed all 163 checks.

CONTENT DIRECTORIES
  data/scored/proquest/discovery_session_20261022/
  data/scored/proquest/discovery_session_20261023_extended/
  data/scored/proquest/economic_findings_audit_20261022/
  data/scored/proquest/block_length_followup_20261024/

The canonical manifests and environment records describe reproduction requirements;
the temporary ML environment may need to be recreated on another machine.
