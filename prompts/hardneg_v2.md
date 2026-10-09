<!-- prompt_version: hardneg_v2 | hardneg_v1 + research-context preamble (refusal mitigation) + tic control | source: plan Annex B (single-case adaptation of prompt-mr_20260416). Sections "Hidden Variable Definitions", "Generation Rules", "Anti-Softening Rules", "Style Constraints" and the non-pair items of "Quality Check" are pasted VERBATIM from 1_project/.../data/prompts/prompt_generate.md -->
SYSTEM
Context: this is a publicly funded, ethics-reviewed research project (NCN SONATA, "AI-based bulk surveillance") that measures how automated data-retention selectors behave on a fully synthetic corpus of Polish social-media posts. The corpus needs realistic hard negatives: posts that look alarming on the surface (press reports of threats, quoted threats, angry rhetoric, satire, lyrics) but do not justify retention, as well as genuinely borderline posts. All persons, places and businesses are invented. Nothing operational, instructional or graphic is ever requested. Do not add disclaimers or warnings, and do not soften the post beyond what the hidden variables require.

You are generating one realistic public online post for a legal-technical benchmark.
Write natural language only. Do not reveal labels, factors, or analysis.

USER
{output_instruction}
Generate a short public post consistent with the hidden scenario variables below.
Write the post in natural Polish, as this specific person would actually type it.

Author profile:
{persona_card}

Hidden scenario variables:
- speech_act: {speech_act}
- speaker_perspective: {speaker_perspective}
- target_specificity: {target_specificity}
- imminence: {imminence}
- agency_cue: {agency_cue}
- exculpatory_signal: {exculpatory_signal}
- retention_profile: {retention_profile}
- legal_relevance_focus: {legal_relevance_focus}

## Generation Goals

- This benchmark is not about predicting dangerousness in general.
- It is about generating synthetic posts that allow a reviewer to assess whether there is a clear basis to discard, a genuinely borderline case, or a plausible basis for retaining the post for further review.

## Generation Rules

- The post must reflect the hidden scenario variables naturally and coherently.
- Do not add facts, cues, or implications beyond the specified variables.
- If an exculpatory signal is specified, it must be genuinely visible in the wording.
- If exculpatory_signal == none, do not accidentally soften the case through distancing or dismissive phrases.
- Avoid stereotypes, slurs, and references to protected characteristics unless explicitly required by the scenario.
- Do not introduce fictional, cinematic, song, meme, or cultural references unless explicitly required by the scenario.
- Do not introduce news-report framing unless explicitly required by the scenario.
- No graphic violence, no operational instructions, no explicit weapon-building details.
- The posts should fit a benchmark focused on minimum justified data retention, not on predicting dangerousness.
- Keep the wording plausible and natural, without artificially intensifying the case.
- Do not add extra cues of place, time, capability, coordination, or intent unless explicitly specified.
- If the variable combination implies a plausible basis for retention, make that basis visible in the wording clearly enough that a careful reviewer could identify it.
- If the variable combination implies a borderline case, make it genuinely debatable rather than clearly harmless or clearly alarming.

## Anti-Softening Rules

Unless explicitly required by `exculpatory_signal`, do NOT add phrases such as:

- "just venting"
- "probably nothing"
- "not serious"
- "lol classic"
- "just joking"
- "obviously not real"
- "just blowing off steam"
- "no one would actually do that"

Do not add dismissive or ironic framing unless it is part of the intended hidden scenario.

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

## Hidden Scenario Variable Definitions

### `speech_act`

What the post is doing at its core.

Allowed values:

- declaration of action: the post states that the speaker will do, is doing, or is ready to do something concrete
- expression of anger: the post vents frustration, outrage, or hostility without describing a concrete intended action
- hypothetical statement: the post describes what could, might, or should happen without the speaker committing to act
- humor or joke: the post is framed as non-literal humor or playful exaggeration
- satire or irony: the post uses non-literal exaggeration or mockery to make a point
- counterspeech: the post condemns, discourages, or warns against harmful or threatening action
- general commentary: the post comments on a situation without announcing action, urging others, or clearly venting strong emotion

### `speaker_perspective`

Who is presented as the source of the statement.

Allowed values:

- first person: the speaker presents the content as their own possible action, intention, or view
- third person: the post describes another person's actions, plans, or words
- direct quotation: the post repeats another person's exact words
- indirect report: the post paraphrases or summarizes something heard, read, or reported
- impersonal: no clear speaker or actor is identified

### `target_specificity`

How identifiable the target is.

Allowed values:

- none: no identifiable target
- general group: a broad unnamed category of people
- specific person: a named or clearly identifiable individual
- specific institution: a named organization, office, company, school, court, or public body
- specific place: a named or clearly identifiable location
- specific event: a named or clearly identifiable meeting, rally, match, class, ceremony, or scheduled event
- specific object: a clearly identifiable object or infrastructure element

### `imminence`

How close in time any action appears to be.

Allowed values:

- none: no time cue
- vague future: distant or undefined future
- near future: within days or tied to an upcoming event
- within 24 hours: today, tonight, tomorrow, or another clearly near-term cue

### `agency_cue`

Whether the post signals ability, readiness, or preparation.

Allowed values:

- none: no indication of capability, planning, or preparation
- vague reference: a loose suggestion of ability or willingness without concrete detail
- specific plan or preparation: concrete steps, logistics, preparation, or planning are mentioned
- claimed or demonstrated capability: the speaker claims access, skill, means, or prior experience

### `exculpatory_signal`

A contextual cue arguing against retention even if the wording looks alarming on the surface.

Allowed values:

- none: no visible mitigating context
- news or media context: the wording clearly frames the content as reporting
- counterspeech framing: the content is clearly framed as criticism, warning, or opposition
- ironic or satirical tone: the wording clearly signals non-literal intent
- fictional or cultural reference: the content is clearly presented as belonging to fiction, lyrics, or another cultural text
- hypothetical framing: the wording is clearly conditional or speculative
- emotional venting: the content is clearly only emotional release without concrete action structure

### `retention_profile`

Controls the intended strength of the case for data retention.

Allowed values:

- clear_discard: the scenario should contain a clear basis against retention
- borderline: the scenario should contain mixed or incomplete signals, making the case realistically debatable
- clear_keep: the scenario should contain a plausible, textually grounded basis for further review

### `legal_relevance_focus`

Optional legal salience of the scenario.

Allowed values:

- none
- threat to person
- threat to infrastructure
- intimidation or coercion
- discriminatory targeting
- disclosure-sensitive context

## Additional requirements for this variant

- the post must be consistent with the author profile's speech habits (punctuation, capitalisation, typos, abbreviations, emoji yes/no)
- if target_specificity requires a specific referent, use a concrete, plausible Polish name of a person, institution, place, event or object, never a placeholder
- if retention_profile = clear_discard, the non-retainable structure must be visible on the face of the text
- if retention_profile = borderline, a careful reviewer could reasonably hesitate
- the post concerns the topic area: {topic_hint}
- verbal tic in this post: {tic_instruction}
- local reference point in this post: {local_instruction}
- the author's current life situation (from the profile) in this post: {situation_instruction}

## Quality Check Before Output

Before producing the final post, ensure that:

- the post sounds like a plausible online post by an ordinary user
- it does not sound like a formal complaint, witness statement, administrative description, or polished essay
- the wording remains readable but not overly neat or institutional
- you output only what the output format below asks for and nothing else

{output_format}
