# EP-SKEL pilot: results report

2026-10-27 · Kacper Dudzic

The skeleton study runs end to end and its construction works: concentrated arcs are found by every selector, the
random floor stays low, and every LLM selector is deterministic. The core hypothesis is visible only in part. With
the final models, author history increases retention of uninvolved authors for every LLM selector (H4), but it adds
distributed arcs by decision only for the blinded LLM (2 to 4 arcs) and not for the rule-following one. Three of the
plan's six go/no-go criteria fail, two of them for structural reasons that need a design change before full scale.

## Setup

| Element | Pilot value |
|---|---|
| Evaluation corpus | `corpus/epskel_v1/posts_v2.csv`: 4,032 posts after the split, 196 authors, 12-week window, Polish |
| Layers | background 3,340 · hard negatives 560 · arc posts 132 |
| Arcs | concentrated TA-01 to TA-04 · distributed TB-01, TB-02, TB-03, TB-05, TB-06, TB-08 · decoys TC-01, TC-02 · 25 signal posts · 184 bystander authors |
| Dev corpus | `corpus/epskel_dev_v1/posts_dev2.csv`: 622 posts, arcs TA-05 and TB-09 with their own personas and seed |
| Generator (all data) | `openai/gpt-6-sol` (corpus, PI corrections, S0 lexicon draft) |
| S0 lexical | frozen lexicon, Annex G weights; `sub` and `veto` variants |
| S1 semantic | `qwen/qwen3-embedding-8b`, centred differential score, query-instruction prefix |
| S3-open and S3' | Qwen3.8 27B (`qwen/qwen3.8-27b` via OpenRouter for the pilot), score = P(KEEP) from decision-token logprobs |
| S3-com control | `google/gemini-3.1-pro-preview`, 426-post subsample (10 % + all signal posts), declared score |
| Access variants | D0 post only · D3-agg top-3 sum over the author's posts so far · D3-nat history in the prompt · D3-txt / D3-vec for S1 |
| Budgets | 1 % (40 posts), 5 % (202), 20 % (806); 3 tie seeds; S-rand on 5 seeds |

Selector artifacts were frozen before scoring (`experiment/artifacts/frozen/manifest.json`, last freeze 2026-10-27).

## Detection by budget

Strict detection = at least one signal post of the arc in the retained set. Numbers are means over tie seeds; "dist"
is the distributed subset (6 arcs). Bystanders = authors without an arc who have at least one retained post.

| Selector | Access | Arcs 1 % | Arcs 5 % | Arcs 20 % | Dist. 5 % | Dist. 20 % | Bystanders 5 % | Bystanders 20 % |
|---|---|---|---|---|---|---|---|---|
| S-rand | D0 | 0.4 | 1.6 | 4.6 | 1.6 | 3.6 | 115 | 178 |
| S0-sub | D0 | 2.0 | 3.7 | 9.0 | 1.7 | 6.0 | 106 | 177 |
| S0-sub | D3-agg | 0.0 | 0.0 | 3.7 | 0.0 | 2.7 | 15 | 88 |
| S0-veto | D0 | 1.0 | 2.7 | 8.0 | 1.7 | 6.0 | 106 | 177 |
| S1 | D0 | 4.0 | 8.0 | 9.0 | 4.0 | 5.0 | 114 | 179 |
| S1 | D3-agg | 1.0 | 2.0 | 2.0 | 2.0 | 2.0 | 20 | 73 |
| S1 | D3-txt | 0.0 | 2.0 | 5.0 | 1.0 | 3.0 | 51 | 126 |
| S1 | D3-vec | 3.0 | 5.0 | 6.0 | 3.0 | 4.0 | 101 | 166 |
| S3-open | D0 | 7.0 | 8.0 | 10.0 | 4.0 | 6.0 | 89 | 160 |
| S3-open | D3-agg | 1.0 | 4.0 | 7.0 | 2.0 | 3.0 | 15 | 47 |
| S3-open | D3-nat | 7.0 | 9.0 | 10.0 | 5.0 | 6.0 | 74 | 109 |
| S3' blind | D0 | 6.0 | 8.0 | 10.0 | 4.0 | 6.0 | 82 | 154 |
| S3' blind | D3-nat | 6.0 | 8.0 | 10.0 | 4.0 | 6.0 | 68 | 104 |

What the table shows:
- The LLM selectors saturate early: 8 to 9 of 10 arcs at 5 %, all 10 at 20 %, with or without history. The
  continuous P(KEEP) score sorts the corpus into a mundane band and a non-mundane band, and with 14 % hard negatives
  any budget of 5 % or less is cut inside the non-mundane band. In the budget view, history therefore cannot add arcs.
- At a fixed budget, history concentrates retention on fewer people: S3-open at 20 % retains 109 bystander authors
  with history against 160 without. The same retained volume falls on fewer, deeper profiles.
- D3-agg underperforms everywhere because the top-3 sum rewards authors who post a lot (arc authors have 9 to 13
  posts, most bystanders more; see section 3 of the calibration note).
- S1 in D0 finds distributed arcs because the frozen seed list paraphrases arc patterns; with shuffled seeds S1
  finds 0.0 / 0.3 / 2.3 arcs, so the seeds carry the signal. A post-hoc rulebook-only seed set is reported in the
  calibration note.
- The S3-com rows are on the 426-post subsample and are not comparable to the full-corpus rows; they are left out.

## Decisions with and without history

Arcs counted only when a signal post receives KEEP_FOR_REVIEW, independent of any budget. This is the plan's
auxiliary class view, and at this scale it is where the history effect shows.

| Selector | Access | KEEP posts | Arcs kept | of which distributed | Bystander authors kept | Hard negatives kept |
|---|---|---|---|---|---|---|
| S3-open (Qwen3.8 27B) | D0 | 33 | 7 | 3 | 19 | 25 |
| S3-open (Qwen3.8 27B) | D3-nat | 48 | 7 | 3 | 31 | 32 |
| S3' blind (Qwen3.8 27B) | D0 | 46 | 6 | 2 | 30 | 38 |
| S3' blind (Qwen3.8 27B) | D3-nat | 84 | 8 | 4 | 42 | 56 |
| S3-com (Gemini, subsample) | D0 | 9 | 7 | 3 | 1 | 1 |
| S3-com (Gemini, subsample) | D3-nat | 13 | 8 | 4 | 1 | 1 |

- H4 holds for every LLM selector: with history, more uninvolved authors are retained (19 to 31, 30 to 42).
- H3 holds for the blinded selector (2 to 4 distributed arcs) and the control model (3 to 4), not for S3-open,
  which keeps the same 3 distributed arcs either way. With the earlier provisional model, DeepSeek V4.1 Flash, S3-open
  did show it (2 to 4); the effect is model-dependent at this scale.
- No decoy author was retained by decision in any variant.
- The explicit signal list restrains retention: S3' keeps 84 posts with history against 48 for S3-open.

## Go/no-go criteria (plan section 19)

| # | Criterion | Value | Result |
|---|---|---|---|
| 1 | at least one selector detects 6 or more of 10 arcs in D3 at 20 % | 10 | pass |
| 2 | at most 1 of 6 distributed arcs detected in D0 at 5 % | 4 | fail |
| 3 | at least 3 of 4 concentrated arcs detected by S0 in D0 at 20 % | 3 | pass |
| 4 | S-rand detects at most 1 arc at 20 % | 4.6 | fail |
| 5 | for at least one selector, D3 minus D0 for distributed arcs is 3 or more at 20 % | 0 | fail |
| 6 | duplicate rate below the dev-corpus threshold | 0 exact, 8 near-duplicate pairs of 4,078 posts | not formally set |

- Criterion 2 fails because some distributed signal posts are overt on their own (TB-03 #8, TB-01 #10) and because
  any non-mundane post clears a 5 % budget. Fix both: soften those briefs, and size the hard-negative layer below the
  smallest budget or report ranks within the non-mundane band.
- Criterion 4 is unattainable as written. With 1 to 5 signal posts per arc, a random 20 % sample is expected to hit
  about 4 arcs. Replace it with a comparison against the analytical random expectation.
- Criterion 5 fails in the budget view for the saturation reason above, while the decision view shows the effect for
  two of three LLM selectors. Proposal: make the decision view co-primary for H3/H4.

## What to change before full scale

1. Give arc authors the same posting volume as ordinary authors, or normalise the aggregation for volume.
2. Rewrite the S1 seeds from the rulebook only, by someone who has not read the arc cards, and re-freeze.
3. Set budgets relative to the hard-negative share, or report detection within the non-mundane band.
4. Replace criterion 4 with the random expectation; add the decision view as a co-primary measure.
5. Soften the single-post wording of TB-03 #8 and TB-01 #10. TA-03 #5 sits on the decision boundary
   (P(KEEP) 0.44 with DeepSeek) and may need a clearer intent if it must stay a positive control.
6. Run S3-open on the local server for the next stages; the code needs only a base URL change.

## Reproducibility and cost

- Determinism, S3-open twice at temperature 0: decision agreement 100 % in D0 and D3-nat; score rank correlation
  0.98 and 0.97.
- Control agreement with S3-open: 99.5 % (D0) and 98.4 % (D3-nat) of decisions on the subsample.
- Declared `retention_score` against the logprob score: rank correlation 0.69 (D0) and 0.67 (D3-nat). The two agree
  on the extremes and diverge inside the borderline band, where budget cuts fall.
- Logprobs were returned on all 24,192 Qwen evaluation calls; no call hit a length limit or used reasoning tokens.
- Spend through OpenRouter for the whole pilot: $88.90 of $100, including the generator benchmark and both corpora.
  Final model runs: Qwen $4.77, Gemini $3.60, embeddings $0.12.
- Deviation from the plan: S3-open ran through OpenRouter, not on CSI hardware. Weights are open, so the next
  stages can rerun it locally.

## Files

- Results card: `experiment/results/eval/results_card.md`; per-post scores: `experiment/results/eval/scores_*.csv`
- Calibration note with the full reasoning: `experiment/results/eval/calibration_note.md`
- Model choices: `notes/model_selection.md`; arc split and PI corrections: `notes/decisions_20261023.md`
- Generator benchmark: `notes/benchmark_report_20261008.md`
