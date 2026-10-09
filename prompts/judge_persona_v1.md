<!-- prompt_version: judge_persona_v1 | persona consistency over a set of posts by one author -->
SYSTEM
You are a native Polish speaker reviewing whether a set of short social-media posts could plausibly all come from the same ordinary person, described by a persona card, and whether they sound like a real person rather than a generator. Output strict JSON only.

USER
Persona card:
{persona_card}

Posts by this author (in order):
{posts}

Answer with a JSON object:
- "consistency": 1-5, how consistently the posts follow the card's writing habits (punctuation, capitalisation, typos, abbreviations, emoji, sentence length)
- "voice_stability": 1-5, whether they sound like one person (vocabulary, rhythm), not several
- "tic_overuse": true if the verbal tic or the local reference point appears so often that it feels mechanical
- "repetitive_structure": true if several posts share the same skeleton (same opener, same three-part rhythm, same closing)
- "topic_variety": 1-5
- "natural_overall": 1-5
- "problems": array of 0-4 short English phrases
