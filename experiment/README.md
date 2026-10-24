# EP-SKEL selection experiment (`selex`)

Scoring runs, retention budgets and metrics for the skeleton study (plan sections 7-10, 19; Annexes E-I).
Kept separate from corpus generation (`../epskel`): this package only reads the built corpus tables and never
imports generator code. Selectors receive `post_id, author_id, timestamp, text` (plus earlier posts of the author
in D3); arc ids, roles and signal status are used only by the metrics.

## Layout

| Path | What |
|---|---|
| `configs/experiment.yaml` | corpus paths, budgets, tie seeds, aggregation, selector models and weights |
| `configs/arc_split.yaml` | which arcs are evaluation / dev / spare (PROVISIONAL until the PI decides) |
| `selex/corpus.py` | loads `posts_v1.csv` etc., applies the split, derives gold (signal posts, targets, bystanders) |
| `selex/s0_lexical.py` | S0 categories A-E, Annex G score, `sub` / `veto` variants; lexicon = `artifacts/s0_lexicon.yaml` |
| `selex/s1_semantic.py` | S1 centred differential score on `qwen/qwen3-embedding-8b`; D3-txt / D3-vec; shuffled-seed control; seeds = `artifacts/s1_seeds.yaml` |
| `selex/s3_llm.py` | S3 prompts (Annex E/F, blinded variants), P(KEEP) from decision-token logprobs, `retention_score`, `decisive_posts` |
| `selex/access.py` | D3-agg (top-3 sum over the author's posts up to the post), random ranking |
| `selex/metrics.py` | budget cut with seeded tie-breaking; detection and invasiveness metrics (section 10) |
| `selex/report.py` | metrics tables, curves, go/no-go (section 19), S3 - S3' difference, determinism / control agreement, results card |
| `selex/freeze.py` | artifact hashes (stage 0); evaluation scoring refuses to run if artifacts changed |
| `prompts/` | `s3_d0_v1`, `s3_d3nat_v1`, `s3_blind_*`, `lexicon_expand_v1` |
| `results/<corpus>/` | `scores_*.csv` (Annex I schema), `metrics_*.csv`, `results_card.md`, `curves.png`, `agreement.json` |
| `results/raw/` | one JSON per LLM call (full prompt + response), `ledger.jsonl` with costs |

## Commands (run inside `experiment/`)

```bash
uv sync
uv run python experiment.py describe
uv run python experiment.py build-lexicon           # LLM draft from definitions -> artifacts/s0_lexicon_draft.yaml (prune by hand into s0_lexicon.yaml)
uv run python experiment.py leak-check              # plan 11.2: signal-post terms vs lexicon / seeds
uv run python experiment.py model-trial --n 200     # S3 D0 on a dev sample per open candidate
uv run python experiment.py score --corpus dev --selectors s0,s1,srand
uv run python experiment.py metrics --corpus dev
uv run python experiment.py freeze --note "stage 0"
uv run python experiment.py score --corpus eval --selectors s0,s1,srand
uv run python experiment.py score --corpus eval --selectors s3open,s3blind,s3com
uv run python experiment.py score --corpus eval --selectors s3open --repeat   # determinism check (second run)
uv run python experiment.py report --corpus eval
```

## Measurement grid

S0-sub/S0-veto x (D0, D3-agg); S1 x (D0, D3-agg, D3-txt, D3-vec) + shuffled-seed control; S3-open x (D0, D3-agg, D3-nat);
S3' (blind) x (D0, D3-nat); S3-com on a ~10 % subsample + all signal posts; S-rand x 5 seeds. Budgets 1 / 5 / 20 %,
3 tie seeds. Scores are continuous; ranks are cut per budget; metrics are absolute counts.

Notes: S3-open runs through OpenRouter (plan: local open model on CSI infrastructure); logprobs are provider-dependent
and recorded per call, with `retention_score` as the fallback. Reasoning is disabled for all S3 calls.

Model choices for the selectors and the open todos: `notes/model_selection.md`.
