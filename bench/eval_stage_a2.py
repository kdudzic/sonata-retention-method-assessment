"""Judge brief compliance on stage A2 (v2 prompts) and compare with stage A (v1) for the same models."""
import json, sys, glob
from pathlib import Path
from epskel.bench import read_posts, slug
from epskel.evaluate import judge_brief, brief_summary
from epskel.llm import LLM, looks_like_refusal
from epskel.personas import load_personas
JUDGE = sys.argv[1] if len(sys.argv) > 1 else "openai/gpt-6-sol"
personas = load_personas("bench/personas_bench12.json"); arc_cards = json.load(open("data/arc_personas.json"))
cards = {c["author_id"]: c for c in personas}; cards.update({v["author_id"]: v for v in arc_cards.values()})
judge = LLM(JUDGE, run_name=f"judge_{slug(JUDGE)}", temperature=0.0, max_tokens=3000)
rows = []
for f in sorted(glob.glob("bench/stageA2/*.jsonl")):
    P = read_posts(Path(f)); model = P[0]["model"]
    arc = [p for p in P if p["layer"] == "arc"]; hn = [p for p in P if p["layer"] == "hardneg"]
    jb = judge_brief(judge, arc + hn, cards)
    row = {"model": model, "prompts": "v2", "refusal_arc": sum(looks_like_refusal(p["text"]) for p in arc), "refusal_hn": sum(looks_like_refusal(p["text"]) for p in hn)}
    row.update({f"arc_{k}": v for k, v in brief_summary(jb[:len(arc)], arc).items()})
    row.update({f"hn_{k}": v for k, v in brief_summary(jb[len(arc):], hn).items()})
    rows.append(row); print(json.dumps(row, ensure_ascii=False), flush=True)
    Path("bench/stageA2_judged").mkdir(exist_ok=True)
    with open(f"bench/stageA2_judged/{slug(model)}__{slug(JUDGE)}.jsonl", "w", encoding="utf-8") as fo:
        for p, j in zip(arc + hn, jb):
            fo.write(json.dumps({"layer": p["layer"], "attrs": p["attrs"], "text": p["text"], "judge": j}, ensure_ascii=False) + "\n")
json.dump(rows, open(f"bench/stageA2_results__{slug(JUDGE)}.json", "w"), ensure_ascii=False, indent=1)
print("judge cost", judge.summary())
