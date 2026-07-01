"""Synthetic CPU reconstruction engine (no GPU, no model) — a procedural corridor flythrough.

Used by the `synthetic` cases: it exercises the SAME per-frame-depth -> unproject -> fuse path as the real
lingbot engine (so the pipeline, contracts, gate, export and the web replay are identical), but runs in
milliseconds on CPU. That makes the pipeline CI-testable without the 4.6 GB model or a GPU, and gives the
App's "Synthetic" source a real (procedural) reconstruction with genuine color/texture, not a fake.
Deterministic given the seed.
"""
from __future__ import annotations

import numpy as np

from ..io.schema import ReconResult, SequenceSpec
from .geometry import depth_to_png_b64, trajectory_length, unproject_depth

_H, _W = 96, 128


def _intrinsics() -> np.ndarray:
    f = 0.95 * max(_H, _W)
    return np.array([[f, 0, _W / 2], [0, f, _H / 2], [0, 0, 1]], np.float64)


def _frame_depth_rgb(t: float) -> tuple[np.ndarray, np.ndarray]:
    """A textured tunnel: depth deep at the vanishing point, near at the edges; walls carry a checker +
    angular color gradient so the cloud is genuinely colored/textured."""
    vv, uu = np.meshgrid(np.arange(_H), np.arange(_W), indexing="ij")
    nx, ny = (uu - _W / 2) / (_W / 2), (vv - _H / 2) / (_H / 2)
    r = np.sqrt(nx ** 2 + ny ** 2).clip(0, 1.4)
    depth = (0.6 + 3.4 * (1.0 - r / 1.4)).astype(np.float32)
    ang = np.arctan2(ny, nx)
    checker = ((np.floor((ang + np.pi) / (np.pi / 6)) + np.floor(depth * 2.0)) % 2).astype(np.float32)
    base = np.stack([0.45 + 0.40 * np.cos(ang + t),
                     0.45 + 0.40 * np.sin(ang * 1.3 - t * 0.5),
                     0.50 + 0.30 * np.cos(depth * 1.5)], -1)
    rgb = (base * (0.65 + 0.35 * checker[..., None])).clip(0, 1).astype(np.float32)
    return depth, rgb


def reconstruct(spec: SequenceSpec, seed: int = 42) -> ReconResult:
    rng = np.random.default_rng(seed)
    S = int(max(8, min(spec.max_frames, 48)))
    K = _intrinsics()
    dec = max(2, spec.decimation // 2)
    all_p, all_c, per_frame, centers, poses, thumbs = [], [], [], [], [], []
    jitter = rng.normal(0, 0.01, size=(S, 2))
    for i in range(S):
        # the camera looks +Z (OpenCV convention, same as the real engine) and MOVES +Z into the corridor it is
        # imaging, so the reconstruction accumulates AHEAD of the motion (not behind it).
        z = 0.14 * i
        c2w = np.array([[1, 0, 0, 0.05 * np.sin(i * 0.3) + jitter[i, 0]],
                        [0, 1, 0, 0.03 * np.cos(i * 0.4) + jitter[i, 1]],
                        [0, 0, 1, z]], np.float64)
        depth, rgb = _frame_depth_rgb(i * 0.12)
        p, c = unproject_depth(depth, K, c2w, rgb, decimate=dec)
        all_p.append(p)
        all_c.append(c)
        centers.append(c2w[:, 3])
        poses.append(c2w[:3, :4].reshape(-1).astype(np.float32))
        per_frame.append({"idx": i, "conf_mean": 1.0, "n_points": int(len(p)),
                          "depth_min": float(depth.min()), "depth_max": float(depth.max())})
        if i % max(1, S // 4) == 0:
            thumbs.append({"idx": i, "png_b64": depth_to_png_b64(depth)})
    pts = np.concatenate(all_p).astype(np.float32)
    cols = np.concatenate(all_c).astype(np.uint8)
    centers = np.asarray(centers, np.float32)
    return ReconResult(
        case_id=spec.case_id, n_frames=S, poses_c2w=np.asarray(poses, np.float32),
        points=pts, colors=cols, per_frame=per_frame,
        path_length=trajectory_length(centers),
        bbox_min=pts.min(0).tolist(), bbox_max=pts.max(0).tolist(), depth_thumbs=thumbs,
    )
