"""Stage 4 - infer: run the reconstruction engine for a sequence.

Model-AGNOSTIC: if the case names an `engine`, it is resolved from the registry (`model/agnostic.py`) so ANY
model (classical baseline, the vendored SOTA reference, or one of OUR trained variants) runs behind the same
contract. Otherwise it auto-dispatches by modality/synthetic (back-compat). Engines import lazily so the
synthetic/CI lane never pulls torch."""
from __future__ import annotations

from ..io.schema import ReconResult, SequenceSpec


def run(spec: SequenceSpec, seed: int = 42) -> ReconResult:
    if spec.engine:
        from ..model.agnostic import get_engine
        return get_engine(spec.engine)(spec, seed)
    if spec.modality == "lidar":
        from ..model.lidar import reconstruct
    elif spec.synthetic:
        from ..model.synthetic import reconstruct
    else:
        from ..model.lingbot import reconstruct
    return reconstruct(spec, seed)
