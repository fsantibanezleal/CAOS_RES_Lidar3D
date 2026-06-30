"""Geometry helpers: pose-encoding -> camera-to-world, and depth -> world point cloud.

lingbot-map emits `pose_enc` + `depth` (+ confidence), NOT a `world_points` tensor, so we
unproject depth with the per-frame intrinsics and place it in the world frame via the c2w pose.
Validated against scripts/validate_lingbot.py (sensible metric bbox + trajectory).
"""
from __future__ import annotations
import numpy as np
import torch

from lingbot_map.utils.pose_enc import pose_encoding_to_extri_intri
from lingbot_map.utils.geometry import closed_form_inverse_se3_general


def pose_enc_to_c2w_K(pose_enc: torch.Tensor, hw: tuple[int, int]) -> tuple[np.ndarray, np.ndarray]:
    """[B,S,9] -> (c2w [S,3,4] float32, K [S,3,3] float32)."""
    extr, intr = pose_encoding_to_extri_intri(pose_enc, hw)   # extr = world->cam (w2c) [B,S,3,4]
    e4 = torch.zeros((*extr.shape[:-2], 4, 4), dtype=extr.dtype, device=extr.device)
    e4[..., :3, :4] = extr
    e4[..., 3, 3] = 1.0
    c2w = closed_form_inverse_se3_general(e4)[..., :3, :4]
    return (c2w.reshape(-1, 3, 4).cpu().float().numpy(),
            intr.reshape(-1, 3, 3).cpu().float().numpy())


def unproject_depth(depth: np.ndarray, K: np.ndarray, c2w: np.ndarray,
                    rgb: np.ndarray | None = None, decimate: int = 1,
                    conf: np.ndarray | None = None, conf_thr: float | None = None
                    ) -> tuple[np.ndarray, np.ndarray]:
    """Unproject one frame's depth to world XYZ (+ optional RGB), decimated and conf-filtered.

    depth (H,W), K (3,3), c2w (3,4), rgb (H,W,3) in 0..1, conf (H,W).
    Returns (points [N,3] float32, colors [N,3] uint8).
    """
    H, W = depth.shape
    vv, uu = np.meshgrid(np.arange(H), np.arange(W), indexing="ij")
    if decimate > 1:
        uu, vv, depth = uu[::decimate, ::decimate], vv[::decimate, ::decimate], depth[::decimate, ::decimate]
        if rgb is not None:
            rgb = rgb[::decimate, ::decimate]
        if conf is not None:
            conf = conf[::decimate, ::decimate]
    fx, fy, cx, cy = K[0, 0], K[1, 1], K[0, 2], K[1, 2]
    x = (uu - cx) / fx * depth
    y = (vv - cy) / fy * depth
    cam = np.stack([x, y, depth], -1).reshape(-1, 3)
    world = cam @ c2w[:3, :3].T + c2w[:3, 3]
    cols = ((rgb.reshape(-1, 3) if rgb is not None else np.full((cam.shape[0], 3), 0.7)) * 255
            ).clip(0, 255).astype(np.uint8)
    if conf is not None and conf_thr is not None:
        keep = conf.reshape(-1) >= conf_thr
        world, cols = world[keep], cols[keep]
    # drop non-finite / zero-depth
    good = np.isfinite(world).all(1) & (np.abs(world).sum(1) > 1e-6)
    return world[good].astype(np.float32), cols[good]


def depth_to_png_b64(depth: np.ndarray, cmap: str = "turbo") -> str:
    """Small base64 PNG of a depth map for the live panel."""
    import io, base64
    import matplotlib
    matplotlib.use("Agg")
    d = depth.astype(np.float32)
    lo, hi = np.percentile(d[np.isfinite(d)], [2, 98]) if np.isfinite(d).any() else (0.0, 1.0)
    n = np.clip((d - lo) / max(hi - lo, 1e-6), 0, 1)
    rgba = (matplotlib.colormaps[cmap](n) * 255).astype(np.uint8)
    from PIL import Image
    buf = io.BytesIO()
    Image.fromarray(rgba).save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
