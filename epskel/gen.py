"""Generators for the three corpus layers plus the method variants under benchmark.

Layers (plan section 6):
  background  - Annex A prompt, attribute sampler (topic/angle/register/length/time)
  hardneg     - Annex B prompt, hidden-variable sampler (clear_discard 60 % / borderline 40 %)
  arc         - Annex C prompt, sequential per arc, with a one-sentence running situation summary

Method variants for the background layer (what the benchmark compares):
  single      - one post per call (baseline)
  vs          - verbalized sampling: k candidates with verbalized probabilities, pick from the tail
  batch       - k posts per call, one brief each, plain JSON (ablation for vs)
  spec_first  - planning call producing k concrete "post seeds" per author, then one call per seed
  rewrite     - single, then a second call "retype this as this person would on a phone"
"""

from __future__ import annotations

import json
import random
import re
from dataclasses import dataclass, field
from typing import Any

import yaml

from . import config
from .llm import LLM, Response, looks_like_refusal
from .personas import render_card, _split

TOPICS = yaml.safe_load((config.DATA / "topics.yaml").read_text(encoding="utf-8"))
ARCS = yaml.safe_load((config.DATA / "arcs.yaml").read_text(encoding="utf-8"))["arcs"]
HIDDEN = json.loads(
    (config.ROOT.parent / "1_project" / "sonata-ai-bulk-surveillance" / "data" / "hidden_variables.json").read_text()
)

TIMES = ["early morning", "morning commute", "late morning", "lunch break", "afternoon", "evening", "late night"]
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

OUT_SINGLE = "Output format:\nPOST: <text of the post>"
TIC_YES = "yes, use it once, naturally"
TIC_NO = "do not use it in this post"
LOCAL_YES = "you may mention it if it fits"
LOCAL_NO = "do not mention it in this post"
SIT_YES = "you may refer to it"
SIT_NO = "do not refer to it; this post is about something else"


def style_flags(rng: random.Random, p_tic: float = 0.30, p_local: float = 0.25, p_sit: float = 0.30) -> dict:
    return {"tic_instruction": TIC_YES if rng.random() < p_tic else TIC_NO,
            "local_instruction": LOCAL_YES if rng.random() < p_local else LOCAL_NO,
            "situation_instruction": SIT_YES if rng.random() < p_sit else SIT_NO}
INSTR_SINGLE = "Generate one short public post."


# ----------------------------------------------------------------------------- helpers
def messages_from(template: str, **slots: Any) -> list[dict[str, str]]:
    sys_part, user_part = _split(config.read_prompt(template))
    # format only known slots; leave braces in pasted text alone
    user = user_part
    for k, v in slots.items():
        user = user.replace("{" + k + "}", str(v))
    return [{"role": "system", "content": sys_part}, {"role": "user", "content": user}]


def parse_single(text: str) -> str:
    t = text.strip()
    m = re.search(r"POST:\s*(.*)", t, flags=re.S)
    if m:
        t = m.group(1).strip()
    t = re.sub(r"^```[a-z]*\n?|\n?```$", "", t).strip()
    # drop surrounding quotes if the whole thing is quoted
    if len(t) > 2 and t[0] in "\"„“" and t[-1] in "\"”“":
        t = t[1:-1].strip()
    return t


def parse_json(text: str) -> Any:
    t = text.strip()
    t = re.sub(r"^```[a-zA-Z]*\n?", "", t)
    t = re.sub(r"\n?```$", "", t)
    i = min([x for x in (t.find("["), t.find("{")) if x >= 0], default=-1)
    j = max(t.rfind("]"), t.rfind("}"))
    if i < 0 or j < 0:
        raise ValueError("no JSON in response")
    return json.loads(t[i : j + 1])


def sample_length(rng: random.Random) -> int:
    cfg = TOPICS["length"]
    return int(round(rng.triangular(cfg["min"], cfg["max"], cfg["mode"])))


def sample_attrs(rng: random.Random) -> dict:
    topics = TOPICS["topics"]
    t = rng.choices(topics, weights=[x["weight"] for x in topics])[0]
    return {
        "topic_id": t["id"],
        "topic": t["label"],
        "subtopic": rng.choice(t["sub"]),
        "register": rng.choice(TOPICS["registers"]),
        "length": sample_length(rng),
        "time_of_day": rng.choice(TIMES),
        "weekday": rng.choice(WEEKDAYS),
        **style_flags(rng),
    }


@dataclass
class Post:
    text: str
    layer: str
    author_id: str
    method: str
    model: str
    prompt_version: str
    attrs: dict = field(default_factory=dict)
    call_ids: list[str] = field(default_factory=list)
    cost: float = 0.0
    refused: bool = False
    raw_text: str = ""
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = self.__dict__.copy()
        return d


# ----------------------------------------------------------------------------- background
class BackgroundGenerator:
    def __init__(self, llm: LLM, method: str = "single", k: int = 5, tau: float = 0.10, seed: int = 0,
                 prompt_version: str = "background_v2", rewrite_llm: LLM | None = None) -> None:
        self.llm = llm
        self.method = method
        self.k = k
        self.tau = tau
        self.rng = random.Random(seed)
        self.pv = prompt_version
        self.rewrite_llm = rewrite_llm or llm
        self.spec_prompt = "spec_plan_v2"
        self.recent: dict[str, list[str]] = {}  # topic_id -> recent posts (anti-repetition)

    def _recent(self, topic_id: str) -> str:
        r = self.recent.get(topic_id, [])[-3:]
        return "\n".join(f"  - {x}" for x in r) if r else "  (none yet)"

    def _remember(self, topic_id: str, text: str) -> None:
        self.recent.setdefault(topic_id, []).append(text)

    def _base_slots(self, card: dict, attrs: dict) -> dict:
        return dict(
            persona_card=render_card(card), topic=attrs["topic"], subtopic=attrs["subtopic"],
            register=attrs["register"], length=attrs["length"], time_of_day=attrs["time_of_day"],
            weekday=attrs["weekday"], recent_examples=self._recent(attrs["topic_id"]),
            tic_instruction=attrs.get("tic_instruction", TIC_NO), local_instruction=attrs.get("local_instruction", LOCAL_NO),
            situation_instruction=attrs.get("situation_instruction", SIT_NO),
        )

    # --- public: generate n posts for one author
    def generate_for_author(self, card: dict, n: int) -> list[Post]:
        if self.method == "single":
            return [self._single(card, sample_attrs(self.rng)) for _ in range(n)]
        if self.method == "rewrite":
            return [self._rewrite(self._single(card, sample_attrs(self.rng))) for _ in range(n)]
        if self.method == "vs":
            return [self._vs(card, sample_attrs(self.rng)) for _ in range(n)]
        if self.method == "batch":
            out: list[Post] = []
            while len(out) < n:
                out.extend(self._batch(card, [sample_attrs(self.rng) for _ in range(min(self.k, n - len(out)))]))
            return out[:n]
        if self.method in ("spec_first", "spec_vs"):
            return self._spec_first(card, n)
        raise ValueError(self.method)

    # --- single
    def _single(self, card: dict, attrs: dict) -> Post:
        msgs = messages_from(f"{self.pv}.md", output_instruction=INSTR_SINGLE, output_format=OUT_SINGLE,
                             **self._base_slots(card, attrs))
        r = self.llm.chat(msgs, tag="bg_single", max_tokens=None, seed=self.rng.randint(0, 2**31))
        text = parse_single(r.text)
        self._remember(attrs["topic_id"], text)
        return Post(text, "background", card["author_id"], "single", self.llm.model, self.pv, attrs,
                    [r.call_id], r.cost, r.refused or looks_like_refusal(text), r.text,
                    {"card_txt": render_card(card)})

    # --- rewrite
    def _rewrite(self, p: Post) -> Post:
        msgs = messages_from("rewrite_v1.md", persona_card=p.extra.get("card_txt", ""), post=p.text)
        r = self.rewrite_llm.chat(msgs, tag="bg_rewrite", max_tokens=None, seed=self.rng.randint(0, 2**31))
        text = parse_single(r.text)
        return Post(text, "background", p.author_id, "rewrite", self.llm.model, self.pv, p.attrs,
                    p.call_ids + [r.call_id], p.cost + r.cost, p.refused or r.refused, r.text,
                    {"draft": p.text})

    # --- verbalized sampling
    def _vs(self, card: dict, attrs: dict) -> Post:
        instr = (
            f"Generate {self.k} different candidate versions of one short public post for the brief below. "
            f"Sample at random from the tails of the distribution of what this author might write, such that the "
            f"probability of each candidate is less than {self.tau:.2f}. The candidates must differ in wording and angle."
        )
        fmt = (
            "Output format: a JSON array only, no prose:\n"
            '[{"text": "<post>", "probability": <number between 0 and 1>}, ...]'
        )
        msgs = messages_from(f"{self.pv}.md", output_instruction=instr, output_format=fmt,
                             **self._base_slots(card, attrs))
        r = self.llm.chat(msgs, tag="bg_vs", max_tokens=None, seed=self.rng.randint(0, 2**31))
        try:
            cands = [c for c in parse_json(r.text) if isinstance(c, dict) and c.get("text")]
        except Exception:
            cands = []
        if not cands:
            text = parse_single(r.text)
            chosen = {"text": text, "probability": None}
        else:
            tail = [c for c in cands if isinstance(c.get("probability"), (int, float)) and c["probability"] < self.tau]
            chosen = self.rng.choice(tail) if tail else min(cands, key=lambda c: c.get("probability") or 1.0)
            text = parse_single(str(chosen["text"]))
        self._remember(attrs["topic_id"], text)
        return Post(text, "background", card["author_id"], "vs", self.llm.model, self.pv, attrs, [r.call_id],
                    r.cost, r.refused or looks_like_refusal(text), r.text,
                    {"candidates": cands, "chosen_p": chosen.get("probability")})

    # --- plain batch
    def _batch(self, card: dict, attrs_list: list[dict]) -> list[Post]:
        briefs = "\n".join(
            f"{i+1}. topic: {a['topic']}; angle: {a['subtopic']}; register: {a['register']}; "
            f"about {a['length']} words; {a['time_of_day']}, {a['weekday']}"
            for i, a in enumerate(attrs_list)
        )
        msgs = messages_from("background_batch_v1.md", persona_card=render_card(card), k=len(attrs_list),
                             briefs=briefs, recent_examples=self._recent(attrs_list[0]["topic_id"]))
        r = self.llm.chat(msgs, tag="bg_batch", max_tokens=None,
                          seed=self.rng.randint(0, 2**31))
        try:
            texts = [parse_single(str(x)) for x in parse_json(r.text)]
        except Exception:
            texts = [parse_single(r.text)]
        out = []
        for a, t in zip(attrs_list, texts):
            self._remember(a["topic_id"], t)
            out.append(Post(t, "background", card["author_id"], "batch", self.llm.model, self.pv, a, [r.call_id],
                            r.cost / max(1, len(texts)), r.refused or looks_like_refusal(t), r.text))
        return out

    # --- spec-first
    def _spec_first(self, card: dict, n: int) -> list[Post]:
        attrs_list = [sample_attrs(self.rng) for _ in range(n)]
        topics = "\n".join(f"{i+1}. {a['topic']} - {a['subtopic']} ({a['time_of_day']}, {a['weekday']})"
                           for i, a in enumerate(attrs_list))
        msgs = messages_from(f"{self.spec_prompt}.md", persona_card=render_card(card), k=n, topics=topics)
        r = self.llm.chat(msgs, tag="bg_spec_plan", max_tokens=None, seed=self.rng.randint(0, 2**31))
        try:
            seeds = parse_json(r.text)
            assert isinstance(seeds, list) and len(seeds) >= 1
        except Exception:
            seeds = []
        out = []
        for i, a in enumerate(attrs_list):
            s = seeds[i] if i < len(seeds) and isinstance(seeds[i], dict) else {}
            a2 = dict(a)
            if s:
                a2["subtopic"] = (
                    f"{s.get('occasion', a['subtopic'])} | mood: {s.get('mood', '')} | "
                    f"opener: {s.get('opener', '')} | verbal tic in this post: {'yes' if s.get('tic_fires') else 'no'}"
                )
                if isinstance(s.get("length_words"), int):
                    a2["length"] = s["length_words"]
            p = self._vs(card, a2) if self.method == "spec_vs" else self._single(card, a2)
            p.method = self.method
            p.call_ids = [r.call_id] + p.call_ids
            p.cost += r.cost / n
            p.extra["seed"] = s
            out.append(p)
        return out


# ----------------------------------------------------------------------------- hard negatives
CONFLICT_DOMAINS = [
    "spór sąsiedzki (hałas, parking, śmieci)", "konflikt w pracy z przełożonym lub firmą", "szkoła: konflikt ucznia z nauczycielem lub rówieśnikiem",
    "kibice i mecz lokalnej drużyny", "komentarz do wiadomości o polityku lub urzędzie", "spór z wynajmującym lub spółdzielnią",
    "kłótnia w internecie z nieznajomym", "były partner / była partnerka", "rada miasta, remont, decyzja urzędu", "kurier, sklep, bank - reklamacja",
    "ruch drogowy, kierowca, rowerzysta", "relacja z protestu lub demonstracji", "serial / gra / książka z przemocą", "tekst piosenki lub cytat z filmu",
    "wiadomości o przestępstwie w okolicy", "dług, pożyczka od znajomego", "kłótnia rodzinna o spadek", "windykacja, komornik",
]


def sample_hidden(rng: random.Random) -> dict:
    """Annex B distribution with light coherence rules."""
    profile = "clear_discard" if rng.random() < 0.60 else "borderline"
    focus = rng.choice([f for f in HIDDEN["legal_relevance_focus"] if f != "none"] + ["none"])
    if profile == "clear_discard":
        exc = rng.choice([e for e in HIDDEN["exculpatory_signal"] if e != "none"])
        if exc == "news or media context":
            persp = rng.choice(["indirect report", "direct quotation", "third person"])
            act = rng.choice(["general commentary", "expression of anger", "counterspeech"])
        elif exc == "counterspeech framing":
            persp = rng.choice(["first person", "impersonal"])
            act = "counterspeech"
        elif exc == "ironic or satirical tone":
            persp = rng.choice(["first person", "impersonal", "third person"])
            act = rng.choice(["satire or irony", "humor or joke"])
        elif exc == "fictional or cultural reference":
            persp = rng.choice(["direct quotation", "first person", "impersonal"])
            act = rng.choice(["general commentary", "humor or joke"])
        elif exc == "hypothetical framing":
            persp = rng.choice(["first person", "impersonal"])
            act = "hypothetical statement"
        else:  # emotional venting
            persp = rng.choice(["first person", "impersonal"])
            act = "expression of anger"
        target = rng.choice(HIDDEN["target_specificity"])
        imm = rng.choice(HIDDEN["imminence"])
        agency = rng.choice(["none", "none", "vague reference"])
    else:  # borderline: mixed, incomplete signals, no clear exculpation
        exc = rng.choice(["none", "none", "emotional venting", "hypothetical framing"])
        persp = rng.choice(["first person", "first person", "third person", "impersonal"])
        act = rng.choice(["expression of anger", "hypothetical statement", "declaration of action", "general commentary"])
        # at most two of the four KEEP components, never all
        comps = rng.sample(["target", "imminence", "agency"], k=rng.choice([1, 2]))
        target = rng.choice(["specific person", "specific institution", "specific place", "specific event"]) if "target" in comps else rng.choice(["none", "general group"])
        imm = rng.choice(["near future", "within 24 hours"]) if "imminence" in comps else rng.choice(["none", "vague future"])
        agency = rng.choice(["vague reference", "specific plan or preparation", "claimed or demonstrated capability"]) if "agency" in comps else "none"
        if act == "declaration of action" and len(comps) == 2:
            act = "hypothetical statement"
    return dict(speech_act=act, speaker_perspective=persp, target_specificity=target, imminence=imm, agency_cue=agency,
                exculpatory_signal=exc, retention_profile=profile, legal_relevance_focus=focus,
                topic_hint=rng.choice(CONFLICT_DOMAINS))


class HardNegGenerator:
    def __init__(self, llm: LLM, seed: int = 0, prompt_version: str = "hardneg_v1") -> None:
        self.llm = llm
        self.rng = random.Random(seed)
        self.pv = prompt_version

    def generate(self, card: dict, hidden: dict | None = None) -> Post:
        h = hidden or sample_hidden(self.rng)
        msgs = messages_from(f"{self.pv}.md", output_instruction=INSTR_SINGLE, output_format=OUT_SINGLE,
                             persona_card=render_card(card), **style_flags(self.rng), **h)
        r = self.llm.chat(msgs, tag="hardneg", max_tokens=None, seed=self.rng.randint(0, 2**31))
        text = parse_single(r.text)
        return Post(text, "hardneg", card["author_id"], "single", self.llm.model, self.pv, h, [r.call_id], r.cost,
                    r.refused or looks_like_refusal(text), r.text)


# ----------------------------------------------------------------------------- arcs
class ArcGenerator:
    def __init__(self, llm: LLM, seed: int = 0, prompt_version: str = "arc_post_v1", summarizer: LLM | None = None) -> None:
        self.llm = llm
        self.rng = random.Random(seed)
        self.pv = prompt_version
        self.summarizer = summarizer or llm

    def summarize(self, posts: list[str]) -> str:
        if not posts:
            return "(nothing yet - this is the first post)"
        msgs = messages_from("situation_summary_v1.md", posts="\n".join(f"- {p}" for p in posts))
        r = self.summarizer.chat(msgs, tag="arc_summary", max_tokens=None, temperature=0.3)
        return r.text.strip().splitlines()[0] if r.text.strip() else "(no summary)"

    def generate_arc(self, arc: dict, card: dict) -> list[Post]:
        out: list[Post] = []
        texts: list[str] = []
        total = len(arc["posts"])
        prev_day = 0
        for p in arc["posts"]:
            situation = self.summarize(texts)
            msgs = messages_from(
                f"{self.pv}.md", output_instruction=INSTR_SINGLE, output_format=OUT_SINGLE,
                persona_card=render_card(card), n=p["n"], total=total, gap_days=(p["day"] - prev_day) if out else "-",
                situation_so_far=situation, previous_post=texts[-1] if texts else "(none)",
                arc_role=p["role"], post_brief=p["brief"], post_level_profile=p["profile"],
                **style_flags(self.rng, p_tic=0.30, p_local=0.20),
            )
            r = self.llm.chat(msgs, tag=f"arc_{arc['arc_id']}", max_tokens=None, seed=self.rng.randint(0, 2**31))
            text = parse_single(r.text)
            texts.append(text)
            prev_day = p["day"]
            out.append(Post(text, "arc", card["author_id"], "single", self.llm.model, self.pv,
                            {"arc_id": arc["arc_id"], "n": p["n"], "day": p["day"], "role": p["role"],
                             "profile": p["profile"], "brief": p["brief"], "situation_so_far": situation},
                            [r.call_id], r.cost, r.refused or looks_like_refusal(text), r.text))
        return out
