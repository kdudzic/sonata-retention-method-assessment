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
| S3-open | `deepseek/deepseek-v4.1-flash` via OpenRouter, providers pinned to Together / DigitalOcean / Novita (return logprobs) | 200-post dev trial vs GLM-5.3-flash, Qwen3.8-27B, Kimi K3: same arcs detected, cheapest, 100 % parseable | provisional |
| S3-com | `anthropic/claude-sonnet-5.5` | different family from the generator (OpenAI) and from S3-open | provisional; deviates from the plan default |
| S1 | `qwen/qwen3-embedding-8b` via OpenRouter, with query-instruction prefix | plan candidate; prefix needed (see `experiment/results/dev/tuning_note.md`) | frozen 2026-10-08 |
| S0 | `experiment/artifacts/s0_lexicon.yaml` | LLM draft from definitions (gpt-6-sol), hand-pruned | frozen 2026-10-08 |

Deviation to declare: everything runs through OpenRouter, not on CSI hardware. Non-determinism is measured instead
(decision agreement 100 % / 99.9 % over two runs on v2).

## Todos: models to choose

Four model slots. One model per slot.

- [ ] **S3-open**, the main LLM selector. Open-weights, locally runnable. Also serves as S3' (blinded prompt).
- [ ] **S3-com**, the control LLM selector. Different family than S3-open; runs on a 10 % subsample.
- [ ] **S1 embedding model**, for the semantic selector. Polish, long window.
- [ ] **Lexicon-expansion LLM** for S0, one-off use to draft the word list from category definitions.

Not a slot: the corpus generator (`openai/gpt-6-sol`, already chosen and used).

## Log

- 2026-10-24: note created from the plan (sections 4, 7, 21, Annexes E-H) and `szkielet.md` section 5.
- 2026-10-24: todos reduced to the four model slots; everything else decided on the fly.
