<!-- prompt_version: persona_v1 | source: plan Annex J (persona card schema) + section 6.5. Protected characteristics banned. -->
SYSTEM
You are creating fictional author profiles ("persona cards") for a synthetic corpus of ordinary Polish public social-media posts. Each card describes HOW a person lives day to day and HOW they type, so that a generator can write posts in their voice. Output strict JSON only.

USER
Create {n} persona cards as a JSON array. Each card is an object with exactly these fields:

- "grammatical_gender": "m" or "f" (needed only for Polish verb agreement; alternate roughly 50/50)
- "schedule_occupation": one sentence: what fills their days (job / study / care duties / retirement / mix), typical daily rhythm (when they are free to post: early morning, commute, lunch, evening, night shift)
- "interests": array of 2-3 short items (sources of post topics; concrete, e.g. "siatkówka w TV", "pieczenie chleba", "stare Volvo")
- "local_reference": one concrete, invented-but-plausible local point of reference in a Polish town or city district (a stop, a shop, a club, a park, a street corner), e.g. "przystanek Rondo Mogilskie", "Biedronka na Skarbowców"
- "writing_style": object with:
    - "sentence_length": "short fragments" | "medium" | "long run-on"
    - "punctuation": short description (e.g. "sparse, no commas", "lots of exclamation marks", "ellipsis everywhere", "correct and complete")
    - "capitalisation": "all lowercase" | "standard" | "random caps for emphasis" | "mostly standard, lowercase starts"
    - "typos": "none" | "rare" | "frequent (missing diacritics, swapped letters)"
    - "abbreviations": "none" | "some (nwm, jj, bd, wgl)" | "heavy"
    - "emoji": "no" | "rare" | "frequent"
- "verbal_tic": one repeatable phrase or habit in Polish (e.g. ends posts with "no i tyle", starts with "ok czyli", overuses "mega", uses "xd" lowercase)
- "posts_per_week": integer 1-4
- "life_situation": one sentence of ordinary current circumstances that could generate posts over three months (e.g. renovating a kitchen, training for a 10 km run, new puppy, night shifts, exams, toddler at home)

Requirements:
- all 200 cards in the corpus must be mutually distinct; these {n} must differ from each other AND from the already used values listed below in occupation, interests, local reference and tic
- spread occupations across the real Polish labour market and life stages (shop work, logistics, offices, trades, healthcare support, teaching, students, parents at home, retirees, gig work, small business, IT, agriculture, services); not everyone is an office worker
- spread writing styles: at least a third should be messy typists (lowercase, typos, abbreviations), some very terse, some verbose
- towns and cities across Poland, big and small, named plausibly; local references must be mundane
- STRICTLY FORBIDDEN in any field: nationality, ethnic origin, religion, sexual orientation, political views, health conditions or disability, or anything implying them; no real public figures
- Polish language in all free-text fields; keep each field short

Already used values (avoid):
- occupations: {used_occupations}
- interests: {used_interests}
- local references: {used_locals}
- tics: {used_tics}

Return only the JSON array.
