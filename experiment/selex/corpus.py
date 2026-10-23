"""Corpus loading for the experiment: evaluation / dev split by arc assignment, gold labels derived programmatically.

The selectors only ever receive `post_id`, `author_id`, `timestamp`, `text` (and for D3 the earlier posts of the
same author). Everything else here (arc ids, roles, signal status) is used solely by the metrics code.

Gold (plan 3, 10): an arc is "detected" (strict) when at least one of its SIGNAL posts is in the retained set;
loosely when any of its posts is. Target authors = authors of concentrated/distributed arcs in the evaluation
split. Bystanders = authors with no arc at all. Decoys (TC-*) are reported separately.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import yaml

from . import config


@dataclass
class Corpus:
    name: str
    posts: pd.DataFrame        # post_id, author_id, timestamp, text, layer, arc_id, arc_position, arc_role, post_level_profile
    authors: pd.DataFrame      # author_id, is_target, arc_id, arc_type, n_posts
    arc_key: pd.DataFrame      # arc_id, arc_type, arc_position, is_signal, legal_relevance_focus
    arcs: dict[str, dict]      # arc_id -> {arc_type, n_posts, signal_positions, post_ids, signal_post_ids, author_id}

    # ---- views for selectors (no labels)
    def selector_view(self) -> pd.DataFrame:
        return self.posts[["post_id", "author_id", "timestamp", "text"]].copy()

    def history(self, post_id: str, max_posts: int | None = None) -> pd.DataFrame:
        """Earlier posts of the same author, oldest first (never later ones; plan section 8)."""
        row = self.posts.loc[self.posts.post_id == post_id].iloc[0]
        h = self.posts[(self.posts.author_id == row.author_id) & (self.posts.timestamp < row.timestamp)].sort_values("timestamp")
        if max_posts is not None and len(h) > max_posts:
            h = h.tail(max_posts)
        return h[["post_id", "timestamp", "text"]]

    # ---- gold
    @property
    def target_arcs(self) -> list[str]:
        return [a for a, v in self.arcs.items() if v["arc_type"] in ("concentrated", "distributed")]

    @property
    def decoy_arcs(self) -> list[str]:
        return [a for a, v in self.arcs.items() if v["arc_type"] == "decoy"]

    @property
    def bystander_authors(self) -> set[str]:
        return set(self.authors.loc[self.authors.arc_id.fillna("") == "", "author_id"])

    @property
    def signal_post_ids(self) -> set[str]:
        return {p for a in self.target_arcs for p in self.arcs[a]["signal_post_ids"]}


def _load_tables(d: Path, version: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    posts = pd.read_csv(d / f"posts_{version}.csv", dtype=str).fillna("")
    authors = pd.read_csv(d / f"authors_{version}.csv", dtype=str).fillna("")
    key_path = d / f"arc_key_{version}.csv"
    empty = pd.DataFrame(columns=["arc_id", "arc_type", "arc_position", "is_signal", "legal_relevance_focus"])
    try:
        key = pd.read_csv(key_path, dtype=str).fillna("") if key_path.exists() else empty
    except pd.errors.EmptyDataError:
        key = empty
    posts["timestamp"] = pd.to_datetime(posts["timestamp"])
    return posts, authors, key


def _build(name: str, posts: pd.DataFrame, authors: pd.DataFrame, key: pd.DataFrame) -> Corpus:
    arcs: dict[str, dict] = {}
    for arc_id, k in key.groupby("arc_id"):
        sub = posts[posts.arc_id == arc_id].sort_values("arc_position", key=lambda s: s.astype(int))
        sig_pos = set(k.loc[k.is_signal.str.lower() == "true", "arc_position"].astype(str))
        arcs[arc_id] = {
            "arc_type": k.arc_type.iloc[0],
            "legal_relevance_focus": k.legal_relevance_focus.iloc[0],
            "author_id": sub.author_id.iloc[0] if len(sub) else None,
            "n_posts": int(len(sub)),
            "signal_positions": sorted(sig_pos, key=int),
            "post_ids": sub.post_id.tolist(),
            "signal_post_ids": sub.loc[sub.arc_position.astype(str).isin(sig_pos), "post_id"].tolist(),
        }
    posts = posts.sort_values(["author_id", "timestamp"]).reset_index(drop=True)
    return Corpus(name, posts, authors.reset_index(drop=True), key, arcs)


def load_split(cfg: dict) -> tuple[Corpus, Corpus]:
    """Returns (evaluation corpus, dev corpus) after applying configs/arc_split.yaml.

    Evaluation = all non-arc authors of the evaluation corpus + the eval arcs + decoys (spare and dev arcs dropped).
    Dev = the dev corpus as built (its own background, hard negatives and the dev arcs generated with separate
    persona cards and seed; see build_dev_arcs.py). Nothing is transplanted between the two corpora.
    """
    c = cfg["corpus"]
    split = yaml.safe_load(config.resolve(c["arc_split"]).read_text(encoding="utf-8"))
    eval_arcs = split["eval"]["concentrated"] + split["eval"]["distributed"] + split["eval"]["decoy"]
    dev_arcs = split.get("dev", [])
    posts, authors, key = _load_tables(config.resolve(c["eval_dir"]), c["eval_version"])
    keep_eval = (posts.arc_id == "") | posts.arc_id.isin(eval_arcs)
    ev = _build("eval", posts[keep_eval].copy(), authors[(authors.arc_id == "") | authors.arc_id.isin(eval_arcs)].copy(), key[key.arc_id.isin(eval_arcs)].copy())
    dposts, dauthors, dkey = _load_tables(config.resolve(c["dev_dir"]), c["dev_version"])
    keep_dev = (dposts.arc_id == "") | dposts.arc_id.isin(dev_arcs)
    dv = _build("dev", dposts[keep_dev].copy(), dauthors[(dauthors.arc_id == "") | dauthors.arc_id.isin(dev_arcs)].copy(), dkey[dkey.arc_id.isin(dev_arcs)].copy())
    return ev, dv


def describe(c: Corpus) -> dict:
    return {
        "name": c.name, "n_posts": int(len(c.posts)), "n_authors": int(len(c.authors)),
        "layers": c.posts.layer.value_counts().to_dict(),
        "arcs": {a: {"type": v["arc_type"], "n": v["n_posts"], "signal": v["signal_positions"]} for a, v in c.arcs.items()},
        "n_signal_posts": len(c.signal_post_ids), "n_bystanders": len(c.bystander_authors),
    }
