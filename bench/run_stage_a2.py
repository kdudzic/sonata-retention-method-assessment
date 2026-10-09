"""Stage A2: refusal mitigation test - v2 prompts (research framing) on arcs + hard negatives only."""
import json, sys, traceback
from concurrent.futures import ThreadPoolExecutor
from epskel.bench import run_stage_a
from epskel.personas import load_personas
personas = load_personas("bench/personas_bench12.json"); arc_cards = json.load(open("data/arc_personas.json"))
def one(m):
    try:
        s = run_stage_a(m, personas, arc_cards, ["TA-04", "TB-08", "TB-01"], n_bg_per_persona=0, hn_prompt="hardneg_v2", arc_prompt="arc_post_v2", stage_dir="stageA2")
        print("DONE", json.dumps({k: s[k] for k in ("model","n_posts","cost","elapsed_s","refusals","errors")}, ensure_ascii=False), flush=True)
    except Exception as e:
        print("FAIL", m, repr(e), flush=True); traceback.print_exc()
MODELS = sys.argv[1:]
with ThreadPoolExecutor(max_workers=len(MODELS)) as ex: list(ex.map(one, MODELS))
