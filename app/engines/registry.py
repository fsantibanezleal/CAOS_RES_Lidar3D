"""Engine + source registry. One GPU engine instance, lazily warmed, reused across runs."""
from __future__ import annotations
import glob
from functools import lru_cache

from app import config
from app.engines.lingbot import LingbotEngine

ENGINES = {"lingbot-map": LingbotEngine}


@lru_cache(maxsize=4)
def get_engine(name: str = "lingbot-map"):
    if name not in ENGINES:
        raise KeyError(f"unknown engine {name!r}; have {list(ENGINES)}")
    return ENGINES[name]()


def list_sources() -> list[dict]:
    return [
        {"id": s.id, "label": s.label, "kind": s.kind, "n_frames": s.n_frames, "note": s.note}
        for s in config.discover_sources()
    ]


def source_paths(source_id: str) -> list[str]:
    for s in config.discover_sources():
        if s.id == source_id and s.path is not None:
            return sorted(glob.glob(str(s.path / "*.png")) + glob.glob(str(s.path / "*.jpg")))
    raise KeyError(f"unknown source {source_id!r}")
