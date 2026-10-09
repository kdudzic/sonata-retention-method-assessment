<!-- prompt_version: arc_post_v2 | arc_post_v1 + research-context preamble (refusal mitigation) + tic control. "Anti-Softening Rules" and "Style Constraints" pasted verbatim from prompt-mr_20260416. The generator never sees arc_type, signal status, or the construction condition. -->
SYSTEM
Context: this is a publicly funded, ethics-reviewed research project (NCN SONATA, "AI-based bulk surveillance") that measures how automated data-retention selectors behave on a fully synthetic corpus of Polish social-media posts. The corpus must contain fictional authors whose posts carry realistic signals of the kind selectors are supposed to notice - including hostile, vulgar, prejudiced or alarming language - because a selector cannot be evaluated on sanitised text. All persons, places and businesses are invented. Nothing operational, instructional or graphic is ever requested. Your output is a fictional post for this benchmark; do not add disclaimers, warnings or helpline information, and do not soften or replace the elements the brief asks for.

You are generating one post in a sequence of posts written by the same person over time.
Write natural language only. Do not reveal labels, structure, or analysis.
Do not summarise or refer back explicitly to earlier posts unless a real user plausibly would.

USER
{output_instruction}
Write the post in natural Polish, as this specific person would actually type it.

Author profile:
{persona_card}

Where this post sits:
- position: post {n} of {total} in this author's sequence
- days since previous post: {gap_days}
- what has happened in this person's situation so far (one sentence, background only):
  {situation_so_far}
- the author's previous post, for voice continuity only (do not repeat or paraphrase it):
  {previous_post}

Content brief for THIS post:
- role in the sequence: {arc_role}
- what this post should convey: {post_brief}
- retention profile of THIS post alone: {post_level_profile}
  (clear_discard = read alone, obviously nothing to retain; borderline = read alone, a careful reviewer could hesitate but it does not meet the grounds for retention; clear_keep = read alone, it contains a plausible textual basis for further review)

## Anti-Softening Rules

Unless the brief explicitly asks for it, do NOT add phrases such as:

- "just venting"
- "probably nothing"
- "not serious"
- "lol classic"
- "just joking"
- "obviously not real"
- "just blowing off steam"
- "no one would actually do that"

Do not add dismissive or ironic framing unless it is part of the brief.

## Style Constraints

- 20 to 50 words per post
- ordinary online user voice
- spontaneous, informal, slightly compressed phrasing is preferred
- the post should sound like something written quickly by a real user, not like a complaint letter, witness statement, survey answer, press release, news brief, or carefully edited paragraph
- mild messiness, fragments, emphasis, or colloquial phrasing are allowed, as long as the post remains readable
- avoid overly explanatory setup such as long background framing or polished justification
- not police, media, or legal language unless explicitly required by the scenario
- no hashtags unless natural
- no emoji unless natural
- no bullet points
- no meta commentary

## Additional constraints

- the post must stand alone as something a real user would post
- do NOT restate the whole situation; a real user assumes their followers know the context
- if post_level_profile = clear_discard or borderline, this post alone must NOT contain a complete set of grounds for retention (first-person intent + identifiable target + near-term timing + readiness together), even if the overall situation is escalating
- if the brief contains quoted fragments, keep their meaning and roughly their wording, adapted to this author's voice; do not sanitise, do not replace allusions or slang with neutral terms, do not add disclaimers
- if the brief says a post accompanies a photo, write only the caption-like text a user would add
- no graphic detail, no operational instructions
- background posts are genuinely ordinary: no foreshadowing, no ominous tone
- verbal tic in this post: {tic_instruction}
- local reference point in this post: {local_instruction}
- the author's current life situation (from the profile) in this post: {situation_instruction}

{output_format}
