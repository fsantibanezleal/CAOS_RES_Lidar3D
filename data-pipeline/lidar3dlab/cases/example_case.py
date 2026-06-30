"""Cases spanning CATEGORIES (the reconstruction problem-type taxonomy). The App shows ONE selected case;
Experiments/Benchmark show cross-case summaries by category. Each case: id, category, SequenceSpec params,
expected band (what a domain expert should see), real|synthetic flag. Includes a synthetic CONTROL the
pipeline must handle without a GPU (CI-safe).

The 4 real sequences are the ones shipped with lingbot-map (preserved on the E: scratch volume, resolved via
LIDAR3D_DATA_ROOT — never an absolute path here). They bake offline on the GPU; the synthetic case bakes on
CPU and is what CI smoke-tests.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..config import sequence_dir
from ..io.schema import SequenceSpec


@dataclass(frozen=True)
class Case:
    id: str
    category: str
    params: SequenceSpec
    expected_band: str
    real_or_synthetic: str


def _real(seq: str, max_frames: int = 48) -> SequenceSpec:
    return SequenceSpec(case_id=seq, source_dir=str(sequence_dir(seq)), n_frames=0, max_frames=max_frames)


CASES: list[Case] = [
    Case("SYN_orbit", "synthetic: procedural corridor (CPU, CI)",
         SequenceSpec("SYN_orbit", source_dir="synthetic://corridor", n_frames=40, max_frames=40,
                      decimation=4, synthetic=True),
         "forward tunnel; colored/textured walls; ~5 m path; runs on CPU in <1 s", "synthetic"),
    Case("oxford", "real: outdoor walk",
         _real("oxford"), "forward outdoor street; smooth metric trajectory (a few metres)", "real"),
    Case("university", "real: courtyard",
         _real("university"), "courtyard walk; metric trajectory; structured facades", "real"),
    Case("loop", "real: revisit (loop closure)",
         _real("loop"), "path that revisits; showcases the drift / loop-closure gap", "real"),
    Case("courthouse", "real: facade orbit",
         _real("courthouse"), "facade orbit; metric trajectory around a structure", "real"),
]
