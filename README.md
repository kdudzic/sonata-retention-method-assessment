# EP-SKEL skeleton corpus generation

Synthetic Polish social-media corpus for the skeleton stage of the NCN SONATA "incremental effect" study
(plan: `Plan_badan_efektu_przyrostowego_EP-SKEL_v2_20260827c.docx`; arcs: `EP-SKEL_luki_szkieletowe_20260827c.docx`).
This repository covers corpus generation only (plan stages 2-6); selectors and scoring runs are out of scope here.

Benchmark results and the model/method decision: `notes/benchmark_report_20261008.md` (tables in `notes/benchmark_tables_20261008.md`, literature in `notes/literature_survey_20261008.md`).

## Layout

| Path | What |
|---|---|
| `epskel/llm.py` | OpenRouter chat client: retries, reasoning-effort fallback, per-call raw logging (`raw/<run>/<call_id>.json`), cost ledger (`raw/ledger.jsonl`) |
| `epskel/personas.py` | Annex J persona cards: batch generation, protected-characteristic screen, embedding dispersion check |
| `epskel/gen.py` | generators: background (methods `single`, `batch`, `vs`, `spec_first`, `spec_vs`, `rewrite`), hard negatives (Annex B hidden-variable sampler), arcs (Annex C, sequential with running situation summary) |
| `epskel/metrics.py` | diversity / duplication / surface metrics, detector AUC, reference-corpus loader; embeddings via OpenRouter `baai/bge-m3` |
| `epskel/evaluate.py` | LLM judges (naturalness, brief compliance, persona consistency) with a per-post cache |
| `epskel/bench.py`, `bench/*.py` | benchmark runners and evaluators (stage A models, A2 refusal test, B methods) |
| `epskel/timeline.py` | 12-week window, per-author posting rhythm, arc day offsets |
| `epskel/build_corpus.py`, `build.py` | resumable full build -> `corpus/<name>/posts_v1.csv`, `authors_v1.csv`, `arc_key_v1.csv`, `manifest_v1.json` |
| `qc.py` | stage-5 quality control: duplicates, flags, per-layer metrics, review samples, signal-post list |
| `prompts/` | versioned prompt files (`*_v1.md`, `*_v2.md`); filenames are recorded on every corpus row |
| `data/arcs.yaml` | the PI's 16 arc skeletons, machine-readable; `data/arc_personas.json` expanded persona cards per arc |
| `data/topics.yaml` | background topic sampler (Annex A weights) |
| `data/ref/twitteremo_final.csv` | real Polish tweets (TwitterEmo-PL, GPL-3.0) used only as a metrics reference |

## Commands

```bash
uv sync
# key: ~/sync/tokens/sonata_openrouter.txt (or ./sonata_openrouter.txt, gitignored) or export OPENROUTER_API_KEY

# full evaluation corpus (resumable; re-run the same --name to continue)
uv run python build.py --name epskel_v1 --model openai/gpt-6-sol --method spec_first \
  --authors 184 --background 3340 --hardneg 560 --arcs all --seed 2026 --start 2026-03-02

# dev corpus (no arcs; PI assigns 2 arcs later)
uv run python build.py --name epskel_dev_v1 --model openai/gpt-6-sol --method spec_first \
  --authors 30 --background 500 --hardneg 100 --arcs none --seed 7331 --start 2025-10-06 --version dev

# quality control
uv run python qc.py corpus/epskel_v1 v1

# benchmarks
uv run python bench/run_stage_a.py <model> [...]        # models
uv run python bench/run_stage_b.py <model> single vs spec_first spec_vs   # methods
uv run python bench/eval_stage_a.py openai/gpt-6-sol     # judge + metrics
uv run python bench/summarize.py
```

## Conventions

- One generator model for all layers (plan 6.6). Changing the model means rebuilding the whole corpus.
- The generator never sees `arc_type`, signal status or the construction condition; those live only in `data/arcs.yaml` and `arc_key_v1.csv`.
- Every post row records `prompt_version`, `method`, `generation_seed` and `call_ids`; the raw call files hold the full prompt and response.
- Reasoning-capable endpoints bill thinking tokens against `max_tokens`; the client keeps a 4,000-token cap and steps the reasoning effort down where the endpoint refuses to disable it.
- Local compute is avoided: embeddings go through OpenRouter (`EPSKEL_EMBED=local` forces the local model, capped at 4 threads).

Pilot results report: `notes/results_report_20261027.md`; one-pager: `notes/results_onepager_20261028.md`.
