# ProQuest TDM integration

This branch preserves the ProQuest extraction/export pipeline and its source
artifacts. The current paper, two-reviewer 300-claim audit, additional verifier
run, and economic analyses are on [main](https://github.com/bodeb-gif/datascience-rise-practicum-private/tree/main).

## Current entry points

- [VM workflow and export guide](JeremysStuff/election_arm/PROQUEST_TDM_GUIDE.md)
- [Pipeline files and offline checks](JeremysStuff/election_arm/README.md)
- Annual raw-candidate exports: `JeremysStuff/election_arm/data/predictions/`
- Annual machine-verified exports: `JeremysStuff/election_arm/data/verified/`
- Current manuscript: [`output/pdf/jcss_submission.pdf` on main](https://github.com/bodeb-gif/datascience-rise-practicum-private/blob/main/output/pdf/jcss_submission.pdf)

The 111 annual shards per set cover 1900–2010 and are preserved byte-for-byte.
Older crisis-window exports remain as provenance only; do not pool them with
annual data. Human-review records, reference spreadsheets, and the historical
changelog are retained. The directory name `election_arm` is kept for existing
VM paths; it does not identify the active research scope.

## October 22 cleanup

Removed the abandoned election/NYT download and extraction path, 47 title-only
files, obsolete planning documents, the superseded extraction-audit proposal,
and the old pooling patch/adapter. Tests for retired modules were removed;
remaining parser, extraction, export, progress, and legacy scorer checks remain.
No ProQuest export or human annotation was removed or edited.

`cleanup_20261022.json` records every deleted path, its hash, and the base commit
`774b68f`. The files remain recoverable from Git history. This is an ordinary
cleanup commit, not a history rewrite. No VM processes or files were changed.
