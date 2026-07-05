"""Classical DEPTH-ONLY method for RGB-D scenarios: frame-to-frame point-to-plane ICP on the sensor depth clouds.

Completes the method matrix on a depth-capable scenario so all outcomes are comparable:
- Track A (Estela): pose from RGB only, scale inferred.
- Track B (rgbd-sensor): pose from RGB features + sensor depth (SIFT + PnP), scale measured.
- classical depth-ICP (this engine): pose from the DEPTH ALONE, no RGB features anywhere in the estimation,
  the same classical registration the LiDAR-only scenario runs (point-to-plane ICP), applied to Kinect depth.

The RGB stream is used ONLY to color the fused cloud for display (it does not influence the pose); on a real
depth-only capture the same pipeline runs with a height ramp instead. Sensor holes stay holes.
"""
from __future__ import annotations

import numpy as np

from ..io.schema import ReconResult, SequenceSpec
from . import geom
from .geometry import depth_to_png_b64, rgb_to_png_b64, trajectory_length

_MAX_D = 6.0


def _pcd(o3d, depth: np.ndarray, K: np.ndarray, stride: int = 2):
    """Unproject a depth frame (holes = 0 dropped) to an Open3D cloud with normals, camera frame."""
    h, w = depth.shape
    vv, uu = np.mgrid[0:h:stride, 0:w:stride]
    z = depth[::stride, ::stride]
    ok = (z > 0.1) & (z < _MAX_D)
    x = (uu[ok] - K[0, 2]) / K[0, 0] * z[ok]
    y = (vv[ok] - K[1, 2]) / K[1, 1] * z[ok]
    p = o3d.geometry.PointCloud()
    p.points = o3d.utility.Vector3dVector(np.stack([x, y, z[ok]], 1).astype(np.float64))
    p.estimate_normals(o3d.geometry.KDTreeSearchParamHybrid(radius=0.25, max_nn=30))
    return p


def reconstruct(spec: SequenceSpec, seed: int = 42) -> ReconResult:  # noqa: ARG001 (deterministic)
    import open3d as o3d
    from PIL import Image

    from ..train.dataset_tum import TUMPairs

    size = 224 if spec.image_size > 448 else spec.image_size
    ds = TUMPairs(spec.source_dir, image_size=size)
    frames = ds.frames[: spec.max_frames] if spec.max_frames else ds.frames
    if len(frames) < 2:
        raise FileNotFoundError(f"no associated RGB-D frames under {spec.source_dir}")
    K = ds._K()
    n = len(frames)

    depths = [ds._load_depth(f[1]) for f in frames]                 # SENSOR depth (pose comes from THIS alone)
    rgbs = [np.asarray(Image.open(ds.seq_dir / f[0]).convert("RGB").resize((size, size), Image.BILINEAR),
                       np.float32) / 255.0 for f in frames]          # display colors only

    clouds = [_pcd(o3d, d, K) for d in depths]
    crit = o3d.pipelines.registration.ICPConvergenceCriteria(max_iteration=30)
    c2ws = [np.eye(4)]
    for i in range(1, n):
        reg = o3d.pipelines.registration.registration_icp(
            clouds[i], clouds[i - 1], 0.12, np.eye(4),
            o3d.pipelines.registration.TransformationEstimationPointToPlane(), crit)
        rel = reg.transformation if reg.fitness > 0.2 else np.eye(4)   # hold pose on a failed registration
        c2ws.append(c2ws[-1] @ rel)

    poses = [c2w[:3, :4].reshape(-1).astype(np.float32) for c2w in c2ws]
    centers = [c2w[:3, 3].astype(np.float32) for c2w in c2ws]
    all_p, all_c, per_frame, dth, rth = [], [], [], [], []
    for i in range(n):
        p, c = geom.unproject(depths[i], K, c2ws[i], rgb=rgbs[i], decimate=max(1, spec.decimation),
                              max_depth=spec.max_render_depth if spec.max_render_depth > 0 else _MAX_D)
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
    return ReconResult(
        case_id=spec.case_id, n_frames=n, poses_c2w=np.asarray(poses, np.float32),
        points=pts, colors=cols, per_frame=per_frame,
        path_length=trajectory_length(np.asarray(centers, np.float32)),
        bbox_min=pts.min(0).tolist(), bbox_max=pts.max(0).tolist(), depth_thumbs=dth, rgb_thumbs=rth,
    )
