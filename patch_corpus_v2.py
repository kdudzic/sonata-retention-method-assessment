"""Corpus v2 = v1 + the PI's corrections of 2026-10-13.

1. TA-04 #4 regenerated with the new brief ("banderowcy" + venue + "jutro wieczorem" + 1st person plural + euphemism).
2. TB-08 #7 split into two posts of one exchange on the same day: new #7 (date + coordination only) and new #8
   (slur + euphemised act, no date); old #8-#12 become #9-#13, timestamps unchanged.
3. Author identifiers: all 200 authors re-drawn at random from one pool A001-A200, so the identifier no longer
   reveals arc authors (was TA01, TB08, ...). Mapping kept in author_id_map_v2.csv, outside the posts table.
   Post identifiers reassigned in (author, timestamp) order for the same reason.

Only the three posts named above are generated; everything else is carried over verbatim.
Usage: uv run python patch_corpus_v2.py [--dry]
"""

from __future__ import annotations

import hashlib
import json
import random
import sys
from datetime import datetime, timedelta

import pandas as pd

from epskel import config
from epskel.gen import ARCS, INSTR_SINGLE, OUT_SINGLE, messages_from, parse_single, style_flags
from epskel.llm import LLM, looks_like_refusal
from epskel.personas import render_card

D = config.CORPUS / "epskel_v1"
MODEL = "openai/gpt-6-sol"
SEED = 20261013
DRY = "--dry" in sys.argv


def gen_post(llm: LLM, arc: dict, card: dict, n: int, prev_texts: list[str], prev_day: int, rng: random.Random) -> tuple[str, str, str]:
    p = next(x for x in arc["posts"] if x["n"] == n)
    r = llm.chat(messages_from("situation_summary_v1.md", posts="\n".join(f"- {t}" for t in prev_texts)), tag="arc_summary", temperature=0.3)
    situation = r.text.strip().splitlines()[0]
    msgs = messages_from("arc_post_v2.md", output_instruction=INSTR_SINGLE, output_format=OUT_SINGLE, persona_card=render_card(card),
                         n=n, total=len(arc["posts"]), gap_days=p["day"] - prev_day, situation_so_far=situation,
                         previous_post=prev_texts[-1], arc_role=p["role"], post_brief=p["brief"], post_level_profile=p["profile"],
                         **style_flags(rng, p_tic=0.30, p_local=0.20))
    for attempt in range(3):
        r = llm.chat(msgs, tag=f"arc_{arc['arc_id']}_{n}", seed=rng.randint(0, 2**31))
        text = parse_single(r.text)
        if text.strip() and not looks_like_refusal(text):
            return text, r.call_id, situation
        print(f"  attempt {attempt}: refusal/empty: {text[:80]!r}")
    raise RuntimeError(f"could not generate {arc['arc_id']} #{n}")


def main() -> None:
    rng = random.Random(SEED)
    posts = pd.read_csv(D / "posts_v1.csv", dtype=str).fillna("")
    authors = pd.read_csv(D / "authors_v1.csv", dtype=str).fillna("")
    key = pd.read_csv(D / "arc_key_v1.csv", dtype=str).fillna("")
    arc_cards = json.loads((config.DATA / "arc_personas.json").read_text(encoding="utf-8"))
    arcs = {a["arc_id"]: a for a in ARCS}
    llm = LLM(MODEL, run_name="corpus_epskel_v2_patch", temperature=1.0, max_tokens=4000)
    changes = []

    def arc_posts(arc_id):
        sub = posts[posts.arc_id == arc_id].copy()
        sub["pos"] = sub.arc_position.astype(int)
        return sub.sort_values("pos")

    # ---- 1. TA-04 #4 (previous post #3 is on day 8)
    ta = arc_posts("TA-04")
    prev = ta[ta.pos < 4].text.tolist()
    text, cid, sit = gen_post(llm, arcs["TA-04"], arc_cards["TA-04"], 4, prev, 8, rng)
    i = ta[ta.pos == 4].index[0]
    changes.append(("TA-04", 4, posts.at[i, "text"], text))
    posts.at[i, "text"] = text; posts.at[i, "call_ids"] = cid; posts.at[i, "prompt_version"] = "arc_post_v2"; posts.at[i, "source_template"] = "arc_post_v2|pi_20261013"
    posts.at[i, "latent_factors_json"] = json.dumps({"brief": arcs["TA-04"]["posts"][3]["brief"], "situation_so_far": sit}, ensure_ascii=False)

    # ---- 2. TB-08 split (#6 is on day 20, #7 and #8 on day 24)
    tb = arc_posts("TB-08")
    prev = tb[tb.pos < 7].text.tolist()
    t7, c7, s7 = gen_post(llm, arcs["TB-08"], arc_cards["TB-08"], 7, prev, 20, rng)
    t8, c8, s8 = gen_post(llm, arcs["TB-08"], arc_cards["TB-08"], 8, prev + [t7], 24, rng)
    i7 = tb[tb.pos == 7].index[0]
    changes.append(("TB-08", 7, posts.at[i7, "text"], t7)); changes.append(("TB-08", 8, "(new)", t8))
    posts.at[i7, "text"] = t7; posts.at[i7, "call_ids"] = c7; posts.at[i7, "source_template"] = "arc_post_v2|pi_20261013"
    posts.at[i7, "latent_factors_json"] = json.dumps({"brief": arcs["TB-08"]["posts"][6]["brief"], "situation_so_far": s7}, ensure_ascii=False)
    for _, row in tb[tb.pos >= 8].iterrows():
        posts.at[row.name, "arc_position"] = str(int(row.pos) + 1)
    ts7 = datetime.fromisoformat(posts.at[i7, "timestamp"])
    ts8 = ts7 + timedelta(minutes=rng.randint(20, 90))
    new8 = posts.loc[i7].copy()
    new8["text"] = t8; new8["call_ids"] = c8; new8["arc_position"] = "8"; new8["timestamp"] = ts8.strftime("%Y-%m-%dT%H:%M:%S")
    new8["latent_factors_json"] = json.dumps({"brief": arcs["TB-08"]["posts"][7]["brief"], "situation_so_far": s8}, ensure_ascii=False)
    new8["post_id"] = "NEW"
    posts = pd.concat([posts, new8.to_frame().T], ignore_index=True)
    for p in arcs["TB-08"]["posts"]:
        m = (posts.arc_id == "TB-08") & (posts.arc_position == str(p["n"]))
        posts.loc[m, "arc_role"] = p["role"]; posts.loc[m, "post_level_profile"] = p["profile"]
    key = key[key.arc_id != "TB-08"]
    a = arcs["TB-08"]
    key = pd.concat([key, pd.DataFrame([{"arc_id": "TB-08", "arc_type": a["arc_type"], "arc_position": str(p["n"]),
                                         "is_signal": str(p["n"] in a["signal_posts"]), "legal_relevance_focus": a["legal_relevance_focus"]} for p in a["posts"]])], ignore_index=True)

    # ---- 3. author ids from one pool; post ids reassigned
    old_ids = authors.author_id.tolist()
    new_pool = [f"A{i+1:03d}" for i in range(len(old_ids))]
    rng.shuffle(new_pool)
    amap = dict(zip(old_ids, new_pool))
    posts["author_id"] = posts.author_id.map(amap); authors["author_id"] = authors.author_id.map(amap)
    posts = posts.sort_values(["author_id", "timestamp"]).reset_index(drop=True)
    posts["post_id"] = [f"P{i+1:05d}" for i in range(len(posts))]
    authors = authors.sort_values("author_id").reset_index(drop=True)
    for i, r in authors.iterrows():
        sub = posts[posts.author_id == r.author_id]
        authors.at[i, "n_posts"] = str(len(sub)); authors.at[i, "first_post_ts"] = sub.timestamp.min(); authors.at[i, "last_post_ts"] = sub.timestamp.max()
    arc_of = authors.set_index("author_id").arc_id
    amap_df = pd.DataFrame({"author_id_v2": [amap[o] for o in old_ids], "author_id_v1": old_ids,
                            "arc_id": [arc_of[amap[o]] for o in old_ids]}).sort_values("author_id_v2")

    for arc_id, n, old, new in changes:
        print(f"{arc_id} #{n}\n  OLD: {old[:160]}\n  NEW: {new[:220]}")
    print(llm.summary())
    if DRY:
        return
    posts.to_csv(D / "posts_v2.csv", index=False); authors.to_csv(D / "authors_v2.csv", index=False)
    key.to_csv(D / "arc_key_v2.csv", index=False); amap_df.to_csv(D / "author_id_map_v2.csv", index=False)
    m1 = json.loads((D / "manifest_v1.json").read_text())
    m2 = dict(m1, version="v2", built=datetime.now().isoformat(timespec="seconds"), based_on="v1",
              changes=["TA-04 #4 regenerated (PI 2026-10-13 brief)", "TB-08 #7 split into #7/#8, old #8-#12 -> #9-#13",
                       "author ids re-drawn from one pool, post ids reassigned; map in author_id_map_v2.csv"],
              n_posts=int(len(posts)), layers=posts.layer.value_counts().to_dict(), patch_model=MODEL, patch_seed=SEED, patch_cost_usd=llm.total_cost,
              sha256_posts=hashlib.sha256((D / "posts_v2.csv").read_bytes()).hexdigest(), sha256_authors=hashlib.sha256((D / "authors_v2.csv").read_bytes()).hexdigest())
    (D / "manifest_v2.json").write_text(json.dumps(m2, indent=1, ensure_ascii=False))
    print("written v2:", len(posts), "posts,", len(authors), "authors")


if __name__ == "__main__":
    main()
