# Economic forecasts in historical newspapers

This project studies the measurement, accuracy and predictive information of
forecasts reported in selected US newspapers. The active corpus is **annual
ProQuest economy claims, 1900–2010**. Machine-verified exports are primary and
raw exports provide sensitivity checks. LOC supports extraction validation;
its historical results are kept separate.

Start with the [research plan](docs/RESEARCH_PLAN.md) and
[active analysis guide](docs/PROQUEST_ANALYSIS.md).

## Project navigation

| Area | Starting point |
| --- | --- |
| Paper | [Workspace and existing outline](paper/README.md) |
| Analysis | [Findings and interpretation](docs/PROQUEST_ANALYSIS_DEEP_DIVE.md) |
| Results | [Evidence and experiment index](data/scored/proquest/README.md) |
| Code | [Entry points by workstream](src/README.md) |
| Reproduction | [Working environment and rebuild](docs/PROQUEST_REPRODUCIBILITY.md) |
| New data | [Preparation and handoff](docs/PROQUEST_DATA_HANDOFF.md) |
| Documentation | [Documentation index](docs/README.md) |

The evidence distinguishes forecast measurement from model improvement.
Outcome definitions materially affect some conclusions; historical RNN
superiority and stable incremental predictive value have not been established.
All tested model arms, including unsuccessful candidates, remain available.
Source validation, modern evaluation and substantive paper drafting are deferred.

## Running the analysis

Run commands from the repository root in a working environment installed from
`requirements-proquest-lock.txt`; do not use the broken root `.venv`.
Start with `python src/analyze_proquest.py`. Consult each analysis script's
specification before running it; versioned experiments generally refuse an
existing output directory. Derived outputs belong in `data/scored/proquest/`.
Original exports and frozen models/protocols must remain unchanged.

After code changes run:

```bash
python tests/test_offline.py
python tests/test_scoring.py
python tests/test_forecasts.py
```

Also run the relevant `tests/test_proquest*.py` checks. The reproducibility guide
covers an isolated rebuild and saved-model prediction checks.

## Historical and validation material

[LOC validation](validation/loc_review/README.md),
[gold extraction evaluation](validation/gold_extraction/PROTOCOL.md), and
[annotator comparison](validation/handgrade_newspapers/README.md) retain their
own populations and limitations. Earlier poster outputs, notebooks, LOC code
and model results remain for historical reproduction as required by AGENTS.md.
See [poster documentation](docs/POSTER.md) for that earlier project.

The [repository cleanup record](data/scored/proquest/repository_cleanup_v1/report.html)
identifies removed redundant execution artifacts, retained dependencies and
Git recovery instructions. It does not remove scientific results or rewrite history.
