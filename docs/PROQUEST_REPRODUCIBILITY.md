# ProQuest reproducibility and results inventory

The October 19, 2026 audit separates primary results, exploratory extensions, retained candidates, and failed improvement experiments. Source validation, modern-data evaluation, and manuscript drafting remain deferred. All analysis uses annual ProQuest exports; LOC and old crisis-window exports are excluded.

## Results roles

The [generated inventory](../data/scored/proquest/results_inventory_v1/inventory.html) and [machine-readable inventory](../data/scored/proquest/results_inventory_v1/results_inventory.csv) identify the existing runs, including the final article-direction audit. Primary describes a result's role in the analysis, not demonstrated superiority or source validity.

| Result | Current role |
| --- | --- |
| Legacy descriptive scores and target robustness | Primary individual-claim evidence; interpretation remains provisional |
| Selected simple macro benchmark | Primary aggregate-information comparison; stable incremental gains not established |
| Original richer macro model and class-frequency comparisons | Earlier benchmarks retained for transparency |
| Original 24-unit RNN | Frozen secondary reference; superiority to logistic controls not established |
| Polarization arms | Exploratory extensions; no replacement selected |
| 8-unit, 20-year-window RNN | Provisional development candidate; no fresh independent evaluation |
| Age-weighted RNN variants | Failed the fixed improvement rule; retained without promotion |
| Direction/comparator and article-direction diagnostics | Exploratory interpretation checks; no new model or primary baseline replacement |

The source/code snapshots and path-addressed hash comparisons are saved alongside the inventory. Historical creation hashes are not silently rewritten when development code changes. The separate original model freeze is checked explicitly.

## Fresh environment

[requirements-proquest-lock.txt](../requirements-proquest-lock.txt) records all 36 installed package versions used for the check. It was tested with Python 3.12.13 on macOS ARM64. It is a version lock, not a cross-platform wheel-hash lock. Do not use the broken repository-root `.venv`.

```bash
UV_CACHE_DIR=/tmp/bode-econ-uv-cache uv venv --python 3.12.13 /tmp/bode-econ-repro-new
UV_CACHE_DIR=/tmp/bode-econ-uv-cache uv pip install \
  --python /tmp/bode-econ-repro-new/bin/python \
  -r requirements-proquest-lock.txt
```

The completed environment installation used `--offline` and the existing local package cache; no source or reference downloads were needed. A machine without those cached versions needs package access. Preserve the interpreter/platform and package versions when comparing floating-point results.

## Isolated rebuild

```bash
MPLCONFIGDIR=/tmp/bode-econ-mpl /tmp/bode-econ-repro-new/bin/python \
  src/proquest_reproducibility.py \
  --out data/scored/proquest/reproducibility_next \
  --rebuild --python /tmp/bode-econ-repro-new/bin/python \
  --scratch /tmp/bode-econ-rebuild-next
```

Both output paths must be new. The harness copies source, tests, scripts and the small offline macro fixtures into an isolated workspace. It links existing input data for reading, gives rebuilt outputs separate locations, and retains every command log. It does not run downloads or overwrite historical results. Input links are a workflow isolation mechanism, not an operating-system read-only mount.

The [completed rebuild record](../data/scored/proquest/reproducibility_v5/rebuild_summary.json) and [comparisons](../data/scored/proquest/reproducibility_v5/rebuild_comparisons.json) cover the annual inventory, complete verified scoring tables, target and direction diagnostics, prepared inputs/outcomes, polarization features, both selected macro studies, and saved four-arm RNN/logistic predictions. Parsed table comparisons use tight numeric tolerances; gzip headers and embedded image timestamps need not be byte-identical. Neural training is exercised on synthetic fixtures; the 114-fit historical development search is not rerun.

The expanded rebuild passed 32 commands and 59 comparisons. The subsequent article-direction audit ran separately in the same fresh environment and passed its synthetic grouping test. The required offline, scoring and forecasts checks passed again after that addition (97/33/33). The latest results inventory snapshots all current code; the rebuild snapshot preserves the version actually executed.

An older offline test depended on a saved model merely to reach a missing-feature guard. It now supplies a synthetic empty model bundle and synthetic missing macro inputs to test that guard without model artifacts or network access. The legacy cached-series checks still use their small local fixtures. Earlier harness attempts and logs remain in `reproducibility_v1` and `v2`; `v3` and `v4` record intermediate successful coverage. Use `v5` for the expanded rebuild.

## Boundaries

Reproducibility establishes computational consistency, not semantic validation, retrieval completeness, forecasting superiority, or fresh holdout status. The original RNN was created with a different Python/NumPy/Pandas combination; this check establishes saved-probability reproduction in the locked environment, not byte-identical neural retraining across interpreters. The preparation scripts are exercised on actual historical data and synthetic future-year fixtures only. See the [data handoff](PROQUEST_DATA_HANDOFF.md) for later execution.
