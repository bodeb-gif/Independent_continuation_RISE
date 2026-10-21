"""Render the completed separate modern study without refitting or selecting models."""
from pathlib import Path
import sys,json,base64,html
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from proquest_modern_analysis import OUT,digest,write_json,freeze_check

summary=json.loads((OUT/'claim_summary.json').read_text())
metrics=pd.read_csv(OUT/'claim_metrics.csv');metrics=metrics[metrics.weighting.eq('equal_article')]
future=json.loads((OUT/'downturn/summary.json').read_text())
down=pd.read_csv(OUT/'downturn/all_metrics.csv')
pretty={'gru_ensemble__baseline':'Frozen RNN (primary)','gru_ensemble__both':'RNN + both polarizations',
        'logistic_metadata_history__baseline':'Logistic + history','gru8_historical_challenger':'Historical GRU8 challenger',
        'logistic_metadata__baseline':'Metadata logistic'}
selected=list(pretty)
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
fig,axs=plt.subplots(1,2,figsize=(12,4.4),layout='constrained')
g=metrics.set_index('model').loc[selected]
axs[0].barh([pretty[x] for x in selected],g.brier,color=['#1e5f8a','#628e75','#8996a7','#9c7e9c','#babfc7'])
axs[0].invert_yaxis();axs[0].set_xlabel('Article-weighted Brier score • lower is better');axs[0].set_title('Claim correctness on modern exports')
for i,x in enumerate(g.brier):axs[0].text(x+.002,i,f'{x:.3f}',va='center')
axs[0].set_xlim(0,.23)
breaks=pd.read_csv(OUT/'claim_breakdowns.csv');topic=breaks[(breaks.model=='gru_ensemble__baseline')&(breaks.group=='topic')]
axs[1].barh(topic.value.str.replace('_',' '),topic.roc_auc,color=['#b66b61' if x<.5 else '#1e5f8a' for x in topic.roc_auc]);axs[1].axvline(.5,color='#555',linestyle='--',linewidth=1)
axs[1].set_xlim(0,1);axs[1].set_xlabel('ROC AUC • 0.5 is no discrimination');axs[1].set_title('Performance differs sharply by topic')
for i,row in enumerate(topic.itertuples()):axs[1].text(row.roc_auc+.015,i,f'{row.roc_auc:.3f}',va='center')
fig.savefig(OUT/'claim_results.png',dpi=170);plt.close(fig)
fig,axs=plt.subplots(2,1,figsize=(12,7),layout='constrained')
for ax,name,title in zip(axs,['recession_onset_12m','production_decline_12m'],['A recession beginning in the following 12 months','Industrial production declining over 12 months']):
 f=pd.read_csv(OUT/'downturn'/name/'modern_predictions.csv');x=pd.PeriodIndex(f.origin,freq='M').to_timestamp();chosen=future[name]['selected_model']
 ax.plot(x,f[chosen],label=chosen.replace('_',' '),color='#1e5f8a',linewidth=1.5)
 ax.plot(x,f.historical_base_rate,label='Expanding historical event rate',color='#b1824b',linestyle='--')
 known=f.evaluated_as_of.astype(bool);positives=known&f.target.eq(1)
 ax.scatter(x[positives],np.full(sum(positives),.98),marker='|',color='#bb4f43',label='Mature positive target months',s=45)
 ax.set_ylim(0,1);ax.set_ylabel('Model probability');ax.set_title(title);ax.legend(loc='upper left',fontsize=8,ncol=2)
 ax.axvline(pd.Timestamp('2026-09-01'),linestyle=':',color='#555');ax.grid(axis='y',alpha=.2)
fig.savefig(OUT/'downturn_probabilities.png',dpi=170);plt.close(fig)
def image(name):return '<img alt="'+html.escape(name)+'" src="data:image/png;base64,'+base64.b64encode((OUT/name).read_bytes()).decode()+'">'
def table(frame):return frame.to_html(index=False,border=0,float_format=lambda x:f'{x:.4f}',escape=True)
forecast_rows=[]
for name,r in future.items():
 metric=down[(down.target==name)&down.selected_pre2011].iloc[0];base=down[(down.target==name)&down.model.eq('historical_base_rate')].iloc[0]
 forecast_rows.append(dict(target=name,chosen_pre2011=r['selected_model'],probability=r['latest_probability'],base_rate_probability=r['all_latest_probabilities']['historical_base_rate'],modern_brier=metric.brier,baseline_brier=base.brier,evaluated_months=r['evaluated_months']))
forecast_table=pd.DataFrame(forecast_rows)
intervals=[]
for name,r in future.items():
 for x in json.loads((OUT/'downturn'/name/'paired_intervals.json').read_text()):
  if x['b']==r['selected_model']:intervals.append(dict(target=name,improvement=x['delta_brier_a_minus_b'],low=x['low'],high=x['high'],time_blocks=x['n_blocks']))
claim_intervals=json.loads((OUT/'claim_paired_intervals.json').read_text())
ci=pd.DataFrame([{k:r[k] for k in ['a','b','delta_brier_a_minus_b','low','high','n_blocks']} for r in claim_intervals])
body='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ProQuest modern evaluation — October 20, 2026</title>
<style>body{font:16px/1.55 system-ui,sans-serif;color:#192f40;background:#f5f7fa;margin:0}main{max-width:1120px;margin:auto;padding:40px 24px}h1{font-size:32px;line-height:1.2}h2{margin-top:36px}section{background:white;padding:24px;margin:20px 0;border:1px solid #dce3e8;border-radius:10px}.note{border-left:5px solid #b1824b;padding:14px 20px;background:#fff9ed}table{border-collapse:collapse;font-size:13px;display:block;overflow:auto}td,th{padding:8px 12px;border-bottom:1px solid #dce3e8;text-align:left}th{background:#edf2f6}img{width:100%;height:auto}a{color:#135e91}code{font-size:13px}li{margin:6px 0}</style><main>
<h1>Modern ProQuest analysis</h1><p>Prepared October 20, 2026 • Separate 2011–2026 study • Exploratory evaluation</p>
<div class="note"><b>The claim RNN and the downturn models answer different questions.</b> The frozen RNN estimates whether an extracted forecast is correct. The separate monthly logistic models estimate recession onset or production decline. Neither establishes what will certainly happen.</div>
<section><h2>Data and validation</h2><p>Imported 91,118 claims. Excluded all 33,071 empty records from model inputs, including 20,580 repeated empty records in 2011. Preserved source bytes and row addresses. Excluded the 19 default-kept verification exceptions from primary inputs, leaving 91,099 claims. Historical and modern exports remain separate.</p>
<p>The author's 150 historical human reviews reconcile locally: 105 included, 44 excluded, 1 unclear across 149 articles. Direction agreement is 94/105 and scope agreement 65/105 among included claims. This positive-candidate sample cannot measure recall and contains no modern claims. It supports assessment of the extraction process, not validation of every modern forecast. Earlier AI/model-label exposure remains documented. Current-state coding conventions differ, so its agreement and the all-eleven-field count are not valid overall accuracy measures.</p>
<p>Prior exposure to modern results remains unknown. The original full intake gate was not certified: processing metadata are incomplete. The dated scope amendment authorizes this exploratory analysis without changing the original frozen gate.</p></section>
<section><h2>Frozen claim-model evaluation</h2><p>56,886 mature, supported claims from 23,775 articles were scored; all models use identical evaluation rows and equal total weight per article. The remaining 32,604 claims have unsupported scope/topic/direction/horizon, 1,138 are immature, and 471 cross missing reference observations. Those gaps are October 2025 CPI and unemployment observations and were not imputed.</p>
<p>Historical reproduction matched 56,807 saved rows across all original arms, with maximum probability error below 3×10⁻⁸. The primary ensemble remains fixed. All 30 frozen artifacts are unchanged.</p>'''+image('claim_results.png')+'''
<p>The primary RNN has Brier 0.1770 and AUC 0.7376; the history logistic control has Brier 0.1936 and AUC 0.6545. The RNN with both polarization measures has Brier 0.1742 and AUC 0.7486 as a secondary result. The historically selected GRU8 challenger does not improve primary Brier. Do not select the modern winner retroactively.</p>
<p><b>Employment is a failure mode:</b> the primary RNN's employment AUC is 0.3064, versus 0.7675 for general business, 0.7881 for markets and 0.9060 for prices. Pooled performance does not justify using it for every topic. Always predicting “incorrect” would achieve 71.3% article-weighted classification accuracy in this sample; the primary RNN reaches 75.4%, so accuracy alone overstates the result.</p>'''+table(metrics.drop(columns='weighting'))+'''
<details><summary>Paired claim-model Brier intervals</summary><p>Difference = primary RNN loss minus comparator loss; negative favors the primary RNN. Five-year blocks anchored at 2011, 2,000 draws. There are four blocks, with only 13 scored claims in the 2026 partial block. These are descriptive intervals, not new permutation p-values. Improvements against the main logistic control and from both polarization measures have intervals crossing zero.</p>'''+table(ci)+'''</details></section>
<section><h2>Separate 12-month downturn forecasts</h2><p>Latest complete newspaper month: <b>August 2026</b>. Latest forecast origin: <b>September 2026</b>, covering <b>September 2026–August 2027</b>. This is not an October-origin forecast. Inputs have 56 recent general-business articles from five newspapers over three observed months. Models refit annually in January; the latest saved coefficients are the January 2026 fit.</p>
<p>Recession means a new 0→1 transition in USREC during the target window, not a recession already under way. Production decline means the monthly INDPRO index at August 2027 is below August 2026; the 2% variant is a separate severity sensitivity. These events are different. USREC is an interpretation of NBER retrospective dating; industrial production is a sectoral production measure, not all GDP. See <a href="https://fred.stlouisfed.org/series/USREC">USREC</a> and <a href="https://fred.stlouisfed.org/series/INDPRO">INDPRO</a>.</p>'''+table(forecast_table)+image('downturn_probabilities.png')+'''
<p><b>Research estimates:</b> 6.9% for recession onset, 28.0% for any production decline, and 22.4% for a decline greater than 2%. Candidate probabilities vary: recession estimates range from 6.9% to 27.0%. The selected production-decline estimate is essentially the same as the latest historical base rate (28.0%).</p>
<p>Selection used only mature pre-2011 rolling Brier results, comparing a base rate and four press/polarization logistic variants. Modern rolling evaluation is separate. The selected recession model improved Brier from 0.0832 to 0.0696; the production-decline model from 0.2570 to 0.2272. The selected greater-than-2% model was worse than its base-rate comparator (0.1470 versus 0.1373); retain that unfavorable result.</p>
<div class="note"><b>These estimates do not yet support a strong downturn call.</b> Modern recession evaluation contains only one distinct onset (March 2020), represented by 12 overlapping positive months. The selected-model improvements have paired block intervals crossing zero. A 92.2% recession classification accuracy is also achieved by always predicting no onset at a 0.5 threshold. Model probabilities are exploratory, not established calibrated risks.</div>
<h3>Selected-model uncertainty</h3><p>Positive improvement = base-rate Brier minus selected-model Brier. There are only three five-year time blocks and overlapping target windows.</p>'''+table(pd.DataFrame(intervals))+'''<details><summary>All modern downturn comparators</summary>'''+table(down)+'''</details></section>
<section><h2>Reproducibility and remaining work</h2><p>Original outcome snapshots are preserved with hashes. Claim maturity requires endpoint plus three months strictly before October 2026. Recession labels use a conservative 24-month allowance; production uses three months. This is approximate historical availability with revised outcomes, not archived real-time label vintages. No macroeconomic values or outcome columns enter the predictor features. Political features use actual lagged House votes, not NOMINATE scores.</p>
<p>Future-publication/vote mutation tests passed. All 163 main-suite checks and 16 intake/modern checks passed. No new model-selection or permutation p-value claim was made. Source-validation errors, changing query/coverage, the full-intake metadata gaps and very few modern recession events remain limitations.</p>
<p>Next priorities: obtain complete September-onward corpus coverage for a current forecast; reconcile upstream processing metadata; investigate the employment failure without flipping predictions on the test set; evaluate against an archived macroeconomic baseline; and assess forecasts prospectively as outcomes mature. Refit/retune any successor on explicitly separated development data and freeze its future evaluation.</p>
<p>Entry points: <code>src/proquest_modern_analysis.py</code> and <code>src/proquest_downturn.py</code>. Run manifest, model bundles, source exclusions, predictions, outcomes, calibration, subgroup metrics and block intervals accompany this report.</p></section></main></html>'''
(OUT/'report.html').write_text(body)
write_json(OUT/'completion_manifest.json',dict(as_of='2026-10-20',frozen_artifacts_unchanged=len(freeze_check()),
    validation={'offline':97,'scoring':33,'forecasts':33,'modern':6,'export_receipt':4,'frozen_intake':6},
    files_sha256={str(p):digest(p) for p in OUT.rglob('*') if p.is_file() and p.name!='completion_manifest.json' and 'voteview' not in p.parts},
    report_generator_sha256=digest(__file__)))
print(OUT/'report.html')
