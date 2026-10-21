"""Receive the TDM export package without activating modern model evaluation.

This transport/inventory check is deliberately separate from the frozen, stricter
proquest_modern_intake.py gate. Source bytes and duplicate rows are preserved.
"""
import argparse
from collections import Counter
from datetime import date
import hashlib
import json
from pathlib import Path
import tarfile


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(ok, message):
    if not ok:
        raise ValueError(message)


def inspect_archive(archive):
    """Validate every member before writing anything; never call extractall."""
    with tarfile.open(archive, 'r:*') as tar:
        members = tar.getmembers()
        require(all(m.isfile() for m in members), 'Only regular files are allowed')
        require(len({m.name for m in members}) == len(members), 'Duplicate archive member')
        require('manifest.json' in {m.name for m in members}, 'Missing manifest')
        manifest_bytes = tar.extractfile('manifest.json').read()
        manifest = json.loads(manifest_bytes)
        require(manifest.get('schema') == 'proquest-modern-export-v1', 'Unsupported manifest')
        require(manifest.get('source') == 'proquest', 'Unexpected source')
        require(manifest.get('package_sets') == ['verified'], 'Expected verified-only package')
        years = manifest['years']
        require(years and all(type(y) is int and y >= 2011 for y in years), 'Modern years required')
        require(len(set(years)) == len(years), 'Duplicate year')
        entries = manifest['files']
        require(Counter(e['year'] for e in entries) == Counter(years), 'Annual coverage mismatch')
        expected = {'manifest.json'}
        for e in entries:
            require(e['set'] == 'verified', 'Unexpected export set')
            require(e['path'] == f"verified/pred_proquest_economy_{e['year']}.export.jsonl", 'Unsafe or unexpected path')
            expected.add(e['path'])
        require({m.name for m in members} == expected, 'Unmanifested/missing archive member')
        payloads = {'manifest.json': manifest_bytes}
        summaries, actual_exceptions, totals = [], [], Counter()
        for e in entries:
            data = tar.extractfile(e['path']).read()
            require(len(data) == e['bytes'] and sha(data) == e['sha256'], 'File bytes/hash mismatch')
            pages, claim_pages, empty_pages = set(), set(), set()
            counts, empty_serializations, dates = Counter(), Counter(), []
            for line_number, line in enumerate(data.decode('utf-8').splitlines(), 1):
                if not line.strip():
                    continue
                row = json.loads(line)
                require(not {'quote', 'claim_text', 'article', 'text', 'full_text'} & row.keys(), 'Source text in export')
                require(row.get('schema_version') == 2 and row.get('page_id'), 'Invalid schema/article')
                page = str(row['page_id']); pages.add(page); counts['records'] += 1
                require(row.get('source', 'proquest') == 'proquest', 'Unexpected row source')
                if row.get('date'):
                    require(date.fromisoformat(row['date']).year == e['year'], 'Date outside shard')
                if row.get('no_predictions') is True:
                    counts['empty_records'] += 1; empty_pages.add(page)
                    empty_serializations[json.dumps(row, sort_keys=True)] += 1
                else:
                    require(row.get('source') == 'proquest' and row.get('date') and row.get('verify_reason'), 'Incomplete claim provenance')
                    counts['claims'] += 1; claim_pages.add(page); dates.append(row['date'])
                    if row['verify_reason'] == 'unjudged (kept by default)':
                        actual_exceptions.append(dict(audit_id=f"verified:{e['year']}:{line_number}",
                            year=e['year'], source_line=line_number, page_id=page, reason=row['verify_reason']))
            require(counts['records'] == e['records'] and counts['claims'] == e['claims'], 'Record/claim count mismatch')
            require(dates and min(dates) == e['min_date'] and max(dates) == e['max_date'], 'Date range mismatch')
            stage = e['stage_counts']
            require(all(type(v) is int and v >= 0 for v in stage.values()), 'Invalid stage count')
            require(stage['retained'] == counts['claims'], 'Retained count mismatch')
            require(stage['candidates'] == stage['retained'] + stage['rejected'], 'Candidate reconciliation mismatch')
            require(stage['verification_default_kept'] == sum(x['year'] == e['year'] for x in actual_exceptions), 'Exception count mismatch')
            require(len(pages) <= stage['articles'], 'Exports exceed stage articles')
            totals.update(stage)
            summaries.append(dict(year=e['year'], path=e['path'], sha256=e['sha256'], **counts,
                represented_articles=len(pages), articles_with_claims=len(claim_pages),
                articles_with_empty_rows=len(empty_pages), articles_with_both=len(empty_pages & claim_pages),
                identical_empty_rows_beyond_first=sum(n-1 for n in empty_serializations.values()),
                stage_articles_without_export_rows=stage['articles']-len(pages)))
            payloads[e['path']] = data
        require(dict(totals) == manifest['totals'], 'Manifest total mismatch')
        key = lambda x: x['audit_id']
        require(sorted(actual_exceptions, key=key) == sorted(manifest['exceptions'], key=key), 'Exception address mismatch')
    report = dict(schema='proquest-export-receipt-v1', transport_integrity='passed',
        archive_sha256=sha(Path(archive).read_bytes()), archive_bytes=Path(archive).stat().st_size,
        manifest_sha256=sha(manifest_bytes), years=years, totals=dict(totals), files=summaries,
        row_order_and_duplicates_preserved=True, model_evaluation_ready=False, scoring='not_performed',
        fresh_holdout_claim=False, prior_outcome_exposure=manifest.get('prior_outcome_exposure'),
        readiness_notes=[
            'This export-format receipt does not satisfy or replace the frozen modern-intake manifest gate.',
            'Complete stage-flow counts, retrieval limits, model identifiers, decoding/chunking settings, and processing-log provenance still need reconciliation.',
            'Prompt-block hashes are retained as supplied; they are not substituted for the required identified extraction/verification prompt hashes.',
            'Prior outcome exposure requires a dated statement before evaluation.',
            'Default-kept exceptions require resolution or a documented exclusion amendment.',
            'Explain repeated empty rows and articles absent from export using VM processing provenance; do not infer successful processing from empty rows.',
            'Activate separate modern scope and verify outcome maturity, references, and print-time features before scoring.'])
    return payloads, report


def receive(archive, destination):
    payloads, report = inspect_archive(archive)
    destination = Path(destination)
    require(not destination.exists(), 'Destination already exists; refuse to overwrite receipt')
    destination.mkdir(parents=True)
    for name, data in payloads.items():
        path = destination / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    # Preserve original compressed bytes; Downloads may have renamed .tar.xz to .tar.
    (destination / 'source_archive.tar.xz').write_bytes(Path(archive).read_bytes())
    report['destination'] = str(destination)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--destination', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    require(not args.report.exists(), 'Report already exists')
    result = receive(args.archive, args.destination)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ('transport_integrity', 'totals', 'model_evaluation_ready')}, indent=2))
