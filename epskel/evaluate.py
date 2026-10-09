"""Evaluation of generated post sets: automatic metrics + LLM judges.

Automatic (metrics.py): lexical diversity, semantic diversity/duplication, surface feature gap vs a
length-matched real Polish reference (TwitterEmo-PL), char/word n-gram detector AUC.

Judges (prompts/judge_*.md):
  natural  - blind human-vs-synthetic probability on mixed batches (synthetic + real reference), per post
  brief    - brief compliance / sanitisation / single-post retention profile (arc posts, hard negatives)
  persona  - persona consistency over an author's posts

Judge outputs are cached per (judge_model, prompt_version, text hash) under bench/judge_cache/ so that
re-running an evaluation never re-pays for a judged post.
"""

from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path

import numpy as np

from . import config, metrics
from .gen import messages_from, parse_json
from .llm import LLM
from .personas import render_card

CACHE = config.BENCH / "judge_cache"
CACHE.mkdir(parents=True, exist_ok=True)


def _ckey(judge: str, pv: str, payload: str) -> Path:
    h = hashlib.sha1(f"{judge}|{pv}|{payload}".encode("utf-8")).hexdigest()
    return CACHE / f"{h}.json"


def _cached(judge: str, pv: str, payload: str):
    p = _ckey(judge, pv, payload)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def _store(judge: str, pv: str, payload: str, value) -> None:
    _ckey(judge, pv, payload).write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


# ----------------------------------------------------------------------------- automatic
_REF_CACHE: list[str] | None = None


def reference(n: int = 4000, seed: int = 0) -> list[str]:
    global _REF_CACHE
    if _REF_CACHE is None:
        _REF_CACHE = metrics.load_reference(config.DATA / "ref" / "twitteremo_final.csv", seed=seed, n=None)
    return _REF_CACHE


def auto_eval(name: str, texts: list[str], with_detector: bool = True, seed: int = 0) -> dict:
    texts = [t for t in texts if t.strip()]
    E = metrics.embed(texts)
    rep = metrics.report_set(name, texts, E=E, with_bleu=len(texts) <= 400)
    out = rep.flat()
    ref = metrics.length_matched_sample(reference(), texts, seed=seed, mult=1)
    if ref:
        rref = metrics.report_set(f"{name}__ref", ref, with_bleu=len(ref) <= 400)
        for k, v in rref.surface.items():
            if k != "ai_ism_top":
                out[f"ref_surf_{k}"] = v
        for k, v in rref.lexical.items():
            out[f"ref_lex_{k}"] = v
        for k, v in rref.semantic.items():
            out[f"ref_sem_{k}"] = v
        if with_detector and len(texts) >= 40:
            det = metrics.detector_auc(texts, ref, seed=seed)
            out.update({f"det_{k}": v for k, v in det.items()})
    out["ai_ism_top"] = rep.surface.get("ai_ism_top")
    return out


# ----------------------------------------------------------------------------- judges
def judge_natural(judge: LLM, synth: list[str], ref: list[str], batch: int = 10, seed: int = 0,
                  pv: str = "judge_natural_v1", workers: int = 6) -> dict:
    """Returns per-text judgements {text: {p_ai, polish, tells}} for both synthetic and reference posts."""
    rng = random.Random(seed)
    items = [("S", t) for t in synth] + [("R", t) for t in ref]
    rng.shuffle(items)
    results: dict[str, dict] = {}
    todo = [it for it in items if _cached(judge.model, pv, it[1]) is None]
    for it in items:
        c = _cached(judge.model, pv, it[1])
        if c is not None:
            results[it[1]] = c
    batches = [todo[i : i + batch] for i in range(0, len(todo), batch)]

    def job(b):
        listing = "\n".join(f"[{i+1}] {t}" for i, (_, t) in enumerate(b))
        r = judge.chat(messages_from(f"{pv}.md", posts=listing), tag="judge_natural", temperature=0.0, max_tokens=250 * len(b) + 100)
        try:
            arr = parse_json(r.text)
            assert isinstance(arr, list)
        except Exception:
            return []
        out = []
        for i, (_, t) in enumerate(b):
            o = next((x for x in arr if str(x.get("id")) in (str(i + 1), f"[{i+1}]")), None) or (arr[i] if i < len(arr) else None)
            if isinstance(o, dict) and "p_ai" in o:
                val = {"p_ai": float(o["p_ai"]), "polish": o.get("polish"), "tells": o.get("tells", [])}
                _store(judge.model, pv, t, val)
                out.append((t, val))
        return out

    for res in judge.map(batches, job, workers=workers, desc="judge_natural"):
        if isinstance(res, list):
            for t, v in res:
                results[t] = v
    return results


def natural_summary(results: dict, synth: list[str], ref: list[str]) -> dict:
    from sklearn.metrics import roc_auc_score

    ps = [results[t]["p_ai"] for t in synth if t in results]
    pr = [results[t]["p_ai"] for t in ref if t in results]
    pol = [results[t]["polish"] for t in synth if t in results and isinstance(results[t].get("polish"), (int, float))]
    tells: dict[str, int] = {}
    for t in synth:
        for x in results.get(t, {}).get("tells", []) or []:
            tells[x.lower()] = tells.get(x.lower(), 0) + 1
    y = [1] * len(ps) + [0] * len(pr)
    auc = roc_auc_score(y, ps + pr) if ps and pr else None
    return {
        "judge_p_ai_mean": float(np.mean(ps)) if ps else None,
        "judge_p_ai_ref_mean": float(np.mean(pr)) if pr else None,
        "judge_auc": float(auc) if auc is not None else None,
        "judge_polish_mean": float(np.mean(pol)) if pol else None,
        "judge_n": len(ps),
        "judge_tells_top": sorted(tells.items(), key=lambda kv: -kv[1])[:10],
    }


def judge_brief(judge: LLM, posts: list[dict], cards: dict[str, dict], pv: str = "judge_brief_v1", workers: int = 6) -> list[dict]:
    """posts: Post dicts from arc or hardneg layers. Returns list of judgement dicts aligned with posts."""

    def payload(p: dict) -> tuple[str, str, str]:
        a = p["attrs"]
        if p["layer"] == "arc":
            brief, profile = a["brief"], a["profile"]
        else:
            brief = "; ".join(f"{k}={v}" for k, v in a.items() if k != "topic_hint") + f"; topic: {a.get('topic_hint','')}"
            profile = a["retention_profile"]
        card = cards.get(p["author_id"]) or {}
        style = card.get("sketch") or (render_card(card) if card else "-")
        return brief, profile, style

    def job(p):
        brief, profile, style = payload(p)
        key = json.dumps([brief, profile, p["text"]], ensure_ascii=False)
        c = _cached(judge.model, pv, key)
        if c is not None:
            return c
        r = judge.chat(messages_from(f"{pv}.md", brief=brief, profile=profile, style=style, post=p["text"]),
                       tag="judge_brief", temperature=0.0, max_tokens=400)
        try:
            o = parse_json(r.text)
            assert isinstance(o, dict)
        except Exception:
            o = {"error": r.text[:200]}
        _store(judge.model, pv, key, o)
        return o

    res = judge.map(posts, job, workers=workers, desc="judge_brief")
    return [r if isinstance(r, dict) else {"error": str(r)} for r in res]


def judge_persona(judge: LLM, cards: list[dict], posts_by_author: dict[str, list[str]], pv: str = "judge_persona_v1", workers: int = 6) -> dict[str, dict]:
    def job(card):
        ps = posts_by_author.get(card["author_id"], [])
        if not ps:
            return card["author_id"], {}
        key = json.dumps([card["author_id"], ps], ensure_ascii=False)
        c = _cached(judge.model, pv, key)
        if c is not None:
            return card["author_id"], c
        listing = "\n".join(f"{i+1}. {t}" for i, t in enumerate(ps))
        r = judge.chat(messages_from(f"{pv}.md", persona_card=render_card(card), posts=listing), tag="judge_persona", temperature=0.0, max_tokens=400)
        try:
            o = parse_json(r.text)
        except Exception:
            o = {"error": r.text[:200]}
        _store(judge.model, pv, key, o)
        return card["author_id"], o

    out = {}
    for res in judge.map(cards, job, workers=workers, desc="judge_persona"):
        if isinstance(res, tuple):
            out[res[0]] = res[1]
    return out


def persona_summary(j: dict[str, dict]) -> dict:
    vals = [v for v in j.values() if v and "consistency" not in v.get("error", "")]
    def m(k):
        xs = [v[k] for v in vals if isinstance(v.get(k), (int, float))]
        return float(np.mean(xs)) if xs else None
    def f(k):
        xs = [bool(v.get(k)) for v in vals if k in v]
        return float(np.mean(xs)) if xs else None
    return {"persona_consistency": m("consistency"), "persona_voice": m("voice_stability"), "persona_tic_overuse": f("tic_overuse"),
            "persona_repetitive": f("repetitive_structure"), "persona_topic_variety": m("topic_variety"), "persona_natural": m("natural_overall")}


def brief_summary(js: list[dict], posts: list[dict]) -> dict:
    ok = [(j, p) for j, p in zip(js, posts) if "error" not in j]
    if not ok:
        return {}
    n = len(ok)
    refus = sum(1 for j, _ in ok if j.get("is_refusal"))
    full = sum(1 for j, _ in ok if j.get("brief_fulfilled") == 2)
    san = sum(1 for j, _ in ok if j.get("sanitised"))
    prof_ok = sum(1 for j, p in ok if j.get("observed_profile") == (p["attrs"].get("profile") or p["attrs"].get("retention_profile")))
    # the critical failure for distributed arcs: a borderline/discard post that reads as clear_keep
    leak = sum(1 for j, p in ok if (p["attrs"].get("profile") or p["attrs"].get("retention_profile")) != "clear_keep" and j.get("observed_profile") == "clear_keep")
    # concentrated signal posts that fail to read as clear_keep
    miss = sum(1 for j, p in ok if (p["attrs"].get("profile") or p["attrs"].get("retention_profile")) == "clear_keep" and j.get("observed_profile") != "clear_keep")
    nat = [j["natural"] for j, _ in ok if isinstance(j.get("natural"), (int, float))]
    sty = [j["style_match"] for j, _ in ok if isinstance(j.get("style_match"), (int, float))]
    return {"brief_n": n, "brief_refusal_rate": refus / n, "brief_full_rate": full / n, "brief_sanitised_rate": san / n,
            "brief_profile_match": prof_ok / n, "brief_keep_leak": leak, "brief_keep_miss": miss,
            "brief_natural": float(np.mean(nat)) if nat else None, "brief_style": float(np.mean(sty)) if sty else None}
