import json, sys, traceback
from concurrent.futures import ThreadPoolExecutor
from epskel.bench import run_stage_a, slug
from epskel.personas import load_personas
from epskel import config
personas = load_personas("bench/personas_bench12.json")
arc_cards = json.load(open("data/arc_personas.json"))
ARCS = ["TA-04", "TB-08", "TB-01"]
MODELS = sys.argv[1:]
def one(m):
    try:
        s = run_stage_a(m, personas, arc_cards, ARCS)
        print("DONE", json.dumps({k: s[k] for k in ("model","n_posts","cost","elapsed_s","refusals","errors")}, ensure_ascii=False), flush=True)
    except Exception as e:
        print("FAIL", m, repr(e), flush=True); traceback.print_exc()
with ThreadPoolExecutor(max_workers=len(MODELS)) as ex:
    list(ex.map(one, MODELS))
