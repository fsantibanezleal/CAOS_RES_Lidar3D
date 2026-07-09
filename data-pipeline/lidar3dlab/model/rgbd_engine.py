"""Track B engine: RGB + REAL SENSOR DEPTH (RGB-D) geometric reconstruction.

The lab's two-track model family: Track A is RGB-only (Estela, the lingbot pointmap reference), where the
monocular metric-scale ambiguity is the measured blocker; Track B integrates the RGB stream with a real depth
sensor (Kinect/LiDAR-class), whose depth is metric BY CONSTRUCTION, so the scale problem disappears at the source.

Method (validated 2026-07-04, wip/lidar3d/exp_sensor_depth.py: 0.034-0.098 m ATE across TUM scenes, ~3x better
than the deployed RGB-only trajectory, zero fallbacks): per pair, match SIFT keypoints on the RGB, KEEP only the
matches whose local sensor-depth patch is filled and flat (the depth-edge guard, probe I1 2026-07-06: cuts ATE
~22-51% on the harder scenes, office 0.077 -> 0.038 m, by dropping correspondences at depth discontinuities where
a 1 px error back-projects to a large 3D error), back-project the surviving frame-i matches to 3D with the SENSOR
depth, and solve the relative pose with PnP + RANSAC. A DISK + LightGlue learned matcher is available opt-in
(LIDAR3D_MATCHER=lightglue) but is not the default: end-to-end, with fusion + the guard, SIFT beats it on 3/5
scenes (learned_match.py). Chain into camera-to-world, unproject every frame's sensor depth (holes = invalid 0
are dropped), and fuse the metric cloud. Honest: every number the sensor did not measure is absent, not invented.

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
_WIN = 6                       # window length for the pose-graph fusion
_SKIP = 2                      # max skip-edge distance inside a window
_DZ = 2                        # depth-edge guard: neighbour radius (px) around a matched pixel
_DEDGE = 0.10                  # depth-edge guard: max metres of depth jump inside that neighbourhood
_GUARD_MIN = 40                # keep the guarded set only if this many matches survive, else use the valid set


def _depth_ok(uv: np.ndarray, depth: np.ndarray) -> np.ndarray:
    """Per-match validity mask for PnP back-projection. A match is VALID if its sensor depth is in range, and is
    additionally KEPT by the depth-edge guard if its local (2*_DZ+1)^2 neighbourhood is filled and flat: a 1 px
    match error at a depth discontinuity back-projects to a large 3D error, so those correspondences are dropped.
    The guarded set is used only when >= _GUARD_MIN survive; otherwise the plain valid set is returned so a
    depth-rich / high-parallax scene is not starved into a pose-hold (probe I1, 2026-07-06)."""
    H, W = depth.shape
    u = np.clip(uv[:, 0].round().astype(int), 0, W - 1)
    v = np.clip(uv[:, 1].round().astype(int), 0, H - 1)
    z = depth[v, u]
    valid = (z > 0.1) & (z < 8.0)                              # sensor holes (0) + far range are invalid
    flat = valid.copy()
    for du in (-_DZ, 0, _DZ):
        for dv in (-_DZ, 0, _DZ):
            zn = depth[np.clip(v + dv, 0, H - 1), np.clip(u + du, 0, W - 1)]
            flat &= (zn > 0.1) & (np.abs(zn - z) < _DEDGE)     # neighbour valid AND flat (no depth jump)
    return flat if flat.sum() >= _GUARD_MIN else valid


def _chain(rel_pose, n: int) -> tuple[list, int]:
    """Plain consecutive chain (the fusion fallback). Holds pose on a failed pair rather than inventing motion."""
    c2ws = [np.eye(4)]
    fallbacks = 0
    for i in range(n - 1):
        e = rel_pose(i, i + 1)
        if e is None:
            c2ws.append(c2ws[-1].copy())
            fallbacks += 1
        else:
            c2ws.append(c2ws[-1] @ e[0])
    return c2ws, fallbacks


def _trajectory(rel_pose, n: int) -> tuple[list, int]:
    """Windowed pose-graph fusion over the metric PnP edges: overlapping windows (stride WIN-1, shared frame),
    per-window edges = consecutive + skip (window_edges), per-edge confidence = the PnP inlier count, fused by the
    differentiable window_pgo (forward-only). Cuts drift 7-26% vs the plain chain on the validation scenes.
    Falls back to the plain chain when torch is unavailable or the window solve fails."""
    try:
        import torch

        from .nets.window_ba import window_edges, window_pgo
    except Exception:  # noqa: BLE001 (no torch in this lane -> plain chain)
        return _chain(rel_pose, n)
    if n < _WIN + 1:
        return _chain(rel_pose, n)
    edges = window_edges(_WIN, skip=_SKIP)
    pairs = edges.tolist()
    G = np.eye(4)
    c2ws = [G.copy()]
    fallbacks = 0
    s = 0
    while s < n - 1:
        if s + _WIN > n:                                   # tail shorter than a window: chain the rest
            for i in range(s, n - 1):
                e = rel_pose(i, i + 1)
                if e is None:
                    c2ws.append(c2ws[-1].copy())
                    fallbacks += 1
                else:
                    c2ws.append(c2ws[-1] @ e[0])
            break
        zs, ws = [], []
        for (a, b) in pairs:
            e = rel_pose(s + a, s + b)
            if e is None:
                zs.append(np.eye(4))
                ws.append(1e-3)                            # near-zero weight: a missing edge must not constrain
                if b - a == 1:
                    fallbacks += 1
            else:
                zs.append(e[0])
                ws.append(float(e[1]))                     # PnP inlier count = edge confidence
        try:
            with torch.no_grad():
                fused = window_pgo(torch.from_numpy(np.stack(zs)).float(), edges,
                                   torch.tensor(ws).float(), _WIN, iters=6).numpy()
        except Exception:  # noqa: BLE001 (degenerate window -> chain it)
            for i in range(s, min(s + _WIN - 1, n - 1)):
                e = rel_pose(i, i + 1)
                c2ws.append(c2ws[-1] @ (e[0] if e else np.eye(4)))
            G = c2ws[-1].copy()
            s += _WIN - 1
            continue
        for f in range(1, _WIN):
            c2ws.append(G @ fused[f])
        G = G @ fused[_WIN - 1]
        s += _WIN - 1
    return c2ws[:n], fallbacks


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
    rgbs_u8 = [(r * 255).astype(np.uint8) for r in rgbs]

    # correspondence front-end: DISK + LightGlue learned matcher (probe I1: +13-27% ATE on 4/5 scenes, far more
    # inliers on hard/blurred frames) with classical SIFT as the CPU / no-GPU / no-weights fallback.
    from .learned_match import build_matcher
    matcher = build_matcher(rgbs_u8)
    if matcher is None:
        sift = cv2.SIFT_create(nfeatures=1200)
        bf = cv2.BFMatcher(cv2.NORM_L2)
        feats = [sift.detectAndCompute(cv2.cvtColor(u8, cv2.COLOR_RGB2GRAY), None) for u8 in rgbs_u8]

    def _sift_match(i: int, j: int):
        (ki, di), (kj, dj) = feats[i], feats[j]
        if di is None or dj is None or len(ki) < _MIN_MATCHES or len(kj) < _MIN_MATCHES:
            return None, None
        good = [m for m, nn in bf.knnMatch(di, dj, k=2) if m.distance < 0.75 * nn.distance]
        if len(good) < _MIN_MATCHES:
            return None, None
        return (np.float32([ki[m.queryIdx].pt for m in good]),
                np.float32([kj[m.trainIdx].pt for m in good]))

    def rel_pose(i: int, j: int) -> tuple[np.ndarray, int] | None:
        """Relative pose (frame j expressed in frame i) via the learned/SIFT correspondences + sensor-depth PnP
        RANSAC, plus the inlier count (used as the edge confidence for the windowed fusion)."""
        uv_i, uv_j = matcher.match(i, j) if matcher is not None else _sift_match(i, j)
        if uv_i is None or len(uv_i) < _MIN_MATCHES:
            return None
        d = depths[i]
        u = np.clip(uv_i[:, 0].round().astype(int), 0, d.shape[1] - 1)
        v = np.clip(uv_i[:, 1].round().astype(int), 0, d.shape[0] - 1)
        z = d[v, u]
        ok = _depth_ok(uv_i, d)                                 # valid depth + the depth-edge guard (with fallback)
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
        return (rel, int(len(inl))) if np.isfinite(rel).all() else None

    # trajectory: windowed pose-graph fusion over the metric PnP edges (consecutive + skip), the M-C solve
    # (window_pgo) run forward-only. On these STRONG metric edges the fusion measurably cuts drift (7-26% across
    # the validation scenes: office 0.097 -> 0.085, desk 0.036 -> 0.034, pioneer 0.033 -> 0.024 m), unlike over
    # weak edges where it fails (the P0.1 finding). Falls back to the plain chain if torch is unavailable.
    c2ws, fallbacks = _trajectory(rel_pose, n)

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
