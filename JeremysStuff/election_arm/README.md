# ProQuest economy extraction tools

Run source-text operations inside the authorized TDM Studio VM. See the
[workflow guide](PROQUEST_TDM_GUIDE.md). The current paper and economic scoring
are on `main`; this branch preserves extraction code and source exports.

| Files | Role |
| --- | --- |
| `tdm_parse.py` | Parse authorized article XML into annual JSONL shards |
| `extract_gpt.py`, `verify_gpt.py` | Candidate extraction and inclusion filtering |
| `run_corpus_economy.sh` | Resume annual extraction, then verification |
| `corpus_progress.py`, `extraction_status.py` | Progress and completion diagnostics |
| `strip_for_export.py` | Remove text-bearing fields and check export records |
| `qa_extraction.py`, `sample_claims.py`, `era_audit.py`, `validate_kappa.py` | Source QA and review utilities |
| `vm_doctor.py`, `pyrun.sh`, `migrate_v2.py` | VM interpreter and schema maintenance |
| `test_offline.py` | Retained offline pipeline and compatibility checks |

`analyze_economy.py`, `livingston_benchmark.py`, `model.py`, and their reference
files are legacy compatibility tools. Their NBER-state scoring and text-feature
model are not the deterministic directional scoring used in the current paper.
Use `docs/PROQUEST_ANALYSIS.md` on `main` for that analysis.

The failed election/NYT path and its title-only inputs have been removed. All
ProQuest exports and human-review records remain intact. Old keyword-window
exports are provenance only, not additional annual observations.

Run checks from any directory with a working Python environment:

```sh
python JeremysStuff/election_arm/test_offline.py
```

The suite uses synthetic fixtures and no model API calls. Install the supplied
requirements into a working environment; do not use the broken root `.venv`.
