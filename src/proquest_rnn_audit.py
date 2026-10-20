"""Audit saved ProQuest RNN predictions; never train, tune, or review sources."""
import hashlib
import json
from pathlib import Path
import platform

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

BASE = Path("data/scored/proquest")
SOURCE = BASE / "polarization"
OUT = BASE / "rnn_audit"
ARMS = ("baseline", "political", "forecast", "both")
COLORS = ("#555555", "#b36b25", "#167b85", "#7154a1")


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def attach_metadata(predictions, scored):
    if predictions.record_id.duplicated().any() or scored.record_id.duplicated().any():
        raise ValueError("Duplicate source-local addresses")
    columns = ["record_id", "page_id", "date", "hit", "topic", "paper", "horizon_basis",
               "horizon_used", "predicted_norm", "realized", "basis", "scorable"]
    result = predictions.merge(scored[columns], on="record_id", how="left", validate="one_to_one",
                               suffixes=("", "_score"), indicator=True)
    if not result._merge.eq("both").all():
        raise ValueError("Prediction without a score record")
    for field in ["page_id", "date", "hit"]:
        if not result[field].equals(result[field + "_score"]):
            # Numeric dtype differences are allowed, different values are not.
            if not result[field].eq(result[field + "_score"]).all():
                raise ValueError(f"Prediction/score mismatch: {field}")
    if not result.scorable.all() or result.basis.eq("NBER proxy").any():
        raise ValueError("Unexpected claim eligibility")
    return result.drop(columns=["_merge", "page_id_score", "date_score", "hit_score"])


def losses(y, p):
    return (p-y)**2, -(y*np.log(np.clip(p,1e-15,1))+(1-y)*np.log(np.clip(1-p,1e-15,1)))


def summarize(group, probability, weights):
    y, p = group.hit.to_numpy(), group[probability].to_numpy()
    brier, logloss = losses(y, p)
    confidence = np.maximum(p,1-p)
    correct = (p >= .5) == y
    high = confidence >= .9
    mean = lambda values: float(np.average(values,weights=weights))
    return {"n_claims":len(group), "n_articles":group.page_id.nunique(),
            "article_mass":float(np.sum(weights)), "hit_prevalence":mean(y),
            "mean_probability":mean(p), "brier":mean(brier), "log_loss":mean(logloss),
            "accuracy":mean(correct), "mean_confidence":mean(confidence),
            "high_confidence_claims":int(high.sum()),
            "high_confidence_article_mass":float(np.sum(weights[high])),
            "high_confidence_accuracy":float(np.average(correct[high],weights=weights[high])) if high.any() else np.nan,
            "high_confidence_wrong_mass_share":mean(high & ~correct)}


def comparison_rows(frame, grouping, global_mass):
    rows=[]
    for value,g in frame.groupby(grouping,dropna=False,observed=True):
        base,_=losses(g.hit.to_numpy(),g.gru_ensemble__baseline.to_numpy())
        for arm in ARMS:
            p=g[f"gru_ensemble__{arm}"].to_numpy()
            current,_=losses(g.hit.to_numpy(),p)
            gap=float(np.sum(g.weight.to_numpy()*(current-base)))
            rows.append({"grouping":grouping,"group":str(value),"arm":arm,
                         **summarize(g,f"gru_ensemble__{arm}",g.weight.to_numpy()),
                         "brier_increase_vs_baseline":gap/g.weight.sum(),
                         "contribution_to_total_brier_increase":gap/global_mass})
    return pd.DataFrame(rows)


def cohort_frames(frame):
    return [("all",frame),("1995_2006",frame[frame.year<=2006]),
            ("2007_2009",frame[frame.year.between(2007,2009)]),
            ("2010",frame[frame.year==2010]),
            ("outside_2007_2009",frame[~frame.year.between(2007,2009)])]


def selected_epoch(history):
    """Reproduce the saved validation-only improvement rule, not test selection."""
    best=np.inf; chosen=None
    for r in history.sort_values("epoch").itertuples():
        if r.validation_weighted_loss < best-.0001:
            best=r.validation_weighted_loss; chosen=int(r.epoch)
    return chosen


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    manifest=json.loads((SOURCE/"output_manifest.json").read_text())
    run=json.loads((SOURCE/"claims_summary.json").read_text())
    expected={**run["inputs_sha256"],**manifest["outputs_sha256"]}
    for name,sha in expected.items():
        if digest(name)!=sha:
            raise ValueError(f"Saved input changed: {name}")
    files={"predictions":SOURCE/"claims/test_predictions.csv.gz",
           "scores":BASE/"descriptive/scored_claims.csv.gz",
           "history":SOURCE/"claims/training_history.csv",
           "features":SOURCE/"features.csv",
           "preprocessing":SOURCE/"claims/added_preprocessing.csv",
           "splits":SOURCE/"claims/split_assignments.csv.gz"}
    expected.update({str(p):digest(p) for p in files.values()})
    frame=attach_metadata(pd.read_csv(files["predictions"]),pd.read_csv(files["scores"]))
    if not frame.year.between(1995,2010).all():
        raise ValueError("Unexpected evaluation years")
    probabilities=[c for c in frame if c.startswith("gru_")]
    if not np.isfinite(frame[probabilities]).all().all() or not ((frame[probabilities]>=0)&(frame[probabilities]<=1)).all().all():
        raise ValueError("Invalid saved probabilities")
    for arm in ARMS:
        mean=frame[[f"gru_seed_{s}__{arm}" for s in [11,29,47]]].mean(axis=1)
        np.testing.assert_allclose(mean,frame[f"gru_ensemble__{arm}"],atol=1e-7)
    frame["weight"]=1/frame.groupby("page_id").page_id.transform("size")
    mass=frame.weight.sum()
    frame["horizon_bucket"]=pd.cut(frame.horizon_used,[0,6,12,24],labels=["1–6","7–12","13–24"])
    frame["period"]=np.where(frame.year.between(2007,2009),"2007–2009",np.where(frame.year<=2006,"1995–2006","2010"))
    frame["period_topic"]=frame.period+" / "+frame.topic
    tables={g:comparison_rows(frame,g,mass) for g in ["year","period","topic","horizon_basis","horizon_bucket","paper","period_topic"]}
    totals=[];seeds=[];calibration=[];confidence=[]
    for scope,g in cohort_frames(frame):
        for arm in ARMS:
            totals.append({"scope":scope,"arm":arm,**summarize(g,f"gru_ensemble__{arm}",g.weight.to_numpy())})
            for seed in [11,29,47]:
                current=summarize(g,f"gru_seed_{seed}__{arm}",g.weight.to_numpy())
                base=summarize(g,f"gru_seed_{seed}__baseline",g.weight.to_numpy())
                seeds.append({"scope":scope,"arm":arm,"seed":seed,**current,
                              "brier_increase_vs_same_seed_baseline":current["brier"]-base["brier"]})
            p=g[f"gru_ensemble__{arm}"].to_numpy();y=g.hit.to_numpy();w=g.weight.to_numpy()
            for bucket in range(10):
                mask=np.minimum((p*10).astype(int),9)==bucket
                if mask.any():
                    calibration.append({"scope":scope,"arm":arm,"bin":bucket,"n_claims":int(mask.sum()),
                                        "article_mass":float(w[mask].sum()),
                                        "mean_probability":np.average(p[mask],weights=w[mask]),
                                        "observed_hit_rate":np.average(y[mask],weights=w[mask])})
            for outcome in [0,1]:
                mask=y==outcome
                confidence.append({"scope":scope,"arm":arm,"actual_hit":outcome,
                                   "n_claims":int(mask.sum()),"article_mass":float(w[mask].sum()),
                                   "mean_probability":np.average(p[mask],weights=w[mask]) if mask.any() else np.nan})
    tables.update(cohorts=pd.DataFrame(totals),seeds=pd.DataFrame(seeds),calibration=pd.DataFrame(calibration),probability_by_outcome=pd.DataFrame(confidence))
    history=pd.read_csv(files["history"]);epochs=[]
    for (arm,seed),h in history.groupby(["arm","seed"]):
        epoch=selected_epoch(h);r=h[h.epoch.eq(epoch)].iloc[0]
        epochs.append({"arm":arm,"seed":int(seed),"selected_epoch":epoch,
                       "epochs_run":len(h),"train_log_loss":r.train_weighted_loss,
                       "validation_log_loss":r.validation_weighted_loss})
    tables["selected_epochs"]=pd.DataFrame(epochs)
    feature=pd.read_csv(files["features"])
    feature["month"]=feature.origin
    frame["month"]=frame.date.str[:7]
    merged=frame.merge(feature,on="month",how="left",validate="many_to_one")
    preprocessing=pd.read_csv(files["preprocessing"])
    shifts=[]
    for scope,g in cohort_frames(merged):
        for field,arm in [("political_polarization","political"),("forecast_polarization","forecast")]:
            row=preprocessing[preprocessing.arm.eq(arm)&preprocessing.feature.eq(field)].iloc[0]
            observed=g[field].notna();z=(g[field]-row["mean"])/row.scale
            shifts.append({"scope":scope,"feature":field,"train_mean":row["mean"],"train_scale":row.scale,
                           "observed_claims":int(observed.sum()),"observed_months":g.loc[observed,"month"].nunique(),
                           "article_weighted_mean":np.average(g.loc[observed,field],weights=g.loc[observed,"weight"]),
                           "mean_training_z":np.average(z[observed],weights=g.loc[observed,"weight"]),
                           "mass_outside_3_training_sd":g.loc[z.abs()>3,"weight"].sum()/g.weight.sum()})
    tables["feature_shift"]=pd.DataFrame(shifts)
    # Contributions retain original full-test article weights, so every partition adds up.
    overall=tables["cohorts"].query("scope == 'all'").set_index("arm")
    for grouping in ["year","period","topic","horizon_basis","horizon_bucket","paper","period_topic"]:
        for arm in ARMS:
            actual=tables[grouping].query("arm == @arm").contribution_to_total_brier_increase.sum()
            np.testing.assert_allclose(actual,overall.loc[arm,"brier"]-overall.loc["baseline","brier"],atol=1e-12)
    # Reconcile with the already reported metrics without refitting.
    old=pd.read_csv(SOURCE/"claims_metrics.csv").query("model == 'gru_ensemble' and scope == 'overall'").set_index("arm")
    for metric in ["brier","log_loss","accuracy"]:
        np.testing.assert_allclose(overall.loc[list(ARMS),metric],old.loc[list(ARMS),metric],atol=1e-8)
    for name,table in tables.items():
        table.to_csv(OUT/f"{name}.csv",index=False)
    figures(tables)
    report(tables)
    for name,sha in expected.items():
        if digest(name)!=sha: raise ValueError(f"Input changed during audit: {name}")
    outputs={str(p):digest(p) for p in OUT.iterdir() if p.is_file() and p.name!="summary.json"}
    summary={"prepared_date":"2026-10-19","status":"Exploratory audit of saved predictions; no fits, no source review",
             "n_claims":len(frame),"n_articles":frame.page_id.nunique(),"inputs_sha256":expected,
             "outputs_sha256":outputs,"code_sha256":digest(__file__),"python":platform.python_version(),
             "weighting":"Each test article has total weight one. Subgroups retain these weights; contributions divide by full-test article mass.",
             "checks":{"ensemble_means":True,"scores_join_one_to_one":True,"saved_metrics_reconciled":True,"contributions_add_up":True}}
    (OUT/"summary.json").write_text(json.dumps(summary,indent=2)+"\n")
    print(tables["cohorts"][["scope","arm","brier","accuracy","mean_probability","hit_prevalence"]].to_string(index=False))
    print(OUT/"report.html")


def figures(tables):
    fig,axes=plt.subplots(2,1,figsize=(11,7),sharex=True)
    for arm,color in zip(ARMS,COLORS):
        d=tables["year"].query("arm == @arm");x=d.group.astype(int)
        axes[0].plot(x,d.brier,label=arm,color=color)
        axes[1].plot(x,d.brier_increase_vs_baseline,label=arm,color=color)
    for ax in axes: ax.axvspan(2006.5,2009.5,color="#dddddd",alpha=.5);ax.grid(alpha=.2)
    axes[0].set_ylabel("Binary Brier loss");axes[0].legend(ncol=4,frameon=False)
    axes[1].set_ylabel("Brier increase vs baseline");axes[1].axhline(0,color="black",lw=.6)
    axes[0].set_title("RNN performance by publication year; equal total weight per article")
    fig.tight_layout();fig.savefig(OUT/"yearly_performance.png",dpi=160);plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(11,4.5))
    for ax,scope in zip(axes,["2007_2009","outside_2007_2009"]):
        for arm,color in zip(ARMS,COLORS):
            d=tables["calibration"].query("scope == @scope and arm == @arm")
            ax.plot(d.mean_probability,d.observed_hit_rate,"o-",color=color,label=arm,markersize=3)
        ax.plot([0,1],[0,1],"--",color="#999");ax.set(xlim=(0,1),ylim=(0,1),title=scope.replace("_"," "),xlabel="Predicted correctness",ylabel="Observed correctness")
    axes[0].legend(frameon=False)
    fig.suptitle("Calibration of saved RNN ensembles; counts and article mass in calibration.csv")
    fig.tight_layout();fig.savefig(OUT/"calibration.png",dpi=160);plt.close(fig)


def report(tables):
    def table(d):return '<div class="table">'+d.to_html(index=False,border=0,float_format=lambda v:f"{v:.4f}")+'</div>'
    body=["<h1>RNN error and stability audit</h1>",
          "<p>Saved predictions only: no training, tuning, source validation or modern scoring. This audit examines 56,807 test claims from 1995–2010 under legacy deterministic scoring rules.</p>",
          "<p>Political polarization alone hurts the 2007–2009 cohort across all three training seeds. Its deterioration is not an increase in ≥90%-confidence errors. Both features together behave differently: their ensemble improves during 2007–2009 but worsens outside those years. These comparisons cannot identify causal effects or uniquely separate added features from neural training variation.</p>",
          "<p>Each test article retains total weight one. Subgroup rates use the original article weights; they are not reweighted to equal articles within each subgroup. Contributions are weighted loss differences divided by full-test article mass and add exactly to the overall change. Positive increases mean worse performance. The 2007–2009 label identifies publication years, not every claim’s outcome window.</p>",
          '<img src="yearly_performance.png" alt="Annual RNN Brier scores and changes against baseline">',
          "<h2>Period results</h2>",table(tables["cohorts"][["scope","arm","n_claims","n_articles","brier","accuracy","mean_probability","hit_prevalence","high_confidence_claims","high_confidence_wrong_mass_share"]]),
          "<h2>Where the overall difference comes from</h2>",table(tables["period_topic"].query("arm == 'political'")[["group","article_mass","brier_increase_vs_baseline","contribution_to_total_brier_increase"]]),
          "<h2>Calibration</h2>",'<img src="calibration.png" alt="Calibration inside and outside 2007–2009">',
          "<p>High confidence means max(p, 1−p) ≥ 0.9. Low frequency of very confident mistakes does not establish good calibration or discrimination. Calibration bins have different sample support; inspect their counts before interpreting the curves.</p>",
          "<h2>Seed stability</h2>",table(tables["seeds"].query("scope in ['all','2007_2009'] and arm != 'baseline'")[["scope","arm","seed","brier","brier_increase_vs_same_seed_baseline"]]),
          "<p>All three seeds are retained. Matching a seed does not make neural initialization identical after changing input dimensions. These are descriptive stability checks, not independent replications or estimates of the causal contribution of each feature.</p>",
          "<h2>Supplementary tables</h2>",
          "<p>Annual, topic, newspaper, numeric-horizon bucket, exported horizon basis, period-by-topic contributions, feature shifts, confidence by actual outcome, and validation-selected epochs are exported alongside this report. Numeric or ‘stated’ exported horizons remain machine labels, not source-validated explicit horizons.</p>",
          "<p>Existing paired intervals remain in <a href='../polarization/claims_paired_intervals.csv'>the polarization results</a>. Only four five-year test blocks are available; the 2007–2009 subset does not provide enough independent eras for a precise block interval. No new significance claim is inferred from these subgroup tables. They do not justify another round of tuning on the same test years.</p>"]
    head='<!doctype html><html lang="en"><meta charset="utf-8"><title>RNN error audit</title><meta name="viewport" content="width=device-width, initial-scale=1"><style>body{font:16px/1.6 system-ui;max-width:1150px;margin:40px auto;padding:0 24px;color:#19313c}img{width:100%}.table{overflow:auto}table{border-collapse:collapse;font-size:13px}td,th{padding:7px;border-bottom:1px solid #ddd;text-align:right}h2{margin-top:36px}</style><main>'
    (OUT/"report.html").write_text(head+"\n".join(body)+"</main></html>")


if __name__=="__main__":main()
