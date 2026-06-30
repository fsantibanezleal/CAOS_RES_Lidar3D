"""The compact TRACE = the web-replay artifact (CONTRACT 2). A decimated, RGB-colored world point cloud +
the camera trajectory (poses) + per-frame summary + a few depth thumbnails. Its shape is mirrored by
frontend/src/lib/contract.types.ts, so a drift fails the web build. Binary arrays are base64 (Float32 xyz,
Uint8 rgb, Float32 poses) to stay compact. Schema id is versioned. Deterministic (seeded decimation)."""
from __future__ import annotations

import base64

import numpy as np

from ..io.schema import ReconResult

TRACE_SCHEMA = "lidar3d.recon/v1"
MAX_POINTS = 120_000   # committed replay-artifact budget; decimate further if larger


def _b64_f32(a: np.ndarray) -> str:
    return base64.b64encode(np.ascontiguousarray(a, dtype="<f4").tobytes()).decode()


def _b64_u8(a: np.ndarray) -> str:
    return base64.b64encode(np.ascontiguousarray(a, dtype=np.uint8).tobytes()).decode()


def build_trace(result: ReconResult, refine_info: dict) -> dict:
    pts = np.asarray(result.points, np.float32)
    cols = np.asarray(result.colors, np.uint8)
    n = len(pts)
    if n > MAX_POINTS:
        idx = np.random.default_rng(0).choice(n, MAX_POINTS, replace=False)
        pts, cols = pts[idx], cols[idx]
    poses = np.asarray(result.poses_c2w, np.float32).reshape(-1, 12)
    return {
        "schema": TRACE_SCHEMA,
        "case_id": result.case_id,
        "n_frames": int(result.n_frames),
        "n_points": int(len(pts)),
        "points_b64": _b64_f32(pts.reshape(-1)),
        "colors_b64": _b64_u8(cols.reshape(-1)),
        "poses_b64": _b64_f32(poses.reshape(-1)),
        "per_frame": result.per_frame,
        "path_length": round(float(result.path_length), 3),
        "bbox_min": [round(float(x), 3) for x in result.bbox_min],
        "bbox_max": [round(float(x), 3) for x in result.bbox_max],
        "depth_thumbs": result.depth_thumbs,
        "refine": refine_info,
        "summary": {"n_points": int(len(pts)), "n_frames": int(result.n_frames),
                    "path_length_m": round(float(result.path_length), 3)},
    }
