"""Scoring runs: selector x access variant -> scores table (plan Annex I `scores_v1.csv` schema).

One row per post x selector x access_variant x run. Tie seeds are applied later by metrics.rank_with_ties, so the
scores table stores the raw continuous score; `rank` here is the seed-0 rank for convenience.

Selectors / variants produced:
  S0-sub, S0-veto    : D0, D3-agg
  S1                 : D0, D3-agg, D3-txt, D3-vec ; S1-shuffled (control): D0
  S3-open            : D0, D3-agg, D3-nat
  S3-blind (S3')     : D0, D3-nat
  S3-com             : D0, D3-nat on a ~10 % subsample
  S-rand             : D0 (5 seeds)
"""

from __future__ import annotations

import json
import time
import uuid
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from . import config
from .access import aggregate_top_k_sum, random_scores
from .corpus import Corpus
from .metrics import rank_with_ties
from .s0_lexical import Lexicon, S0Selector
from .s1_semantic import S1Selector, Seeds
from .s3_llm import S3Selector

SCORE_COLS = ["post_id", "selector", "access_variant", "tie_seed", "raw_score", "rank", "decision", "retention_score",
              "decisive_posts_json", "logprob_decision", "model_id", "prompt_version", "temperature", "run_id", "run_timestamp"]


def _frame(c: Corpus, scores: pd.Series, selector: str, variant: str, model_id: str = "", prompt_version: str = "",
           temperature: float | None = None, extra: dict[str, dict] | None = None, run_id: str | None = None) -> pd.DataFrame:
    run_id = run_id or uuid.uuid4().hex[:10]
    ts = datetime.now().isoformat(timespec="seconds")
    r = rank_with_ties(scores, 0)
    rows = []
    for pid in c.posts.post_id:
        e = (extra or {}).get(pid, {})
        rows.append({"post_id": pid, "selector": selector, "access_variant": variant, "tie_seed": 0,
                     "raw_score": float(scores[pid]), "rank": int(r[pid]), "decision": e.get("decision", ""),
                     "retention_score": e.get("retention_score", np.nan),
                     "decisive_posts_json": json.dumps(e.get("decisive_posts", []), ensure_ascii=False) if e else "",
                     "logprob_decision": e.get("logprob_decision", np.nan), "model_id": model_id, "prompt_version": prompt_version,
                     "temperature": temperature if temperature is not None else "", "run_id": run_id, "run_timestamp": ts})
    return pd.DataFrame(rows, columns=SCORE_COLS)


def save_scores(df: pd.DataFrame, c: Corpus, cfg: dict, name: str) -> Path:
    d = cfg["results_dir"] / c.name
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"scores_{name}.csv"
    df.to_csv(p, index=False)
    return p


def load_all_scores(c: Corpus, cfg: dict) -> pd.DataFrame:
    d = cfg["results_dir"] / c.name
    frames = [pd.read_csv(p, dtype={"post_id": str, "decision": str}) for p in sorted(d.glob("scores_*.csv"))]
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=SCORE_COLS)


# ----------------------------------------------------------------------------- S0
def run_s0(c: Corpus, cfg: dict) -> list[pd.DataFrame]:
    s0 = cfg["selectors"]["s0"]
    lex = Lexicon.load(config.resolve(s0["lexicon"]))
    sel = S0Selector(lex, s0["weights"], s0["proximity_tokens"])
    out = []
    feats = {}
    for variant in s0["variants"]:
        sc = {}
        for pid, txt in zip(c.posts.post_id, c.posts.text):
            s, f = sel.score(txt, variant)
            sc[pid] = s
            feats[pid] = f
        sc = pd.Series(sc)
        name = f"S0-{variant}"
        out.append(_frame(c, sc, name, "D0", model_id=f"lexicon:{lex.version}"))
        agg = aggregate_top_k_sum(c.posts, sc, cfg["aggregation"]["k"])
        out.append(_frame(c, agg, name, "D3-agg", model_id=f"lexicon:{lex.version}"))
    fd = cfg["results_dir"] / c.name
    fd.mkdir(parents=True, exist_ok=True)
    pd.DataFrame.from_dict(feats, orient="index").to_csv(fd / "s0_features.csv")
    return out


# ----------------------------------------------------------------------------- S1
def run_s1(c: Corpus, cfg: dict, shuffled_seeds: list[int] | None = None, include_d3: bool = True) -> list[pd.DataFrame]:
    s1 = cfg["selectors"]["s1"]
    ledger = cfg["results_dir"] / "raw" / "ledger.jsonl"
    ledger.parent.mkdir(parents=True, exist_ok=True)
    seeds = Seeds.load(config.resolve(s1["seeds"]))
    model = s1["embedding_model"]
    sel = S1Selector(seeds, model, ledger=ledger)
    texts = c.posts.text.tolist()
    E = sel.embed_texts(texts)
    sel.fit_center(E)
    np.save(cfg["results_dir"] / c.name / "s1_embeddings_d0.npy", E) if (cfg["results_dir"] / c.name).exists() else None
    pid = c.posts.post_id.tolist()
    out = []
    d0 = pd.Series(sel.score_vectors(E), index=pid)
    mid = f"{model}|seeds:{seeds.version}"
    out.append(_frame(c, d0, "S1", "D0", model_id=mid))
    out.append(_frame(c, aggregate_top_k_sum(c.posts, d0, cfg["aggregation"]["k"]), "S1", "D3-agg", model_id=mid))
    if include_d3:
        # D3-txt: history + post in one window; D3-vec: mixed vectors
        idx = {p: i for i, p in enumerate(pid)}
        txt_inputs, vec = [], np.zeros_like(E)
        for i, p in enumerate(pid):
            h = c.history(p, max_posts=cfg["selectors"]["s3"]["max_history_posts"])
            txt_inputs.append(S1Selector.d3_txt_inputs(texts[i], h.text.tolist()))
            hm = E[[idx[x] for x in h.post_id]].mean(axis=0) if len(h) else None
            vec[i] = S1Selector.d3_vec(E[i], hm, s1["d3_vec_alpha"])
        Et = sel.embed_texts(txt_inputs)
        out.append(_frame(c, pd.Series(sel.score_vectors(Et), index=pid), "S1", "D3-txt", model_id=mid))
        out.append(_frame(c, pd.Series(sel.score_vectors(vec), index=pid), "S1", "D3-vec", model_id=mid))
    for s in (shuffled_seeds or []):
        sh = S1Selector(seeds.shuffled(s), model, ledger=ledger)
        sh.fit_center(E)
        out.append(_frame(c, pd.Series(sh.score_vectors(E), index=pid), f"S1-shuffled{s}", "D0", model_id=f"{model}|seeds:{seeds.version}-shuffled{s}"))
    return out


# ----------------------------------------------------------------------------- S3
def _s3_run(c: Corpus, cfg: dict, model: str, prompt: str, selector: str, variant: str, run_tag: str,
            subset: list[str] | None = None, repeat: int = 0) -> pd.DataFrame:
    s3 = cfg["selectors"]["s3"]
    run_name = f"{c.name}_{selector}_{variant}_{run_tag}" + (f"_rep{repeat}" if repeat else "")
    sel = S3Selector(model, prompt, run_name=run_name, temperature=s3["temperature"], logprobs=True, workers=s3["workers"],
                     seed=repeat, provider_order=(s3.get("provider_order") or {}).get(model),
                     max_cost_usd=s3.get("max_cost_usd_per_run"), max_tokens=int(s3.get("max_tokens", 4000)))
    sel.llm.raw_root = cfg["results_dir"] / "raw"
    sel.llm.raw_dir = sel.llm.raw_root / run_name
    sel.llm.raw_dir.mkdir(parents=True, exist_ok=True)
    sel.llm.ledger = sel.llm.raw_root / "ledger.jsonl"
    ids = subset if subset is not None else c.posts.post_id.tolist()
    text_of = dict(zip(c.posts.post_id, c.posts.text))
    items = []
    for p in ids:
        hist = None
        if variant == "D3-nat":
            h = c.history(p, max_posts=s3["max_history_posts"])
            hist = list(zip(h.post_id, h.text))
        items.append((p, text_of[p], hist))
    res = sel.score_many(items, desc=f"{selector} {variant} {c.name}")
    scores, extra, errors = {}, {}, []
    from .llm import BudgetExceeded
    n_budget = sum(1 for r in res if isinstance(r, BudgetExceeded))
    if n_budget:
        raise BudgetExceeded(f"{run_name}: cap hit, {n_budget} posts not scored, spent ${sel.llm.total_cost:.2f}; nothing saved")
    for it, r in zip(items, res):
        if isinstance(r, Exception):
            errors.append((it[0], str(r)))
            continue
        scores[r.post_id] = r.raw_score
        extra[r.post_id] = {"decision": r.decision, "retention_score": r.retention_score,
                            "logprob_decision": (np.log(max(r.p_keep, 1e-12)) if r.p_keep is not None else np.nan), "decisive_posts": r.decisive_posts}
    if errors:
        (cfg["results_dir"] / c.name).mkdir(parents=True, exist_ok=True)
        (cfg["results_dir"] / c.name / f"errors_{run_name}.json").write_text(json.dumps(errors, ensure_ascii=False, indent=1))
    # posts outside the subset or failed get NaN score -> frame only over scored posts
    sc = pd.Series(scores)
    sub = Corpus(c.name, c.posts[c.posts.post_id.isin(sc.index)].copy(), c.authors, c.arc_key, c.arcs)
    df = _frame(sub, sc, selector, variant, model_id=model, prompt_version=prompt, temperature=s3["temperature"], extra=extra)
    df.attrs["cost"] = sel.llm.total_cost
    print(f"  {run_name}: {len(sc)} scored, {len(errors)} errors, {sel.llm.summary()}")
    return df


def run_s3_open(c: Corpus, cfg: dict, variants: tuple[str, ...] = ("D0", "D3-nat"), repeat: int = 0) -> list[pd.DataFrame]:
    s3 = cfg["selectors"]["s3"]
    out = []
    for v in variants:
        prompt = s3["prompt_d0"] if v == "D0" else s3["prompt_d3nat"]
        df = _s3_run(c, cfg, s3["open_model"], prompt, "S3-open", v, "open", repeat=repeat)
        out.append(df)
        if v == "D0" and repeat == 0:
            sc = df.set_index("post_id")["raw_score"]
            out.append(_frame(c, aggregate_top_k_sum(c.posts, sc, cfg["aggregation"]["k"]), "S3-open", "D3-agg", model_id=s3["open_model"], prompt_version=prompt))
    return out


def run_s3_blind(c: Corpus, cfg: dict, variants: tuple[str, ...] = ("D0", "D3-nat")) -> list[pd.DataFrame]:
    s3 = cfg["selectors"]["s3"]
    out = []
    for v in variants:
        prompt = s3["prompt_blind_d0"] if v == "D0" else s3["prompt_blind_d3nat"]
        out.append(_s3_run(c, cfg, s3["open_model"], prompt, "S3-blind", v, "blind"))
    return out


def control_subsample(c: Corpus, cfg: dict, seed: int = 0) -> list[str]:
    """~10 % of posts at random plus every target-arc signal post (so the control covers the decisive cases)."""
    rng = np.random.default_rng(seed)
    ids = c.posts.post_id.tolist()
    n = int(round(cfg["selectors"]["s3"]["control_fraction"] * len(ids)))
    pick = set(rng.choice(ids, size=n, replace=False).tolist()) | c.signal_post_ids
    return [p for p in ids if p in pick]


def run_s3_control(c: Corpus, cfg: dict, variants: tuple[str, ...] = ("D0", "D3-nat")) -> list[pd.DataFrame]:
    s3 = cfg["selectors"]["s3"]
    sub = control_subsample(c, cfg)
    (cfg["results_dir"] / c.name).mkdir(parents=True, exist_ok=True)
    (cfg["results_dir"] / c.name / "control_subsample.json").write_text(json.dumps(sub))
    out = []
    for v in variants:
        prompt = s3["prompt_d0"] if v == "D0" else s3["prompt_d3nat"]
        out.append(_s3_run(c, cfg, s3["control_model"], prompt, "S3-com", v, "com", subset=sub))
    return out


def run_srand(c: Corpus, cfg: dict) -> list[pd.DataFrame]:
    return [_frame(c, random_scores(c.posts.post_id.tolist(), s), f"S-rand{s}", "D0", model_id="random") for s in cfg["rand_seeds"]]
