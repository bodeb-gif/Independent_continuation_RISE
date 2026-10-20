"""Assemble writing exhibits from existing results; no fits, selection or relabeling.

Every number retains its source hash and unique row selector. Output is a writing
inventory, not a new statistical analysis or a substitute for source validation.
"""
import csv
import hashlib
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = Path("data/scored/proquest")
OUT = BASE / "writing_evidence_v1"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def select_row(rows, where):
    matches = [r for r in rows if all(r.get(k) == v for k, v in where.items())]
    if len(matches) != 1:
        raise ValueError(f"Expected one result for {where}, found {len(matches)}")
    return matches[0]


def assemble(root=ROOT):
    inputs, entries = {}, []

    def source(name):
        rel = str(BASE / name)
        inputs[rel] = sha(root / rel)
        return rel

    def evidence(eid, question, claim, role, sample, metric, limitation, requests):
        facts = []
        for name, where, columns in requests:
            rel = source(name)
            if name.endswith('.csv'):
                with (root / rel).open(newline='') as handle:
                    row = select_row(list(csv.DictReader(handle)), where)
                values = {k: row[k] for k in columns}
                selector = where
            else:
                row = json.loads((root / rel).read_text())
                for key in where:
                    row = select_row(row, key) if isinstance(key, dict) else row[key]
                values = {k: row[k] for k in columns}
                selector = {'json_path': where}
            facts.append({'source': rel, 'sha256': inputs[rel], 'selector': selector, 'values': values})
        entries.append(dict(id=eid, question=question, supported_statement=claim,
                            exhibit_role=role, sample=sample, metric=metric,
                            limitation=limitation, status='historical_exploratory', facts=facts))

    evidence('E01', 'Corpus and measurement', 'The scored sample is a subset of machine-verified extracted claims.',
             'Table 1: sample flow', 'Annual verified ProQuest 1900–2010', 'Counts; legacy claim-weighted accuracy',
             'Machine verification is not human source validation; article-processing denominators remain unavailable.',
             [('publication/evidence.json', [], ['verified_claims','verified_scored_claims','pooled_legacy_hit_rate','pooled_legacy_baseline'])])
    evidence('E02', 'Corpus and measurement', 'The legacy baseline gap persists under equal-article weighting.',
             'Table 2: original scoring', 'All scorable verified claims; articles weighted equally', 'Accuracy and forecast-minus-fixed gap',
             'Conditional on legacy targets and horizons; not a validated population forecast-error rate.',
             [('publication/evidence.json', ['equal_article_comparison'], ['verified_hit_rate','verified_fixed_baseline','verified_gap_vs_fixed'])])
    bands = 'benchmark_interpretation_v2/primary_comparisons.csv'
    evidence('E03', 'Interpretation sensitivity', 'Employment scores and constant-baseline rankings depend on the outcome band.',
             'Figure 1 / Table 3: all three regimes and comparators', '9,260 matched verified employment claims; machine-stated horizons; non-NBER; equal article',
             'Accuracy; forecast-minus-comparator gap; paired five-year block bootstrap interval',
             'Duration scaling and sign-only rules are scenarios, not source-validated corrections; keep all regimes.',
             [(bands, dict(source_set='verified',cohort='machine_stated_non_NBER',topic='employment',horizon_months='all',regime=regime,rule=rule),
               ['n_claims','n_articles','hit_rate','fixed_baseline','gap_vs_fixed','low','high'])
              for regime in ('original','duration_scaled','sign_only') for rule in ('original_fixed','always_flat','always_opposite')])
    alt = 'alternative_targets_v1/primary_comparisons.csv'
    for eid, topic, claim, sample in [
        ('E04','employment','Payroll growth and falling unemployment do not give interchangeable outcome labels.',
         '9,260 matched employment claims; all endpoint series available'),
        ('E05','general_business','GDP and production sensitivity does not establish superiority to always predicting growth.',
         '15,680 business claims; quarter-end publication months and whole-quarter horizons, 1947–2010')]:
        evidence(eid, 'Interpretation sensitivity', claim, 'Table 4: alternative targets', sample,
                 'Equal-article accuracy; paired five-year block bootstrap interval; label disagreement',
                 'Targets are hypothetical mappings pending source review. GDP quarter-average levels are not monthly IP endpoints; never interpolate GDP.',
                 [(alt, dict(source_set='verified',cohort='machine_stated_non_NBER',topic=topic,variant=variant,comparator='always_improve'),
                   ['n_claims','hit_rate','fixed_baseline','gap_vs_fixed','low','high'])
                  for variant in (('frozen_sign','alternative_sign') if topic=='employment' else ('frozen_sign','quarterly_ip_sign','alternative_sign'))]
                 + [('alternative_targets_v1/label_disagreement.csv',
                     dict(source_set='verified',cohort='machine_stated_non_NBER',topic=topic,variant='alternative_sign',reference='frozen_sign' if topic=='employment' else 'quarterly_ip_sign'),
                     ['article_weighted_disagreement'])])
    evidence('E06', 'Incremental macro information', 'The press-augmented aggregate model has a small, uncertain average Brier improvement.',
             'Table 5: aggregate macro task', '408 monthly forecasts, 1977–2010, six-month IP direction',
             'Three-class Brier (0–2); positive improvement favors press; five-year block interval',
             'Do not compare directly with binary claim-correctness Brier; interval spans zero.',
             [('macro_benchmark/core/metrics.csv',dict(grouping='overall',model=m),['n_months','brier']) for m in ('macro_only','macro_plus_press')]
             + [('publication/evidence.json',['monthly_core_brier_interval'],['improvement','low','high','n_blocks'])])
    evidence('E07', 'Incremental macro information', 'Excluding 2007–2009 reverses the aggregate Brier ranking.',
             'Table 5: adjacent robustness panel', '372 monthly forecasts after removing 2007–2009',
             'Three-class Brier (0–2); lower is better',
             'Exploratory era sensitivity, not proof that text has no information or that crises cause the difference.',
             [('macro_benchmark/core/metrics.csv',dict(grouping='sensitivity',period='Exclude 2007–2009',model=m),['n_months','brier']) for m in ('macro_only','macro_plus_press')])
    evidence('E08', 'Claim-correctness prediction', 'The original RNN comparison does not reject equal predictive performance at 0.05.',
             'Appendix A: original model inference', '1995–2010; four publication-time blocks; 16 paired swaps',
             'Binary Brier improvement; one-sided paired permutation p; Holm adjustment across primary comparisons',
             'Minimum exact one-sided p is 1/16 = 0.0625. Do not shorten blocks to seek significance. Non-rejection does not prove equivalence.',
             [('rnn_permutation/paired_tests.csv',dict(metric='brier',comparison=c),['improvement','p_one_sided','n_blocks','n_permutations','primary_holm_p']) for c in ('gru_vs_metadata','gru_vs_history_logistic')])
    evidence('E09', 'Claim-correctness prediction', 'Production inputs improve average RNN loss in the matched experiment, but metadata logistic remains stronger.',
             'Appendix B: complete input ablation', 'Matched business/employment claims; four exposed five-year eras, 1975–1994',
             'Mean of four article-weighted binary Brier scores; lower is better',
             'Historical exploratory comparison; no new superiority test or promotion. Not comparable to the original broader 1995–2010 sample.',
             [('macro_claim_inputs_v1/summary_metrics.csv',dict(topic='all',model=model,arm=arm),['mean_brier','mean_improvement','folds_improved','worst_fold_brier'])
              for model in ('gru','logistic_metadata','logistic_metadata_history') for arm in ('none','production','unemployment','both')])
    evidence('E10', 'Claim-correctness prediction', 'Added macro inputs have different effects across business and employment claims.',
             'Appendix B: topic panels', 'Same matched 1975–1994 experiment; topic-specific article weights',
             'Mean binary Brier and number of improved eras out of four',
             'Small topic support and historical selection limit interpretation; retain adverse input results.',
             [('macro_claim_inputs_v1/summary_metrics.csv',dict(topic=topic,model='gru',arm=arm),['mean_brier','mean_improvement','folds_improved'])
              for topic in ('general_business','employment') for arm in ('none','production','unemployment','both')])
    evidence('E11', 'Source validation', 'Twelve pilot addresses are fixed; source interpretation remains unmeasured.',
             'Table 6: reserved for future audit, no estimates yet', 'Pilot SRS of 12 from 175,855 scored verified records',
             'Sample design only; no validity rate',
             'Do not replace missing mappings or combine pilot and main-audit estimates. Main sample is not yet drawn.',
             [('publication/evidence.json',['pilot'],['seed','n','population_n','design','source_mapping'])])
    evidence('E12', 'Claim-correctness prediction', 'Political and forecast polarization remain separate ablations; neither improves the original RNN average Brier.',
             'Appendix A: original RNN and polarization metrics', '56,807 scored claims, 1995–2010; original saved model experiment',
             'Article-weighted binary Brier, accuracy, AUC and average precision',
             'Political roll-call separation and forecast-direction disagreement are different constructs. This is not a causal polarization effect or a fresh holdout after tuning.',
             [('polarization/claims_summary.json',['metrics',dict(model=model,arm=arm,scope='overall')],
               ['n','brier','accuracy','auc','average_precision'])
              for model in ('gru_ensemble','logistic_metadata','logistic_metadata_history')
              for arm in ('baseline','political','forecast','both')])
    # Specs travel with result selectors so a writer can reconstruct their estimands.
    for name in ['benchmark_interpretation_v2/specification.json','alternative_targets_v1/specification.json',
                 'macro_claim_inputs_v1/specification.json','modern_readiness/model_freeze.json']:
        source(name)
    inputs['src/proquest_writing_evidence.py'] = sha(root/'src/proquest_writing_evidence.py')
    return entries, inputs


def main():
    entries, inputs = assemble()
    out=ROOT/OUT; out.mkdir(parents=True, exist_ok=True)
    (out/'ledger.json').write_text(json.dumps({'status':'Writing preparation; no new analyses or human judgments',
        'entries':entries},indent=2)+'\n')
    with (out/'facts.csv').open('w',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=['evidence_id','source','sha256','selector','field','value'])
        writer.writeheader()
        for e in entries:
            for fact in e['facts']:
                for field,value in fact['values'].items():
                    writer.writerow(dict(evidence_id=e['id'],source=fact['source'],sha256=fact['sha256'],
                                         selector=json.dumps(fact['selector'],sort_keys=True),field=field,value=value))
    body=['<!doctype html><meta charset="utf-8"><title>ProQuest writing evidence</title>',
          '<style>body{font:16px/1.5 system-ui;max-width:1100px;margin:40px auto;padding:0 24px}section{border-top:1px solid #bbb;margin:30px 0}pre{white-space:pre-wrap;overflow-wrap:anywhere}small{color:#555}</style>',
          '<h1>Evidence for writing</h1><p>Historical exploratory evidence. No new model fits or source judgments. Each number retains its exact source selector. Source validation and modern evaluation remain pending.</p>']
    for e in entries:
        body += [f'<section><h2>{e["id"]} · {html.escape(e["supported_statement"])}</h2>',
                 f'<p>{html.escape(e["exhibit_role"])}<br>{html.escape(e["sample"])}<br>{html.escape(e["metric"])}</p>',
                 f'<p><strong>Limit:</strong> {html.escape(e["limitation"])}</p>']
        for f in e['facts']:
            link='../../../../'+f['source']
            body.append(f'<details><summary><a href="{html.escape(link)}">{html.escape(f["source"])}</a> · {html.escape(json.dumps(f["selector"]))}</summary><pre>{html.escape(json.dumps(f["values"],indent=2))}</pre><small>SHA256 {f["sha256"]}</small></details>')
        body.append('</section>')
    (out/'report.html').write_text('\n'.join(body))
    manifest={'inputs_sha256':inputs,'outputs_sha256':{p.name:sha(p) for p in
              (out/'ledger.json',out/'facts.csv',out/'report.html')},'entries':len(entries)}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(f'Wrote {len(entries)} evidence entries to {out}')


if __name__ == '__main__':
    main()
