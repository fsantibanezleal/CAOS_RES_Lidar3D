"""Model-AGNOSTIC engine registry. The pipeline and the web never know WHICH model produced a reconstruction:
every engine is a callable `reconstruct(spec, seed) -> ReconResult`, registered by name here. Adding a model
(a classical baseline, the vendored SOTA reference, or one of OUR trained variants) is one line + its checkpoint,
with no change to the staged pipeline, the contracts, or the App. Factories are lazy so the CI/synthetic lane
never imports torch.
"""
from __future__ import annotations

from collections.abc import Callable

from ..io.schema import ReconResult, SequenceSpec

Reconstruct = Callable[[SequenceSpec, int], ReconResult]


def _synthetic() -> Reconstruct:
    from .synthetic import reconstruct
    return reconstruct


def _lidar() -> Reconstruct:
    from .lidar import reconstruct
    return reconstruct


def _lingbot() -> Reconstruct:
    from .lingbot import reconstruct
    return reconstruct


def _own_depthpose() -> Reconstruct:
    from .own_engine import reconstruct
    return reconstruct


def _rgbd_sensor() -> Reconstruct:
    from .rgbd_engine import reconstruct
    return reconstruct


# name -> lazy factory. `kind` documents where it sits on the ladder (classical / SOTA-reference / ours).
ENGINES: dict[str, Callable[[], Reconstruct]] = {
    "synthetic": _synthetic,        # procedural CPU control (CI-safe)
    "lidar": _lidar,                # classical: Open3D/KISS-ICP point-to-plane odometry
    "lingbot": _lingbot,            # SOTA reference (vendored), wrapped behind this contract
    "own-depthpose": _own_depthpose,  # OURS: trained-from-scratch depth+pose (train/train_depthpose.py)
    "rgbd-sensor": _rgbd_sensor,    # Track B: RGB + real sensor depth (metric by construction, no scale ambiguity)
}

KIND = {"synthetic": "control", "lidar": "classical", "lingbot": "sota-reference", "own-depthpose": "ours",
        "rgbd-sensor": "classical"}


def get_engine(name: str) -> Reconstruct:
    if name not in ENGINES:
        raise KeyError(f"unknown engine '{name}'; known: {sorted(ENGINES)}")
    return ENGINES[name]()


def available() -> list[str]:
    return sorted(ENGINES)
