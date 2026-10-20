"""Build a results inventory and verify selected results in an isolated checkout.

Does not overwrite historical artifacts, refit neural candidates, or use modern data.
"""
import argparse
import csv
import hashlib
import html
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

ROOT=Path(__file__).resolve().parents[1]
BASE=Path('data/scored/proquest')
CATALOG=[
 ('descriptive','primary descriptive','Legacy deterministic individual-claim scoring; source interpretation unresolved','src/proquest_descriptive.py'),
 ('robustness','primary sensitivity','Raw versus verified and matched composition; not a causal filter effect','src/proquest_robustness.py'),
 ('target_robustness_v1','primary descriptive uncertainty','Paired baseline gaps; marginal conditional block intervals','src/proquest_target_robustness.py'),
 ('direction_diagnostics_v1','exploratory comparator audit','All constant directions and warning costs retained; original baseline unchanged','src/proquest_direction_diagnostics.py'),
 ('article_direction_audit_v1','exploratory unit-of-analysis audit','Multiple directions within article/target/horizon groups; no deduplication or error judgment','src/proquest_article_direction_audit.py'),
 ('macro_benchmark','primary aggregate model','Selected simple macro versus macro plus press; stable advantage not established','src/proquest_macro_benchmark.py'),
 ('macro_information','superseded benchmark','Earlier richer macro benchmark retained for comparison','src/proquest_macro_information.py'),
 ('monthly_information','exploratory weaker benchmark','Newspaper signals against class-frequency controls','src/proquest_information.py'),
 ('macro_diagnostics','diagnostic','Explains earlier macro errors; no new model','src/proquest_macro_diagnostics.py'),
 ('followups','exploratory descriptive','Warnings, horizons, attribution and matched publishers','src/proquest_followups.py'),
 ('crisis_2008','exploratory annual-corpus subset','2008–2009 analysis from annual exports, not old crisis-window exports','src/proquest_2008.py'),
 ('rnn','secondary frozen reference','24-unit GRU; historical superiority not established','src/proquest_rnn.py'),
 ('polarization','exploratory feature extension','Political and forecast measures separate; added arms not promoted','src/proquest_polarization_models.py'),
 ('rnn_audit','diagnostic','Saved-prediction stability and subgroup losses','src/proquest_rnn_audit.py'),
 ('rnn_permutation','diagnostic inference','Original four-block comparison and input perturbations; no chance-learning test','src/proquest_rnn_permutation.py'),
 ('rnn_block_sensitivity','diagnostic sensitivity','All tested block lengths retained; no p-value selection',''),
 ('rnn_development_v1','provisional candidate','8-unit 20-year-window baseline candidate; no fresh independent evaluation','src/proquest_rnn_development.py'),
 ('rnn_age_weighting_v1','failed improvement rule','Three age-decay candidates retained; incumbent unchanged','src/proquest_rnn_age_weighting.py'),
 ('export_reconciliation','provenance','222 historical files reconciled; processing completeness remains separate',''),
 ('modern_readiness','deferred execution','Prepared manifest and original model freeze; no modern evaluation','src/proquest_modern_intake.py'),
 ('prepared_inputs_check_v1','data handoff check','All historical print-time columns reproduced without outcome columns','src/proquest_prepare_inputs.py'),
 ('prepared_scoring_check_v1','data handoff check','Historical eligibility and deterministic outcomes reproduced with maturity gates','src/proquest_prepare_inputs.py'),
 ('prepared_features_check_v1','data handoff check','Explicit-calendar political and forecast feature reconstruction','src/proquest_prepare_features.py'),
 ('publication','evidence assembly only','Prior manuscript snapshot and uncompleted source-review pilot','src/proquest_publication.py'),
]


def digest(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump(path,value): Path(path).write_text(json.dumps(value,indent=2)+'\n')


def audit(out):
    rows=[]
    for directory,status,meaning,entry in CATALOG:
        folder=ROOT/BASE/directory
        rows.append(dict(directory=str(BASE/directory),status=status,interpretation=meaning,entrypoint=entry,
                         exists=folder.is_dir(),report=str(BASE/directory/'report.html') if (folder/'report.html').exists() else '',
                         file_count=sum(p.is_file() for p in folder.rglob('*'))))
    known={name for name,*_ in CATALOG}
    for folder in sorted((ROOT/BASE).iterdir()):
        if folder.is_dir() and folder.name not in known and folder.resolve()!=out.resolve():
            rows.append(dict(directory=str(folder.relative_to(ROOT)),status='auxiliary check or diagnostic',
                             interpretation='Retained run artifacts; not a replacement for primary results',entrypoint='',exists=True,
                             report=str(folder.relative_to(ROOT)/'report.html') if (folder/'report.html').exists() else '',
                             file_count=sum(p.is_file() for p in folder.rglob('*'))))
    with (out/'results_inventory.csv').open('w') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    # Snapshot the actual current code separately from historical creation hashes.
    paths=[*ROOT.glob('src/*.py'),*ROOT.glob('tests/*.py'),*ROOT.glob('scripts/*.py'),*ROOT.glob('scripts/*.sh'),
           *ROOT.glob('requirements-proquest*.txt')]
    snapshot={str(p.relative_to(ROOT)):digest(p) for p in paths}
    dump(out/'current_code_snapshot.json',snapshot)
    freeze=json.loads((ROOT/BASE/'modern_readiness/model_freeze.json').read_text())['files_sha256']
    changed=[p for p,h in freeze.items() if not (ROOT/p).exists() or digest(ROOT/p)!=h]
    if changed: raise ValueError(f'Frozen originals changed: {changed}')
    checks=[];cache={}
    def walk(value,parent=''):
        if isinstance(value,dict):
            for k,v in value.items():
                if isinstance(v,str) and len(v)==64 and all(c in '0123456789abcdef' for c in v) and (k.startswith(('data/','src/','docs/','tests/','requirements')) or Path(k).is_absolute()):
                    yield k,v,parent
                else: yield from walk(v,k)
        elif isinstance(value,list):
            for v in value:yield from walk(v,parent)
    manifests=sorted(p for p in (ROOT/BASE).rglob('*.json') if p.name in {'summary.json','manifest.json','run_manifest.json','output_manifest.json','feature_manifest.json','bundle_manifest.json','model_freeze.json'})
    for p in manifests:
        if out==p.parent:continue
        for name,expected,kind in walk(json.loads(p.read_text())):
            target=ROOT/name
            if name not in cache:cache[name]=digest(target) if target.is_file() else None
            actual=cache[name]
            checks.append(dict(manifest=str(p.relative_to(ROOT)),path=name,kind=kind,
                               status='match' if actual==expected else 'missing' if actual is None else 'changed',
                               expected=expected,current=actual))
    dump(out/'provenance_checks.json',checks)
    warnings=[r for r in checks if r['status']!='match']
    summary=dict(catalog_entries=len(rows),frozen_original_files_verified=len(freeze),hash_checks=len(checks),
                 current_hash_differences=len(warnings),differences=warnings,
                 interpretation='Historical code hashes describe creation versions. Changed runner code is not evidence that saved model weights changed; frozen artifacts are checked separately.',
                 git_status=subprocess.run(['git','status','--short'],cwd=ROOT,text=True,capture_output=True,check=True).stdout)
    dump(out/'inventory_summary.json',summary)
    page='<html><meta charset="utf-8"><title>ProQuest results inventory</title><style>body{font:16px/1.5 system-ui;margin:40px}td,th{padding:8px;border-bottom:1px solid #ddd}</style><h1>ProQuest results inventory</h1><p>Historical 1900–2010 only. Source validation, modern evaluation and manuscript drafting remain deferred. Primary refers to analysis role, not validated superiority.</p><table><tr><th>Directory</th><th>Status</th><th>Interpretation</th></tr>'
    for r in rows:page+='<tr>'+''.join(f'<td>{html.escape(str(r[k]))}</td>' for k in ['directory','status','interpretation'])+'</tr>'
    page+=f'</table><p>Verified {len(freeze)} frozen original files. Historical manifest differences: {len(warnings)}; see provenance_checks.json.</p></html>'
    (out/'inventory.html').write_text(page)
    print(f'Inventory: {len(rows)} entries, {len(checks)} hash checks, {len(warnings)} historical differences',flush=True)


def rebuild(out,python,scratch):
    import pandas as pd
    if scratch.exists():raise ValueError('Scratch path already exists; preserve the old run')
    scratch.mkdir(parents=True)
    for name in ['src','tests','scripts','docs']:
        shutil.copytree(ROOT/name,scratch/name,ignore=shutil.ignore_patterns('__pycache__'))
    for p in ROOT.glob('requirements*.txt'):shutil.copy2(p,scratch/p.name)
    # Legacy offline checks use these small local macro fixtures; never fetch them.
    shutil.copytree(ROOT/'cache',scratch/'cache')
    (scratch/'data/scored/proquest').mkdir(parents=True)
    (scratch/'data/proquest').symlink_to(ROOT/'data/proquest',target_is_directory=True)
    (scratch/'data/reference').symlink_to(ROOT/'data/reference',target_is_directory=True)
    for p in (ROOT/BASE).iterdir():
        if p.name in ['target_robustness_v1','macro_benchmark','direction_diagnostics_v1'] or p.resolve()==out.resolve():continue
        (scratch/BASE/p.name).symlink_to(p,target_is_directory=p.is_dir())
    macro=scratch/BASE/'macro_benchmark';macro.mkdir()
    shutil.copy2(ROOT/BASE/'macro_benchmark/evaluation_spec.json',macro/'evaluation_spec.json')
    logs=out/'logs';logs.mkdir()
    commands=[]
    def run(name,args):
        start=time.monotonic()
        with (logs/f'{name}.log').open('w') as log:
            process=subprocess.run([str(python),*args],cwd=scratch,stdout=log,stderr=subprocess.STDOUT,
                                   env=dict(os.environ,MPLCONFIGDIR=str(scratch/'mpl'),OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1'))
        commands.append(dict(name=name,arguments=args,exit_code=process.returncode,seconds=time.monotonic()-start))
        dump(out/'commands.json',commands)
        print(f'{name}: exit {process.returncode}',flush=True)
        if process.returncode:raise RuntimeError(f'{name} failed; see {logs/name}.log')
    for p in sorted((scratch/'tests').glob('test_proquest*.py')):
        run(p.stem,[f'tests/{p.name}'])
    for name in ['offline','scoring','forecasts']:run(f'test_{name}',[f'tests/test_{name}.py'])
    run('inventory',['src/analyze_proquest.py','--out',str(BASE/'rebuilt_inventory')])
    run('descriptive',['src/proquest_descriptive.py','--out',str(BASE/'rebuilt_descriptive')])
    run('target_robustness',['src/proquest_target_robustness.py'])
    run('direction_diagnostics',['src/proquest_direction_diagnostics.py'])
    run('prepare_scored_inputs',['src/proquest_prepare_inputs.py','--exports','data/proquest/verified',
          '--first-year','1900','--last-year','2010','--score','--as-of','2026-10-19',
          '--reference-dir','data/reference/proquest','--out',str(BASE/'rebuilt_prepared_inputs')])
    run('prepare_features',['src/proquest_prepare_features.py','--claims',str(BASE/'rebuilt_prepared_inputs/claims.csv.gz'),
          '--rollcalls',str(BASE/'polarization/rollcall_separation.csv.gz'),'--start','1900-01','--through','2010-12',
          '--out',str(BASE/'rebuilt_prepared_features')])
    run('macro_benchmark',['src/proquest_macro_benchmark.py'])
    run('rnn_reload',['src/proquest_rnn_runner.py','predict','--claims',str(BASE/'descriptive/scored_claims.csv.gz'),
                      '--features',str(BASE/'polarization/features.csv'),'--bundle',str(BASE/'polarization/claims'),
                      '--start','1995-01','--through','2010-12','--out',str(BASE/'rebuilt_rnn_predictions')])
    comparisons=[]
    def compare_csv(name,a,b):
        left=pd.read_csv(a);right=pd.read_csv(b)
        pd.testing.assert_frame_equal(left,right,check_dtype=False,rtol=1e-10,atol=1e-12)
        comparisons.append(dict(name=name,rows=len(left),columns=len(left.columns),status='match',rtol=1e-10,atol=1e-12))
    assert json.loads((scratch/BASE/'rebuilt_inventory/inventory.json').read_text())==json.loads((ROOT/BASE/'inventory.json').read_text())
    comparisons.append(dict(name='annual inventory',status='exact JSON match'))
    for p in sorted((ROOT/BASE/'descriptive').glob('*.csv*')):
        compare_csv(f'descriptive/{p.name}',p,scratch/BASE/'rebuilt_descriptive'/p.name)
    for p in sorted((ROOT/BASE/'target_robustness_v1').glob('*.csv')):
        compare_csv(f'target_robustness/{p.name}',p,scratch/BASE/'target_robustness_v1'/p.name)
    for p in sorted((ROOT/BASE/'direction_diagnostics_v1').glob('*.csv')):
        compare_csv(f'direction_diagnostics/{p.name}',p,scratch/BASE/'direction_diagnostics_v1'/p.name)
    prepared=pd.read_csv(scratch/BASE/'rebuilt_prepared_inputs/claims.csv.gz')
    columns=[c for c in prepared if c!='unscorable_reason']
    legacy=pd.read_csv(ROOT/BASE/'descriptive/scored_claims.csv.gz',usecols=columns)
    pd.testing.assert_frame_equal(prepared[columns],legacy[columns],check_dtype=False,rtol=1e-12,atol=1e-12)
    comparisons.append(dict(name='prepared inputs and mature deterministic scores',rows=len(prepared),status='match',
                            note='Exclusion reason wording differs; scoring eligibility, outcomes and feature columns compared'))
    compare_csv('political and forecast feature reconstruction',ROOT/BASE/'polarization/features.csv',scratch/BASE/'rebuilt_prepared_features/features.csv')
    for p in sorted((ROOT/BASE/'macro_benchmark').rglob('*.csv')):
        compare_csv(f'macro_benchmark/{p.relative_to(ROOT/BASE/"macro_benchmark")}',p,macro/p.relative_to(ROOT/BASE/'macro_benchmark'))
    compare_csv('frozen RNN/logistic probability reload',ROOT/BASE/'rnn_runner_check_v2/predictions.csv.gz',scratch/BASE/'rebuilt_rnn_predictions/predictions.csv.gz')
    dump(out/'rebuild_comparisons.json',comparisons)
    versions=json.loads(subprocess.check_output([str(python),'-c','import importlib.metadata as m,json; print(json.dumps({d.metadata["Name"].lower().replace("_","-"):d.version for d in m.distributions()}))'],text=True))
    dump(out/'rebuild_summary.json',dict(status='passed',scratch=str(scratch),python=str(python),versions=versions,
         commands=len(commands),comparisons=len(comparisons),neural_refits=0,
         scope='Annual inventory, verified deterministic scoring/tables, target and direction sensitivity, input/scoring/feature preparation, both selected macro studies and saved four-arm neural/logistic inference. Neural training checked with synthetic tests, not full historical refits.',
         code_snapshot_sha256=digest(out/'current_code_snapshot.json'),lock_sha256=digest(ROOT/'requirements-proquest-lock.txt')))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,default=BASE/'reproducibility_v1')
    parser.add_argument('--rebuild',action='store_true')
    parser.add_argument('--python',type=Path)
    parser.add_argument('--scratch',type=Path)
    args=parser.parse_args()
    out=args.out.resolve()
    if not out.is_relative_to((ROOT/BASE).resolve()) or out.exists():raise ValueError('Use a new output under data/scored/proquest')
    if args.rebuild and (not args.python or not args.scratch):parser.error('--rebuild requires --python and --scratch')
    out.mkdir(parents=True)
    audit(out)
    # Resolving the executable symlink would escape the selected virtualenv.
    if args.rebuild:rebuild(out,args.python.absolute(),args.scratch.resolve())


if __name__=='__main__':main()
