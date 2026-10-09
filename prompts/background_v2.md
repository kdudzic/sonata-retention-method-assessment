<!-- prompt_version: background_v2 | background_v1 + per-post control of verbal tic and local reference frequency -->
SYSTEM
You are generating ordinary, everyday public online posts for a research corpus.
The posts must be completely mundane. Write natural language only.
Do not reveal any labels, variables, or analysis.

Hard exclusions - the post must contain NONE of the following:
- anger directed at an identifiable person, place, institution, or event
- threats, violence, weapons, or references to harming anyone
- news-report or press framing
- quotation or reporting of someone else's alarming words
- satire or irony about violence
- crime, policing, courts, or security topics
- political or ideological positioning
- references to protected characteristics (nationality, ethnicity, religion, sexual orientation, political views, health conditions)

USER
{output_instruction}
Write in natural Polish, as this specific person would actually type it on their phone.

Author profile:
{persona_card}

Topic for this post: {topic}
Concrete angle: {subtopic}
Register: {register}
Target length: about {length} words
Time of day: {time_of_day}, {weekday}

Constraints:
- ordinary user voice, written quickly, not edited
- fragments, lowercase starts, mild messiness allowed; follow the profile's writing habits exactly (punctuation, capitalisation, typos, abbreviations, emoji yes/no)
- verbal tic in this post: {tic_instruction}
- local reference point in this post: {local_instruction}
- the author's current life situation (from the profile) in this post: {situation_instruction}
- no hashtags unless natural, no emoji unless the profile uses them
- no bullet points, no meta commentary, no explanation of the situation; assume followers know this person
- do not open with a greeting or a day-of-week statement unless natural
- avoid stock openers like "No i", "Ech", "Serio", "Klasyk" and avoid tidy closing punchlines
- must not resemble any of these recently generated posts (different wording, different angle):
{recent_examples}

{output_format}
