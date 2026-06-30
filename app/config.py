"""Runtime configuration for the Lidar 3D workbench.

Heavy weights/data live OUTSIDE the repo on the E: scratch volume (ADR-0050). Paths are
overridable via environment (.env), but default to the verified local layout. No secrets here.
"""
from __future__ import annotations
import os
from dataclasses import dataclass, field
from pathlib import Path


def _env_path(key: str, default: str) -> Path:
    return Path(os.environ.get(key, default))


# --- where the heavy assets live (verified 2026-06-29) ------------------------------------
MODELS_ROOT = _env_path("LIDAR3D_MODELS_ROOT", r"E:/_Models/3D_Spatial_Reconstruction")
DATA_ROOT = _env_path("LIDAR3D_DATA_ROOT", r"E:/_Datos/3D_Spatial_Reconstruction")

LINGBOT_DIR = MODELS_ROOT / "lingbot-map"
EXAMPLES_DIR = DATA_ROOT / "lingbot-map-examples"


@dataclass(frozen=True)
class EngineDefaults:
    """8 GB-safe lingbot-map config (validated on RTX 4070 Laptop, peak 7.13 GB)."""
    checkpoint: str = "lingbot-map.pt"          # balanced; lingbot-map-long.pt for long scenes
    image_size: int = 518                        # working res; lower (392/364) for >3 FPS
    patch_size: int = 14
    kv_cache_sliding_window: int = 16            # default 64 -> 16 fits 8 GB
    num_scale_frames: int = 8
    camera_num_iterations: int = 1               # 4 = best accuracy, 1 = faster
    use_sdpa: bool = True                        # no FlashInfer build on this host
    max_frames: int = 80                         # safety cap for the interactive App
    point_decimation: int = 6                    # keep every Nth pixel for the browser cloud
    conf_quantile: float = 0.30                  # drop the lowest-confidence pixels


DEFAULTS = EngineDefaults()


@dataclass(frozen=True)
class Source:
    id: str
    label: str
    kind: str                # "real" | "synthetic" | "upload"
    path: Path | None
    n_frames: int
    note: str = ""


def discover_sources() -> list[Source]:
    """The real example sequences shipped with lingbot-map (preserved on E:\\_Datos)."""
    meta = {
        "oxford":     ("Oxford (outdoor walk)", "320-frame outdoor sequence, gentle forward motion."),
        "university": ("University (courtyard)", "324-frame courtyard walk."),
        "loop":       ("Loop (revisit)", "237-frame path that revisits — showcases the drift / loop-closure gap."),
        "courthouse": ("Courthouse (facade)", "286-frame facade orbit."),
    }
    out: list[Source] = []
    for sid, (label, note) in meta.items():
        d = EXAMPLES_DIR / sid
        if d.is_dir():
            n = len(list(d.glob("*.png")) + list(d.glob("*.jpg")))
            out.append(Source(id=sid, label=label, kind="real", path=d, n_frames=n, note=note))
    return out


def checkpoint_path(name: str | None = None) -> Path:
    return LINGBOT_DIR / (name or DEFAULTS.checkpoint)
