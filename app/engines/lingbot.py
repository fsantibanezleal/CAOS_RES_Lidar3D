"""LingbotEngine — the real streaming reconstruction engine (the hero).

Drives lingbot-map's streaming loop *frame by frame* (scale block, then one frame at a time
with the paged KV cache) and yields each frame's geometry as it is computed — genuinely
processed LIVE on the local GPU, not a baked replay. 8 GB-safe defaults from app.config.
"""
from __future__ import annotations
import os
import time
from typing import Iterator

os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
import numpy as np
import torch

from app.config import DEFAULTS, checkpoint_path
from app.geometry import pose_enc_to_c2w_K, unproject_depth, depth_to_png_b64
from app.engines.base import FramePayload, b64_f32, b64_u8


class LingbotEngine:
    name = "lingbot-map"

    def __init__(self, checkpoint: str | None = None, image_size: int | None = None,
                 kv_window: int | None = None, scale_frames: int | None = None,
                 camera_iters: int | None = None):
        self.ckpt = checkpoint_path(checkpoint)
        self.image_size = image_size or DEFAULTS.image_size
        self.patch_size = DEFAULTS.patch_size
        self.kv_window = kv_window or DEFAULTS.kv_cache_sliding_window
        self.scale_frames = scale_frames or DEFAULTS.num_scale_frames
        self.camera_iters = camera_iters or DEFAULTS.camera_num_iterations
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self._use_cuda = self.device.type == "cuda"
        self.dtype = (torch.bfloat16 if self._use_cuda and torch.cuda.get_device_capability()[0] >= 8
                      else torch.float32)
        self.model = None

    # ---- lifecycle -----------------------------------------------------------------------
    def warmup(self) -> None:
        if self.model is not None:
            return
        from lingbot_map.models.gct_stream import GCTStream
        m = GCTStream(
            img_size=self.image_size, patch_size=self.patch_size, enable_3d_rope=True,
            max_frame_num=1024, kv_cache_sliding_window=self.kv_window,
            kv_cache_scale_frames=self.scale_frames, kv_cache_cross_frame_special=True,
            kv_cache_include_scale_frames=True, use_sdpa=True,
            camera_num_iterations=self.camera_iters,
        )
        ckpt = torch.load(str(self.ckpt), map_location="cpu", weights_only=False)
        sd = ckpt.get("model", ckpt) if isinstance(ckpt, dict) else ckpt
        m.load_state_dict(sd, strict=False)
        m = m.to(self.device).eval()
        if self.dtype != torch.float32 and getattr(m, "aggregator", None) is not None:
            m.aggregator = m.aggregator.to(dtype=self.dtype)   # heads stay fp32
        self.model = m

    def _vram(self) -> float:
        return torch.cuda.max_memory_allocated() / 1e9 if self._use_cuda else 0.0

    # ---- streaming -----------------------------------------------------------------------
    def stream(self, image_paths: list[str], params: dict) -> Iterator[FramePayload]:
        self.warmup()
        from lingbot_map.utils.load_fn import load_and_preprocess_images

        max_frames = int(params.get("max_frames", DEFAULTS.max_frames))
        decimate = int(params.get("decimation", DEFAULTS.point_decimation))
        conf_q = float(params.get("conf_quantile", DEFAULTS.conf_quantile))
        keyframe_interval = int(params.get("keyframe_interval", 1))
        paths = list(image_paths)[:max_frames]

        images = load_and_preprocess_images(
            paths, mode="crop", image_size=self.image_size, patch_size=self.patch_size
        )                                            # [S,3,H,W] in 0..1, cpu
        if images.ndim == 4:
            images = images.unsqueeze(0)             # [1,S,3,H,W]
        B, S, C, H, W = images.shape
        scale = min(self.scale_frames, S)
        rgb_all = images[0].permute(0, 2, 3, 1).cpu().numpy()   # [S,H,W,3]

        if self._use_cuda:
            torch.cuda.reset_peak_memory_stats(); torch.cuda.empty_cache()
        self.model.clean_kv_cache()
        t_start = time.time()

        def _np(x):
            if x is None:
                return None
            return x.detach().cpu().float().numpy() if isinstance(x, torch.Tensor) else np.asarray(x)

        def emit(idx: int, pose_enc_1, depth_1, conf_1, is_kf: bool, t0: float) -> FramePayload:
            c2w, K = pose_enc_to_c2w_K(pose_enc_1, (H, W))         # [1,3,4],[1,3,3]
            depth = _np(depth_1).reshape(H, W)
            conf = _np(conf_1).reshape(H, W) if conf_1 is not None else None
            thr = float(np.quantile(conf, conf_q)) if conf is not None else None
            pts, cols = unproject_depth(depth, K[0], c2w[0], rgb_all[idx],
                                        decimate=decimate, conf=conf, conf_thr=thr)
            dt = max(time.time() - t0, 1e-6)
            return FramePayload(
                idx=idx, total=S, is_keyframe=is_kf,
                pose_c2w=[float(v) for v in c2w[0].reshape(-1)],
                points_b64=b64_f32(pts.reshape(-1)), colors_b64=b64_u8(cols.reshape(-1)),
                n_points=int(pts.shape[0]),
                depth_png=depth_to_png_b64(depth),
                conf_mean=float(np.nanmean(conf)) if conf is not None else 0.0,
                fps=1.0 / dt, vram_gb=self._vram(),
            )

        with torch.no_grad(), torch.amp.autocast("cuda", dtype=self.dtype, enabled=self._use_cuda):
            # Phase 1 — scale frames as one bidirectional block
            t0 = time.time()
            torch.compiler.cudagraph_mark_step_begin()
            out = self.model.forward(
                images[:, :scale].to(self.device, non_blocking=True),
                num_frame_for_scale=scale, num_frame_per_block=scale, causal_inference=True,
            )
            batch_dt = max(time.time() - t0, 1e-6)            # amortize the scale-block cost
            pe, dp = out["pose_enc"], out.get("depth")
            dc = out.get("depth_conf")
            for j in range(scale):
                yield emit(j, pe[:, j:j+1], dp[:, j] if dp is not None else None,
                           dc[:, j] if dc is not None else None, True,
                           time.time() - batch_dt / scale)
            del out

            # Phase 2 — one frame at a time (causal, paged KV cache)
            for i in range(scale, S):
                t0 = time.time()
                is_kf = (keyframe_interval <= 1) or ((i - scale) % keyframe_interval == 0)
                if not is_kf:
                    self.model._set_skip_append(True)
                torch.compiler.cudagraph_mark_step_begin()
                out = self.model.forward(
                    images[:, i:i+1].to(self.device, non_blocking=True),
                    num_frame_for_scale=scale, num_frame_per_block=1, causal_inference=True,
                )
                if not is_kf:
                    self.model._set_skip_append(False)
                pe, dp = out["pose_enc"], out.get("depth")
                dc = out.get("depth_conf")
                yield emit(i, pe[:, -1:], dp[:, -1] if dp is not None else None,
                           dc[:, -1] if dc is not None else None, is_kf, t0)
                del out

        _ = t_start  # (kept for future end-to-end timing)
