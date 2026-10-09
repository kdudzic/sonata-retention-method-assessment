"""Paths and key resolution for the EP-SKEL generation pipeline."""

from __future__ import annotations

import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROMPTS = ROOT / "prompts"
DATA = ROOT / "data"
BENCH = ROOT / "bench"
CORPUS = ROOT / "corpus"
RAW = ROOT / "raw"
NOTES = ROOT / "notes"

KEY_FILE = ROOT / "sonata_openrouter.txt"
KEY_FILE_HOME = Path.home() / "sync" / "tokens" / "sonata_openrouter.txt"   # user keeps keys here since 2026-10-09
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


def read_api_key() -> str:
    """Resolve the OpenRouter key: env var first, then the local key file."""
    key = os.environ.get("OPENROUTER_API_KEY")
    if key:
        return key.strip()
    for kf in (KEY_FILE, KEY_FILE_HOME):
        if kf.exists():
            m = re.search(r"sk-or-[A-Za-z0-9_\-]+", kf.read_text())
            if m:
                return m.group(0)
    raise RuntimeError("No OpenRouter key: set OPENROUTER_API_KEY or put sonata_openrouter.txt in ~/sync/tokens/")


def read_prompt(name: str) -> str:
    return (PROMPTS / name).read_text(encoding="utf-8")
