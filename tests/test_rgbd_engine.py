"""Track B (rgbd-sensor) engine: the windowed-fusion trajectory helpers and the RGB-D-root contract fallback.

torch-dependent pieces skip in the no-torch CI lane (same policy as test_window_ba)."""
import numpy as np
import pytest

from lidar3dlab.io.contract import count_frames
from lidar3dlab.model.rgbd_engine import _GUARD_MIN, _WIN, _chain, _depth_ok, _trajectory


def _make_rel(dx: float):
    t = np.eye(4)
    t[0, 3] = dx
    return t


def test_chain_holds_pose_on_failed_pair():
    """A failed pair must HOLD the pose (no invented motion) and be counted."""
    def rel_pose(i, j):
        if i == 2:
            return None
        return (_make_rel(0.1), 50)
    c2ws, fallbacks = _chain(rel_pose, 6)
    assert len(c2ws) == 6 and fallbacks == 1
    assert np.allclose(c2ws[3], c2ws[2])                   # held
    assert np.isclose(c2ws[5][0, 3], 0.4)                  # 4 good steps of 0.1


def test_trajectory_matches_chain_on_clean_translation():
    """On noise-free consecutive+skip-consistent edges the fused trajectory equals the chain (identity fixture)."""
    pytest.importorskip("torch")

    def rel_pose(i, j):
        return (_make_rel(0.1 * (j - i)), 100)             # consistent: skip edges = summed consecutive
    n = _WIN + 3                                            # one full window + a chained tail
    fused, fb = _trajectory(rel_pose, n)
    chain, _ = _chain(rel_pose, n)
    assert len(fused) == n and fb == 0
    for a, b in zip(fused, chain):
        assert np.allclose(a[:3, 3], b[:3, 3], atol=1e-2)


def test_trajectory_short_sequence_falls_back_to_chain():
    def rel_pose(i, j):
        return (_make_rel(0.1), 10)
    fused, _ = _trajectory(rel_pose, 3)                     # shorter than a window
    chain, _ = _chain(rel_pose, 3)
    assert len(fused) == 3
    for a, b in zip(fused, chain):
        assert np.allclose(a, b)


def test_depth_edge_guard_rejects_discontinuity_matches():
    """With the guard active (enough flat matches survive), matches on a depth edge are dropped."""
    depth = np.full((128, 128), 2.0, np.float32)
    depth[:, 96:] = 5.0                                       # a vertical depth cliff at column 96
    # >= _GUARD_MIN flat matches in the near region (columns << 96) so the guarded set is USED (not the fallback)
    flat = np.array([[float(5 + (k % 40) * 2), float(5 + (k // 40) * 2)] for k in range(_GUARD_MIN + 5)], np.float32)
    edge = np.array([[96.0, 10.0], [95.0, 40.0]], np.float32)  # straddling the cliff -> steep neighbourhoods
    uv = np.concatenate([flat, edge])
    ok = _depth_ok(uv, depth)
    assert ok[: len(flat)].all()                              # flat matches kept
    assert not ok[-1] and not ok[-2]                          # edge matches dropped


def test_depth_edge_guard_falls_back_when_starved():
    """When too few matches survive the guard (< _GUARD_MIN), the plain valid mask is returned (no starvation)."""
    depth = np.full((64, 64), 2.0, np.float32)
    depth[::2, :] = 5.0                                        # alternating rows: every pixel is on a depth edge
    uv = np.array([[float(x % 64), float(x // 64 % 64)] for x in range(_GUARD_MIN - 1)], np.float32)
    ok = _depth_ok(uv, depth)
    assert ok.sum() == len(uv)                                 # guard starved -> fell back to the valid set (all in range)


def test_depth_edge_guard_drops_sensor_holes():
    depth = np.full((32, 32), 2.0, np.float32)
    depth[5, 5] = 0.0                                          # a sensor hole
    uv = np.array([[5.0, 5.0], [20.0, 20.0]], np.float32)
    ok = _depth_ok(uv, depth)
    assert not ok[0] and ok[1]


def test_count_frames_rgbd_root(tmp_path):
    """CONTRACT 1 accepts a TUM RGB-D sequence ROOT (frames under rgb/)."""
    (tmp_path / "rgb").mkdir()
    for i in range(9):
        (tmp_path / "rgb" / f"{i}.png").write_bytes(b"x")
    assert count_frames(str(tmp_path)) == 9
    assert count_frames(str(tmp_path / "rgb")) == 9         # direct folder still works