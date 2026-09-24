# Active analysis scope

Analyze only the annual ProQuest economy claims (1900–2010) in
`data/proquest/verified/`, with `data/proquest/raw/` as a sensitivity set.
LOC pages/claims are for extraction validation only. Exclude old crisis-window
exports from analysis. The historical LOC pipeline/results remain on main but
must not be pooled into ProQuest results.

Start with `docs/PROQUEST_ANALYSIS.md` and `src/analyze_proquest.py`.
Write derived analysis into `data/scored/proquest/` and keep the source exports
unchanged. Do not automatically deduplicate stripped labels without claim-level
evidence. Retrospective window annotations and verifier prose are not features.
Score against deterministic real-world outcomes; use time-block evaluation and
only information available at print time for model features.

The old repo-root `.venv` is broken; do not use it. Run the main test suites
(`tests/test_offline.py`, `tests/test_scoring.py`, `tests/test_forecasts.py`)
after code changes using a working environment.
