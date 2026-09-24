"""Audit the 2007–2009 reversal in verified ProQuest forecast correctness.

Publication-year cohorts, not outcome-year cohorts. No models are fitted.
Reuses and validates the original ProQuest scoring rules and frozen references.
"""
import base64
from functools import lru_cache
import hashlib
import html
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from proquest_descriptive import BANDS, load_reference, realized_outcome
from proquest_followups import confusion_metrics, load_claims, matched_pair

OUT = Path('data/scored/proquest/crisis_2008')


def rates(group):
    grounded = group[group.horizon_basis.ne('default')]
    return {'n_claims': len(group), 'n_claim_articles': group.page_id.nunique(),
            'hit_count': int(group.hit.sum()), 'hit_rate': group.hit.mean(),
            'fixed_growth_direction_baseline': group.fixed_baseline_hit.mean(),
            'equal_article_hit_rate': group.groupby('page_id').hit.mean().mean(),
            'grounded_claims': len(grounded), 'grounded_hit_rate': grounded.hit.mean(),
            'default_horizon_share': group.horizon_basis.eq('default').mean()}


def grouped_rates(frame, keys):
    rows = []
    for key, group in frame.groupby(keys, observed=True):
        values = key if isinstance(key, tuple) else (key,)
        rows.append({**dict(zip(keys, values)), **rates(group)})
    return pd.DataFrame(rows)


def topic_decomposition(scored, start, end):
    """Symmetric two-factor arithmetic decomposition; not a causal estimate."""
    a, b = scored[scored.year.eq(start)], scored[scored.year.eq(end)]
    table = pd.concat([a.groupby('topic').hit.agg(['mean', 'size']).add_prefix('start_'),
                       b.groupby('topic').hit.agg(['mean', 'size']).add_prefix('end_')], axis=1)
    table['start_weight'] = table.start_size / len(a)
    table['end_weight'] = table.end_size / len(b)
    table['within_topic_contribution'] = (table.end_mean - table.start_mean) * (table.start_weight + table.end_weight) / 2
    table['topic_mix_contribution'] = (table.end_weight - table.start_weight) * (table.start_mean + table.end_mean) / 2
    assert np.isclose(table[['within_topic_contribution', 'topic_mix_contribution']].to_numpy().sum(), b.hit.mean() - a.hit.mean())
    table.insert(0, 'start_year', start); table.insert(1, 'end_year', end)
    return table.reset_index()


def sensitivities(scored, refs):
    rows = []
    for setting, multiplier, default in [('Base', 1., 12), ('Half bands', .5, 12), ('Double bands', 2., 12),
                                         ('Default 6 months', 1., 6), ('Default 24 months', 1., 24)]:
        @lru_cache(None)
        def label(topic, month, horizon):
            return realized_outcome(refs, topic, month, horizon, {k: v * multiplier for k, v in BANDS.items()})[0]
        for year in [2007, 2008, 2009]:
            group = scored[scored.year.eq(year)]
            hits = []
            for row in group.itertuples():
                horizon = default if row.horizon_basis == 'default' else int(row.horizon_used)
                actual = label(row.topic, str(row.month), horizon)
                assert actual is not None
                hits.append(int(row.predicted_norm == actual))
            rows.append({'setting': setting, 'year': year, 'n_claims': len(hits), 'hit_rate': np.mean(hits)})
    return pd.DataFrame(rows)


def charts(out, yearly, quarterly, business_quarter, topic_year):
    plt.rcParams.update({'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False})
    names = []
    def save(fig, name):
        fig.tight_layout(); fig.savefig(out/name, dpi=160, bbox_inches='tight'); plt.close(fig); names.append(name)
    fig, ax = plt.subplots(figsize=(10, 4.7))
    ax.plot(yearly.year, yearly.hit_rate * 100, 'o-', label='All eligible claims', color='#174e70')
    ax.plot(yearly.year, yearly.equal_article_hit_rate * 100, 's--', label='Equal weight per claim-bearing article', color='#668a40')
    ax.plot(yearly.year, yearly.grounded_hit_rate * 100, 'd--', label='Claim-grounded horizons only', color='#d47835')
    ax.axvspan(2007.75, 2008.25, color='#9ab6c7', alpha=.2)
    ax.set_xlabel('Publication year'); ax.set_ylabel('Correct forecasts (%)'); ax.set_ylim(0, 100)
    ax.set_title('2008 is an accuracy peak; the sharp drop follows in 2009'); ax.legend(fontsize=9); ax.grid(alpha=.15)
    save(fig, 'annual_accuracy.png')
    fig, ax = plt.subplots(figsize=(10, 4.7))
    for topic, group in topic_year.groupby('topic'):
        ax.plot(group.year, group.hit_rate * 100, 'o-', label=topic.replace('_', ' ').title())
    ax.set_xticks([2007, 2008, 2009]); ax.set_ylim(0, 100); ax.set_ylabel('Correct forecasts (%)')
    ax.set_title('Business and employment improve in 2008; prices deteriorate'); ax.legend(); ax.grid(alpha=.15)
    save(fig, 'topics.png')
    fig, axes = plt.subplots(2, 1, figsize=(11, 7), sharex=True)
    x = np.arange(len(quarterly))
    axes[0].plot(x, quarterly.hit_rate * 100, 'o-', color='#174e70')
    axes[0].set_ylabel('All-topic hit rate (%)'); axes[0].set_ylim(0, 100)
    axes[0].set_title('The reversal is concentrated in early 2009, not late 2008')
    lookup = dict(zip(quarterly.quarter, x))
    bx = business_quarter.quarter.map(lookup)
    axes[1].plot(bx, business_quarter.warning_share * 100, 'o-', color='#d47835', label='Business calls predicting worsening')
    axes[1].plot(bx, business_quarter.actual_decline_share * 100, 's--', color='#174e70', label='Horizon endpoints showing output decline')
    axes[1].set_ylim(0, 100); axes[1].set_ylabel('Business forecasts (%)'); axes[1].legend(fontsize=8)
    axes[1].set_xticks(x, quarterly.quarter, rotation=45)
    for ax in axes:
        ax.axvline(7.5, linestyle='--', color='#999'); ax.grid(alpha=.15)
    save(fig, 'quarterly_reversal.png')
    return names


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    claims, metadata, digests = load_claims()
    scored = claims[claims.scorable & claims.year.between(2004, 2010)].copy()
    scored['quarter'] = scored.date.dt.to_period('Q').astype(str)
    yearly = grouped_rates(scored, ['year'])
    yearly['verified_claims_all_scopes_topics'] = yearly.year.map(claims.groupby('year').size())
    yearly['scorable_share'] = yearly.n_claims / yearly.verified_claims_all_scopes_topics
    close = scored[scored.year.between(2007, 2009)].copy()
    yearly_close = yearly[yearly.year.between(2007, 2009)]
    topic_year = grouped_rates(close, ['year', 'topic'])
    quarterly = grouped_rates(close, ['quarter'])
    monthly = grouped_rates(close.assign(publication_month=close.month.astype(str)), ['publication_month'])
    business = close[close.topic.eq('general_business')]
    business_year = pd.DataFrame([{'year': year, **confusion_metrics(group)} for year, group in business.groupby('year')])
    business_quarter = pd.DataFrame([{'quarter': quarter, **confusion_metrics(group)} for quarter, group in business.groupby('quarter')])
    directions = close.groupby(['year', 'topic', 'predicted_norm']).agg(n_claims=('hit','size'), hit_count=('hit','sum'), hit_rate=('hit','mean')).reset_index()
    directions['forecast_share'] = directions.n_claims / directions.groupby(['year','topic']).n_claims.transform('sum')
    actual = close.groupby(['year', 'topic', 'realized']).size().rename('n_claims').reset_index()
    actual['outcome_share'] = actual.n_claims / actual.groupby(['year','topic']).n_claims.transform('sum')
    matrices = close.groupby(['year','topic','predicted_norm','realized']).size().rename('n_claims').reset_index()
    publishers = grouped_rates(close, ['year','paper'])
    common = set(close[close.year.eq(2007)].paper) & set(close[close.year.eq(2008)].paper) & set(close[close.year.eq(2009)].paper)
    common_year = grouped_rates(close[close.paper.isin(common)], ['year'])
    matching = []
    for later, earlier in [(2008,2007),(2009,2008)]:
        pair, cells = matched_pair(close, 'year', later, earlier, ['paper','topic','basis','horizon_basis','horizon_used'])
        matching.append(pair); cells.to_csv(OUT/f'matched_cells_{earlier}_{later}.csv', index=False)
    decompositions = pd.concat([topic_decomposition(close, 2007, 2008), topic_decomposition(close, 2008, 2009)], ignore_index=True)
    attribution = decompositions.groupby(['start_year','end_year'])[['within_topic_contribution','topic_mix_contribution']].sum().reset_index()
    pre_post = []
    for label, start, end in [('Before Lehman date', '2008-01-01','2008-09-14'), ('On/after Lehman date','2008-09-15','2008-12-31')]:
        group = close[close.date.between(start,end)]
        b = group[group.topic.eq('general_business')]
        pre_post.append({'period':label, **rates(group), 'business_claims':len(b),
                         'business_warning_share':b.predicted_norm.eq('worsen').mean(), 'business_hit_rate':b.hit.mean()})
    pre_post = pd.DataFrame(pre_post)
    horizons = grouped_rates(close, ['year','horizon_basis'])
    numeric_horizons = grouped_rates(close[close.horizon_basis.eq('stated')], ['year','topic','horizon_used'])
    refs, _ = load_reference()
    sensitivity = sensitivities(close, refs)
    endpoints = []
    for topic in ['general_business','markets','prices','employment']:
        for start in ['2007-01','2007-07','2008-01','2008-07','2008-12','2009-01','2009-07']:
            month = pd.Period(start,'M'); a,b = refs[topic][month],refs[topic][month+12]
            endpoints.append({'topic':topic,'publication_month':start,'horizon':12,'target_month':str(month+12),
                              'start_level':a,'end_level':b,'change':b-a if topic=='employment' else 100*(b/a-1),
                              'change_unit':'percentage points' if topic=='employment' else 'percent',
                              'realized':realized_outcome(refs,topic,start,12)[0]})
    tables = {'yearly':yearly,'year_topic':topic_year,'quarterly':quarterly,'monthly':monthly,
              'business_yearly':business_year,'business_quarterly':business_quarter,'forecast_directions':directions,
              'realized_directions':actual,'confusion_by_topic':matrices,'publishers':publishers,
              'common_publishers_yearly':common_year,'matched_year_comparisons':pd.DataFrame(matching),
              'topic_mix_decomposition':decompositions,'lehman_date_comparison':pre_post,
              'horizon_basis':horizons,'numeric_horizons':numeric_horizons,'sensitivity':sensitivity,
              'reference_12_month_examples':pd.DataFrame(endpoints)}
    for name, table in tables.items(): table.to_csv(OUT/f'{name}.csv',index=False)
    figures = charts(OUT,yearly,quarterly,business_quarter,topic_year)
    sections = [
        ('Overall publication-year cohorts',
         'Annual verified ProQuest claims only; US-national scope and the first report\'s four scored topics. '
         '2008 accuracy rises from 41.8% to 64.3%, then falls to 36.6% in 2009. '
         'A 2008 publication may be evaluated against an endpoint in 2009 or 2010; these are publication years, not outcome years. '
         'Equal-article rates are 45.3%, 64.6%, and 36.0%, respectively. These articles are claim-bearing records, not a full sampling denominator.',
         yearly[['year','n_claims','n_claim_articles','hit_rate','equal_article_hit_rate','grounded_claims','grounded_hit_rate']],['annual_accuracy.png']),
        ('Where the improvement and failures occurred',
         'Business improves from 42.5% to 75.3%, employment from 45.1% to 81.7%; markets are essentially unchanged at 47.4% versus 47.5%. '
         'Prices fall from 28.3% to 15.1%. CPI-flat outcomes account for 792/1,130 price claims (70.1%), but only 54 (4.8%) predict flat prices. '
         '617 predict falling prices and 459 rising prices; 52 and 85 are correct, respectively. '
         'Flat means an endpoint CPI change within ±1.5%, not zero inflation throughout the horizon. '
         'CPI matching is a broad consumer-price proxy; stripped quotes cannot establish that each claim concerns CPI rather than a particular commodity or price.',
         topic_year[['year','topic','n_claims','hit_rate']],['topics.png']),
        ('Warnings versus optimistic misses',
         '2008 business worsening calls: 4,143/4,233 correct (97.9%). Improvement calls: 6/1,191 correct (0.5%). '
         'Nevertheless 1,233 of 5,376 decline outcomes receive an improve/flat call (22.9% missed); 1,146 receive an improve call. '
         'Unemployment-rise predictions: 854/900 correct (94.9%); unemployment-fall predictions: 0/139 correct. '
         'Mechanically calling every business horizon a decline would score 97.5% in this cohort, and every unemployment horizon a rise would score 94.6%. '
         'These are retrospective state-direction comparisons, not a strategy selected before 2008 or evidence that the recession was anticipated.',
         directions[['year','topic','predicted_norm','n_claims','hit_count','hit_rate','forecast_share']],[]),
        ('Chronology: foresight and reversal',
         'In 2007 business accuracy rises from 18.6% in Q1 and 9.2% in Q2 to 48.8% in Q3 and 66.7% in Q4. '
         'Worsening-call shares rise from 55.6%/59.0% in Q1/Q2 to 73.8%/72.8% in Q3/Q4. '
         'The sample already contains many worsening calls before the crisis; the 2006 share is 64.6%, with only 3/354 correct. '
         'Thus the rise in correct warnings combines more pessimistic calls with a change in which direction became correct. '
         'NBER later dated the peak to December 2007, announced December 1, 2008; all 2008 publication months are retrospectively recession months in USREC. '
         'Lehman filed September 15, 2008. Before that date the business warning share is 73.3%, afterward 81.9%; '
         'business accuracy is 71.6% versus 80.8%. Unequal date windows and shifting composition prevent interpreting this as a causal response to Lehman. '
         'Overall quarterly accuracy falls sharply from 68.4% in 2008Q4 to 31.0% in 2009Q1.',
         quarterly[['quarter','n_claims','hit_rate']],['quarterly_reversal.png']),
        ('The large misses move into 2009',
         'Business worsening calls in 2009: 57/2,388 correct (2.4%); 2,331 false alarms comprise 1,567 growth and 764 flat outcomes. '
         'Improvement calls: 1,777/2,213 correct (80.3%). In 2009Q1, business accuracy is 14.5%, with 67.9% calling worsening '
         'but only 6.0% of horizon outcomes declining. Across all 2009, output-growth endpoints account for 72.8% of business claims. '
         'Market worsening calls: 2/664 correct; improvement calls: 508/530 correct (95.8%). '
         'Almost all market endpoints rise (1,192/1,250), yet 53.1% of calls still predict worsening. '
         'Employment accuracy also drops to 32.6%: 960/1,777 outcomes are flat under the ±0.5-point unemployment rule, '
         'and only 16 calls predict flat. These labels suggest difficulty adjusting expectations around turning points, '
         'but do not prove that the same forecasters persisted in the same view; this is an aggregate sample, not a speaker panel.',
         business_quarter[['quarter','n_claims','warning_share','actual_decline_share','warning_precision']],[]),
        ('Composition and horizon checks',
         'The same five publisher families represented in 2007, 2008 and 2009 score 41.8%, 64.3%, and 36.8%. '
         'Boston Globe and Los Angeles Times have no scored 2007 claims in these exports, so full-year publisher coverage differs. '
         'Shared paper/topic/benchmark/horizon-basis/exact-horizon cells with ten claims on each side score 44.2% in 2007 versus 63.9% in 2008 '
         '(42 cells; +19.7 points), and 66.8% in 2008 versus 37.1% in 2009 (86 cells; -29.6 points). '
         'Neither comparison controls publication month or economic state; they describe similar forecast composition, not causal differences. '
         'Claim-grounded accuracy is 30.5%, 58.4%, 37.6%; explicitly stated horizons score 29.0%, 57.7%, 38.0%. '
         '2008 default-horizon claims score 69.5%, so defaults amplify the peak but do not create it.',
         pd.DataFrame(matching),[]),
        ('Sensitivity and arithmetic attribution',
         'The sensitivity table changes outcome flat bands and the default horizon while preserving explicit/inferred horizons. '
         'Under every tested setting 2008 exceeds 2007 and 2009. In the base calculation, 21.3 of the 22.5 percentage-point '
         '2007–2008 rise is within-topic accuracy change; topic weights account for the other 1.2 points. '
         'The decomposition splits the overall change into within-topic rate changes and changes in topic weights, using symmetric arithmetic weights. '
         'It is an exact accounting identity, not a causal attribution or a significance test.',
         sensitivity,[]),
        ('Exact topic accounting',
         'Contributions below add exactly to the pooled publication-year accuracy changes. Figures are fractions of one, '
         'so 0.213 means 21.3 percentage points. Within-topic changes still combine direction mix, forecast horizons, publisher '
         'composition and economic outcomes; they are not estimates of improved forecaster skill.',
         attribution,[]),
        ('Scoring examples and limits',
         'The endpoint examples use frozen revised references. Business uses ±2% industrial production; markets ±5% monthly-average Shiller prices; '
         'prices ±1.5% CPI; employment ±0.5 percentage point unemployment. January 2008 to January 2009 output falls 13.4%, '
         'stock prices fall 37.2%, CPI changes only +0.03%, and unemployment rises 2.8 points. '
         'December 2008 stock prices to December 2009 rise 26.5%, so a bearish forecast near the crash may fail at its later endpoint. '
         'A directional hit does not measure magnitude, precise timing, recession-onset prediction, or tail-risk anticipation. '
         'The original query contains recession/downturn/depression/recovery/slump near prediction language; it is a selected corpus, '
         'not an unbiased panel of all press forecasts. High crisis-era claim counts do not establish more press attention without article denominators. '
         'Machine verification is not human validation; stripped quotes prevent causal narrative reconstruction, semantic rechecking, '
         'and definitive deduplication. Rows sharing an article and monthly benchmark outcome are not independent trials.',
         pd.DataFrame(endpoints),[])]
    markdown = ['# ProQuest forecasts around 2008', '']; blocks = ['<h1>ProQuest forecasts around 2008</h1>']
    for title, paragraph, table, images in sections:
        markdown += [f'## {title}','',paragraph,'']; blocks += [f'<h2>{html.escape(title)}</h2>',f'<p>{html.escape(paragraph)}</p>']
        display = table.copy()
        for col in display:
            if pd.api.types.is_numeric_dtype(display[col]):
                if any(word in col for word in ['rate','share','gap','baseline']):
                    display[col] = display[col].map(lambda v: f'{v:.1%}' if pd.notna(v) else '—')
                elif any(word in col for word in ['year','horizon','cells','claims','articles','count']):
                    display[col] = display[col].map(lambda v: f'{v:.0f}' if pd.notna(v) else '—')
                else: display[col] = display[col].map(lambda v: f'{v:.3f}' if pd.notna(v) else '—')
        markdown += ['| '+' | '.join(display.columns)+' |','| '+' | '.join(['---']*len(display.columns))+' |']
        markdown += ['| '+' | '.join(str(v) for v in row)+' |' for row in display.itertuples(index=False,name=None)]; markdown += ['']
        blocks.append('<div class="table">'+display.to_html(index=False,border=0)+'</div>')
        for name in images:
            blocks.append('<img alt="'+name+'" src="data:image/png;base64,'+base64.b64encode((OUT/name).read_bytes()).decode()+'">')
    sources = {'Recession peak determination and announcement':'https://www.nber.org/news/business-cycle-dating-committee-announcement-december-1-2008',
               'Recession trough announcement':'https://www.nber.org/sites/default/files/2021-03/sept2010.pdf',
               'Lehman chronology':'https://www.federalreservehistory.org/essays/support-for-specific-institutions'}
    for label,url in sources.items():
        markdown += [f'[{label}]({url})','']; blocks += [f'<p><a href="{url}">{html.escape(label)}</a></p>']
    (OUT/'report.md').write_text('\n'.join(markdown))
    style='body{font:16px system-ui;line-height:1.6;max-width:1100px;margin:40px auto;padding:0 24px;color:#17364b}img{max-width:100%}.table{overflow-x:auto}table{border-collapse:collapse;font-size:13px}th,td{padding:8px;border-bottom:1px solid #ddd}'
    (OUT/'report.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><title>ProQuest 2008 analysis</title><style>'+style+'</style><body>'+''.join(blocks)+'</body></html>')
    facts={'verified_claims':len(claims),'scorable_claims_total':int(claims.scorable.sum()),
           'yearly':yearly.to_dict('records'),'business_yearly':business_year.to_dict('records'),
           'matched_comparisons':matching,'common_publishers':sorted(common),'reference':metadata['reference'],
           'verified_source_sha256':digests,'historical_sources':sources,
           'score_sha256':hashlib.sha256(Path('data/scored/proquest/descriptive/scored_claims.csv.gz').read_bytes()).hexdigest(),
           'code_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (OUT/'summary.json').write_text(json.dumps(facts,indent=2,default=lambda v:v.item() if isinstance(v,np.generic) else str(v))+'\n')
    print(yearly_close.to_string(index=False));print(sensitivity.to_string(index=False));print(decompositions.to_string(index=False))
    print('Report:',OUT/'report.html')


if __name__ == '__main__':
    main()
