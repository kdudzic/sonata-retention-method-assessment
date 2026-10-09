"""Persona cards (plan Annex J) and their rendering for generator prompts.

Cards are generated in batches by an LLM, then screened: (1) a forbidden-term
check for protected characteristics, (2) embedding-based dispersion (a card too
similar to an existing one is rejected and regenerated) - the survey evidence
says set-level persona dispersion matters more than per-card detail.
"""

from __future__ import annotations

import json
import random
import re
from pathlib import Path

from . import config
from .llm import LLM

PROMPT_VERSION = "persona_v1"

# Terms whose presence in a card indicates a protected-characteristic leak.
# Deliberately broad; false positives are cheap (card is just regenerated).
FORBIDDEN = [
    r"\bukrai", r"\bbiałoru", r"\brosja", r"\brosyj", r"\bniemc", r"\bniemiec", r"\bwietnam", r"\bhindus",
    r"\bromsk", r"\bcygan", r"\bżyd", r"\bmuzułm", r"\bislam", r"\bkatoli", r"\bkości[óo]ł", r"\bparafi",
    r"\bksiądz", r"\breligi", r"\bwiar[ay]\b", r"\bmsz[ay]\b", r"\bmodli",
    r"\bgej\b", r"\blesb", r"\blgbt", r"\bhomoseks", r"\borientac",
    r"\bpis\b", r"\bpo\b.*\bpartia", r"\bpartia", r"\bpolity", r"\bwybor", r"\bkonfederac", r"\blewic", r"\bprawic",
    r"\bniepełnospraw", r"\binwalid", r"\bdepresj", r"\bchorob", r"\bchory\b", r"\bchora\b", r"\bterapi", r"\bpsychiatr",
    r"\bnałog", r"\balkoholi", r"\bcukrzyc", r"\bnowotw", r"\brak\b", r"\brenta\b", r"\brencist",
    r"\bimigrant", r"\bmigrant", r"\buchodź", r"\bobcokrajow", r"\bcudzoziem", r"\bnarodow",
]
_FORBIDDEN_RE = [re.compile(p, re.I) for p in FORBIDDEN]


def forbidden_hits(card: dict) -> list[str]:
    blob = json.dumps(card, ensure_ascii=False).lower()
    return [p.pattern for p in _FORBIDDEN_RE if p.search(blob)]


def render_card(card: dict) -> str:
    """Compact text block inserted into generator prompts."""
    ws = card["writing_style"]
    g = "mężczyzna (formy męskie)" if card["grammatical_gender"] == "m" else "kobieta (formy żeńskie)"
    lines = [
        f"- płeć gramatyczna: {g}",
        f"- zajęcie i rytm dnia: {card['schedule_occupation']}",
        f"- zainteresowania: {', '.join(card['interests'])}",
        f"- lokalny punkt odniesienia: {card['local_reference']}",
        f"- aktualna sytuacja życiowa: {card.get('life_situation', '')}",
        "- sposób pisania: "
        f"zdania: {ws['sentence_length']}; interpunkcja: {ws['punctuation']}; "
        f"wielkie litery: {ws['capitalisation']}; literówki: {ws['typos']}; "
        f"skróty: {ws['abbreviations']}; emoji: {ws['emoji']}",
        f"- tik językowy: {card['verbal_tic']}",
    ]
    return "\n".join(lines)


def _extract_json_array(text: str) -> list:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
    i, j = text.find("["), text.rfind("]")
    if i < 0 or j < 0:
        raise ValueError("no JSON array in response")
    return json.loads(text[i : j + 1])


def generate_personas(
    llm: LLM,
    n_total: int,
    batch: int = 10,
    seed: int = 0,
    existing: list[dict] | None = None,
    sim_threshold: float = 0.90,
    embedder=None,
    parallel: int = 4,
) -> list[dict]:
    """Generate n_total cards (in addition to `existing`), screened for leaks and near-duplicates."""
    rng = random.Random(seed)
    tmpl = config.read_prompt(f"{PROMPT_VERSION}.md")
    sys_part, user_part = _split(tmpl)
    cards: list[dict] = list(existing or [])
    start_id = len(cards)
    rejected = {"forbidden": 0, "similar": 0, "schema": 0}
    attempts = 0
    from concurrent.futures import ThreadPoolExecutor

    while len(cards) - start_id < n_total:
        attempts += 1
        if attempts > 3 * (n_total // batch + 1) + 3:
            raise RuntimeError(f"persona generation stalled: {rejected}")
        remaining = n_total - (len(cards) - start_id)
        n_calls = max(1, min(parallel, -(-remaining // batch)))
        used_occ = "; ".join(c["schedule_occupation"][:60] for c in rng.sample(cards, min(40, len(cards)))) or "-"
        used_int = "; ".join(i for c in rng.sample(cards, min(40, len(cards))) for i in c["interests"]) or "-"
        used_loc = "; ".join(c["local_reference"] for c in rng.sample(cards, min(60, len(cards)))) or "-"
        used_tic = "; ".join(c["verbal_tic"] for c in rng.sample(cards, min(60, len(cards)))) or "-"

        def one(seed_i: int) -> list:
            k = batch
            user = user_part.format(
                n=k, used_occupations=used_occ, used_interests=used_int, used_locals=used_loc, used_tics=used_tic
            )
            r = llm.chat(
                [{"role": "system", "content": sys_part}, {"role": "user", "content": user}],
                tag="persona", temperature=1.0, max_tokens=600 * k + 300, seed=seed_i,
            )
            try:
                return _extract_json_array(r.text)
            except Exception:
                rejected["schema"] += 1
                return []

        seeds = [rng.randint(0, 2**31) for _ in range(n_calls)]
        with ThreadPoolExecutor(max_workers=n_calls) as ex:
            batches = list(ex.map(one, seeds))
        for new in batches:
            for c in new:
                if len(cards) - start_id >= n_total:
                    break
                if not _valid_schema(c):
                    rejected["schema"] += 1
                    continue
                if forbidden_hits(c):
                    rejected["forbidden"] += 1
                    continue
                if embedder is not None and cards:
                    sim = _max_similarity(embedder, c, cards)
                    if sim > sim_threshold:
                        rejected["similar"] += 1
                        continue
                c["author_id"] = f"A{len(cards) + 1:03d}"
                c["prompt_version"] = PROMPT_VERSION
                c["generator_model"] = llm.model
                cards.append(c)
    print(f"personas: {len(cards) - start_id} new, rejected {rejected}")
    return cards


def _valid_schema(c: dict) -> bool:
    try:
        ws = c["writing_style"]
        return (
            c["grammatical_gender"] in ("m", "f")
            and isinstance(c["interests"], list) and 1 <= len(c["interests"]) <= 4
            and all(k in ws for k in ("sentence_length", "punctuation", "capitalisation", "typos", "abbreviations", "emoji"))
            and isinstance(c["verbal_tic"], str) and isinstance(c["local_reference"], str)
            and 1 <= int(c["posts_per_week"]) <= 6
        )
    except Exception:
        return False


def _card_text(c: dict) -> str:
    return f"{c['schedule_occupation']} {' '.join(c['interests'])} {c.get('life_situation','')} {c['verbal_tic']}"


def _max_similarity(embedder, c: dict, cards: list[dict]) -> float:
    """embedder is kept for signature compatibility; any truthy value enables the check. Uses metrics.embed
    (OpenRouter by default)."""
    import numpy as np

    from .metrics import embed

    E = embed([_card_text(c)] + [_card_text(x) for x in cards])
    return float(np.max(E[1:] @ E[0]))


def _split(tmpl: str) -> tuple[str, str]:
    """Split a prompt file into SYSTEM and USER parts (markers on their own lines)."""
    body = re.sub(r"<!--.*?-->\s*", "", tmpl, flags=re.S)
    m = re.search(r"^SYSTEM\s*\n(.*?)^USER\s*\n(.*)$", body, flags=re.S | re.M)
    if not m:
        raise ValueError("prompt file must contain SYSTEM and USER sections")
    return m.group(1).strip(), m.group(2).strip()


def load_personas(path: Path) -> list[dict]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save_personas(cards: list[dict], path: Path) -> None:
    Path(path).write_text(json.dumps(cards, ensure_ascii=False, indent=1), encoding="utf-8")
