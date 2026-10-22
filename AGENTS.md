# ProQuest integration branch instructions

This branch contains the ProQuest economy extraction/export pipeline. Work in
`JeremysStuff/election_arm/`; the directory name is historical. The paper,
validated review packages, and current economic analyses are on `main`.

- Keep all existing ProQuest source exports and human-review records unchanged.
- Use annual 1900–2010 exports for historical analysis; old crisis-window exports
  are provenance only and must not be pooled into annual results.
- Restricted article text stays inside the authorized TDM VM. Export only
  permitted categorical records using the export checks.
- Retrospective window labels and verifier prose are not model features.
- Do not restart an extraction run or make paid API calls as part of maintenance.
  Check running processes before any separately authorized VM run.
- The old repo-root `.venv` is broken. Use a working environment and run
  `python JeremysStuff/election_arm/test_offline.py` after code changes.

See `README.md` and `JeremysStuff/election_arm/PROQUEST_TDM_GUIDE.md` for current
entry points. Legacy scoring helpers are retained for compatibility, not as the
current paper's scoring specification. Preserve exact row lineage and never
infer duplicate claims from categorical labels alone.
