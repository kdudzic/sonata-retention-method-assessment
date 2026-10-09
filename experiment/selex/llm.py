"""OpenRouter client for the selection experiment: chat with optional token logprobs, and embeddings.

Independent of the corpus-generation package on purpose (the experiment must not import generator code).
Every chat call is logged as JSON under results/raw/<run>/ with the full prompt, parameters and response,
and appended to results/raw/ledger.jsonl with its cost.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable

import httpx
import numpy as np
from openai import OpenAI, APIError, RateLimitError, APITimeoutError, APIConnectionError

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
ROOT = Path(__file__).resolve().parent.parent
KEY_FILE = ROOT.parent / "sonata_openrouter.txt"
KEY_FILE_HOME = Path.home() / "sync" / "tokens" / "sonata_openrouter.txt"   # user keeps keys here since 2026-10-09


def read_api_key() -> str:
    key = os.environ.get("OPENROUTER_API_KEY")
    if key:
        return key.strip()
    for kf in (KEY_FILE, KEY_FILE_HOME):
        if kf.exists():
            m = re.search(r"sk-or-[A-Za-z0-9_\-]+", kf.read_text())
            if m:
                return m.group(0)
    raise RuntimeError("No OpenRouter key: set OPENROUTER_API_KEY or put sonata_openrouter.txt in ~/sync/tokens/")


@dataclass
class ChatResult:
    text: str
    model: str
    cost: float
    prompt_tokens: int
    completion_tokens: int
    finish_reason: str | None
    call_id: str
    latency_s: float
    logprobs: list[dict] | None = None   # per generated token: {token, logprob, top_logprobs:[{token,logprob}]}
    raw: dict[str, Any] = field(default_factory=dict)


class LLM:
    _REASONING_LADDER = [{"enabled": False}, {"effort": "minimal"}, {"effort": "low"}, {"exclude": True}]

    def __init__(self, model: str, run_name: str, temperature: float | None = 0.0, max_tokens: int = 4000,
                 seed: int | None = None, logprobs: bool = False, top_logprobs: int = 8, max_retries: int = 5,
                 timeout: float = 120.0, raw_root: Path | None = None, reasoning: bool = False) -> None:
        self.model = model
        self.run_name = run_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.seed = seed
        self.want_logprobs = logprobs
        self.top_logprobs = top_logprobs
        self.max_retries = max_retries
        self.extra_body: dict[str, Any] = {"usage": {"include": True}}
        if not reasoning:
            self.extra_body["reasoning"] = {"enabled": False}
        self.client = OpenAI(base_url=OPENROUTER_BASE_URL, api_key=read_api_key(), timeout=timeout, max_retries=0,
                             default_headers={"X-Title": "EP-SKEL selection experiment"})
        self.total_cost = 0.0
        self.n_calls = 0
        self._lock = threading.Lock()
        self.raw_root = raw_root or (ROOT / "results" / "raw")
        self.raw_dir = self.raw_root / run_name
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.ledger = self.raw_root / "ledger.jsonl"

    def chat(self, messages: list[dict[str, str]], *, tag: str = "", temperature: float | None = None,
             max_tokens: int | None = None, seed: int | None = None, response_format: dict | None = None) -> ChatResult:
        kwargs: dict[str, Any] = dict(model=self.model, messages=messages, extra_body=dict(self.extra_body))
        t = self.temperature if temperature is None else temperature
        if t is not None:
            kwargs["temperature"] = t
        kwargs["max_tokens"] = self.max_tokens if max_tokens is None else max_tokens
        s = self.seed if seed is None else seed
        if s is not None:
            kwargs["seed"] = s
        if self.want_logprobs:
            kwargs["logprobs"] = True
            kwargs["top_logprobs"] = self.top_logprobs
        if response_format is not None:
            kwargs["response_format"] = response_format
        call_id = uuid.uuid4().hex[:12]
        delay = 2.0
        last_err: Exception | None = None
        for attempt in range(self.max_retries):
            t0 = time.time()
            try:
                resp = self.client.chat.completions.create(**kwargs)
                raw = resp.model_dump()
                choice = raw["choices"][0]
                text = (choice.get("message") or {}).get("content") or ""
                usage = raw.get("usage") or {}
                lp = None
                if choice.get("logprobs") and choice["logprobs"].get("content"):
                    lp = [{"token": x.get("token"), "logprob": x.get("logprob"),
                           "top_logprobs": [{"token": y.get("token"), "logprob": y.get("logprob")} for y in (x.get("top_logprobs") or [])]}
                          for x in choice["logprobs"]["content"]]
                r = ChatResult(text=text, model=raw.get("model", self.model), cost=float(usage.get("cost") or 0.0),
                               prompt_tokens=int(usage.get("prompt_tokens") or 0), completion_tokens=int(usage.get("completion_tokens") or 0),
                               finish_reason=choice.get("finish_reason"), call_id=call_id, latency_s=time.time() - t0, logprobs=lp, raw=raw)
                self._account(r, kwargs, tag)
                return r
            except (RateLimitError, APITimeoutError, APIConnectionError, httpx.HTTPError) as e:
                last_err = e
            except APIError as e:
                last_err = e
                status = getattr(e, "status_code", None)
                msg = str(e)
                if status == 400 and "easoning" in msg:
                    used = kwargs["extra_body"].get("reasoning")
                    with self._lock:
                        current = self.extra_body.get("reasoning")
                    if used == current and not self._step_reasoning():
                        break
                    kwargs["extra_body"] = dict(kwargs["extra_body"], reasoning=self.extra_body["reasoning"])
                    continue
                if status == 400 and "logprobs" in msg.lower():
                    # provider does not support logprobs: drop them for this instance
                    self.want_logprobs = False
                    kwargs.pop("logprobs", None); kwargs.pop("top_logprobs", None)
                    continue
                if status and 400 <= status < 500 and status != 429:
                    break
            time.sleep(delay)
            delay = min(delay * 2, 30)
        raise RuntimeError(f"LLM call failed after {self.max_retries} attempts ({self.model}): {last_err}")

    def _step_reasoning(self) -> bool:
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

    def _account(self, r: ChatResult, kwargs: dict, tag: str) -> None:
        with self._lock:
            self.total_cost += r.cost
            self.n_calls += 1
            with self.ledger.open("a", encoding="utf-8") as f:
                f.write(json.dumps({"ts": time.time(), "run": self.run_name, "tag": tag, "call_id": r.call_id, "model": self.model,
                                    "cost": r.cost, "prompt_tokens": r.prompt_tokens, "completion_tokens": r.completion_tokens,
                                    "latency_s": round(r.latency_s, 2), "finish_reason": r.finish_reason}, ensure_ascii=False) + "\n")
        params = {k: v for k, v in kwargs.items() if k != "messages"}
        (self.raw_dir / f"{r.call_id}.json").write_text(json.dumps({
            "call_id": r.call_id, "tag": tag, "params": params, "messages": kwargs["messages"],
            "prompt_sha1": hashlib.sha1(json.dumps(kwargs["messages"], ensure_ascii=False).encode()).hexdigest(),
            "response": r.raw}, ensure_ascii=False, indent=1), encoding="utf-8")

    def map(self, jobs: Iterable[Any], fn: Callable[[Any], Any], workers: int = 8, desc: str = "") -> list[Any]:
        from tqdm import tqdm

        jobs = list(jobs)
        out: list[Any] = [None] * len(jobs)
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futs = {ex.submit(fn, j): i for i, j in enumerate(jobs)}
            for fut in tqdm(as_completed(futs), total=len(jobs), desc=desc or self.model, leave=False):
                i = futs[fut]
                try:
                    out[i] = fut.result()
                except Exception as e:
                    out[i] = e
        return out

    def summary(self) -> str:
        return f"{self.model}: {self.n_calls} calls, ${self.total_cost:.4f}"


# ----------------------------------------------------------------------------- embeddings
def embed(texts: list[str], model: str = "qwen/qwen3-embedding-8b", batch_size: int = 32, workers: int = 4,
          ledger: Path | None = None) -> np.ndarray:
    """L2-normalised embeddings via the OpenRouter embeddings endpoint."""
    url = f"{OPENROUTER_BASE_URL}/embeddings"
    headers = {"Authorization": f"Bearer {read_api_key()}", "Content-Type": "application/json"}
    batches = [texts[i: i + batch_size] for i in range(0, len(texts), batch_size)]
    cost_total = [0.0]
    lock = threading.Lock()

    def one(batch: list[str]) -> list[list[float]]:
        payload = {"model": model, "input": [t if t.strip() else "." for t in batch]}
        delay = 2.0
        for attempt in range(6):
            try:
                r = httpx.post(url, headers=headers, json=payload, timeout=180)
                if r.status_code == 200:
                    j = r.json()
                    with lock:
                        cost_total[0] += float((j.get("usage") or {}).get("cost") or 0.0)
                    data = sorted(j["data"], key=lambda d: d.get("index", 0))
                    return [d["embedding"] for d in data]
                if r.status_code in (429, 500, 502, 503, 504):
                    raise RuntimeError(f"{r.status_code}: {r.text[:200]}")
                raise RuntimeError(f"embeddings failed {r.status_code}: {r.text[:300]}")
            except (httpx.HTTPError, RuntimeError):
                if attempt == 5:
                    raise
                time.sleep(delay)
                delay = min(delay * 2, 30)
        raise RuntimeError("unreachable")

    with ThreadPoolExecutor(max_workers=workers) as ex:
        results = list(ex.map(one, batches))
    E = np.array([v for b in results for v in b], dtype=np.float32)
    E /= np.maximum(np.linalg.norm(E, axis=1, keepdims=True), 1e-9)
    if ledger is not None:
        with ledger.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": time.time(), "run": "embeddings", "model": model, "n_texts": len(texts), "cost": cost_total[0]}) + "\n")
    return E
