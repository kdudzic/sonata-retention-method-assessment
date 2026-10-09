"""Diversity, duplication and surface-naturalness metrics for a set of posts.

All metrics are computed per set (e.g. per layer, per model, per method) and are
meant to be reported as a GAP against a length-matched real Polish reference
(TwitterEmo-PL), not as raw values.

Families
- lexical:   distinct-1/2/3, MATTR, gzip compression ratio, 4-gram self-repetition, self-BLEU-4
- semantic:  mean pairwise cosine, share of pairs > 0.8, Vendi score, near-duplicate rate
- surface:   length stats, lowercase-start rate, terminal punctuation, emoji/hashtag/@, em-dash,
             ellipsis, exclamation/question rates, all-caps words, expletives, Polish AI-ism lexicon
- detector:  char n-gram logistic regression AUC (synthetic vs reference), cross-validated
"""

from __future__ import annotations

import math
import re
import zlib
from collections import Counter
from dataclasses import dataclass
from typing import Iterable

import numpy as np

EMOJI_RE = re.compile(
    "[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF⭐⬆⤴⤵〰〽㊗㊙️]"
)
WORD_RE = re.compile(r"\w+", re.U)
EXPLETIVES = [
    "kurwa", "kurwy", "kurwie", "chuj", "chuja", "pierdol", "pierdal", "jebać", "jebie", "zajeb", "wkurw",
    "spierdal", "pizd", "gówno", "gowno", "cholera", "szlag", "dupa", "dupy", "cholerny", "kurde", "kurcze",
]
# Candidate Polish "AI-isms": stock LLM openers/closers and tidy connectives. Empirical list; the
# over-representation test (vs reference) is what matters, not the list itself.
AI_ISMS = [
    "no i", "ech", "ehh", "serio", "klasyk", "klasycznie", "typowe", "typowo", "no cóż", "cóż", "w każdym razie",
    "ale hej", "czy tylko ja", "ciekawe czy", "mały sukces", "małe rzeczy", "to jest to", "i tak oto",
    "najlepsze jest to", "szczerze mówiąc", "generalnie", "ogólnie", "podsumowując", "warto", "zdecydowanie",
    "absolutnie", "dosłownie", "poziom", "level", "moment", "chwila prawdy", "plot twist", "update", "edit",
    "pozdrawiam", "dzień dobry", "miłego", "życzę", "jak zwykle", "jak to bywa", "no nic", "no dobra", "ok czyli",
    "ta energia", "vibe", "mood", "nie ma to jak", "uwielbiam", "kocham to", "trzymajcie kciuki", "ktoś jeszcze",
    "kto jeszcze", "powiedzcie mi", "pytanie do", "czy to normalne", "mam wrażenie", "przyznaję", "nie ukrywam",
]


# ----------------------------------------------------------------------------- tokenisation
def words(t: str) -> list[str]:
    return [w.lower() for w in WORD_RE.findall(t)]


def ngrams(toks: list[str], n: int) -> Iterable[tuple[str, ...]]:
    return (tuple(toks[i : i + n]) for i in range(len(toks) - n + 1))


# ----------------------------------------------------------------------------- lexical
def distinct_n(texts: list[str], n: int) -> float:
    total, uniq = 0, set()
    for t in texts:
        toks = words(t)
        g = list(ngrams(toks, n))
        total += len(g)
        uniq.update(g)
    return len(uniq) / total if total else 0.0


def mattr(texts: list[str], window: int = 50) -> float:
    toks = [w for t in texts for w in words(t)]
    if len(toks) < window:
        return len(set(toks)) / max(1, len(toks))
    vals = [len(set(toks[i : i + window])) / window for i in range(0, len(toks) - window + 1, 10)]
    return float(np.mean(vals))


def compression_ratio(texts: list[str]) -> float:
    """Shaib et al. 2024: bytes(raw)/bytes(gzip). Higher = more redundant (less diverse)."""
    raw = "\n".join(texts).encode("utf-8")
    if not raw:
        return 0.0
    return len(raw) / len(zlib.compress(raw, 9))


def self_repetition(texts: list[str], n: int = 4) -> float:
    """Share of posts containing at least one n-gram that also appears in another post."""
    grams = [set(ngrams(words(t), n)) for t in texts]
    cnt: Counter = Counter(g for s in grams for g in s)
    rep = sum(1 for s in grams if any(cnt[g] > 1 for g in s))
    return rep / len(texts) if texts else 0.0


def self_bleu(texts: list[str], max_n: int = 4, sample: int = 300, seed: int = 0) -> float:
    """Average sentence-BLEU of each (sampled) post against all others as references. Smoothed."""
    rng = np.random.default_rng(seed)
    toks = [words(t) for t in texts]
    idx = rng.choice(len(toks), size=min(sample, len(toks)), replace=False) if len(toks) > sample else range(len(toks))
    scores = []
    # reference n-gram max counts, pooled (standard self-BLEU uses all others as refs)
    ref_counts = [Counter(ngrams(t, n)) for n in range(1, max_n + 1) for t in [sum(toks, [])]]  # placeholder
    # pooled counting is too lax; use per-reference max-count clip
    per_ref = [[Counter(ngrams(t, n)) for n in range(1, max_n + 1)] for t in toks]
    for i in idx:
        hyp = toks[i]
        if len(hyp) < max_n:
            continue
        logp = 0.0
        for n in range(1, max_n + 1):
            hc = Counter(ngrams(hyp, n))
            clipped = 0
            for g, c in hc.items():
                m = max((per_ref[j][n - 1].get(g, 0) for j in range(len(toks)) if j != i), default=0)
                clipped += min(c, m)
            total = max(1, sum(hc.values()))
            p = (clipped + 1) / (total + 1)  # add-one smoothing
            logp += math.log(p) / max_n
        scores.append(math.exp(logp))
    return float(np.mean(scores)) if scores else 0.0


# ----------------------------------------------------------------------------- semantic
_EMBEDDER = None


def get_embedder(name: str = "BAAI/bge-m3"):
    global _EMBEDDER
    if _EMBEDDER is None:
        import os
        import torch
        from sentence_transformers import SentenceTransformer

        # Keep the CPU usable for the person running this: cap torch at a few threads.
        n = int(os.environ.get("EPSKEL_THREADS", "4"))
        torch.set_num_threads(n)
        _EMBEDDER = SentenceTransformer(name, device="cpu")
    return _EMBEDDER


def embed(texts: list[str], batch_size: int = 64, model: str = "baai/bge-m3") -> np.ndarray:
    """Embeddings via OpenRouter (default; ~$0.01/M tokens, no local CPU load) or the local model.

    Set EPSKEL_EMBED=local to force the local sentence-transformers model (same bge-m3 weights).
    """
    import os

    if os.environ.get("EPSKEL_EMBED", "openrouter") == "local":
        return get_embedder().encode(texts, batch_size=batch_size, normalize_embeddings=True, show_progress_bar=False)
    return embed_openrouter(texts, batch_size=batch_size, model=model)


def embed_openrouter(texts: list[str], batch_size: int = 64, model: str = "baai/bge-m3", workers: int = 4) -> np.ndarray:
    import time
    from concurrent.futures import ThreadPoolExecutor

    import httpx

    from . import config

    url = f"{config.OPENROUTER_BASE_URL}/embeddings"
    headers = {"Authorization": f"Bearer {config.read_api_key()}", "Content-Type": "application/json"}
    batches = [texts[i : i + batch_size] for i in range(0, len(texts), batch_size)]

    def one(batch: list[str]) -> list[list[float]]:
        # empty strings are rejected by some providers; embed a placeholder and zero it afterwards
        payload = {"model": model, "input": [t if t.strip() else "." for t in batch]}
        delay = 2.0
        for attempt in range(6):
            try:
                r = httpx.post(url, headers=headers, json=payload, timeout=120)
                if r.status_code == 200:
                    data = sorted(r.json()["data"], key=lambda d: d.get("index", 0))
                    return [d["embedding"] for d in data]
                if r.status_code in (429, 500, 502, 503, 504):
                    raise RuntimeError(f"{r.status_code}: {r.text[:200]}")
                raise RuntimeError(f"embeddings failed {r.status_code}: {r.text[:300]}")
            except (httpx.HTTPError, RuntimeError) as e:
                if attempt == 5:
                    raise
                time.sleep(delay)
                delay = min(delay * 2, 30)
        raise RuntimeError("unreachable")

    with ThreadPoolExecutor(max_workers=workers) as ex:
        results = list(ex.map(one, batches))
    E = np.array([v for b in results for v in b], dtype=np.float32)
    E /= np.maximum(np.linalg.norm(E, axis=1, keepdims=True), 1e-9)
    for i, t in enumerate(texts):
        if not t.strip():
            E[i] = 0.0
    return E


def semantic_metrics(E: np.ndarray, dup_threshold: float = 0.90) -> dict:
    n = E.shape[0]
    if n < 2:
        return {"mean_cos": 0.0, "pairs_gt_0.8": 0.0, "vendi": 1.0, "near_dup_rate": 0.0}
    S = E @ E.T
    iu = np.triu_indices(n, 1)
    sims = S[iu]
    np.fill_diagonal(S, -1)
    max_other = S.max(axis=1)
    # Vendi score on the cosine kernel (Friedman & Dieng 2022): exp(entropy of eigenvalues of K/n)
    K = (E @ E.T) / n
    ev = np.linalg.eigvalsh(K)
    ev = ev[ev > 1e-12]
    vendi = float(np.exp(-np.sum(ev * np.log(ev))))
    return {
        "mean_cos": float(sims.mean()),
        "pairs_gt_0.8": float((sims > 0.8).mean()),
        "vendi": vendi,
        "vendi_norm": vendi / n,
        "near_dup_rate": float((max_other > dup_threshold).mean()),
    }


# ----------------------------------------------------------------------------- surface
def surface_metrics(texts: list[str]) -> dict:
    n = len(texts)
    if n == 0:
        return {}
    lens = np.array([len(words(t)) for t in texts])
    chars = np.array([len(t) for t in texts])
    first_lower = np.mean([t.strip()[:1].islower() for t in texts if t.strip()])
    ends_no_punct = np.mean([not re.search(r"[.!?…]\s*$", t.strip()) for t in texts])
    has_emoji = np.mean([bool(EMOJI_RE.search(t)) for t in texts])
    has_hashtag = np.mean([bool(re.search(r"(^|\s)#\w", t)) for t in texts])
    has_mention = np.mean([bool(re.search(r"(^|\s)@\w", t)) for t in texts])
    em_dash = np.mean([("—" in t) or (" – " in t) for t in texts])
    ellipsis = np.mean([("..." in t) or ("…" in t) for t in texts])
    excl = np.mean(["!" in t for t in texts])
    quest = np.mean(["?" in t for t in texts])
    allcaps = np.mean([bool(re.search(r"\b[A-ZĄĆĘŁŃÓŚŹŻ]{3,}\b", t)) for t in texts])
    expl = np.mean([any(e in t.lower() for e in EXPLETIVES) for t in texts])
    no_diacritics = np.mean([not re.search(r"[ąćęłńóśźż]", t.lower()) for t in texts])
    sentences = np.array([max(1, len(re.findall(r"[.!?…]+", t))) for t in texts])
    ai_hits = Counter()
    for t in texts:
        tl = " " + re.sub(r"\s+", " ", t.lower()) + " "
        for p in AI_ISMS:
            if f" {p} " in tl or tl.startswith(f" {p},") or tl.startswith(f" {p} "):
                ai_hits[p] += 1
    return {
        "n": n,
        "len_mean": float(lens.mean()), "len_std": float(lens.std()), "len_median": float(np.median(lens)),
        "len_p10": float(np.percentile(lens, 10)), "len_p90": float(np.percentile(lens, 90)),
        "chars_mean": float(chars.mean()),
        "first_lower": float(first_lower), "ends_no_punct": float(ends_no_punct),
        "emoji": float(has_emoji), "hashtag": float(has_hashtag), "mention": float(has_mention),
        "em_dash": float(em_dash), "ellipsis": float(ellipsis), "excl": float(excl), "quest": float(quest),
        "allcaps_word": float(allcaps), "expletive": float(expl), "no_diacritics": float(no_diacritics),
        "sentences_mean": float(sentences.mean()),
        "ai_ism_per_post": float(sum(ai_hits.values()) / n),
        "ai_ism_top": ai_hits.most_common(8),
    }


# ----------------------------------------------------------------------------- detector
def detector_auc(synth: list[str], ref: list[str], seed: int = 0, folds: int = 5) -> dict:
    """Cross-validated AUC of a char-ngram logistic regression separating synthetic from reference.

    0.5 = indistinguishable; 1.0 = trivially separable. Length-match the reference before calling.
    Also returns the most discriminative features (what gives the synthetic text away).
    """
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import StratifiedKFold, cross_val_predict
    from sklearn.metrics import roc_auc_score
    from sklearn.pipeline import make_pipeline

    X = synth + ref
    y = np.array([1] * len(synth) + [0] * len(ref))
    pipe = make_pipeline(
        TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4), min_df=2, sublinear_tf=True, lowercase=True),
        LogisticRegression(max_iter=2000, C=1.0),
    )
    cv = StratifiedKFold(n_splits=folds, shuffle=True, random_state=seed)
    p = cross_val_predict(pipe, X, y, cv=cv, method="predict_proba")[:, 1]
    auc = roc_auc_score(y, p)
    pipe.fit(X, y)
    vec, clf = pipe.steps[0][1], pipe.steps[1][1]
    names = np.array(vec.get_feature_names_out())
    coef = clf.coef_[0]
    top_synth = names[np.argsort(-coef)[:15]].tolist()
    top_ref = names[np.argsort(coef)[:15]].tolist()
    # word-level variant: more interpretable tells
    pipe_w = make_pipeline(
        TfidfVectorizer(analyzer="word", ngram_range=(1, 2), min_df=2, sublinear_tf=True, lowercase=True),
        LogisticRegression(max_iter=2000, C=1.0),
    )
    pw = cross_val_predict(pipe_w, X, y, cv=cv, method="predict_proba")[:, 1]
    auc_w = roc_auc_score(y, pw)
    pipe_w.fit(X, y)
    vec_w, clf_w = pipe_w.steps[0][1], pipe_w.steps[1][1]
    names_w = np.array(vec_w.get_feature_names_out())
    top_synth_w = names_w[np.argsort(-clf_w.coef_[0])[:20]].tolist()
    return {
        "auc_char": float(auc), "auc_word": float(auc_w),
        "tells_synth_char": top_synth, "tells_ref_char": top_ref, "tells_synth_word": top_synth_w,
    }


# ----------------------------------------------------------------------------- reference
def load_reference(path, min_words: int = 6, max_words: int = 60, seed: int = 0, n: int | None = None) -> list[str]:
    """TwitterEmo-PL: strip mentions/URLs, keep tweets in the length band."""
    import csv

    rng = np.random.default_rng(seed)
    out = []
    with open(path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            t = r["tekst"]
            if "http" in t:
                continue
            t = re.sub(r"@anonymized_account", "", t)
            t = re.sub(r"\s+", " ", t).strip()
            if t.startswith("RT "):
                continue
            k = len(words(t))
            if min_words <= k <= max_words:
                out.append(t)
    if n is not None and len(out) > n:
        out = [out[i] for i in rng.choice(len(out), size=n, replace=False)]
    return out


def length_matched_sample(ref: list[str], target: list[str], seed: int = 0, mult: int = 1) -> list[str]:
    """Sample from ref so that the word-length histogram matches target (per-length bins)."""
    rng = np.random.default_rng(seed)
    by_len: dict[int, list[str]] = {}
    for t in ref:
        by_len.setdefault(len(words(t)), []).append(t)
    out = []
    for t in target:
        L = len(words(t))
        for d in (0, 1, -1, 2, -2, 3, -3):
            pool = by_len.get(L + d)
            if pool:
                for _ in range(mult):
                    out.append(pool[rng.integers(len(pool))])
                break
    return out


@dataclass
class SetReport:
    name: str
    lexical: dict
    semantic: dict
    surface: dict

    def flat(self) -> dict:
        d = {"set": self.name}
        d.update({f"lex_{k}": v for k, v in self.lexical.items()})
        d.update({f"sem_{k}": v for k, v in self.semantic.items()})
        d.update({f"surf_{k}": v for k, v in self.surface.items() if k != "ai_ism_top"})
        return d


def report_set(name: str, texts: list[str], E: np.ndarray | None = None, with_bleu: bool = True) -> SetReport:
    lex = {
        "distinct1": distinct_n(texts, 1), "distinct2": distinct_n(texts, 2), "distinct3": distinct_n(texts, 3),
        "mattr": mattr(texts), "compression_ratio": compression_ratio(texts), "self_rep4": self_repetition(texts, 4),
    }
    if with_bleu:
        lex["self_bleu4"] = self_bleu(texts)
    if E is None:
        E = embed(texts)
    sem = semantic_metrics(E)
    surf = surface_metrics(texts)
    return SetReport(name, lex, sem, surf)
