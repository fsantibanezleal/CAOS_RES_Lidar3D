"""Stage 4 — infer: run the reconstruction engine for a sequence. Dispatches to the synthetic CPU engine
(CI-safe) or the real lingbot-map GPU engine (imported lazily so the synthetic lane never pulls torch)."""
from __future__ import annotations

from ..io.schema import ReconResult, SequenceSpec


def run(spec: SequenceSpec, seed: int = 42) -> ReconResult:
    if spec.modality == "lidar":
        from ..model.lidar import reconstruct
    elif spec.synthetic:
        from ..model.synthetic import reconstruct
    else:
        from ..model.lingbot import reconstruct
    return reconstruct(spec, seed)
