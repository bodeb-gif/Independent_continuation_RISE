# LOC extraction validation review

This folder is for **LOC source validation only**. LOC claim labels must not be
pooled into the annual ProQuest outcome analysis. The review page borrows the
workflow of the supplied `human_anchor_H2.html`: source text beside a focused
item, a progress bar, autosave, keyboard choices, and JSONL export. It does
not reuse that document's medical tasks or data.

## Use the prepared claim review

Open [`loc_claim_review.html`](loc_claim_review.html) in a browser. It contains
120 LOC claim candidates on 62 locally available pages, sampled with seed
20260924 from 239 candidates linked to those pages. One quote has no reliable
OCR locator; the others have exact or visibly marked partial text anchors.
The review saves in browser storage. Export JSONL regularly as a backup; an
export from the same build can be imported later. Each row contains the source
unit ID, your judgments, timestamp, and whether the file is partial. The
machine labels live separately in
[`loc_claim_review.manifest.jsonl`](loc_claim_review.manifest.jsonl) and are
deliberately absent from the HTML so you can judge the source first.

The locally available OCR is a **partial** collection: 103 pages in the
neighboring checkout's `pages_monthly.shard1of153.jsonl`, plus 16 historical
gold pages in this repo. There is no complete monthly page corpus here. The
prepared sample is useful for review practice and error discovery; it cannot
estimate claim validity across the complete LOC collection without a full
page set and a new probability sample.

To rebuild or create a new sample with the available OCR:

```bash
python3 src/loc_validation.py claim-review \
  --pages /Users/bodebosell/Documents/GitHub/datascience-rise-practicum/data/monthly/pages_monthly.shard1of153.jsonl \
  --pages validation/gold_extraction/gold_pages.jsonl \
  --n 120 --seed 20260924 \
  --out validation/loc_review/loc_claim_review.html
```

When a complete LOC page corpus is available locally, pass its JSONL file(s)
instead. `--n 0` selects every linked claim; otherwise claims are sampled
uniformly from the subset with available pages. The manifest records the
selection probability **within that subset**, source line numbers, and machine
labels. If the input pages are partial, that probability is not a full-corpus
inclusion probability. The builder fails on conflicting OCR for one page ID.

## Recall packet for another model

The prepared [`recall_pilot_pages.jsonl`](recall_pilot_pages.jsonl) contains
24 uniformly sampled pages from the 103-page partial shard, with full OCR and
**no extracted claim suggestions**. Its
[`manifest`](recall_pilot_pages.manifest.json) records the seed, input hash,
page IDs, and sampling fraction. It is a pilot for testing the instructions,
cost, and matching code. It is **not** a full-corpus recall estimate.

To sample from the complete LOC OCR corpus once it is present:

```bash
python3 src/loc_validation.py sample-recall \
  --pages data/corpus/monthly/pages_monthly.jsonl \
  --n 100 --seed 20260924 \
  --population-label 'complete LOC monthly OCR corpus' \
  --out validation/loc_review/generated/recall_pages.jsonl
```

If the corpus is split into shards, repeat `--pages` for each shard. Verify
that the manifest's `available_pages` agrees with the expected source corpus
before describing the sample as representative. Preserve the source files and
their hashes. Sampling is uniform over the pages supplied, including pages
with no extracted claims. Do not select only pages where the extractor found
something: those pages cannot identify misses on empty-output pages.

Give the other model **only** the page packet and this instruction:

> Read each complete OCR newspaper page independently. Enumerate **every**
> falsifiable forecast of future economic conditions on that page, including
> forecasts in quotations and forecast-bearing headlines. Exclude present or
> past descriptions, advertisements, conditional scenarios without a committed
> prediction, non-economic futures, and text too damaged to interpret. Copy
> each forecast's shortest sufficient quote verbatim from the OCR; do not
> paraphrase, repair OCR, use outside historical knowledge, or inspect any
> existing extracted-claim file. Return exactly one JSON object per input
> page, even if no forecasts were found: `{"page_id":"...","claims":[]}`.
> For each forecast, put an object with at least `quote`, and optionally
> `topic`, `direction`, `scope`, `horizon_months`, and `note`, in `claims`.
> If two clauses make genuinely separate forecasts, give them separate
> records. Do not duplicate the same forecast because it appears in both a
> headline and the article body.

The fuller inclusion and span rubric is in
[`../gold_extraction/PROTOCOL.md`](../gold_extraction/PROTOCOL.md). The output
must cover *every* packet page exactly once, including pages labeled with
`claims: []`. This enables missed claims to be counted.

After the model writes `recall_reference.jsonl`, compare it with the LOC
extracted claims:

```bash
python3 src/loc_validation.py score-recall \
  --packet validation/loc_review/generated/recall_pages.jsonl \
  --reference validation/loc_review/generated/recall_reference.jsonl \
  --reference-kind model \
  --out validation/loc_review/generated/recall_comparison.json
```

The comparison uses a one-to-one OCR token-containment match at 0.7. Review
model-only and extractor-only cases manually, especially overlapping spans,
short quotes, and duplicated claims. A model reference measures **coverage
relative to that model**, not absolute recall. To estimate human-adjudicated
recall, a reviewer must enumerate all forecasts on a probability sample of
pages while blind to extractor output, resolve disagreements, retain zero-claim
pages, and rerun the scorer with `--reference-kind human_adjudicated`. Report
the page sampling frame, number of pages, reference claim denominator,
matched and missed counts, and uncertainty clustered by page. Keep this
validation separate from ProQuest outcome scoring.
