"""Track B engine: RGB + REAL SENSOR DEPTH (RGB-D) geometric reconstruction.

The lab's two-track model family: Track A is RGB-only (Estela, the lingbot pointmap reference), where the
monocular metric-scale ambiguity is the measured blocker; Track B integrates the RGB stream with a real depth
sensor (Kinect/LiDAR-class), whose depth is metric BY CONSTRUCTION, so the scale problem disappears at the source.

Method (validated 2026-07-04, wip/lidar3d/exp_sensor_depth.py: 0.034-0.098 m ATE across TUM scenes, ~3x better
than the deployed RGB-only trajectory, zero fallbacks): per consecutive pair, match SIFT keypoints on the RGB,
back-project the frame-i matches to 3D with the SENSOR depth, and solve the relative pose with PnP + RANSAC.
Chain into camera-to-world, unproject every frame's sensor depth (holes = invalid 0 are dropped), and fuse the
metric cloud. Classical, transparent, and honest: every number the sensor did not measure is absent, not invented.

Data contract: `spec.source_dir` is a TUM-format sequence root (rgb/ + depth/ + rgb.txt + depth.txt +
groundtruth.txt optional); frames are associated by nearest timestamp exactly like the training loader.
Registered as `rgbd-sensor` in the model-agnostic registry.
"""
from __future__ import annotations

import numpy as np

from ..io.schema import ReconResult, SequenceSpec
from . import geom
from .geometry import depth_to_png_b64, rgb_to_png_b64, trajectory_length

_MIN_MATCHES = 12
_MIN_INLIERS = 8


def _load_frames(spec: SequenceSpec, size: int):
    """TUM association (nearest depth timestamp per RGB), reusing the training loader's index."""
    from ..train.dataset_tum import TUMPairs
    ds = TUMPairs(spec.source_dir, image_size=size)
    frames = ds.frames[: spec.max_frames] if spec.max_frames else ds.frames
    return ds, frames


def reconstruct(spec: SequenceSpec, seed: int = 42) -> ReconResult:  # noqa: ARG001 (deterministic; seed unused)
    import cv2
    from PIL import Image

    size = 224 if spec.image_size > 448 else spec.image_size    # working resolution (PnP is stable at 224)
    ds, frames = _load_frames(spec, size)
    if len(frames) < 2:
        raise FileNotFoundError(f"no associated RGB-D frames under {spec.source_dir}")
    K = ds._K()
    n = len(frames)

    def load_rgb(fn: str) -> np.ndarray:
        im = Image.open(ds.seq_dir / fn).convert("RGB").resize((size, size), Image.BILINEAR)
        return np.asarray(im, np.float32) / 255.0

    rgbs = [load_rgb(f[0]) for f in frames]
    depths = [ds._load_depth(f[1]) for f in frames]             # SENSOR depth, metric metres, 0 = invalid

    sift = cv2.SIFT_create(nfeatures=1200)
    bf = cv2.BFMatcher(cv2.NORM_L2)
    feats = [sift.detectAndCompute(cv2.cvtColor((r * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY), None)
             for r in rgbs]

    def rel_pose(i: int) -> np.ndarray | None:
        """Relative pose (frame i+1 expressed in frame i) via SIFT + sensor-depth PnP RANSAC."""
        (ki, di), (kj, dj) = feats[i], feats[i + 1]
        if di is None or dj is None or len(ki) < _MIN_MATCHES or len(kj) < _MIN_MATCHES:
            return None
        good = [m for m, nn in bf.knnMatch(di, dj, k=2) if m.distance < 0.75 * nn.distance]
        if len(good) < _MIN_MATCHES:
            return None
        uv_i = np.float32([ki[m.queryIdx].pt for m in good])
        uv_j = np.float32([kj[m.trainIdx].pt for m in good])
        d = depths[i]
        u = np.clip(uv_i[:, 0].round().astype(int), 0, d.shape[1] - 1)
        v = np.clip(uv_i[:, 1].round().astype(int), 0, d.shape[0] - 1)
        z = d[v, u]
        ok = (z > 0.1) & (z < 8.0)                              # sensor holes (0) + far range are invalid
        if ok.sum() < _MIN_INLIERS:
            return None
        p3d = np.stack([(uv_i[:, 0] - K[0, 2]) / K[0, 0] * z,
                        (uv_i[:, 1] - K[1, 2]) / K[1, 1] * z, z], 1).astype(np.float32)
        found, rvec, tvec, inl = cv2.solvePnPRansac(p3d[ok], uv_j[ok], K, None, reprojectionError=3.0,
                                                    iterationsCount=200, confidence=0.999)
        if not found or inl is None or len(inl) < _MIN_INLIERS:
            return None
        R, _ = cv2.Rodrigues(rvec)
        T = np.eye(4)
        T[:3, :3] = R
        T[:3, 3] = tvec[:, 0]                                   # cam_i -> cam_j
        rel = np.linalg.inv(T)                                  # cam_j in cam_i, like the model's rel_pose
        return rel if np.isfinite(rel).all() else None

    c2ws = [np.eye(4)]
    fallbacks = 0
    for i in range(n - 1):
        rel = rel_pose(i)
        if rel is None:                                          # rare (0 in validation); hold pose rather than invent
            rel = np.eye(4)
            fallbacks += 1
        c2ws.append(c2ws[-1] @ rel)

    poses = [c2w[:3, :4].reshape(-1).astype(np.float32) for c2w in c2ws]
    centers = [c2w[:3, 3].astype(np.float32) for c2w in c2ws]

    # fuse: unproject every frame's SENSOR depth at its solved pose. Holes stay holes (honest); the sensor's own
    # validity IS the confidence, so no learned-confidence quantile is applied.
    all_p, all_c, per_frame, dth, rth = [], [], [], [], []
    for i in range(n):
        p, c = geom.unproject(depths[i], K, c2ws[i], rgb=rgbs[i], decimate=max(1, spec.decimation),
                              max_depth=spec.max_render_depth if spec.max_render_depth > 0 else 6.0)
        all_p.append(p)
        all_c.append(c)
        valid = depths[i] > 0
        per_frame.append({"idx": i, "conf_mean": float(valid.mean()), "n_points": int(len(p)),
                          "depth_min": float(depths[i][valid].min()) if valid.any() else 0.0,
                          "depth_max": float(depths[i].max())})
        if i % max(1, n // 48) == 0 or i == n - 1:
            dth.append({"idx": i, "png_b64": depth_to_png_b64(depths[i])})
            rth.append({"idx": i, "png_b64": rgb_to_png_b64(rgbs[i])})

    pts = np.concatenate(all_p).astype(np.float32)
    cols = np.concatenate(all_c).astype(np.uint8)
    if fallbacks:
        print(f"  [rgbd-sensor] {fallbacks}/{n - 1} pairs had too few valid matches (pose held)")
    return ReconResult(
        case_id=spec.case_id, n_frames=n, poses_c2w=np.asarray(poses, np.float32),
        points=pts, colors=cols, per_frame=per_frame,
        path_length=trajectory_length(np.asarray(centers, np.float32)),
        bbox_min=pts.min(0).tolist(), bbox_max=pts.max(0).tolist(), depth_thumbs=dth, rgb_thumbs=rth,
    )
