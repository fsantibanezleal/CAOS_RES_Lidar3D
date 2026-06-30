"""Engine interface shared by every reconstruction backend (real, swappable).

A `StreamingEngine` turns an ordered list of frames (image paths) into a stream of
`FramePayload`s, one per processed frame, ready to ship over the WebSocket. Point chunks
are base64-encoded raw bytes (Float32 xyz + Uint8 rgb) — far smaller than JSON arrays.
"""
from __future__ import annotations
import base64
from dataclasses import dataclass, asdict
from typing import Iterator, Protocol, runtime_checkable
import numpy as np


def b64_f32(a: np.ndarray) -> str:
    return base64.b64encode(np.ascontiguousarray(a, dtype="<f4").tobytes()).decode()


def b64_u8(a: np.ndarray) -> str:
    return base64.b64encode(np.ascontiguousarray(a, dtype=np.uint8).tobytes()).decode()


@dataclass
class FramePayload:
    idx: int
    total: int
    is_keyframe: bool
    pose_c2w: list[float]          # 12 floats (row-major 3x4), camera-to-world
    points_b64: str                # Float32 xyz, length 3*N
    colors_b64: str                # Uint8 rgb, length 3*N
    n_points: int
    depth_png: str                 # data:image/png;base64,...
    conf_mean: float
    fps: float
    vram_gb: float

    def to_msg(self) -> dict:
        d = asdict(self)
        d["type"] = "frame"
        return d


@runtime_checkable
class StreamingEngine(Protocol):
    name: str
    def warmup(self) -> None: ...
    def stream(self, image_paths: list[str], params: dict) -> Iterator[FramePayload]: ...
