"""Stage 4b, evaluate (validation): trajectory + cloud-quality metrics.

ATE and RPE are computed against ground-truth camera poses whenever the sequence carries them
(`ReconResult.gt_c2w`, set by the engines that load a GT-bearing dataset). Sequences without GT
report `gt: "none"` and null metrics rather than a fabricated number.

Conventions (Zhang and Scaramuzza 2018, the visual-inertial convention this lab uses):
  ATE: RMS position error after a RIGID (R, t) alignment of the estimated trajectory to the GT.
       No scale is fitted, because every engine here is metric by construction; a Sim(3) variant
       would hide exactly the scale error the RGB-only track is judged on.
  RPE: error of the relative motion between consecutive frames, reported as the RMS translation
       error in metres and the RMS rotation error in degrees. RPE is drift per step; ATE is the
       accumulated result, and a method can be good at one and poor at the other.
"""
from __future__ import annotations

import numpy as np

from ..io.schema import ReconResult


def umeyama_rigid_ate(pred_c: np.ndarray, gt_c: np.ndarray) -> float:
    """RMS ATE after a rigid (R, t) alignment of the predicted centres to the GT (no scale)."""
    mp, mg = pred_c.mean(0), gt_c.mean(0)
    p, g = pred_c - mp, gt_c - mg
    u, _, vt = np.linalg.svd(p.T @ g)
    d = np.sign(np.linalg.det(vt.T @ u.T))
    r = vt.T @ np.diag([1.0, 1.0, d]) @ u.T
    aligned = (r @ p.T).T + mg
    return float(np.sqrt(((aligned - gt_c) ** 2).sum(1).mean()))


def relative_pose_error(pred: np.ndarray, gt: np.ndarray, valid: np.ndarray | None = None) -> tuple[float, float]:
    """RMS relative-pose error over consecutive frames: (translation metres, rotation degrees).

    Only pairs whose BOTH frames carry ground truth are used, so a frame the GT recording does not
    cover (a boundary frame, the normal case) never turns into a fabricated two-step motion.
    """
    t_err, r_err = [], []
    for i in range(len(pred) - 1):
        if valid is not None and not (valid[i] and valid[i + 1]):
            continue
        rel_p = np.linalg.inv(pred[i]) @ pred[i + 1]
        rel_g = np.linalg.inv(gt[i]) @ gt[i + 1]
        delta = np.linalg.inv(rel_g) @ rel_p
        t_err.append(float(np.linalg.norm(delta[:3, 3])))
        # Rotation angle of the residual rotation, numerically guarded at the trace bounds.
        cos = (np.trace(delta[:3, :3]) - 1.0) / 2.0
        r_err.append(float(np.degrees(np.arccos(np.clip(cos, -1.0, 1.0)))))
    if not t_err:
        return float("nan"), float("nan")
    return (float(np.sqrt(np.mean(np.square(t_err)))),
            float(np.sqrt(np.mean(np.square(r_err)))))


def _as_matrices(poses: np.ndarray) -> np.ndarray:
    """[S,12] row-major 3x4 or [S,4,4] -> [S,4,4]."""
    arr = np.asarray(poses, dtype=np.float64)
    if arr.ndim == 3 and arr.shape[1:] == (4, 4):
        return arr
    out = np.tile(np.eye(4), (arr.shape[0], 1, 1))
    out[:, :3, :4] = arr.reshape(-1, 3, 4)
    return out


def run(result: ReconResult) -> dict:
    pts = np.asarray(result.points)
    extent = (np.asarray(result.bbox_max) - np.asarray(result.bbox_min)).tolist()
    mean_conf = (float(np.mean([f["conf_mean"] for f in result.per_frame])) if result.per_frame else 0.0)
    metrics = {
        "n_points": int(len(pts)),
        "n_frames": int(result.n_frames),
        "path_length_m": round(float(result.path_length), 3),
        "bbox_extent_m": [round(float(e), 3) for e in extent],
        "mean_conf": round(mean_conf, 3),
        "ate_m": None, "rpe_trans": None, "rpe_rot": None,
        "gt": "none (this sequence carries no ground-truth poses; ATE and RPE are reported only when it does)",
    }

    gt = result.gt_c2w
    if gt is None:
        return metrics
    gt_m = _as_matrices(gt)
    pred_m = _as_matrices(result.poses_c2w)
    n = min(len(gt_m), len(pred_m))
    gt_m, pred_m = gt_m[:n], pred_m[:n]
    # A frame the GT recording does not cover is NaN, not a nearby sample pretending to be it.
    valid = np.isfinite(gt_m.reshape(n, -1)).all(axis=1)
    k = int(valid.sum())
    if k < 4:
        metrics["gt"] = f"present but only {k} frames aligned; ATE needs at least 4"
        return metrics
    metrics["ate_m"] = round(umeyama_rigid_ate(pred_m[valid][:, :3, 3], gt_m[valid][:, :3, 3]), 4)
    rpe_t, rpe_r = relative_pose_error(pred_m, gt_m, valid)
    metrics["rpe_trans"] = round(rpe_t, 4)
    metrics["rpe_rot"] = round(rpe_r, 4)
    suffix = "" if k == n else f" ({n - k} frames outside the ground-truth record)"
    metrics["gt"] = f"ground truth, {k} of {n} frames, rigid-aligned ATE (no scale fitted){suffix}"
    return metrics
