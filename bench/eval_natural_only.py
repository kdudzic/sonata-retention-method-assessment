"""Second-opinion naturalness judge on stage A background posts. Usage: uv run python bench/eval_natural_only.py JUDGE_MODEL"""
import json, sys, glob
from pathlib import Path
from epskel.bench import read_posts, slug
from epskel.evaluate import judge_natural, natural_summary, reference
from epskel.llm import LLM, looks_like_refusal
from epskel.metrics import length_matched_sample
JUDGE = sys.argv[1]
judge = LLM(JUDGE, run_name=f"judge_{slug(JUDGE)}", temperature=0.0, max_tokens=6000)
ref_all = reference(); rows = []
for f in sorted(glob.glob("bench/stageA/*.jsonl")):
    P = read_posts(Path(f)); model = P[0]["model"]
    texts = [p["text"] for p in P if p["layer"] == "background" and p["text"].strip() and not looks_like_refusal(p["text"])]
    ref = length_matched_sample(ref_all, texts, seed=1)
    jn = judge_natural(judge, texts, ref)
    row = {"model": model}; row.update(natural_summary(jn, texts, ref)); rows.append(row)
    print(json.dumps({k: (round(v, 3) if isinstance(v, float) else v) for k, v in row.items() if k != "judge_tells_top"}), flush=True)
json.dump(rows, open(f"bench/stageA_natural__{slug(JUDGE)}.json", "w"), ensure_ascii=False, indent=1)
print("judge cost", judge.summary())
