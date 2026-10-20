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
Source validation, modern evaluation and substantive manuscript drafting remain
deferred unless the user reopens them.

Run scripts from the repository root. Keep the flat source layout: entry points
use bare module imports, and saved models/manifests refer to existing paths.
Do not change frozen artifacts to accommodate housekeeping. Use the working
environment and version lock; the old repository `.venv` is broken.

After code changes run `tests/test_offline.py`, `tests/test_scoring.py` and
`tests/test_forecasts.py`, plus relevant ProQuest tests. Never run paid extraction
without authorization and a cost cap. Keep keys in ignored local configuration.

Earlier LOC methods and poster results remain in their existing documentation
and result folders. Their presence is historical context, not the active scope.
