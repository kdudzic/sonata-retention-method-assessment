"""Stage A evaluation: automatic metrics + judges per model. Usage: uv run python bench/eval_stage_a.py [judge_model]"""
import json, sys, glob, random
from pathlib import Path
from epskel import config
from epskel.bench import read_posts, slug
from epskel.evaluate import auto_eval, judge_natural, natural_summary, judge_brief, brief_summary, judge_persona, persona_summary, reference
from epskel.llm import LLM, looks_like_refusal
from epskel.personas import load_personas
from epskel.metrics import length_matched_sample

JUDGE = sys.argv[1] if len(sys.argv) > 1 else "openai/gpt-6-sol"
personas = load_personas("bench/personas_bench12.json")
arc_cards = json.load(open("data/arc_personas.json"))
cards_by_author = {c["author_id"]: c for c in personas}
cards_by_author.update({v["author_id"]: v for v in arc_cards.values()})
judge = LLM(JUDGE, run_name=f"judge_{slug(JUDGE)}", temperature=0.0, max_tokens=3000)

rows = []
files = sorted(glob.glob("bench/stageA/*.jsonl"))
# shared reference sample for the naturalness judge (same for all models)
rng = random.Random(0)
ref_all = reference()
for f in files:
    P = read_posts(Path(f))
    model = P[0]["model"]
    for p in P:
        p["refused"] = looks_like_refusal(p["text"])
    bg = [p for p in P if p["layer"] == "background" and not p["refused"]]
    hn = [p for p in P if p["layer"] == "hardneg"]
    arc = [p for p in P if p["layer"] == "arc"]
    row = {"model": model, "n_bg": len(bg), "n_hn": len(hn), "n_arc": len(arc),
           "refusal_bg": sum(p["refused"] for p in P if p["layer"] == "background"),
           "refusal_hn": sum(p["refused"] for p in hn), "refusal_arc": sum(p["refused"] for p in arc)}
    summ = json.load(open(f.replace(".jsonl", ".summary.json")))
    row["cost_usd"] = summ["cost"]; row["elapsed_s"] = summ["elapsed_s"]
    texts = [p["text"] for p in bg]
    row.update(auto_eval(slug(model), texts))
    # naturalness judge: bg posts vs length-matched real posts
    ref = length_matched_sample(ref_all, texts, seed=1)
    jn = judge_natural(judge, texts, ref)
    row.update(natural_summary(jn, texts, ref))
    # brief judge on arcs + hardneg
    jb = judge_brief(judge, arc + hn, cards_by_author)
    row.update({f"arc_{k}": v for k, v in brief_summary(jb[:len(arc)], arc).items()})
    row.update({f"hn_{k}": v for k, v in brief_summary(jb[len(arc):], hn).items()})
    # persona judge on bg
    by_author = {}
    for p in bg:
        by_author.setdefault(p["author_id"], []).append(p["text"])
    row.update(persona_summary(judge_persona(judge, personas, by_author)))
    rows.append(row)
    print(json.dumps({k: (round(v, 3) if isinstance(v, float) else v) for k, v in row.items() if not k.startswith("det_tells") and k not in ("ai_ism_top", "judge_tells_top")}, ensure_ascii=False), flush=True)
    # store per-post judgements for inspection
    Path("bench/stageA_judged").mkdir(exist_ok=True)
    with open(f"bench/stageA_judged/{slug(model)}__{slug(JUDGE)}.jsonl", "w", encoding="utf-8") as fo:
        for p, j in zip(arc + hn, jb):
            fo.write(json.dumps({"layer": p["layer"], "attrs": p["attrs"], "text": p["text"], "judge": j}, ensure_ascii=False) + "\n")
json.dump(rows, open(f"bench/stageA_results__{slug(JUDGE)}.json", "w"), ensure_ascii=False, indent=1)
print("judge cost", judge.summary())
