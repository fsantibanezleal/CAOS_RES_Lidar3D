"""Pure-NumPy geometry shared by the engines: unproject a depth map (with intrinsics + camera-to-world pose)
into a world-frame RGB point cloud, and trajectory helpers. No torch / no lingbot import here, so the
synthetic CPU lane and the tests stay light. Validated against the lingbot streaming output (2026-06-29).
"""
from __future__ import annotations

import numpy as np


def unproject_depth(depth: np.ndarray, K: np.ndarray, c2w: np.ndarray,
                    rgb: np.ndarray | None = None, decimate: int = 1,
                    conf: np.ndarray | None = None, conf_thr: float | None = None
                    ) -> tuple[np.ndarray, np.ndarray]:
    """depth (H,W), K (3,3), c2w (3,4), rgb (H,W,3) in 0..1 -> (points [N,3] f32, colors [N,3] u8)."""
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
    good = np.isfinite(world).all(1) & (np.abs(world).sum(1) > 1e-6)
    return world[good].astype(np.float32), cols[good]


def trajectory_length(centers: np.ndarray) -> float:
    if len(centers) < 2:
        return 0.0
    return float(np.linalg.norm(np.diff(centers, axis=0), axis=1).sum())


def depth_to_png_b64(depth: np.ndarray, cmap: str = "turbo") -> str:
    """Small base64 PNG of a depth map for the live/replay panel (a few keyframes only)."""
    import base64
    import io

    import matplotlib
    matplotlib.use("Agg")
    from PIL import Image
    d = depth.astype(np.float32)
    finite = np.isfinite(d)
    lo, hi = (np.percentile(d[finite], [2, 98]) if finite.any() else (0.0, 1.0))
    n = np.clip((d - lo) / max(hi - lo, 1e-6), 0, 1)
    rgba = (matplotlib.colormaps[cmap](n) * 255).astype(np.uint8)
    buf = io.BytesIO()
    Image.fromarray(rgba).save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
