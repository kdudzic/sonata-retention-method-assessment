<!-- prompt_version: background_batch_v1 | k posts per call, one brief each (ablation for verbalized sampling) -->
SYSTEM
You are generating ordinary, everyday public online posts for a research corpus.
The posts must be completely mundane. Write natural language only.
Do not reveal any labels, variables, or analysis.

Hard exclusions - the posts must contain NONE of the following:
- anger directed at an identifiable person, place, institution, or event
- threats, violence, weapons, or references to harming anyone
- news-report or press framing
- quotation or reporting of someone else's alarming words
- satire or irony about violence
- crime, policing, courts, or security topics
- political or ideological positioning
- references to protected characteristics (nationality, ethnicity, religion, sexual orientation, political views, health conditions)

USER
Generate {k} different short public posts by the same author, one per brief below, in order.
Write in natural Polish, as this specific person would actually type it on their phone.

Author profile:
{persona_card}

Briefs (one post each):
{briefs}

Constraints:
- ordinary user voice, written quickly, not edited
- fragments, lowercase starts, mild messiness allowed; follow the profile's writing habits exactly (punctuation, capitalisation, typos, abbreviations, emoji yes/no)
- do not use the verbal tic in every post; use it only where it fits naturally
- no hashtags unless natural, no emoji unless the profile uses them
- no bullet points, no meta commentary, no explanation of the situation; assume followers know this person
- the posts must differ from each other in opening, structure and rhythm; do not reuse a sentence pattern
- avoid stock openers like "No i", "Ech", "Serio", "Klasyk" and avoid tidy closing punchlines
- must not resemble any of these recently generated posts:
{recent_examples}

Output format: a JSON array of {k} strings only, no prose.
