"""Descriptive follow-ups using only annual machine-verified ProQuest claims.

Reuses the documented outcome scores, validates them against the original
verified exports, and writes a separate report. No fitted ML models.
"""
import argparse
import base64
import hashlib
import html
from itertools import combinations
import json
from pathlib import Path
import re
import unicodedata

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from analyze_proquest import annual_files
from proquest_descriptive import add_comparisons, horizon, paper_name, predicted_norm

SOURCE = Path("data/scored/proquest/descriptive")
OUT = Path("data/scored/proquest/followups")
CELL_KEYS = ["year", "topic", "basis", "horizon_basis", "horizon_bucket"]


def speaker_key(value):
    text = unicodedata.normalize("NFKC", str(value or "")).casefold().strip()
    if text in {"", "na", "n/a", "none", "unknown", "unclear", "nan"}:
        return None
    # Conservative spelling normalization only. Do not merge surname-only,
    # initials, titles or similar-looking names without source evidence.
    normalized = re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", text)).strip()
    return None if normalized.replace(' ', '') in {'', 'na', 'none', 'unknown', 'unclear', 'nan'} else normalized


def load_claims(source=SOURCE):
    frame = pd.read_csv(source / "scored_claims.csv.gz", dtype={"page_id": str})
    metadata = json.loads((source / "summary.json").read_text())
    if metadata["input_directory"] != "data/proquest/verified":
        raise ValueError("Outcome scores did not come from the verified ProQuest set")
    rows, digests = [], {}
    for path in annual_files("data/proquest/verified"):
        digests[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
        year = int(path.name.split('_')[-1].split('.')[0])
        with path.open() as source_file:
            for number, line in enumerate(source_file, 1):
                if not line.strip():
                    continue
                row = json.loads(line)
                if row.get("no_predictions"):
                    continue
                if row.get("source") != "proquest" or row.get("schema_version") != 2 or "verify_reason" not in row:
                    raise ValueError(f"Unverified/non-ProQuest row in {path}:{number}")
                months, horizon_basis, _ = horizon(row)
                rows.append({"record_id": f"{year}:{number}", "page_id_source": str(row["page_id"]),
                             "date_source": row["date"], "topic_source": row["topic"],
                             "scope_source": row["scope"], "direction_source": row["direction"],
                             "paper_source": paper_name(row.get("publisher") or row.get("newspaper_title")),
                             "voice_source": row.get('voice'), "confidence_source": row.get('confidence'),
                             "horizon_used_source": months, "horizon_basis_source": horizon_basis,
                             "predicted_norm_source": predicted_norm(row),
                             "speaker_name": row.get("speaker_name")})
    original = pd.DataFrame(rows)
    if set(frame.record_id) != set(original.record_id):
        raise ValueError("Saved scores do not contain exactly the current verified claims")
    frame = frame.merge(original, on="record_id", validate="one_to_one")
    for key in ["page_id", "date", "topic", "scope", "direction", "paper", 'voice', 'confidence',
                'horizon_basis', 'predicted_norm']:
        if not frame[key].fillna('<missing>').astype(str).eq(frame[f"{key}_source"].fillna('<missing>').astype(str)).all():
            raise ValueError(f"Saved scores differ from the verified exports: {key}")
    if not frame.horizon_used.fillna(-1).eq(frame.horizon_used_source.fillna(-1)).all():
        raise ValueError('Saved scores differ from verified exports: horizon_used')
    frame = frame.drop(columns=[c for c in frame if c.endswith('_source')])
    frame["date"] = pd.to_datetime(frame.date)
    frame["month"] = frame.date.dt.to_period("M")
    frame["speaker_key"] = frame.speaker_name.map(speaker_key)
    frame["horizon_bucket"] = pd.cut(frame.horizon_used, [0, 6, 12, 24], labels=["1–6", "7–12", "13–24"]).astype(str)
    for ref in metadata["reference"].values():
        if hashlib.sha256(Path(ref["file"]).read_bytes()).hexdigest() != ref["sha256"]:
            raise ValueError(f"Reference file changed since scoring: {ref['file']}")
    return frame, metadata, digests


def confusion_metrics(group):
    warning, decline = group.predicted_norm.eq("worsen"), group.realized.eq("worsen")
    tp, fp = int((warning & decline).sum()), int((warning & ~decline).sum())
    fn, tn = int((~warning & decline).sum()), int((~warning & ~decline).sum())
    divide = lambda a, b: a / b if b else np.nan
    return {"n_claims": len(group), "n_articles": group.page_id.nunique(),
            "true_warnings": tp, "false_alarms": fp, "missed_declines": fn, "true_nonwarnings": tn,
            "actual_decline_share": divide(tp + fn, len(group)),
            "warning_share": divide(tp + fp, len(group)),
            "warning_precision": divide(tp, tp + fp),
            "decline_recall": divide(tp, tp + fn),
            "miss_rate": divide(fn, tp + fn), "false_alarm_rate": divide(fp, fp + tn),
            "optimistic_among_actual_declines": divide(int((group.predicted_norm.eq('improve') & decline).sum()), tp + fn),
            "false_alarms_followed_by_growth": int((warning & group.realized.eq('improve')).sum()),
            "false_alarms_followed_by_flat": int((warning & group.realized.eq('flat')).sum())}


def failure_tables(scored):
    # Production changes are not NBER recession starts: keep the targets apart.
    production = scored[(scored.topic == "general_business") & (scored.basis == "INDPRO")]
    by_paper = pd.DataFrame([{"paper": paper, **confusion_metrics(group)}
                             for paper, group in production.groupby("paper")])
    by_decade = pd.DataFrame([{"decade": decade, **confusion_metrics(group)}
                              for decade, group in production.groupby("decade")])
    overall = pd.DataFrame([{"subset": "Production, all eligible horizons", **confusion_metrics(production)},
                            {"subset": "Production, claim-grounded horizons", **confusion_metrics(production[production.horizon_basis != 'default'])}])
    matrix = pd.crosstab(production.predicted_norm, production.realized).reindex(
        index=["improve", "flat", "worsen"], columns=["improve", "flat", "worsen"], fill_value=0)
    return production, overall, by_paper, by_decade, matrix


def recession_starts(series):
    return series.index[(series == 1) & (series.shift(1) == 0)]


def assign_events(frame, starts, before=24, after=12):
    """Nearest eligible onset; each forecast enters at most one onset study."""
    frame = frame.copy()
    ordinals = np.array([m.ordinal for m in frame.month])
    offsets = ordinals[:, None] - np.array([m.ordinal for m in starts])[None, :]
    eligible = (offsets >= -before) & (offsets <= after)
    distances = np.where(eligible, abs(offsets), np.inf)
    best = distances.argmin(axis=1)
    ok = np.isfinite(distances[np.arange(len(frame)), best])
    frame = frame.loc[ok].copy()
    best = best[ok]
    frame["onset"] = [str(starts[i]) for i in best]
    frame["relative_month"] = offsets[ok, :][np.arange(len(best)), best]
    return frame


def warning_timing(claims, rec):
    starts = recession_starts(rec)
    starts = starts[(starts >= pd.Period('1900-01', 'M')) & (starts <= pd.Period('2010-12', 'M'))]
    # Timing needs a readable direction, not an outcome-scoring horizon.
    business = claims[(claims.scope == "national") & (claims.topic == "general_business") &
                      claims.direction.isin(["improve", "worsen"])].copy()
    business["warning"] = business.direction.eq("worsen").astype(float)
    events = assign_events(business, starts)
    monthly = events.groupby(["onset", "relative_month"]).agg(
        warning_share=("warning", "mean"), n_claims=("warning", "size"), n_articles=("page_id", "nunique"))
    article = events.groupby(["onset", "relative_month", "page_id"]).warning.mean()
    monthly["article_equal_warning_share"] = article.groupby(level=[0, 1]).mean()
    panel = monthly.reset_index()
    adequate = panel[panel.n_claims >= 10]
    curve = adequate.groupby("relative_month").agg(
        event_equal_warning_share=("warning_share", "mean"), n_events=("onset", "size"),
        n_claims=("n_claims", "sum"), article_equal_event_share=("article_equal_warning_share", "mean")).reset_index()
    events["phase"] = pd.cut(events.relative_month, [-25, -13, -7, -1, 5, 12],
                             labels=["13–24 months before", "7–12 months before", "1–6 months before", "0–5 months after", "6–12 months after"])
    # Pre-onset comparisons are during expansion; after-onset comparisons are
    # during recession. Prevent the 1980/1981 overlap masquerading as foresight.
    clean = events[((events.relative_month < 0) & (events.recession_at_print == 0)) |
                   ((events.relative_month >= 0) & (events.recession_at_print == 1))]
    phases = clean.groupby(["onset", "phase"], observed=True).agg(
        warning_share=("warning", "mean"), n_claims=("warning", "size"), n_articles=("page_id", "nunique")).reset_index()
    needed = ["7–12 months before", "1–6 months before", "0–5 months after"]
    counts = phases.pivot(index="onset", columns="phase", values="n_claims").reindex(columns=needed).fillna(0)
    matched = counts.index[(counts >= 30).all(axis=1)]
    paired = phases[phases.onset.isin(matched) & phases.phase.isin(needed)]
    matched_summary = paired.groupby("phase", observed=True).agg(
        event_equal_warning_share=("warning_share", "mean"), n_events=("onset", "size"), n_claims=("n_claims", "sum")).reset_index()
    matched_summary["phase"] = matched_summary.phase.astype(str)
    return events, panel, curve, phases, matched_summary, [str(m) for m in starts]


def historical_consensus(scored, minimum=20, minimum_papers=2, dominance=.6):
    """Other-paper predictions in [date-90 days, date), never future/same-day."""
    result = scored.copy()
    result["consensus"] = "Insufficient peers"
    result["peer_majority"] = None
    result["prior_peer_claims"] = 0
    result["prior_peer_papers"] = 0
    result["peer_dominance"] = np.nan
    keys = ["topic", "basis", "horizon_basis", "horizon_bucket"]
    for _, group in result.groupby(keys, observed=True):
        papers = sorted(group.paper.unique())
        directions = sorted(group.predicted_norm.unique())
        columns = pd.MultiIndex.from_product([papers, directions], names=["paper", "predicted_norm"])
        daily = group.groupby(["date", "paper", "predicted_norm"]).size().unstack(["paper", "predicted_norm"], fill_value=0)
        daily = daily.reindex(columns=columns, fill_value=0).sort_index()
        history = daily.rolling("90D", closed="left").sum().fillna(0)
        totals = pd.DataFrame({d: history.xs(d, axis=1, level="predicted_norm").sum(axis=1) for d in directions})
        per_paper = pd.DataFrame({p: history.xs(p, axis=1, level="paper").sum(axis=1) for p in papers})
        for paper, own in group.groupby("paper"):
            other = totals - history.xs(paper, axis=1, level="paper").reindex(columns=directions)
            n = other.sum(axis=1)
            n_papers = (per_paper > 0).sum(axis=1) - (per_paper[paper] > 0).astype(int)
            majority = other.idxmax(axis=1)
            strength = (other.max(axis=1) / n).where(n > 0)
            own_counts = n.reindex(own.date).to_numpy()
            own_papers = n_papers.reindex(own.date).to_numpy()
            own_strength = strength.reindex(own.date).to_numpy()
            own_majority = majority.reindex(own.date).to_numpy()
            enough = (own_counts >= minimum) & (own_papers >= minimum_papers)
            clear = enough & (own_strength >= dominance)
            category = np.where(~enough, "Insufficient peers", np.where(~clear, "No clear consensus",
                                np.where(own.predicted_norm.to_numpy() == own_majority, "Agrees with prior consensus", "Contrarian")))
            result.loc[own.index, "consensus"] = category
            result.loc[own.index, "peer_majority"] = np.where(clear, own_majority, None)
            result.loc[own.index, "prior_peer_claims"] = own_counts.astype(int)
            result.loc[own.index, "prior_peer_papers"] = own_papers.astype(int)
            result.loc[own.index, "peer_dominance"] = own_strength
    return result


def matched_pair(frame, category, left, right, keys, minimum=10):
    """Shared cell comparison, using the same overlap weights for both groups."""
    eligible = frame[frame[category].isin([left, right])]
    cells = eligible.groupby(keys + [category], observed=True).agg(
        hit_rate=("hit", "mean"), n=("hit", "size"), baseline=("fixed_baseline_hit", "mean")).unstack(category)
    if left not in cells["n"] or right not in cells["n"]:
        return {}, pd.DataFrame()
    cells = cells[(cells["n"][left] >= minimum) & (cells["n"][right] >= minimum)]
    if cells.empty:
        return {}, pd.DataFrame()
    weight = 2 * cells["n"][left] * cells["n"][right] / (cells["n"][left] + cells["n"][right])
    paired = cells.index.to_frame(index=False)
    for label, value in [("weight", weight), ("left_hit_rate", cells["hit_rate"][left]),
                         ("right_hit_rate", cells["hit_rate"][right]), ("left_baseline", cells["baseline"][left]),
                         ("right_baseline", cells["baseline"][right])]:
        paired[label] = value.to_numpy()
    gap = paired.left_hit_rate - paired.right_hit_rate
    baseline_gap = paired.left_baseline - paired.right_baseline
    avg = lambda v: np.average(v, weights=weight)
    result = {"left": left, "right": right, "n_cells": len(cells),
              "left_claims_in_cells": int(cells["n"][left].sum()), "right_claims_in_cells": int(cells["n"][right].sum()),
              "left_matched_hit_rate": avg(paired.left_hit_rate), "right_matched_hit_rate": avg(paired.right_hit_rate),
              "matched_gap": avg(gap), "baseline_gap": avg(baseline_gap), "gap_beyond_baseline": avg(gap - baseline_gap)}
    if "year" in paired:
        blocks = paired.assign(block=paired.year // 5, weighted_gap=paired.weight * gap)
        sums = blocks.groupby("block")[["weight", "weighted_gap"]].sum()
        result["n_time_blocks"] = len(sums)
        if len(sums) >= 4:
            draws = np.random.default_rng(20260916).integers(0, len(sums), (1500, len(sums)))
            ratios = sums.weighted_gap.to_numpy()[draws].sum(axis=1) / sums.weight.to_numpy()[draws].sum(axis=1)
            result["block_ci_low"], result["block_ci_high"] = np.quantile(ratios, [.025, .975])
    return result, paired


def rate_table(frame, keys):
    return frame.groupby(keys, observed=True).agg(
        n_claims=("hit", "size"), n_articles=("page_id", "nunique"), hit_rate=("hit", "mean"),
        fixed_baseline=("fixed_baseline_hit", "mean"), peer_adjusted_gap=("peer_adjusted_gap", "mean")).reset_index()


def speaker_table(scored):
    named = scored[scored.speaker_key.notna()]
    result = named.groupby("speaker_key").agg(n_claims=("hit", "size"), n_articles=("page_id", "nunique"),
        n_papers=("paper", "nunique"), n_years=("year", "nunique"), first_year=("year", "min"), last_year=("year", "max"))
    display = named.groupby("speaker_key").speaker_name.agg(lambda names: names.value_counts().index[0])
    result.insert(0, "speaker", display)
    result["adequate_coverage"] = (result.n_claims >= 100) & (result.n_papers >= 2) & (result.n_years >= 5)
    return result.reset_index().sort_values("speaker_key")


def disagreement_table(consensus, rec):
    """Retrospective diagnostic; onset labels never enter consensus construction."""
    frame = consensus[(consensus.topic == 'general_business') & (consensus.basis == 'INDPRO') &
                      (consensus.recession_at_print == 0) & (consensus.prior_peer_claims >= 20) &
                      (consensus.prior_peer_papers >= 2)].copy()
    starts = np.array([m.ordinal for m in recession_starts(rec)])
    month_ordinals = np.array([m.ordinal for m in frame.month])
    future = starts[None, :] - month_ordinals[:, None]
    frame['recession_within_12_months'] = ((future > 0) & (future <= 12)).any(axis=1)
    frame['production_decline'] = frame.realized.eq('worsen')
    frame['prior_agreement'] = pd.cut(frame.peer_dominance, [0, .6, .75, 1.],
                                      labels=['At most 60%', '60–75%', 'Above 75%'], include_lowest=True)
    result = frame.groupby('prior_agreement', observed=True).agg(
        n_claims=('hit', 'size'), n_months=('month', 'nunique'),
        recession_within_12_months_share=('recession_within_12_months', 'mean'),
        production_decline_share=('production_decline', 'mean'))
    monthly = frame.groupby(['prior_agreement', 'month'], observed=True).recession_within_12_months.mean()
    result['month_equal_recession_share'] = monthly.groupby(level=0, observed=True).mean()
    return result.reset_index()


def make_charts(out, failure, curve, specialties, horizon_table, consensus, ranks, decade_table):
    plt.rcParams.update({"font.size": 10, "font.family": "DejaVu Sans", "axes.spines.top": False, "axes.spines.right": False})
    files = []
    def save(fig, name):
        fig.tight_layout(); fig.savefig(out / name, dpi=160, bbox_inches="tight"); plt.close(fig); files.append(name)
    view = failure[failure.n_claims >= 500].sort_values("decline_recall")
    fig, axes = plt.subplots(1, 2, figsize=(11, 5.5))
    axes[0].barh(view.paper, view.decline_recall * 100, color="#174e70")
    axes[1].barh(view.paper, view.warning_precision * 100, color="#d47835")
    axes[0].set_xlabel("Share of actual output declines warned about (%)")
    axes[1].set_xlabel("Share of warnings followed by output decline (%)")
    for ax in axes: ax.set_xlim(0, 100); ax.grid(axis='x', alpha=.15)
    fig.suptitle("Catching output declines and avoiding false alarms are different", fontsize=13)
    save(fig, "false_alarms_and_misses.png")
    fig, axes = plt.subplots(2, 1, figsize=(10, 6.8), sharex=True, gridspec_kw={"height_ratios": [3, 1]})
    axes[0].plot(curve.relative_month, curve.event_equal_warning_share * 100, 'o-', color='#174e70', label='Equal weight to each adequately sampled recession')
    axes[0].plot(curve.relative_month, curve.article_equal_event_share * 100, '--', color='#738b32', label='Equal weight to articles within each event-month')
    axes[0].set_ylabel('Business forecasts predicting worsening (%)'); axes[0].legend(fontsize=8)
    axes[0].set_title('Did warnings rise before recessions, or after they began?')
    axes[1].bar(curve.relative_month, curve.n_events, color='#8aabbf'); axes[1].set_ylabel('Events'); axes[1].set_xlabel('Months relative to first recession month')
    for ax in axes: ax.axvline(0, color='#d47835', linestyle='--'); ax.grid(alpha=.15)
    save(fig, 'warning_timing.png')
    fig, ax = plt.subplots(figsize=(10, 5.2))
    heat = specialties[specialties.n_claims >= 200].pivot(index='paper', columns='topic', values='hit_rate')
    heat = heat.reindex(columns=['general_business', 'markets', 'prices', 'employment'])
    im = ax.imshow(heat, vmin=.25, vmax=.60, cmap='YlGnBu', aspect='auto')
    ax.set_xticks(range(len(heat.columns)), [c.replace('_', ' ').title() for c in heat.columns]); ax.set_yticks(range(len(heat)), heat.index)
    for i in range(len(heat)):
        for j in range(len(heat.columns)):
            value = heat.iloc[i, j]
            if pd.notna(value): ax.text(j, i, f'{value:.1%}', ha='center', va='center', color='white' if value > .47 else '#16364b')
    ax.set_title('Publisher specialties: raw hit rates (at least 200 claims per cell)'); fig.colorbar(im, ax=ax, label='Hit rate')
    save(fig, 'publisher_specialties.png')
    fig, ax = plt.subplots(figsize=(10, 4.8))
    bands = ['1–3', '4–6', '7–12', '13–24']
    for topic, group in horizon_table.groupby('topic'):
        group = group[group.n_claims >= 100].copy()
        ax.plot(group.horizon_band.astype(str).map(dict(zip(bands, range(4)))), group.hit_rate * 100, 'o-', label=topic.replace('_', ' ').title())
    ax.set_xticks(range(4), bands)
    ax.set_ylabel('Correct forecasts (%)'); ax.set_xlabel('Stated forecast horizon (months)'); ax.set_title('Horizon patterns differ by topic; default horizons excluded')
    ax.legend(fontsize=9); ax.grid(alpha=.15); save(fig, 'forecast_horizons.png')
    view = consensus.set_index('consensus').reindex(['Agrees with prior consensus', 'Contrarian', 'No clear consensus']).dropna(subset=['hit_rate'])
    fig, ax = plt.subplots(figsize=(9, 4.6))
    ax.barh(view.index, view.hit_rate * 100, color='#174e70')
    for i, row in enumerate(view.itertuples()): ax.text(row.hit_rate * 100 + .6, i, f'{row.hit_rate:.1%} · n={row.n_claims:,}', va='center', fontsize=9)
    ax.set_xlim(0, 80); ax.set_xlabel('Correct forecasts (%)'); ax.set_title('Agreement with strictly earlier other-paper forecasts')
    save(fig, 'consensus.png')
    fig, ax = plt.subplots(figsize=(10, 5.1))
    view = ranks.sort_values('mean_pairwise_matched_gap')
    ax.barh(view.paper, view.mean_pairwise_matched_gap * 100, color=np.where(view.mean_pairwise_matched_gap >= 0, '#174e70', '#d47835'))
    ax.axvline(0, color='#778'); ax.set_xlabel('Mean gap across matched pairwise comparisons (percentage points)')
    ax.set_title('A coverage-adjusted publisher comparison, without ML'); ax.grid(axis='x', alpha=.15)
    save(fig, 'matched_publishers.png')
    fig, ax = plt.subplots(figsize=(11, 5.2))
    heat = decade_table[decade_table.n_claims >= 500].pivot(index='paper', columns='decade', values='peer_adjusted_gap')
    im = ax.imshow(heat * 100, cmap='RdBu', vmin=-8, vmax=8, aspect='auto')
    ax.set_xticks(range(len(heat.columns)), heat.columns, rotation=45); ax.set_yticks(range(len(heat)), heat.index)
    for i in range(len(heat)):
        for j in range(len(heat.columns)):
            if pd.notna(heat.iloc[i, j]): ax.text(j, i, f'{heat.iloc[i,j]*100:+.1f}', ha='center', va='center', fontsize=8)
    ax.set_title('Publisher advantages vary across decades (at least 500 claims per cell)')
    fig.colorbar(im, ax=ax, label='Gap versus comparable other-paper forecasts (pp)'); save(fig, 'publisher_stability.png')
    return files


def write_report(out, sections, figures, facts):
    text = ['# ProQuest descriptive follow-ups', '',
            'Annual machine-verified ProQuest claims only. No LOC analysis, old crisis-window files, or ML models.', '']
    blocks = ['<h1>ProQuest descriptive follow-ups</h1>', '<p>Annual machine-verified ProQuest claims only. No ML analysis.</p>']
    for heading, paragraphs, tables, image_names in sections:
        text += [f'## {heading}', '']
        blocks += [f'<h2>{html.escape(heading)}</h2>']
        for paragraph in paragraphs:
            text += [paragraph, '']; blocks += [f'<p>{html.escape(paragraph)}</p>']
        for name in image_names:
            encoded = base64.b64encode((out / name).read_bytes()).decode()
            blocks += [f'<img alt="{html.escape(name.replace("_", " "))}" src="data:image/png;base64,{encoded}">']
        for caption, table in tables:
            text += [caption, '']
            display = table.copy()
            for col in display:
                if pd.api.types.is_numeric_dtype(display[col]):
                    if any(s in col for s in ['rate', 'share', 'precision', 'recall', 'gap', 'baseline']):
                        display[col] = display[col].map(lambda v: '—' if pd.isna(v) else f'{v:.1%}')
                    else:
                        display[col] = display[col].map(lambda v: '—' if pd.isna(v) else f'{v:,.0f}')
            text += ['| ' + ' | '.join(display.columns) + ' |', '| ' + ' | '.join(['---'] * len(display.columns)) + ' |']
            text += ['| ' + ' | '.join(str(v) for v in row) + ' |' for row in display.itertuples(index=False, name=None)]
            text += ['']
            blocks += [f'<p><strong>{html.escape(caption)}</strong></p>', '<div class="table">' + display.to_html(index=False, escape=True, border=0) + '</div>']
    (out / 'report.md').write_text('\n'.join(text) + '\n')
    style = 'body{font:16px system-ui,sans-serif;line-height:1.55;color:#17364b;max-width:1100px;margin:40px auto;padding:0 24px}h1{font-size:32px}h2{margin-top:42px}img{width:100%;margin:18px 0}.table{overflow-x:auto}table{border-collapse:collapse;font-size:13px;width:100%}th,td{padding:8px;border-bottom:1px solid #dce5ec;text-align:right}td:first-child,th:first-child{text-align:left}th{background:#f1f5f8}'
    (out / 'report.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><title>ProQuest descriptive follow-ups</title><style>'+style+'</style><body>'+''.join(blocks)+'</body></html>')
    (out / 'summary.json').write_text(json.dumps(facts, indent=2, default=lambda v: v.item() if isinstance(v, np.generic) else str(v)) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=OUT)
    args = parser.parse_args(); out = args.out; out.mkdir(parents=True, exist_ok=True)
    claims, metadata, digests = load_claims()
    scored = add_comparisons(claims[claims.scorable].copy())
    print(f'Validated {len(claims):,} verified claims; {len(scored):,} outcome-scored claims.', flush=True)
    production, failure, failure_papers, failure_decades, matrix = failure_tables(scored)
    rec_frame = pd.read_csv('data/reference/proquest/fred_USREC.csv')
    rec = pd.Series(rec_frame.iloc[:, 1].to_numpy(), index=pd.PeriodIndex(pd.to_datetime(rec_frame.iloc[:, 0]), freq='M'))
    events, panel, curve, phases, timing, starts = warning_timing(claims, rec)
    print(f'Warning timing: {len(events):,} directional business forecasts; {len(starts)} recession starts.', flush=True)
    consensus_claims = historical_consensus(scored)
    consensus = rate_table(consensus_claims, ['consensus'])
    consensus_pair, consensus_cells = matched_pair(consensus_claims, 'consensus', 'Agrees with prior consensus', 'Contrarian',
        ['paper', 'year', 'month', 'topic', 'basis', 'horizon_basis', 'horizon_used'], minimum=5)
    consensus_decades = rate_table(consensus_claims, ['decade', 'consensus'])
    disagreement = disagreement_table(consensus_claims, rec)
    print('Prior-only consensus comparisons finished.', flush=True)
    stated = scored[scored.horizon_basis == 'stated'].copy()
    stated['horizon_band'] = pd.cut(stated.horizon_used, [0, 3, 6, 12, 24], labels=['1–3', '4–6', '7–12', '13–24'])
    horizons = rate_table(stated, ['topic', 'horizon_band'])
    horizon_pair, _ = matched_pair(stated, 'horizon_used', 6., 12., ['paper', 'year', 'topic', 'basis'])
    specialties = rate_table(scored, ['paper', 'topic'])
    paper_decade = rate_table(scored, ['paper', 'decade'])
    voice = rate_table(scored, ['paper', 'voice'])
    voice_pair, _ = matched_pair(scored, 'voice', 'expert', 'journalist', ['paper'] + CELL_KEYS)
    voice_by_paper = []
    for paper, group in scored.groupby('paper'):
        pair, _ = matched_pair(group, 'voice', 'expert', 'journalist', CELL_KEYS)
        if pair: voice_by_paper.append({'paper': paper, **pair})
    speakers = speaker_table(scored)
    papers = sorted(scored.groupby('paper').size().loc[lambda n: n >= 500].index)
    pairs, ranks = [], []
    for left, right in combinations(papers, 2):
        pair, _ = matched_pair(scored, 'paper', left, right, CELL_KEYS)
        if pair: pairs.append(pair)
    pairs = pd.DataFrame(pairs)
    for paper in papers:
        involved = pairs[(pairs.left == paper) | (pairs.right == paper)].copy()
        sign = np.where(involved.left == paper, 1, -1)
        ranks.append({'paper': paper, 'n_opponents': len(involved),
                      'mean_pairwise_matched_gap': np.mean(sign * involved.matched_gap),
                      'mean_gap_beyond_baseline': np.mean(sign * involved.gap_beyond_baseline)})
    ranks = pd.DataFrame(ranks).sort_values('mean_pairwise_matched_gap', ascending=False)
    coverage = scored.groupby('paper').agg(first_year=('year', 'min'), last_year=('year', 'max'), n_claims=('hit', 'size')).reset_index()
    tables = {'failure_overall': failure, 'failure_by_paper': failure_papers, 'failure_by_decade': failure_decades,
              'warning_event_months': panel, 'warning_event_phases': phases, 'warning_timing_matched_events': timing,
              'warning_timing_curve': curve, 'consensus': consensus, 'consensus_by_decade': consensus_decades,
              'consensus_matched_cells': consensus_cells, 'disagreement_and_future_recessions': disagreement,
              'horizons_by_topic': horizons,
              'publisher_specialties': specialties, 'publisher_decades': paper_decade, 'voice_by_paper': voice,
              'voice_matched_by_paper': pd.DataFrame(voice_by_paper), 'speaker_attributions': speakers,
              'publisher_pairwise_matched': pairs, 'publisher_matched_ranking': ranks, 'publisher_coverage': coverage}
    for name, table in tables.items(): table.to_csv(out / f'{name}.csv', index=False)
    matrix.to_csv(out / 'production_direction_confusion.csv')
    consensus_claims[['record_id', 'consensus', 'peer_majority', 'prior_peer_claims', 'prior_peer_papers', 'peer_dominance']].to_csv(out / 'consensus_claims.csv.gz', index=False, compression='gzip')
    charts = make_charts(out, failure_papers, curve, specialties, horizons, consensus, ranks, paper_decade)
    f = failure.iloc[0]
    eligible_speakers = speakers[speakers.adequate_coverage]
    voice_display = pd.DataFrame(voice_by_paper)
    voice_display = voice_display[(voice_display.left_claims_in_cells >= 100) & (voice_display.right_claims_in_cells >= 100)]
    topic_leaders = specialties[specialties.n_claims >= 500].sort_values('hit_rate').groupby('topic').tail(1)
    leader_text = 'Among publisher/topic groups with at least 500 scored claims: ' + '; '.join(
        f"{row.paper} has the highest raw {row.topic.replace('_',' ')} rate ({row.hit_rate:.1%})"
        for row in topic_leaders.itertuples()) + '. These raw leaders are not baseline-relative skill rankings.'
    cons = consensus.set_index('consensus')
    timing_text = 'Matched onset phases could not be formed under the sample thresholds.'
    if len(timing) == 3:
        rates = timing.set_index('phase')
        timing_text = (f"Among {int(rates.iloc[0].n_events)} recessions with at least 30 directional forecasts in each phase, "
                       f"the event-weighted worsening share is {rates.loc['7–12 months before','event_equal_warning_share']:.1%} "
                       f"7–12 months before onset, {rates.loc['1–6 months before','event_equal_warning_share']:.1%} "
                       f"1–6 months before, and {rates.loc['0–5 months after','event_equal_warning_share']:.1%} in the first six recession months.")
    sections = [
        ('False alarms versus missed output declines', [
            f"Among {int(f.n_claims):,} production-scored business forecasts, {f.warning_precision:.1%} of worsening calls "
            f"are followed by an output decline beyond 2%. The calls warn about {f.decline_recall:.1%} of actual declines; "
            f"{f.miss_rate:.1%} are missed. The false-alarm rate among nondeclining outcomes is {f.false_alarm_rate:.1%}.",
            'A miss includes improve or flat calls when output actually falls. A false alarm includes a worsening call followed by growth or flat output. '
            'These are claim-level industrial-production declines over each forecast horizon, not a count of NBER recessions successfully predicted. '
            'Pre-1919 NBER proxy scores are excluded from this comparison.'],
            [('Overall and claim-grounded horizon checks', failure[['subset','n_claims','warning_precision','decline_recall','miss_rate','false_alarm_rate']]),
             ('Publisher warning tradeoffs (at least 500 production-scored claims)', failure_papers[failure_papers.n_claims >= 500][['paper','n_claims','warning_precision','decline_recall','false_alarm_rate']])], ['false_alarms_and_misses.png']),
        ('Were warnings early?', [timing_text,
            'This uses national, readable improve/worsen business forecasts, including those with unscorable horizons. Recession starts come from '
            'the continuous USREC chronology, not the abandoned crisis-window exports. The graph includes event-months with at least 10 forecasts; '
            'the number of contributing events varies, so read its lower panel. Each claim is assigned to the nearest onset within 24 months before '
            'through 12 months after; no claim is counted at multiple onsets.',
            'The phase comparison weights each matched event equally, requires 30 claims in every phase, and restricts pre-onset forecasts to expansion '
            'months and after-onset forecasts to recession months. These are worsening expectations, not necessarily literal recession predictions. '
            'Recession dating is retrospective and used only for descriptive outcomes, never to construct an ex-ante model feature.'],
            [('Same-event warning comparison', timing)], ['warning_timing.png']),
        ('Consensus versus contrarians', [
            f"Forecasts agreeing with a clear earlier other-paper consensus have a raw hit rate of {cons.loc['Agrees with prior consensus','hit_rate']:.1%}; "
            f"contrarians have {cons.loc['Contrarian','hit_rate']:.1%}. The matched agreement-minus-contrarian gap is "
            f"{consensus_pair.get('matched_gap', np.nan)*100:+.1f} percentage points, comparing the same paper, publication month, topic, "
            'benchmark, horizon basis, and exact horizon. Each cell requires five agreement and five contrarian claims.',
            f"The five-year block-resampling interval for that gap is "
            f"{consensus_pair.get('block_ci_low',np.nan)*100:+.1f} to {consensus_pair.get('block_ci_high',np.nan)*100:+.1f} percentage points. "
            'It crosses zero: the pooled advantage is unstable across historical periods and does not establish a consistently superior strategy.',
            'Consensus uses only predictions in the preceding 90 calendar days, excluding the current date and the current paper. '
            'It requires at least 20 earlier claims from two other papers in the same topic, benchmark, horizon-basis and horizon-bucket group, '
            'with at least 60% backing one normalized direction. Flat is a valid direction. No future predictions or realized outcomes form consensus. '
            'A contrarian label is a descriptive comparison, not evidence that the speaker knew or opposed those other forecasts.',
            'The disagreement diagnostic below restricts production forecasts to months retrospectively classified as expansion. '
            'It compares earlier agreement strength with an onset in the next 12 months. Publication months have equal weight within each group; '
            'a month can appear in more than one group. Topic, horizon and era composition can still differ, so these are descriptive associations. '
            'The month-weighted onset shares are very similar (20.6–21.4%); the apparent claim-weighted gradient largely disappears '
            'when heavily represented months receive less weight.'],
            [('Prior-only consensus groups', consensus[['consensus','n_claims','hit_rate','fixed_baseline']]),
             ('Earlier agreement strength and later recession onset', disagreement)], ['consensus.png']),
        ('Forecast horizon', [
            f"For explicit numeric horizons, a matched 6-month versus 12-month comparison gives "
            f"{horizon_pair.get('left_matched_hit_rate',np.nan):.1%} versus {horizon_pair.get('right_matched_hit_rate',np.nan):.1%} "
            f"({horizon_pair.get('matched_gap',np.nan)*100:+.1f} percentage points).",
            'The chart excludes default and inferred horizons. The direct 6/12-month comparison uses the same papers, years, topics, and '
            'benchmarks, requires at least 10 claims for each horizon in each cell, and weights both horizons by the same overlap distribution. '
            f"The 6-minus-12-month fixed-baseline gap is {horizon_pair.get('baseline_gap',np.nan)*100:+.1f} percentage points; "
            f"the forecast gap beyond that baseline is {horizon_pair.get('gap_beyond_baseline',np.nan)*100:+.1f} points. "
            'Thus the higher raw 12-month hit rate does not establish better skill: the baseline advantage is larger. '
            'Horizon choice was not randomized, so differences are not causal.'],
            [('Explicit-horizon results by topic', horizons[['topic','horizon_band','n_claims','hit_rate','fixed_baseline']])], ['forecast_horizons.png']),
        ('Publisher specialties and ranking stability', [
            leader_text,
            'Raw topic hit rates answer which published calls came true most often. Coverage-adjusted gaps answer a narrower question: '
            'how a paper compared to other papers forecasting similar years, topics, benchmarks, horizon bases, and horizon buckets. '
            'The heatmap masks cells below 200 claims; rankings include publishers with at least 500 scored claims.',
            'Each pairwise publisher comparison keeps only cells with at least 10 claims from both papers and uses harmonic-overlap weights '
            'for identical composition on both sides. The ranking averages each paper\'s gaps across available opponents with equal opponent weight; '
            'different pairs still have different shared coverage, so this is not a universal common-period tournament. '
            'Five-year block intervals for each pair are in publisher_pairwise_matched.csv; multiple comparisons are exploratory.',
            'Coverage correction: the machine-verified Wall Street Journal claims begin in 1984, not 1960 as the first report stated. '
            'Chicago Tribune coverage ends in 2001. The earlier report and its generator have been corrected. '
            'Decade cells can cover only part of a decade: Chicago in the 2000s covers 2000–2001, and all 2010s cells cover 2010 only.'],
            [('Actual coverage of scored claims', coverage), ('Mean pairwise coverage-adjusted gaps', ranks)],
            ['publisher_specialties.png','matched_publishers.png','publisher_stability.png']),
        ('Who made the forecast?', [
            f"Within matched paper/year/topic/benchmark/horizon cells, expert-attributed forecasts score "
            f"{voice_pair.get('left_matched_hit_rate',np.nan):.1%}, versus {voice_pair.get('right_matched_hit_rate',np.nan):.1%} "
            f"for journalists ({voice_pair.get('matched_gap',np.nan)*100:+.1f} percentage points).",
            f"The five-year block interval for the expert-minus-journalist gap is "
            f"{voice_pair.get('block_ci_low',np.nan)*100:+.1f} to {voice_pair.get('block_ci_high',np.nan)*100:+.1f} points, "
            'providing no clear separation in this comparison.',
            'Speaker attribution is noisy. Names are normalized only for capitalization, punctuation, and spacing; initials, surname-only forms, '
            'titles, and similar names are not automatically merged. The listed names are attribution strings and may denote an institution. '
            'The attribution coverage table highlights strings with 100 scored claims, at least five distinct publication years, and at least '
            f'two newspaper families. There are {len(eligible_speakers)} sufficiently represented attribution strings. '
            'The alphabetized CSV provides coverage counts for later source-quote review; identities still need validation.'],
            [('Experts versus journalists within matched cells, by publisher (at least 100 claims in each group)', voice_display[['paper','left_claims_in_cells','right_claims_in_cells','left_matched_hit_rate','right_matched_hit_rate','matched_gap']])], []),
        ('Interpretation and reproducibility', [
            'All outcome rates reuse the first report\'s documented national-scope and benchmark rules. Market forecasts remain a provisional '
            'broad-stock-price proxy. Machine verification is not human validation, and stripped quotes prevent semantic rechecking and definitive '
            'deduplication locally. Claim counts are not independent trials. Equal-weight events, shared-cell comparisons, and block resampling '
            'reduce some confounding but do not make these observational results causal.',
            'Run python src/proquest_followups.py from the repository root. Source and reference digests are recorded in summary.json. '
            'The saved outcome rows are checked one-to-one against every annual verified export before the analysis starts. '
            'LOC data, raw/unverified candidates, and old window shards are never loaded. No numerical confidence probabilities, ML model, '
            'or page-denominator attention rate is invented.'], [], [])]
    facts = {'verified_claims': len(claims), 'scorable_claims': len(scored), 'production_failure_metrics': failure.to_dict('records'),
             'warning_timing_matched_events': timing.to_dict('records'), 'recession_starts': starts,
             'consensus_matched_comparison': consensus_pair, 'horizon_6_vs_12_matched_comparison': horizon_pair,
             'expert_vs_journalist_matched_comparison': voice_pair,
             'publisher_matched_comparison': ranks.to_dict('records'), 'eligible_speaker_strings': len(eligible_speakers),
             'verified_source_sha256': digests, 'reference': metadata['reference'],
             'prior_report_scores_sha256': hashlib.sha256((SOURCE / 'scored_claims.csv.gz').read_bytes()).hexdigest()}
    write_report(out, sections, charts, facts)
    print(failure.to_string(index=False)); print(timing.to_string(index=False)); print(consensus.to_string(index=False))
    print(ranks.to_string(index=False)); print(f'Report: {out / "report.html"}')


if __name__ == '__main__':
    main()
