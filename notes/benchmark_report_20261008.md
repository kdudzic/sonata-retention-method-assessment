# EP-SKEL skeleton corpus: generation methods, model choice, build

Date: 2026-10-08. Author: Kacper (with Claude Code). Companion files: `benchmark_tables_20261008.md` (all numbers), `literature_survey_20261008.md` (sources), `bench/` (raw outputs, per-post judgements), `corpus/epskel_v1/` and `corpus/epskel_dev_v1/` (built corpora).

## 1. What was decided

| Item | Decision | Why (short) |
|---|---|---|
| Generator model (all layers) | `openai/gpt-6-sol` (mid tier, $2/$10 per Mtok) | zero refusals on the slur/familicide arcs, best Polish (4.75/5), AI-ism rate at real-tweet level, hard negatives read as their intended profile, top-3 naturalness by both judges |
| Background method | `spec_first` (one planning call per author producing concrete "post seeds", then one call per seed) | removes repeated post skeletons (judge flag 42 % of authors -> 0 %), raises persona naturalness 3.4 -> 3.9, costs 1.8x single calls |
| Verbalized sampling | not used in v1; implemented as `vs` / `spec_vs` flags | no measurable gain over spec_first on gpt-6-sol at n = 60; 1.8-2.3x cost; strong gain only on Gemini Flash |
| Flagship needed? | No | gpt-6-astra is marginally better on hard-negative brief fulfilment (0.92 vs 0.58-0.67) and persona naturalness but ~5x the cost and not more natural by the judges; Claude Opus refuses one arc post and costs 4x |
| Cheap tier enough? | No | luna/haiku/deepseek/glm are the easiest to tell from human text (judge AUC 0.98-0.99 vs 0.91-0.95), and either refuse (haiku) or fail hard-negative briefs (deepseek 0.17, haiku 0.17) |
| Prompts | `background_v2`, `hardneg_v2`, `arc_post_v2`, `spec_plan_v2`, `persona_v1`, `persona_from_sketch_v1` | v2 adds per-post control of verbal tic / local reference / life situation (every model overused all three under v1) and a research-context preamble |
| Arcs | all 16 from the PI's document generated; PI picks 10 + 2 for evaluation | cheap (177 posts); the key file `arc_key_v1.csv` keeps signal status out of the posts table |
| Reference corpus | TwitterEmo-PL (36k real Polish tweets, GPL-3.0) for metrics only | the plan allows real data as reference for distributions; nothing from it enters the corpus |

## 2. Literature-derived method set (what was implemented)

From the survey (`literature_survey_20261008.md`): structural prompt-level interventions beat sampling knobs; set-level persona dispersion matters more than per-card detail; one-call-many-outputs is more diverse than repeated single calls; a hard word-length target is the single best-supported lever; rewriting/"humanizing" passes mostly fool detectors, not readers. Implemented in `epskel/gen.py`:

- `single`: Annex A prompt, attribute sampler (13 weighted topics x sub-angles, 5 registers, triangular 8-50 word length, time of day, weekday), 3 recent same-topic posts as anti-repetition examples.
- `batch`: k = 5 posts per call, one brief each (ablation).
- `vs`: verbalized sampling (k = 5 candidates with verbalized probabilities, tail threshold 0.10, pick from the tail).
- `spec_first`: planning call -> k concrete occasions (occasion, mood, opener type, length, whether the tic fires), then one post per seed.
- `spec_vs`: spec_first with VS at the post step.
- `rewrite`: single + "retype as this person on a phone" second pass.
- Persona set dispersion: cards generated in batches with the already-used occupations/interests/places/tics shown as exclusions, screened by a forbidden-term list (protected characteristics) and by embedding similarity (BGE-M3, reject > 0.90).

## 3. Metrics (what was measured)

Automatic (`epskel/metrics.py`), each against a word-length-matched sample of real tweets: distinct-n, MATTR, gzip compression ratio, 4-gram self-repetition, self-BLEU-4; BGE-M3 mean pairwise cosine, share of pairs > 0.8, Vendi score, near-duplicate rate (> 0.90); surface panel (length, lowercase starts, terminal punctuation, emoji/hashtag/mention, em-dash, ellipsis, all-caps, expletives, missing diacritics, a 60-phrase Polish AI-ism list); char- and word-n-gram logistic-regression detector AUC (synthetic vs reference).

LLM judges (`prompts/judge_*.md`): blind human-vs-synthetic probability on mixed batches (synthetic + real), Polish fluency, free-text "tells"; brief compliance + sanitisation + single-post retention profile under the rulebook (arcs, hard negatives); persona consistency, tic overuse, repetitive structure. Primary judge gpt-6-sol, second naturalness judge claude-sonnet-5.5.

Caveat on the naturalness numbers: the reference tweets are mostly political replies, the synthetic posts are mundane by design, so both the detector AUC (0.99 everywhere) and the judge AUC partly measure topic, not style. They are usable for ranking models under identical conditions, not as absolute human-likeness. The judge "tells" and the AI-ism panel are the interpretable part.

## 4. Stage A: 11 models, same personas, same briefs

Per model: 60 background posts (12 personas x 5), 12 hard negatives, three arcs chosen as the hardest for safety filters (TA-04 slur + venue + date; TB-08 coordinated slur; TB-01 familicide hints). Full table in `benchmark_tables_20261008.md`.

Refusals and compliance on the sensitive arcs (32 arc posts, 12 hard negatives):

| Model | Arc refusals | Sanitised | Brief fully met (arc) | Hard-neg brief met | Hard-neg profile as intended | Cost / 104 posts |
|---|---|---|---|---|---|---|
| claude-haiku-5.5 | 7 | 19 % | 69 % | 17 % | 42 % | $0.03 |
| claude-sonnet-5.5 | 1 | 3 % | 94 % | 58 % | 50 % | $0.49 |
| claude-opus-5.5 | 1 | 9 % | 84 % | 67 % | 58 % | $1.27 |
| mistral-large-4-0 | 1 | 9 % | 84 % | 25 % | 67 % | $0.10 |
| gpt-6-astra | 1 | 6 % | 94 % | 92 % | 83 % | $1.57 |
| glm-5.3-flash | 1 | 3 % | 94 % | 42 % | 75 % | $0.02 |
| gpt-6-sol | 0 | 3 % | 94 % | 58 % | 100 % | $0.33 |
| gpt-6-luna | 0 | 6 % | 94 % | 75 % | 92 % | $0.02 |
| gemini-3.8-flash | 0 | 0 % | 94 % | 67 % | 17 % | $0.14 |
| deepseek-v4.1-flash | 0 | 6 % | 78 % | 17 % | 50 % | $0.03 |
| kimi-k3 | 0 | 6 % | 84 % | 42 % | 58 % | $0.27 |

The refused post is almost always TA-04 #4 (group slur + named venue + "jutro wieczorem" + "we" + historical euphemism). The research-context preamble (stage A2, v2 prompts) did not change refusal counts for Haiku/Sonnet/Mistral; Opus went 1 -> 0, GLM's arc brief fulfilment dropped to 53 %.

Naturalness and diversity of background posts (lower judge AUC = harder to tell from real):

| Model | Judge AUC (sol) | Judge AUC (sonnet) | Polish (sol) | AI-isms / post | Mean cosine | Compression ratio | Persona natural |
|---|---|---|---|---|---|---|---|
| gemini-3.8-flash | 0.906 | 0.889 | 4.43 | 0.23 | 0.476 | 2.01 | 3.33 |
| gpt-6-astra | 0.920 | 0.937 | 4.62 | 0.10 | 0.515 | 2.10 | 3.92 |
| gpt-6-sol | 0.947 | 0.904 | 4.75 | 0.05 | 0.504 | 2.11 | 3.67 |
| claude-sonnet-5.5 | 0.960 | 0.941 | 4.30 | 0.23 | 0.478 | 2.08 | 3.08 |
| mistral-large-4-0 | 0.963 | 0.950 | 4.05 | 0.32 | 0.489 | 2.16 | 2.58 |
| claude-opus-5.5 | 0.969 | 0.942 | 4.63 | 0.28 | 0.478 | 2.08 | 3.17 |
| kimi-k3 | 0.975 | 0.943 | 3.88 | 0.33 | 0.483 | 2.07 | 2.83 |
| glm-5.3-flash | 0.976 | 0.911 | 3.40 | 0.27 | 0.486 | 2.06 | 2.25 |
| claude-haiku-5.5 | 0.976 | 0.986 | 3.78 | 0.25 | 0.503 | 2.21 | 2.67 |
| deepseek-v4.1-flash | 0.982 | 0.919 | 4.42 | 0.30 | 0.478 | 2.15 | 2.75 |
| gpt-6-luna | 0.991 | 0.982 | 4.45 | 0.15 | 0.511 | 2.16 | 3.00 |
| real tweets (length-matched) | - | - | - | 0.05 | 0.408 | 1.93 | - |

Why not Gemini Flash despite the best naturalness: 5 of 12 hard negatives intended as `clear_discard`/`borderline` read as `clear_keep` to the judge (it adds first-person intent and timing on its own). That mislabels the hard-negative layer, which is the layer that makes the lexical baseline meaningful. gpt-6-sol errs the other way (some hard negatives come out softer than briefed: fulfilment 58 %, but every one keeps its intended profile), which the anti-softening rules of the plan are designed to catch; this is the main thing to watch in QC.

Judge "tells" for gpt-6-sol: repeated ellipses (persona-driven), unmotivated location detail, over-explained context, tidy narrative arc. Under v1 prompts every model used the verbal tic and the local reference in 60-100 % of an author's posts; v2 prompts fix this per post (tic in ~30 %, local place ~25 %, life situation ~30 %).

Reasoning tokens: claude-sonnet/opus-5.5, gemini-3.8-flash, glm-5.3-flash and gpt-6-astra do not allow reasoning to be disabled; thinking tokens are billed and count against `max_tokens`, so short-output caps return empty or truncated posts. The client steps down an effort ladder and the pipeline sets a 4,000-token cap for every call.

## 5. Stage B: methods on gpt-6-sol (v2 prompts, 60 posts each)

| Method | Judge AUC | AI-isms / post | Compression ratio | Self-BLEU-4 | Repetitive-structure flag | Persona natural | Cost / 60 |
|---|---|---|---|---|---|---|---|
| single | 0.950 | 0.02 | 2.06 | 0.126 | 42 % | 3.42 | $0.12 |
| vs | 0.973 | 0.15 | 2.06 | 0.137 | 8 % | 3.75 | $0.27 |
| spec_first | 0.968 | 0.17 | 2.01 | 0.118 | 0 % | 3.92 | $0.21 |
| spec_vs | 0.948 | 0.03 | 1.97 | 0.115 | 8 % | 3.83 | $0.37 |

Differences between judge AUCs at n = 60 are within noise. spec_first was chosen for its structural effect (no repeated skeletons, concrete occasions) at 1.8x the single-call cost; spec_vs adds a small further gain in lexical diversity and AI-isms at 3.2x. The planner's v1 wording put a clock time in almost every seed; `spec_plan_v2` asks for at most one small detail and often none.

On gemini-3.8-flash, spec_vs was clearly the best configuration of the whole benchmark (judge AUC 0.883, mean cosine 0.446), so if the hard-negative layer were generated separately, Gemini + spec_vs would be the background choice. The plan's single-generator requirement (6.6: stylistic separability) rules that out for now.

## 6. Build configuration

- `corpus/epskel_v1/`: 184 ordinary authors + 16 arc authors; 3,340 background (spec_first) + 560 hard negatives (Annex B sampler: 60 % clear_discard / 40 % borderline, exculpatory signal spread, press-report perspectives) + 177 arc posts; window 2026-03-02 to 2026-05-25; seed 2026.
- `corpus/epskel_dev_v1/`: 30 authors; 500 background + 100 hard negatives; no arcs; seed 7331; window 2025-10-06 onwards. The PI assigns 2 of the 16 arcs to the dev corpus (`authors_v1.csv` has `arc_id`; move those rows).
- Hard negatives are spread over ordinary authors with a skewed allocation (40 % of authors none, Pareto tail), so author-level invasiveness is not trivially uniform.
- Timestamps: per-author rhythm class from the card (day worker, early shift, night shift, student, home, retired, gig) x weekday pattern; arc day offsets from the PI's tables are kept exactly, with a random start inside the window.
- Every row carries `prompt_version`, `method`, `generation_seed` and the raw-call ids (`raw/corpus_epskel_v1/<id>.json` holds the full prompt and response). `manifest_v1.json` records model, versions, window, layer counts and SHA-256 of the tables.

## 7. Open points for the PI / next steps

1. Pick the 10 arcs + 2 decoys for evaluation and 2 arcs for the dev corpus; approve the ~30 signal posts (`arc_key_v1.csv` x `posts_v1.csv`).
2. Protected characteristics: persona cards carry only a grammatical gender (needed for Polish verb agreement, balanced 50/50) and no other protected trait; a regex screen rejected cards mentioning any. The PI's own arc sketches (TA-04, TB-08) require group slurs by design.
3. The hard-negative softening tendency of gpt-6-sol should be checked in QC (stage 5): a sample of 30 hard negatives rated blind for whether they are "hard" enough.
4. Selector-model overlap: the generator is an OpenAI model; the commercial control selector (S3-com) was planned as the XAI-study model set, which includes OpenAI. Either pick a non-OpenAI control model or document the overlap.
5. Generation cost at full scale (15k posts) with this configuration: roughly $65-80.

## 8. Dev corpus QC (corpus/epskel_dev_v1, 600 posts, 30 authors)

| Check | Value |
|---|---|
| exact duplicates | 0 |
| near-duplicate pairs (cosine > 0.90) | 0 |
| flagged posts (refusal-like, empty, placeholders, forbidden topics in background) | 0 |
| posts per author | mean 20, min 6, max 54 |
| length (words) | mean 23.1, p10 14, p90 35 |
| background: compression ratio / self-BLEU-4 / mean cosine | 2.52 / 0.203 / 0.511 |
| hard negatives: compression ratio / self-BLEU-4 / mean cosine | 2.36 / 0.152 / 0.528 |
| background AI-isms per post | 0.054 |
| background posts with emoji | 0.42 |
| within-author mean cosine | 0.518 |

The dev corpus cost $2.12 (personas $0.09, background $1.44, hard negatives $0.60). Note the emoji rate: 42 % of background posts carry an emoji, driven by persona cards marked "emoji: frequent"; the real reference has almost none, so the persona prompt's emoji mix is a candidate for tuning in v2 of the corpus.

## 9. Evaluation corpus QC (corpus/epskel_v1, built 2026-10-08)

Manifest: 4077 posts, 200 authors, layers {'background': 3340, 'hardneg': 560, 'arc': 177}, window 2026-03-02 to 2026-05-25, generation cost $14.52 (+ $0.53 personas), SHA-256 of posts table `f33d5b67b25ca7cc...`.

| Check | Value |
|---|---|
| refusals in arc / hard-negative layers | 0 / 0 |
| exact duplicates | 0 |
| near-duplicate pairs (cosine > 0.90), all cross-author, same sub-angle | 8 (0.4 % of posts) |
| flagged background posts | 9, all false positives of the word screen (knife while cooking, "sądziłam", "rząd" = row, "partia" = board-game round) |
| posts per author | mean 20.4, min 5, max 63 |
| length (words) | mean 22.8, p10 14, p90 35 |
| background: compression ratio / self-rep-4 / mean cosine / AI-isms | 2.67 / 0.43 / 0.506 / 0.057 |
| hard negatives: compression ratio / self-BLEU-4 / mean cosine | 2.65 / 0.223 / 0.521 |
| arcs: compression ratio / self-BLEU-4 / mean cosine | 2.31 / 0.158 / 0.485 |
| background posts with emoji | 0.37 |

Compression ratio and 4-gram self-repetition rise with set size (3,340 posts vs 60 in the benchmark), so compare them with the 500-post dev layer (2.52), not with stage B. The 8 near-duplicate pairs are listed in `qc_neardups_v1.csv` for the PI's decision before freezing v1.0; nothing was removed automatically. Review samples: `sample_pi_200_v1.csv` (PI uniformity review), `sample_blind_30_v1.csv` (external blind check), `signal_posts_v1.csv` (all arc posts with signal status, for approval of the signal posts).

## 10. Spend

Total API spend on 2026-10-08: $43.88 (benchmarks and judges ~$21, dev corpus $2.12, evaluation corpus $15.05, a leaked retry loop $5.85 - see notes in memory). Key balance after today: about $38.
