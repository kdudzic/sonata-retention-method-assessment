"""Add the two dev arcs (configs/arc_split.yaml: dev) to the dev corpus with NEW persona cards and a NEW seed.

Plan: the dev corpus has 600 posts + 2 arcs from different generation seeds; the PI (2026-10-23) asked for
"other persons, other seed" so that selector parameters can be tuned without looking at the evaluation corpus.

Steps
  1. persona cards for the dev arcs expanded again from the PI's sketches (data/arc_personas_dev.json), checked to
     differ from the evaluation cards in local reference, tic and life situation
  2. arc posts generated with ArcGenerator (prompt arc_post_v2, seed 7331 + 5)
  3. dev corpus re-assembled as posts_dev2.csv etc. from the existing background/hardneg + the new arcs,
     with author ids re-drawn from one pool (A001-A032) and post ids in (author, timestamp) order; map in
     author_id_map_dev2.csv
Usage: uv run python build_dev_arcs.py
"""

from __future__ import annotations

import hashlib
import json
import random
from datetime import datetime

import pandas as pd
import yaml

from epskel import config
from epskel.bench import arc_persona_cards
from epskel.build_corpus import CorpusBuilder, _jsonl_read, _jsonl_write
from epskel.gen import ARCS, ArcGenerator
from epskel.llm import LLM, looks_like_refusal

NAME = "epskel_dev_v1"
D = config.CORPUS / NAME
MODEL = "openai/gpt-6-sol"
SEED = 7331
split = yaml.safe_load((config.ROOT / "experiment" / "configs" / "arc_split.yaml").read_text(encoding="utf-8"))
DEV_ARCS = split["dev"]


def main() -> None:
    llm = LLM(MODEL, run_name=f"corpus_{NAME}_arcs", temperature=1.0, max_tokens=4000)
    # 1. new persona cards (separate cache file; generation is sampled, so cards differ from the eval ones)
    out = config.DATA / "arc_personas_dev.json"
    cards = arc_persona_cards(llm, arc_ids=DEV_ARCS, out=out)
    eval_cards = json.loads((config.DATA / "arc_personas.json").read_text(encoding="utf-8"))
    for a in DEV_ARCS:
        same = [k for k in ("local_reference", "verbal_tic", "life_situation") if cards[a].get(k) == eval_cards[a].get(k)]
        if same:
            raise SystemExit(f"{a}: dev card repeats eval card fields {same}; delete {out} and rerun")
        print(f"{a} dev card: {cards[a]['local_reference']} | tic: {cards[a]['verbal_tic']}")
    # 2. arc posts
    path = D / "arcs.jsonl"
    done = {d["attrs"]["arc_id"] for d in _jsonl_read(path)}
    gen = ArcGenerator(llm, seed=SEED + 5, prompt_version="arc_post_v2")
    for a in DEV_ARCS:
        if a in done:
            continue
        arc = next(x for x in ARCS if x["arc_id"] == a)
        ps = gen.generate_arc(arc, cards[a])
        bad = [p.attrs["n"] for p in ps if looks_like_refusal(p.text) or not p.text.strip()]
        if bad:
            raise SystemExit(f"{a}: refusal/empty at positions {bad}; fix and rerun (nothing written for this arc)")
        _jsonl_write(ps, path)
        print(f"{a}: {len(ps)} posts, ${gen.llm.total_cost:.3f} so far")
    # 3. assemble dev2
    personas = json.loads((D / "personas.json").read_text(encoding="utf-8"))
    b = CorpusBuilder(NAME, MODEL, "spec_first", 30, 500, 100, DEV_ARCS, SEED, datetime(2025, 10, 6))
    posts, authors = b.assemble(personas, cards, _jsonl_read(D / "background.jsonl"), _jsonl_read(D / "hardneg.jsonl"),
                                _jsonl_read(path), version="dev2")
    # blind ids
    rng = random.Random(SEED + 9)
    old_ids = authors.author_id.tolist()
    pool = [f"A{i+1:03d}" for i in range(len(old_ids))]
    rng.shuffle(pool)
    amap = dict(zip(old_ids, pool))
    posts["author_id"] = posts.author_id.map(amap); authors["author_id"] = authors.author_id.map(amap)
    posts = posts.sort_values(["author_id", "timestamp"]).reset_index(drop=True)
    posts["post_id"] = [f"P{i+1:05d}" for i in range(len(posts))]
    authors = authors.sort_values("author_id").reset_index(drop=True)
    posts.to_csv(D / "posts_dev2.csv", index=False); authors.to_csv(D / "authors_dev2.csv", index=False)
    pd.DataFrame({"author_id_dev2": [amap[o] for o in old_ids], "author_id_build": old_ids,
                  "arc_id": [authors.set_index("author_id").arc_id[amap[o]] for o in old_ids]}).sort_values("author_id_dev2").to_csv(D / "author_id_map_dev2.csv", index=False)
    m = json.loads((D / "manifest_dev2.json").read_text(encoding="utf-8"))
    m.update(version="dev2", arcs=DEV_ARCS, arc_persona_file="data/arc_personas_dev.json", arc_seed=SEED + 5,
             note="dev arcs generated with new persona cards and seed per PI 2026-10-23; author/post ids re-drawn",
             sha256_posts=hashlib.sha256((D / "posts_dev2.csv").read_bytes()).hexdigest(),
             sha256_authors=hashlib.sha256((D / "authors_dev2.csv").read_bytes()).hexdigest(), cost_usd_arcs=llm.total_cost)
    (D / "manifest_dev2.json").write_text(json.dumps(m, indent=1, ensure_ascii=False))
    print("dev2:", len(posts), "posts,", len(authors), "authors;", llm.summary())


if __name__ == "__main__":
    main()
