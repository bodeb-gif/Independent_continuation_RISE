# ProQuest paper workspace

This folder holds the paper on economic forecasts reported in selected US
newspapers, 1900–2010. It brings the existing writing together with links to
the evidence. The manuscript remains an unfinished outline; source validation,
modern evaluation and substantive drafting are still deferred.

| Folder | Contents |
| --- | --- |
| [manuscript](manuscript/outline.md) | Existing outline and historical evidence tables |
| [planning](planning/concept.md) | Paper question, scope and proposed contribution |
| [references](references/literature.md) | Existing literature comparison and source links |
| [figures](figures/README.md) | Figure index with canonical generated files |
| [tables](tables/README.md) | Table index with result roles and limitations |

The [publication plan](../docs/PROQUEST_PUBLICATION_PLAN.md) covers the proposed
publication route. The [latest analysis](../docs/PROQUEST_ANALYSIS_DEEP_DIVE.md)
includes results produced after the manuscript outline and should guide any
later revision. Current evidence concerns measurement sensitivity and uncertain
incremental predictive value; it does not establish RNN superiority.

## Where the supporting work lives

- [Methods and protocols](../docs/publication/README.md): analysis specification,
  source review, polarization and the frozen modern-evaluation procedure.
- [Analysis documentation](../docs/README.md): findings, execution and data handoff.
- [Results index](../data/scored/proquest/README.md): primary evidence, exploratory
  analyses, model candidates and reproducibility checks.
- [Code index](../src/README.md): entry points grouped by purpose.

Generated tables, figures and model files remain under `data/scored/proquest/`
at their recorded paths. Use those canonical outputs rather than maintaining
independent copies in this folder. Future publication-specific figures and
tables can be placed in the corresponding subfolders with provenance links.

The three writing files were relocated without substantive edits. Their former
paths in `docs/publication/` point here; [organization.json](organization.json)
records the move and hashes. Frozen protocol files and source exports were not moved.
