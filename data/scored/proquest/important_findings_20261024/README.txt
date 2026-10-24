IMPORTANT PROQUEST FINDINGS - OCTOBER 24, 2026

Read important_findings.pdf (8 pages) or report.html.

Scope: annual verified ProQuest 1900-2010, raw sensitivity only. The historical
250-candidate human review is isolated from the modern supplement. LOC metrics
are explicitly separate extraction-validation development evidence.

New work: paired verification uncertainty and six tests; simultaneous accuracy
intervals across five populations and three temporal block lengths. These are
post-hoc, not preregistered. Existing results and frozen source exports are not
modified. New calculations and all non-significant results are retained.

Reproduce from repository root with scientific Python (do not use root .venv):
  /opt/anaconda3/bin/python3 data/scored/proquest/important_findings_20261024/analyze_evidence.py
  /opt/anaconda3/bin/python3 data/scored/proquest/important_findings_20261024/refine_accuracy_tails.py
  /opt/anaconda3/bin/python3 data/scored/proquest/important_findings_20261024/build_report.py
  /opt/anaconda3/bin/python3 data/scored/proquest/important_findings_20261024/validate_report.py

Use a copy when rebuilding to preserve this dated evidence snapshot. NumPy,
SciPy, pandas, matplotlib, ReportLab and PyMuPDF are required. Here, ReportLab
5.1.0 was installed separately under /tmp/bode-important-report-deps; the build
script also works if ReportLab is installed in the active interpreter. Set
MPLCONFIGDIR to a writable directory if needed. Quality checks record the
scientific library versions. The PDF was rendered with PyMuPDF because Poppler
was unavailable. All eight rendered pages were visually reviewed.

New precision intervals are paired article-cluster bootstrap intervals within
review batches; statistical tests compare enrichment and equal-cost errors
separately. One unclear human decision has both interpretations retained. The
unsuccessful model verdict is kept. No source candidates are deduplicated.
Fisher tails are independently checked with hypergeometric probabilities.

The accuracy family uses approximate simultaneous percentile intervals with
Bonferroni alpha across 15 contrasts, conditional on the original labels and
scoring rules. One million draws refine every original interval; the original
100,000-draw output is retained. Temporal dependence and label error remain.

External literature is linked in the report. Cost projections are dated,
archived development calculations, not current prices or equal-quality claims.

Key files:
  report_content.json                  Editable report content
  verification_tests.csv               All six new tests and corrections
  verification_effects.csv             Precision and retention estimates
  verification_sensitivities.csv       All retained sensitivity checks
  accuracy_simultaneous.csv             Original 100,000-draw intervals
  accuracy_tail_refinement.csv          One-million-draw precision audit
  source_verification.json              All 222 source hashes and token counts
  analysis_manifest.json                New analysis input hashes and versions
  quality_checks.json                   Source/statistics/document checks
  final_manifest.json                   Report evidence and deliverable hashes

The offline/scoring/forecast suites passed 97/33/33 checks. No model API calls,
new source review, model fitting, corpus edits, or paid extraction were performed.
