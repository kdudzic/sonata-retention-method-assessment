# Dev-corpus tuning note (plan 11.3: all tuning on the dev corpus only)

Dev corpus: `corpus/epskel_dev_v1` (500 background + 100 hard negatives, 30 authors) + the two dev arcs from the
provisional split (TA-05 concentrated, TB-09 distributed; `configs/arc_split.yaml`), 622 posts.

## S0 (lexical)
- Lexicon: `artifacts/s0_lexicon.yaml` = LLM expansion from the category definitions (prompt `lexicon_expand_v1`,
  gpt-6-sol, no corpus text shown) pruned by hand: removed stems colliding with everyday words (`był*`, `bar*`, `sąd*`,
  `wiec*`, `zakład*`, `gotow*`), removed family nouns and first-person possessives from category B, added the
  rulebook's first-person movement/action verbs to A and readiness phrases to D, regexes for inflected place nouns.
- Control pair from Annex G: "Idę dziś wieczorem na przystanek Ratusz i ktoś dostanie nauczkę" -> A,B,C, s = 10
  (both proximity bonuses fire; Annex G quotes 9); "Policja podała, że mężczyzna groził ..." -> B,C,E, s = 0 (sub) / 0 (veto).
- Category hit rates on dev (share of posts): background A 3 %, B 30 %, C 45 %, D 4 %, E 6 %; hard negatives E 59 %,
  B 52 %. Category C fires on almost half of mundane posts (weekday names, "dziś", "wieczorem"): expected coarseness.
- Weight grid on dev (E in {2,4,6}, AB-proximity in {2,3}, A in {3,4}): detection of the concentrated arc is identical
  everywhere (D0 at 1 %); the distributed arc is reached only in D3-agg at 20 % and only with (E>=4, prox=2, A=3).
  Decision: keep Annex G weights unchanged (A 3, B 2, C 2, D 1, AB-proximity 2, ABC-sentence 1, E 4).
- Category F (identity references) not implemented, per the PI's recommendation (a).

## S1 (semantic)
- Seeds: `artifacts/s1_seeds.yaml`, 14 SEED+ / 16 SEED- Polish descriptions written from the rulebook signal families.
- Embedding model: `qwen/qwen3-embedding-8b` via OpenRouter (4096-d; plan Annex H candidate).
- Finding on dev: with plain embeddings the centred differential score ranked the explicit-threat post 181/622 and
  S1 detected nothing at 20 %. Posts are first-person informal text, seeds are third-person descriptions, and this
  register gap dominated cosine similarity. Using the embedding model's query instruction prefix on the post side
  ("Instruct: Given a short Polish social media post, retrieve the description of the kind of content it is. Query: ...")
  moved it to 11/622; S1 D0 now detects the concentrated dev arc at 5 %. Seeds unchanged (no example posts used).
- First-person "example-like" seeds were tried as a probe and rejected (they are the single-word/paraphrase leakage
  the plan warns about): they ranked the TB-09 reconnaissance post 1/622 because the seed paraphrased its brief.
- D3-vec alpha = 0.5 (not tuned); D3-txt uses up to 40 earlier posts in one window.

## Aggregation
- top-3 sum, frozen (plan section 8); sensitivity analysis deferred to full scale.
