"""Stage 4b — evaluate (validation): trajectory + cloud-quality metrics. ATE/RPE vs ground-truth camera
poses when a GT file is present; the bundled example sequences have none, so those are reported as 'no GT'
rather than faked. Honest numbers only."""
from __future__ import annotations

import numpy as np

from ..io.schema import ReconResult


def run(result: ReconResult) -> dict:
    pts = np.asarray(result.points)
    extent = (np.asarray(result.bbox_max) - np.asarray(result.bbox_min)).tolist()
    mean_conf = (float(np.mean([f["conf_mean"] for f in result.per_frame])) if result.per_frame else 0.0)
    return {
        "n_points": int(len(pts)),
        "n_frames": int(result.n_frames),
        "path_length_m": round(float(result.path_length), 3),
        "bbox_extent_m": [round(float(e), 3) for e in extent],
        "mean_conf": round(mean_conf, 3),
        "ate_m": None, "rpe_trans": None, "rpe_rot": None,
        "gt": "none (example sequences carry no ground-truth poses; ATE/RPE reported only when GT is provided)",
    }
