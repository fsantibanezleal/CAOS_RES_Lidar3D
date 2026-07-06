"""The real streaming-reconstruction engine: lingbot-map (arXiv:2604.14141), vendored under
`third_party/lingbot-map` (Apache-2.0). Heavy (torch + a 4.6 GB checkpoint + a CUDA GPU), so the
offline/precompute lane runs it; it is imported LAZILY by stages/infer.py (the synthetic/CI lane never
imports torch). 8 GB-safe config (SDPA, CPU-offload, window=16, bf16) validated on an RTX 4070 (2026-06-29).
"""
from __future__ import annotations

import os

os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
import glob

import numpy as np
import torch

from ..config import checkpoint_path
from ..io.schema import ReconResult, SequenceSpec
from .geometry import depth_to_png_b64, rgb_to_png_b64, trajectory_length, unproject_depth

_IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".PNG", ".JPG")


def _frame_paths(source_dir: str, max_frames: int) -> list[str]:
    paths = sorted(sum([glob.glob(os.path.join(source_dir, f"*{e}")) for e in _IMAGE_EXTS], []))
    return paths[:max_frames]


def reconstruct(spec: SequenceSpec, seed: int = 42) -> ReconResult:
    from lingbot_map.models.gct_stream import GCTStream
    from lingbot_map.utils.geometry import closed_form_inverse_se3_general
    from lingbot_map.utils.load_fn import load_and_preprocess_images
    from lingbot_map.utils.pose_enc import pose_encoding_to_extri_intri

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    use_cuda = device.type == "cuda"
    dtype = torch.bfloat16 if (use_cuda and torch.cuda.get_device_capability()[0] >= 8) else torch.float32

    paths = _frame_paths(spec.source_dir, spec.max_frames)
    if not paths:
        raise FileNotFoundError(f"no frames in {spec.source_dir}")
    images = load_and_preprocess_images(paths, mode="crop", image_size=spec.image_size, patch_size=14)
    if images.ndim == 4:
        images = images.unsqueeze(0)
    B, S, C, H, W = images.shape

    model = GCTStream(
        img_size=spec.image_size, patch_size=14, enable_3d_rope=True, max_frame_num=1024,
        kv_cache_sliding_window=spec.kv_window, kv_cache_scale_frames=spec.scale_frames,
        kv_cache_cross_frame_special=True, kv_cache_include_scale_frames=True, use_sdpa=True,
        camera_num_iterations=spec.camera_iters,
    )
    ckpt = torch.load(str(checkpoint_path()), map_location="cpu", weights_only=False)
    model.load_state_dict(ckpt.get("model", ckpt) if isinstance(ckpt, dict) else ckpt, strict=False)
    model = model.to(device).eval()
    if dtype != torch.float32 and getattr(model, "aggregator", None) is not None:
        model.aggregator = model.aggregator.to(dtype=dtype)

    rgb_all = images[0].permute(0, 2, 3, 1).cpu().numpy()  # [S,H,W,3] 0..1
    with torch.no_grad(), torch.amp.autocast("cuda", dtype=dtype, enabled=use_cuda):
        pred = model.inference_streaming(images.to(device), num_scale_frames=spec.scale_frames,
                                         keyframe_interval=1, output_device=torch.device("cpu"))

    extr, intr = pose_encoding_to_extri_intri(pred["pose_enc"], (H, W))
    # The pose encoding decodes to CAMERA-TO-WORLD already (verified empirically on the oxford walk: using it
    # directly gives forward-facing motion, cos(fwd, motion) +0.79, a smooth 5.5 m path; inverting it gave a
    # BACKWARDS camera, cos -0.48, and a jagged 13.9 m path, the "reconstruction is backwards" bug). Do NOT
    # invert. closed_form_inverse_se3_general stays imported for reference but unused here.
    _ = closed_form_inverse_se3_general  # kept for reference; see the convention note above
    c2w = extr.cpu().reshape(-1, 3, 4).numpy()
    K = intr.reshape(-1, 3, 3).cpu().numpy()
    depth = np.asarray(pred["depth"]).reshape(S, H, W)
    conf = np.asarray(pred.get("depth_conf")).reshape(S, H, W) if "depth_conf" in pred else None

    all_p, all_c, per_frame, thumbs, rthumbs = [], [], [], [], []
    for i in range(S):
        thr = float(np.quantile(conf[i], spec.conf_quantile)) if conf is not None else None
        p, c = unproject_depth(depth[i], K[i], c2w[i], rgb_all[i], decimate=spec.decimation,
                               conf=conf[i] if conf is not None else None, conf_thr=thr)
        all_p.append(p)
        all_c.append(c)
        per_frame.append({"idx": i, "conf_mean": float(np.nanmean(conf[i])) if conf is not None else 0.0,
                          "n_points": int(len(p)), "depth_min": float(depth[i].min()),
                          "depth_max": float(depth[i].max())})
        if i % max(1, S // 48) == 0 or i == S - 1:            # ~48 keyframes for the per-frame panel
            thumbs.append({"idx": i, "png_b64": depth_to_png_b64(depth[i])})
            rthumbs.append({"idx": i, "png_b64": rgb_to_png_b64(rgb_all[i])})
    pts = np.concatenate(all_p).astype(np.float32)
    cols = np.concatenate(all_c).astype(np.uint8)
    centers = c2w[:, :, 3]
    return ReconResult(
        case_id=spec.case_id, n_frames=S, poses_c2w=c2w[:, :3, :4].reshape(S, 12).astype(np.float32),
        points=pts, colors=cols, per_frame=per_frame, path_length=trajectory_length(centers),
        bbox_min=pts.min(0).tolist(), bbox_max=pts.max(0).tolist(), depth_thumbs=thumbs, rgb_thumbs=rthumbs,
    )
