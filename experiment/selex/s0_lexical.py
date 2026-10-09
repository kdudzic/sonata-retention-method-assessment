"""S0: lexical selector (plan section 7, Annex G).

Categories (presence, not counts):
  A  first-person agency: 1st-person future/modal verb forms ("zrobię", "pójdę", "załatwię", "przysięgam, że"), incl.
     2nd-person "you'll see" forms the rulebook lists ("zobaczysz")
  B  concrete target: named person/institution/place/object/event. Implemented as (i) gazetteer of target nouns
     (szkoła, urząd, przystanek, lokal, sklep, poradnia, ...), (ii) possessive deixis + target noun ("ich biuro",
     "jego dom"), (iii) proper-noun heuristic: capitalised token not at sentence start and not in a stoplist
  C  temporal proximity: closed list ("dziś", "jutro", "wieczorem", "za godzinę", "po szkole", weekday names, "w sobotę")
  D  readiness / capability ("mam dostęp", "wiem gdzie", "spakowane", "jestem w drodze", "mam klucze", "mam kod")
  E  DISCARD signals, negative weight: reporting verbs, attribution, quotation marks, satire/lyrics/counterspeech markers

Score (Annex G):
  s = 3A + 2B + 2C + 1D + 2[A and B within 10 tokens] + 1[A, B, C in the same sentence] - 4E      (S0-sub)
  S0-veto: s = 0 whenever E is present.

The lexicon is an artifact (artifacts/s0_lexicon.yaml) expanded by an LLM FROM THE CATEGORY DEFINITIONS, never
from corpus texts, pruned by hand, then frozen with a checksum before the evaluation corpus is scored.
Matching is on lower-cased, diacritics-normalised tokens; lexicon entries may be single tokens, multi-token
phrases, or regex (prefix "re:").
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

import yaml

TOKEN_RE = re.compile(r"\w+|[„”\"«»']", re.U)
SENT_SPLIT_RE = re.compile(r"(?<=[.!?…])\s+|\n+")
CAP_STOP = {
    # sentence-internal capitalised tokens that are not targets (months, weekdays, common abbreviations, pronouns)
    "ja", "ty", "on", "ona", "my", "wy", "oni", "nfz", "tv", "pkp", "zus", "pit", "ok", "xd", "pln", "zł",
    "poniedziałek", "wtorek", "środa", "czwartek", "piątek", "sobota", "niedziela",
    "styczeń", "luty", "marzec", "kwiecień", "maj", "czerwiec", "lipiec", "sierpień", "wrzesień", "październik", "listopad", "grudzień",
    "polska", "polski", "polsce", "polak", "polacy", "allegro", "steam", "netflix", "glovo", "biedronka", "lidl", "żabka", "orlen", "ikea",
}


def strip_diacritics(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)).replace("ł", "l").replace("Ł", "L")


def norm(s: str) -> str:
    # lower-case, diacritics stripped, commas blanked (keeps offsets) so "mówił, że" == "mówił że"
    return strip_diacritics(s.lower()).replace(",", " ")


@dataclass
class Lexicon:
    A: list[str] = field(default_factory=list)
    B_nouns: list[str] = field(default_factory=list)
    B_possessive: list[str] = field(default_factory=list)
    C: list[str] = field(default_factory=list)
    D: list[str] = field(default_factory=list)
    E: list[str] = field(default_factory=list)
    version: str = ""

    @classmethod
    def load(cls, path: Path) -> "Lexicon":
        d = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        return cls(A=d.get("A", []), B_nouns=d.get("B_nouns", []), B_possessive=d.get("B_possessive", []),
                   C=d.get("C", []), D=d.get("D", []), E=d.get("E", []), version=str(d.get("version", "")))


class _Matcher:
    """Compiles lexicon entries into regexes over the normalised text; returns token-index spans."""

    def __init__(self, entries: list[str]) -> None:
        pats = []
        for e in entries:
            e = e.strip()
            if not e:
                continue
            if e.startswith("re:"):
                pats.append(e[3:])
            else:
                toks = [re.escape(norm(t).strip()) for t in e.replace(",", " ").split()]
                # allow inflection on the last token when entry ends with '*'
                if toks and toks[-1].endswith(r"\*"):
                    toks[-1] = toks[-1][:-2] + r"\w*"
                pats.append(r"\b" + r"\s+".join(toks) + r"\b")
        self.re = re.compile("|".join(f"(?:{p})" for p in pats), re.I) if pats else None

    def find(self, text_norm: str) -> list[tuple[int, int]]:
        if self.re is None:
            return []
        return [(m.start(), m.end()) for m in self.re.finditer(text_norm)]


class S0Selector:
    def __init__(self, lexicon: Lexicon, weights: dict, proximity_tokens: int = 10) -> None:
        self.lex = lexicon
        self.w = weights
        self.prox = proximity_tokens
        self.mA = _Matcher(lexicon.A)
        self.mBn = _Matcher(lexicon.B_nouns)
        self.mBp = _Matcher([f"{p} {n}" for p in lexicon.B_possessive for n in lexicon.B_nouns] if lexicon.B_possessive else [])
        self.mC = _Matcher(lexicon.C)
        self.mD = _Matcher(lexicon.D)
        self.mE = _Matcher(lexicon.E)

    # ---- feature extraction
    def features(self, text: str) -> dict:
        tn = norm(text)
        # char offset -> token index map
        tokens = [(m.start(), m.end(), m.group()) for m in TOKEN_RE.finditer(tn)]
        starts = [t[0] for t in tokens]

        def tok_idx(ch: int) -> int:
            import bisect
            return max(0, bisect.bisect_right(starts, ch) - 1)

        A = [tok_idx(s) for s, _ in self.mA.find(tn)]
        B = [tok_idx(s) for s, _ in self.mBn.find(tn)] + [tok_idx(s) for s, _ in self.mBp.find(tn)]
        B += self._proper_nouns(text)
        C = [tok_idx(s) for s, _ in self.mC.find(tn)]
        D = [tok_idx(s) for s, _ in self.mD.find(tn)]
        E = [tok_idx(s) for s, _ in self.mE.find(tn)]
        if re.search(r"[„”«»]|\"[^\"]{6,}\"", text):
            E.append(-1)  # quotation marks
        # sentence index per token
        sent_bounds = []
        pos = 0
        for s in SENT_SPLIT_RE.split(tn):
            sent_bounds.append((pos, pos + len(s)))
            pos += len(s) + 1
        def sent_of(ti: int) -> int:
            if ti < 0 or ti >= len(tokens):
                return -1
            ch = tokens[ti][0]
            for k, (a, b) in enumerate(sent_bounds):
                if a <= ch <= b:
                    return k
            return len(sent_bounds) - 1
        ab_prox = any(abs(a - b) <= self.prox for a in A for b in B if b >= 0)
        abc_sent = any(sent_of(a) == sent_of(b) == sent_of(c) >= 0 for a in A for b in B for c in C if b >= 0)
        return {"A": bool(A), "B": bool(B), "C": bool(C), "D": bool(D), "E": bool(E), "AB_prox": ab_prox, "ABC_sent": abc_sent,
                "nA": len(A), "nB": len(B), "nC": len(C), "nD": len(D), "nE": len(E)}

    def _proper_nouns(self, text: str) -> list[int]:
        """Capitalised tokens not at sentence start (proper-noun heuristic for category B). Returns token indices in the
        normalised token stream (approximate: same tokenisation on the original text)."""
        out = []
        toks = [(m.start(), m.group()) for m in TOKEN_RE.finditer(text)]
        sent_start = True
        for i, (ch, tok) in enumerate(toks):
            if tok in ("„", "”", '"', "«", "»", "'"):
                continue
            if not sent_start and tok[:1].isupper() and len(tok) > 2 and norm(tok) not in CAP_STOP and not tok.isupper():
                out.append(i)
            sent_start = bool(re.match(r"[.!?…]", text[ch + len(tok): ch + len(tok) + 2].strip()[:1] or "")) if i + 1 < len(toks) else False
            # crude: a token followed by sentence punctuation makes the next token a sentence start
            nxt = text[ch + len(tok): toks[i + 1][0]] if i + 1 < len(toks) else ""
            sent_start = bool(re.search(r"[.!?…\n]", nxt))
        return out

    # ---- score
    def score(self, text: str, variant: str = "sub") -> tuple[float, dict]:
        f = self.features(text)
        w = self.w
        s = w["A"] * f["A"] + w["B"] * f["B"] + w["C"] * f["C"] + w["D"] * f["D"] + w["AB_proximity"] * f["AB_prox"] + w["ABC_same_sentence"] * f["ABC_sent"]
        if variant == "veto":
            s = 0.0 if f["E"] else s
        else:
            s = s - w["E"] * f["E"]
        return float(s), f


def lexicon_sha256(path: Path) -> str:
    import hashlib
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
