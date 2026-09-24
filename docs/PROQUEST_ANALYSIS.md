# ProQuest-only analysis

The active analysis corpus is the annual ProQuest economy export, 1900–2010.
Use `data/proquest/verified/` as the primary machine-filtered set and
`data/proquest/raw/` for extraction/filter sensitivity checks. Both contain
111 annual shards, copied unchanged from `proquest-tdm-integration` at `774b68f`.
Older crisis-window exports are excluded.

LOC pages and claims are for extraction validation only. Existing LOC results
and models on main describe a previous corpus; they are not ProQuest results.
Do not use LOC claims, scores, page denominators, or fitted artifacts in this analysis.

From the repository root, start with:

```bash
python3 src/analyze_proquest.py
# Optional: assemble the verified claims for a later scoring run.
python3 src/analyze_proquest.py --export-claims
```

Reports go into `data/scored/proquest/`. The assembled JSONL omits empty
records, retrospective window annotations, and verifier prose. All original
exports remain unchanged. Identical exported labels are counted but retained:
the exports omit quotes and lack a unique claim identifier, so labels alone
cannot prove that two forecasts are duplicates.

## First descriptive outcome analysis

The descriptive entry point scores only the annual machine-verified set:

```bash
pip install -r requirements-proquest.txt
python src/proquest_descriptive.py
python tests/test_proquest_descriptive.py
```

The first run scored 175,855 of 274,070 verified claims. The pooled hit rate
is 40.8%, versus 53.6% for a fixed-direction baseline on the same topic/horizon
mix. No ML models were fitted to the corpus. Read
`data/scored/proquest/descriptive/report.html` for charts, exclusions,
publisher comparisons, horizon subsets, and scoring sensitivity. The report's
methods section documents the actual rules; the old LOC results are not reused.

References are frozen in `data/reference/proquest/`: existing local FRED
snapshots for production, CPI, unemployment, and USREC, plus the public Shiller
S&P Composite workbook downloaded 2026-09-16 from `https://shillerdata.com/`.
Reference hashes and coverage are recorded in the result's `summary.json`.
Shiller is used consistently for market claims across the entire period; it
is a provisional broad-market proxy, not an exact match to every asset forecast.

The script excludes nonnational/unsupported-topic claims, accepts positive
integer numeric horizons of 1–24 months, rejects invalid/longer horizons, and
reports default versus claim-grounded horizons separately. It retains every
eligible label row and reports equal-article weighting as a sensitivity check.
Publisher rankings merge historical editions and include only papers with at
least 500 scored claims. They are descriptive; topic/era mix still matters.
The fixed baseline predicts production/stocks/prices rise and unemployment
falls. It is not a learned model or a claim that rising prices are good news.

Future refinements can resolve excluded labels and improve semantic matching
between claims and benchmark series using the in-VM source quotes.

## Descriptive follow-ups

```bash
python src/proquest_followups.py
python tests/test_proquest_followups.py
```

The standalone `data/scored/proquest/followups/report.html` covers false alarms
and missed industrial-production declines, warning timing around recession
starts, consensus versus contrarians, stated horizons, publisher specialties,
coverage-adjusted comparisons and decade stability, and forecast voice.
Speaker-attribution coverage is exported alphabetically for later identity and
source-quote review. Individual forecasters are not assigned accuracy rankings.

The script validates saved outcome rows one-to-one against all annual verified
exports and verifies frozen reference hashes. Historical consensus uses only
outcome-eligible forecasts from other papers in the preceding 90 days,
excluding the current date. It requires 20 earlier claims from two other
papers and matches topic, benchmark, horizon basis, and horizon bucket.
No realized outcome is used to form consensus. Its accuracy comparison matches
the same paper, publication month, topic, benchmark, horizon basis, and exact
horizon, requiring five claims in each group. Exact matches share the same
benchmark outcome and fixed-direction baseline.

Publisher and voice comparisons use shared year/topic/benchmark/horizon-basis/
horizon-bucket cells, requiring ten claims from each group. Six-versus-twelve-
month comparisons use explicitly stated horizons in shared paper/year/topic/
benchmark cells. Harmonic-overlap weights give both groups the same cell mix.
Five-year block resampling describes historical variability; claims are not
independent observations, and intervals are not corrected for multiple tests.
Publisher pairwise averages use different shared coverage for each opponent,
so the resulting order is descriptive, not a universal common-period ranking.

Warning timing uses the continuous frozen USREC chronology, rather than any
old crisis-window claims. Each directional national business forecast is
assigned to at most one nearby recession onset. The phase comparison includes
the same 16 events with at least 30 forecasts in each phase, equally weighted,
with pre-onset expansion months and post-onset recession months. This measures
worsening expectations, not necessarily explicit recession predictions.
The disagreement/onset diagnostic is also retrospective and descriptive.

Coverage correction: Wall Street Journal verified claims begin in 1984;
Chicago Tribune scored coverage ends in 2001. The first report's earlier
1960 start-year statement for the Journal has been corrected in its generator
and generated files.

Do not infer sampling attention from claims alone; obtain ProQuest article
denominators from the VM. Train/evaluate models by time blocks, never random
claims, and use only information available at the forecast date as features.

Machine-verified labels still need extraction validation. Gold/LOC agreement
is validation evidence, not another analysis corpus or human recall estimate.

## VM daily-quota waiting

Copy `scripts/proquest_enable_quota_wait.py` into the VM's `election_arm`
folder, then apply it there:

```bash
"$PY" proquest_enable_quota_wait.py
```

It backs up and syntax-checks the existing `run_corpus_economy.sh`, then makes
both extraction and verification wait on exit code 2 (daily quota exhausted).
The runner waits 3,600 seconds and retries the same stage/year from saved
progress, repeating until a retry succeeds. It does not assume a reset timezone
or bypass the quota. Other errors retain the runner's existing handling.
`QUOTA_RETRY_SECONDS` can change the interval (integer seconds, minimum 60).

For the modern extension, launch the patched runner from `election_arm`:

```bash
PYTHONUNBUFFERED=1 nohup bash run_corpus_economy.sh \
  2011 2012 2013 2014 2015 2016 2017 2018 \
  2019 2020 2021 2022 2023 2024 2025 2026 \
  > moderndayreal.log 2>&1 &
```

The patch affects subsequent launches, not an already-running job. Run one
pipeline at a time. A terminal disconnect is supported by `nohup`, but stopping
the VM still stops the process. This installer has been prepared locally; it
does not connect to or modify the remote VM. Modern claims must still finish
verification and be exported/imported before they become analysis inputs.

## 2008 crisis and 2009 reversal

```bash
python src/proquest_2008.py
```

The standalone `data/scored/proquest/crisis_2008/report.html` audits publication
cohorts around the financial crisis, with three charts, direction confusion
tables, quarterly timing, exact-horizon composition matching, sensitivity
checks and frozen-reference endpoint examples. Only annual verified claims
enter this descriptive analysis; it fits no model.

Pooled correctness rises from 41.8% in 2007 (2,330 scored claims) to 64.3% in
2008 (9,065), then falls to 36.6% in 2009 (8,555). Business and employment drive
the 2008 rise; price correctness falls to 15.1%. Business worsening calls are
97.9% correct in 2008 but 2.4% correct in 2009. These are horizon-direction
hits, not evidence of predicting the recession's onset. The 2008 peak persists
with equal article weights, grounded horizons, common publishers and tested
alternative thresholds/default horizons.

The query selects downturn/recovery language, quotes have been stripped, and
claims share articles and monthly outcomes. Revised endpoint references,
publication-year/outcome-year differences and broad topic proxies limit
interpretation. Aggregate shifts do not establish that particular forecasters
changed or maintained their views. Reported topic contributions are arithmetic
identities, not causal effects or estimates of individual skill.

## First RNN experiment

```bash
pip install -r requirements-proquest-rnn.txt
python src/proquest_rnn.py
python tests/test_proquest_rnn.py
```

`data/scored/proquest/rnn/report.html` presents a small GRU predicting whether
an individual forecast matches the documented deterministic outcome rule.
It uses claim metadata and the preceding 12 complete months of machine-verified
national forecast patterns. The original quotes are absent, so this is a
temporal metadata model, not a text model. No LOC claims, crisis-window exports,
verifier prose, speaker identities, macro values or realized outcome features
enter the model. Readable verified claims with unscorable outcomes can still
contribute print-time context. Pre-1919 NBER-proxy scores are excluded as targets.

Training publications precede 1985, validation spans 1985–1994, and testing
spans 1995–2010. Outcomes must reach their horizon endpoint plus a conservative
three-month release allowance before the next split; 7,743 unresolved labels
are purged. This yields 70,722 training, 39,536 validation and 56,807 test claims.
The release allowance prevents obvious overlap but does not establish true
historical vintage availability: the benchmark series are revised snapshots.
Categories and scaling are learned only from the training period. Neural epoch
selection uses validation log loss; three preset seeds form an ensemble.

Each article receives equal total training weight. Primary evaluation also
weights articles equally, with claim-weighted results exported separately.
Baselines are constant training prevalence, logistic metadata, and logistic
metadata plus flattened historical inputs. The ensemble's test average
precision is 0.6833 versus 0.5958 for history logistic and 0.5788 for metadata
logistic; its Brier score is 0.1929 versus 0.2364 and 0.2183, respectively.
The five-year-block average-precision gap interval versus history logistic is
[-0.1912, +0.2102], so a stable improvement is not established. This comparison
also cannot separate the effect of recurrence from neural nonlinearity.

The folder contains three `.pt` state-dict checkpoints, train-only preprocessing
and logistic baselines, split assignments, test predictions, subgroup metrics,
training histories and a hash/version manifest. Models are exploratory research
artifacts; future tuning should use forward-time development folds rather than
repeatedly choosing configurations against this already observed test period.
