# Calibration note (plan section 15: "what came out differently than planned")

Draft 2026-10-08 on corpus v1; section 7 added 2026-10-23 after the re-run on corpus v2 (PI corrections, blind ids, final arc split). Sections on S3 are filled after the S3 runs complete (see results_card.md).

## 1. Protocol deviations to declare
- **Arc split.** Final on 2026-10-23, delegated by the PI; rationale in `configs/arc_split.yaml` and `notes/decisions_20261023.md`.
  Dev arcs TA-05 and TB-09 now have their own persona cards and seed (`posts_dev2.csv`), as the plan requires.
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

## 7. Re-run on corpus v2 (2026-10-23)

Changes between v1 and v2: TA-04 #4 regenerated with "banderowcy"; TB-08 #7 split into #7 (date + arrangement) and
#8 (slur + euphemised act, no date); all author and post identifiers re-drawn so that the identifier carries no label.
Same frozen lexicon, seeds, prompts, weights and aggregation (hash-identical). Scoring cost $6.72.

**Stability.** Every budget-view number for S0, S1, S3-open and S3' is within one arc of the v1 value (table in
`bench_compare_v1_v2.py` output). Determinism of S3-open across two runs: decision agreement 100 % (D0) and 99.9 %
(D3-nat), score Spearman 0.89 / 0.91. S-rand at 20 % moved from 3.4 to 4.6 arcs because TB-08 now has five signal
posts (expected value 1 - 0.8^5 = 0.67 for that arc alone); criterion 4 remains unattainable by construction.

**Did the PI's two corrections do what they were meant to do?**
- TB-08: no single post is flagged any more. In S3-open D0 the five signal posts rank between 2.8 % and 15 % of the
  corpus (p_keep 0.000-0.012, all DISCARD); #8 alone carries the historical euphemism and sits at 2.8 %, #7 (date only)
  at 15 %. In D3-nat the arc is still retained only through the ranking band, not through a KEEP decision: S3-open
  keeps 4 of 6 distributed arcs by decision in D3-nat, the same four as in v1 (TB-01, TB-03, TB-05, TB-06); TB-08 is
  not among them, and neither is TB-02. S3' does keep all six distributed arcs by decision in D3-nat (as in v1). So
  the split made TB-08 strictly a history-only arc for the rule-following selector, which is the intended design.
- TA-04 #4 with "banderowcy": p_keep 1.000, rank 2 of 4,032 in D0. Comparable now to TB-08 #8 in wording, and the
  concentrated/distributed contrast between the two arcs is the one the PI wanted.

**One flip to note.** TA-03 #5 (camera blind spot + "I'd earn more than in a year here") is DISCARD in both v2 runs
with p_keep 0.438, after KEEP in v1 with the same text. It is the softest concentrated signal post by construction
(disclosure plus a conditional gain, no target person, no date) and sits on the decision boundary; in the budget view
it is retained at 1 % in every S3 variant, so the arc count is unaffected. For the full-scale corpus the PI may want
the TA-03 brief to state the intent less conditionally, or accept it as the designed "weakest concentrated" case.

**Decision view, v2 (KEEP_FOR_REVIEW only).**

| selector | D0: distributed arcs / bystander authors | D3-nat: distributed arcs / bystander authors |
|---|---|---|
| S3-open (two runs) | 2 / 6 and 1 / 6 | 4 / 18 and 4 / 17 |
| S3' blind | 3 / 22 | 6 / 77 |
| S3-com (subsample) | 2 / 2 | 3 / 4 |

The H3/H4 pattern of v1 holds: history roughly doubles both the distributed arcs caught and the bystanders retained,
and the explicit signal list restrains retention by a factor of three to four.

**Dev2.** With new personas and seed, TA-05 is caught by S0, S1 and S3 in D0 at 5 % or lower; TB-09 by S3-open
only in D3-nat (decision view: 0 distributed arcs in D0, 1 in D3-nat). Dev2 therefore reproduces the eval pattern on
unseen text, which is what the dev corpus is for.

## 8. Control model switched to gemini-3.1-pro-preview (2026-10-24)

S3-com is now the plan's default, a commercial model from the XAI study set, disjoint from the generator (OpenAI) and
S3-open (DeepSeek). On the 426-post subsample it agrees with S3-open on 99.1 % (D0) and 98.1 % (D3-nat) of decisions;
by decision it keeps 7 arcs in D0 and 8 in D3-nat, the same H3 direction as S3-open. Gemini returns no token logprobs,
so its ranking uses the declared `retention_score` as the plan foresees. Operational finding: with a 400-token output
cap Gemini truncated 108 of 426 history prompts (thinking tokens), which silently turned hard cases into parse errors;
the cap is now 4,000 for every S3 call and the truncated run is kept under `superseded_s3com_gemini_cap400/`.
