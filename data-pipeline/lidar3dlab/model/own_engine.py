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


def _frames(source_dir: str, max_frames: int) -> list[str]:
    paths = sorted(sum([glob.glob(os.path.join(source_dir, f"*{e}")) for e in _EXTS], []))
    return paths[:max_frames]


def _rgb_png_b64(rgb01: np.ndarray) -> str:
    import base64
    import io

    from PIL import Image
    a = (np.clip(rgb01, 0, 1) * 255).astype(np.uint8)
    buf = io.BytesIO()
    Image.fromarray(a).save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def reconstruct(spec: SequenceSpec, seed: int = 42) -> ReconResult:
    import torch
    from PIL import Image

    from .nets.own_depthpose import OwnDepthPose

    ckpt_path = MODELS_ROOT / "own-depthpose" / "own-depthpose.pt"
    if not ckpt_path.exists():
        raise FileNotFoundError(f"no trained checkpoint at {ckpt_path}; run train_depthpose.py first")
    paths = _frames(spec.source_dir, spec.max_frames)
    if not paths:
        raise FileNotFoundError(f"no frames in {spec.source_dir}")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    ck = torch.load(str(ckpt_path), map_location="cpu")
    size = int(ck.get("size", 224))
    model = OwnDepthPose(base=int(ck.get("base", 32)), max_depth=float(ck.get("max_depth", 10.0)))
    model.load_state_dict(ck["model"])
    model = model.to(device).eval()
    K = geom.intrinsics_from_fov(size, size, 60.0)  # own model is intrinsics-free; a fixed FoV colours the cloud

    def load(p: str) -> np.ndarray:
        im = Image.open(p).convert("RGB").resize((size, size), Image.BILINEAR)
        return (np.asarray(im, np.float32) / 255.0)

    rgbs = [load(p) for p in paths]
    all_p, all_c, per_frame, dth, rth, poses, centers = [], [], [], [], [], [], []
    c2w = np.eye(4)
    with torch.no_grad():
        for i, rgb in enumerate(rgbs):
            t0 = torch.from_numpy(rgb.transpose(2, 0, 1))[None].to(device)
            t1 = torch.from_numpy(rgbs[min(i + 1, len(rgbs) - 1)].transpose(2, 0, 1))[None].to(device)
            out = model(t0, t1)
            depth = out["depth0"][0, 0].float().cpu().numpy()
            logvar = out["logvar0"][0, 0].float().cpu().numpy()
            conf = np.exp(-logvar)                      # aleatoric confidence (high = reliable)
            thr = float(np.quantile(conf, spec.conf_quantile))
            poses.append(c2w[:3, :4].reshape(-1).astype(np.float32))   # the pose used to place THIS frame
            centers.append(c2w[:3, 3].copy())
            p, c = geom.unproject(depth, K, c2w, rgb=rgb, decimate=max(1, spec.decimation),
                                  conf=conf, conf_thr=thr)
            all_p.append(p)
            all_c.append(c)
            per_frame.append({"idx": i, "conf_mean": float(conf.mean()), "n_points": int(len(p)),
                              "depth_min": float(depth.min()), "depth_max": float(depth.max())})
            if i % max(1, len(rgbs) // 48) == 0 or i == len(rgbs) - 1:   # ~48 keyframes for the panel
                dth.append({"idx": i, "png_b64": depth_to_png_b64(depth)})
                rth.append({"idx": i, "png_b64": _rgb_png_b64(rgb)})
            if i + 1 < len(rgbs):                        # advance the trajectory by the predicted relative pose
                c2w = c2w @ out["rel_pose"][0].float().cpu().numpy()
    pts = np.concatenate(all_p).astype(np.float32)
    cols = np.concatenate(all_c).astype(np.uint8)
    return ReconResult(
        case_id=spec.case_id, n_frames=len(rgbs), poses_c2w=np.asarray(poses, np.float32),
        points=pts, colors=cols, per_frame=per_frame,
        path_length=geom.trajectory_length(np.asarray(centers, np.float32)),
        bbox_min=pts.min(0).tolist(), bbox_max=pts.max(0).tolist(), depth_thumbs=dth, rgb_thumbs=rth,
    )
