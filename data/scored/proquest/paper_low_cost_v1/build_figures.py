"""Render manuscript figures from saved results; never fit or rescore a model.

Run at repository root with a working Python environment and matplotlib.
All modern values are a presentation of the separately saved October 20 study.
"""
from pathlib import Path
import csv
import hashlib
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[3]
SOURCES = set()

def records(relative):
    path = ROOT / relative
    SOURCES.add(path)
    return list(csv.DictReader(path.open()))

def document(relative):
    path = ROOT / relative
    SOURCES.add(path)
    return json.loads(path.read_text())

plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 9,
                     'axes.spines.top': False, 'axes.spines.right': False,
                     'axes.labelcolor': '#253645', 'text.color': '#253645',
                     'axes.edgecolor': '#81909c', 'pdf.fonttype': 42})
BLUE, ORANGE, GREY = '#215b79', '#bc673a', '#87959d'

def finish(fig, name):
    fig.savefig(OUT / (name + '.pdf'), bbox_inches='tight')
    fig.savefig(OUT / (name + '.png'), dpi=190, bbox_inches='tight')
    plt.close(fig)

# Costs are the recorded 23,000-page projections, not current prices.
configs = [('regex','Regex',0), ('gptoss120b','OSS extraction',22.65),
           ('oss120b_voss','OSS + self-verification',26.82),
           ('oss120b_vgemlite','OSS + Lite verifier',43.52),
           ('oss120b_vgemflash','OSS + Flash verifier',105.43),
           ('gem35flash_1chunk','Flash, one window',290.36),
           ('gemini35flash','Flash, 8k windows',403.70)]
SOURCES.add(ROOT / 'validation/gold_extraction/RESULTS.md')
fig, ax = plt.subplots(figsize=(6.55,3.3))
for i,(stem,label,cost) in enumerate(configs):
    r=document('validation/gold_extraction/result_'+stem+'.json')
    ax.scatter(cost/23,r['f1'],s=46,color=ORANGE if stem=='oss120b_voss' else BLUE,zorder=3)
    offsets={'regex':(6,7),'gptoss120b':(9,-17),'oss120b_voss':(100,-25),
             'oss120b_vgemlite':(7,17),'oss120b_vgemflash':(10,0),
             'gem35flash_1chunk':(-5,11),'gemini35flash':(-5,-17)}
    dx,dy=offsets[stem]
    ax.annotate(label,(cost/23,r['f1']),xytext=(dx,dy),textcoords='offset points',
                ha='right' if dx<0 else 'left',fontsize=8,
                arrowprops={'arrowstyle':'-', 'color':ORANGE, 'lw':.8}
                if stem=='oss120b_voss' else None)
ax.set(xlabel='Recorded projected API cost per 1,000 LOC pages (USD)',
       ylabel='F1 against model-adjudicated reference',xlim=(-.5,19),ylim=(.32,.86))
ax.grid(alpha=.18)
finish(fig,'cost_quality')

rs=records('data/scored/proquest/benchmark_interpretation_v2/primary_comparisons.csv')
rs=[r for r in rs if r['source_set']=='verified' and r['cohort']=='machine_stated_non_NBER'
    and r['topic']=='employment' and r['horizon_months']=='all' and r['rule']=='original_fixed'
    and r['block_years']=='5']
order=['original','duration_scaled','sign_only']
rs=sorted(rs,key=lambda r:order.index(r['regime']))
assert len(rs)==3 and all(int(r['n_claims'])==9260 for r in rs)
fig,(ax, bx)=plt.subplots(1,2,figsize=(6.55,3.1),gridspec_kw={'width_ratios':[1.3,1]})
x=np.arange(3)
for field,color,label,shift in [('hit_rate',BLUE,'Newspaper claims',-.17),('fixed_baseline',ORANGE,'Always improve',.17)]:
    vals=[100*float(r[field]) for r in rs]
    ax.bar(x+shift,vals,.32,color=color,label=label)
    for xi,v in zip(x+shift,vals):ax.text(xi,v+1,f'{v:.1f}',ha='center',fontsize=8)
ax.set_xticks(x,['Original','Duration\nscaled','Sign only'])
ax.set(ylabel='Correct (%)',ylim=(0,70));ax.legend(frameon=False,fontsize=8,loc='upper left')
v=np.array([100*float(r['gap_vs_fixed']) for r in rs])
lo=np.array([100*float(r['low']) for r in rs]);hi=np.array([100*float(r['high']) for r in rs])
bx.errorbar(v,x,xerr=[v-lo,hi-v],fmt='o',color=BLUE,capsize=4)
bx.axvline(0,color=GREY,ls='--',lw=1)
bx.set_yticks(x,['Original','Duration scaled','Sign only']);bx.invert_yaxis()
bx.set(xlabel='Advantage over baseline (pp)',xlim=(-10,35));bx.grid(axis='x',alpha=.18)
fig.tight_layout(w_pad=1.5);finish(fig,'employment_sensitivity')

# Field comparisons remain separate by review batch and sampling frame.
first=document('data/scored/proquest/source_review_150_v1/human_reconciliation_summary.json')
later=document('data/scored/proquest/source_review_additional150_v1/summary.json')
fields=['topic','direction','horizon_months','scope']
fig,ax=plt.subplots(figsize=(6.55,3.2))
for j,(data,label,color) in enumerate([(first,'Historical batch 1 (105 included)',GREY),
    (later['historical'],'Historical batch 2 (72 included)',BLUE),
    (later['modern'],'Modern extension (35 included)',ORANGE)]):
    vals=[100*data['field_agreement'][f]['matches']/data['field_agreement'][f]['denominator'] for f in fields]
    ax.scatter(vals,np.arange(4)+(j-1)*.19,label=label,s=35,color=color)
ax.set_yticks(range(4),['Topic','Direction','Horizon','Scope']);ax.invert_yaxis()
ax.set(xlim=(50,100),xlabel='Literal field agreement among included claims (%)')
ax.grid(axis='x',alpha=.18);ax.legend(loc='lower left',bbox_to_anchor=(0,1.01),frameon=False,fontsize=8,ncol=1)
finish(fig,'human_agreement')

rs=records('data/scored/proquest/modern_analysis_v1/claim_calibration.csv')
rs=[r for r in rs if r['model']=='gru_ensemble__baseline']
topics=records('data/scored/proquest/modern_analysis_v1/claim_breakdowns.csv')
topics=[r for r in topics if r['model']=='gru_ensemble__baseline' and r['group']=='topic']
fig,(ax,bx)=plt.subplots(1,2,figsize=(6.55,3.2),gridspec_kw={'width_ratios':[1,1]})
ax.plot([0,1],[0,1],ls='--',color=GREY,lw=1)
ax.plot([float(r['predicted']) for r in rs],[float(r['observed']) for r in rs],'-o',color=BLUE,ms=4)
ax.set(xlim=(0,1),ylim=(0,1),xlabel='Mean predicted correctness',ylabel='Observed correctness')
ax.set_title('A. Calibration',loc='left',fontsize=10)
names={'employment':'Employment','general_business':'Business','markets':'Markets','prices':'Prices'}
topics.sort(key=lambda r:float(r['roc_auc']))
bx.barh([names[r['value']] for r in topics],[float(r['roc_auc']) for r in topics],color=[ORANGE,BLUE,BLUE,BLUE])
bx.axvline(.5,color=GREY,ls='--',lw=1)
bx.set(xlim=(0,1),xlabel='Within-topic AUC')
for i,r in enumerate(topics):bx.text(float(r['roc_auc'])+.015,i,f"{float(r['roc_auc']):.3f}",va='center',fontsize=8)
bx.set_title('B. Discrimination',loc='left',fontsize=10)
fig.tight_layout(w_pad=1.5);finish(fig,'modern_diagnostics')

# Hash the sources used by the manuscript, not just those plotted above.
extra=['paper/manuscript/outline_low_cost_extraction.md','docs/PROQUEST_ANALYSIS.md',
       'docs/publication/ANALYSIS_SPEC.md','docs/publication/MODERN_ANALYSIS_AMENDMENT_20261020.md',
       'validation/gold_extraction/PROTOCOL.md','validation/gold_extraction/cost_table.py',
       'data/scored/proquest/inventory.json','data/scored/proquest/descriptive/summary.json',
       'data/scored/proquest/descriptive/exclusions.csv','data/scored/proquest/publication/evidence.json',
       'data/scored/proquest/alternative_targets_v1/primary_comparisons.csv',
       'data/scored/proquest/alternative_targets_v1/label_disagreement.csv',
       'data/scored/proquest/macro_benchmark/core/metrics.csv',
       'data/scored/proquest/macro_benchmark/evaluation_spec.json','data/scored/proquest/rnn/summary.json',
       'data/scored/proquest/rnn/metrics.csv','data/scored/proquest/rnn/report.md',
       'data/scored/proquest/source_review_additional150_v1/human_review_attestation_20261020.json',
       'data/scored/proquest/source_review_additional150_v1/README.md',
       'data/scored/proquest/source_review_150_v1/README.md',
       'data/scored/proquest/modern_analysis_v1/claim_metrics.csv',
       'data/scored/proquest/modern_analysis_v1/claim_summary.json',
       'data/scored/proquest/modern_analysis_v1/claim_paired_intervals.json',
       'data/scored/proquest/modern_analysis_v1/downturn/summary.json',
       'data/scored/proquest/modern_analysis_v1/downturn/all_metrics.csv',
       'src/proquest_descriptive.py','src/score_predictions.py','src/analyze_proquest.py',
       'validation/gold_extraction/eval_extraction.py',
       'data/scored/proquest/benchmark_interpretation_v2/specification.json',
       'data/scored/proquest/alternative_targets_v1/specification.json',
       'data/scored/proquest/rnn_permutation/paired_tests.csv',
       'docs/publication/POLARIZATION.md','data/scored/proquest/polarization/evaluation_spec.json']
SOURCES.update(ROOT/p for p in extra)
SOURCES.update((ROOT/'validation/gold_extraction').glob('hard_*.json'))
SOURCES.update((ROOT/'data/scored/proquest/modern_analysis_v1/downturn').glob('*/paired_intervals.json'))
manifest={'date':'2026-10-20','operation':'Presentation of saved evidence; no model fitting or rescoring',
          'sources':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(SOURCES)},
          'annual_source_exports':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
             for name in ['verified','raw'] for p in sorted((ROOT/'data/proquest'/name).glob('*.jsonl'))}}
(OUT/'source_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('Rendered four figures; recorded',len(SOURCES),'evidence sources and',len(manifest['annual_source_exports']),'annual export hashes.')
