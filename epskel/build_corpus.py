"""Full corpus build (plan sections 4-6, Annex I).

Pipeline (each stage is cached to corpus/<name>/ so a crash resumes):
  1. personas:   N ordinary authors (Annex J) + one card per arc (from PI sketches)
  2. quotas:     posts per ordinary author (from posts_per_week, scaled to the layer totals)
  3. background: method-of-choice generator, per author
  4. hardneg:    Annex B generator; hard negatives are spread over ordinary authors with a skewed
                 allocation (most authors 0-2, a few up to ~8), never over arc authors
  5. arcs:       Annex C generator, all arcs in data/arcs.yaml (PI chooses the 10+2 subset later)
  6. timeline:   12-week window, per-author rhythm; arc day offsets preserved
  7. tables:     posts_v1.csv, authors_v1.csv (Annex I) + corpus_manifest.json (versions, seeds, hashes)

The generator model, prompt versions, seeds and method are recorded on every row.
"""

from __future__ import annotations

import hashlib
import json
import random
from datetime import datetime
from pathlib import Path

import pandas as pd

from . import config
from .gen import ARCS, ArcGenerator, BackgroundGenerator, HardNegGenerator, Post
from .llm import LLM, looks_like_refusal
from .personas import generate_personas, load_personas, save_personas
from .timeline import Timeline, iso, rhythm_class


def _jsonl_write(posts: list[Post], path: Path) -> None:
    with path.open("a", encoding="utf-8") as f:
        for p in posts:
            f.write(json.dumps(p.to_dict(), ensure_ascii=False) + "\n")


def _jsonl_read(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def allocate_quotas(cards: list[dict], total: int, rng: random.Random, weeks: int = 12) -> dict[str, int]:
    """Posts per ordinary author proportional to posts_per_week, jittered, scaled to `total`."""
    raw = {c["author_id"]: max(1.0, float(c["posts_per_week"]) * weeks * rng.uniform(0.6, 1.4)) for c in cards}
    s = sum(raw.values())
    q = {k: max(3, int(round(v / s * total))) for k, v in raw.items()}
    # fix rounding drift
    diff = total - sum(q.values())
    keys = list(q)
    while diff != 0:
        k = rng.choice(keys)
        if diff > 0:
            q[k] += 1; diff -= 1
        elif q[k] > 3:
            q[k] -= 1; diff += 1
    return q


def allocate_hardneg(cards: list[dict], total: int, rng: random.Random) -> dict[str, int]:
    """Skewed allocation: ~40 % of authors get none; the rest follow a geometric-ish tail."""
    ids = [c["author_id"] for c in cards]
    counts = {i: 0 for i in ids}
    weights = [0.0 if rng.random() < 0.40 else rng.paretovariate(1.8) for _ in ids]
    if sum(weights) == 0:
        weights = [1.0] * len(ids)
    for _ in range(total):
        counts[rng.choices(ids, weights=weights)[0]] += 1
    return counts


class CorpusBuilder:
    def __init__(self, name: str, model: str, method: str, n_authors: int, n_background: int, n_hardneg: int,
                 arc_ids: list[str] | None, seed: int, start: datetime, bg_prompt: str = "background_v2",
                 hn_prompt: str = "hardneg_v2", arc_prompt: str = "arc_post_v2", workers: int = 8,
                 temperature: float = 1.0, persona_model: str | None = None) -> None:
        self.name = name
        self.dir = config.CORPUS / name
        self.dir.mkdir(parents=True, exist_ok=True)
        self.model = model
        self.method = method
        self.n_authors = n_authors
        self.n_background = n_background
        self.n_hardneg = n_hardneg
        self.arc_ids = arc_ids or [a["arc_id"] for a in ARCS]
        self.seed = seed
        self.start = start
        self.bg_prompt, self.hn_prompt, self.arc_prompt = bg_prompt, hn_prompt, arc_prompt
        self.workers = workers
        self.temperature = temperature
        self.persona_model = persona_model or model
        self.llm = LLM(model, run_name=f"corpus_{name}", temperature=temperature, max_tokens=4000)
        self.rng = random.Random(seed)
        self.log = self.dir / "build_log.jsonl"

    def _logev(self, **kw) -> None:
        kw["ts"] = datetime.now().isoformat(timespec="seconds")
        with self.log.open("a", encoding="utf-8") as f:
            f.write(json.dumps(kw, ensure_ascii=False) + "\n")

    # ------------------------------------------------------------------ 1. personas
    def personas(self) -> tuple[list[dict], dict[str, dict]]:
        p = self.dir / "personas.json"
        if p.exists():
            cards = load_personas(p)
        else:
            pl = LLM(self.persona_model, run_name=f"corpus_{self.name}_personas", temperature=1.0, max_tokens=6000)
            cards = generate_personas(pl, n_total=self.n_authors, batch=6, seed=self.seed, embedder=True, parallel=6)
            save_personas(cards, p)
            self._logev(stage="personas", n=len(cards), cost=pl.total_cost, model=pl.model)
        arc_cards = json.loads((config.DATA / "arc_personas.json").read_text(encoding="utf-8"))
        return cards, arc_cards

    # ------------------------------------------------------------------ 3. background
    def background(self, cards: list[dict]) -> list[dict]:
        path = self.dir / "background.jsonl"
        done = _jsonl_read(path)
        done_by_author: dict[str, int] = {}
        for d in done:
            done_by_author[d["author_id"]] = done_by_author.get(d["author_id"], 0) + 1
        quotas = allocate_quotas(cards, self.n_background, random.Random(self.seed + 1))
        (self.dir / "quotas_background.json").write_text(json.dumps(quotas, indent=1))
        todo = [(c, quotas[c["author_id"]] - done_by_author.get(c["author_id"], 0)) for c in cards]
        todo = [(c, n) for c, n in todo if n > 0]
        if not todo:
            return done
        gen = BackgroundGenerator(self.llm, method=self.method, seed=self.seed + 2, prompt_version=self.bg_prompt)

        def job(args):
            c, n = args
            try:
                ps = gen.generate_for_author(c, n)
            except Exception as e:
                self._logev(stage="background", author=c["author_id"], error=str(e))
                return []
            ps = [p for p in ps if p.text.strip()]
            _jsonl_write(ps, path)
            return ps

        self.llm.map(todo, job, workers=self.workers, desc="background")
        self._logev(stage="background", cost=self.llm.total_cost)
        return _jsonl_read(path)

    # ------------------------------------------------------------------ 4. hard negatives
    def hardneg(self, cards: list[dict]) -> list[dict]:
        path = self.dir / "hardneg.jsonl"
        done = _jsonl_read(path)
        alloc = allocate_hardneg(cards, self.n_hardneg, random.Random(self.seed + 3))
        (self.dir / "quotas_hardneg.json").write_text(json.dumps(alloc, indent=1))
        done_by_author: dict[str, int] = {}
        for d in done:
            done_by_author[d["author_id"]] = done_by_author.get(d["author_id"], 0) + 1
        by_id = {c["author_id"]: c for c in cards}
        jobs = []
        for aid, n in alloc.items():
            for _ in range(n - done_by_author.get(aid, 0)):
                jobs.append(by_id[aid])
        if not jobs:
            return done
        gen = HardNegGenerator(self.llm, seed=self.seed + 4, prompt_version=self.hn_prompt)

        def job(c):
            try:
                p = gen.generate(c)
            except Exception as e:
                self._logev(stage="hardneg", author=c["author_id"], error=str(e))
                return None
            if p.text.strip():
                _jsonl_write([p], path)
            return p

        self.llm.map(jobs, job, workers=self.workers, desc="hardneg")
        self._logev(stage="hardneg", cost=self.llm.total_cost)
        return _jsonl_read(path)

    # ------------------------------------------------------------------ 5. arcs
    def arcs(self, arc_cards: dict[str, dict]) -> list[dict]:
        path = self.dir / "arcs.jsonl"
        done = _jsonl_read(path)
        done_ids = {d["attrs"]["arc_id"] for d in done}
        todo = [a for a in self.arc_ids if a not in done_ids]
        if not todo:
            return done
        gen = ArcGenerator(self.llm, seed=self.seed + 5, prompt_version=self.arc_prompt)

        def job(arc_id):
            arc = next(a for a in ARCS if a["arc_id"] == arc_id)
            try:
                ps = gen.generate_arc(arc, arc_cards[arc_id])
            except Exception as e:
                self._logev(stage="arcs", arc=arc_id, error=str(e))
                return []
            _jsonl_write(ps, path)
            return ps

        self.llm.map(todo, job, workers=min(self.workers, len(todo)), desc="arcs")
        self._logev(stage="arcs", cost=self.llm.total_cost)
        return _jsonl_read(path)

    # ------------------------------------------------------------------ 6-7. assemble
    def assemble(self, cards: list[dict], arc_cards: dict[str, dict], bg: list[dict], hn: list[dict], arcs: list[dict],
                 version: str = "v1") -> tuple[pd.DataFrame, pd.DataFrame]:
        tl = Timeline(self.start, seed=self.seed + 6)
        by_id = {c["author_id"]: c for c in cards}
        rows = []
        # ordinary authors: background + hardneg interleaved on one timeline
        per_author: dict[str, list[dict]] = {}
        for d in bg + hn:
            per_author.setdefault(d["author_id"], []).append(d)
        for aid, ds in per_author.items():
            rnd = random.Random(f"{self.seed}-{aid}")
            rnd.shuffle(ds)
            stamps = tl.author_timestamps(by_id[aid], len(ds))
            for d, ts in zip(ds, stamps):
                rows.append(self._row(d, ts, None))
        # arcs
        arc_by_id = {a["arc_id"]: a for a in ARCS}
        grouped: dict[str, list[dict]] = {}
        for d in arcs:
            grouped.setdefault(d["attrs"]["arc_id"], []).append(d)
        for arc_id, ds in grouped.items():
            ds.sort(key=lambda d: d["attrs"]["n"])
            card = arc_cards[arc_id]
            stamps = tl.arc_timestamps(card, [d["attrs"]["day"] for d in ds])
            for d, ts in zip(ds, stamps):
                rows.append(self._row(d, ts, arc_by_id[arc_id]))
        posts = pd.DataFrame(rows).sort_values(["author_id", "timestamp"]).reset_index(drop=True)
        posts["post_id"] = [f"P{i+1:05d}" for i in range(len(posts))]
        cols = ["post_id", "author_id", "layer", "timestamp", "text", "generator_version", "prompt_version", "generation_seed",
                "arc_id", "arc_position", "arc_role", "post_level_profile", "latent_factors_json", "source_template", "method", "call_ids"]
        posts = posts[cols]
        # authors table
        arows = []
        for c in cards:
            sub = posts[posts.author_id == c["author_id"]]
            arows.append({"author_id": c["author_id"], "persona_card_json": json.dumps({k: v for k, v in c.items() if k not in ("prompt_version", "generator_model")}, ensure_ascii=False),
                          "is_target": False, "arc_id": "", "arc_type": "", "n_posts": len(sub),
                          "first_post_ts": sub.timestamp.min() if len(sub) else "", "last_post_ts": sub.timestamp.max() if len(sub) else "",
                          "rhythm_class": rhythm_class(c)})
        for arc_id, card in arc_cards.items():
            if arc_id not in grouped:
                continue
            a = arc_by_id[arc_id]
            sub = posts[posts.author_id == card["author_id"]]
            arows.append({"author_id": card["author_id"], "persona_card_json": json.dumps({k: v for k, v in card.items() if k not in ("forbidden_hits",)}, ensure_ascii=False),
                          "is_target": a["arc_type"] != "decoy", "arc_id": arc_id, "arc_type": a["arc_type"], "n_posts": len(sub),
                          "first_post_ts": sub.timestamp.min(), "last_post_ts": sub.timestamp.max(), "rhythm_class": rhythm_class(card)})
        authors = pd.DataFrame(arows)
        posts.to_csv(self.dir / f"posts_{version}.csv", index=False)
        authors.to_csv(self.dir / f"authors_{version}.csv", index=False)
        # signal-post key (PI's "wzorcowa kwalifikacja"), kept OUT of the posts table
        key = []
        for arc_id, ds in grouped.items():
            a = arc_by_id[arc_id]
            for d in ds:
                key.append({"arc_id": arc_id, "arc_type": a["arc_type"], "arc_position": d["attrs"]["n"],
                            "is_signal": d["attrs"]["n"] in a["signal_posts"], "legal_relevance_focus": a["legal_relevance_focus"]})
        pd.DataFrame(key).to_csv(self.dir / f"arc_key_{version}.csv", index=False)
        manifest = {
            "corpus": self.name, "version": version, "built": datetime.now().isoformat(timespec="seconds"),
            "model": self.model, "method": self.method, "temperature": self.temperature, "seed": self.seed,
            "prompt_versions": {"background": self.bg_prompt, "hardneg": self.hn_prompt, "arc": self.arc_prompt,
                                "persona": cards[0].get("prompt_version") if cards else None},
            "window_start": iso(tl.start), "window_end": iso(tl.end),
            "n_posts": int(len(posts)), "n_authors": int(len(authors)),
            "layers": posts.layer.value_counts().to_dict(),
            "arcs": sorted(grouped),
            "sha256_posts": hashlib.sha256((self.dir / f"posts_{version}.csv").read_bytes()).hexdigest(),
            "sha256_authors": hashlib.sha256((self.dir / f"authors_{version}.csv").read_bytes()).hexdigest(),
            "cost_usd_generation": self.llm.total_cost,
        }
        (self.dir / f"manifest_{version}.json").write_text(json.dumps(manifest, indent=1, ensure_ascii=False))
        return posts, authors

    def _row(self, d: dict, ts: datetime, arc: dict | None) -> dict:
        a = d["attrs"]
        latent = {k: v for k, v in a.items() if k not in ("brief", "situation_so_far", "n", "day", "role", "profile")} if d["layer"] != "background" else {}
        return {
            "author_id": d["author_id"], "layer": d["layer"], "timestamp": iso(ts), "text": d["text"],
            "generator_version": "epskel-0.1", "prompt_version": d["prompt_version"], "generation_seed": self.seed,
            "arc_id": a.get("arc_id", "") if arc else "", "arc_position": a.get("n", "") if arc else "",
            "arc_role": a.get("role", "") if arc else "",
            "post_level_profile": a.get("profile", "") if arc else (a.get("retention_profile", "") if d["layer"] == "hardneg" else "clear_discard"),
            "latent_factors_json": json.dumps(latent, ensure_ascii=False) if latent else "",
            "source_template": d["prompt_version"], "method": d["method"], "call_ids": "|".join(d.get("call_ids", [])),
        }

    # ------------------------------------------------------------------ run
    def run(self) -> tuple[pd.DataFrame, pd.DataFrame]:
        cards, arc_cards = self.personas()
        bg = self.background(cards)
        hn = self.hardneg(cards)
        arcs = self.arcs(arc_cards)
        return self.assemble(cards, arc_cards, bg, hn, arcs)
