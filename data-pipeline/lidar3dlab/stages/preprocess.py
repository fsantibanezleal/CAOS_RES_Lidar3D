"""Stage 1 — preprocess: resolve + sanity-check the sequence's frames (CONTRACT 1 already validated the
schema). Returns the ordered frame paths the engine consumes. No-op for synthetic procedural cases."""
from __future__ import annotations

import glob
import os

from ..io.schema import SequenceSpec

_EXTS = (".png", ".jpg", ".jpeg", ".PNG", ".JPG")


def run(spec: SequenceSpec) -> dict:
    if spec.synthetic:
        return {"frames": [], "synthetic": True}
    paths = sorted(sum([glob.glob(os.path.join(spec.source_dir, f"*{e}")) for e in _EXTS], []))[:spec.max_frames]
    if not paths:
        raise FileNotFoundError(f"no frames in {spec.source_dir}")
    return {"frames": paths, "synthetic": False}
