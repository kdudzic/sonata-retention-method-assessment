# EP-SKEL pilot: one-pager

2026-10-28 · Kacper Dudzic · full report: `notes/results_report_20261027.md`

Corpus: 4,032 Polish posts, 196 authors, 10 target arcs (4 concentrated, 6 distributed), 2 decoys, 184 bystander
authors. Budgets cut the top 1 % / 5 % / 20 % of posts (40 / 202 / 806).

## Results by selector

| Selector | Model | Access | Arcs found 1 % / 5 % / 20 % | Distributed found at 20 % (of 6) | Bystander authors at 20 % | Arcs kept by KEEP decision (distributed) | Bystander authors kept by decision |
|---|---|---|---|---|---|---|---|
| S-rand | random, 5 seeds | D0 | 0.4 / 1.6 / 4.6 | 3.6 | 178 | n/a | n/a |
| S0 lexical (sub) | frozen word list | D0 | 2.0 / 3.7 / 9.0 | 6.0 | 177 | n/a | n/a |
| S0 lexical (sub) | frozen word list | D3-agg | 0.0 / 0.0 / 3.7 | 2.7 | 88 | n/a | n/a |
| S1 semantic | Qwen3-Embedding-8B | D0 | 4 / 8 / 9 | 5 | 179 | n/a | n/a |
| S1 semantic | Qwen3-Embedding-8B | D3-txt | 0 / 2 / 5 | 3 | 126 | n/a | n/a |
| S3-open | Qwen3.8 27B | D0 | 7 / 8 / 10 | 6 | 160 | 7 (3) | 19 |
| S3-open | Qwen3.8 27B | D3-nat | 7 / 9 / 10 | 6 | 109 | 7 (3) | 31 |
| S3' blind | Qwen3.8 27B | D0 | 6 / 8 / 10 | 6 | 154 | 6 (2) | 30 |
| S3' blind | Qwen3.8 27B | D3-nat | 6 / 8 / 10 | 6 | 104 | 8 (4) | 42 |
| S3-com control | Gemini 3.1 Pro | D0, 10 % sample | n/a | n/a | n/a | 7 (3) | 1 |
| S3-com control | Gemini 3.1 Pro | D3-nat, 10 % sample | n/a | n/a | n/a | 8 (4) | 1 |

D0 = the post alone. D3 = the post plus the author's earlier posts (D3-nat: history in the LLM prompt; D3-txt: history
in the embedding window; D3-agg: sum of the author's top-3 post scores). Detection = at least one signal post of the
arc retained. Numbers are means over tie seeds.

## Key points

- **The construction works.** S0 finds 3 of 4 concentrated arcs from the post alone, every LLM selector finds all 4,
  no decoy author is ever kept by decision, and the random floor is 0.4 arcs at 1 %.
- **LLM selectors saturate the budget view.** They find 8 to 9 arcs at 5 % with or without history, because any
  non-mundane post clears a budget that small (hard negatives are 14 % of the corpus).
- **History raises invasiveness (H4) for every LLM selector.** By decision, bystander authors kept go from 19 to 31
  (S3-open) and from 30 to 42 (S3'). At a fixed budget the same volume falls on fewer, deeper profiles (160 to 109).
- **History adds distributed arcs (H3) only for some selectors.** By decision: S3' 2 to 4, Gemini 3 to 4, S3-open
  unchanged at 3.
- **The explicit signal list restrains the LLM.** With history, S3' keeps 84 posts against 48 for S3-open.
- **S1 and D3-agg results are not clean.** S1's frozen seeds paraphrase arc patterns (shuffled seeds find 0 to 2
  arcs), and the top-3 aggregation rewards authors who post a lot.
- **Go/no-go: 2 of 6 criteria pass, 3 fail, 1 has no threshold set.** Criterion 4 (random at most 1 arc at 20 %) is
  unattainable with 1 to 5 signal posts per arc; criteria 2 and 5 fail for the saturation reason above.
- **Reproducible and cheap.** Two S3-open runs agree on 100 % of decisions; the control agrees with S3-open on 98 to
  99.5 %. The whole pilot cost $88.90 through OpenRouter.
- **Before full scale:** pad arc authors to normal posting volume, rewrite S1 seeds from the rulebook only, size
  budgets against the hard-negative share, and make the decision view a co-primary measure.
