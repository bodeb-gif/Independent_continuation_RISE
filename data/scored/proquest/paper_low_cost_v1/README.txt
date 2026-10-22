LOW-COST EXTRACTION MANUSCRIPT - OCTOBER 20, 2026

Final paper: output/pdf/low_cost_extraction.pdf
Editable source: paper/manuscript/low_cost_extraction.tex

This directory presents saved evidence. It does not fit models, rescore claims,
edit source exports, or combine LOC observations with ProQuest estimates.
Modern results are reported separately from the historical analysis.

From the repository root, using the working environment on this machine:

MPLCONFIGDIR=/tmp/bode-paper-mpl /tmp/bode-econ-repro-20261019/bin/python data/scored/proquest/paper_low_cost_v1/build_figures.py
mkdir -p tmp/pdfs/low_cost_extraction output/pdf
pdflatex -interaction=nonstopmode -halt-on-error -output-directory=tmp/pdfs/low_cost_extraction paper/manuscript/low_cost_extraction.tex
pdflatex -interaction=nonstopmode -halt-on-error -output-directory=tmp/pdfs/low_cost_extraction paper/manuscript/low_cost_extraction.tex
cp tmp/pdfs/low_cost_extraction/low_cost_extraction.pdf output/pdf/low_cost_extraction.pdf

The source manifest records 68 evidence files and all 222 historical raw and
verified annual export hashes. Cost projections come from the dated LOC report;
the script does not query current model prices. The bibliography is embedded
in the LaTeX source. Build requirements are Python with matplotlib and NumPy,
and TeX Live with the packages named in the manuscript preamble.

Quality checks record counts, hashes, PDF structure, and the three required
test-suite results. All rendered pages were visually reviewed; detailed checks
included the title, statistical tables, figures, evidence appendix, and references.
PyMuPDF was used to render pages because system Poppler was unavailable.

The paper has no inferred author name or affiliation. The requested style
attachment was not available to the session, so the layout uses conventional
single-column academic typography, numbered exhibits, and linked references.
