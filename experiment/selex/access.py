"""Access variants (plan section 8) and the shared aggregation function.

D0      selector sees the post only
D3-agg  score(post) = sum of the top-k D0 scores among the author's posts up to and including the post
        (k = 3, frozen before the runs; identical for every selector)
D3-nat  (S3 only) earlier posts in the prompt - built by the runner from Corpus.history
D3-txt / D3-vec  (S1 only) see s1_semantic

The ranking unit stays the post in every variant.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def aggregate_top_k_sum(posts: pd.DataFrame, scores: pd.Series, k: int = 3) -> pd.Series:
    """posts: DataFrame with post_id, author_id, timestamp (sorted or not). scores: indexed by post_id.
    Returns a Series indexed by post_id with the D3-agg score."""
    df = posts[["post_id", "author_id", "timestamp"]].copy()
    df["s"] = df.post_id.map(scores).astype(float)
    df = df.sort_values(["author_id", "timestamp", "post_id"])
    out = {}
    for _, g in df.groupby("author_id", sort=False):
        vals: list[float] = []
        for pid, s in zip(g.post_id, g.s):
            vals.append(s)
            top = sorted(vals, reverse=True)[:k]
            out[pid] = float(np.sum(top))
    return pd.Series(out)


def random_scores(post_ids: list[str], seed: int) -> pd.Series:
    rng = np.random.default_rng(seed)
    return pd.Series(rng.random(len(post_ids)), index=post_ids)
