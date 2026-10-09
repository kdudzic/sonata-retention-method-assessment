"""Artifact freezing (plan stage 0, 11.2): selector artifacts are hashed and recorded BEFORE the evaluation
corpus is scored. Scoring the evaluation corpus refuses to run unless the current artifacts match the frozen
manifest. Dev-corpus runs are always allowed (tuning happens there)."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path

from . import config

MANIFEST = config.FROZEN / "manifest.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def artifact_paths(cfg: dict) -> dict[str, Path]:
    s = cfg["selectors"]
    paths = {
        "s0_lexicon": config.resolve(s["s0"]["lexicon"]),
        "s1_seeds": config.resolve(s["s1"]["seeds"]),
        "experiment_config": config.CONFIGS / "experiment.yaml",
        "arc_split": config.resolve(cfg["corpus"]["arc_split"]),
    }
    for p in ("prompt_d0", "prompt_d3nat", "prompt_blind_d0", "prompt_blind_d3nat"):
        paths[p] = config.PROMPTS / f"{s['s3'][p]}.md"
    return paths


def freeze(cfg: dict, note: str = "") -> dict:
    paths = artifact_paths(cfg)
    man = {"frozen_at": datetime.now().isoformat(timespec="seconds"), "note": note,
           "artifacts": {k: {"path": str(p.relative_to(config.ROOT)), "sha256": sha256(p)} for k, p in paths.items()},
           "s0_weights": cfg["selectors"]["s0"]["weights"], "aggregation": cfg["aggregation"],
           "s1_model": cfg["selectors"]["s1"]["embedding_model"], "s3_open_model": cfg["selectors"]["s3"]["open_model"],
           "s3_control_model": cfg["selectors"]["s3"]["control_model"]}
    config.FROZEN.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(man, indent=1, ensure_ascii=False), encoding="utf-8")
    # keep frozen copies next to the manifest
    for k, p in paths.items():
        (config.FROZEN / f"{k}{p.suffix}").write_bytes(p.read_bytes())
    return man


def check(cfg: dict) -> tuple[bool, list[str]]:
    if not MANIFEST.exists():
        return False, ["no frozen manifest: run `freeze` first"]
    man = json.loads(MANIFEST.read_text(encoding="utf-8"))
    problems = []
    for k, p in artifact_paths(cfg).items():
        rec = man["artifacts"].get(k)
        if rec is None:
            problems.append(f"{k}: not in manifest")
        elif rec["sha256"] != sha256(p):
            problems.append(f"{k}: changed since freeze")
    if man.get("s0_weights") != cfg["selectors"]["s0"]["weights"]:
        problems.append("s0 weights changed since freeze")
    if man.get("aggregation") != cfg["aggregation"]:
        problems.append("aggregation changed since freeze")
    return (not problems), problems
