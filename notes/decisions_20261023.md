# Decisions of 2026-10-23 (after the PI's notes of 2026-10-13)

## PI's notes and what was done

| PI note | Action | Where |
|---|---|---|
| 1. Split TB-08 #7 into #7 (date + arrangement) and #8 (slur + euphemised act, no date), same exchange, same day; old 8-12 -> 9-13 | regenerated #7 and #8 with gpt-6-sol, 22 min apart; signal set {2, 3, 5, 7, 8} | `data/arcs.yaml`, `corpus/epskel_v1/posts_v2.csv`, `arc_key_v2.csv` |
| 2. TA-04 #4 in the given shape ("banderowcy" + venue + "jutro wieczorem" + 1st person plural + euphemism) | regenerated; model reproduced the PI's sentence in the persona's voice, no refusal | same files |
| 3. Dev corpus gets two arcs, other persons, other seed | TA-05 and TB-09 generated with new persona cards (`data/arc_personas_dev.json`) and seed 7336 into `corpus/epskel_dev_v1/posts_dev2.csv` | `build_dev_arcs.py` |
| 4. Arc author ids must not reveal the arc | all author ids re-drawn from one pool (A001-A200 eval, A001-A032 dev), post ids reassigned in (author, timestamp) order; mapping only in `author_id_map_v2.csv` / `author_id_map_dev2.csv` | `patch_corpus_v2.py`, `build_dev_arcs.py` |

## Arc split (final for the skeleton; PI delegated the choice)

Evaluation: TA-01, TA-02, TA-03, TA-04; TB-01, TB-02, TB-03, TB-05, TB-06, TB-08; TC-01, TC-02.
Dev: TA-05, TB-09. Spare: TB-04, TB-07.

Reasons (full text in `experiment/configs/arc_split.yaml`):
- TA-05 dropped from eval because it shares the doctor theme and the "Tuesday until 18" signal wording with TB-09; one of the pair is enough, and moving both to dev keeps the dev theme disjoint from eval.
- TB-04 dropped: five signal posts over seven weeks cannot be represented by the frozen top-3 aggregation, and five signal posts alone give the random baseline a 67 % chance of a hit at 20 %.
- TB-07 dropped: the motive post relies on an allusion to a real public figure and post 9 is borderline only by euphemism (PI's own note), so it is the arc most likely to fail criterion 2 for reasons unrelated to the hypothesis.
- Kept distributed set covers person x3, infrastructure, intimidation, discriminatory targeting; signal counts 3 / 3 / 4 / 3 / 3 / 5.

## Protocol re-run

All v1-id results moved to `experiment/results/archive_v1_ids/`. Artifacts re-frozen on 2026-10-23 with unchanged lexicon, seeds, prompts, weights and aggregation (same SHA-256 as the 2026-10-08 freeze); only the corpus pointers (v2, dev2) and the split file changed. Scoring on dev2 and v2 launched 2026-10-23 14:50.

Follow-up: selector model selection is tracked in `notes/model_selection.md`.
