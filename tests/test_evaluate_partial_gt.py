"""A frame outside the ground-truth record must be dropped, not paired with a distant sample.

This is the normal case, not an edge case: on freiburg3_long_office the GT recording starts 67 ms
after the first image, and an all-or-nothing association threw the whole trajectory away.
"""
from __future__ import annotations

import numpy as np

from lidar3dlab.io.schema import ReconResult
from lidar3dlab.stages import evaluate


def _result(poses: np.ndarray, gt: np.ndarray) -> ReconResult:
    return ReconResult(
        case_id="T", n_frames=len(poses),
        poses_c2w=np.asarray([p[:3, :4].reshape(-1) for p in poses], np.float32),
        points=np.zeros((10, 3), np.float32), colors=np.zeros((10, 3), np.uint8),
        per_frame=[{"idx": i, "conf_mean": 1.0} for i in range(len(poses))],
        path_length=1.0, bbox_min=[0, 0, 0], bbox_max=[1, 1, 1], gt_c2w=gt)


def _traj(n: int = 20) -> np.ndarray:
    out = np.tile(np.eye(4), (n, 1, 1))
    out[:, 0, 3] = np.arange(n) * 0.1
    return out


def test_unmatched_frames_are_dropped_and_counted():
    gt = _traj()
    gt[0] = np.nan                       # the first image predates the GT record
    gt[7] = np.nan                       # and one sample is missing mid-run
    m = evaluate.run(_result(_traj(), gt))
    assert m["ate_m"] == 0.0             # the aligned frames are perfect
    assert "18 of 20 frames" in m["gt"]
    assert "2 frames outside the ground-truth record" in m["gt"]


def test_rpe_skips_pairs_that_straddle_a_missing_frame():
    """A gap must not become a fabricated two-step motion."""
    gt = _traj()
    gt[10] = np.nan
    est = _traj()
    est[11:, 0, 3] += 5.0                # a jump exactly across the gap
    m = evaluate.run(_result(est, gt))
    # The pairs (9,10) and (10,11) are skipped, so the jump is invisible to RPE...
    assert m["rpe_trans"] == 0.0
    # ...but ATE still sees it, because those frames are compared in position.
    assert m["ate_m"] > 1.0


def test_too_few_matched_frames_is_stated():
    gt = _traj(10)
    gt[3:] = np.nan
    m = evaluate.run(_result(_traj(10), gt))
    assert m["ate_m"] is None
    assert "only 3 frames aligned" in m["gt"]
