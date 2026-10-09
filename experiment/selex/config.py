"""Configuration loading and paths for the selection experiment."""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIGS = ROOT / "configs"
PROMPTS = ROOT / "prompts"
ARTIFACTS = ROOT / "artifacts"
FROZEN = ARTIFACTS / "frozen"


def load(path: str | Path = CONFIGS / "experiment.yaml") -> dict:
    cfg = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    cfg["_root"] = ROOT
    cfg["results_dir"] = (ROOT / cfg.get("results_dir", "results")).resolve()
    cfg["results_dir"].mkdir(parents=True, exist_ok=True)
    return cfg


def resolve(p: str | Path) -> Path:
    p = Path(p)
    return p if p.is_absolute() else (ROOT / p).resolve()


def read_prompt(name: str) -> str:
    return (PROMPTS / f"{name}.md").read_text(encoding="utf-8")
