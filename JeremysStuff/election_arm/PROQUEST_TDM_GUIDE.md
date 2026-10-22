# ProQuest TDM workflow

This branch is the extraction and export handoff. The current manuscript,
reviewed labels, and economic scoring are on `main`. Existing VM paths retain
the historical folder name `election_arm`. This guide replaces the obsolete
multi-arm and corpus-pooling instructions; the old guide is in Git at `774b68f`.

## Environment and access

Article XML, source text, quotations, and unrestricted model responses stay in
the authorized TDM Studio VM. Keep credentials out of Git and exports. Use the
workbench-provided proxy configuration with `extract_gpt.py` and `verify_gpt.py`.
The local requirements list import dependencies; VM setup must use the packages
and network access permitted by that workbench.

`vm_doctor.py` diagnoses interpreter and package availability. `pyrun.sh` selects
a working VM Python interpreter. The repository-root `.venv` is broken.

## Parse and inspect an authorized corpus

Run inside the VM from `/home/ec2-user/SageMaker/election_arm`:

```sh
bash pyrun.sh tdm_parse.py --arm economy --corpus --dataset-dir /path/to/authorized/dataset --inspect
bash pyrun.sh tdm_parse.py --arm economy --corpus --dataset-dir /path/to/authorized/dataset
bash pyrun.sh corpus_progress.py --by-year
```

The parser writes annual `data/raw/proquest_economy_YYYY.jsonl` shards and
preserves article identifiers. Resume logic skips already-parsed identifiers.
Inspect missing dates and source coverage rather than treating every parsed row
as a valid candidate. Old keyword windows are not another annual sample.

## Extraction and verification

For a separately authorized run, first check `pgrep -af extract_gpt` and
`pgrep -af verify_gpt`; do not launch competing processes. The existing
`run_corpus_economy.sh` resumes extraction oldest-first, then begins verification
only after the extraction-completion gate clears:

```sh
bash run_corpus_economy.sh
```

Monitor with `bash pyrun.sh corpus_progress.py --by-year`. It counts source
articles separately from emitted claims; line counts are not article counts.
A daily quota stop is not a reason to start duplicate jobs. Verification writes
into `data/verified/`, separate from unfiltered `data/predictions/`. Keep drop
records and failure information for provenance inside the VM.

The extractor's schema-version checks prevent incompatible resumed outputs.
Do not disable them or mix schema versions. `migrate_v2.py` is retained for
explicit, separately reviewed migrations. Print-time information restrictions
apply even if retrospective window labels remain in provenance metadata.

## Export and handoff

Inspect the schema and run the existing text-removal and prose checks on each
intended export. For example, inside the VM:

```sh
bash pyrun.sh strip_for_export.py data/verified/pred_proquest_economy_1930.jsonl
```

Export only the permitted resulting `.export.jsonl` through the workbench's
approved export flow. A successful script run does not replace review of the
export policy or newly added fields. Never export article text, quotations, or
free-text source notes. Do not overwrite the frozen files already committed
here; put a new authorized run in a dated package with hashes and a receipt.

The 111 committed annual candidate exports in `data/predictions/` and the 111
annual verified exports in `data/verified/` cover 1900–2010. Files with named
window suffixes are legacy provenance. On `main`, the annual copies are under
`data/proquest/raw/` and `data/proquest/verified/`. Their source rows and bytes
must remain traceable. Do not deduplicate using stripped labels alone.

For current economic scoring and review reproduction, use
`docs/PROQUEST_ANALYSIS.md` and `docs/PROQUEST_REPRODUCIBILITY.md` on `main`.
The retained local NBER-state scorer and text-feature model are legacy tools;
their outputs are not interchangeable with the current paper's results.

## Offline maintenance check

```sh
python JeremysStuff/election_arm/test_offline.py
```

The suite runs without API calls and checks the retained extraction, parsing,
export, progress-gate, and legacy scoring behavior. A repository cleanup does
not itself authorize restarting a model run or modifying VM data.
