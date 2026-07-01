"""Inference engine for OUR trained depth+pose model (train/train_depthpose.py), behind the model-agnostic
Reconstructor contract. Loads the checkpoint, runs the model over a folder of ordered RGB frames (per-frame
metric depth + pairwise relative pose), accumulates a camera-to-world trajectory, and unprojects each frame with
OUR geometry (`model/geom.py`) into a fused, RGB-colored world point cloud. No vendored dependency.
"""
from __future__ import annotations

import glob
import os

import numpy as np

from ..config import MODELS_ROOT
from ..io.schema import ReconResult, SequenceSpec
from . import geom
from .geometry import depth_to_png_b64  # kept: the shared depth-thumbnail helper

_EXTS = (".png", ".jpg", ".jpeg", ".PNG", ".JPG")


def _natkey(p: str):
    """Natural sort key so numeric frame names order 0,1,2,...,10 (not 0,1,10,...); timestamped TUM names sort the
    same as lexicographic, so this is safe for every dataset (ICL-NUIM needs it: 0.png..1508.png)."""
    import re
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", os.path.basename(p))]


def _frames(source_dir: str, max_frames: int, frame_glob: str = "") -> list[str]:
    if frame_glob:                                    # a folder that mixes files (7-Scenes: color/depth/pose)
        paths = glob.glob(os.path.join(source_dir, frame_glob))
    else:
        paths = sum([glob.glob(os.path.join(source_dir, f"*{e}")) for e in _EXTS], [])
    return sorted(paths, key=_natkey)[:max_frames]


def _rgb_png_b64(rgb01: np.ndarray) -> str:
    import base64
    import io

    from PIL import Image
    a = (np.clip(rgb01, 0, 1) * 255).astype(np.uint8)
    buf = io.BytesIO()
    Image.fromarray(a).save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def _cam_pcd(o3d, depth: np.ndarray, conf: np.ndarray, K: np.ndarray, conf_q: float, max_d: float, decim: int = 6):
    """Build an Open3D camera-frame point cloud (with normals) from a depth map, keeping only near, confident
    pixels. Used as the ICP source/target for frame-to-frame pose refinement."""
    H, W = depth.shape
    vv, uu = np.meshgrid(np.arange(H), np.arange(W), indexing="ij")
    uu, vv, d, c = uu[::decim, ::decim], vv[::decim, ::decim], depth[::decim, ::decim], conf[::decim, ::decim]
    fx, fy, cx, cy = K[0, 0], K[1, 1], K[0, 2], K[1, 2]
    x = (uu - cx) / fx * d
    y = (vv - cy) / fy * d
    pts = np.stack([x, y, d], -1).reshape(-1, 3)
    dr, cr = d.reshape(-1), c.reshape(-1)
    thr = np.quantile(cr, conf_q)
    m = np.isfinite(pts).all(1) & (dr > 1e-6) & (dr < max_d) & (cr >= thr)
    pts = pts[m]
    if len(pts) < 50:
        return None
    pcd = o3d.geometry.PointCloud(o3d.utility.Vector3dVector(pts.astype(np.float64)))
    pcd.estimate_normals(o3d.geometry.KDTreeSearchParamHybrid(radius=0.25, max_nn=30))
    return pcd


def _refine_trajectory(depths: list, confs: list, K: np.ndarray, model_rels: list, conf_q: float,
                       max_d: float) -> list:
    """Accumulate camera-to-world poses, refining each model-predicted relative pose with frame-to-frame
    point-to-plane ICP on the depth clouds. Falls back to the raw model pose if Open3D is missing or ICP does not
    converge cleanly (guarded so a bad frame never corrupts the whole trajectory). Toggle off: LIDAR3D_OWN_ICP=0."""
    n = len(depths)
    c2ws = [np.eye(4)]
    o3d = None
    if os.environ.get("LIDAR3D_OWN_ICP", "1") != "0":
        try:
            import open3d as o3d  # noqa: F401
        except Exception:  # noqa: BLE001
            o3d = None
    prev = _cam_pcd(o3d, depths[0], confs[0], K, conf_q, max_d) if o3d else None
    for i in range(1, n):
        rel = model_rels[i - 1]                         # model init: maps frame i -> frame i-1
        cur = _cam_pcd(o3d, depths[i], confs[i], K, conf_q, max_d) if o3d else None
        if o3d is not None and prev is not None and cur is not None:
            try:
                reg = o3d.pipelines.registration.registration_icp(
                    cur, prev, 0.12, rel,
                    o3d.pipelines.registration.TransformationEstimationPointToPlane(),
                    o3d.pipelines.registration.ICPConvergenceCriteria(max_iteration=30))
                t = reg.transformation
                # accept only a sane, well-fitting refinement close to the prior (reject ICP blow-ups)
                if (reg.fitness > 0.3 and np.isfinite(t).all()
                        and np.linalg.norm(t[:3, 3] - rel[:3, 3]) < 0.5):
                    rel = t
            except Exception:  # noqa: BLE001
                pass
        c2ws.append(c2ws[-1] @ rel)
        if cur is not None:
            prev = cur
    return c2ws


def reconstruct(spec: SequenceSpec, seed: int = 42) -> ReconResult:
    import torch
    from PIL import Image

    from .nets.own_depthpose import OwnDepthPose

    ckpt_path = MODELS_ROOT / "own-depthpose" / "own-depthpose.pt"
    if not ckpt_path.exists():
        raise FileNotFoundError(f"no trained checkpoint at {ckpt_path}; run train_depthpose.py first")
    paths = _frames(spec.source_dir, spec.max_frames, spec.frame_glob)
    if not paths:
        raise FileNotFoundError(f"no frames in {spec.source_dir}")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    ck = torch.load(str(ckpt_path), map_location="cpu")
    size = int(ck.get("size", 224))
    # backbone comes from the checkpoint; pretrained=False since the ImageNet weights are already baked into it
    model = OwnDepthPose(base=int(ck.get("base", 32)), max_depth=float(ck.get("max_depth", 10.0)),
                         backbone=str(ck.get("backbone", "scratch")), pretrained=False)
    model.load_state_dict(ck["model"])
    model = model.to(device).eval()
    # unproject with the dataset's REAL intrinsics (scaled to the working resolution) for a geometrically consistent
    # cloud; fall back to a fixed FoV only when none are provided. A wrong (fixed) FoV systematically misaligns frames.
    if spec.intrinsics:
        fx, fy, cx, cy, W, H = (float(v) for v in spec.intrinsics.split(","))
        sx, sy = size / W, size / H
        K = geom.intrinsics(fx * sx, fy * sy, cx * sx, cy * sy)
    else:
        K = geom.intrinsics_from_fov(size, size, 60.0)

    def load(p: str) -> np.ndarray:
        im = Image.open(p).convert("RGB").resize((size, size), Image.BILINEAR)
        return (np.asarray(im, np.float32) / 255.0)

    rgbs = [load(p) for p in paths]
    n = len(rgbs)
    # ---- pass 1: per-frame metric depth + aleatoric confidence + the model's predicted relative poses ----
    depths, confs, model_rels = [], [], []
    with torch.no_grad():
        for i in range(n):
            t0 = torch.from_numpy(rgbs[i].transpose(2, 0, 1))[None].to(device)
            t1 = torch.from_numpy(rgbs[min(i + 1, n - 1)].transpose(2, 0, 1))[None].to(device)
            out = model(t0, t1)
            depths.append(out["depth0"][0, 0].float().cpu().numpy())
            confs.append(np.exp(-out["logvar0"][0, 0].float().cpu().numpy()))  # aleatoric confidence (high=reliable)
            model_rels.append(out["rel_pose"][0].float().cpu().numpy())        # maps frame i+1 -> frame i

    # ---- refine the trajectory: frame-to-frame point-to-plane ICP, INITIALISED by the model's relative pose.
    # The model gives sharp per-frame depth + a good pose prior; ICP on the depth clouds removes the accumulated
    # drift that otherwise blurs the fused map. Model init + geometric refinement = a standard, honest VO stack. ----
    c2ws = _refine_trajectory(depths, confs, K, model_rels, spec.conf_quantile,
                              spec.max_render_depth if spec.max_render_depth > 0 else 6.0)

    # ---- pass 2: unproject every frame at its refined pose into the fused, RGB-colored world cloud ----
    all_p, all_c, per_frame, dth, rth, poses, centers = [], [], [], [], [], [], []
    for i in range(n):
        depth, conf, c2w, rgb = depths[i], confs[i], c2ws[i], rgbs[i]
        thr = float(np.quantile(conf, spec.conf_quantile))
        poses.append(c2w[:3, :4].reshape(-1).astype(np.float32))   # the pose used to place THIS frame
        centers.append(c2w[:3, 3].copy())
        p, c = geom.unproject(depth, K, c2w, rgb=rgb, decimate=max(1, spec.decimation),
                              conf=conf, conf_thr=thr, max_depth=spec.max_render_depth)
        all_p.append(p)
        all_c.append(c)
        per_frame.append({"idx": i, "conf_mean": float(conf.mean()), "n_points": int(len(p)),
                          "depth_min": float(depth.min()), "depth_max": float(depth.max())})
        if i % max(1, n // 48) == 0 or i == n - 1:   # ~48 keyframes for the panel
            dth.append({"idx": i, "png_b64": depth_to_png_b64(depth)})
            rth.append({"idx": i, "png_b64": _rgb_png_b64(rgb)})
    pts = np.concatenate(all_p).astype(np.float32)
    cols = np.concatenate(all_c).astype(np.uint8)
    return ReconResult(
        case_id=spec.case_id, n_frames=len(rgbs), poses_c2w=np.asarray(poses, np.float32),
        points=pts, colors=cols, per_frame=per_frame,
        path_length=geom.trajectory_length(np.asarray(centers, np.float32)),
        bbox_min=pts.min(0).tolist(), bbox_max=pts.max(0).tolist(), depth_thumbs=dth, rgb_thumbs=rth,
    )
