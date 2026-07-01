"""CONTRACT 2 — artifact (pipeline -> web). The manifest is the authoritative, versioned record of a baked
case: its source label (NEVER an absolute path), inference knobs, seed, engine+version, the artifact pointer
+ byte size, the lane/gate verdict, CONTRACT-1 flags, the refine info and the evaluation metrics. The web
loads ONLY manifests + artifacts; frontend/src/lib/contract.types.ts mirrors this schema so a drift fails
the build. A flat index.json inventories every case."""
from __future__ import annotations

import os
from typing import Any

from .. import __version__
from .trace import TRACE_SCHEMA

MANIFEST_SCHEMA = "lidar3d.manifest/v1"
INDEX_SCHEMA = "lidar3d.index/v1"


def _source_label(params: Any) -> str:
    if getattr(params, "synthetic", False):
        return "synthetic"
    return os.path.basename(str(params.source_dir).rstrip("/\\")) or "sequence"


def build_case_manifest(*, case: Any, params: Any, seed: int, artifact_rel: str, trace_bytes: int,
                        gate: dict, flags: list[dict], metrics: dict, engine: dict, refine: dict) -> dict:
    # Deterministic: a pure function of (params, seed). No absolute paths, no wall-clock.
    return {
        "schema": MANIFEST_SCHEMA,
        "case_id": case.id,
        "category": case.category,
        "real_or_synthetic": case.real_or_synthetic,
        "expected_band": case.expected_band,
        "dataset": getattr(case, "dataset", ""),
        "license": getattr(case, "license", ""),
        "engine": engine,
        "params": {
            "source": _source_label(params),
            "n_frames": params.n_frames, "max_frames": params.max_frames, "image_size": params.image_size,
            "kv_window": params.kv_window, "scale_frames": params.scale_frames,
            "decimation": params.decimation, "conf_quantile": params.conf_quantile,
        },
        "seed": seed,
        "artifact": {"path": artifact_rel, "format": "json", "trace_schema": TRACE_SCHEMA, "bytes": trace_bytes},
        "lane": gate["lane"],
        "gate": gate,
        "flags": flags,
        "refine": refine,
        "metrics": metrics,
    }


def build_index(entries: list[dict]) -> dict:
    return {
        "schema": INDEX_SCHEMA,
        "engine_version": __version__,
        "n_cases": len(entries),
        "cases": sorted(entries, key=lambda e: e["case_id"]),
    }
