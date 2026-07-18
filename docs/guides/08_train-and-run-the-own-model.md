# Guide: train and run our own depth+pose model (local)

The complete local workflow for the own model: train it on the GPU, bake a scene, tune the pose-refinement ladder,
add a new scene, and verify. Everything runs locally; only compact artifacts are committed (weights stay off-git).

## 0. One-time setup

```bash
# from the repo root
python -m venv .venv && .venv/Scripts/activate       # Windows; use bin/activate on POSIX
pip install -r data-pipeline/requirements.txt        # torch, torchvision, open3d, laspy, ...
```

Point the two env vars at your local data + model volumes (never hard-code machine paths in the repo):

```bash
export LIDAR3D_DATA_ROOT="/path/to/data"     # holds train/tum-rgbd, train/icl-nuim, train/7scenes, train/tartanground
export LIDAR3D_MODELS_ROOT="/path/to/models" # where checkpoints are written/read
```

## 1. Train the model

```bash
cd data-pipeline
python -m lidar3dlab.train.train_depthpose --backbone resnet18 --use_icl \
  --epochs 12 --batch 6 --lr 1e-4 --size 224
```

Key flags:

| Flag | Meaning |
|---|---|
| `--backbone {scratch,resnet18}` | from-scratch UNet (desde cero) or a pretrained ImageNet ResNet-18 (sharper depth) |
| `--pose_head {siamese,corr}` | global-pooled Siamese MLP (default, best so far) or a local correlation cost volume (experimental; see model history) |
| `--use_icl` | add ICL-NUIM synthetic perfect-depth pairs to the real TUM data |
| `--epochs / --batch / --lr / --size` | optimisation knobs (8 GB-safe: batch 6 at size 224) |
| `--smoke` | one tiny step, no checkpoint (CI/plumbing check) |

Training uses **best-checkpoint early stopping** (the held-out `long_office` ATE is evaluated each epoch; the
checkpoint is saved only when it improves). Outputs under `LIDAR3D_MODELS_ROOT/own-depthpose/`:

- `own-depthpose.pt` — the canonical file the engine loads.
- `own-depthpose-<variant>-<runid>.pt` — a **unique per-run archive** (never clobbered, so no model is ever lost).
- `own-depthpose.meta.json` — a tiny sidecar (backbone, pose_head, ATE, data) that the pipeline reads for an
  accurate engine label.
- `experiments.jsonl` — one appended line per epoch (the full training history, fed to the web Model-history tab).

## 2. Bake a scene (offline precompute)

```bash
python -m lidar3dlab.pipeline OWN_tum_desk        # one case
python -m lidar3dlab.pipeline all                 # every case (rebuilds index.json)
```

The engine runs the model over the ordered RGB frames, refines the poses, unprojects a fused RGB cloud, and writes
the compact trace (CONTRACT 2) + manifest. Then build the Potree octree for the scalable renderer:

```bash
export LIDAR3D_POTREECONVERTER="…/PotreeConverter.exe"   # native binary
export LIDAR3D_PC_TMP="…/pc_tmp"                          # a clean temp dir (must exist)
python -m lidar3dlab.potree OWN_tum_desk
```

## 3. Tune the pose-refinement ladder

The engine refines the model's poses before fusing. Toggle the rungs with env vars (see
[models/01](../models/01_own-depth-pose.md) for the theory):

| Env var | Default | Effect |
|---|---|---|
| `LIDAR3D_OWN_ICP` | `1` | frame-to-frame point-to-plane ICP (local drift removal). `0` = raw model poses. |
| `LIDAR3D_OWN_GLOBAL` | `0` | D1 global pose-graph + loop closure. Turn on for looping trajectories once poses are accurate. |
| `LIDAR3D_OWN_TSDF` | `0` | TSDF volumetric fusion (denoised surface). Turn on once poses are sub-voxel accurate. |
| `LIDAR3D_VERBOSE` | `0` | print loop-closure counts / fallbacks. |

At the current monocular pose accuracy (~0.37 m ATE) ICP is the robust default; D1/TSDF are opt-in and become the
default once a stronger pose model lands (see the model history for why).

## 4. Add a new scene

A scene is any folder of ordered RGB frames. Add a `_own(...)` case in `cases/example_case.py`:

```python
_own("OWN_my_scene", "tum-rgbd/rgbd_dataset_freiburg2_desk/rgb",
     "what a domain expert should see",
     "TUM RGB-D (freiburg2_desk, Sturm et al. 2012)", "CC BY 4.0 (TUM RGB-D)", _TUM2,
     frames=240, glob="", max_depth=6.0)
```

- `intr` (5th arg): the dataset's real intrinsics `"fx,fy,cx,cy,W,H"` (a wrong FoV misaligns frames). Presets:
  `_TUM1/_TUM2/_TUM3`, `_S7` (7-Scenes), `_ICL`.
- `glob`: `"*.color.png"` when the folder mixes files (7-Scenes); empty for a pure RGB folder.
- `max_depth`: drop far points (they amplify pose error into scatter).

Then bake it (step 2). Frames are natural-sorted, so numeric names (`0.png … 1508.png`) order correctly.

## 5. Verify + deploy

Build the SPA (which copies `data/derived` into `public/`) and screenshot-verify before deploy:

```bash
cd frontend && npm run build && npm run preview
# capture with tools/visual-verify, exercise every scene, then PR develop -> main
```

See [guides/01](01_precompute-pipeline.md) for the pipeline internals and
[guides/06](06_add-an-engine-or-case.md) for adding a whole new engine.
