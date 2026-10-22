# Journal of Computational Social Science: author-review draft

Revised October 22, 2026. This package has not been submitted.

## Current files

- Authoritative source: `paper/manuscript/low_cost_extraction.tex`.
- Readable draft: `output/pdf/jcss_submission.pdf`.
- Self-contained LaTeX upload: `output/overleaf/jcss_submission.zip`.
- Unpacked upload: `paper/overleaf/jcss_submission/`.
- Build and verification receipt: `data/scored/proquest/paper_jcss_v1/build_receipt.json`.

The older split Overleaf project is superseded by this journal package. Editing
the canonical source and rebuilding keeps the journal copies synchronized.

## What changed

The manuscript now leads with the measurement problem, the paired two-reviewer
audit, and the consequences of inclusion filtering for interpretation. The
abstract combines the 1900–2026 corpus totals and reports descriptive results
for the full 300-claim audit. Tables report the additional
pass on the exact 300 reviewed candidates and all eleven label fields against
each reviewer, preserving historical and modern denominators. Predictive
results remain exploratory. All LOC material has been removed from the paper.
The appendices are condensed to the modern model comparison, additional label
validation, and a compact evidence/reproduction guide; ancillary examples,
cost analysis, downturn illustrations, and external-data commentary are omitted.

The draft uses the official Springer Nature two-column class, numbered
references, a 184-word abstract, six keywords, and Statements and Declarations.
Requirements were checked against the [journal's official submission
guidelines](https://link.springer.com/journal/42001/submission-guidelines).

## Details the author must finish

- Confirm affiliation and postal address. Name **Bode Bosell** and corresponding
  email **bodeb@bu.edu** were supplied; no institution was inferred from the email.
- Confirm the complete author list, contributions, acknowledgments, funding,
  and financial/non-financial competing interests.
- Confirm the applicable ethics determination and any consent obligations for
  source-review participants. No approval or exemption has been invented.
- Supply a permanent public archive or reviewer-access URL and confirm the
  redistribution permissions for the material included there. Restricted
  ProQuest text is not part of the journal source ZIP.
- Review all prose, results, references, and AI-use disclosures; replace the
  explicitly pending declarations before submitting.
- Prepare the requested handling-editor and reviewer suggestions in the
  submission portal, along with author profile/identifier details as applicable.

## Scientific limits retained in the draft

The audit samples previously retained candidates, so it estimates the effect
of an **additional** filter, not the original production pass's precision gain
or source-level extraction recall. Human judgments are unadjudicated, and prior
label exposure is disclosed. Label agreement after filtering is conditional on
each reviewer's inclusion and does not mean labels were corrected. The unclear
human case is bounded; the one parsing failure is retained without retry.

The economic sensitivity results are saved analyses, not recalculated from
human-corrected labels. Modern outcome exposure prevents a confirmatory-holdout
claim. These limitations remain visible rather than being resolved by manuscript
wording.

## Rebuild

From the repository root, use a working Python environment with matplotlib:

```sh
python scripts/build_jcss_package.py
cd paper/overleaf/jcss_submission
pdflatex -interaction=nonstopmode -halt-on-error main.tex
pdflatex -interaction=nonstopmode -halt-on-error main.tex
pdflatex -interaction=nonstopmode -halt-on-error main.tex
```

The package has no external bibliography dependency. Copy the settled PDF to
`output/pdf/jcss_submission.pdf` after inspecting the rendered pages. Figure
generation reads saved summaries and makes no API calls. The repository-root
`.venv` is broken and must not be used.
