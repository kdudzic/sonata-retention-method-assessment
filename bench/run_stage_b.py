"""Stage B: method variants on the background layer. Usage: uv run python bench/run_stage_b.py MODEL METHOD [METHOD...]"""
import json, sys, traceback
from concurrent.futures import ThreadPoolExecutor
from epskel.bench import run_stage_b
from epskel.personas import load_personas
personas = load_personas("bench/personas_bench12.json")
model, methods = sys.argv[1], sys.argv[2:]
def one(method):
    try:
        s = run_stage_b(model, method, personas, n_per_persona=5, k=5)
        print("DONE", json.dumps(s, ensure_ascii=False), flush=True)
    except Exception as e:
        print("FAIL", method, repr(e), flush=True); traceback.print_exc()
with ThreadPoolExecutor(max_workers=len(methods)) as ex:
    list(ex.map(one, methods))
