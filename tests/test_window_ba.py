"""M-C windowed pose-graph optimiser (#22): it must reduce trajectory drift vs chaining single-pair estimates
AND be differentiable (so the geometric head can be trained THROUGH it)."""
import torch

from lidar3dlab.model.nets.own_depthpose import se3_exp
from lidar3dlab.model.nets.window_ba import window_pgo


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
