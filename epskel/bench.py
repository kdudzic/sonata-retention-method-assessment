"""Benchmark runners.

Stage A (models):  same personas, same attribute draws, same arcs; one model per run.
                   Output: bench/stageA/<model_slug>.jsonl (one Post per line) + cost summary.
Stage B (methods): best models x method variants on the background layer.
                   Output: bench/stageB/<model_slug>__<method>.jsonl
"""

from __future__ import annotations

import json
import random
import re
import sys
import time
from pathlib import Path

from . import config
from .gen import ARCS, ArcGenerator, BackgroundGenerator, HardNegGenerator, Post, messages_from, parse_json, sample_attrs, sample_hidden
from .llm import LLM
from .personas import forbidden_hits, load_personas, save_personas


def slug(model: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", model.lower()).strip("_")


def write_posts(posts: list[Post], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for p in posts:
            f.write(json.dumps(p.to_dict(), ensure_ascii=False) + "\n")


def read_posts(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


# ----------------------------------------------------------------------------- arc personas
def arc_persona_cards(llm: LLM, arc_ids: list[str] | None = None, out: Path | None = None) -> dict[str, dict]:
    """One Annex J card per arc, expanded from the PI's sketch. Cached in data/arc_personas.json."""
    out = out or (config.DATA / "arc_personas.json")
    cards: dict[str, dict] = json.loads(out.read_text(encoding="utf-8")) if out.exists() else {}
    for arc in ARCS:
        if arc_ids and arc["arc_id"] not in arc_ids:
            continue
        if arc["arc_id"] in cards:
            continue
        for _ in range(3):
            r = llm.chat(messages_from("persona_from_sketch_v1.md", sketch=arc["persona_sketch"]),
                         tag=f"arc_persona_{arc['arc_id']}", temperature=0.7, max_tokens=900)
            try:
                c = parse_json(r.text)
                assert isinstance(c, dict) and "writing_style" in c
            except Exception:
                continue
            c["author_id"] = f"T{arc['arc_id'][1:]}"  # TA-01 -> TA-01 kept readable
            c["author_id"] = arc["arc_id"].replace("-", "")
            c["sketch"] = arc["persona_sketch"]
            c["forbidden_hits"] = forbidden_hits({k: v for k, v in c.items() if k != "sketch"})
            cards[arc["arc_id"]] = c
            break
    out.write_text(json.dumps(cards, ensure_ascii=False, indent=1), encoding="utf-8")
    return cards


# ----------------------------------------------------------------------------- stage A
def run_stage_a(model: str, personas: list[dict], arc_cards: dict[str, dict], arc_ids: list[str],
                n_bg_per_persona: int = 5, n_hardneg: int = 12, seed: int = 11, workers: int = 6,
                temperature: float = 1.0, bg_prompt: str = "background_v1", hn_prompt: str = "hardneg_v1",
                arc_prompt: str = "arc_post_v1", stage_dir: str = "stageA") -> dict:
    out_path = config.BENCH / stage_dir / f"{slug(model)}.jsonl"
    llm = LLM(model, run_name=f"stageA_{slug(model)}", temperature=temperature, max_tokens=4000)
    t0 = time.time()
    posts: list[Post] = []
    errors: list[str] = []

    # background: fixed attribute draws per persona index (same across models)
    bg = BackgroundGenerator(llm, method="single", seed=seed, prompt_version=bg_prompt)

    def bg_job(card):
        try:
            return bg.generate_for_author(card, n_bg_per_persona)
        except Exception as e:
            errors.append(f"bg {card['author_id']}: {e}")
            return []

    if n_bg_per_persona > 0:
        for res in llm.map(personas, bg_job, workers=workers, desc=f"{slug(model)} bg"):
            if isinstance(res, list):
                posts.extend(res)

    # hard negatives: one per persona (hidden draws fixed by seed)
    hn = HardNegGenerator(llm, seed=seed, prompt_version=hn_prompt)
    hidden_draws = [sample_hidden(random.Random(seed + i)) for i in range(n_hardneg)]

    def hn_job(args):
        card, h = args
        try:
            return hn.generate(card, h)
        except Exception as e:
            errors.append(f"hn {card['author_id']}: {e}")
            return None

    for res in llm.map(list(zip(personas * 3, hidden_draws)), hn_job, workers=workers, desc=f"{slug(model)} hn"):
        if isinstance(res, Post):
            posts.append(res)

    # arcs: sequential inside an arc, arcs in parallel
    ag = ArcGenerator(llm, seed=seed, prompt_version=arc_prompt)

    def arc_job(arc_id):
        arc = next(a for a in ARCS if a["arc_id"] == arc_id)
        try:
            return ag.generate_arc(arc, arc_cards[arc_id])
        except Exception as e:
            errors.append(f"arc {arc_id}: {e}")
            return []

    for res in llm.map(arc_ids, arc_job, workers=min(workers, len(arc_ids)), desc=f"{slug(model)} arcs"):
        if isinstance(res, list):
            posts.extend(res)

    write_posts(posts, out_path)
    summ = {
        "model": model, "n_posts": len(posts), "cost": llm.total_cost, "calls": llm.n_calls,
        "prompt_tokens": llm.n_prompt_tokens, "completion_tokens": llm.n_completion_tokens,
        "elapsed_s": round(time.time() - t0, 1), "refusals": sum(p.refused for p in posts),
        "empty": sum(1 for p in posts if not p.text.strip()), "errors": errors, "reasoning": llm.extra_body.get("reasoning"),
    }
    (config.BENCH / stage_dir / f"{slug(model)}.summary.json").write_text(json.dumps(summ, indent=1, ensure_ascii=False))
    return summ


# ----------------------------------------------------------------------------- stage B
def run_stage_b(model: str, method: str, personas: list[dict], n_per_persona: int = 5, seed: int = 11,
                workers: int = 6, temperature: float = 1.0, k: int = 5, tau: float = 0.10,
                rewrite_model: str | None = None) -> dict:
    out_path = config.BENCH / "stageB" / f"{slug(model)}__{method}.jsonl"
    llm = LLM(model, run_name=f"stageB_{slug(model)}_{method}", temperature=temperature, max_tokens=6000)
    rl = LLM(rewrite_model, run_name=f"stageB_{slug(model)}_{method}_rw", temperature=temperature, max_tokens=4000) if rewrite_model else None
    bg = BackgroundGenerator(llm, method=method, k=k, tau=tau, seed=seed, rewrite_llm=rl)
    t0 = time.time()
    posts: list[Post] = []
    errors: list[str] = []

    def job(card):
        try:
            return bg.generate_for_author(card, n_per_persona)
        except Exception as e:
            errors.append(f"{card['author_id']}: {e}")
            return []

    for res in llm.map(personas, job, workers=workers, desc=f"{slug(model)} {method}"):
        if isinstance(res, list):
            posts.extend(res)
    write_posts(posts, out_path)
    cost = llm.total_cost + (rl.total_cost if rl else 0.0)
    summ = {"model": model, "method": method, "n_posts": len(posts), "cost": cost, "calls": llm.n_calls + (rl.n_calls if rl else 0),
            "elapsed_s": round(time.time() - t0, 1), "refusals": sum(p.refused for p in posts), "errors": errors}
    (config.BENCH / "stageB" / f"{slug(model)}__{method}.summary.json").write_text(json.dumps(summ, indent=1, ensure_ascii=False))
    return summ
