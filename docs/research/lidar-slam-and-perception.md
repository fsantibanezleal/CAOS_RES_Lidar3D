# LiDAR-based 3D Perception, Odometry/SLAM & Foundation Models: State of the Art

**Survey for the "Lidar 3D" research lab + interactive web app**
**Scope:** LiDAR / point-cloud side + camera-LiDAR fusion (camera-only feed-forward 3D reconstruction is covered by a separate analyst).
**Date:** 2026-06-29
**Author:** Research analyst (LiDAR track)

> Verification convention: every non-trivial claim is tagged **[verified]** (read on a primary GitHub README / arXiv abstract / official dataset page during this research) or **[assumed]** (inferred, from secondary sources, or approximate). Benchmark numbers vary by split (val vs test) and test-time augmentation; treat single-decimal mIoU/drift figures as indicative, not exact.

---

## 1. Executive summary of the LiDAR-3D landscape

The LiDAR-3D field splits into four layers that map almost 1:1 onto what the "Lidar 3D" app will need to demonstrate. They are **largely independent code-bases** with very different practicality profiles for a browser-facing Python research repo.

### 1.1 Odometry & SLAM (estimate the trajectory + build the map)
This is the most "productizable" layer. The state of the art has bifurcated:

- **Pure-LiDAR odometry/SLAM** (no IMU required): the modern reference is the **KISS family from PRBonn**, **KISS-ICP** (RA-L 2023) for odometry and **KISS-SLAM** (IROS 2025) for full loop-closed SLAM. Both are **point-to-point ICP done carefully**, ship as **pip-installable, ROS-optional, MIT-licensed Python packages that run real-time on a CPU**. **MAD-ICP** (RA-L 2024, BSD-3, pip `mad-icp`) is the other strong CPU-only pure-LiDAR contender. The classical lineage (**LOAM to LeGO-LOAM to CT-ICP**) is feature-/edge-plane-based and mostly ROS1-bound; it is now a baseline rather than the frontier.
- **LiDAR-inertial odometry (LIO)**, tightly couples an IMU, much higher robustness under aggressive motion: the **HKU-MARS line FAST-LIO2 then Point-LIO** (iterated-EKF, 100+ Hz) and **LIO-SAM / DLIO / GLIM** (factor-graph + GPU scan-matching in GLIM). These dominate field robotics but **almost all require ROS/ROS2 and an IMU stream**, which makes them awkward to embed in a browser demo.
- **Neural / implicit SLAM** is an emerging third branch: **PIN-SLAM** (TRO 2024, MIT) uses a point-based implicit neural map for global consistency; **NeRF-LOAM**, **KN-LIO** and 2026 test-time-adapted global-context methods are research-grade. These need a GPU and are not yet "just works."

**Key practical fact:** for a CPU-only, ROS-free, permissively-licensed engine you can `pip install` and drive from Python, the realistic set is **KISS-ICP, KISS-SLAM, MAD-ICP** (all three) and, GPU-permitting, **PIN-SLAM**.

### 1.2 Place recognition & loop closure (recognize a revisited place)
A self-contained sub-field feeding the SLAM back-end. Two camps:

- **Hand-crafted, CPU-light, no training:** **Scan Context / Scan Context++** (IROS 2018 / TRO 2021), the de-facto standard rotation-invariant descriptor, runs 10–15 Hz on CPU. **BoW3D** (RA-L 2022) for real-time bag-of-words loop closing. **RING / RING++** (TRO 2023) roto-translation-invariant. PRBonn's **MapClosures** (used inside KISS-SLAM) belongs here.
- **Learned global descriptors (GPU to train, often GPU to query):** **OverlapTransformer** (RA-L 2022, range-image transformer, yaw-invariant), **LoGG3D-Net** (ICRA 2022, sparse point-voxel U-Net), and the 2025 wave of **BEV-based** methods (**BEVPlace++** TRO 2025, **S-BEVLoc**, **UniLGL**, **ForestLPR**) that fold in vision foundation backbones.

### 1.3 Semantic / panoptic perception (label every point)
The most benchmark-driven layer (SemanticKITTI / nuScenes-lidarseg / Waymo). State of the art on SemanticKITTI sits around **74–76 mIoU (val)** for the strongest single models:

- **Point Transformer V3 (PTv3)** (CVPR 2024 Oral, MIT) is the current backbone of record, serialized point attention, scales to large scenes, tops several leaderboards (1st place Waymo 2024 semseg via "PTv3-Extreme"). It is the natural perception engine for the lab.
- **Range-/projection-view & sparse-conv alternatives:** **SphereFormer** (CVPR 2023, radial-window transformer), **Cylinder3D** (CVPR 2021, cylindrical sparse conv, Apache-2.0), **WaffleIron** (ICCV 2023, dense-conv MLP-mixer-like, Apache-2.0), **RangeFormer** (ICCV 2023), **FRNet** (frustum-range, fast), and the cross-modal **2DPASS** (ECCV 2022, distills 2D priors).
- These generally **need a GPU and a sparse-conv stack** (spconv / Minkowski / Pointcept's serialized attention). Inference of a single scan can be exported to **ONNX** for a browser-ish demo, but training is GPU-cluster territory.

### 1.4 Self-supervised pretraining & "point-cloud foundation models"
The fastest-moving layer and the one that justifies the word "foundation" in the lab name:

- **Sonata** (CVPR 2025 Highlight, Meta/FAIR, PTv3 encoder-only) is the headline 3D SSL result, self-distillation over 140k point clouds, **triples ScanNet linear-probe accuracy (21.8 to 72.5%)** by defeating the "geometric shortcut." Pretrained PTv3 weights are released.
- **Concerto** (NeurIPS 2025, Pointcept) extends this with **joint 2D-3D** self-distillation (+4.8% over best 3D SSL, 80.7 mIoU ScanNet fine-tuned). **Utonia** (ICML 2026) is the latest in the same lineage.
- **Distillation-from-2D-VFM line (Valeo):** **Seal** (NeurIPS 2023 Spotlight, SAM+DINOv2 to LiDAR), **ScaLR** ("Three Pillars", DINOv2 to WaffleIron), **ALSO** (occupancy-based SSL, CVPR 2023). **PonderV2** (T-PAMI 2025, neural-rendering pretraining). **GrowSP** (CVPR 2023, fully unsupervised segmentation).

> **Bottom line for the app:** odometry/SLAM is where LiDAR-only, CPU, ROS-free, permissive code actually exists and can run live in a Python+browser stack (KISS-ICP/KISS-SLAM/MAD-ICP). Perception (PTv3) and foundation models (Sonata) are where the "advanced" story is, but they are GPU/ONNX-offline experiences. The app should pair a **live LiDAR-odometry workbench** with an **offline PTv3/Sonata perception+embedding showcase**.

---

## 2. Comparison tables

### 2.1 Odometry / SLAM

| Method | arXiv / venue | Modality | Core idea | Real-time / CPU | ROS dep. | Code + license | Notes |
|---|---|---|---|---|---|---|---|
| **KISS-ICP** | 2209.15397 · RA-L 2023 | **LiDAR-only** | Point-to-point ICP + adaptive threshold + constant-velocity motion comp; "no tuning" | **Yes, CPU real-time** [verified] | **ROS-optional** (pip + CLI `kiss_icp_pipeline`) [verified] | PRBonn/kiss-icp · **MIT** [verified] | Standalone Python pkg `kiss-icp`; loaders incl. KITTI/rosbag/ply. Best "just works" baseline. |
| **KISS-SLAM** | 2503.12660 · IROS 2025 | **LiDAR-only** | KISS-ICP odometry + MapClosures loop closure + g2o pose-graph | **Yes (CPU)** [assumed, built on CPU stack] | **ROS-optional** (pip `kiss-slam`) [verified] | PRBonn/kiss-slam · **MIT** [verified] | Full SLAM w/ loop closure; "enhanced generalization, little/no tuning." No IMU. |
| **MAD-ICP** | 2405.05828 · RA-L 2024 | **LiDAR-only** | ICP on a multi-resolution **kd-tree surfel** map; "anytime real-time" | **Yes, CPU** (tunable `num_cores`) [verified] | **ROS-optional** (pip `mad-icp`) [verified] | rvp-group/mad-icp · **BSD-3-Clause** [verified] | Inputs: Rosbag1/2, KITTI bin, MulRan. Strong pure-LiDAR accuracy. |
| **FAST-LIO2** | 2107.06829 · T-RO 2022 | **LiDAR-inertial** | Tightly-coupled iterated-EKF, direct (no features), ikd-Tree map; up to 100 Hz | **Yes, 100 Hz**; runs RPi/Jetson (needs IMU) [verified] | **ROS1 + official ROS2 branch** [verified] | hku-mars/FAST_LIO · **GPL-2.0** [verified] | Field-robotics workhorse; needs IMU + ROS. Copyleft. |
| **Point-LIO** | AISY 2023 (DOI 10.1002/aisy.202200459) | **LiDAR-inertial** | Point-by-point EKF update (no frame accumulation) to 4–8 kHz output, handles saturation/75 rad/s | Yes, very high bandwidth (needs synced IMU) [verified] | **ROS1 only** [verified] | hku-mars/Point-LIO · **GPL-2.0** [verified] | Extreme-dynamics robustness; IMU + ROS. Copyleft. |
| **LIO-SAM** | 2007.00258 · IROS 2020 | **LiDAR-inertial** (needs **9-axis IMU**, +GPS opt.) | Factor-graph smoothing (GTSAM), keyframe scan-matching, loop closure | "10× faster than real-time" (needs IMU) [verified] | **ROS1** (+ros2 branch) **+ GTSAM** [verified] | TixiaoShan/LIO-SAM · **BSD-3-Clause** [verified] | Very popular; hard ROS+GTSAM dependency. |
| **DLIO** | 2203.03749 · ICRA 2023 | **LiDAR-inertial** (6-axis IMU) | Direct continuous-time motion correction, fast point-to-plane GICP | Real-time (needs IMU) [verified] | **ROS1** (+`feature/ros2` branch) [verified] | vectr-ucla/direct_lidar_inertial_odometry · **MIT** [verified] | Lightweight; from the DLO authors. |
| **GLIM** | RAS 2024 (Koide et al.) | **LiDAR-only OR LiDAR-inertial** (IMU optional) | **GPU (CUDA)-accelerated** voxel scan-matching factors + global optimization; very robust | Real-time; **GPU optional** (CPU path runs on RPi) [verified] | **ROS1 + ROS2 + non-ROS C++ API** [verified] | koide3/glim · **MIT** [verified] | Extensible multi-sensor; GPU recommended. Configurable modality. |
| **LOAM / LeGO-LOAM** | LOAM RSS 2014; LeGO-LOAM IROS 2018 | **LiDAR (IMU optional)** | Edge/planar feature extraction + scan-to-map; LeGO-LOAM adds ground seg + lightweight | Yes, real-time 6-DoF (embedded-class) [verified] | **ROS1 only** [verified] | RobustFieldAutonomyLab/LeGO-LOAM · **BSD-3-Clause** [verified] | The historical baseline lineage; ROS1-bound. |
| **CT-ICP** | 2109.12979 · ICRA 2022 | **LiDAR-only** (continuous-time) | Elastic per-scan continuous-time ICP + loop closure | Real-time elastic odometry (CPU) [verified] | **Standalone C++** (no ROS; ROS wrapper opt.); **Python binding `pyct_icp` marked broken** [verified] | jedeschaud/ct_icp · **MIT** [verified] | **KITTI 0.59% avg RTE**, top public-code on KITTI odometry leaderboard [verified]. C++ build. |
| **PIN-SLAM** | TRO 2024 | **LiDAR-only** | Point-based **implicit neural** map, elastic deformation on loop closure to global consistency | Sensor-rate **on a GPU**; CPU = much slower [verified] | **ROS-optional** (standalone `pin_slam.py`) [verified] | PRBonn/PIN_SLAM · **MIT** [verified] | Many loaders (KITTI/NCD/rosbag/ply/las). Best "neural SLAM you can actually run." |

*Modality legend: LiDAR-only = no IMU needed; LiDAR-inertial = requires a synchronized IMU.*

### 2.2 Place recognition / loop closure

| Method | arXiv / venue | Type | Core idea | GPU? | Code + license | Weights |
|---|---|---|---|---|---|---|
| **Scan Context** | IROS 2018 | Hand-crafted | Polar bird's-eye ring-key descriptor; rotation-invariant via column shift | No (10–15 Hz CPU) [verified] | gisbi-kim/scancontext (C++/MATLAB/Py) · **CC BY-NC-SA 4.0** [verified] | n/a (no learning) |
| **Scan Context++** | T-RO 2021 | Hand-crafted | Adds lateral/translation invariance + semantic variants | No (CPU) [verified] | same repo family · **CC BY-NC-SA 4.0** [assumed] | n/a |
| **BoW3D** | 2208.07473 · RA-L 2022 | Hand-crafted (online) | Bag-of-words over LinK3D features; corrects 6-DoF loop pose in real time | No (CPU real-time) [verified] | YungeCui/BoW3D · **GPLv3** [assumed] | n/a |
| **RING / RING++** | TRO 2023 | Hand-crafted | Roto-translation-invariant Gram (Radon/Fourier) for global localization on sparse maps | No (CPU) [assumed] | lus6-Jenny/RING · **MIT** [assumed] | n/a |
| **OverlapTransformer** | 2203.03397 · RA-L 2022 | **Learned** | Transformer on LiDAR range image to yaw-invariant global descriptor; <4 ms | Recommended (CPU viable) [verified] | haomo-ai/OverlapTransformer · **GPLv3** [verified] | Yes (KITTI, Haomo) [verified] |
| **LoGG3D-Net** | 2109.08336 · ICRA 2022 | **Learned** | Sparse point-voxel U-Net, local-consistency + global-contrastive loss | Yes (training/inference) [verified] | csiro-robotics/LoGG3D-Net · LICENCE file present [verified] | Yes, 7 ckpts ~**741 MB** (KITTI×6, MulRan×1) [verified] |
| **BEVPlace++** | TRO 2025 | **Learned** | Fast/robust/lightweight BEV global localization for ground vehicles | Yes [assumed] | (Repo per paper) [assumed] | [assumed] |
| **S-BEVLoc / UniLGL / ForestLPR** | 2025 (various) | **Learned** | BEV self-supervision / VFM-backbone fusion / forest multi-BEV | Yes [assumed] | per paper [assumed] | per paper [assumed] |

### 2.3 Semantic / panoptic segmentation & perception

| Method | arXiv / venue | Task | SemanticKITTI mIoU | nuScenes-lidarseg mIoU | Backbone | GPU | Code + license | Weights |
|---|---|---|---|---|---|---|---|---|
| **Point Transformer V3 (PTv3)** | 2312.10035 · CVPR 2024 Oral | sem. seg (also indoor) | **72.3 val** (w/ PPT) [verified] | **80.4 val** (w/ PPT); 80.3 base [verified] | Serialized point attention (no KNN) | Yes | Pointcept/PointTransformerV3 · **MIT** [verified] | Yes (HF/Pointcept; README warns some links "temporarily invalid") [verified] |
| **PTv3-Extreme** | 2407.15282 · 2024 | sem. seg | leaderboard-topping [verified] | n/a | PTv3 + multi-frame/ensemble | Yes | Pointcept · **MIT** [verified] | 1st place Waymo 2024 semseg [verified] |
| **SphereFormer** | 2303.12766 · CVPR 2023 | sem. seg (+det) | **67.8 / 69.0 TTA (val)**; 74.8 (test/paper) [verified] | **78.4 / 79.5 TTA (val)**; 81.9 (test) [verified] | Sparse-conv U-Net + radial-window transformer | Yes | dvlab-research/SphereFormer · **Apache-2.0** [verified] | Yes (nuScenes+SemKITTI; Waymo withheld) [verified] |
| **Cylinder3D** | 2011.10033 · CVPR 2021 | sem. seg / panoptic | ~67–68 (test) [verified-range] | **77.9 (test)** [verified] | Cylindrical asymmetrical sparse conv | Yes | xinge008/Cylinder3D · **Apache-2.0** [verified] | Yes (GDrive/Baidu) [verified] |
| **WaffleIron** | 2301.10100 · ICCV 2023 | sem. seg | **68.0 val** [verified] | **77.6 val** [verified] | Dense 2D-conv "waffle" + MLP (no sparse conv) | Yes | valeoai/WaffleIron · **Apache-2.0** [verified] | Yes (kitti + nuscenes tar.gz) [verified] |
| **RangeFormer** | 2303.05367 · ICCV 2023 | sem. + panoptic seg | **73.3 (test)** [verified] | ~73 val (claimed) [verified-secondary] | Range view (full-cycle) | Yes | **NO official repo** (project page + 3rd-party reimpls only) [verified] | No [verified] |
| **FRNet** | 2312.04484 · 2024 | sem. seg (fast/real-time) | **68.7 val / 73.3 test** [verified] | **79.0 val / 82.5 test** [verified] | Frustum-range (FFE + frustum-point fusion) | Yes | Xiangxu-0103/FRNet · **Apache-2.0** [verified] | Yes (GDrive) [verified] |
| **2DPASS** | 2207.04397 · ECCV 2022 | sem. seg | **70.7 / 72.0 TTA (val)** [verified] | **78.0 / 80.5 TTA (val)** [verified] | Sparse conv + 2D-prior distill (3D-only infer) | Yes (2D only at train) | yanx27/2DPASS · **MIT** [verified] | Yes (Model Zoo, GDrive) [verified] |

> Note: SemanticKITTI **test** leaderboard numbers (single decimal) drift over time and depend on TTA/ensembling; the **val** numbers a research repo will reproduce are typically a few points lower. PTv3's headline advantage is *consistency across indoor+outdoor* and scalability, not just peak mIoU.

### 2.4 Self-supervised pretraining / foundation models

| Method | arXiv / venue | Idea | Headline result | Backbone | Code + license | Weights |
|---|---|---|---|---|---|---|
| **Sonata** | 2503.16429 · CVPR 2025 Highlight | Self-distillation defeating the "geometric shortcut"; 140k clouds | **ScanNet linear-probe 21.8 to 72.5%** (3.3×) [verified]; ~2× perf at 1% data; SOTA fine-tune indoor+outdoor [verified] | **PTv3 encoder-only** | facebookresearch/sonata · **code Apache-2.0, weights CC-BY-NC 4.0** [verified] | **Yes, pretrained PTv3 encoder** (HF `facebook/sonata`; size not in README) [verified] |
| **Concerto** | 2510.23607 · NeurIPS 2025 | Joint **2D-3D** self-distillation (intra-modal 3D + cross-modal 2D-3D) | LP +14.2% vs SOTA-2D, **+4.8% vs SOTA-3D**; **80.7 mIoU ScanNet** (fine-tune); no outdoor LiDAR in abstract [verified] | **PTv3 encoder-only** + 2D | Pointcept/Concerto · **code Apache-2.0, weights CC-BY-NC 4.0** [verified] | Yes (HF: 39M/108M/208M) [verified] |
| **Utonia** | **2603.03283** · ICML 2026 | "One encoder for all point clouds": single PT encoder jointly pretrained across remote-sensing/outdoor-LiDAR/indoor/CAD/video-lifted | Improved cross-domain transfer; no SemKITTI/nuScenes in abstract [verified] | PTv3-family | Pointcept/Utonia · license unread [assumed] | Yes (HF `Pointcept/Utonia`) [verified] |
| **PonderV2** | 2310.08586 · T-PAMI 2025 | Universal pretraining via differentiable **neural rendering** (3D↔2D) | SOTA on 11 benchmarks (no per-number in README/abstract) [verified] | Sparse-conv (SparseUNet) | OpenGVLab/PonderV2 · **MIT** [verified] | Yes (`docs/model_zoo.md`) [verified] |
| **Seal** | 2306.09347 · NeurIPS 2023 Spotlight | Distill **SAM/DINOv2** via 2D superpixel to 3D superpoint; spatial contrast + temporal consistency | nuScenes **LP 45.0**; SemKITTI LP@1% 46.6, full FT 75.1 [verified] | MinkUNet student | youquanl/Segment-Any-Point-Cloud · **CC-BY-NC-SA 4.0** [verified] | README unclear on downloadable ckpts [verified] |
| **ScaLR** ("Three Pillars") | 2310.17504 · CVPR 2024 | Scale 2D+3D backbones + diverse data; distill **DINOv2** | nuScenes **LP 67.8 / FT 78.4**; SemKITTI **LP 55.8 / FT 65.8** [verified] | WaffleIron (WI-48-768) | valeoai/ScaLR · **Apache-2.0** [verified] | Yes (WI-48-768 from DINOv2 ViT-L/14) [verified] |
| **ALSO** | 2212.05867 · CVPR 2023 | Self-supervision by **occupancy / surface reconstruction** | Pretrain boosts det+seg (no per-number in README) [verified] | MinkUNet34/SPVCNN (seg); SECOND/PV-RCNN (det) | valeoai/ALSO · **Apache-2.0** [verified] | Yes (seg + det weights) [verified] |
| **GrowSP** | 2305.16404 · CVPR 2023 | **Fully unsupervised** semantic seg via growing superpoints | Beats unsup baselines, approaches supervised PointNet [verified] | Sparse-conv + clustering | vLAR-group/GrowSP · **CC-BY-NC-SA 4.0** [verified] | Yes (GDrive; S3DIS/ScanNet/SemKITTI) [verified] |

### 2.5 Camera-LiDAR fusion / BEV perception

| Method | arXiv / venue | Task | nuScenes | GPU/stack | Code + license | Weights |
|---|---|---|---|---|---|---|
| **BEVFusion (MIT)** | 2205.13542 · ICRA 2023 | Detection + BEV map seg | **det ~68.5 mAP / 71.4 NDS (val)**; map seg **~63 mIoU** [verified] | GPU; mmdet3d + custom CUDA BEV-pool | mit-han-lab/bevfusion · **Apache-2.0** [verified] | Yes (Dropbox ckpts) [verified] |
| **BEVFusion (ADLab)** | 2205.13790 · NeurIPS 2022 | Detection | ~69.6 mAP / 72.1 NDS (test, TTA) [verified] | GPU; mmdet3d | ADLab-AutoDrive/BEVFusion · per repo [assumed] | Yes [assumed] |
| (direction) **unified driving perception** | n/a | det/seg/occupancy/forecast | n/a | GPU | OpenPCDet / mmdet3d ecosystems | n/a |

### 2.6 Open-vocabulary / language-grounded 3D (relevance: medium)

| Method | arXiv / venue | Idea | Code |
|---|---|---|---|
| **OpenScene** | 2211.15654 · CVPR 2023 | Co-embed 3D points with CLIP text/image features to zero-shot open-vocab queries on 3D scenes | pengsongyou/openscene [verified] |
| **Open3DIS** | 2312.10671 · CVPR 2024 | Open-vocab 3D instance seg with 2D mask guidance | per paper |
| **HOV-SG** | 2403.17846 · RSS 2024 | Hierarchical open-vocab 3D scene graphs for nav | hovsg/HOV-SG [verified] |
| **3D-AVS** | 2406.09126 | LiDAR auto-vocabulary segmentation | per paper |

> Open-vocab work is mostly **indoor/RGB-D-centric** (OpenScene, Open3DIS, HOV-SG). For automotive **LiDAR**, the practical "language-grounded" route is via the VFM-distillation models (Seal/ScaLR) rather than LERF-style radiance fields.

---

## 3. Datasets

| Dataset | Sensor(s) | Total size | Gated? | License | Task(s) | URL | Smallest demo chunk |
|---|---|---|---|---|---|---|---|
| **SemanticKITTI** | Velodyne HDL-64E (+ KITTI stereo/IMU) | **~84 GB** = 80 GB Velodyne + 179 MB labels + ~0.7 GB voxels + ~1 GB calib [verified]; add-on **<1 GB** if you hold KITTI | KITTI parent: free email reg for 80 GB zip; **labels direct** | CC BY-NC-SA (labels 4.0 / KITTI 3.0) | Semantic/panoptic seg, scene completion, MOS; odometry via KITTI | http://semantic-kitti.org/dataset.html | **One seq ~1–4 GB** (seq 08=val; 00–10 labelled) [approx] |
| **KITTI-360** | Velodyne HDL-64E + SICK 2D laser + 2 fisheye + perspective stereo + GPS/IMU | **~773 GB** full (raw+fused clouds+perspective+fisheye+2D/3D labels) [verified-secondary]; 3D-LiDAR-only subset tens of GB | **Registration** (account + purpose) [verified] | CC BY-NC-SA 3.0 | Sem/instance seg (2D+3D), detection, novel-view, semantic SLAM | https://www.cvlibs.net/datasets/kitti-360/ | `data_3d_raw` Velodyne for one drive ~a few GB [approx] |
| **nuScenes** (full) | 32-beam HDL-32E + 6 cam + 5 radar + GPS/IMU | **~300+ GB** trainval+test [approx]; **lidarseg** add-on ~0.5–1 GB labels [approx] | **Registration**, non-commercial [verified] | nuScenes/Motional non-commercial | Detection, tracking, lidarseg (sem+panoptic), prediction | https://www.nuscenes.org/nuscenes | n/a |
| **nuScenes-mini** | same (10 scenes, all sensors) | **~4 GB** (`v1.0-mini.tgz`) [verified] | **Registration** (free) | non-commercial | Demo/dev of all nuScenes tasks, **best small multimodal demo** | https://www.nuscenes.org/nuscenes | whole mini ~4 GB |
| **Waymo Open (Perception)** | 5× LiDAR + 5 cam | **~1 TB** full (2,030 seg × 20 s) [verified-secondary]; v2 Parquet selectively downloadable | **License gate** (Google acct + accept terms) [verified] | Waymo OD License (non-commercial) | Detection, tracking, semseg, occupancy | https://waymo.com/open/ | One `.tfrecord` segment (20 s) ~1–1.5 GB [approx] |
| **Newer College** | Ouster OS1-64 / OS0-128 + RealSense D435i or Alphasense 4-cam + LiDAR IMU | **~30–60 GB** rosbags whole collection [approx] | **Free** (download form, academic) [verified] | non-commercial academic | LiDAR/visual SLAM + odometry benchmark, reconstruction, place rec. | https://ori-drs.github.io/newer-college-dataset/ | Single sequence rosbag (e.g. "quad-easy") **~3–10 GB** [approx] |
| **Oxford Spires** | Hesai QT64 + 3 colour fisheye + MEMS IMU + survey TLS/RTK GT | **~10× Newer College** to order **~300–600 GB** [approx; only "~10×" published] | **Free** (GitHub + HF, academic) [verified] | CC BY-NC-SA 4.0 | Large-scale LiDAR-visual localisation, reconstruction, NeRF/3DGS, SLAM | https://dynamic.robots.ox.ac.uk/datasets/oxford-spires/ | One of 24 sequences from HF [approx] |
| **Argoverse 2** | 2× VLP-32C (64 beams) + 7 ring + 2 stereo cam | **Sensor = ~1 TB** (1,000 scen.) [verified]; **LiDAR-only = ~5 TB** (20k seq) [verified]; Forecasting ~58 GB | **Open, free via AWS S3, NO registration** [verified] | CC BY-NC-SA 4.0 | Detection, tracking, forecasting, self-sup LiDAR, point-cloud forecasting | https://www.argoverse.org/av2.html (`s3://argoverse/datasets/av2/`) | One scenario (~15 s) from S3 **~1 GB** [approx] |
| **Hilti SLAM Challenge** | PandarXT-32 / Robosense BPearl / Ouster OS0-64 + Alphasense 5-cam + IMU | 2022 **~159 GB** core (+88 GB extra); 2023 **~329 GB**; per-bag **6–80 GB** [verified] | **Open** (direct AWS S3, free) [verified] | CC BY-NC-SA 3.0 | LiDAR-inertial + visual-inertial SLAM benchmark (mm GT) | https://hilti-challenge.com/ | One smaller rosbag **~6–15 GB** [verified-range] |
| **Pandaset** | Pandar64 (mech.) + PandarGT (solid-state) + 6 cam + GPS/IMU | **~44.5 GB** (Hugging Face mirror) [verified] | **Open on HF** (no gate); pandaset.org/Scale portal deprecated | **CC BY 4.0** (+ terms) | Detection, semseg, multimodal fusion | https://huggingface.co/datasets/georghess/pandaset | One scene folder (1 of 103, 8 s) **~0.4 GB** [approx] |

> **Access pattern:** no-friction sets are **Argoverse 2** (open S3, no registration), **Hilti** (direct S3), and **Pandaset** (HF mirror, CC BY 4.0). **nuScenes-mini (~4 GB)** is the single best small multimodal demo. Gated-but-free = KITTI-360, nuScenes, Waymo. Almost everything is CC BY-NC-SA; **Pandaset (CC BY 4.0) is the only commercial-friendly outlier**, and **Argoverse 2** is unusually open in access despite its NC-SA license.

---

## 4. Downloadable assets

### 4.1 The ~8 most important papers (arXiv PDF URLs)

| # | Paper | arXiv PDF | Why it matters |
|---|---|---|---|
| 1 | KISS-ICP (RA-L 2023) | https://arxiv.org/pdf/2209.15397 | The pure-LiDAR odometry reference; pip + CPU. |
| 2 | KISS-SLAM (IROS 2025) | https://arxiv.org/pdf/2503.12660 | Full LiDAR-only SLAM, loop closure, MIT, pip. |
| 3 | MAD-ICP (RA-L 2024) | https://arxiv.org/pdf/2405.05828 | Strong CPU pure-LiDAR ICP; pip `mad-icp`. |
| 4 | FAST-LIO2 (T-RO 2022) | https://arxiv.org/pdf/2107.06829 | The LIO reference (IMU + iterated-EKF, 100 Hz). |
| 5 | Point Transformer V3 (CVPR 2024) | https://arxiv.org/pdf/2312.10035 | The perception backbone of record; MIT. |
| 6 | Sonata (CVPR 2025 Highlight) | https://arxiv.org/pdf/2503.16429 | The 3D self-supervised "foundation" result; PTv3 weights. |
| 7 | BEVFusion / MIT (ICRA 2023) | https://arxiv.org/pdf/2205.13542 | Camera-LiDAR BEV fusion reference; Apache-2.0. |
| 8 | PIN-SLAM (TRO 2024) | https://arxiv.org/pdf/2401.09101 | Best runnable neural-implicit LiDAR SLAM; MIT. |
| +1 | Scan Context (IROS 2018) | https://gisbi-kim.github.io/publications/gkim-2018-iros.pdf | The place-recognition descriptor everyone compares to. |
| +1 | Concerto (NeurIPS 2025) | https://arxiv.org/pdf/2510.23607 | Newest joint 2D-3D foundation pretraining. |

### 4.2 Pretrained weights (methods that ship models)

| Method | What you get | Approx size | Where | License |
|---|---|---|---|---|
| **PTv3** | Sem-seg checkpoints (SemanticKITTI / nuScenes / ScanNet / Waymo) | tens–hundreds of MB each [assumed] | Pointcept model zoo (GitHub releases / HF) | code **MIT** [verified] |
| **Sonata** | Pretrained **PTv3 encoder** (SSL) for linear-probe/fine-tune | encoder-size (tens–hundreds of MB); exact size not in README [assumed] | HF `facebook/sonata` | **weights CC-BY-NC 4.0** / code Apache-2.0 [verified] |
| **Concerto** | Pretrained models + inference + demo | **39M / 108M / 208M** param variants [verified] | HF (Pointcept/Concerto) | **weights CC-BY-NC 4.0** / code Apache-2.0 [verified] |
| **BEVFusion (MIT)** | Detection + BEV-seg checkpoints | per-ckpt 100s of MB [assumed] | mit-han-lab/bevfusion (Dropbox) | Apache-2.0 [verified] |
| **OverlapTransformer** | Place-recognition weights (KITTI, Haomo) | small (MBs) [assumed] | haomo-ai/OverlapTransformer (Google Drive) | GPLv3 [verified] |
| **LoGG3D-Net** | 7 checkpoints (KITTI×6, MulRan×1) | **~741 MB** total [verified] | csiro-robotics/LoGG3D-Net (Dropbox/CloudStor) | LICENCE in repo [verified] |
| **ScaLR** | DINOv2-distilled WaffleIron (WI-48-768) | [assumed] | valeoai/ScaLR | Apache-2.0 [verified] |
| **PonderV2 / ALSO / GrowSP / Seal** | Pretrained 3D encoders | [assumed] | OpenGVLab / Valeo / vLAR / youquanl repos | PonderV2 **MIT**, ALSO **Apache-2.0**; **Seal & GrowSP CC-BY-NC-SA 4.0** [verified] |

### 4.3 Engines that are pip-installable (no weights needed, they *compute*)

| Package | `pip install` | Runs without ROS? | CPU? | License |
|---|---|---|---|---|
| **kiss-icp** | `pip install kiss-icp` | **Yes** [verified] | **Yes** [verified] | MIT [verified] |
| **kiss-slam** | `pip install kiss-slam` | **Yes** [verified] | Yes [assumed] | MIT [verified] |
| **mad-icp** | `pip install mad-icp` | **Yes** [verified] | **Yes** [verified] | BSD-3 [verified] |
| **PIN-SLAM** | clone + `pin_slam.py` (no pip on PyPI) | **Yes** [verified] | Yes but slow (GPU recommended) [verified] | MIT [verified] |

### 4.4 Smallest freely-downloadable demo bundle (recommended for the app)

- **A single SemanticKITTI sequence** (e.g. seq `00`–`10` from KITTI odometry Velodyne), a few GB, ungated, gives you `.bin` scans + per-point labels to drive both odometry (KISS-ICP) and a PTv3 semseg demo. Root: http://semantic-kitti.org/dataset.html
- **Newer College "short experiment"** single sequence, ungated, Ouster OS1 `.pcd`/rosbag, ideal to show KISS-SLAM loop closure on a handheld walk. Root: https://ori-drs.github.io/newer-college-dataset/
- **nuScenes-mini (~4–10 GB)**, for any camera-LiDAR fusion / BEVFusion demo (free registration).
- **Pandaset (Hugging Face mirror)**, `huggingface.co/datasets/georghess/pandaset`, CC BY 4.0, no NDA, solid-state + mechanical LiDAR for variety.

---

## 5. Recommendation, most advanced **and** practical to integrate

**Constraints recap:** Python research repo + browser visualization; want permissive license + real weights or a pip-installable engine; flag anything that hard-requires ROS or a GPU cluster.

### Top pick (live, runnable today): **KISS-ICP + KISS-SLAM** (PRBonn)
- **Why:** MIT-licensed, **pip-installable, ROS-optional, CPU real-time, no IMU**. KISS-ICP gives live odometry; KISS-SLAM adds loop closure + a consistent map. This is the only cluster that genuinely runs **live in a Python backend** and streams poses/points to a browser (three.js / deck.gl / potree) without ROS or CUDA. Loaders already cover KITTI `.bin`, `.ply`, rosbags. **[verified: license, pip, ROS-optional, CPU]**
- **Use in app:** "LiDAR Odometry/SLAM workbench" tab, feed a SemanticKITTI or Newer College sequence, run KISS-ICP/KISS-SLAM server-side, visualize the growing map + trajectory + loop closures live, with adjustable voxel size / max-range / deskew toggles.

### Second pick (CPU pure-LiDAR alternative + comparison): **MAD-ICP**
- **Why:** BSD-3, **pip `mad-icp`, ROS-optional, "anytime" CPU real-time**, reads KITTI/MulRan/rosbag directly. Gives the app a genuine **method-comparison** (KISS-ICP vs MAD-ICP drift on the same sequence), exactly the kind of honest, real-compute panel the lab wants. **[verified: license, pip, ROS-optional, CPU]**
- **Optional 3rd pure-LiDAR baseline:** **CT-ICP** (MIT, standalone C++, no ROS) is worth bundling because it is the **only method in this survey with a verified KITTI odometry number on its primary page (0.59% avg RTE, top public-code on the KITTI leaderboard)**, a credible accuracy anchor for the comparison panel. Caveat: its Python binding `pyct_icp` is **marked broken**, so you'd call the C++ `run_odometry` binary rather than import it. **[verified]**

### Third pick (the "foundation / perception" showcase, offline then ONNX): **PTv3 + Sonata** (Pointcept / Meta)
- **Why:** **MIT** PTv3 is the perception backbone of record; **Sonata** gives a real **point-cloud foundation encoder** (CVPR 2025 Highlight) with released weights and a striking linear-probe story (21.8 to 72.5% on ScanNet). Together they cover "semantic segmentation" + "self-supervised foundation features" with **real downloadable weights**. **[verified: PTv3 MIT + weights; Sonata weights + numbers]**
- **Caveat / flag:** **GPU required** for training and comfortable inference; the browser experience must be a pipeline of **(1) offline precompute, (2) export single-scan inference to ONNX, (3) render the colored point cloud + a learned-feature similarity/segmentation panel**. Do **not** attempt live GPU inference in-browser at scale; bake results, ship ONNX for a small interactive scan. This matches the repo's "real compute, no compute-bomb" rule: precompute heavy passes, expose a controllable lightweight inference on one scan.

### Honorable mention (neural SLAM, GPU): **PIN-SLAM**
- MIT, ROS-optional, standalone Python, many loaders, the best **neural-implicit LiDAR SLAM** you can actually run. **Flag:** needs a GPU for real-time (CPU mode "much slower"). Good as an **offline "neural map" demo** rather than the live default.

### Place recognition add-on (cheap, CPU, no training): **Scan Context (++)**
- Pairs naturally with KISS-SLAM's loop-closure story; CPU, no GPU, well-understood. **Flag:** license is **CC BY-NC-SA 4.0** (non-commercial), fine for a research lab/demo, but note it if anything becomes commercial. For a permissive learned alternative, **OverlapTransformer (GPLv3, weights provided)**, GPL is copyleft, so keep it as an optional module, not linked into permissively-licensed core.

### Explicitly flagged as **NOT** browser-friendly (ROS and/or GPU-cluster):
- **FAST-LIO2, Point-LIO, LIO-SAM, DLIO, GLIM, LOAM/LeGO-LOAM**, require **ROS/ROS1/ROS2 and an IMU** (GLIM also wants a GPU). Great for a real robot, wrong layer for an in-browser app. Use only if you add a separate ROS service; do not put on the critical path.
- **BEVFusion, SphereFormer, Cylinder3D, WaffleIron, training any PTv3/Sonata from scratch**, **GPU (often multi-GPU)** + sparse-conv/custom-CUDA stacks. Offline-only; ship baked outputs / ONNX, never live training.

### Suggested app architecture (one paragraph)
A Python (FastAPI) backend exposes two engines: (1) **live odometry/SLAM** via `kiss-icp` / `kiss-slam` / `mad-icp` running on uploaded or bundled sequences, streaming incremental poses + downsampled points over WebSocket to a **deck.gl / three.js** point-cloud viewer with method-switch + parameter knobs; (2) an **offline perception/foundation** path where PTv3 (segmentation) and Sonata (features) are run once on a GPU, results baked to disk, and a **single-scan ONNX** model is shipped for a small interactive "color by class / color by learned-feature-similarity" panel. Place recognition (Scan Context) annotates loop closures on the live map. All heavy compute is precomputed or capped; the live path is CPU-only and ROS-free.

---

## 6. Verification status of key claims

**Verified on primary GitHub README / arXiv abstract / official page during this research:**
- KISS-ICP: MIT, pip `kiss-icp`, ROS-optional, CLI `kiss_icp_pipeline`, RA-L 2023. ✔
- KISS-SLAM: MIT, pip `kiss-slam`, builds on KISS-ICP+MapClosures+g2o, IROS 2025, LiDAR-only (no IMU). ✔
- MAD-ICP: BSD-3, pip `mad-icp`, ROS-optional, "anytime real-time" CPU, inputs Rosbag1/2 + KITTI + MulRan, RA-L 2024. ✔
- PIN-SLAM: MIT, TRO 2024, point-based implicit neural, ROS-optional standalone `pin_slam.py`, GPU recommended (CPU slower), many loaders. ✔
- PTv3: MIT, CVPR 2024 Oral, arXiv 2312.10035, Pointcept; PTv3-Extreme = 1st place Waymo 2024 semseg. ✔
- Sonata: CVPR 2025 Highlight, arXiv 2503.16429, PTv3 encoder-only, 140k clouds, ScanNet linear-probe 21.8 to 72.5%. ✔
- Concerto: NeurIPS 2025, arXiv 2510.23607, joint 2D-3D, 80.7 mIoU ScanNet fine-tune. ✔
- BEVFusion (MIT): Apache-2.0, ICRA 2023, arXiv 2205.13542, val ~68.5 mAP / 71.4 NDS, ~63 mIoU map-seg, ckpts provided, mmdet3d+CUDA. ✔
- Scan Context: CC BY-NC-SA 4.0, IROS 2018, CPU 10–15 Hz, C++/MATLAB/Py. ✔
- OverlapTransformer: GPLv3, RA-L 2022, arXiv 2203.03397, weights provided (KITTI/Haomo). ✔
- LoGG3D-Net: ICRA 2022, arXiv 2109.08336, 7 ckpts ~741 MB, sparse point-voxel U-Net. ✔
- Sonata/PTv3 part of Pointcept; Concerto (NeurIPS'25, arXiv 2510.23607), Utonia (ICML'26, arXiv 2603.03283) listed in Pointcept. ✔
- **Odometry/SLAM licenses (all read on primary LICENSE/sidebar):** MIT = KISS-ICP, KISS-SLAM, DLIO, GLIM, CT-ICP, PIN-SLAM. BSD-3 = LIO-SAM, MAD-ICP, LeGO-LOAM. **GPL-2.0 (copyleft) = FAST-LIO2, Point-LIO.** ✔
- **Modality (verified):** pure-LiDAR = KISS-ICP/KISS-SLAM/MAD-ICP/CT-ICP/LeGO-LOAM(IMU opt.); LiDAR-inertial = FAST-LIO2/Point-LIO/LIO-SAM(9-axis)/DLIO(6-axis); GLIM configurable. ✔
- **ROS-free / pip:** `pip install` for KISS-ICP, KISS-SLAM, MAD-ICP; standalone C++ (no ROS) for CT-ICP (Py binding broken), GLIM (non-ROS C++ API). ROS-bound: FAST-LIO2 (ROS1+ROS2 branch), Point-LIO (ROS1 only), LIO-SAM (ROS1+ros2+GTSAM), DLIO (ROS1+ros2 branch), LeGO-LOAM (ROS1 only). ✔
- **CT-ICP KITTI 0.59% avg RTE** (top public-code on KITTI odometry leaderboard), only verified KITTI drift figure in this survey. ✔
- **Segmentation mIoU (verified, split-labelled):** PTv3 72.3 val / 80.4 nuS; SphereFormer 67.8–69.0 val (74.8 test); Cylinder3D 77.9 nuS test; WaffleIron 68.0/77.6 val; FRNet 68.7 val/73.3 test; 2DPASS 70.7 to 72.0 TTA / 78.0 to 80.5 TTA. Licenses verified (MIT: PTv3/2DPASS/PonderV2; Apache-2.0: SphereFormer/Cylinder3D/WaffleIron/FRNet/ScaLR/ALSO). ✔
- **SSL linear-probe (verified):** Sonata ScanNet 72.5%; Seal nuScenes LP 45.0 / SemKITTI LP@1% 46.6, FT 75.1; ScaLR nuScenes LP 67.8/FT 78.4, SemKITTI LP 55.8/FT 65.8; Concerto +4.8% vs SOTA-3D, 80.7 ScanNet FT. ✔
- **NC caveat:** code is mostly permissive, but **weights of Sonata & Concerto are CC-BY-NC 4.0**, and **Seal & GrowSP (code+weights) are CC-BY-NC-SA 4.0**, non-commercial. Fine for the research lab; flag before any commercial framing. ✔
- **Dataset sizes (verified):** SemanticKITTI ~84 GB (add-on <1 GB); KITTI-360 ~773 GB; Waymo ~1 TB; Argoverse-2 sensor ~1 TB / LiDAR-only ~5 TB; Hilti 2022 ~159 GB / 2023 ~329 GB (per-bag 6–80 GB); Pandaset 44.5 GB (HF); nuScenes-mini ~4 GB. ✔
- **Access (verified):** Argoverse-2 + Hilti = open S3 no registration; Pandaset = open HF, CC BY 4.0; nuScenes/KITTI-360/Waymo = free registration/license gate. ✔

**Still assumed / approximate (not read on a primary page, or numbers that drift):**
- Per-checkpoint file sizes for PTv3 / Sonata / BEVFusion / ScaLR weights, orders-of-magnitude only.
- Exact GB of nuScenes full trainval+test (~300+ GB) and lidarseg add-on; Newer College / Oxford Spires absolute GB (Spires only has a "~10×" anchor).
- Licenses of RING (likely MIT), BoW3D (likely GPLv3), Utonia, not individually read.
- "Single SemanticKITTI sequence" and "one Argoverse-2 scenario" sizes, estimated, not measured.

> **Action items to fully close the survey:** (1) measure actual weight-file sizes by hitting the HF/Dropbox links; (2) confirm nuScenes full + lidarseg exact GB and Newer College / Oxford Spires absolute sizes from the logged-in download pages; (3) read RING / BoW3D / Utonia LICENSE files.

---

## 7. Sub-agent deep-dives (companion files in this folder)

Three parallel research sub-agents wrote verified detail tables to disk (all three completed; their facts are already folded into the tables above). Consult them for the long-form per-method evidence and verification ledgers:
- `subagent-odometry-2026-06-29.md`, odometry/SLAM repos (licenses, ROS dep, CPU, KITTI drift; e.g. CT-ICP 0.59% RTE, FAST-LIO2/Point-LIO GPL-2.0).
- `subagent-segmentation-foundation-2026-06-29.md`, segmentation + foundation models (split-labelled mIoU, licenses incl. NC-weights caveat, weights; RangeFormer has no official repo).
- `subagent-datasets-2026-06-29.md`, datasets (verified GB sizes incl. KITTI-360 ~773 GB, Argoverse-2 ~5 TB LiDAR-only, Pandaset 44.5 GB; gating; smallest demo chunk).

---

## 8. Sources

**Odometry / SLAM**
- KISS-ICP: https://github.com/PRBonn/kiss-icp · https://arxiv.org/abs/2209.15397
- KISS-SLAM: https://github.com/PRBonn/kiss-slam · https://arxiv.org/abs/2503.12660
- MAD-ICP: https://github.com/rvp-group/mad-icp · https://arxiv.org/abs/2405.05828
- FAST-LIO / FAST-LIO2: https://github.com/hku-mars/FAST_LIO · https://arxiv.org/abs/2107.06829
- Point-LIO: https://github.com/hku-mars/Point-LIO
- LIO-SAM: https://github.com/TixiaoShan/LIO-SAM · https://arxiv.org/abs/2007.00258
- DLIO: https://github.com/vectr-ucla/direct_lidar_inertial_odometry · https://arxiv.org/abs/2203.03749
- GLIM: https://github.com/koide3/glim
- LeGO-LOAM: https://github.com/RobustFieldAutonomyLab/LeGO-LOAM
- CT-ICP: https://github.com/jedeschaud/ct_icp
- PIN-SLAM: https://github.com/PRBonn/PIN_SLAM · https://arxiv.org/html/2401.09101v2
- SLAM app/benchmark collections: https://github.com/engcang/SLAM-application · https://github.com/MapsHD/HDMapping

**Place recognition**
- Scan Context: https://github.com/gisbi-kim/scancontext · https://gisbi-kim.github.io/publications/gkim-2018-iros.pdf
- OverlapTransformer: https://github.com/haomo-ai/OverlapTransformer · https://arxiv.org/abs/2203.03397
- LoGG3D-Net: https://github.com/csiro-robotics/LoGG3D-Net · https://arxiv.org/abs/2109.08336
- BoW3D: https://arxiv.org/abs/2208.07473
- RING/RING++: https://github.com/lus6-Jenny/RING · https://arxiv.org/abs/2210.05984
- Awesome lists: https://github.com/hogyun2/awesome-lidar-place-recognition · https://github.com/kxhit/awesome-point-cloud-place-recognition
- BEVPlace++/S-BEVLoc/UniLGL/ForestLPR: https://arxiv.org/abs/2503.04475 · https://arxiv.org/html/2509.09110 · https://arxiv.org/abs/2507.12194

**Segmentation / perception**
- PTv3: https://github.com/Pointcept/PointTransformerV3 · https://arxiv.org/abs/2312.10035
- PTv3-Extreme (Waymo 2024): https://arxiv.org/abs/2407.15282
- SphereFormer: https://github.com/dvlab-research/SphereFormer · https://arxiv.org/abs/2303.12766
- Cylinder3D: https://github.com/xinge008/Cylinder3D · https://arxiv.org/abs/2011.10033
- WaffleIron: https://github.com/valeoai/WaffleIron · https://arxiv.org/abs/2301.10100
- RangeFormer: https://arxiv.org/abs/2303.05367
- FRNet: https://github.com/Xiangxu-0103/FRNet · https://arxiv.org/abs/2312.04484
- 2DPASS: https://github.com/yanx27/2DPASS · https://arxiv.org/abs/2207.04397
- Pointcept codebase: https://github.com/Pointcept/Pointcept

**Foundation / self-supervised**
- Sonata: https://github.com/facebookresearch/sonata · https://arxiv.org/abs/2503.16429 · https://www.projectaria.com/news/introducing-sonata/
- Concerto: https://github.com/Pointcept/Concerto · https://arxiv.org/abs/2510.23607 · https://pointcept.github.io/Concerto/
- PonderV2: https://github.com/OpenGVLab/PonderV2 · https://arxiv.org/abs/2310.08586
- Seal: https://github.com/youquanl/Segment-Any-Point-Cloud · https://arxiv.org/abs/2306.09347
- ScaLR ("Three Pillars"): https://github.com/valeoai/ScaLR · https://arxiv.org/abs/2310.17504
- ALSO: https://github.com/valeoai/ALSO · https://arxiv.org/abs/2212.05867
- GrowSP: https://github.com/vLAR-group/GrowSP · https://arxiv.org/abs/2305.16404

**Fusion / BEV**
- BEVFusion (MIT): https://github.com/mit-han-lab/bevfusion · https://arxiv.org/abs/2205.13542
- BEVFusion (ADLab): https://github.com/ADLab-AutoDrive/BEVFusion · https://arxiv.org/abs/2205.13790

**Open-vocabulary 3D**
- OpenScene: https://github.com/pengsongyou/openscene
- Open3DIS: https://arxiv.org/abs/2312.10671
- HOV-SG: https://github.com/hovsg/HOV-SG · https://arxiv.org/abs/2403.17846

**Datasets**
- SemanticKITTI: http://semantic-kitti.org/dataset.html
- KITTI-360: https://www.cvlibs.net/datasets/kitti-360/ · https://arxiv.org/abs/2109.13410
- nuScenes: https://www.nuscenes.org/nuscenes · https://github.com/nutonomy/nuscenes-devkit
- Waymo Open: https://waymo.com/open/ · https://github.com/waymo-research/waymo-open-dataset
- Newer College: https://ori-drs.github.io/newer-college-dataset/
- Oxford Spires: https://dynamic.robots.ox.ac.uk/datasets/oxford-spires/ · https://arxiv.org/abs/2411.10546
- Argoverse 2: https://www.argoverse.org/av2.html · https://registry.opendata.aws/argoverse/
- Hilti SLAM Challenge: https://hilti-challenge.com/
- Pandaset (HF mirror): https://huggingface.co/datasets/georghess/pandaset · devkit https://github.com/scaleapi/pandaset-devkit
- Dataset collections: https://github.com/minwoo0611/Awesome-3D-LiDAR-Datasets

**Surveys / context**
- LiDAR SLAM survey: https://arxiv.org/abs/2311.00276
- LiDAR place-recognition survey: https://arxiv.org/abs/2306.10561
