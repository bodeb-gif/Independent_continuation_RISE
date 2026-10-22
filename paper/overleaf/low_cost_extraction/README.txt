OVERLEAF PROJECT: LOW-COST EXTRACTION OF ECONOMIC FORECASTS

SUPERSEDED OCTOBER 22, 2026: this split project is an earlier draft. Use
paper/overleaf/jcss_submission/ or output/overleaf/jcss_submission.zip for the
current Journal of Computational Social Science revision. Its canonical source
is paper/manuscript/low_cost_extraction.tex. The instructions below describe
this older project only; its manuscript text has not been synchronized.

Upload the ZIP as a new Overleaf project. Select main.tex as the main document and pdfLaTeX as the compiler. Use TeX Live 2025 or newer. Recompile until cross-references settle.

EDITING GUIDE
main.tex: assembles the paper in order.
preamble.tex: document class, packages, typography, colors, margins, and macros.
frontmatter.tex: title, date, abstract, and keywords.
sections/: one file per main section, plus the disclosure.
appendices/: one file per appendix.
references.tex: all 33 references in a natbib-compatible thebibliography environment. Edit entries here and cite their existing keys with \citep or \citet. BibTeX is not needed.
figures/: the four vector PDF figure assets; the workflow diagram and all tables remain editable LaTeX in the relevant section.

Build locally: run pdflatex -interaction=nonstopmode -halt-on-error main.tex repeatedly until labels settle (usually two or three passes).

This is a self-contained typesetting copy of the revised manuscript. The prose, empirical results, bibliography, and figures are preserved. Repository paths printed in the evidence appendix identify the original research files; they are documentation, not compilation dependencies. No source exports, restricted article text, Python environment, or analysis rerun is needed to compile this project.

The original repository manuscript remains at paper/manuscript/low_cost_extraction.tex. Edits to this split project do not automatically synchronize back to that file.
