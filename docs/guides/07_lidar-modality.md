# 07 · The LiDAR modality (bake LiDAR, and the KISS-ICP swap)

The lab's second modality: consume **actual LiDAR scans** and estimate the trajectory + registered map by
point-to-plane ICP. This guide is how to bake LiDAR, synthetic (CI-safe) and real (`.bin`/`.npy`/`.ply`/
`.pcd`), and how to swap the built-in Open3D ICP for the SOTA **KISS-ICP** engine. The geometry is
[theory 04](../theory/04_lidar-odometry.md); the code is `data-pipeline/lidar3dlab/model/lidar.py`.

---

## 1. Why LiDAR is here

The camera engine reconstructs LiDAR-*like* clouds from video; this engine consumes real scans, which makes
the name "Lidar 3D" honest and gives the lab a **metric, lighting-invariant** trajectory to compare against
(and, later, to distill from, [theory 06 D2](../theory/06_novel-agenda.md)). LiDAR runs on **CPU** (a tiny
$6\times6$ solve per step); no GPU or checkpoint is needed. The pipeline routes to it whenever
`SequenceSpec.modality == "lidar"` (`stages/infer.py`).

## 2. Bake the synthetic LiDAR case (CI-safe)

```bash
.venv/Scripts/python.exe -m lidar3dlab.pipeline LID_synthetic
```

`model/lidar.py:_synthetic_scans` builds a corridor world (two walls, floor, ceiling), defines a forward
ground-truth path (~9 m), and renders each pose's range-limited, subsampled, noisy scan in the sensor frame.
Point-to-plane ICP then recovers the path and accumulates a height-colored registered map. This needs no
dataset and no GPU, so it is a CI control alongside `SYN_orbit`. Because a ground-truth path exists here, it is
also the honest place to compute ATE (the real example sequences carry no GT).

## 3. Bake real LiDAR (bring your own scans)

Point a case at a folder of scans (resolved via `LIDAR3D_DATA_ROOT`; the `kitti_lidar` case expects
`<DATA_ROOT>/lidar/kitti00/`):

```bash
LIDAR3D_DATA_ROOT=… .venv/Scripts/python.exe -m lidar3dlab.pipeline kitti_lidar
```

Supported scan formats (`model/lidar.py:_real_scans`, read in sorted filename order):

| Extension | Parse | Notes |
|---|---|---|
| `.bin` | `np.fromfile(p, float32).reshape(-1, 4)[:, :3]` | **KITTI Velodyne** `xyzi`; intensity dropped |
| `.npy` | `np.load(p)[:, :3]` | any `[N, ≥3]` array |
| `.ply` / `.pcd` | `open3d.io.read_point_cloud(p).points` | needs Open3D |

The scans go through CONTRACT 1 like any input ([guide 02](02_bring-your-own-data.md)): declare the case with
`modality="lidar"` and a `source_dir`; missing folders are rejected cleanly, short sequences flagged. To add
your own LiDAR case, follow [guide 06 §4](06_add-an-engine-or-case.md) with `modality="lidar"`.

## 4. What the engine does (per bake)

`model/lidar.py:reconstruct` (details in [theory 04](../theory/04_lidar-odometry.md)):

1. Load scans (synthetic or real).
2. For each consecutive pair, register `scan_i` onto `scan_{i-1}` with `_icp`: voxel-downsample (0.18 m), estimate
   target normals, point-to-plane ICP (`max_correspondence_distance = voxel*2.5`, `max_iteration=30`).
3. Compose the relative transforms into world poses (`poses[-1] @ rel`).
4. Transform each scan into the world frame, decimate, accumulate into a height-colored map; the camera
   centers form the odometry trajectory.
5. Return the standard `ReconResult` (so export/replay are identical to the camera lane).

Because it is scan-to-scan with no loop closure, **drift is visible** on long runs; that is deliberate (it is
the phenomenon the SOTA swap and the loop-closure agenda address).

## 5. The KISS-ICP swap (SOTA)

The built-in `_icp` is a correct, standard Open3D registration, deliberately simple and swappable behind the
same interface. The SOTA upgrade is **KISS-ICP** (RA-L 2023, PRBonn, MIT, `pip install kiss-icp`): pure-LiDAR,
IMU-free, ROS-optional, CPU-real-time odometry that reduces drift via an **adaptive threshold**, a
**constant-velocity motion model**, and a **local map** (scan-to-map, not just scan-to-scan). Its sibling
**KISS-SLAM** adds `MapClosures` loop closure + a g2o pose graph, exactly the loop-closure back-end the camera
engine lacks. **MAD-ICP** (RA-L 2024, BSD-3, `pip install mad-icp`) is the other strong CPU-only option. See
`docs/research/lidar-slam-and-perception.md` §2.1.

To swap:

1. **Pin** `kiss-icp` in the pipeline requirements and document it under `docs/frameworks/kiss-icp/`.
2. **Implement** the same step behind `lidar.reconstruct`: feed the loaded scans to the KISS-ICP pipeline,
   collect its per-scan poses, then build the same registered map + `ReconResult`. Keep the Open3D path as the
   dependency-light fallback (as the docstring intends), selectable by a knob or by availability.
3. **Do not** change the `ReconResult` shape, so export/replay/tests are unaffected.
4. **Test** on `LID_synthetic` (CPU, deterministic) first, then a real KITTI folder.

## 6. Honesty + metrics

Report ATE only where ground truth exists (the synthetic case, or a dataset that ships GT); otherwise
`stages/evaluate.py` reports "no GT" rather than faking a number. When you add KISS-ICP, the honest win is a
measured **drift/ATE reduction** vs the Open3D scan-to-scan baseline on the same scans, and a visibly
tighter registered map, cross-checked against the actual engine output, not merely asserted.
