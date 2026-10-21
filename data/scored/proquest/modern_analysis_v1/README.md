# Modern ProQuest exploratory analysis

Open [report.html](report.html) for the results, figures, limitations and future
forecast interpretation. This separate run was authorized October 20, 2026 under
`docs/publication/MODERN_ANALYSIS_AMENDMENT_20261020.md`. Prior modern outcome
exposure is unknown; this is not an untouched confirmatory holdout.

## Main results

- 91,099 input claims after excluding 19 default-kept exceptions. All 33,071
  empty export records are excluded from inputs; source exports are unchanged.
- 56,886 mature, supported claims from 23,775 articles were evaluated using
  equal article weights. Primary frozen RNN AUC: 0.7376; metadata-plus-history
  logistic control: 0.6545. Both polarization measures: RNN AUC 0.7486.
- Paired five-year block intervals cross zero for the main model improvements.
  These intervals are not new permutation p-values. Employment AUC is 0.3064,
  an important failure hidden by pooled performance.
- Separate monthly models selected using pre-2011 results estimate 6.9% recession
  onset risk and 28.0% industrial-production decline risk for September 2026
  through August 2027. Complete newspaper inputs end in August 2026; this is not
  an October-origin forecast. Candidate recession probabilities range 6.9–27.0%.
- Modern recession evaluation contains one distinct onset. Selected-model
  improvement intervals cross zero. The production-decline probability is
  effectively equal to its historical base rate. These are research estimates,
  not established calibrated probabilities or a strong downturn call.
- The greater-than-2% production-decline sensitivity performs worse than its
  base-rate comparator; all results, including unfavorable ones, are retained.

## Evidence and reproduction

`run_manifest.json` records sources, code and feature hashes. Claim predictions
were saved before outcome attachment. `historical_reproduction.json` verifies
the frozen models against saved historical predictions. All 30 original frozen
artifacts remain unchanged. `completion_manifest.json` inventories final outputs.

`claim_*` files contain predictions, exclusions, calibration, subgroup metrics
and paired intervals. `downturn/` contains all five candidate models per target,
pre-2011 selection records, annual refit audits, saved January 2026 bundles,
predictions, outcomes and comparisons. Source checks and reference gaps are
retained alongside the results. Failed FRED refreshes are recorded; preserved
reference snapshots were used, with no interpolation of missing outcomes.

The author's 150 historical human reviews were received separately in
`../source_review_150_v1/`. They assess extraction, not modern predictive accuracy.

Run entry points from the repository root, using the working environment
`/tmp/bode-econ-repro-20261019/bin/python` and `MPLCONFIGDIR=/tmp/bode-mpl`:

1. `src/proquest_modern_analysis.py prepare` prepares the dated intake/features.
2. `src/proquest_modern_analysis.py claims` evaluates frozen claim models.
3. `src/proquest_downturn.py` runs the separate monthly forecasting study.
4. `scripts/report_proquest_modern.py` rebuilds the report from saved results.

This is a fixed dated run: preparation and downturn execution refuse existing
destinations. Preserve this run when adding data; create a new versioned output
location and dated configuration, recording any successor model development
separately. Do not tune to the modern results and then relabel them as a holdout.
The broken repository-root `.venv` must not be used.

Validation passed: 97 offline, 33 scoring and 33 forecast tests, plus 6 modern
analysis, 4 export-receipt and 6 frozen-intake tests. Figures were visually checked.
