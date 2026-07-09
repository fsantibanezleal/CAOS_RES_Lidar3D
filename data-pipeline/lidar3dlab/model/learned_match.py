"""DISK + LightGlue learned correspondence for the geometric (Track B) front-end. Opt-in, NOT the default.

Probe I1 (2026-07-06) measured this against SIFT two ways. Over a PLAIN chain (matcher effect isolated) LightGlue
won 4/5 scenes (+13-27% ATE) with 2-3x more inliers everywhere (e.g. pioneer 78 -> 193 on motion-blurred frames).
But over the ACTUAL deployed pipeline (window_pgo fusion + the depth-edge guard, rgbd_engine) the advantage
collapsed: the fusion already absorbs most drift, and the depth-edge guard removes exactly the noisier, more
distributed matches the learned matcher added, so SIFT beats LightGlue end-to-end on 3/5 scenes (office 0.038 vs
0.049, pioneer 0.040 vs 0.052, freiburg2_desk 0.014 vs 0.021). An honest negative: the learned matcher is not a
deployed win on clean benchmarks. It is kept AVAILABLE (LIDAR3D_MATCHER=lightglue) because its much higher inlier
count is a real robustness asset on hard/blurred imagery the clean TUM benchmark does not reward.

The matcher precomputes DISK features once per sequence (one forward per frame), then matches any pair with the
kornia LightGlueMatcher (descriptors + LAFs -> mutual match indices). Returns pixel correspondences in the SAME
(uv_i, uv_j) contract SIFT uses, so the engine's PnP path is unchanged.
"""
from __future__ import annotations

import os

import numpy as np

_MIN = 12                       # min keypoints / matches to attempt a pose (matches the engine's _MIN_MATCHES)


class LearnedMatcher:
    """DISK keypoints + descriptors, matched pairwise by LightGlue. Precompute once, match many."""

    def __init__(self, imgs_uint8: list[np.ndarray], max_kpts: int = 2048):
        import kornia.feature as KF
        import torch

        self._torch = torch
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self._disk = KF.DISK.from_pretrained("depth").to(self.device).eval()
        self._lg = KF.LightGlueMatcher("disk").to(self.device).eval()
        self._laf_of = KF.laf_from_center_scale_ori

        self._kpts: list = []
        self._desc: list = []
        self._lafs: list = []
        self._hw: list = []
        with torch.no_grad():
            for a in imgs_uint8:
                t = torch.from_numpy(np.ascontiguousarray(a)).permute(2, 0, 1).float().to(self.device) / 255.0
                f = self._disk(t[None], max_kpts, pad_if_not_divisible=True)[0]
                self._kpts.append(f.keypoints)
                self._desc.append(f.descriptors)
                self._lafs.append(self._laf_of(f.keypoints[None]))
                self._hw.append((a.shape[0], a.shape[1]))

    def match(self, i: int, j: int):
        """Pixel correspondences (uv_i, uv_j) as float32 (N, 2), or (None, None) when too few survive."""
        ki, kj = self._kpts[i], self._kpts[j]
        if ki.shape[0] < _MIN or kj.shape[0] < _MIN:
            return None, None
        with self._torch.no_grad():
            _, idx = self._lg(self._desc[i], self._desc[j], self._lafs[i], self._lafs[j], self._hw[i], self._hw[j])
        if idx.shape[0] < _MIN:
            return None, None
        uv_i = ki[idx[:, 0]].cpu().numpy().astype(np.float32)
        uv_j = kj[idx[:, 1]].cpu().numpy().astype(np.float32)
        return uv_i, uv_j


_LEARNED = {"lightglue", "disk", "learned"}


def build_matcher(imgs_uint8: list[np.ndarray]):
    """Return the learned DISK+LightGlue matcher ONLY when explicitly opted in (`LIDAR3D_MATCHER=lightglue`), else
    None so the caller uses its SIFT path. Default is SIFT: probe I1 (2026-07-06) found that once the windowed
    fusion AND the depth-edge guard are applied, SIFT beats the learned matcher end-to-end on 3/5 TUM scenes (the
    learned matcher's extra inliers were largely the depth-edge matches the guard removes). LightGlue stays
    available for hard/blurred imagery, where its 2-3x inlier count is a robustness asset the clean benchmark
    does not reward."""
    if os.environ.get("LIDAR3D_MATCHER", "").lower() not in _LEARNED:
        return None
    try:
        return LearnedMatcher(imgs_uint8)
    except Exception as e:  # noqa: BLE001 (no torch/kornia/CUDA/weights -> SIFT fallback)
        print(f"  [rgbd-sensor] learned matcher unavailable ({type(e).__name__}); using SIFT")
        return None
