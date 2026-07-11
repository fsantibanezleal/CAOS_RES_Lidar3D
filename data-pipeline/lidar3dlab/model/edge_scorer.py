"""E4 pose-edge scorer (croquis ladder E4, design persisted in the management repo 2026-07-11).

A tiny supervised MLP that predicts the relative-pose ERROR of a Track B PnP edge from cheap
per-edge features, so the windowed pose-graph fusion can weight edges by PREDICTED QUALITY
instead of the raw PnP inlier count. Evidence chain this stands on (probe I1, 2026-07-06):
window_pgo multiplies edge consistency (+7-26 pct on metric-consistent edges) but cannot fix a
bad front end; the depth-edge guard (+16-51 pct) was a zero-learning edge-quality win; the
learned MATCHER was an isolated win and a deployed wash. The scorer targets the same surface as
the guard (edge quality) with supervision, and its ship rule is END-TO-END (eval_edge_scorer).

Feature vector (N_FEAT, fixed order; every entry computable in the engine at inference and in
the future croquis station PGO; the Siamese descriptor-distance feature of the design dossier
is deliberately OMITTED here: it is matcher-specific and the record documents the omission):

  0 raw match count / 500          (ratio-test survivors)
  1 guard-survivor ratio           (depth-edge guard kept / raw)
  2 PnP inlier ratio               (inliers / PnP input matches)
  3 PnP inlier count / 300
  4 match spatial spread           (std(u) * std(v) / size^2, frame-i kept matches)
  5 mean parallax / size           (mean |uv_j - uv_i| of kept matches)
  6 mean local depth roughness     (mean |z_neighbour - z| at kept matches / guard threshold)
  7 median match depth / 8 m
  8 skip distance                  (j - i - 1: 0 consecutive, 1+ skip edges)
  9 chain-gap translation (m)      (edge measurement vs composed consecutive edges; 0 when n/a)
 10 chain-gap rotation (rad)       (same, geodesic; 0 when n/a)

Target: log1p(err_t + err_r_rad), the GT relative-pose error with a 1 m lever-arm equivalence
between translation metres and rotation radians (stated, not tuned). Weight mapping:
w = exp(-alpha * expm1(pred)), alpha calibrated on the scorer's validation split at export.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np

N_FEAT = 11


def base_features(uv_i: np.ndarray, uv_j: np.ndarray, kept: np.ndarray, z_kept: np.ndarray,
                  rough_kept: np.ndarray, inliers: int, pnp_in: int, size: int, skip: int) -> np.ndarray:
    """Features 0..8 from quantities the PnP front-end already has in hand. `kept` is the
    _depth_ok mask over raw matches; z_kept / rough_kept are sensor depth + local roughness at
    the kept matches; pnp_in is the match count PnP actually consumed."""
    raw = max(len(uv_i), 1)
    ui, vi = uv_i[kept, 0], uv_i[kept, 1]
    spread = float(ui.std() * vi.std()) / float(size * size) if kept.sum() >= 2 else 0.0
    parallax = float(np.linalg.norm(uv_j[kept] - uv_i[kept], axis=1).mean()) / size if kept.any() else 0.0
    out = np.zeros(N_FEAT, np.float32)
    out[0] = raw / 500.0
    out[1] = float(kept.sum()) / raw
    out[2] = inliers / max(pnp_in, 1)
    out[3] = inliers / 300.0
    out[4] = spread
    out[5] = parallax
    out[6] = float(rough_kept.mean()) / 0.10 if rough_kept.size else 0.0
    out[7] = float(np.median(z_kept)) / 8.0 if z_kept.size else 0.0
    out[8] = float(skip)
    return out


def chain_gap(z_edge: np.ndarray, consecutive: list[np.ndarray | None]) -> tuple[float, float]:
    """Features 9/10: how far the edge measurement deviates from the composition of the window's
    consecutive measurements over the same span (the consistency window_pgo exploits). Returns
    (0, 0) when any consecutive edge in the span is missing (honesty: absent, not invented)."""
    comp = np.eye(4)
    for c in consecutive:
        if c is None:
            return 0.0, 0.0
        comp = comp @ c
    err = np.linalg.inv(z_edge) @ comp
    gap_t = float(np.linalg.norm(err[:3, 3]))
    cos = (np.trace(err[:3, :3]) - 1.0) / 2.0
    gap_r = float(np.arccos(np.clip(cos, -1.0, 1.0)))
    return gap_t, gap_r


def relpose_error(z_edge: np.ndarray, gt_rel: np.ndarray) -> tuple[float, float]:
    """GT label: translation (m) and rotation (rad) error of a measured edge vs the GT relative
    pose (both cam_j-in-cam_i)."""
    err = np.linalg.inv(gt_rel) @ z_edge
    err_t = float(np.linalg.norm(err[:3, 3]))
    cos = (np.trace(err[:3, :3]) - 1.0) / 2.0
    return err_t, float(np.arccos(np.clip(cos, -1.0, 1.0)))


def build_net():
    """The 2x64 MLP (about 5k params). torch import stays local: the engine is torch-optional."""
    import torch.nn as nn

    return nn.Sequential(nn.Linear(N_FEAT, 64), nn.ReLU(), nn.Linear(64, 64), nn.ReLU(), nn.Linear(64, 1))


class EdgeScorer:
    """Inference wrapper: features [E, N_FEAT] -> per-edge weights in (0, 1]."""

    def __init__(self, net, mean: np.ndarray, std: np.ndarray, alpha: float) -> None:
        self._net = net
        self._mean = mean
        self._std = std
        self.alpha = alpha

    def weights(self, feats: np.ndarray) -> np.ndarray:
        import torch

        x = (feats.astype(np.float32) - self._mean) / self._std
        with torch.no_grad():
            pred = self._net(torch.from_numpy(x)).numpy()[:, 0]
        return np.exp(-self.alpha * np.expm1(np.clip(pred, 0.0, 10.0))).astype(np.float32)


def scorer_path() -> Path:
    from ..config import MODELS_ROOT

    return Path(MODELS_ROOT) / "edge-scorer" / "edge_scorer.pt"


def load_scorer() -> EdgeScorer | None:
    """Load the exported scorer iff LIDAR3D_EDGE_SCORER enables it ("1" or a checkpoint path).
    Returns None (engine keeps its inlier-count weights) when disabled, absent, or torch-less."""
    flag = os.environ.get("LIDAR3D_EDGE_SCORER", "")
    if not flag or flag == "0":
        return None
    try:
        import torch
    except Exception:  # noqa: BLE001 (torch-optional engine discipline)
        return None
    path = scorer_path() if flag == "1" else Path(flag)
    if not path.exists():
        return None
    ck = torch.load(str(path), map_location="cpu", weights_only=True)
    net = build_net()
    net.load_state_dict(ck["model"])
    net.eval()
    meta = ck["meta"]
    return EdgeScorer(net, np.asarray(meta["mean"], np.float32), np.asarray(meta["std"], np.float32),
                      float(meta["alpha"]))


def save_scorer(path: Path, net, mean: np.ndarray, std: np.ndarray, alpha: float, report: dict) -> None:
    import torch

    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save({"model": net.state_dict(),
                "meta": {"mean": mean.tolist(), "std": std.tolist(), "alpha": alpha, "n_feat": N_FEAT}}, str(path))
    path.with_suffix(".meta.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
