"""OpenRouter chat client with retries, cost accounting and raw-response logging.

Every generator in the pipeline goes through `LLM.chat`. Each call is logged as
one JSON file under raw/<run>/ with the full prompt, parameters and response,
so that any post in the corpus can be traced back to the exact call that made it
(documentation standard, plan section 17).

Cost: OpenRouter returns `usage.cost` (USD) when `usage.include` is requested.
We accumulate it per LLM instance and persist a ledger line per call.
"""

from __future__ import annotations

import hashlib
import json
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable

import httpx
from openai import OpenAI, APIError, RateLimitError, APITimeoutError, APIConnectionError

from . import config


@dataclass
class Response:
    text: str
    model: str
    cost: float
    prompt_tokens: int
    completion_tokens: int
    finish_reason: str | None
    call_id: str
    latency_s: float
    raw: dict[str, Any] = field(default_factory=dict)
    refused: bool = False


REFUSAL_MARKERS = (
    "i can't", "i cannot", "i can’t", "i'm sorry", "i am sorry", "i won't", "i won’t", "i'm not able", "i am not able",
    "i'm unable", "as an ai", "i will not", "i do not feel comfortable", "i'm not comfortable",
    "nie napiszę", "nie mogę tego napisać", "nie mogę napisać", "nie będę", "nie jestem w stanie", "jako model",
    "nie mogę pomóc", "nie mogę stworzyć", "nie mogę wygenerować", "przykro mi, ale", "niestety nie mogę",
)


def looks_like_refusal(text: str) -> bool:
    """Refusal heuristic: an English/Polish refusal marker in the first 60 characters, or a long English
    explanation where Polish was requested. Verified manually on stage A outputs."""
    head = text.strip()[:60].lower()
    if any(m in head for m in REFUSAL_MARKERS):
        return True
    t = text.strip()
    # Polish posts almost always contain diacritics; a 200+ char answer without any and with English
    # function words is an explanation, not a post.
    if len(t) > 200 and not any(ch in t.lower() for ch in "ąćęłńóśźż") and (" the " in t or " this " in t):
        return True
    return False


class LLM:
    """Single-model chat client. One instance per (model, run)."""

    def __init__(
        self,
        model: str,
        run_name: str,
        temperature: float | None = None,
        top_p: float | None = None,
        min_p: float | None = None,
        max_tokens: int | None = None,
        seed: int | None = None,
        extra_body: dict[str, Any] | None = None,
        max_retries: int = 5,
        timeout: float = 120.0,
        log_raw: bool = True,
        reasoning: bool = False,
    ) -> None:
        self.model = model
        self.run_name = run_name
        self.temperature = temperature
        self.top_p = top_p
        self.min_p = min_p
        self.max_tokens = max_tokens
        self.seed = seed
        self.extra_body = dict(extra_body or {})
        # Reasoning/thinking is off by default: posts are short, thinking tokens are billed as
        # completion tokens, and for hybrid models they would silently eat the max_tokens budget.
        if not reasoning and "reasoning" not in self.extra_body:
            self.extra_body["reasoning"] = {"enabled": False}
        self.max_retries = max_retries
        self.log_raw = log_raw
        self.client = OpenAI(
            base_url=config.OPENROUTER_BASE_URL,
            api_key=config.read_api_key(),
            timeout=timeout,
            max_retries=0,
            default_headers={
                "HTTP-Referer": "https://github.com/ked/sonata-epskel",
                "X-Title": "EP-SKEL corpus generation",
            },
        )
        self.total_cost = 0.0
        self.n_calls = 0
        self.n_prompt_tokens = 0
        self.n_completion_tokens = 0
        self._lock = threading.Lock()
        self.raw_dir = config.RAW / run_name
        if log_raw:
            self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.ledger = config.RAW / "ledger.jsonl"
        self.ledger.parent.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ core
    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        tag: str = "",
        temperature: float | None = None,
        max_tokens: int | None = None,
        response_format: dict | None = None,
        seed: int | None = None,
    ) -> Response:
        body: dict[str, Any] = {"usage": {"include": True}}
        body.update(self.extra_body)
        if self.min_p is not None:
            body["min_p"] = self.min_p
        kwargs: dict[str, Any] = dict(model=self.model, messages=messages, extra_body=body)
        t = self.temperature if temperature is None else temperature
        if t is not None:
            kwargs["temperature"] = t
        if self.top_p is not None:
            kwargs["top_p"] = self.top_p
        mt = self.max_tokens if max_tokens is None else max_tokens
        if mt is not None:
            kwargs["max_tokens"] = mt
        s = self.seed if seed is None else seed
        if s is not None:
            kwargs["seed"] = s
        if response_format is not None:
            kwargs["response_format"] = response_format

        call_id = uuid.uuid4().hex[:12]
        delay = 2.0
        last_err: Exception | None = None
        for attempt in range(self.max_retries):
            t0 = time.time()
            try:
                resp = self.client.chat.completions.create(**kwargs)
                lat = time.time() - t0
                raw = resp.model_dump()
                choice = raw["choices"][0]
                text = (choice.get("message") or {}).get("content") or ""
                usage = raw.get("usage") or {}
                cost = float(usage.get("cost") or 0.0)
                rt = ((usage.get("completion_tokens_details") or {}).get("reasoning_tokens")) or 0
                r = Response(
                    text=text,
                    model=raw.get("model", self.model),
                    cost=cost,
                    prompt_tokens=int(usage.get("prompt_tokens") or 0),
                    completion_tokens=int(usage.get("completion_tokens") or 0),
                    finish_reason=choice.get("finish_reason"),
                    call_id=call_id,
                    latency_s=lat,
                    raw=raw,
                    refused=looks_like_refusal(text),
                )
                r.raw["_reasoning_tokens"] = rt
                self._account(r, kwargs, tag)
                return r
            except (RateLimitError, APITimeoutError, APIConnectionError, httpx.HTTPError) as e:
                last_err = e
            except APIError as e:
                last_err = e
                status = getattr(e, "status_code", None)
                msg = str(e)
                # Some endpoints refuse reasoning=disabled; step down the effort ladder instead.
                if status == 400 and "easoning" in msg:
                    used = kwargs["extra_body"].get("reasoning")
                    with self._lock:
                        current = self.extra_body.get("reasoning")
                    # another thread already moved the shared setting: adopt it; otherwise step the ladder
                    if used == current and not self._step_reasoning_fallback():
                        break
                    body = dict(kwargs["extra_body"]); body["reasoning"] = self.extra_body["reasoning"]
                    kwargs["extra_body"] = body
                    continue
                # 4xx other than 429: don't hammer
                if status and 400 <= status < 500 and status != 429:
                    break
            time.sleep(delay)
            delay = min(delay * 2, 30)
        raise RuntimeError(f"LLM call failed after {self.max_retries} attempts ({self.model}): {last_err}")

    _REASONING_LADDER = [{"enabled": False}, {"effort": "minimal"}, {"effort": "low"}, {"exclude": True}]

    def _step_reasoning_fallback(self) -> bool:
        cur = self.extra_body.get("reasoning")
        try:
            i = self._REASONING_LADDER.index(cur)
        except ValueError:
            return False
        if i + 1 >= len(self._REASONING_LADDER):
            return False
        with self._lock:
            self.extra_body["reasoning"] = self._REASONING_LADDER[i + 1]
        return True

    def _account(self, r: Response, kwargs: dict, tag: str) -> None:
        with self._lock:
            self.total_cost += r.cost
            self.n_calls += 1
            self.n_prompt_tokens += r.prompt_tokens
            self.n_completion_tokens += r.completion_tokens
        rec = {
            "ts": time.time(),
            "run": self.run_name,
            "tag": tag,
            "call_id": r.call_id,
            "model": self.model,
            "model_served": r.model,
            "cost": r.cost,
            "prompt_tokens": r.prompt_tokens,
            "completion_tokens": r.completion_tokens,
            "latency_s": round(r.latency_s, 2),
            "finish_reason": r.finish_reason,
            "refused": r.refused,
            "reasoning_tokens": r.raw.get("_reasoning_tokens", 0),
        }
        with self._lock:
            with self.ledger.open("a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        if self.log_raw:
            params = {k: v for k, v in kwargs.items() if k != "messages"}
            payload = {
                "call_id": r.call_id,
                "tag": tag,
                "params": params,
                "messages": kwargs["messages"],
                "prompt_sha1": hashlib.sha1(
                    json.dumps(kwargs["messages"], ensure_ascii=False).encode()
                ).hexdigest(),
                "response": r.raw,
            }
            (self.raw_dir / f"{r.call_id}.json").write_text(
                json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8"
            )

    # -------------------------------------------------------------- parallel
    def map(
        self,
        jobs: Iterable[Any],
        fn: Callable[[Any], Any],
        workers: int = 8,
        desc: str = "",
    ) -> list[Any]:
        """Run fn(job) in a thread pool, preserving job order. fn should call self.chat."""
        jobs = list(jobs)
        out: list[Any] = [None] * len(jobs)
        from tqdm import tqdm

        with ThreadPoolExecutor(max_workers=workers) as ex:
            futs = {ex.submit(fn, j): i for i, j in enumerate(jobs)}
            for fut in tqdm(as_completed(futs), total=len(jobs), desc=desc or self.model, leave=False):
                i = futs[fut]
                try:
                    out[i] = fut.result()
                except Exception as e:  # keep going; caller inspects None
                    out[i] = e
        return out

    def summary(self) -> str:
        return (
            f"{self.model}: {self.n_calls} calls, "
            f"{self.n_prompt_tokens} in / {self.n_completion_tokens} out tokens, "
            f"${self.total_cost:.4f}"
        )


def ledger_total(run_prefix: str | None = None) -> float:
    """Sum of cost in the ledger, optionally filtered by run name prefix."""
    p = config.RAW / "ledger.jsonl"
    if not p.exists():
        return 0.0
    total = 0.0
    for line in p.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        if run_prefix is None or rec["run"].startswith(run_prefix):
            total += rec.get("cost", 0.0)
    return total
