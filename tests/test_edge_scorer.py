"""E4 edge-scorer units: feature vector shape/determinism, chain-gap geometry on constructed
poses, GT-label geometry, and the weight mapping's monotonicity (higher predicted error must
never get a higher weight)."""
import numpy as np

from lidar3dlab.model.edge_scorer import (
    N_FEAT, EdgeScorer, base_features, build_net, chain_gap, relpose_error,
)


def _pose(t, axis_angle_z=0.0):
    T = np.eye(4)
    c, s = np.cos(axis_angle_z), np.sin(axis_angle_z)
    T[:3, :3] = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])
    T[:3, 3] = t
    return T


def test_base_features_shape_and_determinism():
    rng = np.random.default_rng(0)
    uv_i = rng.uniform(0, 224, (100, 2)).astype(np.float32)
    uv_j = uv_i + rng.normal(0, 2, (100, 2)).astype(np.float32)
    kept = rng.random(100) > 0.3
    z = rng.uniform(0.5, 5.0, int(kept.sum())).astype(np.float32)
    rough = rng.uniform(0, 0.05, int(kept.sum())).astype(np.float32)
    a = base_features(uv_i, uv_j, kept, z, rough, 40, int(kept.sum()), 224, 1)
    b = base_features(uv_i, uv_j, kept, z, rough, 40, int(kept.sum()), 224, 1)
    assert a.shape == (N_FEAT,)
    np.testing.assert_array_equal(a, b)
    assert a[9] == 0.0 and a[10] == 0.0, "chain gaps belong to the window logic"


def test_chain_gap_zero_for_consistent_chain():
    e01 = _pose([0.1, 0, 0])
    e12 = _pose([0.1, 0, 0], 0.05)
    z02 = e01 @ e12
    gt, gr = chain_gap(z02, [e01, e12])
    assert gt < 1e-9 and gr < 1e-9


def test_chain_gap_detects_deviation():
    e01 = _pose([0.1, 0, 0])
    e12 = _pose([0.1, 0, 0])
    z02 = _pose([0.35, 0, 0], 0.1)   # measured edge disagrees with the composed chain
    gt, gr = chain_gap(z02, [e01, e12])
    assert abs(gt - 0.15) < 1e-6
    assert abs(gr - 0.1) < 1e-6


def test_chain_gap_missing_edge_is_absent_not_invented():
    assert chain_gap(_pose([0.2, 0, 0]), [_pose([0.1, 0, 0]), None]) == (0.0, 0.0)


def test_relpose_error_geometry():
    gt = _pose([1.0, 0, 0])
    z = _pose([1.0, 0.2, 0], 0.1)
    err_t, err_r = relpose_error(z, gt)
    assert abs(err_r - 0.1) < 1e-6
    assert 0.19 < err_t < 0.21


def test_weight_mapping_monotone():
    import torch

    net = build_net()
    torch.manual_seed(0)
    mean = np.zeros(N_FEAT, np.float32)
    std = np.ones(N_FEAT, np.float32)
    scorer = EdgeScorer(net, mean, std, alpha=2.0)
    feats = np.random.default_rng(1).normal(0, 1, (32, N_FEAT)).astype(np.float32)
    w = scorer.weights(feats)
    assert w.shape == (32,) and (w > 0).all() and (w <= 1.0 + 1e-6).all()
    with torch.no_grad():
        pred = net(torch.from_numpy(feats)).numpy()[:, 0]
    order_err = np.argsort(pred)
    assert (np.diff(w[order_err]) <= 1e-9).all(), "higher predicted error must never weigh more"
