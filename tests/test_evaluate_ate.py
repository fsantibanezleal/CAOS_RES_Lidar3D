"""Gates for the evaluate stage's trajectory metrics.

Until 0.16.000 the stage reported `ate_m: null, gt: "none"` for EVERY case, including the ten that
carry TUM or ICL ground truth, so every published ATE came from an out-of-band script and none of
them was reproducible from the committed pipeline. These tests pin the metric itself (a rigid
alignment, no scale) and the honest-absence behaviour.
"""
from __future__ import annotations

import numpy as np

from lidar3dlab.io.schema import ReconResult
from lidar3dlab.stages import evaluate


def _result(poses: np.ndarray, gt: np.ndarray | None) -> ReconResult:
    return ReconResult(
        case_id="T", n_frames=len(poses),
        poses_c2w=np.asarray([p[:3, :4].reshape(-1) for p in poses], np.float32),
        points=np.zeros((10, 3), np.float32), colors=np.zeros((10, 3), np.uint8),
        per_frame=[{"idx": i, "conf_mean": 1.0} for i in range(len(poses))],
        path_length=1.0, bbox_min=[0, 0, 0], bbox_max=[1, 1, 1], gt_c2w=gt)


def _traj(n: int = 20, drift: float = 0.0) -> np.ndarray:
    """A straight walk along +x, optionally bent by an ACCUMULATING (quadratic) drift.

    The drift is quadratic on purpose: a linear sideways drift of a straight path is just a
    rotation of it, so a rigid alignment absorbs it and ATE correctly reads near zero. Real
    accumulated drift bends the path, which no rigid transform can undo.
    """
    out = np.tile(np.eye(4), (n, 1, 1))
    for i in range(n):
        f = i / max(n - 1, 1)
        out[i, 0, 3] = i * 0.1
        out[i, 1, 3] = drift * f * f
    return out


def test_no_ground_truth_reports_absence_not_a_number():
    m = evaluate.run(_result(_traj(), None))
    assert m["ate_m"] is None and m["rpe_trans"] is None and m["rpe_rot"] is None
    assert m["gt"].startswith("none")


def test_a_perfect_trajectory_scores_zero():
    gt = _traj()
    m = evaluate.run(_result(gt.copy(), gt))
    assert m["ate_m"] == 0.0
    assert m["rpe_trans"] == 0.0
    assert m["rpe_rot"] == 0.0
    assert "ground truth" in m["gt"]


def test_a_rigid_offset_is_aligned_away_and_a_drift_is_not():
    """ATE must not punish the arbitrary world frame, and must punish real drift."""
    gt = _traj()
    shifted = gt.copy()
    shifted[:, :3, 3] += np.array([5.0, -2.0, 3.0])          # a pure translation of the whole run
    theta = 0.7
    rot = np.array([[np.cos(theta), -np.sin(theta), 0.0],
                    [np.sin(theta), np.cos(theta), 0.0],
                    [0.0, 0.0, 1.0]])
    for i in range(len(shifted)):
        shifted[i, :3, 3] = rot @ shifted[i, :3, 3]           # and a rotation of it
    assert evaluate.run(_result(shifted, gt))["ate_m"] < 1e-6

    # A bent path is real error and must survive the alignment. The rigid fit still absorbs the
    # linear part of a quadratic bend, so the residual is a fraction of the end displacement (a
    # 0.2 m end drift over a 1.9 m walk leaves 0.017 m): the property to assert is that it is
    # clearly non-zero and grows with the drift, not a particular fraction.
    small = evaluate.run(_result(_traj(drift=0.1), gt))["ate_m"]
    large = evaluate.run(_result(_traj(drift=0.2), gt))["ate_m"]
    assert small > 0.005, small
    assert large > 1.8 * small, (small, large)


def test_rpe_sees_per_step_error_that_ate_can_hide():
    """A trajectory that wobbles per step but ends in the right place: low ATE, non-zero RPE."""
    gt = _traj(n=30)
    wobble = gt.copy()
    wobble[1::2, 1, 3] += 0.01                                # every other frame nudged sideways
    m = evaluate.run(_result(wobble, gt))
    assert m["ate_m"] < 0.01
    assert m["rpe_trans"] > 0.005


def test_rotation_error_is_reported_in_degrees():
    gt = _traj(n=12)
    est = gt.copy()
    theta = np.radians(3.0)
    step = np.array([[np.cos(theta), -np.sin(theta), 0.0],
                     [np.sin(theta), np.cos(theta), 0.0],
                     [0.0, 0.0, 1.0]])
    # Each estimated frame carries one extra 3 degree rotation relative to its predecessor.
    for i in range(1, len(est)):
        est[i, :3, :3] = step @ est[i - 1, :3, :3]
    m = evaluate.run(_result(est, gt))
    assert abs(m["rpe_rot"] - 3.0) < 0.2, m["rpe_rot"]


def test_too_few_aligned_frames_is_stated_not_computed():
    gt = _traj(n=3)
    m = evaluate.run(_result(gt.copy(), gt))
    assert m["ate_m"] is None
    assert "at least 4" in m["gt"]
