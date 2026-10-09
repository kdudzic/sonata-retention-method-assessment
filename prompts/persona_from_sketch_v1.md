<!-- prompt_version: persona_from_sketch_v1 | expands a PI persona sketch (Annex D) into a full Annex J card -->
SYSTEM
You expand a short sketch of a fictional author into a full persona card for a synthetic corpus of Polish social-media posts. Output strict JSON only.

USER
Sketch (keep every trait it states; add only what is missing):
{sketch}

Return ONE JSON object with exactly these fields:
- "grammatical_gender": "m" or "f" (follow the sketch if it implies one; otherwise choose)
- "schedule_occupation": one sentence: what fills their days and when they are free to post
- "interests": array of 2-3 short concrete items consistent with the sketch
- "local_reference": one concrete, invented-but-plausible local point of reference in a Polish town (stop, shop, club, park, corner)
- "writing_style": object with "sentence_length" ("short fragments" | "medium" | "long run-on"), "punctuation" (short description), "capitalisation" ("all lowercase" | "standard" | "random caps for emphasis" | "mostly standard, lowercase starts"), "typos" ("none" | "rare" | "frequent (missing diacritics, swapped letters)"), "abbreviations" ("none" | "some (nwm, jj, bd, wgl)" | "heavy"), "emoji" ("no" | "rare" | "frequent") - all derived from the sketch's description of tone and style
- "verbal_tic": one repeatable phrase or habit in Polish
- "posts_per_week": integer 1-4
- "life_situation": one sentence of ordinary circumstances consistent with the sketch (do not add any plot; background only)

Rules: Polish in free-text fields; STRICTLY no nationality, ethnic origin, religion, sexual orientation, political views, health conditions or disability in any field. Return only the JSON object.
