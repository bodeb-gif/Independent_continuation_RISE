"""Exploratory, time-block permutation diagnostics of frozen ProQuest RNNs.

No label shuffling, model fits, source review, or modern scoring. Run at repo root.
"""
import hashlib
import itertools
import json
from pathlib import Path
import platform

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score
import torch

from proquest_followups import load_claims
from proquest_rnn import ClaimGRU, monthly_context, sequence_indices, neural_probabilities

BASE = Path("data/scored/proquest")
SAVED = BASE / "polarization"
OUT = BASE / "rnn_permutation"
ARMS = {"baseline": (), "political": ("political_polarization",),
        "forecast": ("forecast_polarization",),
        "both": ("political_polarization", "forecast_polarization")}
SPEC = {
    "date": "2026-10-19", "status": "Exploratory diagnostics specified after historical results were inspected",
    "population": "Frozen annual verified ProQuest test predictions, 1995–2010; equal total weight per article",
    "models": "Saved 3-seed ensembles and saved logistic predictions; no fitting or model selection",
    "primary_metric": "Binary Brier loss; lower is better",
    "paired_test": "Swap the two models' entire prediction vectors within each five-year publication block (1995–99, 2000–04, 2005–09, 2010). Enumerate all 16 swaps including identity; one-sided tail counts include ties. Null requires joint within-block model-label exchangeability, not merely equal mean loss. Cross-block outcome dependence and four blocks limit interpretation. Not a target-permutation test of learning versus chance.",
    "primary_comparisons": ["baseline GRU vs metadata logistic", "baseline GRU vs metadata-history logistic"],
    "secondary_comparisons": "baseline GRU vs frozen training prevalence; each augmented GRU vs baseline GRU",
    "multiplicity": "Holm-adjust the two primary Brier p-values; other metrics/comparisons are exploratory",
    "feature_permutation": "All 24 permutations of four consecutive 48-month origin blocks from 1995–2010. Preserve within-block month order, season, all claims at a month, and full donor 12-month sequences. Keep claim metadata and outcomes fixed. Permute sequence, individual polarization scalar with its missingness flag, or all monthly inputs jointly. Use a common mapping across all seeds and arms. Importance = perturbed Brier minus original Brier; mean/quantiles exclude identity. Scores are diagnostic synthetic perturbations, may assign later context to earlier claims and break dependencies with metadata; never deployable forecasts or causal effects. Rank fractions are descriptive, not calibrated significance p-values.",
    "sequence_order": "Baseline only: reverse all 12 monthly steps; also 99 unique random nonidentity step permutations with seed 20261019, shared across every sequence and seed. Keep values and metadata fixed. Measures reliance on ordering; not superiority to a nonrecurrent neural model.",
    "references": ["https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.permutation_test.html",
                   "https://scikit-learn.org/stable/modules/permutation_importance"],
    "modern": "Deferred at user request. Only 1900–2010 available; build reusable data-path/model runner instead."
}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def scores(y, p, w):
    p = np.asarray(p, dtype=float)
    if not np.isfinite(p).all() or (p < 0).any() or (p > 1).any():
        raise ValueError("Invalid probabilities")
    return {"brier": float(np.average((p-y)**2, weights=w)),
            "log_loss": float(np.average(-(y*np.log(np.clip(p,1e-15,1)) + (1-y)*np.log(np.clip(1-p,1e-15,1))), weights=w)),
            "accuracy": float(np.average((p >= .5) == y, weights=w)),
            "auc": float(roc_auc_score(y,p,sample_weight=w)),
            "average_precision": float(average_precision_score(y,p,sample_weight=w))}


def block_swap(y, a, b, weights, blocks):
    """Positive observed differences favor model a. Exhaustive conditional test."""
    _, codes = np.unique(blocks, return_inverse=True)
    n = int(codes.max()) + 1
    if n > 12:
        raise ValueError("Too many blocks for this exhaustive diagnostic")
    values = []
    for pattern in itertools.product((False, True), repeat=n):
        switch = np.asarray(pattern)[codes]
        sa = scores(y, np.where(switch,b,a), weights)
        sb = scores(y, np.where(switch,a,b), weights)
        values.append({"swap": ''.join(str(int(i)) for i in pattern),
                       **{m: (sb[m]-sa[m] if m in ("brier","log_loss") else sa[m]-sb[m]) for m in sa}})
    distribution = pd.DataFrame(values)
    result = []
    for metric in scores(y,a,weights):
        observed = distribution[metric].iloc[0]
        p = float(np.mean(distribution[metric].to_numpy() >= observed - 1e-12))
        result.append({"metric":metric, "improvement":observed, "p_one_sided":p,
                       "n_blocks":n, "n_permutations":len(distribution)})
    return pd.DataFrame(result), distribution


def holm(values):
    values = np.asarray(values, dtype=float)
    order = np.argsort(values)
    result = np.empty_like(values)
    result[order] = np.minimum(1, np.maximum.accumulate(values[order] * np.arange(len(values),0,-1)))
    return result


def month_mapping(order, block_months=48):
    if sorted(order) != list(range(len(order))):
        raise ValueError("Not a block permutation")
    return np.concatenate([np.arange(i*block_months,(i+1)*block_months) for i in order])


def added_values(features, parameters, names):
    """Apply saved scalar transformations; no fit on evaluation months."""
    if not names:
        return np.empty((len(features),0), dtype=np.float32)
    rows = parameters.set_index("feature").loc[list(names)]
    values = features[list(names)].to_numpy(float)
    missing = np.isnan(values)
    scaled = (np.where(missing, rows["median"].to_numpy(), values)-rows["mean"].to_numpy())/rows["scale"].to_numpy()
    return np.column_stack([scaled,missing]).astype(np.float32)


def fast_predict(models, hidden, claim, month_codes, added, donor, group, names):
    """Cache GRU states by unique month; only the head varies per claim."""
    context_codes = donor[month_codes] if group in ("sequence","all_monthly") else month_codes
    extra = added[month_codes].copy()
    for index,name in enumerate(names):
        if group in (name,"all_monthly"):
            columns = [index,index+len(names)]
            extra[:,columns] = added[donor[month_codes]][:,columns]
    claim_tensor = torch.from_numpy(np.column_stack([claim,extra]).astype(np.float32))
    predictions = []
    with torch.no_grad():
        for model,states in zip(models,hidden):
            predictions.append(model.head(torch.cat([states[context_codes],claim_tensor],dim=1)).squeeze(1).sigmoid().numpy())
    return np.mean(predictions,axis=0)


def main():
    torch.set_num_threads(2)
    torch.use_deterministic_algorithms(True)
    OUT.mkdir(parents=True,exist_ok=True)
    spec_path = OUT / "specification.json"
    if spec_path.exists() and json.loads(spec_path.read_text()) != SPEC:
        raise ValueError("Preserve prior specification and record an amendment")
    spec_path.write_text(json.dumps(SPEC,indent=2)+"\n")
    frozen = json.loads((BASE/"modern_readiness/model_freeze.json").read_text())["files_sha256"]
    frozen.update(json.loads((SAVED/"output_manifest.json").read_text())["outputs_sha256"])
    frozen.update(json.loads((SAVED/"claims_summary.json").read_text())["inputs_sha256"])
    for path,sha in frozen.items():
        if digest(path) != sha: raise ValueError(f"Frozen input changed: {path}")
    claims, _, source_hashes = load_claims()
    frozen.update(source_hashes)
    saved = pd.read_csv(SAVED/"claims/test_predictions.csv.gz",dtype={"page_id":str})
    test = claims.set_index("record_id").loc[saved.record_id].reset_index()
    if not test.scorable.all() or test.basis.eq("NBER proxy").any() or not test.year.between(1995,2010).all():
        raise ValueError("Invalid test population")
    if not np.array_equal(test.hit,saved.hit) or not np.array_equal(test.page_id,saved.page_id):
        raise ValueError("Saved outcome/article mismatch")
    if not np.array_equal(test.date.dt.strftime('%Y-%m-%d'),saved.date):
        raise ValueError("Saved date mismatch")
    if test.record_id.duplicated().any(): raise ValueError("Duplicate test addresses")
    y = test.hit.to_numpy(int)
    weights = 1/test.groupby('page_id').page_id.transform('size').to_numpy()
    parameters = joblib.load(SAVED/"claims/preprocessing_and_baselines.joblib")
    context = monthly_context(claims)
    if list(context.columns) != parameters['context_features']: raise ValueError("Context vocabulary changed")
    months = pd.period_range('1995-01','2010-12',freq='M')
    month_codes = months.get_indexer(test.month)
    if (month_codes < 0).any(): raise ValueError("Month outside frozen test")
    sequence = parameters['context_scaler'].transform(context).astype('float32')[sequence_indices(months,context.index)]
    categories = test[parameters['claim_categories']].fillna('missing')
    claim = np.column_stack([parameters['encoder'].transform(categories),
                             parameters['horizon_scaler'].transform(test[['horizon_used']])]).astype('float32')
    features = pd.read_csv(SAVED/'features.csv').set_index('origin').loc[months.astype(str)]
    prep = pd.read_csv(SAVED/'claims/added_preprocessing.csv')
    swaps=[]; swap_distributions=[]
    original_path=BASE/'rnn/test_predictions.csv.gz'; frozen[str(original_path)] = digest(original_path)
    original=pd.read_csv(original_path).set_index('record_id').loc[test.record_id]
    comparisons=[('gru_vs_metadata','baseline','logistic_metadata__baseline'),
                 ('gru_vs_history_logistic','baseline','logistic_metadata_history__baseline'),
                 ('gru_vs_constant','baseline','constant_train_prevalence')]
    comparisons += [(f'{a}_vs_baseline',a,'gru_ensemble__baseline') for a in ARMS if a!='baseline']
    for name,arm,comparator in comparisons:
        b = original[comparator].to_numpy() if comparator=='constant_train_prevalence' else saved[comparator].to_numpy()
        result, distribution = block_swap(y,saved[f'gru_ensemble__{arm}'].to_numpy(),b,weights,test.year.to_numpy()//5)
        swaps.append(result.assign(comparison=name)); swap_distributions.append(distribution.assign(comparison=name))
    paired = pd.concat(swaps,ignore_index=True)
    primary = paired.comparison.isin(['gru_vs_metadata','gru_vs_history_logistic']) & paired.metric.eq('brier')
    paired.loc[primary,'primary_holm_p'] = holm(paired.loc[primary,'p_one_sided'])
    paired.to_csv(OUT/'paired_tests.csv',index=False)
    pd.concat(swap_distributions,ignore_index=True).to_csv(OUT/'paired_null_scores.csv',index=False)
    rows=[]; reproduction=[]; order_rows=[]
    identity=np.arange(len(months))
    permutations=list(itertools.permutations(range(4)))
    for arm,names in ARMS.items():
        models=[]; hidden=[]
        extra=added_values(features,prep[prep.arm.eq(arm)],names)
        for seed in (11,29,47):
            checkpoint=torch.load(SAVED/f'claims/gru_{arm}_{seed}.pt',map_location='cpu',weights_only=True)
            model=ClaimGRU(checkpoint['context_size'],checkpoint['claim_size'],checkpoint['hidden_size'])
            model.load_state_dict(checkpoint['state_dict']); model.eval(); models.append(model)
            with torch.no_grad(): hidden.append(model.gru(torch.from_numpy(sequence))[1][-1])
            direct=neural_probabilities(model,torch.from_numpy(sequence[month_codes]),
                                       torch.from_numpy(np.column_stack([claim,extra[month_codes]]).astype('float32')))
            error=float(np.max(np.abs(direct-saved[f'gru_seed_{seed}__{arm}'].to_numpy())))
            if error>2e-6: raise ValueError(f'Saved checkpoint reproduction failed: {arm}, {seed}, {error}')
            reproduction.append({'arm':arm,'seed':seed,'max_probability_error':error})
        base=fast_predict(models,hidden,claim,month_codes,extra,identity,'none',names)
        np.testing.assert_allclose(base,saved[f'gru_ensemble__{arm}'],rtol=0,atol=2e-6)
        original_scores=scores(y,base,weights)
        groups=['sequence',*names]+(['all_monthly'] if names else [])
        for group in groups:
            for perm in permutations:
                p=fast_predict(models,hidden,claim,month_codes,extra,month_mapping(perm),group,names)
                result=scores(y,p,weights)
                rows.append({'arm':arm,'feature_group':group,'block_order':''.join(map(str,perm)),
                             'identity':perm==(0,1,2,3),**result,
                             'brier_increase':result['brier']-original_scores['brier'],
                             'average_precision_drop':original_scores['average_precision']-result['average_precision']})
            print(f'Completed {arm}: {group}',flush=True)
        if arm=='baseline':
            rng=np.random.default_rng(20261019); orders=[]; seen={tuple(range(12))}
            while len(orders)<99:
                order=tuple(rng.permutation(12).tolist())
                if order not in seen: orders.append(order); seen.add(order)
            for label,order in [('reverse',tuple(range(11,-1,-1)))]+[(f'random_{i:02}',v) for i,v in enumerate(orders)]:
                with torch.no_grad():
                    altered=[m.gru(torch.from_numpy(sequence[:,order,:].copy()))[1][-1] for m in models]
                p=fast_predict(models,altered,claim,month_codes,extra,identity,'none',names)
                result=scores(y,p,weights)
                order_rows.append({'perturbation':label,'step_order':','.join(map(str,order)),**result,
                                   'brier_increase':result['brier']-original_scores['brier']})
            print('Completed 12-step order diagnostics',flush=True)
    permutations_frame=pd.DataFrame(rows)
    permutations_frame.to_csv(OUT/'feature_permutation_scores.csv',index=False)
    pd.DataFrame(order_rows).to_csv(OUT/'sequence_order_scores.csv',index=False)
    pd.DataFrame(reproduction).to_csv(OUT/'checkpoint_reproduction.csv',index=False)
    importance=[]
    for (arm,group),data in permutations_frame.groupby(['arm','feature_group']):
        baseline=data[data.identity].iloc[0]; altered=data[~data.identity]
        importance.append({'arm':arm,'feature_group':group,'baseline_brier':baseline.brier,
                           'mean_permuted_brier':altered.brier.mean(),'mean_brier_increase':altered.brier_increase.mean(),
                           'permutation_q025':altered.brier_increase.quantile(.025),
                           'permutation_q975':altered.brier_increase.quantile(.975),
                           'mean_average_precision_drop':altered.average_precision_drop.mean(),
                           'descriptive_brier_rank_fraction':float((data.brier<=baseline.brier+1e-12).mean()),
                           'n_nonidentity_permutations':len(altered)})
    importance=pd.DataFrame(importance); importance.to_csv(OUT/'feature_importance.csv',index=False)
    report(paired,importance,pd.DataFrame(order_rows))
    for path,sha in frozen.items():
        if digest(path)!=sha: raise ValueError(f'Input changed during diagnostics: {path}')
    summary={'status':'Completed exploratory historical permutation diagnostics; modern evaluation deferred at user request',
             'n_claims':len(test),'n_articles':test.page_id.nunique(),'source_validation':'not_performed','model_fits':0,
             'inputs_sha256':frozen,'code_sha256':digest(__file__),'versions':{'python':platform.python_version(),'torch':torch.__version__,'numpy':np.__version__,'pandas':pd.__version__},
             'outputs_sha256':{str(p):digest(p) for p in OUT.iterdir() if p.is_file() and p.name!='summary.json'}}
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(paired[paired.metric.eq('brier')].to_string(index=False))
    print(importance.to_string(index=False))


def report(paired,importance,order):
    html='''<!doctype html><html lang="en"><meta charset="utf-8"><title>RNN permutation diagnostics</title>
<style>body{font:16px/1.6 system-ui;max-width:1200px;margin:40px auto;padding:0 20px;color:#18343c}table{border-collapse:collapse;font-size:13px}td,th{padding:8px;border-bottom:1px solid #ddd}.table{overflow:auto}</style><main>
<h1>RNN permutation diagnostics</h1><p>Frozen historical models, 1995–2010. No model fits, source review, or modern results.</p>
<h2>Paired model comparison</h2><p>Positive improvement favors the first model. All 16 within-block swaps are enumerated across four five-year publication blocks. The smallest possible one-sided p-value is 0.0625. These conditional randomization results require blockwise model-label exchangeability; overlapping horizons and few eras limit that assumption. They are not label-permutation tests proving learning versus chance. Primary Brier comparisons receive a two-test Holm adjustment.</p>'''
    for title,frame in [('Brier comparisons',paired[paired.metric.eq('brier')]),('Monthly-input permutation importance',importance),('12-step sequence-order diagnostics',order)]:
        html+=f'<h2>{title}</h2><div class="table">'+frame.to_html(index=False,border=0,float_format=lambda x:f'{x:.5f}')+'</div>'
        if title.startswith('Monthly'):
            html+='<p>Positive Brier increase means damaging the input hurts the fitted model. Mean and quantiles use 23 nonidentity block rearrangements; quantiles are perturbation spread, not confidence intervals. The rank fraction includes identity and is descriptive, not a significance p-value. Whole 48-month origin blocks preserve season and full donor sequences, but can create unrealistic combinations with current-claim metadata. A value near zero does not prove the feature is irrelevant. Inspect joint permutations for correlated inputs.</p>'
    html+='''<p>Order perturbations keep all monthly values but change their ordering. They diagnose dependence on chronology, not whether recurrence beats an equally flexible nonrecurrent network. No modern claim has been evaluated.</p>
<p>Methods references: <a href="https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.permutation_test.html">SciPy paired permutation tests</a>; <a href="https://scikit-learn.org/stable/modules/permutation_importance">scikit-learn permutation importance</a>. Full choices are in specification.json, per-permutation metrics in the adjacent CSVs, and hashes in summary.json.</p></main></html>'''
    (OUT/'report.html').write_text(html)


if __name__=='__main__': main()
