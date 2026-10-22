# Human-label rescoring and design-based accuracy correction

Run 2026-10-21 at the author's request with `src/proquest_human_rescore.py`
(locked Python 3.12.13 environment). Exploratory. No source text, no model
fitting, and no change to source exports or frozen artifacts. The
[specification](specification.json) was fixed in code after field-level
disagreement counts had been inspected, but before any human-label correctness
was computed. This README interprets results and was written afterwards.

## What was done

The 300 reviewed claims were rescored with the author's categorical labels,
using the unchanged deterministic outcome rules. Each frame was then estimated
three ways: the machine census, the human sample alone (inverse-probability
Hajek ratio) and the design-based supervised learning (DSL) correction. DSL
takes the machine frame total and adds the weighted mean of (human − machine)
on reviewed claims.

The two frames are estimated separately and never pooled:

- **Historical:** 175,843 scored 1900–2010 claims. The 250 reviewed claims are
  one simple random sample from that frame.
- **Modern:** 91,118 retained 2011–2026 candidates, stratified by year (50
  reviewed claims).

Checks: both frames reproduce their sampling manifests (historical address
hash; modern per-year counts). All 175,843 historical and 91,099 modern saved
machine scores were reproduced exactly (0 mismatches). Every reviewed claim's
saved machine labels match its export row.

## Historical results (primary variant)

| Estimand | Machine census | Human sample only [95%] | DSL [95%] |
| --- | ---: | ---: | ---: |
| Share of scored claims that are genuine, scorable national forecasts | 100% | 44.0% [37.8, 50.2] | 44.0% [37.8, 50.2] |
| Accuracy among them | 40.8% | 39.1% [30.0, 48.2] | 41.8% [29.6, 54.1] |
| Always-improve baseline on the same claims | 53.6% | 50.0% [40.6, 59.4] | 43.7% [32.0, 55.4] |
| Accuracy minus baseline (pp) | −12.8 | −10.9 [−20.8, −1.0] | −1.8 [−16.6, 12.9] |

Of the 250 reviewed claims, 110 survive as genuine, scorable national
forecasts; 43 of those are correct. The other 140 fail for these reasons:

| Reason | Claims |
| --- | ---: |
| Not a forecast | 72 |
| Industry scope | 40 |
| Foreign scope | 21 |
| Regional scope | 2 |
| No scorable direction | 3 |
| Topic "other" | 1 |
| Unclear | 1 |

Among the 110, switching to human labels flips correctness for 13 claims
(5 correct → incorrect, 8 incorrect → correct).

DSL is less precise than the human sample alone here. Most of the disagreement
concerns whether a claim counts at all, not whether it was right, so a claim's
machine score transfers poorly to its human score. The sample's machine "luck"
(its gap is −16.8 pp versus −12.8 in the census) is then corrected roughly
1/0.44 times over. A power-tuned estimator (PPI++) would be at least as precise
as the human sample alone. It was not part of this specification.

Sensitivities are in `estimates.csv`:

- **Human horizon codes only:** accuracy 41.8% (human sample).
- **Strict horizons** (vague not scorable): only 19.2% [14.3, 24.1] of scored
  claims qualify.
- **Article weighting:** a 34.9% share and 40.3% accuracy.
- **Reviewed with machine labels concealed (150 claims):** 34.3% accuracy,
  versus 19/40 (47.5%) among the 100 reviewed with labels visible. That
  difference is consistent with anchoring but not statistically established.

## Modern results

The human sample alone gives a 32.1% [17.8, 46.4] share of scorable national
forecasts, versus 62.4% scored by the machine. Accuracy is 53.7% [28.5, 79.0]
(16 scorable claims).

DSL is uninformative at n = 50: point estimates fall outside 0–1. The sample's
machine accuracy (51.6%) far exceeds its frame's (29.0%), and the uncorrected
DSL subtracts the whole difference. Do not report modern DSL values as
estimates.

## Limitations

- Human labels are treated as truth. There was one reviewer, without an
  established second-coder agreement study.
- The historical frame contains only machine-scored claims. Forecasts the
  machine rejected, mislabeled as unscorable or never extracted cannot enter.
  Recall is unknown.
- Intervals cover sampling of reviewed claims from a fixed frame. They omit
  reviewer error, business-cycle dependence and outcome-definition uncertainty.
- Reviewed subgroups (for example, 24 included employment claims) are too
  small for topic-specific correction.

## Files

- `specification.json`
- `estimates.csv`: all variants, estimators and estimands.
- `reviewed_rescored.csv`: categorical per-claim machine and human scores.
- `summary.json`: checks, diagnostics, primary table and input hashes.

Rerun into a new directory:
`python src/proquest_human_rescore.py --out <new path>`.
