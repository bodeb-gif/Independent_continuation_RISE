# Modern ProQuest export handoff

Export submitted successfully through ProQuest's documented results channel on October 20, 2026 (America/Chicago). The package was downloaded and imported unchanged into `data/proquest/modern/20261020/`. Receipt did not score claims; the subsequently authorized exploratory analysis is in [`../modern_analysis_v1/report.html`](../modern_analysis_v1/report.html).

- Dataset: `moderndayreal`; dashboard range January 1, 2011–September 1, 2026.
- Articles: 46,248; all extracted at schema version 2.
- Candidates: 174,684 = 91,118 retained + 83,566 rejected.
- Retained verification exceptions: 19 kept by default; preserved and individually flagged in the package manifest.
- VM reconciliation: exact multiset equality of original candidate records and retained plus rejected records, excluding only the added verification reason; no deduplication.
- Exported package: `modern_2011_2026_verified_20261020.tar.xz`, 1,931,788 bytes.
- Contents: 16 annual stripped verified JSONL files plus `manifest.json`, including file/source/code hashes, stage counts, dataset provenance, and exception addresses. Original row order is preserved. Quotes and article text are omitted.
- VM location: `/home/ec2-user/SageMaker/election_arm/modern_2011_2026_verified_20261020.tar.xz`.
- Official destination: `s3://pq-tdm-studio-results/tdm-ale-data/a5379/results/modern_2011_2026_verified_20261020.tar.xz`; CLI reported upload success.
- Delivery: ProQuest sends the download link to `bodeb@bu.edu`; its manual states the link expires after two hours.

The current VM manual states a 3 MB weekly allowance, differing from older repository notes describing 15 MB. The verified package fits below 3 MB. The combined raw-candidate and verified package is 4,153,916 bytes and remains staged in the VM, not submitted. `raw` in that staged package means extracted labels, never article text.

Receipt is complete: all 16 annual file hashes, byte counts, record counts, claim-date ranges and the 19 exception addresses match the supplied manifest. Do not pool it into the active 1900–2010 analysis or treat late-2026 forecast outcomes as mature. Prior exposure to modern outcome results remains undocumented.

Correction to the initial status message: retained claims total **91,118**, not 89,418; exact candidate total is **174,684**.

## Local receipt, October 20, 2026

`receipt.json` records the reproducible transport/inventory audit. Downloads named
the compressed archive `.tar`; its bytes are XZ-compressed and are preserved as
`source_archive.tar.xz` (SHA256
`1c09f2a7ae9c9bee34e16398fc476f23c1971df6f63f0f3f2d3461992c802a37`).
The unpacked Downloads files also match all 16 manifest hashes.

- 124,189 export rows: 91,118 claims and 33,071 empty records.
- 44,120 represented articles, versus 46,248 stage articles: 2,128 stage articles
  have no export row. Rejected-only articles are a possible explanation, but
  require VM article-level reconciliation; the receipt does not assume it.
- The 2011 shard has 21,560 empty rows for 980 distinct articles, including
  20,580 identical empty rows beyond the first. All are preserved. Never use
  these rows as an article denominator or silently deduplicate claim labels.
- All 19 default-kept verification exceptions remain individually addressable.
- Transport integrity passes; the frozen evaluation-readiness gate is not met.
  The supplied manifest uses a different export schema and lacks full stage-flow,
  model/decoding/log metadata and a dated prior-outcome-exposure statement.
  Its prompt-block hashes are preserved without claiming they identify the
  full prompts required by the frozen protocol.

The 30 frozen model/protocol artifacts were checked and remain unchanged.
The historical source corpus remains unchanged. Reference coverage and outcome
maturity were subsequently evaluated in `../modern_analysis_v1/`; that separate
analysis does not certify the original full readiness gate.

Reproduce receipt into a new directory (the receiver refuses overwrites):

```bash
python src/proquest_export_receipt.py \
  --archive data/proquest/modern/20261020/source_archive.tar.xz \
  --destination /tmp/proquest-modern-receipt \
  --report /tmp/proquest-modern-receipt-report.json
```
