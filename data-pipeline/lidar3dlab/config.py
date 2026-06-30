"""Runtime paths from the ENVIRONMENT (no personal paths are ever versioned).

Real values come from a gitignored `.env` provisioned from `_CAOS_MANAGE/credentials/app-env/lidar3d.env`;
`.env.example` carries generic placeholders. If unset, paths fall back to repo-relative defaults and the
ingestion contract simply REJECTS a missing source (clean), so nothing crashes at import.
"""
from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# Heavy assets live OUTSIDE git (ADR-0050/0055). Override via env; default to repo-relative (will be empty).
MODELS_ROOT = Path(os.environ.get("LIDAR3D_MODELS_ROOT", str(REPO_ROOT / "models")))
DATA_ROOT = Path(os.environ.get("LIDAR3D_DATA_ROOT", str(REPO_ROOT / "data" / "raw")))

LINGBOT_CHECKPOINT = os.environ.get("LIDAR3D_LINGBOT_CKPT", "lingbot-map.pt")
EXAMPLES_SUBDIR = "lingbot-map-examples"


def checkpoint_path(name: str | None = None) -> Path:
    return MODELS_ROOT / "lingbot-map" / (name or LINGBOT_CHECKPOINT)


def sequence_dir(seq: str) -> Path:
    """Resolve a real example sequence folder under DATA_ROOT (best-effort; the contract validates existence)."""
    return DATA_ROOT / EXAMPLES_SUBDIR / seq
