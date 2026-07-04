"""M-C: a differentiable WINDOWED pose-graph optimisation (the joint multi-frame step #22 is built on).

Motivation (the whole point of the exploration). Every PER-PAIR pose estimator drifts: small consecutive
errors accumulate coherently over the trajectory (measured: regression 0.28 m, correlation 0.63, DINOv2 0.61,
single-pair geometry / M-B 1.21 m). The state of the art (DROID-SLAM, DPVO, DINO-VO) fixes this with a
multi-frame bundle-adjustment / pose-graph step that jointly optimises a WINDOW of poses for global
consistency, not one pair at a time. This module is the differentiable core of that step.

Given relative-pose measurements Z_ij between frames in a window (produced per-edge by the geometric head,
including NON-consecutive skip edges) and their confidences, it solves for the absolute poses T_0..T_{N-1}
(T_0 anchored to identity) that best satisfy all the edges at once, by a few Gauss-Newton iterations. It is
fully differentiable (the GN linear solve is autograd-friendly), so the geometric head can be trained THROUGH
the window optimiser to produce measurements that are globally consistent, not just locally good.

Conventions
- A pose T_i is a 4x4 camera-i-to-world transform.
- A measurement Z_ij predicts the relative pose T_i^{-1} T_j (frame j expressed in frame i).
- Edge residual: E_ij = Z_ij^{-1} (T_i^{-1} T_j) should be identity; we use its 3x4 deviation from [I|0]
  (12 numbers) as the residual. This avoids an SE(3) log and is fully differentiable; for the small errors a
  BA operates in it is an excellent proxy for the geodesic residual and drives the poses to consistency.
- Free variables are the se(3) tangents xi_1..xi_{N-1} (xi_0 fixed = 0 anchor); T_i = se3_exp(xi_i). GN updates
  xi additively (a valid, differentiable retraction for the small steps GN takes near the solution).
"""
from __future__ import annotations

import torch

from .own_depthpose import se3_exp

_EYE34 = None


def _eye34(device, dtype):
    global _EYE34
    if _EYE34 is None or _EYE34.device != device or _EYE34.dtype != dtype:
        _EYE34 = torch.eye(4, device=device, dtype=dtype)[:3]  # [3,4] = [I|0]
    return _EYE34


def _poses_from_xi(xi_free: torch.Tensor, n: int) -> torch.Tensor:
    """xi_free: [(n-1)*6] -> absolute poses [n,4,4] with pose 0 = identity anchor."""
    xi0 = torch.zeros(1, 6, device=xi_free.device, dtype=xi_free.dtype)
    xi = torch.cat([xi0, xi_free.view(n - 1, 6)], 0)          # [n,6]
    return se3_exp(xi)                                        # [n,4,4]


def _edge_residual(xi_free: torch.Tensor, n: int, ei: torch.Tensor, ej: torch.Tensor,
                   z_inv: torch.Tensor) -> torch.Tensor:
    """Stacked 3x4 deviations E_ij - [I|0] for all edges -> [E*12]. z_inv = Z_ij^{-1} precomputed [E,4,4]."""
    t = _poses_from_xi(xi_free, n)                            # [n,4,4]
    ti_inv = torch.linalg.inv(t[ei])                         # [E,4,4]
    rel = ti_inv @ t[ej]                                      # T_i^{-1} T_j  [E,4,4]
    e = z_inv @ rel                                           # should be identity
    dev = e[:, :3, :] - _eye34(xi_free.device, xi_free.dtype)  # [E,3,4]
    return dev.reshape(-1)


def window_pgo(z_rel: torch.Tensor, edges: torch.Tensor, weight: torch.Tensor,
               n: int, iters: int = 5, damping: float = 1e-3) -> torch.Tensor:
    """Differentiable windowed pose-graph optimisation.

    z_rel:  [E,4,4] measured relative poses T_i^{-1} T_j for each edge.
    edges:  [E,2] long, the (i,j) frame indices per edge.
    weight: [E]    per-edge confidence (>=0).
    Returns absolute poses [n,4,4] (pose 0 = identity), differentiable w.r.t. z_rel + weight.
    """
    device, dtype = z_rel.device, torch.float32
    z_rel = z_rel.to(dtype)
    ei, ej = edges[:, 0], edges[:, 1]
    z_inv = torch.linalg.inv(z_rel)
    w = weight.to(dtype).clamp(min=0)
    w12 = w.repeat_interleave(12)                            # residual weight per 12-block
    xi = torch.zeros((n - 1) * 6, device=device, dtype=dtype, requires_grad=False)

    for _ in range(iters):
        def res_fn(x):
            return _edge_residual(x, n, ei, ej, z_inv)
        r = res_fn(xi)                                       # [E*12]
        # Jacobian via autograd (small: [E*12, (n-1)*6]); create_graph keeps the solve differentiable.
        j = torch.autograd.functional.jacobian(res_fn, xi, create_graph=True, vectorize=True)  # [E*12,(n-1)*6]
        jw = j * w12[:, None]
        h = jw.transpose(0, 1) @ j                           # [P,P] approx Hessian (J^T W J)
        g = jw.transpose(0, 1) @ r                           # [P] gradient (J^T W r)
        h = h + damping * torch.eye(h.shape[0], device=device, dtype=dtype)
        dx = torch.linalg.solve(h, -g)                       # GN step
        xi = xi + dx
    return _poses_from_xi(xi, n)


# ---- synthetic self-test: does the windowed PGO beat chained single-pair on a noisy window? ---------------
if __name__ == "__main__":
    torch.manual_seed(0)
    N = 6
    # a ground-truth trajectory (small random poses)
    xi_gt = torch.randn(N, 6) * 0.15
    xi_gt[0] = 0
    T_gt = se3_exp(xi_gt)                                    # [N,4,4]

    # noisy per-edge relative measurements: consecutive (i,i+1) + skip (i,i+2). This is the extra constraint a
    # window has that a pure chain does not, and is what reduces drift.
    edges = []
    for i in range(N - 1):
        edges.append((i, i + 1))
    for i in range(N - 2):
        edges.append((i, i + 2))
    edges_t = torch.tensor(edges, dtype=torch.long)
    z_clean = torch.linalg.inv(T_gt[edges_t[:, 0]]) @ T_gt[edges_t[:, 1]]
    noise = se3_exp(torch.randn(len(edges), 6) * 0.03)      # ~2 deg / 3 cm per-edge noise
    z_noisy = z_clean @ noise
    w = torch.ones(len(edges))

    # baseline: chain ONLY the consecutive noisy edges (what M-B effectively does)
    T_chain = [torch.eye(4)]
    for i in range(N - 1):
        T_chain.append(T_chain[-1] @ z_noisy[i])           # consecutive edges are the first N-1
    T_chain = torch.stack(T_chain)

    # windowed PGO over ALL edges (consecutive + skip)
    T_pgo = window_pgo(z_noisy, edges_t, w, N, iters=8)

    def traj_err(T):                                        # mean translation error vs GT (both anchored at 0)
        return (T[:, :3, 3] - T_gt[:, :3, 3]).norm(dim=1).mean().item()

    print(f"chained single-pair drift: {traj_err(T_chain):.4f} m")
    print(f"windowed PGO drift:        {traj_err(T_pgo):.4f} m")
    # differentiability check: gradient flows from the PGO output back to the measurements
    z_req = z_noisy.clone().requires_grad_(True)
    out = window_pgo(z_req, edges_t, w, N, iters=3)
    out[:, :3, 3].sum().backward()
    print(f"grad flows to measurements: {z_req.grad is not None and z_req.grad.abs().sum().item() > 0}")
