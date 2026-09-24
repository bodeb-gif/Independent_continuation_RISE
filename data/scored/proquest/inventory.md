# ProQuest annual corpus inventory

Only annual ProQuest exports enter this report. LOC and old crisis-window files are excluded.

| Set | Annual files | Claims | Represented articles | National claims |
| --- | ---: | ---: | ---: | ---: |
| Raw | 111 | 488,660 | 156,435 | 344,326 |
| Machine-verified | 111 | 274,070 | 146,720 | 193,887 |

Both sets span 1900–2010 with no missing annual shards.

Raw article IDs absent from verified exports: 9,715. These counts cannot establish extraction or verification completeness without an in-VM article manifest.

## Verified claim counts by decade

| Decade | Claims |
| --- | ---: |
| 1900 | 1,573 |
| 1910 | 1,534 |
| 1920 | 4,985 |
| 1930 | 19,269 |
| 1940 | 6,904 |
| 1950 | 8,301 |
| 1960 | 8,252 |
| 1970 | 26,471 |
| 1980 | 55,383 |
| 1990 | 71,123 |
| 2000 | 61,757 |
| 2010 | 8,518 |

## Analysis readiness

- 696 verified rows share identical exported labels. They are retained: stripped quotes mean distinct forecasts can have identical labels.
- 142,810 verified claims have default horizons; report these separately from claim-grounded horizons.
- 21,249 verified horizons fall outside the current scorer's 6/12/24/vague vocabulary. Resolve these before scoring rather than silently defaulting them.
- Score only national, supported-topic forecasts against the appropriate economic series. The existing scope gate permits some unexpected labels; tighten it before a full run.
- The current stock index ends in 1968. Later market claims need a documented benchmark.
- Machine verification is a filter, not human validation. LOC is reserved for extraction validation.
- Attention requires a ProQuest article sampling denominator. Do not substitute LOC page counts.
- No hit rate or model result has been computed by this inventory.
