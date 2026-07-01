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


def _pairwise_icp(o3d, src, tgt, init, max_corr: float = 0.12):
    """Point-to-plane ICP aligning src -> tgt (Open3D convention). Returns (transformation, information, fitness)."""
    reg = o3d.pipelines.registration.registration_icp(
        src, tgt, max_corr, init,
        o3d.pipelines.registration.TransformationEstimationPointToPlane(),
        o3d.pipelines.registration.ICPConvergenceCriteria(max_iteration=30))
    info = o3d.pipelines.registration.get_information_matrix_from_point_clouds(src, tgt, max_corr, reg.transformation)
    return reg.transformation, info, reg.fitness


def _refine_odometry(o3d, clouds: list, model_rels: list, conf_q: float, max_d: float) -> list:
    """Frame-to-frame point-to-plane ICP chain (local drift removal). Camera-to-world per frame. Model pose as init;
    a bad frame falls back to the raw prior so it never corrupts the trajectory."""
    n = len(clouds)
    c2ws = [np.eye(4)]
    for i in range(1, n):
        rel = model_rels[i - 1]                         # model init: maps frame i -> frame i-1
        if o3d is not None and clouds[i] is not None and clouds[i - 1] is not None:
            try:
                t, _, fit = _pairwise_icp(o3d, clouds[i], clouds[i - 1], rel)
                if fit > 0.3 and np.isfinite(t).all() and np.linalg.norm(t[:3, 3] - rel[:3, 3]) < 0.5:
                    rel = t
            except Exception:  # noqa: BLE001
                pass
        c2ws.append(c2ws[-1] @ rel)
    return c2ws


def _refine_global(o3d, clouds: list, model_rels: list, conf_q: float, max_d: float) -> list:
    """D1: GLOBAL pose-graph optimization with loop closure (Open3D multiway registration). Builds odometry edges
    (consecutive ICP) + loop-closure edges (spatially-near but temporally-distant frames that still align), then
    distributes the accumulated drift globally so revisited surfaces snap together, not smear. Returns per-frame
    camera-to-world. Falls back to the odometry-only chain on any failure. Toggle off: LIDAR3D_OWN_GLOBAL=0."""
    reg = o3d.pipelines.registration
    n = len(clouds)
    pg = reg.PoseGraph()
    odo = np.eye(4)                                     # world->cam accumulator (Open3D convention)
    pg.nodes.append(reg.PoseGraphNode(np.eye(4)))
    odos = [np.eye(4)]
    for i in range(1, n):
        # odometry edge: align frame i-1 -> frame i (Open3D source->target). init = inv(model rel: i->i-1)
        init = np.linalg.inv(model_rels[i - 1])
        t = init
        info = np.eye(6)
        if clouds[i] is not None and clouds[i - 1] is not None:
            try:
                tt, info_t, fit = _pairwise_icp(o3d, clouds[i - 1], clouds[i], init)
                if fit > 0.3 and np.isfinite(tt).all() and np.linalg.norm(tt[:3, 3] - init[:3, 3]) < 0.5:
                    t, info = tt, info_t
            except Exception:  # noqa: BLE001
                pass
        odo = t @ odo
        odos.append(odo)
        pg.nodes.append(reg.PoseGraphNode(np.linalg.inv(odo)))   # node.pose = cam-to-world
        pg.edges.append(reg.PoseGraphEdge(i - 1, i, t, info, uncertain=False))

    # loop closures: for each frame, the nearest few earlier frames (by odometry position) that are temporally far
    positions = np.array([np.linalg.inv(o)[:3, 3] for o in odos])
    span = float(np.linalg.norm(positions.max(0) - positions.min(0))) or 1.0
    radius = 0.15 * span                                # "near" = within 15% of the scene extent
    min_gap = max(15, n // 12)                          # "temporally distant"
    n_loops = 0
    for i in range(min_gap, n):
        if clouds[i] is None:
            continue
        # candidate earlier frames within radius, temporally distant, closest first
        cand = [j for j in range(0, i - min_gap) if clouds[j] is not None
                and np.linalg.norm(positions[i] - positions[j]) < radius]
        cand.sort(key=lambda j: np.linalg.norm(positions[i] - positions[j]))
        for j in cand[:2]:                              # at most 2 loop edges per frame (bounds cost)
            init = odos[i] @ np.linalg.inv(odos[j])     # source j -> target i, per odometry
            try:
                t, info, fit = _pairwise_icp(o3d, clouds[j], clouds[i], init)
                if fit > 0.55 and np.isfinite(t).all():
                    pg.edges.append(reg.PoseGraphEdge(j, i, t, info, uncertain=True))
                    n_loops += 1
            except Exception:  # noqa: BLE001
                pass
    if int(os.environ.get("LIDAR3D_VERBOSE", "0")):
        print(f"  [global] {n} frames, {n_loops} loop-closure edges")

    option = reg.GlobalOptimizationOption(max_correspondence_distance=0.12, edge_prune_threshold=0.25,
                                          reference_node=0)
    reg.global_optimization(pg, reg.GlobalOptimizationLevenbergMarquardt(),
                            reg.GlobalOptimizationConvergenceCriteria(), option)
    poses = [np.asarray(pg.nodes[i].pose) for i in range(n)]
    if not all(np.isfinite(p).all() for p in poses):    # optimization diverged -> keep the odometry chain
        raise RuntimeError("global optimization produced non-finite poses")
    return poses


def _refine_trajectory(depths: list, confs: list, K: np.ndarray, model_rels: list, conf_q: float,
                       max_d: float) -> list:
    """Accumulate camera-to-world poses from the model's per-frame depth + predicted relative pose. Refinement
    ladder (each falls back to the previous on failure):
      GLOBAL pose-graph optimization + loop closure (D1, default)  ->  frame-to-frame ICP  ->  raw model poses.
    LIDAR3D_OWN_GLOBAL=0 drops to ICP-only; LIDAR3D_OWN_ICP=0 drops to raw model poses."""
    n = len(depths)
    o3d = None
    if os.environ.get("LIDAR3D_OWN_ICP", "1") != "0":
        try:
            import open3d as o3d  # noqa: F401
        except Exception:  # noqa: BLE001
            o3d = None
    if o3d is None:
        c2ws = [np.eye(4)]                               # raw model accumulation
        for i in range(1, n):
            c2ws.append(c2ws[-1] @ model_rels[i - 1])
        return c2ws
    clouds = [_cam_pcd(o3d, depths[i], confs[i], K, conf_q, max_d) for i in range(n)]
    # GLOBAL pose-graph optimization (D1) is implemented + available, but OPT-IN: at the current monocular pose
    # accuracy (~0.37 m ATE) its loop closures over-constrain single-area indoor sweeps. It becomes the right default
    # once a stronger model (more training data) gives sub-decimetre poses. Enable with LIDAR3D_OWN_GLOBAL=1.
    if os.environ.get("LIDAR3D_OWN_GLOBAL", "0") != "0":
        try:
            return _refine_global(o3d, clouds, model_rels, conf_q, max_d)
        except Exception as e:  # noqa: BLE001
            if int(os.environ.get("LIDAR3D_VERBOSE", "0")):
                print(f"  [global] failed ({e}); falling back to frame-to-frame ICP")
    return _refine_odometry(o3d, clouds, model_rels, conf_q, max_d)


def _fuse_tsdf(o3d, depths: list, rgbs: list, confs: list, c2ws: list, K: np.ndarray, conf_q: float,
               max_d: float, voxel: float = 0.025):
    """TSDF volumetric fusion (KinectFusion-style): integrate every confident, near depth frame into a truncated
    signed-distance volume at its refined pose, then extract a single DENOISED surface point cloud (with colors +
    normals). Volumetric averaging cancels the per-frame monocular depth noise that no pose refinement can remove,
    so surfaces come out clean instead of a scattered spray. Returns (points [N,3] f32, colors [N,3] u8)."""
    size = depths[0].shape[0]
    vol = o3d.pipelines.integration.ScalableTSDFVolume(
        voxel_length=voxel, sdf_trunc=voxel * 3,
        color_type=o3d.pipelines.integration.TSDFVolumeColorType.RGB8)
    intr = o3d.camera.PinholeCameraIntrinsic(size, size, float(K[0, 0]), float(K[1, 1]),
                                             float(K[0, 2]), float(K[1, 2]))
    for i in range(len(depths)):
        d = depths[i].astype(np.float32).copy()
        thr = float(np.quantile(confs[i], conf_q))
        d[(confs[i] < thr) | (d >= max_d)] = 0.0        # drop low-confidence + far pixels (invalid = 0)
        col = o3d.geometry.Image(np.ascontiguousarray((np.clip(rgbs[i], 0, 1) * 255).astype(np.uint8)))
        dep = o3d.geometry.Image(np.ascontiguousarray(d))
        rgbd = o3d.geometry.RGBDImage.create_from_color_and_depth(
            col, dep, depth_scale=1.0, depth_trunc=max_d, convert_rgb_to_intensity=False)
        vol.integrate(rgbd, intr, np.linalg.inv(c2ws[i]))   # extrinsic = world-to-cam
    pcd = vol.extract_point_cloud()
    pts = np.asarray(pcd.points, np.float32)
    cols = (np.asarray(pcd.colors) * 255.0).clip(0, 255).astype(np.uint8) if pcd.has_colors() \
        else np.full((len(pts), 3), 180, np.uint8)
    return pts, cols


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
                         backbone=str(ck.get("backbone", "scratch")), pretrained=False,
                         pose_head=str(ck.get("pose_head", "siamese")))
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

    # ---- pass 2: per-frame poses + panel thumbnails (independent of how the cloud is built) ----
    poses = [c2w[:3, :4].reshape(-1).astype(np.float32) for c2w in c2ws]
    centers = [c2w[:3, 3].astype(np.float32) for c2w in c2ws]
    dth, rth, per_frame = [], [], []
    for i in range(n):
        per_frame.append({"idx": i, "conf_mean": float(confs[i].mean()), "n_points": 0,
                          "depth_min": float(depths[i].min()), "depth_max": float(depths[i].max())})
        if i % max(1, n // 48) == 0 or i == n - 1:   # ~48 keyframes for the panel
            dth.append({"idx": i, "png_b64": depth_to_png_b64(depths[i])})
            rth.append({"idx": i, "png_b64": _rgb_png_b64(rgbs[i])})

    # ---- the fused cloud: raw ICP-refined accumulation (default) or TSDF volumetric fusion (OPT-IN). TSDF gives a
    # denoised surface ONLY when the poses are sub-voxel accurate; at the current monocular pose accuracy it fuses
    # sparsely (frames disagree), so it is opt-in (LIDAR3D_OWN_TSDF=1) and becomes the default once poses improve. ----
    pts = cols = None
    if os.environ.get("LIDAR3D_OWN_TSDF", "0") != "0":
        try:
            import open3d as o3d
            max_d = spec.max_render_depth if spec.max_render_depth > 0 else 6.0
            tp, tc = _fuse_tsdf(o3d, depths, rgbs, confs, c2ws, K, spec.conf_quantile, max_d)
            if len(tp) > 500:
                from scipy.spatial import cKDTree
                near = cKDTree(np.asarray(centers, np.float32)).query(tp)[1]  # nearest camera frame per point
                order = np.argsort(near, kind="stable")                       # reveal builds up along the path
                pts, cols = tp[order].astype(np.float32), tc[order].astype(np.uint8)
                counts = np.bincount(near[order], minlength=n)
                for i in range(n):
                    per_frame[i]["n_points"] = int(counts[i])
        except Exception as e:  # noqa: BLE001
            if int(os.environ.get("LIDAR3D_VERBOSE", "0")):
                print(f"  [tsdf] failed ({e}); falling back to raw accumulation")
    if pts is None:                                    # raw per-frame unprojection (per-frame-attributed)
        all_p, all_c = [], []
        for i in range(n):
            thr = float(np.quantile(confs[i], spec.conf_quantile))
            p, c = geom.unproject(depths[i], K, c2ws[i], rgb=rgbs[i], decimate=max(1, spec.decimation),
                                  conf=confs[i], conf_thr=thr, max_depth=spec.max_render_depth)
            all_p.append(p)
            all_c.append(c)
            per_frame[i]["n_points"] = int(len(p))
        pts = np.concatenate(all_p).astype(np.float32)
        cols = np.concatenate(all_c).astype(np.uint8)
    return ReconResult(
        case_id=spec.case_id, n_frames=len(rgbs), poses_c2w=np.asarray(poses, np.float32),
        points=pts, colors=cols, per_frame=per_frame,
        path_length=geom.trajectory_length(np.asarray(centers, np.float32)),
        bbox_min=pts.min(0).tolist(), bbox_max=pts.max(0).tolist(), depth_thumbs=dth, rgb_thumbs=rth,
    )
