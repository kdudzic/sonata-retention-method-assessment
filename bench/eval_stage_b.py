"""Stage B evaluation (methods): auto metrics + naturalness judge + persona judge. Usage: uv run python bench/eval_stage_b.py JUDGE_MODEL"""
import json, sys, glob, random
from pathlib import Path
from epskel.bench import read_posts, slug
from epskel.evaluate import auto_eval, judge_natural, natural_summary, judge_persona, persona_summary, reference
from epskel.llm import LLM, looks_like_refusal
from epskel.personas import load_personas
from epskel.metrics import length_matched_sample

JUDGE = sys.argv[1] if len(sys.argv) > 1 else "openai/gpt-6-sol"
personas = load_personas("bench/personas_bench12.json")
judge = LLM(JUDGE, run_name=f"judge_{slug(JUDGE)}", temperature=0.0, max_tokens=3000)
ref_all = reference()
rows = []
for f in sorted(glob.glob("bench/stageB/*.jsonl")):
    P = read_posts(Path(f))
    model, method = P[0]["model"], P[0]["method"]
    texts = [p["text"] for p in P if p["text"].strip() and not looks_like_refusal(p["text"])]
    summ = json.load(open(f.replace(".jsonl", ".summary.json")))
    row = {"model": model, "method": method, "n": len(texts), "cost_usd": summ["cost"], "calls": summ["calls"], "elapsed_s": summ["elapsed_s"]}
    row.update(auto_eval(f"{slug(model)}__{method}", texts))
    ref = length_matched_sample(ref_all, texts, seed=1)
    jn = judge_natural(judge, texts, ref)
    row.update(natural_summary(jn, texts, ref))
    by_author = {}
    for p in P:
        by_author.setdefault(p["author_id"], []).append(p["text"])
    row.update(persona_summary(judge_persona(judge, personas, by_author)))
    rows.append(row)
    print(json.dumps({k: (round(v, 3) if isinstance(v, float) else v) for k, v in row.items() if not k.startswith("det_tells") and k not in ("ai_ism_top", "judge_tells_top")}, ensure_ascii=False), flush=True)
json.dump(rows, open(f"bench/stageB_results__{slug(JUDGE)}.json", "w"), ensure_ascii=False, indent=1)
print("judge cost", judge.summary())
