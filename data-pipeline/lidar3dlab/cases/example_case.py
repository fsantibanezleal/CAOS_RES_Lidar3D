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

from ..config import DATA_ROOT, sequence_dir
from ..io.schema import SequenceSpec


@dataclass(frozen=True)
class Case:
    id: str
    category: str
    params: SequenceSpec
    expected_band: str
    real_or_synthetic: str
    dataset: str = "Synthetic (CAOS, no third-party data)"   # human-readable data source
    license: str = "Synthetic - no third-party data"          # surfaced in the App to avoid licensing issues


def _real(seq: str, max_frames: int = 96) -> SequenceSpec:
    return SequenceSpec(case_id=seq, source_dir=str(sequence_dir(seq)), n_frames=0, max_frames=max_frames)


CASES: list[Case] = [
    Case("SYN_orbit", "synthetic: camera, procedural corridor (CPU, CI)",
         SequenceSpec("SYN_orbit", source_dir="synthetic://corridor", n_frames=120, max_frames=120,
                      decimation=4, synthetic=True),
         "forward tunnel; colored/textured walls; ~5 m path; runs on CPU in <1 s", "synthetic"),
    Case("LID_synthetic", "synthetic: LiDAR ICP odometry (CPU, CI)",
         SequenceSpec("LID_synthetic", source_dir="synthetic://lidar", n_frames=90, max_frames=90,
                      synthetic=True, modality="lidar"),
         "forward LiDAR sweep down a corridor; point-to-plane ICP odometry recovers a ~9 m path; height-colored map",
         "synthetic"),
    Case("OWN_tum_desk", "ours: trained depth+pose model (TUM RGB-D)",
         SequenceSpec("OWN_tum_desk",
                      source_dir=str(DATA_ROOT / "train" / "tum-rgbd" / "rgbd_dataset_freiburg1_desk" / "rgb"),
                      n_frames=0, max_frames=120, decimation=2, engine="own-depthpose"),
         "OUR from-scratch depth+pose model (trained on TUM RGB-D, ~0.2 m held-out ATE) reconstructs a desk sweep",
         "real", dataset="TUM RGB-D (freiburg1_desk, Sturm et al. 2012)", license="CC BY 4.0 (TUM RGB-D)"),
    Case("kitti_lidar", "real: LiDAR odometry (KITTI-style scans)",
         SequenceSpec("kitti_lidar", source_dir=str(DATA_ROOT / "lidar" / "kitti00"), n_frames=0, max_frames=40,
                      modality="lidar"),
         "a folder of .bin/.npy/.ply LiDAR scans; ICP odometry + registered map (bakes offline when the dataset is present)",
         "real", dataset="KITTI odometry (Geiger et al. 2012)", license="CC BY-NC-SA 3.0 (KITTI)"),
    Case("oxford", "real: outdoor walk",
         _real("oxford"), "forward outdoor street; smooth metric trajectory (a few metres)", "real",
         dataset="lingbot-map examples", license="Apache-2.0 (lingbot-map)"),
    Case("university", "real: courtyard",
         _real("university"), "courtyard walk; metric trajectory; structured facades", "real",
         dataset="lingbot-map examples", license="Apache-2.0 (lingbot-map)"),
    Case("loop", "real: revisit (loop closure)",
         _real("loop"), "path that revisits; showcases the drift / loop-closure gap", "real",
         dataset="lingbot-map examples", license="Apache-2.0 (lingbot-map)"),
    Case("courthouse", "real: facade orbit",
         _real("courthouse"), "facade orbit; metric trajectory around a structure", "real",
         dataset="lingbot-map examples", license="Apache-2.0 (lingbot-map)"),
]
