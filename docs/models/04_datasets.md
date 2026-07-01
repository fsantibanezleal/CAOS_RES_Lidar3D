# Datasets (model data)

The data behind OUR depth+pose model: what trains it, what it reconstructs, the formats, the real intrinsics, and the
licenses. Everything lives under `LIDAR3D_DATA_ROOT/train/` (never a machine path in the repo); raw data stays off-git,
only compact derived artifacts are committed.

## Training data

| Dataset | Type | Seqs used | Frames | GT depth | GT pose | Loader |
|---|---|---|---|---|---|---|
| **TUM RGB-D** | real indoor RGB-D | 11 (fr1/fr2/fr3) | ~22k | registered sensor depth (scale 5000) | motion-capture trajectory | `TUMPairs` |
| **ICL-NUIM** | synthetic indoor | living-room | 1509 | **perfect** (rendered) | perfect (rendered) | `ICLPairs` |
| **7-Scenes** | real indoor (held-out) | heads, stairs | 1500 | Kinect depth | camera pose | reconstructed only |

TUM is the backbone of training: RGB + registered metric depth + a ground-truth camera trajectory, so both the depth
head (supervised metric depth) and the pose head (relative pose from the trajectory) get real supervision. ICL-NUIM
adds synthetic *perfect*-depth pairs (a clean supervisory signal). The held-out sequence for the ATE is
`freiburg3_long_office_household` (pinned, so `OWN_tum_office` stays a true held-out scene).

The 11 TUM sequences: `freiburg1_{360,desk,room,xyz}`, `freiburg2_{desk,desk_with_person,large_no_loop,pioneer_slam}`,
`freiburg3_{long_office_household,nostructure_texture_near_withloop,structure_texture_far}`. More can be dropped in and
are auto-discovered by `list_sequences()`.

## Real camera intrinsics

The unprojection uses each dataset's **real** intrinsics (a wrong fixed FoV systematically misaligns frames). Native
(640×480) `fx, fy, cx, cy`, scaled to the working resolution at bake time:

| Dataset | fx | fy | cx | cy |
|---|---|---|---|---|
| TUM freiburg1 | 517.306 | 516.469 | 318.643 | 255.314 |
| TUM freiburg2 | 520.909 | 521.007 | 325.141 | 249.701 |
| TUM freiburg3 | 535.4 | 539.2 | 320.1 | 247.6 |
| 7-Scenes (Kinect) | 585 | 585 | 320 | 240 |
| ICL-NUIM | 481.2 | 480.0 | 319.5 | 239.5 |

## Formats

- **TUM**: `rgb.txt` / `depth.txt` (`timestamp filename`), `groundtruth.txt` (`timestamp tx ty tz qx qy qz qw`,
  camera-to-world). Frames associated by nearest timestamp; depth = uint16 / 5000 metres. `rgb/` is a pure image
  folder (timestamped names sort correctly).
- **ICL-NUIM**: `associations.txt` pairs rgb<->depth by index; `livingRoom*.gt.freiburg` holds the poses; depth PNG
  scale 5000. Numeric names (`0.png … 1508.png`) need natural sort (the engine does this).
- **7-Scenes**: `seq-XX/frame-NNNNNN.{color.png,depth.png,pose.txt}` (color/depth/pose mixed in one folder), so a
  case uses `frame_glob="*.color.png"` to pick only the RGB frames.

## Licenses (surfaced in the App, to avoid problems)

| Dataset | License / terms |
|---|---|
| TUM RGB-D | CC BY 4.0 (Sturm et al. 2012) |
| ICL-NUIM | research use (Handa et al. 2014) |
| 7-Scenes | Microsoft Research 7-Scenes, research use (Shotton et al. 2013) |
| KITTI (LiDAR) | CC BY-NC-SA 3.0 (Geiger et al. 2012) |
| lingbot-map examples | Apache-2.0 |

Each deployed case shows its dataset + license in the App's reconstruction stats.

## Bigger data (roadmap)

The classic benchmarks above are small. The real lever for pose accuracy (which bounds a clean fused surface) is more,
broader data. Candidates:

- **TartanAir** — huge synthetic VO/SLAM set with perfect depth + pose; needs the official `tartanair_tools`
  downloader (Azure blob / SAS), not a direct download.
- **ScanNet / ScanNet++** — large real indoor RGB-D; needs a signed terms-of-use agreement.
- **ARKitScenes** — very large real indoor with iPhone LiDAR; downloadable via Apple's script.

Adding any of these means a small loader (their pose/depth formats differ from TUM) plus a retrain; see the training
guide. The append-only experiments log keeps every run, so scaling data is a tracked, reversible experiment.
