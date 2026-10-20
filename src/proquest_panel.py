"""Print-time monthly ProQuest panels, independent of economic outcomes.

All readable national direction labels enter, even when a claim's horizon or
eventual outcome cannot be scored. Counts are export coverage, not attention.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from analyze_proquest import annual_files
from proquest_descriptive import paper_name
from score_predictions import predicted_norm

TOPICS = ("general_business", "markets", "prices", "employment")
SIGNS = ("positive", "flat", "negative")
FEATURES = ("net_direction_3m", "net_change_common_papers", "disagreement_3m", "paper_dispersion_3m")
CALENDAR = pd.period_range("1900-01", "2010-12", freq="M")


def sign_label(claim):
    """Positive means improving business/markets/jobs, but rising prices for CPI.

    These are direction labels, not a universal desirability or welfare scale.
    Employment signs invert the normalized unemployment direction.
    """
    direction = predicted_norm(claim)
    if claim["topic"] == "employment":
        return {"down": "positive", "up": "negative", "flat": "flat"}.get(direction)
    return {"improve": "positive", "up": "positive", "worsen": "negative",
            "down": "negative", "flat": "flat"}.get(direction)


def read_claims(base=Path("data/proquest/verified")):
    rows, counts, hashes = [], Counter(), {}
    for path in annual_files(base):
        hashes[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
        year = int(path.name.split("_")[-1].split(".")[0])
        with path.open(encoding="utf-8") as source:
            for number, line in enumerate(source, 1):
                if not line.strip():
                    continue
                claim = json.loads(line)
                if claim.get("no_predictions"):
                    counts["empty_records"] += 1
                    continue
                if claim.get("source") != "proquest" or claim.get("schema_version") != 2 or "verify_reason" not in claim:
                    raise ValueError(f"Not an annual verified ProQuest claim: {path}:{number}")
                printed = pd.Timestamp(claim["date"])
                if printed.year != year or not claim.get("page_id"):
                    raise ValueError(f"Invalid date/article ID: {path}:{number}")
                counts["claims"] += 1
                if claim.get("scope") != "national":
                    counts["excluded_nonnational"] += 1
                    continue
                if claim.get("topic") not in TOPICS:
                    counts["excluded_topic"] += 1
                    continue
                sign = sign_label(claim)
                if sign is None:
                    counts["excluded_direction"] += 1
                    continue
                counts["panel_claims"] += 1
                # Whitelist only printed metadata. No horizons, verifier prose,
                # outcome eligibility, annotations, or realized outcomes are read.
                rows.append({"page_id": str(claim["page_id"]), "date": printed.date().isoformat(),
                             "month": printed.to_period("M"), "topic": claim["topic"], "sign": sign,
                             "paper": paper_name(claim.get("publisher") or claim.get("newspaper_title"))})
    frame = pd.DataFrame(rows)
    if frame.empty:
        raise ValueError("No readable national direction labels")
    if (frame.groupby("page_id")[["date", "paper"]].nunique() > 1).any().any():
        raise ValueError("Article IDs have inconsistent dates or publishers")
    return frame, dict(counts), hashes


def build_panels(claims, calendar=CALENDAR):
    """Equal articles within paper/topic/month; then equal observed newspapers."""
    keys = ["month", "paper", "topic"]
    article = claims.groupby(keys + ["page_id", "sign"]).size().unstack(fill_value=0)
    article = article.reindex(columns=SIGNS, fill_value=0)
    article["n_claims"] = article[list(SIGNS)].sum(axis=1)
    for sign in SIGNS:
        article[f"{sign}_share"] = article[sign] / article.n_claims
    article = article.reset_index()
    aggregation = {"n_claims": ("n_claims", "sum"), "n_articles": ("page_id", "size")}
    aggregation.update({f"{sign}_share": (f"{sign}_share", "mean") for sign in SIGNS})
    aggregation.update({f"{sign}_claims": (sign, "sum") for sign in SIGNS})
    paper = article.groupby(keys).agg(**aggregation)
    index = pd.MultiIndex.from_product([calendar, sorted(claims.paper.unique()), TOPICS], names=keys)
    paper = paper.reindex(index)
    for field in ["n_claims", "n_articles"] + [f"{s}_claims" for s in SIGNS]:
        paper[field] = paper[field].fillna(0).astype(int)
    paper["observed"] = paper.n_articles > 0
    paper["net_direction"] = paper.positive_share - paper.negative_share
    paper["disagreement"] = 1.5 * (1 - paper[[f"{s}_share" for s in SIGNS]].pow(2).sum(axis=1, min_count=3))
    paper = paper.reset_index().sort_values(["paper", "topic", "month"]).reset_index(drop=True)
    paper["net_change_1m"] = paper.groupby(["paper", "topic"]).net_direction.diff()
    observed = paper[paper.observed]
    national = observed.groupby(["month", "topic"]).agg(
        n_papers=("paper", "size"), n_articles=("n_articles", "sum"), n_claims=("n_claims", "sum"),
        **{f"{s}_share": (f"{s}_share", "mean") for s in SIGNS},
        paper_dispersion=("net_direction", lambda x: x.std(ddof=0) if len(x) >= 2 else np.nan))
    national = national.reindex(pd.MultiIndex.from_product([calendar, TOPICS], names=["month", "topic"]))
    for field in ("n_papers", "n_articles", "n_claims"):
        national[field] = national[field].fillna(0).astype(int)
    national["net_direction"] = national.positive_share - national.negative_share
    national["disagreement"] = 1.5 * (1 - national[[f"{s}_share" for s in SIGNS]].pow(2).sum(axis=1, min_count=3))
    national = national.reset_index().sort_values(["topic", "month"]).reset_index(drop=True)
    national["net_change_1m"] = national.groupby("topic").net_direction.diff()
    return article, paper, national


def forecast_features(paper, national, origins):
    """Use complete print months strictly before each origin, without outcomes."""
    business = paper[(paper.topic == "general_business") & paper.observed].copy()
    monthly = national[national.topic == "general_business"].set_index("month")
    rows = []
    for origin in origins:
        recent = business[(business.month >= origin - 3) & (business.month < origin)]
        previous = business[(business.month >= origin - 6) & (business.month < origin - 3)]
        def enough(window):
            # Articles have exactly one print month; sum is unique within topic.
            return window.month.nunique() >= 2 and window.paper.nunique() >= 2 and window.n_articles.sum() >= 5
        row = {"origin": origin, "latest_print_month": origin - 1,
               "recent_articles": int(recent.n_articles.sum()), "recent_papers": recent.paper.nunique(),
               "recent_observed_months": recent.month.nunique(), **{name: np.nan for name in FEATURES}}
        if enough(recent):
            levels = monthly.reindex(pd.period_range(origin - 3, origin - 1, freq="M"))
            row["net_direction_3m"] = levels.net_direction.mean()
            row["disagreement_3m"] = levels.disagreement.mean()
            row["paper_dispersion_3m"] = levels.paper_dispersion.mean()
            if enough(previous):
                current_papers = recent.groupby("paper").net_direction.mean()
                prior_papers = previous.groupby("paper").net_direction.mean()
                common = current_papers.index.intersection(prior_papers.index)
                if len(common) >= 2:
                    row["net_change_common_papers"] = (current_papers[common] - prior_papers[common]).mean()
        rows.append(row)
    return pd.DataFrame(rows)
