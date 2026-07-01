"""OUR own geometry: the single source of truth for camera math across every engine (no vendored dependency).

ONE convention, used everywhere:
  - Camera looks along +Z (OpenCV / computer-vision convention), image x right (+u), image y down (+v).
  - Depth D(u,v) is the metric distance along the camera +Z axis (D > 0 is IN FRONT of the camera).
  - A pose is camera-to-world (c2w): world = R_c2w @ p_cam + t_c2w. The camera CENTER in the world is t_c2w;
    the camera FORWARD (viewing direction) in the world is the third column of R_c2w (its +Z axis).

Keeping this convention in one tested module is what makes the classic "the reconstruction is built behind the
camera / it moves backward" bug impossible: `test_geom.py` reconstructs a known ground-truth cube and asserts the
world points come back where they started AND that the camera forward points toward the scene.
"""
from __future__ import annotations

import numpy as np

Array = np.ndarray


def intrinsics(fx: float, fy: float, cx: float, cy: float) -> Array:
    return np.array([[fx, 0.0, cx], [0.0, fy, cy], [0.0, 0.0, 1.0]], np.float64)


def intrinsics_from_fov(width: int, height: int, hfov_deg: float) -> Array:
    """Pinhole K from a horizontal field of view (self-calibration analogue)."""
    fx = (width / 2.0) / np.tan(np.radians(hfov_deg) / 2.0)
    return intrinsics(fx, fx, width / 2.0, height / 2.0)


def invert_se3(c2w: Array) -> Array:
    """Inverse of a 3x4 or 4x4 SE(3). world<->camera. R^-1 = R^T; t' = -R^T t."""
    R = c2w[:3, :3]
    t = c2w[:3, 3]
    out = np.eye(4, dtype=np.float64)
    out[:3, :3] = R.T
    out[:3, 3] = -R.T @ t
    return out


def look_at(eye: Array, target: Array, up: Array | None = None) -> Array:
    """A camera-to-world pose whose +Z axis points from `eye` toward `target` (so it LOOKS at the target).
    up defaults to -Y (image-up), matching the +Y-down image convention."""
    eye = np.asarray(eye, np.float64)
    target = np.asarray(target, np.float64)
    up = np.array([0.0, -1.0, 0.0]) if up is None else np.asarray(up, np.float64)
    z = target - eye
    z = z / max(np.linalg.norm(z), 1e-12)          # camera forward = +Z toward the target
    x = np.cross(up, z)
    x = x / max(np.linalg.norm(x), 1e-12)          # right = +X
    y = np.cross(z, x)                             # down = +Y
    c2w = np.eye(4, dtype=np.float64)
    c2w[:3, 0] = x
    c2w[:3, 1] = y
    c2w[:3, 2] = z
    c2w[:3, 3] = eye
    return c2w


def unproject(depth: Array, K: Array, c2w: Array, rgb: Array | None = None, decimate: int = 1,
              conf: Array | None = None, conf_thr: float | None = None) -> tuple[Array, Array]:
    """depth (H,W) metric-along-+Z, K (3,3), c2w (3x4 or 4x4) -> (world points [N,3] f32, colors [N,3] u8).

    A pixel (u,v) with depth D maps to the camera-frame point ((u-cx)/fx*D, (v-cy)/fy*D, D) and then to the
    world by the camera-to-world pose. Points with D<=0 or non-finite are dropped. Deterministic."""
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
    R = c2w[:3, :3]
    t = c2w[:3, 3]
    world = cam @ R.T + t                                   # world = R_c2w p_cam + t_c2w
    cols = ((rgb.reshape(-1, 3) if rgb is not None else np.full((cam.shape[0], 3), 0.7)) * 255
            ).clip(0, 255).astype(np.uint8)
    keep = np.isfinite(world).all(1) & (depth.reshape(-1) > 1e-6)
    if conf is not None and conf_thr is not None:
        keep &= conf.reshape(-1) >= conf_thr
    return world[keep].astype(np.float32), cols[keep]


def project(world: Array, K: Array, c2w: Array) -> tuple[Array, Array]:
    """Inverse of `unproject` for a set of world points: -> (pixels [N,2], depth [N]). For tests/loop-closure."""
    w2c = invert_se3(c2w)
    cam = world @ w2c[:3, :3].T + w2c[:3, 3]
    d = cam[:, 2]
    uv = (cam[:, :2] / np.clip(d[:, None], 1e-9, None)) * np.array([K[0, 0], K[1, 1]]) + np.array([K[0, 2], K[1, 2]])
    return uv, d


def trajectory_length(centers: Array) -> float:
    centers = np.asarray(centers, np.float64)
    if len(centers) < 2:
        return 0.0
    return float(np.linalg.norm(np.diff(centers, axis=0), axis=1).sum())


def camera_forward(c2w: Array) -> Array:
    """The world-space viewing direction (+Z axis of the camera). Data should accumulate along +this."""
    return c2w[:3, 2] / max(np.linalg.norm(c2w[:3, 2]), 1e-12)
