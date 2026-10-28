# EP-SKEL pilot: one-pager

2026-10-28 · Kacper Dudzic · full report in `notes/results_report_20261027.md` · Polish version in `notes/results_onepager_20261028_pl.md`

The corpus has 4,032 Polish posts by 196 authors. It holds 10 target arcs, of which 4 are concentrated and 6
distributed, plus 2 decoy profiles and 184 bystander authors. Each budget keeps the top 1 %, 5 % or 20 % of posts,
which is 40, 202 or 806 posts.

## Results by selector

| Selector | Model | Access | Arcs found at 1 % / 5 % / 20 % | Distributed arcs found at 20 %, of 6 | Bystander authors at 20 % | Arcs kept by KEEP decision, distributed in brackets | Bystander authors kept by decision |
|---|---|---|---|---|---|---|---|
| S-rand | random, 5 seeds | D0 | 0.4 / 1.6 / 4.6 | 3.6 | 178 | none | none |
| S0 lexical, sub | frozen word list | D0 | 2.0 / 3.7 / 9.0 | 6.0 | 177 | none | none |
| S0 lexical, sub | frozen word list | D3-agg | 0.0 / 0.0 / 3.7 | 2.7 | 88 | none | none |
| S1 semantic | Qwen3-Embedding-8B | D0 | 4 / 8 / 9 | 5 | 179 | none | none |
| S1 semantic | Qwen3-Embedding-8B | D3-txt | 0 / 2 / 5 | 3 | 126 | none | none |
| S3-open | Qwen3.8 27B | D0 | 7 / 8 / 10 | 6 | 160 | 7 [3] | 19 |
| S3-open | Qwen3.8 27B | D3-nat | 7 / 9 / 10 | 6 | 109 | 7 [3] | 31 |
| S3' blind | Qwen3.8 27B | D0 | 6 / 8 / 10 | 6 | 154 | 6 [2] | 30 |
| S3' blind | Qwen3.8 27B | D3-nat | 6 / 8 / 10 | 6 | 104 | 8 [4] | 42 |
| S3-com control | Gemini 3.1 Pro | D0, 10 % sample | not comparable | not comparable | not comparable | 7 [3] | 1 |
| S3-com control | Gemini 3.1 Pro | D3-nat, 10 % sample | not comparable | not comparable | not comparable | 8 [4] | 1 |

D0 means the selector sees the post alone. The D3 variants also give it the author's earlier posts. D3-nat puts
that history in the LLM prompt, D3-txt puts it in the embedding window, and D3-agg sums the author's three highest
post scores. An arc counts as found when at least one of its signal posts is retained. Values are means over tie
seeds. S0 and S1 produce no KEEP decisions, so their last two columns are empty. The control model scored a
426-post sample, so its budget results do not compare with the other rows.

## Key points

- **Positive controls pass.** S0 finds 3 of 4 concentrated arcs from the post alone, and every LLM selector finds
  all 4. No decoy author is kept by decision. Random selection finds 0.4 arcs at the 1 % budget.
- **LLM selectors saturate the budget view.** They find 8 or 9 arcs at 5 % with or without history. Any non-mundane
  post clears a budget that small, because hard negatives make up 14 % of the corpus.
- **History raises the number of uninvolved people retained, which is H4.** By decision, kept bystander authors go
  from 19 to 31 for S3-open and from 30 to 42 for S3'. At a fixed 20 % budget, S3-open spreads the same volume over
  109 authors with history instead of 160, so each retained profile is deeper.
- **History adds distributed arcs, which is H3, for two of the three LLM selectors.** By decision, S3' goes from 2
  to 4 distributed arcs and Gemini from 3 to 4. S3-open keeps 3 with or without history.
- **The explicit signal list restrains the LLM.** With history, S3' keeps 84 posts and S3-open keeps 48.
- **S1 and D3-agg results are not clean.** The frozen S1 seed descriptions paraphrase arc patterns, and with shuffled
  seeds S1 finds 0 to 2 arcs. The top-3 aggregation favours authors who post a lot.
- **Two of six go/no-go criteria pass, three fail, and one has no threshold yet.** Criterion 4 asks random selection
  to find at most 1 arc at 20 %, which cannot happen with 1 to 5 signal posts per arc. Criteria 2 and 5 fail because
  of the saturation described above.
- **Runs are reproducible and cheap.** Two S3-open runs agree on 100 % of decisions. The control model agrees with
  S3-open on 98 to 99.5 % of decisions. The whole pilot cost $88.90 through OpenRouter.
- **Four changes are needed before full scale.** Give arc authors the same number of posts as other authors. Write
  the S1 seeds from the rulebook only. Set budgets against the hard-negative share. Report the decision view
  alongside the budget view as a primary measure.
