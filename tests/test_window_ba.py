"""M-C windowed pose-graph optimiser (#22): it must reduce trajectory drift vs chaining single-pair estimates
AND be differentiable (so the geometric head can be trained THROUGH it).

torch is the local-GPU dependency and is NOT in the CI offline lane, so skip this module there (it still runs
in the local .venv where the model + training live)."""
import pytest

pytest.importorskip("torch")

import torch  # noqa: E402

from lidar3dlab.model.nets.own_depthpose import se3_exp  # noqa: E402
from lidar3dlab.model.nets.window_ba import WindowDepthPose, window_edges, window_pgo  # noqa: E402


def _window(n, gt_scale=0.15, noise=0.03, seed=0):
    torch.manual_seed(seed)
    xi_gt = torch.randn(n, 6) * gt_scale
    xi_gt[0] = 0
    t_gt = se3_exp(xi_gt)
    edges = [(i, i + 1) for i in range(n - 1)] + [(i, i + 2) for i in range(n - 2)]
    et = torch.tensor(edges, dtype=torch.long)
    z_clean = torch.linalg.inv(t_gt[et[:, 0]]) @ t_gt[et[:, 1]]
    z_noisy = z_clean @ se3_exp(torch.randn(len(edges), 6) * noise)
    return t_gt, et, z_noisy


def test_windowed_pgo_reduces_drift_vs_chaining():
    n = 6
    t_gt, et, z_noisy = _window(n)
    # baseline: chain ONLY the consecutive noisy edges (what a per-pair estimator effectively does)
    chain = [torch.eye(4)]
    for i in range(n - 1):
        chain.append(chain[-1] @ z_noisy[i])
    t_chain = torch.stack(chain)
    t_pgo = window_pgo(z_noisy, et, torch.ones(len(et)), n, iters=8)

    def drift(t):
        return (t[:, :3, 3] - t_gt[:, :3, 3]).norm(dim=1).mean().item()

    # the joint window solve (with the non-consecutive skip edges) must cut drift meaningfully
    assert drift(t_pgo) < 0.75 * drift(t_chain)


def test_windowed_pgo_is_differentiable():
    n = 4
    _, et, z = _window(n, seed=1)
    z = z.clone().requires_grad_(True)
    out = window_pgo(z, et, torch.ones(len(et)), n, iters=3)
    out[:, :3, 3].sum().backward()
    assert z.grad is not None and z.grad.abs().sum().item() > 0


def test_window_edges_are_valid_ordered_pairs():
    """Regression: window_edges must emit (i, i+j) frame pairs, not (i, distance). Every edge connects two
    DISTINCT frames i<j inside the window with j-i in 1..skip (no self-edges), covering the consecutive chain
    plus the skip edges."""
    e = [tuple(p) for p in window_edges(6, skip=2).tolist()]
    assert all(0 <= i < j < 6 and 1 <= j - i <= 2 for i, j in e)
    assert {(0, 1), (1, 2), (2, 3), (3, 4), (4, 5)} <= set(e)          # consecutive chain
    assert {(0, 2), (1, 3), (2, 4), (3, 5)} <= set(e)                  # skip-2 constraints
    assert len(e) == 9 and len(set(e)) == 9                            # 5 consecutive + 4 skip, no dupes


def test_measure_supervision_backward_is_finite():
    """The M-C training pivot (#22): supervising the per-edge measurements DIRECTLY (measure_edges + a
    relative-pose loss) gives a finite FIRST-ORDER backward from a fresh, untrained model, unlike
    back-propagating through window_pgo with an untrained head (a degenerate second-order solve that went NaN).
    This guards that the trainer's loss path stays finite."""
    torch.manual_seed(0)
    model = WindowDepthPose(backbone="resnet18", base=32, pretrained=False, iters=3)
    n = 4
    rgbs = torch.rand(n, 3, 64, 64)
    k = torch.tensor([[80.0, 0, 32], [0, 80.0, 32], [0, 0, 1]])
    edges = window_edges(n, skip=2)
    m = model.measure_edges(rgbs, k, edges)
    loss = m["z_rel"][:, :3, 3].abs().mean() + m["z_rel"][:, :3, :3].pow(2).mean() + m["depth"].mean()
    loss.backward()
    grads = [p.grad for p in model.parameters() if p.grad is not None]
    assert grads and all(torch.isfinite(g).all() for g in grads)
