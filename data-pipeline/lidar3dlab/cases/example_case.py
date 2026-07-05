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


# Real camera intrinsics "fx,fy,cx,cy,W,H" (native px) for a geometrically consistent unprojection (vs a wrong fixed FoV).
_TUM1 = "517.306,516.469,318.643,255.314,640,480"    # TUM freiburg1
_TUM2 = "520.909,521.007,325.141,249.701,640,480"    # TUM freiburg2
_TUM3 = "535.4,539.2,320.1,247.6,640,480"            # TUM freiburg3
_S7 = "585,585,320,240,640,480"                       # Microsoft 7-Scenes (Kinect)
_ICL = "481.2,480.0,319.5,239.5,640,480"              # ICL-NUIM


def _own(cid: str, subpath: str, expected: str, dataset: str, license: str, intr: str, frames: int = 240,
         glob: str = "", max_depth: float = 5.0) -> Case:
    """An OUR-model case: point the from-scratch/pretrained depth+pose engine at any folder of ordered RGB frames
    under DATA_ROOT/train/. `frames` = (larger) coverage cap; `glob` selects the RGB frames when the folder mixes
    files ("*.color.png" for 7-Scenes); `intr` = real intrinsics for a correct cloud; `max_depth` drops far points
    (which amplify pose error into scatter) so the accumulated cloud stays sharp."""
    return Case(cid, "track A: RGB-only, Estela (ours)",
                SequenceSpec(cid, source_dir=str(DATA_ROOT / "train" / subpath), n_frames=0, max_frames=frames,
                             decimation=2, conf_quantile=0.65, engine="own-depthpose", frame_glob=glob,
                             intrinsics=intr, max_render_depth=max_depth),
                expected, "real", dataset=dataset, license=license)


CASES: list[Case] = [
    Case("SYN_orbit", "control: synthetic camera (CPU, CI)",
         SequenceSpec("SYN_orbit", source_dir="synthetic://corridor", n_frames=120, max_frames=120,
                      decimation=4, synthetic=True),
         "forward tunnel; colored/textured walls; ~5 m path; runs on CPU in <1 s", "synthetic"),
    Case("LID_synthetic", "sensor-only: LiDAR ICP odometry (no camera)",
         SequenceSpec("LID_synthetic", source_dir="synthetic://lidar", n_frames=90, max_frames=90,
                      synthetic=True, modality="lidar"),
         "forward LiDAR sweep down a corridor; point-to-plane ICP odometry recovers a ~9 m path; height-colored map",
         "synthetic"),
    _own("OWN_tum_desk", "tum-rgbd/rgbd_dataset_freiburg1_desk/rgb",
         "Estela (pretrained ResNet-18 backbone + our decoder/pose, trained on TUM RGB-D + ICL-NUIM) reconstructs a desk sweep",
         "TUM RGB-D (freiburg1_desk, Sturm et al. 2012)", "CC BY 4.0 (TUM RGB-D)", _TUM1),
    _own("OWN_tum_office", "tum-rgbd/rgbd_dataset_freiburg3_long_office_household/rgb",
         "Estela on a TRULY HELD-OUT office sweep (freiburg3_long_office is the evaluation sequence, never trained on): honest generalization",
         "TUM RGB-D (freiburg3_long_office_household, Sturm et al. 2012)", "CC BY 4.0 (TUM RGB-D)", _TUM3, max_depth=6.0),
    _own("OWN_tum_xyz", "tum-rgbd/rgbd_dataset_freiburg1_xyz/rgb",
         "Estela on a translational xyz-calibration sweep: near-planar desktop, tight motion, a clean reconstruction test",
         "TUM RGB-D (freiburg1_xyz, Sturm et al. 2012)", "CC BY 4.0 (TUM RGB-D)", _TUM1),
    _own("OWN_tum_desk2", "tum-rgbd/rgbd_dataset_freiburg2_desk/rgb",
         "Estela on a longer, wider desk loop (freiburg2): a bigger workspace with more depth range",
         "TUM RGB-D (freiburg2_desk, Sturm et al. 2012)", "CC BY 4.0 (TUM RGB-D)", _TUM2, max_depth=6.0),
    _own("OWN_tum_pioneer", "tum-rgbd/rgbd_dataset_freiburg2_pioneer_slam/rgb",
         "Estela on a robot (Pioneer) SLAM run through a hall: long fast trajectory, the hardest drift test",
         "TUM RGB-D (freiburg2_pioneer_slam, Sturm et al. 2012)", "CC BY 4.0 (TUM RGB-D)", _TUM2, max_depth=6.0),
    _own("OWN_7scenes_heads", "7scenes/heads/seq-01",
         "Estela on Microsoft 7-Scenes 'heads' (HELD-OUT relocalization data, never trained on): a tight cluttered desk corner",
         "7-Scenes (heads, Shotton et al. 2013)", "Microsoft Research 7-Scenes (research use)", _S7, glob="*.color.png"),
    _own("OWN_7scenes_stairs", "7scenes/stairs/seq-01",
         "Estela on Microsoft 7-Scenes 'stairs' (HELD-OUT, never trained on): a repetitive staircase, a texture-ambiguity test",
         "7-Scenes (stairs, Shotton et al. 2013)", "Microsoft Research 7-Scenes (research use)", _S7, glob="*.color.png"),
    _own("OWN_icl_living", "icl-nuim/rgb",
         "Estela on ICL-NUIM synthetic living-room (perfect-depth synthetic domain, IN the training set via --use_icl): a clean best-case sharpness reference, not held-out",
         "ICL-NUIM (living_room, Handa et al. 2014)", "ICL-NUIM (research use)", _ICL, max_depth=6.0),
    Case("kitti_lidar", "sensor-only: LiDAR ICP odometry (no camera)",
         SequenceSpec("kitti_lidar", source_dir=str(DATA_ROOT / "lidar" / "kitti00"), n_frames=0, max_frames=40,
                      modality="lidar"),
         "a folder of .bin/.npy/.ply LiDAR scans; ICP odometry + registered map (bakes offline when the dataset is present)",
         "real", dataset="KITTI odometry (Geiger et al. 2012)", license="CC BY-NC-SA 3.0 (KITTI)"),
    Case("oxford", "track A: RGB-only, pointmap SOTA reference",
         _real("oxford"), "forward outdoor street; smooth metric trajectory (a few metres)", "real",
         dataset="lingbot-map examples", license="Apache-2.0 (lingbot-map)"),
    Case("university", "track A: RGB-only, pointmap SOTA reference",
         _real("university"), "courtyard walk; metric trajectory; structured facades", "real",
         dataset="lingbot-map examples", license="Apache-2.0 (lingbot-map)"),
    Case("loop", "track A: RGB-only, pointmap SOTA reference",
         _real("loop"), "path that revisits; showcases the drift / loop-closure gap", "real",
         dataset="lingbot-map examples", license="Apache-2.0 (lingbot-map)"),
    Case("courthouse", "track A: RGB-only, pointmap SOTA reference",
         _real("courthouse"), "facade orbit; metric trajectory around a structure", "real",
         dataset="lingbot-map examples", license="Apache-2.0 (lingbot-map)"),
    # ---- Track B: RGB + REAL SENSOR DEPTH (rgbd-sensor engine). The RGB-only cases above are Track A; these
    # integrate the Kinect depth stream, so the metric scale comes from the SENSOR (no monocular ambiguity) and the
    # trajectory is ~3x tighter than the RGB-only Estela on the same scenes (0.034-0.098 m validated vs 0.03-0.28).
    # Same scenes as OWN_tum_office/desk so the site shows an honest side-by-side of what the depth sensor buys. ----
    Case("RGBD_tum_office", "track B: RGB + sensor depth (Kinect)",
         SequenceSpec("RGBD_tum_office",
                      source_dir=str(DATA_ROOT / "train" / "tum-rgbd" / "rgbd_dataset_freiburg3_long_office_household"),
                      n_frames=0, max_frames=240, decimation=2, engine="rgbd-sensor",
                      intrinsics=_TUM3, max_render_depth=6.0),
         "the SAME office sweep as OWN_tum_office, but integrating the real Kinect depth: SIFT+PnP geometric pose "
         "on sensor depth (metric by construction, 0.098 m ATE vs 0.28 m RGB-only), sensor holes stay honest holes",
         "real", dataset="TUM RGB-D (freiburg3_long_office_household, Sturm et al. 2012)",
         license="CC BY 4.0 (TUM RGB-D)"),
    Case("RGBD_tum_desk", "track B: RGB + sensor depth (Kinect)",
         SequenceSpec("RGBD_tum_desk",
                      source_dir=str(DATA_ROOT / "train" / "tum-rgbd" / "rgbd_dataset_freiburg1_desk"),
                      n_frames=0, max_frames=240, decimation=2, engine="rgbd-sensor",
                      intrinsics=_TUM1, max_render_depth=5.0),
         "the SAME desk sweep as OWN_tum_desk with the real Kinect depth integrated: 0.037 m ATE (vs 0.119 m "
         "RGB-only), the cleanest demonstration of what a depth sensor buys",
         "real", dataset="TUM RGB-D (freiburg1_desk, Sturm et al. 2012)", license="CC BY 4.0 (TUM RGB-D)"),
]
