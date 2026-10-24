# Model selection for the selectors (working note)

Living document. Started 2026-10-24. Update in place; keep the log at the bottom.

## What the plan prescribes

### Main LLM selector (S3-open)
- Open-weights model that CSI could run locally on one L40s-class GPU. No A100 needed.
- Picked on a sample of the dev corpus during M2. PI approves the pick.
- Named candidates: DeepSeek V4 Flash or Pro, GLM-5.2, Kimi K3, Qwen3.8 27B or Max. Kacper's notes add Inkling.
- Selection rule is pragmatic: the largest model that is sensible locally and competent in Polish.
- Not a model-comparison study. No Chinese vs non-Chinese framing; that is a separate side study.
- Score = log-probability of the decision token; the declared `retention_score` is recorded alongside.
- Temperature 0. Two identical runs to measure non-determinism.
- The same model also runs as S3' with the signal lists removed from the prompt.

### Control LLM (S3-com)
- A different model than the main one. Plan default: a commercial model from the XAI study
  (gpt-5.5, gemini-3.1-pro, grok-4.20, mistral-large-2512, deepseek-v4-pro).
- Only on about 10 % of the corpus, roughly 800 to 1,200 calls.
- Ranked by the declared `retention_score`, since log-probs may be unavailable.

### Embedding model (S1)
- Must handle Polish and a long window (about 20 posts of 40 words for the history variant).
- HerBERT rejected (512-token window), ModernBERT rejected (English only).
- Candidates: Qwen3-Embedding-8B or BGE-M3. Chosen before artifacts are frozen.

### Lexical selector (S0)
- No model at runtime. An LLM expands the word list from category definitions only, never from corpus text.
  Kacper prunes by hand, then the list is frozen with a checksum.

### Process rules
- All selection and tuning on the dev corpus, never on the evaluation corpus.
- Record model version, prompt version, temperature, seeds and per-post outputs for every run.
- Plan's budget estimate: a dozen to twenty-odd GPU hours on one L40s for generation plus about 12,000 scoring calls.

## Current state (provisional picks from the 2026-10-08 trial, not yet approved)

| Slot | Current | Basis | Status |
|---|---|---|---|
| S3-open | Qwen3.8 27B on a local server (decided 2026-10-24). Current results still from `deepseek/deepseek-v4.1-flash` via OpenRouter (provisional) | Qwen3.8-27B was in the 2026-10-08 dev trial: same arcs detected as the others, logprobs available on 78 % of calls via OpenRouter, 100 % parseable | decided; run pending on local hardware |
| S3-com | `google/gemini-3.1-pro-preview` | plan default (XAI study set); disjoint from generator (OpenAI) and S3-open (DeepSeek) | decided 2026-10-24; Sonnet run archived in `results/eval/superseded_s3com_sonnet/` |
| S1 | `qwen/qwen3-embedding-8b` via OpenRouter, with query-instruction prefix | plan candidate; prefix needed (see `experiment/results/dev/tuning_note.md`) | frozen 2026-10-08 |
| S0 | `experiment/artifacts/s0_lexicon.yaml` | LLM draft from definitions (gpt-6-sol), hand-pruned | frozen 2026-10-08 |

Deviation to declare: everything runs through OpenRouter, not on CSI hardware. Non-determinism is measured instead
(decision agreement 100 % / 99.9 % over two runs on v2).

## Todos: models to choose

Four model slots. One model per slot. Plan directives per slot are listed under each.

- [x] **S3-open**, the main LLM selector. Also serves as S3' (same model, blinded prompt). DECIDED 2026-10-24: Qwen3.8 27B, to be run on a local server (not via OpenRouter). No experiments run yet; the DeepSeek results in `results/eval/` stay as the provisional S3-open until the local Qwen run replaces them.
  - open weights, runnable locally on one L40s-class GPU at CSI
  - chosen on a dev-corpus sample; PI approves
  - candidates named in the plan: DeepSeek V4 Flash / Pro, GLM-5.2, Kimi K3, Qwen3.8 27B / Max (Kacper's list adds Inkling)
  - rule: largest model that is sensible locally and competent in Polish
  - score from the log-probability of the decision token; temperature 0; two runs for non-determinism
  - no Chinese vs non-Chinese comparison framing

- [x] **S3-com**, the control LLM selector. DECIDED 2026-10-24: `google/gemini-3.1-pro-preview` (from the XAI study set; different family from the generator and from S3-open).
  - a different model than S3-open
  - plan default: a commercial model from the XAI study (gpt-5.5, gemini-3.1-pro, grok-4.20, mistral-large-2512; deepseek-v4-pro was also in that study but is not commercial)
  - runs on about 10 % of the corpus, 800 to 1,200 calls
  - ranked by the declared `retention_score`; log-probs optional

- [ ] **S1 embedding model**, for the semantic selector.
  - must handle Polish and a window long enough for about 20 posts of 40 words (history variant D3-txt)
  - HerBERT excluded (512-token window), ModernBERT excluded (English)
  - candidates: Qwen3-Embedding-8B (Kacper's proposal) or BGE-M3
  - chosen before artifacts are frozen (stage 0)

- [ ] **Lexicon-expansion LLM** for S0, one-off.
  - expands the word list from the category definitions only, never from corpus texts
  - output is pruned by hand by Kacper, then frozen with a checksum
  - no model constraints stated in the plan

Not a slot: the corpus generator (`openai/gpt-6-sol`, already chosen and used).

## Log

- 2026-10-24: note created from the plan (sections 4, 7, 21, Annexes E-H) and `szkielet.md` section 5.
- 2026-10-24: todos reduced to the four model slots; everything else decided on the fly.
- 2026-10-24: plan directives added under each slot.
- 2026-10-24: S3-open = Qwen3.8 27B, local server. Noted only; no runs yet. Open items when the run is set up: logprob access from the local serving stack (vLLM/llama.cpp expose them), reasoning off, temperature 0, provider pinning no longer applies, re-freeze with the new model id and re-run S3-open + S3' on eval v2 and dev2.
- 2026-10-24: S3-com = gemini-3.1-pro-preview. gpt-5.5 was considered first and dropped because it shares the generator's family. Control run on eval v2 ($3.60 incl. one discarded run): decision agreement with S3-open 99.1 % (D0) / 98.1 % (D3-nat); declared-score Spearman 0.52 / 0.62; by decision 7 arcs in D0, 8 in D3-nat (4/4 concentrated, 3 then 4 distributed), no decoys, no logprobs returned. First attempt discarded: Gemini's thinking tokens hit the 400-token output cap on 108 of 426 history prompts; cap raised to 4,000 for all S3 calls (`selex/s3_llm.py`).
