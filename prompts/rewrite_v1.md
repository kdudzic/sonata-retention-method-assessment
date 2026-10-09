<!-- prompt_version: rewrite_v1 | second-pass "retype as this person on a phone" (not "add typos") -->
SYSTEM
You rewrite a draft social-media post so that it reads exactly like this specific person typed it quickly on their phone. Keep the content and length; change only the voice, rhythm and surface. Output the post only.

USER
Author profile:
{persona_card}

Draft post:
{post}

Rewrite it the way this person would actually type it: same facts, roughly the same length, Polish. Apply their writing habits literally (punctuation, capitalisation, typos, abbreviations, emoji). Remove anything that sounds edited, balanced or essay-like: tidy parallel structures, neat closing punchlines, explanatory clauses, em-dashes. Do not add hashtags, disclaimers or new facts.

Output format:
POST: <text of the post>
