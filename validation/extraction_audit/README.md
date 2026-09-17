# Extraction audit plan

This audit separates the evidence about false positives from the evidence about
missed claims. It must not report an AI-agreement rate as human recall.

## Samples

- **Recall-agreement sample:** 150 pages, stratified by decade. Run both
  `gpt-4o-mini` and Gemini Flash independently on exactly these pages. Each run
  uses the production ProQuest extraction prompt and its double-pass check.
- **Human precision sample:** 500--700 claims sampled from the production
  `gpt-4o-mini` output, also stratified by decade. A human marks each emitted
  claim `y` (a real forward-looking, scorable forecast) or `n` (not one).

The human precision sample is blinded to model verdicts. It is separate from
the page sample and does not require reading whole pages.

## Run order

```bash
# 1. Freeze the 150-page recall-agreement sample.
python validation/extraction_audit/audit.py pages \
  --pages <downloaded-pages.jsonl> --n 150 --out validation/extraction_audit/loc_2026

# 2. Create the 700-claim human precision sheet.
python validation/extraction_audit/audit.py claims \
  --claims <gpt4o-mini-output.jsonl> --n 700 --out validation/extraction_audit/loc_2026

# 3. Extract only manifest.json's pages independently with both models, then
#    measure claim-level agreement with one-to-one fuzzy quote matching.
python validation/extraction_audit/audit.py agreement \
  --claims <gpt4o-mini-output.jsonl> \
  --reference-claims <gemini-flash-output.jsonl> \
  --out validation/extraction_audit/loc_2026

# 4. After the human fills claims.csv's verdict column, score the precision audit.
python validation/extraction_audit/audit.py score \
  --claims <gpt4o-mini-output.jsonl> --out validation/extraction_audit/loc_2026
```

`agreement` reports both directions: the share of Gemini Flash claims also found
by gpt-4o-mini, and the share of gpt-4o-mini claims also found by Gemini Flash.
It reports Wilson intervals and decade breakdowns, but it is model agreement,
not a recall estimate against ground truth. Do not combine it with human
precision to calculate or publish F1.

`score` writes the human precision result into the same `result.json` without
overwriting the agreement result. Keep the output directory immutable after the
sample is frozen; make a new dated directory for a new draw.
