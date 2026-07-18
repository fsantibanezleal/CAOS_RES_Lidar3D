# Cases + categories (the scenarios)

Each case (`data-pipeline/lidar3dlab/cases/example_case.py`) declares a **CATEGORY** (the reconstruction problem-type
taxonomy), its params, an expected band (what a domain expert should see), a real|synthetic flag, and its dataset +
license. `registry.list_categories()` groups them. The **App shows ONE selected case**; **Experiments/Benchmark show
cross-case summaries** (never mixed into the App). A scene is any folder of ordered RGB frames (or LiDAR scans); the
model-agnostic engine handles the rest.

## Coverage matrix (14 deployed scenarios)

| id | category | engine | dataset | held-out? | expected band |
|---|---|---|---|---|---|
| `SYN_orbit` | synthetic camera (CPU/CI) | synthetic corridor | CAOS synthetic | n/a | forward tunnel, textured walls, ~5 m, runs on CPU in <1 s |
| `LID_synthetic` | synthetic LiDAR (CPU/CI) | Open3D ICP | CAOS synthetic | n/a | forward LiDAR sweep, ICP odometry recovers ~9 m, height-colored |
| `kitti_lidar` | real LiDAR odometry | Open3D ICP | KITTI odometry | n/a | `.bin/.npy/.ply` scans, ICP odometry + registered map (bakes when present) |
| `oxford` / `university` / `loop` / `courthouse` | real camera (GPU) | lingbot-map GCT | lingbot-map examples | n/a | outdoor walk / courtyard / revisit (loop) / facade orbit |
| **`OWN_tum_desk`** | ours: trained depth+pose | our net | TUM freiburg1_desk | no (in train) | a desk sweep; the reference own scene |
| **`OWN_tum_office`** | ours: trained depth+pose | our net | TUM freiburg3_long_office | **YES** (the eval seq) | honest generalization on the held-out office |
| **`OWN_tum_xyz`** | ours: trained depth+pose | our net | TUM freiburg1_xyz | no | tight translational calibration sweep, near-planar desktop |
| **`OWN_tum_desk2`** | ours: trained depth+pose | our net | TUM freiburg2_desk | no | a larger, wider desk workspace, more depth range |
| **`OWN_tum_pioneer`** | ours: trained depth+pose | our net | TUM freiburg2_pioneer_slam | no | a robot SLAM run through a hall, the hardest drift test |
| **`OWN_7scenes_heads`** | ours: trained depth+pose | our net | 7-Scenes heads | **YES** (never trained) | a tight cluttered desk corner (relocalization data) |
| **`OWN_7scenes_stairs`** | ours: trained depth+pose | our net | 7-Scenes stairs | **YES** (never trained) | a repetitive staircase, a texture-ambiguity test |
| **`OWN_icl_living`** | ours: trained depth+pose | our net | ICL-NUIM living-room | no (in train) | a synthetic living room; the cleanest own cloud (perfect depth) |

## What the scenarios span

- **Modalities**: camera (synthetic, lingbot SOTA, and our model) + LiDAR (synthetic + real KITTI).
- **Engines**: control (synthetic), classical (Open3D ICP), SOTA reference (lingbot-map), and OURS (trained
  depth+pose) — all behind one `reconstruct(spec) -> ReconResult` contract, so they are directly comparable.
- **Honesty axis**: 4 of the own scenes are **truly held-out** (freiburg3 office, 7-Scenes heads/stairs), so they
  test generalization, not memorization; the rest are in the training distribution and labelled as such.
- **Difficulty axis**: from tight calibration motion (xyz) through desk sweeps to a long fast robot hall
  (pioneer) — the drift stress-test.
- **Datasets + licenses**: every case surfaces its dataset + license in the App (see
  [models/04_datasets.md](../models/04_datasets.md)).

Each own scene is baked at 240 frames with real intrinsics + the ICP-refined pose ladder (see
[models/01_own-depth-pose.md](../models/01_own-depth-pose.md)). Add a scenario by pointing the engine at a new RGB
folder — see [guides/08](../guides/08_train-and-run-the-own-model.md).
