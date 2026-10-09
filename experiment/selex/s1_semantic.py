"""S1: zero-shot semantic selector (plan Annex H).

  v       = embed(post) - mean_embedding(corpus)          (centering against anisotropy)
  s(post) = max_i cos(v, SEED+_i) - max_j cos(v, SEED-_j)

Seeds are written FROM THE DECISION RULES, not from example posts (artifacts/s1_seeds.yaml), and frozen.
Access variants:
  D0      post text only
  D3-txt  earlier posts of the author concatenated with the post in one encoder window (main D3 variant)
  D3-vec  normalised mix of the post vector and the mean history vector (sub-analysis, alpha in config)
  D3-agg  handled generically by access.aggregate on D0 scores
Control: shuffled seeds (random re-assignment of +/- labels and shuffling within sets) - plan Annex H.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import yaml

from .llm import embed


@dataclass
class Seeds:
    plus: list[str]
    minus: list[str]
    version: str

    @classmethod
    def load(cls, path: Path) -> "Seeds":
        d = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        return cls(plus=list(d["SEED_PLUS"]), minus=list(d["SEED_MINUS"]), version=str(d.get("version", "")))

    def shuffled(self, seed: int) -> "Seeds":
        rng = random.Random(seed)
        pool = self.plus + self.minus
        rng.shuffle(pool)
        return Seeds(plus=pool[: len(self.plus)], minus=pool[len(self.plus):], version=f"{self.version}-shuffled{seed}")


QUERY_INSTRUCTION = ("Instruct: Given a short Polish social media post, retrieve the description of the kind of content it is.\n"
                     "Query: ")


class S1Selector:
    """Posts are embedded as instruction-prefixed queries (the embedding model's intended retrieval usage); seed
    descriptions are embedded as plain documents. Without the prefix the register mismatch (descriptive seeds vs
    first-person posts) dominated the similarity on the dev corpus (explicit-threat post ranked 181/622; with the
    prefix 11/622)."""

    def __init__(self, seeds: Seeds, model: str, ledger: Path | None = None, query_instruction: str = QUERY_INSTRUCTION) -> None:
        self.seeds = seeds
        self.model = model
        self.ledger = ledger
        self.qi = query_instruction
        self.Ep = embed(seeds.plus, model=model, ledger=ledger)
        self.Em = embed(seeds.minus, model=model, ledger=ledger)
        self.mean: np.ndarray | None = None

    def fit_center(self, E_corpus: np.ndarray) -> None:
        self.mean = E_corpus.mean(axis=0)

    def _center(self, E: np.ndarray) -> np.ndarray:
        if self.mean is None:
            raise RuntimeError("call fit_center first")
        V = E - self.mean
        return V / np.maximum(np.linalg.norm(V, axis=1, keepdims=True), 1e-9)

    def score_vectors(self, E: np.ndarray) -> np.ndarray:
        V = self._center(E)
        # seeds are centred the same way so that both sides live in the same space
        Sp = self._center(self.Ep)
        Sm = self._center(self.Em)
        return (V @ Sp.T).max(axis=1) - (V @ Sm.T).max(axis=1)

    def embed_texts(self, texts: list[str]) -> np.ndarray:
        return embed([self.qi + t for t in texts], model=self.model, ledger=self.ledger)

    @staticmethod
    def d3_txt_inputs(post_text: str, history_texts: list[str]) -> str:
        """One encoder window: earlier posts (oldest first) + the post under review, separated by newlines."""
        return "\n".join(history_texts + [post_text])

    @staticmethod
    def d3_vec(E_post: np.ndarray, E_hist_mean: np.ndarray | None, alpha: float) -> np.ndarray:
        if E_hist_mean is None:
            return E_post
        v = alpha * E_post + (1 - alpha) * E_hist_mean
        return v / max(float(np.linalg.norm(v)), 1e-9)
