"""LiDAR odometry engine — the second modality that makes "Lidar 3D" honest (the camera engines reconstruct
LiDAR-LIKE clouds from video; this one consumes actual LiDAR scans).

Frame-to-frame registration with Open3D point-to-plane ICP (a real, standard point-cloud registration
engine), accumulating a registered, height-colored map + the odometry trajectory. KISS-ICP (the SOTA
LiDAR-only odometry) is pinned in requirements and swappable behind this same interface.

A `synthetic` LiDAR case builds scans procedurally (CI-safe, CPU, no dataset); a real case reads a folder of
`.bin`/`.npy`/`.ply` scans (resolved via LIDAR3D_DATA_ROOT). Deterministic given the seed.
"""
from __future__ import annotations

import glob
import os

import numpy as np

from ..io.schema import ReconResult, SequenceSpec
from .geometry import trajectory_length


def _corridor_world(rng: np.random.Generator) -> np.ndarray:
    """A simple corridor (two walls, floor, ceiling) as a dense world cloud."""
    n = 9000
    L, W, H = 18.0, 2.2, 2.6
    pts = []
    z = rng.uniform(0, L, n)
    for sign in (-1, 1):                       # side walls
        y = rng.uniform(-H / 2, H / 2, n // 3)
        pts.append(np.stack([np.full(n // 3, sign * W / 2), y, rng.uniform(0, L, n // 3)], 1))
    x = rng.uniform(-W / 2, W / 2, n // 3)      # floor + ceiling
    pts.append(np.stack([x, np.full(n // 3, H / 2), rng.uniform(0, L, n // 3)], 1))
    pts.append(np.stack([x, np.full(n // 3, -H / 2), rng.uniform(0, L, n // 3)], 1))
    _ = z
    return np.concatenate(pts).astype(np.float64)


def _height_colors(pts: np.ndarray) -> np.ndarray:
    import matplotlib
    y = pts[:, 1]
    n = (y - y.min()) / max(float(np.ptp(y)), 1e-6)
    return (matplotlib.colormaps["turbo"](n)[:, :3] * 255).astype(np.uint8)


def _range_png(scan: np.ndarray, h: int = 48, w: int = 160) -> str:
    """A per-scan spherical RANGE image (azimuth x elevation -> nearest range), turbo-colored, as a base64 PNG.
    This is the LiDAR analogue of a per-frame depth image, so the App's per-frame Depth view always exists."""
    import base64
    import io

    import matplotlib
    from PIL import Image
    p = np.asarray(scan, np.float64)
    r = np.linalg.norm(p, axis=1)
    good = r > 1e-3
    p, r = p[good], r[good]
    img = np.full((h, w), np.inf)
    if len(r):
        az = np.arctan2(p[:, 0], p[:, 2])                       # forward = +z
        el = np.arcsin(np.clip(p[:, 1] / r, -1, 1))
        ui = ((az + np.pi) / (2 * np.pi) * (w - 1)).astype(int).clip(0, w - 1)
        vi = ((el + np.pi / 2) / np.pi * (h - 1)).astype(int).clip(0, h - 1)
        order = np.argsort(-r)                                  # far first, so the nearest range wins per cell
        img[vi[order], ui[order]] = r[order]
    finite = np.isfinite(img)
    lo, hi = (np.percentile(img[finite], [2, 98]) if finite.any() else (0.0, 1.0))
    n = np.where(finite, np.clip((img - lo) / max(hi - lo, 1e-6), 0, 1), 0.0)
    rgba = (matplotlib.colormaps["turbo"](n) * 255).astype(np.uint8)
    rgba[~finite] = [12, 16, 32, 255]
    buf = io.BytesIO()
    Image.fromarray(rgba).save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def _synthetic_scans(spec: SequenceSpec, seed: int) -> tuple[list[np.ndarray], np.ndarray]:
    """Per-pose LiDAR scans (the corridor seen from a forward-moving sensor) + the ground-truth path."""
    rng = np.random.default_rng(seed)
    world = _corridor_world(rng)
    S = int(max(6, min(spec.max_frames, 90)))
    gt = np.stack([0.04 * np.sin(np.arange(S) * 0.3),
                   0.02 * np.cos(np.arange(S) * 0.4),
                   np.linspace(0, 9.0, S)], 1)            # forward 9 m
    scans = []
    for i in range(S):
        local = world - gt[i]                              # sensor-frame points
        rng_local = np.random.default_rng(seed + i)
        keep = (np.linalg.norm(local, axis=1) < 12.0)      # range limit
        sc = local[keep]
        idx = rng_local.choice(len(sc), min(2600, len(sc)), replace=False)
        scans.append((sc[idx] + rng_local.normal(0, 0.01, (len(idx), 3))).astype(np.float64))
    return scans, gt


def _real_scans(spec: SequenceSpec) -> tuple[list[np.ndarray], None]:
    paths = sorted(sum([glob.glob(os.path.join(spec.source_dir, f"*{e}")) for e in (".bin", ".npy", ".ply", ".pcd")], []))
    paths = paths[:spec.max_frames]
    if not paths:
        raise FileNotFoundError(f"no LiDAR scans in {spec.source_dir}")
    import open3d as o3d
    scans = []
    for p in paths:
        if p.endswith(".bin"):
            sc = np.fromfile(p, np.float32).reshape(-1, 4)[:, :3].astype(np.float64)  # KITTI velodyne
        elif p.endswith(".npy"):
            sc = np.load(p)[:, :3].astype(np.float64)
        else:
            sc = np.asarray(o3d.io.read_point_cloud(p).points)
        scans.append(sc)
    return scans, None


def _icp(src: np.ndarray, tgt: np.ndarray, init: np.ndarray, voxel: float) -> np.ndarray:
    import open3d as o3d
    s = o3d.geometry.PointCloud()
    s.points = o3d.utility.Vector3dVector(src)
    t = o3d.geometry.PointCloud()
    t.points = o3d.utility.Vector3dVector(tgt)
    s = s.voxel_down_sample(voxel)
    t = t.voxel_down_sample(voxel)
    t.estimate_normals(o3d.geometry.KDTreeSearchParamHybrid(radius=voxel * 3, max_nn=20))
    reg = o3d.pipelines.registration.registration_icp(
        s, t, voxel * 2.5, init,
        o3d.pipelines.registration.TransformationEstimationPointToPlane(),
        o3d.pipelines.registration.ICPConvergenceCriteria(max_iteration=30))
    return reg.transformation


def reconstruct(spec: SequenceSpec, seed: int = 42) -> ReconResult:
    scans, _gt = _synthetic_scans(spec, seed) if spec.synthetic else _real_scans(spec)
    voxel = 0.18
    poses = [np.eye(4)]
    for i in range(1, len(scans)):
        rel = _icp(scans[i], scans[i - 1], np.eye(4), voxel)   # scan_i -> scan_{i-1}
        poses.append(poses[-1] @ rel)
    # accumulate the registered, decimated, height-colored map
    all_p, per_frame, centers, dth = [], [], [], []
    for i, (sc, P) in enumerate(zip(scans, poses)):
        w = sc @ P[:3, :3].T + P[:3, 3]
        dec = max(1, len(w) // 1500)
        all_p.append(w[::dec])
        centers.append(P[:3, 3])
        per_frame.append({"idx": i, "conf_mean": 1.0, "n_points": int(len(w[::dec])),
                          "depth_min": float(np.linalg.norm(sc, axis=1).min()),
                          "depth_max": float(np.linalg.norm(sc, axis=1).max())})
        if i % max(1, len(scans) // 48) == 0 or i == len(scans) - 1:  # ~48 keyframe range images for the panel
            dth.append({"idx": i, "png_b64": _range_png(sc)})
    pts = np.concatenate(all_p).astype(np.float32)
    cols = _height_colors(pts)
    centers = np.asarray(centers, np.float32)
    # 3x4 [R | t] row-major (r00 r01 r02 tx  r10 r11 r12 ty  r20 r21 r22 tz). The old
    # concatenate([R.flat, t]).reshape(3,4) SCRAMBLED R and t (det(R)=0, zero forward) -> no frustum, wrong dir.
    poses12 = np.asarray([P[:3, :4].reshape(-1) for P in poses], np.float32)
    return ReconResult(
        case_id=spec.case_id, n_frames=len(scans), poses_c2w=poses12, points=pts, colors=cols,
        per_frame=per_frame, path_length=trajectory_length(centers),
        bbox_min=pts.min(0).tolist(), bbox_max=pts.max(0).tolist(), depth_thumbs=dth,
    )
