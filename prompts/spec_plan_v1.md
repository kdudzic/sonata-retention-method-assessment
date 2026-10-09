<!-- prompt_version: spec_plan_v1 | planning stage of the spec-first method: concrete post seeds per author -->
SYSTEM
You are planning a sequence of ordinary, mundane public social-media posts for one fictional author. You do not write the posts; you invent the concrete, small, specific everyday occasions behind them. Output strict JSON only.

USER
Author profile:
{persona_card}

For each of the {k} topic prompts below, invent ONE concrete, specific, small occasion from this person's life that would make them post (not a generic statement about the topic: a particular thing that happened, with a detail a real person would mention - a name of a product, a time, a number, a place from their life). Vary mood (bored, amused, tired, pleased, mildly annoyed, neutral, curious), vary how the post starts (mid-thought, a question, a one-word reaction, a fact, a quote of what someone said), and decide whether the verbal tic appears (at most in a third of posts). Occasions must not involve conflict with identifiable people, politics, crime, security, violence, or protected characteristics.

Topic prompts:
{topics}

Return a JSON array of {k} objects, in order, each with:
- "occasion": one or two sentences in Polish, concrete
- "mood": one word in English
- "opener": one of "mid-thought", "question", "one-word reaction", "plain fact", "reported speech", "complaint", "list of two things"
- "length_words": integer between 8 and 50, varied across the set (some very short)
- "tic_fires": true or false
