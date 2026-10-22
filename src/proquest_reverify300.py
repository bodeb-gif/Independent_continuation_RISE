"""One additional GPT-4o mini KEEP/DROP pass on the frozen 300-claim sample.

Run inside ProQuest TDM. Source text, prompts, and raw responses stay there.
Default mode only prepares and validates inputs. --run permits model calls.
Each audit ID gets at most one API attempt, including across interrupted runs.
The original verifier prompt is reused without human decisions or old verdicts.
"""
import argparse
from collections import Counter
import contextlib
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import time
from types import SimpleNamespace

METADATA_SHA = '4a2410c353b49cc37a7a91bf018f3e9896f50119a3fe778931a6d7b9ab565279'
RUN_NAME = 'gpt4omini_reverify300_20261022'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat()


def dump_new(path, obj):
    with Path(path).open('x', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write('\n')
        f.flush()
        os.fsync(f.fileno())


def strict_verdict(raw):
    raw = raw.strip()
    if raw.startswith('```'):
        raw = raw.split('\n', 1)[1].rsplit('```', 1)[0].strip()
    values = json.loads(raw)
    if not isinstance(values, list) or len(values) != 1:
        raise ValueError('Expected exactly one verdict')
    v = values[0]
    if type(v.get('id')) is not int or v['id'] != 0 or type(v.get('keep')) is not bool:
        raise ValueError('Invalid candidate ID or non-boolean keep')
    return v['keep']


def prepare(project):
    project = Path(project)
    metadata_bytes = (project/'reviewer2_300_v1/sample_metadata.json').read_bytes()
    assert sha(metadata_bytes) == METADATA_SHA, 'Changed 300-claim selection'
    metadata = json.loads(metadata_bytes)
    assert len(metadata) == len({r['audit_id'] for r in metadata}) == 300
    sources, source_hashes = {}, {}
    for batch in ['source_review_150_v1', 'source_review_additional150_v1']:
        p = project/batch/'sources.json'
        content = p.read_bytes()
        source_hashes[str(p.relative_to(project))] = sha(content)
        data = json.loads(content)
        assert isinstance(data, list) and len(data) == 150, 'Unexpected source store'
        for s in data:
            assert s['audit_id'] not in sources, 'Duplicate source audit ID'
            assert s.get('recovered') is True, 'Unrecovered source'
            assert all(isinstance(s.get(k), str) and s[k].strip() for k in ['quote','article'])
            sources[s['audit_id']] = s
    assert set(sources) == {r['audit_id'] for r in metadata}, 'Source/sample mismatch'
    sys.path.insert(0, str(project))
    import verify_gpt
    import extract_gpt
    assert Path(verify_gpt.__file__).resolve().parent == project.resolve()
    assert Path(extract_gpt.__file__).resolve().parent == project.resolve()
    output = project/RUN_NAME
    output.mkdir(exist_ok=True)
    (output/'requests').mkdir(exist_ok=True)
    (output/'responses').mkdir(exist_ok=True)
    (output/'attempts').mkdir(exist_ok=True)
    prompts = []
    for n, meta in enumerate(metadata, 1):
        source = sources[meta['audit_id']]
        # Only these source fields enter the model. Never send human labels,
        # comparison data, original verifier reasons, or realized outcomes.
        page = {'publisher':meta['publisher'], 'date':meta['date'], 'ocr_text':source['article']}
        prompt = verify_gpt.build_prompt(page, [{'quote':source['quote']}])
        request = {'n':n, 'audit_id':meta['audit_id'], 'prompt':prompt,
                   'prompt_sha256':sha(prompt.encode()), 'quote_sha256':sha(source['quote'].encode()),
                   'article_sha256':sha(source['article'].encode())}
        path = output/'requests'/f'{n:03}.json'
        if path.exists():
            assert json.loads(path.read_text()) == request, 'Changed prepared request'
        else:
            dump_new(path, request)
        prompts.append(request)
    spec = {'schema':'proquest-reverify300-spec-v1', 'run_name':RUN_NAME, 'n':300,
            'metadata_sha256':METADATA_SHA, 'model_requested':'gpt-4o-mini',
            'temperature':0, 'max_tokens':256, 'max_retries':0, 'calls_per_claim_max':1,
            'context':'Existing VM verify_gpt.build_prompt; one sampled claim per call',
            'human_labels_in_prompt':False, 'source_hashes':source_hashes,
            'script_sha256':sha(Path(__file__).read_bytes()),
            'verify_script_sha256':sha((project/'verify_gpt.py').read_bytes()),
            'extract_script_sha256':sha((project/'extract_gpt.py').read_bytes()),
            'verify_prompt_sha256':sha(verify_gpt.VERIFY_PROMPT.encode()),
            'ordered_prompt_sha256':sha(json.dumps([r['prompt_sha256'] for r in prompts]).encode()),
            'failure_policy':'No retry. Unsuccessful or interrupted attempts are unresolved; conservative filter keeps them.',
            'comparison':'Existing 300 accepted claims versus their retained subset after this additional pass; compare separately with each frozen human review and by period.'}
    path = output/'specification.json'
    if path.exists():
        assert json.loads(path.read_text()) == spec, 'Changed frozen run specification'
    else:
        dump_new(path, spec)
    print('PREPARED 300/300 source-linked requests; no human labels loaded.', flush=True)
    return metadata, prompts, spec, output, extract_gpt


def export_results(metadata, spec, output):
    records = []
    for n, meta in enumerate(metadata, 1):
        response_path = output/'responses'/f'{n:03}.json'
        attempt_path = output/'attempts'/f'{n:03}.json'
        if response_path.exists():
            response = json.loads(response_path.read_text())
            record = {k:response.get(k) for k in ['n','audit_id','status','keep','response_model',
                      'finish_reason','usage','request_id','prompt_sha256','response_sha256','completed_at_utc','error_type']}
        else:
            record = {'n':n, 'audit_id':meta['audit_id'], 'status':'attempted_unresolved' if attempt_path.exists() else 'not_attempted', 'keep':None}
        assert record['audit_id'] == meta['audit_id']
        record['sampling_frame'] = 'historical_1900_2010' if int(meta['date'][:4]) <= 2010 else 'modern_2011_2026'
        records.append(record)
    counts = dict(Counter(r['status'] for r in records))
    result = {'schema':'proquest-reverify300-export-v1', 'run_name':RUN_NAME,
              'specification':spec, 'updated_at_utc':now(), 'records':records,
              'counts':counts, 'keep_n':sum(r.get('keep') is True for r in records),
              'drop_n':sum(r.get('keep') is False for r in records),
              'attempted_n':sum((output/'attempts'/f'{n:03}.json').exists() for n in range(1,301)),
              'source_text_exported':False, 'reason_prose_exported':False}
    path = output/'categorical_export.json'
    tmp = output/'categorical_export.tmp'
    tmp.write_text(json.dumps(result,indent=2)+'\n')
    tmp.replace(path)
    print(json.dumps({k:result[k] for k in ['counts','keep_n','drop_n','attempted_n']}), flush=True)
    return result


def run(project, execute=False):
    metadata, prompts, spec, output, extract = prepare(project)
    if not execute:
        return export_results(metadata, spec, output)
    # A nonblocking process lock prevents simultaneous launches. Per-claim
    # exclusive attempt files additionally prevent retries after interruption.
    import fcntl
    with (output/'run.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        args = SimpleNamespace(sample=str(Path(project)/'gpt_sample.txt'),
                               base_url=None, key_file=None, model='gpt-4o-mini')
        with contextlib.redirect_stdout(io.StringIO()):
            client, model = extract.make_client(args)
        assert model == 'gpt-4o-mini'
        client = client.with_options(max_retries=0, timeout=90)
        consecutive_errors = 0
        for request in prompts:
            n = request['n']
            attempt_path = output/'attempts'/f'{n:03}.json'
            if attempt_path.exists():
                continue
            dump_new(attempt_path, {'n':n, 'audit_id':request['audit_id'], 'started_at_utc':now(),
                                    'prompt_sha256':request['prompt_sha256']})
            result = {k:request[k] for k in ['n','audit_id','prompt_sha256']}
            result.update(status='unresolved', keep=None)
            stop = False
            try:
                response = client.chat.completions.create(model=model, temperature=0,
                    max_tokens=256, messages=[{'role':'user', 'content':request['prompt']}])
                raw = response.model_dump()
                result['raw_response'] = raw
                result['response_sha256'] = sha(json.dumps(raw,sort_keys=True).encode())
                result['response_model'] = response.model
                result['request_id'] = getattr(response, '_request_id', None)
                result['usage'] = response.usage.model_dump() if response.usage else None
                choice = response.choices[0]
                result['finish_reason'] = choice.finish_reason
                assert choice.finish_reason == 'stop', 'Incomplete model response'
                keep = strict_verdict(choice.message.content)
                result.update(status='judged', keep=keep)
                consecutive_errors = 0
            except Exception as exc:
                result['error_type'] = type(exc).__name__
                consecutive_errors += 1
                stop = getattr(exc,'status_code',None) in {401,403,429} or consecutive_errors >= 3
            result['completed_at_utc'] = now()
            dump_new(output/'responses'/f'{n:03}.json', result)
            print(f'{n}/300 {result["status"]} keep={result["keep"]}', flush=True)
            if n % 10 == 0 or stop:
                export_results(metadata,spec,output)
            if stop:
                print('Stopped after connection/quota errors; no attempted claim will be retried.', flush=True)
                break
            time.sleep(0.2)
        return export_results(metadata,spec,output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project',type=Path,default=Path('/home/ec2-user/SageMaker/election_arm'))
    parser.add_argument('--run',action='store_true')
    args = parser.parse_args()
    run(args.project,args.run)
