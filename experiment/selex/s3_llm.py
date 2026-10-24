"""S3: LLM selectors (plan section 7, Annexes E and F).

Variants
  S3-open   open-weights model, prompts with the signal lists; leading score = P(KEEP) from the logprob of the
            decision token (plan Annex E note), `retention_score` recorded alongside
  S3'       same model, prompts without the signal lists ("blinded")
  S3-com    control model (commercial), ranked by `retention_score` (logprobs may be unavailable)

Access variants: D0 (post only), D3-nat (post + earlier posts of the author in the prompt).

Score semantics (raw_score, in [0, 1]):
  logprob available -> p_keep = P('K...') / (P('K...') + P('D...')) at the decision token
  else              -> retention_score / 100
Both are stored; `logprob_decision` is ln p_keep (NaN when unavailable).
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass

from . import config
from .llm import LLM, ChatResult


def _split(tmpl: str) -> tuple[str, str]:
    body = re.sub(r"<!--.*?-->\s*", "", tmpl, flags=re.S)
    m = re.search(r"^SYSTEM\s*\n(.*?)^USER\s*\n(.*)$", body, flags=re.S | re.M)
    if not m:
        raise ValueError("prompt must have SYSTEM and USER sections")
    return m.group(1).strip(), m.group(2).strip()


def build_messages(prompt_name: str, post_id: str, post: str, history: list[tuple[str, str]] | None = None) -> list[dict]:
    sys_part, user_part = _split(config.read_prompt(prompt_name))
    user = user_part.replace("{post_id}", post_id).replace("{post}", post)
    if "{history}" in user:
        hist = "\n".join(f"[{pid}] {txt}" for pid, txt in (history or [])) or "(no earlier posts)"
        user = user.replace("{history}", hist)
    return [{"role": "system", "content": sys_part}, {"role": "user", "content": user}]


def parse_json(text: str) -> dict:
    t = text.strip()
    t = re.sub(r"^```[a-zA-Z]*\n?", "", t)
    t = re.sub(r"\n?```$", "", t)
    i, j = t.find("{"), t.rfind("}")
    if i < 0 or j < 0:
        raise ValueError("no JSON object")
    return json.loads(t[i: j + 1])


def p_keep_from_logprobs(lp: list[dict] | None) -> float | None:
    """Find the decision token (first token after the `decision` key's opening quote) and compute
    P(K*) / (P(K*) + P(D*)) from its top alternatives. Returns None if not found."""
    if not lp:
        return None
    toks = [x["token"] or "" for x in lp]
    for i, tok in enumerate(toks):
        if "decision" in tok or (i > 0 and toks[i - 1].endswith('"') and "decision" in "".join(toks[max(0, i - 3): i])):
            # scan forward for the first token starting with K or D after the key
            for j in range(i + 1, min(i + 8, len(toks))):
                head = toks[j].strip().strip('"').strip()
                if head[:1].upper() in ("K", "D"):
                    alts = {}
                    for a in lp[j].get("top_logprobs") or []:
                        h = (a["token"] or "").strip().strip('"').strip()[:1].upper()
                        if h in ("K", "D"):
                            alts[h] = max(alts.get(h, -1e9), a["logprob"])
                    own = head[:1].upper()
                    alts[own] = max(alts.get(own, -1e9), lp[j]["logprob"])
                    pk = math.exp(alts.get("K", -1e9))
                    pd = math.exp(alts.get("D", -1e9))
                    if pk + pd <= 0:
                        return None
                    return pk / (pk + pd)
    return None


@dataclass
class S3Output:
    post_id: str
    decision: str
    retention_score: float | None
    p_keep: float | None
    raw_score: float
    decisive_posts: list[str]
    rationale: str
    call_id: str
    cost: float
    parse_ok: bool


class S3Selector:
    def __init__(self, model: str, prompt_name: str, run_name: str, temperature: float = 0.0, logprobs: bool = True,
                 workers: int = 8, seed: int | None = 0, provider_order: list[str] | None = None) -> None:
        self.model = model
        self.prompt_name = prompt_name
        self.llm = LLM(model, run_name=run_name, temperature=temperature, logprobs=logprobs, top_logprobs=8, seed=seed)
        if provider_order:
            # pin to providers that return token logprobs (and keep the backend fixed for the determinism check)
            self.llm.extra_body["provider"] = {"order": list(provider_order), "allow_fallbacks": False}
        self.workers = workers

    def score_one(self, post_id: str, text: str, history: list[tuple[str, str]] | None = None) -> S3Output:
        msgs = build_messages(self.prompt_name, post_id, text, history)
        # 4000, not 400: reasoning models (gemini, claude 5.5) bill thinking tokens against max_tokens and truncate the JSON otherwise
        r: ChatResult = self.llm.chat(msgs, tag=post_id, max_tokens=4000)
        try:
            o = parse_json(r.text)
            ok = True
        except Exception:
            o, ok = {}, False
        dec = str(o.get("decision", "")).upper()
        dec = "KEEP_FOR_REVIEW" if "KEEP" in dec else ("DISCARD" if "DISCARD" in dec else "PARSE_ERROR")
        rs = o.get("retention_score")
        try:
            rs = float(rs) if rs is not None else None
        except (TypeError, ValueError):
            rs = None
        pk = p_keep_from_logprobs(r.logprobs)
        if pk is None and r.logprobs is None and dec != "PARSE_ERROR":
            pass
        raw = pk if pk is not None else ((rs / 100.0) if rs is not None else (1.0 if dec == "KEEP_FOR_REVIEW" else 0.0))
        dp = o.get("decisive_posts") or []
        if not isinstance(dp, list):
            dp = [str(dp)]
        return S3Output(post_id, dec, rs, pk, float(raw), [str(x) for x in dp], str(o.get("short_rationale", ""))[:500],
                        r.call_id, r.cost, ok)

    def score_many(self, items: list[tuple[str, str, list[tuple[str, str]] | None]], desc: str = "") -> list[S3Output | Exception]:
        return self.llm.map(items, lambda it: self.score_one(*it), workers=self.workers, desc=desc)
