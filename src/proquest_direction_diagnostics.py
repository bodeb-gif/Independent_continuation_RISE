"""Exploratory fixed-direction and warning-cost diagnostics of saved claims.

Motivated by inspected employment/flat-label imbalance. No model fitting or
replacement of the original baseline, and no source-validity claims.
"""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from proquest_target_robustness import SOURCE,TOPICS,load_scored,cohort,weighted,block_summary,digest

OUT=Path('data/scored/proquest/direction_diagnostics_v1')
BASELINE={'general_business':'improve','markets':'improve','prices':'up','employment':'down'}
OPPOSITE={'general_business':'worsen','markets':'worsen','prices':'down','employment':'up'}
SPEC={
 'date':'2026-10-19','status':'Exploratory diagnostics motivated by already inspected topic results and flat-label imbalance',
 'inputs':'Saved annual ProQuest 1900–2010 scores; verified primary, raw sensitivity',
 'comparators':['original fixed direction','always flat','always opposite direction'],
 'cohorts':['all_legacy','non_NBER','machine_stated_non_NBER'],
 'weights':'Equal article within each source set, cohort, topic and horizon subset',
 'uncertainty':'Paired occupied publication-block percentile intervals, 5000 resamples; 5 years primary, 2 and 10 sensitivity. Marginal and conditional on fixed scoring, not source-error or selection uncertainty.',
 'horizons':'Machine-stated non-NBER claims in fixed 1–6, 7–12 and 13–24 month bins; do not relabel them source-validated',
 'warning_task':'Binary detection of the direction opposite the original fixed baseline. A flat prediction is a nonwarning; a flat outcome is a nonevent. This is a different task from three-class accuracy. For prices, the event is a price decline, not universally an adverse economic event.',
 'costs':'Illustrative missed-event/false-alarm cost ratios 1,2,5,10. Compare to both never warn and always warn on identical rows; retain every result. No data-selected cost ratio or policy recommendation.',
 'decision':'Do not replace any primary model/baseline, alter scoring bands, calculate new superiority p-values, or use later data for tuning.',
}


def binary_costs(frame):
    weights=1/frame.groupby('page_id').page_id.transform('size').to_numpy()
    event=frame.realized.eq(OPPOSITE[frame.topic.iloc[0]]).to_numpy()
    warning=frame.predicted_norm.eq(OPPOSITE[frame.topic.iloc[0]]).to_numpy()
    avg=lambda x:float(np.average(x,weights=weights))
    tp=avg(event&warning);fp=avg(~event&warning);fn=avg(event&~warning);tn=avg(~event&~warning)
    divide=lambda x,y:x/y if y else np.nan
    metrics=dict(tp=tp,fp=fp,fn=fn,tn=tn,event_share=tp+fn,warning_share=tp+fp,
                 precision=divide(tp,tp+fp),recall=divide(tp,tp+fn),false_positive_rate=divide(fp,fp+tn),
                 break_even_vs_never=divide(fp,tp),break_even_vs_always=divide(tn,fn))
    costs=[]
    for ratio in [1,2,5,10]:
        loss=fp+ratio*fn
        costs.append(dict(miss_to_false_alarm_cost=ratio,forecast_loss=loss,never_warn_loss=ratio*(tp+fn),
                          always_warn_loss=fp+tn,improvement_vs_never=ratio*tp-fp,improvement_vs_always=tn-ratio*fn))
    return metrics,costs


def evaluate(frame,key,lengths=(2,5,10)):
    records=[]
    for rule,label in [('original_fixed',BASELINE[key['topic']]),('always_flat','flat'),('always_opposite',OPPOSITE[key['topic']])]:
        changed=frame.copy();changed['fixed_baseline_hit']=changed.realized.eq(label).astype(int)
        data=weighted(changed,'article')
        for length in lengths:
            result,_=block_summary(data,length)
            records.append(dict(**key,rule=rule,n_claims=len(frame),n_articles=frame.page_id.nunique(),**result))
    return records


def main():
    if OUT.exists():raise ValueError('Preserve existing diagnostic version')
    OUT.mkdir(parents=True);(OUT/'specification.json').write_text(json.dumps(SPEC,indent=2)+'\n')
    prior=Path('data/scored/proquest/target_robustness_v1/summary.json')
    expected=json.loads(prior.read_text())['inputs_sha256'][str(SOURCE)]
    if digest(SOURCE)!=expected:raise ValueError('Scored snapshot changed')
    frame=load_scored(SOURCE)
    labels=pd.read_csv(SOURCE,usecols=['source_set','record_id','realized','predicted_norm'])
    frame=frame.merge(labels,on=['source_set','record_id'],validate='one_to_one')
    if not frame.predicted_norm.eq(frame.realized).astype(int).eq(frame.hit).all():raise ValueError('Correctness labels inconsistent')
    comparisons=[];mix=[];warning_metrics=[];costs=[];horizons=[];decomposition=[]
    for source in ['verified','raw']:
        for cname in SPEC['cohorts']:
            pop=cohort(frame[frame.source_set.eq(source)],cname)
            for topic in TOPICS:
                sub=pop[pop.topic.eq(topic)].copy();key=dict(source_set=source,cohort=cname,topic=topic)
                comparisons+=evaluate(sub,key)
                w=weighted(sub,'article').mass.to_numpy();den=w.sum()
                for label in [BASELINE[topic],'flat',OPPOSITE[topic]]:
                    pred=sub.predicted_norm.eq(label).to_numpy();actual=sub.realized.eq(label).to_numpy()
                    mix.append(dict(**key,direction=label,forecast_share=float(np.sum(w*pred)/den),outcome_share=float(np.sum(w*actual)/den)))
                    # Contributions keep full-topic weights so they sum to the original gap.
                    d=(sub.hit-sub.fixed_baseline_hit).to_numpy()
                    decomposition.append(dict(**key,outcome=label,contribution_to_original_gap=float(np.sum(w*actual*d)/den)))
                if cname!='all_legacy':
                    metrics,rows=binary_costs(sub);warning_metrics.append(dict(**key,**metrics));costs.extend(dict(**key,**r) for r in rows)
                if cname=='machine_stated_non_NBER':
                    for low,high in [(1,6),(7,12),(13,24)]:
                        subset=sub[sub.horizon_used.between(low,high)]
                        if len(subset):horizons+=evaluate(subset,dict(**key,horizon_months=f'{low}-{high}'),(5,))
    tables=dict(comparisons=pd.DataFrame(comparisons),direction_mix=pd.DataFrame(mix),warning_metrics=pd.DataFrame(warning_metrics),
                illustrative_costs=pd.DataFrame(costs),horizon_comparisons=pd.DataFrame(horizons),gap_decomposition=pd.DataFrame(decomposition))
    for name,t in tables.items():t.to_csv(OUT/f'{name}.csv',index=False)
    check=tables['gap_decomposition'].groupby(['source_set','cohort','topic']).contribution_to_original_gap.sum()
    actual=tables['comparisons'].query("rule=='original_fixed' and block_years==5").set_index(['source_set','cohort','topic']).gap_vs_fixed
    np.testing.assert_allclose(check.sort_index(),actual.sort_index(),atol=1e-12)
    primary=tables['comparisons'].query("source_set=='verified' and cohort=='all_legacy' and block_years==5")
    fig,axes=plt.subplots(1,2,figsize=(12,4.6),layout='constrained')
    flat=tables['direction_mix'].query("source_set=='verified' and cohort=='all_legacy' and direction=='flat'").set_index('topic').loc[TOPICS]
    y=np.arange(4);axes[0].barh(y-.16,flat.forecast_share*100,height=.3,label='Forecast flat');axes[0].barh(y+.16,flat.outcome_share*100,height=.3,label='Outcome flat')
    axes[0].set_yticks(y,['Business','Markets','Prices','Employment*']);axes[0].set_xlabel('Article-weighted share (%)');axes[0].set_title('Flat labels are much rarer than flat outcomes');axes[0].legend()
    for i,rule in enumerate(['original_fixed','always_flat']):
        t=primary[primary.rule.eq(rule)].set_index('topic').loc[TOPICS];yy=y+(i-.5)*.17
        axes[1].hlines(yy,t.low*100,t.high*100,color=['#176b87','#b27639'][i]);axes[1].scatter(t.gap_vs_fixed*100,yy,color=['#176b87','#b27639'][i],label=rule.replace('_',' '))
    axes[1].axvline(0,color='#777');axes[1].set_yticks(y,['Business','Markets','Prices','Employment*']);axes[1].set_xlabel('Accuracy minus comparator (percentage points)');axes[1].set_title('Comparator choice changes the employment result');axes[1].legend()
    fig.suptitle('Recorded labels and legacy scoring; *employment uses unemployment-rate outcomes',fontsize=11)
    fig.savefig(OUT/'direction_diagnostics.png',dpi=160);plt.close(fig)
    page='<html lang="en"><meta charset="utf-8"><title>Direction and baseline diagnostics</title><style>body{font:16px/1.5 system-ui;margin:35px;max-width:1200px}td,th{padding:6px;border-bottom:1px solid #ddd}.table{overflow:auto}img{max-width:100%}</style><h1>Direction and baseline diagnostics</h1><p>Exploratory analysis prompted by observed flat-label imbalance. No new model, baseline replacement, scoring-band change, or source validation. Fixed alternatives are displayed together; they are not selected using outcomes.</p><img src="direction_diagnostics.png" alt="Flat forecast and outcome shares and comparator sensitivity">'
    for name,t in [('Verified legacy comparator sensitivity',primary),('Verified direction mix',tables['direction_mix'].query("source_set=='verified' and cohort=='all_legacy'")),('Verified stated-horizon comparisons',tables['horizon_comparisons'].query("source_set=='verified'")),('Warning classification',tables['warning_metrics']),('Illustrative cost tradeoffs',tables['illustrative_costs'])]:
        page+=f'<h2>{name}</h2><div class="table">'+t.to_html(index=False,float_format=lambda v:f'{v:.5f}')+'</div>'
    page+='<p>Flat is defined by the existing topic-specific endpoint bands, not literal zero change. Newspaper labels and realized bands may differ in meaning; source review is needed. Employment forecasts may concern job levels rather than unemployment. Cost ratios are illustrative, with no selected operational threshold; the binary warning task differs from three-class accuracy. Repeated outcomes, selection, nonstationarity and unmeasured interpretation errors limit all comparisons. Full block-length sensitivities are in comparisons.csv. No p-values are calculated.</p></html>'
    (OUT/'report.html').write_text(page)
    if digest(SOURCE)!=expected:raise ValueError('Input changed')
    summary=dict(status='complete',code_sha256=digest(__file__),inputs_sha256={str(SOURCE):expected,str(prior):digest(prior)},
                 imported_code_sha256={'src/proquest_target_robustness.py':digest('src/proquest_target_robustness.py')},
                 model_fits=0,source_reviews=0,new_p_values=False,outputs_sha256={str(p):digest(p) for p in OUT.iterdir() if p.is_file()})
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(primary[['topic','rule','hit_rate','fixed_baseline','gap_vs_fixed','low','high']].to_string(index=False))


if __name__=='__main__':main()
