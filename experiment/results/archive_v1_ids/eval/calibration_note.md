# Calibration note (plan section 15: "what came out differently than planned")

Draft, 2026-10-08. Sections on S3 are filled after the S3 runs complete (see results_card.md).

## 1. Protocol deviations to declare
- **Arc split is provisional.** `configs/arc_split.yaml` assigns TA-05 and TB-09 to the dev corpus and TB-04, TB-07 to
  spare so the pipeline could run end to end; the PI decides the final 10 + 2 + 2. Changing the split changes the
  evaluation corpus and requires re-running the frozen protocol (cheap: ~$6 of API calls, ~1.5 h).
- **S1 seeds v1 leak arc logic.** The frozen SEED+ list includes descriptions at the level of the PI's arc patterns
  ("systematic tracking of one person's daily routine, when she is alone, when there is no security";
  "takes the family along, everyone will be at peace on a given day"; "group hostility + a named shop + a date").
  These are not the rulebook's generic signal families; they paraphrase the arcs. Consequence: S1 in D0 ranks
  TB-03 #8 first in the whole corpus and TB-01 #10 third, and detects 4 of 6 distributed arcs at 5 %. The frozen
  v1 result is reported as is; a post-hoc variant `S1-v2rulebook` (seeds restricted to the rulebook's five KEEP and
  five DISCARD families) is reported separately and labelled post-hoc because it was written after inspecting the
  evaluation results. v2 is weak in D0 (1-2 arcs at 5-20 %, no concentrated arc) and better with history
  (D3-txt: 6 arcs at 20 %). Recommendation for full scale: freeze rulebook-only seeds, written by someone who has
  not read the arc cards.
- **S1 needs the embedding model's query instruction.** Without it the descriptive seeds and first-person posts
  live in different registers and S1 detected nothing on the dev corpus. Documented in `results/dev/tuning_note.md`.
- **S3-open runs through OpenRouter**, not on CSI hardware, pinned to three providers that return token logprobs.
  Batch non-determinism is measured (two runs at temperature 0).

## 2. Plan criteria that cannot be met as written
- **Criterion 4 (S-rand detects at most 1 arc at 20 %).** With 1-4 signal posts per arc the expected number of arcs
  with at least one signal post in a random 20 % sample is sum over arcs of 1 - 0.8^k = 3.9 for this split
  (observed 3.4, range 1-7 over seeds). The criterion is unattainable by construction; the plan's own note on 1 %
  (~0.1 arcs) extrapolates linearly. Proposal: compare each selector to the S-rand expectation instead
  (detected minus 3.9 at 20 %, minus 1.0 at 5 %, minus 0.2 at 1 %).
- **Criterion 2 (at most 1/6 distributed arcs in D0 at 5 %)** fails for S1 v1 (4) and S0-sub (1.7, tie-dependent):
  some distributed signal posts are too overt on their own. The posts that give the arcs away in D0 are
  TB-03 #8 ("ona w czwartki wraca później i sama"), TB-01 #10 ("w niedzielę będziemy już spokojni, całą trójką"),
  TB-03 #2 (8:15 at the stop), TB-05 #5, TB-08 #3. These are exactly the PI's briefs rendered faithfully; the fix is
  in the arc cards (weaker single-post wording), not in the generator. Plan 11.4 says: adjust the skeleton, do not
  drop the arc.

## 3. Aggregation favours prolific authors
D3-agg = sum of the top-3 scores over the author's posts so far. Arc authors have 9-12 posts; 147 of 184 bystanders
have more (mean 21, max 63). The maximum of three noisy scores grows with the number of draws, so bystanders with
long streams outrank arc authors: Spearman(author post count, best D3-agg score) = 0.51 for S1, 0.32 for S0, against
0.25 / 0.26 for D0. Visible in the results: S1 D0 detects 9 arcs at 20 % but S1 D3-agg only 2. For full scale either
(a) give arc authors the same posting volume as ordinary authors (pad arcs with background posts; the plan's
"average 20 posts per author" should hold for arc authors too), or (b) use a volume-normalised aggregation (e.g. the
mean of the top-3 divided by the expected top-3 of a null stream of the same length). (a) is the cleaner fix.

## 4. Lexical selector
- S0-sub in D0 at 20 % detects 3/4 concentrated arcs (criterion 3 met); S0-veto only 2/4 because the TA-04 signal post
  contains an E-category marker, so the veto variant zeroes it. TA-03 (disclosure of a camera blind spot) carries no
  first-person or timing lexeme and is invisible to S0 by construction.
- The frozen lexicon lacks "dopadnę" (TA-01 #4) in category A: the category was expanded from definitions, not from
  the texts, and this is the price of that rule. Reported, not patched.
- Category C (temporal proximity) fires on 45 % of mundane posts (weekday names, "dziś", "wieczorem"); the ranking
  therefore has massive ties at low scores (tie_span up to 2 arcs at 5 %), as the plan anticipated.

## 5. S3: the budget ranking saturates in D0, the decisions show the incremental effect

**Budget view (plan's main mechanics).** S3-open in D0 detects 7/10 arcs at 1 % and 10/10 at 5 %; S3-blind the same;
D3-nat adds nothing because D0 is already saturated. This is not because the model flags the distributed signal
posts: in D0 it returns KEEP_FOR_REVIEW for only 14 of 4,031 posts (6 arc posts, 8 hard negatives, 0 background).
It is because the continuous score P(KEEP) orders the corpus into three bands: mundane posts at ~0.000, the
hard-negative / borderline band at 0.001-0.3, and a handful of explicit posts near 1. The distributed signal posts
(borderline by construction) sit in the second band, and with 14 % hard negatives any budget of 5 % or less is cut
entirely inside that band. At 5 % S3-open retains 153 hard negatives, 32 background posts and 17 arc posts.
"Detected in D0" therefore means "ranked above the mundane 95 %", which any non-mundane post achieves.
Consequences for the design: (i) criterion 2 cannot discriminate single-post leakage from band membership while the
hard-negative share exceeds the budget; (ii) the budget curve for S3 is flat between 5 % and 20 % and uninformative
about history; (iii) the ranking inside the borderline band is what the full-scale study will measure, so hard
negatives need to be graded (clear_discard vs borderline) in the metrics, not only in generation.

**Decision view (auxiliary classes, budget-independent).** Counting an arc as detected only when a signal post receives
KEEP_FOR_REVIEW reproduces the plan's expected pattern:

| selector | D0: distributed arcs / bystander authors | D3-nat: distributed arcs / bystander authors |
|---|---|---|
| S3-open (deepseek-v4.1-flash) | 2 / 8 | 4 / 15 |
| S3' blind (no signal list) | 4 / 24 | 6 / 53 |
| S3-com (claude-sonnet-5.5, 10 % subsample + signal posts) | 1 / 4 | 4 / 3 |

History doubles the distributed arcs caught (H3) and doubles the bystanders retained (H4); removing the explicit
signal list makes the model both more sensitive and roughly three times more invasive (the explicit criterion list
restrains retention, which is the value of a precise specification that S3' was designed to measure). All concentrated
arcs are kept in every variant. Decoys: S3' D0 keeps one TC post; no other variant keeps any.

**Declared vs internal score.** Spearman between P(KEEP) from logprobs and the declared `retention_score` is 0.50 (D0) and
0.38 (D3-nat): the two scales agree on the extremes and disagree inside the borderline band, i.e. exactly where the
budget cut happens. This is the faithfulness gap the XAI study left open; the logprob is the leading score per plan.

**Control model.** On 425 posts (10 % + all signal posts) S3-com agrees with S3-open on 98 % of decisions; the rank
correlation of declared scores is 0.63 (D0) / 0.50 (D3-nat).

**Determinism.** See `results_card.md` (two runs at temperature 0 on a pinned provider).

## 6. Recommendations before full scale
1. Fix the arc authors' posting volume (pad to the ordinary-author distribution) or change the aggregation; otherwise
   D3-agg measures volume.
2. Re-write the S1 seeds from the rulebook only (by someone blind to the arc cards) and re-freeze.
3. Decide the budget grid relative to the hard-negative share, or report metrics within the non-mundane band
   (e.g. budgets of 1 / 2 / 5 % of posts with hard negatives at 5 % of the corpus), so that D3 can show up in the
   ranking view and not only in decisions.
4. Replace criterion 4 by a comparison with the analytical S-rand expectation.
5. Keep the decision-based view as a co-primary metric; it is where H3/H4 are visible at this scale.
6. Weaken the single-post wording of TB-03 #8, TB-06 #7, TB-01 #10 (the posts that make their arcs visible in D0).
