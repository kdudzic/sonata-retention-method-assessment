"""CLI: build a corpus. Example:
  uv run python build.py --name epskel_v1 --model openai/gpt-6-sol --method spec_vs --authors 184 --background 3340 --hardneg 560 --seed 2026 --start 2026-03-02
Resumable: re-running with the same --name continues from cached stages under corpus/<name>/.
"""
import argparse, json
from datetime import datetime
from epskel.build_corpus import CorpusBuilder

ap = argparse.ArgumentParser()
ap.add_argument("--name", required=True)
ap.add_argument("--model", required=True)
ap.add_argument("--method", default="single")
ap.add_argument("--authors", type=int, default=184)
ap.add_argument("--background", type=int, default=3340)
ap.add_argument("--hardneg", type=int, default=560)
ap.add_argument("--arcs", default="all", help="comma-separated arc ids, 'all' or 'none'")
ap.add_argument("--seed", type=int, default=2026)
ap.add_argument("--start", default="2026-03-02")
ap.add_argument("--workers", type=int, default=8)
ap.add_argument("--persona-model", default=None)
ap.add_argument("--version", default="v1")
a = ap.parse_args()
arc_ids = None if a.arcs == "all" else ([] if a.arcs == "none" else a.arcs.split(","))
b = CorpusBuilder(a.name, a.model, a.method, a.authors, a.background, a.hardneg, arc_ids, a.seed,
                  datetime.strptime(a.start, "%Y-%m-%d"), workers=a.workers, persona_model=a.persona_model)
if arc_ids == []:
    cards, arc_cards = b.personas(); bg = b.background(cards); hn = b.hardneg(cards)
    posts, authors = b.assemble(cards, arc_cards, bg, hn, [], version=a.version)
else:
    posts, authors = b.run()
print(json.dumps(json.load(open(b.dir / f"manifest_{a.version}.json")), indent=1, ensure_ascii=False))
print(b.llm.summary())
