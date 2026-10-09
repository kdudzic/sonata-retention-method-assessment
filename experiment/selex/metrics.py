"""Retention budgets and metrics (plan sections 9-10).

Mechanics: sort posts by score descending, break ties randomly with a seed, cut the top k % -> retained set.
Metrics are computed per (selector, access variant, budget, tie seed) and reported as absolute numbers.

Detection (10.1)
  detected_arcs@k         arcs with >= 1 SIGNAL post in the retained set (strict)
  detected_arcs_loose@k   arcs with any post in the retained set
  detection_by_type@k     concentrated / distributed split of the strict count
  detection_lag           per detected arc: arc position of the earliest retained signal post (and its index among the arc's signal posts)
  decoy_hits@k            decoy authors with >= 1 retained post
Invasiveness (10.2)
  bystander_authors@k     authors without any arc that have >= 1 retained post
  BPD@k                   bystander_authors / detected_arcs (None if 0 detected)
  profile_depth@k         mean retained posts per retained bystander author
  review_load@k           retained posts / detected_arcs (None if 0)
Control (10.3)
  tie_span                range of a metric across tie seeds (computed by the caller over seeds)
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .corpus import Corpus


@dataclass
class BudgetResult:
    budget: float
    tie_seed: int
    n_retained: int
    detected_arcs: int
    detected_arcs_loose: int
    detected_concentrated: int
    detected_distributed: int
    detected_arc_ids: list[str]
    detection_lag: dict[str, int]
    decoy_hits: int
    bystander_authors: int
    bystander_posts: int
    profile_depth: float | None
    bpd: float | None
    review_load: float | None
    target_authors_hit: int
    retained_signal_posts: int
    extra: dict = field(default_factory=dict)

    def flat(self) -> dict:
        d = {k: v for k, v in self.__dict__.items() if k not in ("detected_arc_ids", "detection_lag", "extra")}
        d["detected_arc_ids"] = "|".join(self.detected_arc_ids)
        d["detection_lag"] = "|".join(f"{a}:{p}" for a, p in sorted(self.detection_lag.items()))
        d.update(self.extra)
        return d


def rank_with_ties(scores: pd.Series, tie_seed: int) -> pd.Series:
    """Returns 1-based rank per post_id; ties broken by a seeded random key (lower rank = retained first)."""
    rng = np.random.default_rng(tie_seed)
    df = pd.DataFrame({"post_id": scores.index, "score": scores.values.astype(float), "key": rng.random(len(scores))})
    df = df.sort_values(["score", "key"], ascending=[False, True]).reset_index(drop=True)
    df["rank"] = np.arange(1, len(df) + 1)
    return df.set_index("post_id")["rank"]


def retained_set(scores: pd.Series, budget: float, tie_seed: int) -> set[str]:
    n = int(round(budget * len(scores)))
    r = rank_with_ties(scores, tie_seed)
    return set(r[r <= n].index)


def evaluate_budget(c: Corpus, scores: pd.Series, budget: float, tie_seed: int) -> BudgetResult:
    kept = retained_set(scores, budget, tie_seed)
    posts = c.posts.set_index("post_id")
    detected, loose, lag = [], [], {}
    conc = dist = 0
    for arc_id in c.target_arcs:
        a = c.arcs[arc_id]
        sig_hit = [p for p in a["signal_post_ids"] if p in kept]
        any_hit = any(p in kept for p in a["post_ids"])
        if any_hit:
            loose.append(arc_id)
        if sig_hit:
            detected.append(arc_id)
            if a["arc_type"] == "concentrated":
                conc += 1
            else:
                dist += 1
            lag[arc_id] = min(int(posts.loc[p, "arc_position"]) for p in sig_hit)
    decoy_hits = sum(1 for arc_id in c.decoy_arcs if any(p in kept for p in c.arcs[arc_id]["post_ids"]))
    by = c.bystander_authors
    kept_posts = posts.loc[list(kept)]
    by_kept = kept_posts[kept_posts.author_id.isin(by)]
    by_authors = by_kept.author_id.nunique()
    target_authors = {c.arcs[a]["author_id"] for a in c.target_arcs}
    nd = len(detected)
    return BudgetResult(
        budget=budget, tie_seed=tie_seed, n_retained=len(kept),
        detected_arcs=nd, detected_arcs_loose=len(loose), detected_concentrated=conc, detected_distributed=dist,
        detected_arc_ids=sorted(detected), detection_lag=lag, decoy_hits=decoy_hits,
        bystander_authors=int(by_authors), bystander_posts=int(len(by_kept)),
        profile_depth=(float(len(by_kept) / by_authors) if by_authors else None),
        bpd=(by_authors / nd if nd else None), review_load=(len(kept) / nd if nd else None),
        target_authors_hit=int(kept_posts.author_id.isin(target_authors).sum() > 0 and kept_posts[kept_posts.author_id.isin(target_authors)].author_id.nunique()),
        retained_signal_posts=int(sum(1 for p in c.signal_post_ids if p in kept)),
    )


def evaluate_grid(c: Corpus, scores: pd.Series, budgets: list[float], tie_seeds: list[int], meta: dict) -> pd.DataFrame:
    rows = []
    for b in budgets:
        for s in tie_seeds:
            r = evaluate_budget(c, scores, b, s)
            d = r.flat()
            d.update(meta)
            rows.append(d)
    df = pd.DataFrame(rows)
    # tie span per budget: range of detected_arcs and bystander_authors over seeds
    spans = df.groupby("budget").agg(tie_span_detected=("detected_arcs", lambda x: x.max() - x.min()),
                                      tie_span_bystanders=("bystander_authors", lambda x: x.max() - x.min())).reset_index()
    return df.merge(spans, on="budget")


def summarize(df: pd.DataFrame) -> pd.DataFrame:
    """Mean over tie seeds (absolute numbers kept), one row per selector x variant x budget."""
    keys = ["selector", "access_variant", "budget"]
    agg = df.groupby(keys).agg(
        n_retained=("n_retained", "first"),
        detected=("detected_arcs", "mean"), detected_min=("detected_arcs", "min"), detected_max=("detected_arcs", "max"),
        detected_loose=("detected_arcs_loose", "mean"), conc=("detected_concentrated", "mean"), dist=("detected_distributed", "mean"),
        decoy_hits=("decoy_hits", "mean"), bystanders=("bystander_authors", "mean"), bystander_posts=("bystander_posts", "mean"),
        profile_depth=("profile_depth", "mean"), review_load=("review_load", "mean"), signal_posts=("retained_signal_posts", "mean"),
        tie_span_detected=("tie_span_detected", "first"),
    ).reset_index()
    agg["bpd"] = agg.apply(lambda r: (r.bystanders / r.detected) if r.detected else np.nan, axis=1)
    return agg
