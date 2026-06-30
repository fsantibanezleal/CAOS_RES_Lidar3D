"""Typed objects passed between pipeline stages — the inter-stage contract. Plain dataclasses.

Domain: streaming 3D reconstruction. A `SequenceSpec` is one validated operating point (a frame sequence
+ the 8 GB-safe inference knobs); a `ReconResult` is the engine's raw output for that sequence (per-frame
poses + dense depth + a fused, RGB-colored world point cloud + trajectory).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class SequenceSpec:
    """One validated reconstruction job (the analogue of the example's params)."""
    case_id: str
    source_dir: str            # folder of ordered RGB frames (png/jpg), intrinsics-free
    n_frames: int              # frames available in the source
    max_frames: int = 64       # cap processed (8 GB-safe)
    image_size: int = 518      # working resolution (multiple of patch handled by the loader)
    kv_window: int = 16        # lingbot sliding KV window (8 GB-safe)
    scale_frames: int = 8      # anchor/scale block
    camera_iters: int = 1      # camera-head refinement steps (1 = faster)
    decimation: int = 6        # keep every Nth pixel for the committed cloud
    conf_quantile: float = 0.30  # drop the lowest-confidence pixels
    synthetic: bool = False    # a procedural CPU case (CI-safe; no GPU/model)
    modality: str = "camera"   # "camera" (lingbot / synthetic) or "lidar" (ICP odometry on scans)


@dataclass(frozen=True)
class FrameFeature:
    """Per-frame derived features (feature_extraction stage): cheap quality/aux signals."""
    idx: int
    mean_luma: float           # 0..1 average brightness (low -> unreliable geometry)
    sharpness: float           # variance-of-Laplacian proxy (focus / motion blur)


@dataclass(frozen=True)
class ReconResult:
    """The engine output for one sequence (infer stage) — raw, undecimated. Offline/precompute lane, so the
    arrays are NumPy (efficient for millions of points); the export stage decimates + base64-encodes them."""
    case_id: str
    n_frames: int
    poses_c2w: Any                        # np.ndarray [S,12] camera-to-world (row-major 3x4)
    points: Any                           # np.ndarray [P,3] float32 world XYZ (fused, conf-filtered)
    colors: Any                           # np.ndarray [P,3] uint8 RGB from the source frames
    per_frame: list[dict] = field(default_factory=list)  # idx, conf_mean, n_points, depth_min/max
    path_length: float = 0.0              # metric trajectory length (m)
    bbox_min: list[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    bbox_max: list[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    depth_thumbs: list[dict] = field(default_factory=list)  # a few {idx, png_b64} keyframes for the panel
