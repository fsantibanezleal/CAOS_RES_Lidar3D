# Neural 3D Representations, Dense / Gaussian SLAM, and the Browser Visualization Stack — State of the Art

**Survey for the "Lidar 3D" research lab + interactive web app** (feed-forward 3D reconstruction from video + LiDAR point clouds).
**Date:** 2026-06-29 · **Author:** Lucy (research analyst).

> **Scope.** (A) neural rendering & dense/visual SLAM SOTA; (B) reconstruction/SLAM datasets; (C) the practical web visualization + in-browser inference stack — so we can build a real interactive 3D workbench in the browser with a Python-FastAPI backend + JS frontend.
>
> **Method.** ~30 web searches + targeted page fetches (GitHub READMEs, arXiv abstracts/HTML, official docs, HF model cards), run as four parallel deep-dive agents plus the author's own independent cross-verification of the load-bearing facts (VGGT award, Spark, viser, 3DGS license, SplaTAM/MonoGS numbers, transformers.js WebGPU, demo dataset). Each sub-agent's raw notes are in the sibling files `_sub_*.md`, `feedforward-3d-foundation-models-2026-06-29.md`, `subagent-odometry-2026-06-29.md`, `subagent-segmentation-foundation-2026-06-29.md`.
>
> **Claim-marking convention.** Each non-trivial claim is tagged **[V]** (verified — read on a primary source this session) or **[A]** (assumed — inferred, secondary-source, or rounded). Star counts drift; treat all as approximate even when tagged [V] (they were [V]-read on the repo page on 2026-06-29).

---

## 1. Executive summary

### Representations
The field has consolidated on **3D Gaussian Splatting (3DGS)** (Kerbl et al., SIGGRAPH 2023 Best Paper) as the default explicit, real-time, differentiable scene representation, displacing NeRF for most reconstruction-and-view-synthesis use. **Critical product caveat:** the **original INRIA reference code is a custom NON-COMMERCIAL research license** [V] (owned by Inria + MPII; commercial use needs explicit consent, contact `stip-sophia.transfert@inria.fr`). For a real deployable product the rendering math is fine but you must build on the **Apache-2.0 `gsplat` library** (nerfstudio, ~5.3k★) [V], not the INRIA repo. Key variants to track: **2DGS** (planar surfels → clean surface/mesh extraction) [V], **Mip-Splatting** (anti-aliasing) [V], **Scaffold-GS** (structured/anchored) [V], and the **compression** subfield (HAC, ContextGS, Compact3D; survey "3DGS.zip", CGF 2025) [A].

### The pointmap revolution is the heart of "feed-forward from video"
**DUSt3R → MASt3R → MASt3R-SfM** regress dense per-pixel **pointmaps** directly from uncalibrated images (no SfM, no known intrinsics/poses) [V]. **VGGT (Visual Geometry Grounded Transformer), CVPR 2025 Best Paper** [V], is the current apex: a single feed-forward ViT (DINOv2-L backbone, ~1B params) that in **under one second** outputs camera intrinsics+extrinsics, depth maps, dense point maps, and 3D point tracks from 1…hundreds of views (`facebookresearch/vggt`, ~13.6k★) [V]. This is exactly the Lidar-3D thesis. The 2025-2026 frontier extends VGGT three ways: **reference-free permutation-equivariant** geometry (**π³ / Pi3**, ICLR 2026, code BSD-3) [V]; **streaming with bounded memory** (**CUT3R**, **StreamVGGT**, **LONG3R**, **VGGT-Long**, and the standout **lingbot-map** — arXiv 2604.14141, Apr 2026, Apache-2.0, ~20 FPS over 10k+ frames, ships a viser viewer) [V]; and **universal/minimal-modeling** (**MapAnything** (Meta, Apache ckpt) [V], **Depth Anything 3** (ByteDance, multi-size) [V], **AMB3R** (CVPR'26)). Direct feed-forward 3DGS: **pixelSplat → MVSplat → Splatt3R → AnySplat → Long-LRM** (sparse views → renderable Gaussians in one pass) [V].

### Dense / Gaussian SLAM (three converging families)
- **Gaussian-splatting SLAM** (photorealistic dense SLAM). Canonical baselines **SplaTAM** (RGB-D, Replica ATE **0.36 cm**, TUM **5.48 cm**, ~2.1k★, BSD-3) [V] and **MonoGS / "Gaussian Splatting SLAM"** (mono/stereo/RGB-D, CVPR'24 Highlight + Best Demo, Replica **0.32 cm**, TUM RGB-D **1.47 cm**, ~10 FPS mono on RTX4090) [V]. Plus **Gaussian-SLAM** (sub-maps, MIT), **Photo-SLAM** (ORB-SLAM3 + 3DGS hybrid, real-time on Jetson AGX Orin, GPL-3) [V], **GS-ICP-SLAM** (~100 FPS, MIT) [V], **RTG-SLAM** (compact, SIGGRAPH'24, GPL-3), **LoopSplat** (loop closure by registering splats; Replica **0.26 cm** best; ScanNet++ **2.05 cm** vs SplaTAM's **89 cm** — the large-motion story) [V]. **RGB-only** is the 2025 frontier: **Splat-SLAM** (Google, global BA + deformable map) [V], **HI-SLAM2**.
- **Feed-forward / pointmap SLAM** (bleeding edge, most relevant to us). **MASt3R-SLAM** (CVPR 2025, 15 FPS, globally consistent, loop closure, no camera-model assumption) [V]; **VGGT-SLAM** (MIT-SPARK, NeurIPS 2025, aligns VGGT submaps on the SL(4) manifold for uncalibrated mono) [V]; 2026 follow-ons **VGGT-Long**, **FILT3R**, **Flash-Mono**, and **lingbot-map** as a streaming-SLAM-grade foundation model.
- **LiDAR + 3DGS.** Two distinct things [V]: (a) **genuine online LiDAR-Inertial-Visual SLAM** that fuses LiDAR depth for pose *and* geometry — **Gaussian-LIC / Gaussian-LIC2** (ICRA'25, GPL-3), **GS-LIVM** (ICCV'25), **GS-LIVO**, **LIV-GaussMap** — the relevant lineage for the LiDAR half; (b) **driving-scene NVS reconstruction** that uses LiDAR only as a prior with known poses — **Street Gaussians** (ECCV'24, ~1.4k★), **DrivingGaussian** (CVPR'24, academic-only). For raw-LiDAR odometry (no cameras), the mature classical stack is **KISS-ICP / KISS-SLAM** (MIT, `pip`-installable, no ROS), **FAST-LIO2 / Point-LIO** (GPL-2, LiDAR-inertial), **CT-ICP** (MIT, 0.59% KITTI RTE), **GLIM**, **MAD-ICP** [V].

Primary survey to cite: **Tosi et al., "How NeRFs and 3D Gaussian Splatting are Reshaping SLAM: a Survey," arXiv 2402.13255** [V]. On standard benchmarks leading 3DGS-SLAM methods report **sub-centimeter ATE on Replica** and **a few cm on TUM-RGBD** [V]; accuracy is largely solved on easy scenes, and the real differentiator is robustness to fast motion / large scenes, where loop closure dominates.

### The web-viz reality (decisive for this app)
Rendering millions of points or Gaussians in a browser is solved enough to ship; the heavy *reconstruction model must run server-side*.
- **Viewer/transport:** the 3D-foundation-model community standardizes on **`viser`** (`nerfstudio-project/viser`, **Apache-2.0**, ~2.6k★, v1.0.30) [V] — a Python lib that serves a three.js web client over websockets with `add_point_cloud` / `add_mesh` / **`add_gaussian_splats`** / `add_camera_frustum` plus a full GUI builder. It is how nerfstudio's viewer, the VGGT demo, and lingbot-map all ship. **Fastest path to a real Python-backed workbench.**
- **Massive point clouds:** **Potree** (octree LOD streaming; mature but last release 1.8.2 Dec-2023; WebGPU successor "Potree-Next" is research-grade) [V]; **deck.gl `PointCloudLayer`** (Apache-2.0, WebGL2, WebGPU in progress) [V]; **CesiumJS / 3D Tiles** if geospatial — and 3D Tiles now renders Gaussian splats with hierarchical LOD [V].
- **Gaussian-splat web renderers:** **Spark** (`sparkjsdev/spark`, World Labs, **MIT**, ~3.3k★, three.js, **deliberately WebGL2** for ~98% device reach, v2 adds streamable LOD + `.rad` format) [V] is the production leader; **mkkellogg/GaussianSplats3D** (MIT, ~2.7k★) the lighter classic [V]; **PlayCanvas SuperSplat** (MIT, ~9.4k★, best editor, now WebGPU) [V]; **Babylon.js** (GS on both WebGL2+WebGPU) [V]; **antimatter15/splat** the original WebGL demo [V]. Splatting is **WebGL2-dominant**; the per-frame depth **sort** is the bottleneck, and GPU radix sort is the main reason to want WebGPU [V].
- **In-browser inference:** **transformers.js v3 + ONNX Runtime Web** run a *small* depth model (**Depth Anything V2 Small, ~25M params**) client-side on **WebGPU**, with a working video-depth example [V]. **WebGPU is Baseline as of Jan 2026** (Chrome/Edge/Firefox/Safari 26+) [V]; **WebNN** is Origin-Trial only (~2027) [V]. A **VGGT-class ~1B ViT cannot run client-side** at usable speed — VGGT's own browser demo is Gradio (server-side) [V]. **Verdict: heavy model server-side (FastAPI+GPU), stream geometry; reserve client-side inference for a lightweight depth/segmentation preview.**

### Bottom-line recommendation (full detail in §6)
**Server-side feed-forward model on FastAPI+GPU → stream pointmaps/poses/splats → browser viewer.** Hero engine: **VGGT** for snapshot multi-image reconstruction (<1 s) and **lingbot-map** (or **MASt3R-SLAM**) for live video streaming SLAM. Viewer: **viser** for the research workbench now; graduate to **three.js + Spark** (WebGL2) for the polished public front-end and **Potree** for billion-point LiDAR. Representation: **point cloud / pointmap for the live feed-forward view; 3DGS (via gsplat, Apache-2.0) for the refined photorealistic scene; 2DGS when a clean mesh is the deliverable.** Optional **Depth Anything V2 Small (transformers.js + WebGPU)** client-side "instant preview."

---

## 2. Dense / Gaussian / feed-forward SLAM — comparison table

> ATE = Absolute Trajectory Error RMSE (cm). "Replica" = standard pre-rendered SLAM trajectories; "TUM" = TUM-RGBD freiburg. Cross-paper numbers vary by run/keyframing (e.g. SplaTAM on Replica is 0.36 in its own paper, 0.38 in LoopSplat's re-run). FPS is approximate and hardware-dependent. Stars [V]-read 2026-06-29, approximate.

| Method | Year / venue | Input | Representation | ~Real-time FPS (HW) | ATE Replica (cm) | ATE TUM (cm) | Repo | Stars | License |
|---|---|---|---|---|---|---|---|---|---|
| **SplaTAM** | CVPR'24 | RGB-D | 3D Gaussians (isotropic) | heavy per-iter (~<1 practical) [A] | **0.36** [V] | **5.48** [V] | spla-tam/SplaTAM | ~2.1k [V] | **BSD-3** [V] |
| **MonoGS** (Gaussian Splatting SLAM) | CVPR'24 Highlight + Best Demo | mono / stereo / RGB-D | 3D Gaussians (anisotropic) | 3.2 mono; up to **10** (4090) [V] | **0.32** / 0.58 [V] | RGB-D **1.47**; mono 3.96 [V] | muskie82/MonoGS | ~2.1k [V] | research (LICENSE.md) [V] |
| **Gaussian-SLAM** | arXiv Dec'23 | RGB-D | 3DGS sub-maps | interactive (~few) [A] | 0.31 (re-run) [V] | a few [A] | VladimirYugay/Gaussian-SLAM | ~1.2k [V] | **MIT** [V] |
| **Photo-SLAM** | CVPR'24 | mono / stereo / RGB-D | ORB-SLAM3 + 3DGS (hybrid) | real-time; **Jetson Orin** [V] | sub-cm [A] | a few [A] | HuajianUP/Photo-SLAM | ~750 [V] | **GPL-3** [V] |
| **GS-ICP-SLAM** | ECCV'24 | RGB-D | 3DGS + Generalized-ICP | up to **~100** [V-claim] | sub-cm [A] | a few [A] | Lab-of-AI-and-Robotics/GS_ICP_SLAM | ~530 [V] | **MIT** [V] |
| **RTG-SLAM** | SIGGRAPH'24 | RGB-D | compact 3DGS (opaque/transparent) | real-time (~2× NeRF-SLAM, ½ mem) [V-claim] | sub-cm [A] | a few [A] | MisEty/RTG-SLAM | ~500 [V] | **GPL-3** [V] |
| **LoopSplat** | 3DV'25 Oral | RGB-D | 3DGS sub-maps + loop closure (PGO) | offline-quality (not real-time) [A] | **0.26** (best) [V] | reported [A] | GradientSpaces/LoopSplat | ~390 [V] | **MIT** [V] |
| **Splat-SLAM** | CVPR'25 W | **RGB-only** | 3DGS + DROID global BA, deformable | fast; small map [A] | strong RGB-only [A] | a few [A] | google-research/Splat-SLAM | ~110 [V] | Apache-2.0 [A] |
| **HI-SLAM2** | arXiv Nov'24 | **RGB-only** mono | geometry-aware 3DGS + PGBA | fast mono [A] | reported [A] | reported [A] | (arXiv 2411.17982) | — | — |
| **GauS-SLAM** | arXiv May'25 | RGB-D | 2D Gaussian surfels | efficient [A] | reported [A] | reported [A] | (arXiv 2505.01934) | — | — |
| **MASt3R-SLAM** | CVPR'25 | **RGB (uncalibrated)** | pointmaps (MASt3R prior) | **~15** [V] | dense, globally consistent [V] | robust in-the-wild [V] | rmurai0610/MASt3R-SLAM | — | CC-BY-NC (code) [A] |
| **VGGT-SLAM** | NeurIPS'25 | **RGB (uncalibrated)** | VGGT submaps on SL(4) | real-time on Jetson Thor [V] | improved on long video [V] | — | MIT-SPARK/VGGT-SLAM | — | research [A] |
| **lingbot-map** | arXiv Apr'26 | **RGB video stream** | streaming pointmap + pose + depth (VGGT backbone) | **~20** over 10k+ frames [V] | 7-Scenes ATE 0.08; ETH3D F1 98.98 [V] | not in fetched tables [A] | robbyant/lingbot-map | ~8.6k [V] | **Apache-2.0** [V] |
| --- *NeRF-SLAM lineage (context)* --- | | | | | | | | | |
| **iMAP** | ICCV'21 | RGB-D | single MLP | track 10 Hz / map 2 Hz [V] | ~3–5 [A] | — | (no official) | — | — |
| **NICE-SLAM** | CVPR'22 | RGB-D | hierarchical feature grid + MLP | seconds/frame (large) [A] | ~1.06 [V] | a few [A] | cvg/nice-slam | ~1.6k [V] | Apache-2.0 [A] |
| **Co-SLAM** | CVPR'23 | RGB-D | coord + hash encoding | **10–17 Hz** [V] | ~1 [A] | a few [A] | HengyiWang/Co-SLAM | ~460 [V] | Apache-2.0 [A] |
| **Point-SLAM** | ICCV'23 | RGB-D | neural point cloud | slow (heavy render) [A] | ~0.5 [A] | a few [A] | eriksandstroem/Point-SLAM | — | research [A] |
| **NeRF-SLAM** (Rosinol) | arXiv Oct'22 | **RGB-only** mono | Instant-NGP + DROID-SLAM | real-time [A] | (recon focus) | — | ToniRV/NeRF-SLAM | — | BSD/research [A] |
| --- *LiDAR + 3DGS (genuine LIVO SLAM)* --- | | | | | | | | | |
| **Gaussian-LIC / LIC2** | ICRA'25 / arXiv'25 | **LiDAR + IMU + cam** (fused) | 3DGS, LiDAR+visual init | real-time (C++/CUDA, 3090/4090) [V] | outdoor (no Replica) | — | APRIL-ZJU/Gaussian-LIC | ~560 [V] | **GPL-3** [V] |
| **GS-LIVM** | ICCV'25 | **LiDAR + IMU + cam** | voxel 3DGS + GP regression | real-time, large outdoor [V-claim] | — | — | xieyuser/GS-LIVM | — | **GPL-3** [V] |
| **LIV-GaussMap** | arXiv Jan'24 | **LiDAR + IMU + cam** | surface Gaussians, adaptive voxels | real-time [V-claim] | — | — | sheng00125/LIV-GaussMap | — | research [A] |
| --- *LiDAR + 3DGS (driving NVS, not SLAM)* --- | | | | | | | | | |
| **Street Gaussians** | ECCV'24 | cam + LiDAR depth (driving) | composite 3DGS (static+dynamic) | offline recon; real-time render [A] | Waymo/KITTI (PSNR) | — | zju3dv/street_gaussians | ~1.4k [V] | research [A] |
| **DrivingGaussian** | CVPR'24 | surround cam + LiDAR prior | composite/incremental 3DGS | offline recon; real-time render [A] | nuScenes/KITTI (PSNR) | — | VDIGPKU/DrivingGaussian | ~400 [V] | academic-only [V] |

**Key reading:** On Replica, strong 3DGS methods cluster at **0.26–0.58 cm** (LoopSplat best). The differentiator is **large-motion robustness** (ScanNet++): LoopSplat **2.05 cm** vs MonoGS **12.88** vs SplaTAM **89.41** [V] — loop closure is decisive. Speed leaders: GS-ICP-SLAM (~100 FPS), MonoGS speedup branch (~10 FPS), Photo-SLAM (Jetson-real-time). **For Lidar-3D specifically**, the streaming feed-forward line (lingbot-map / MASt3R-SLAM / VGGT-SLAM) is the architecturally-aligned choice; the LIVO-SLAM line (Gaussian-LIC etc.) is the choice if real LiDAR-inertial hardware is in scope.

---

## 3. Datasets for reconstruction & SLAM

> Sizes tagged [V] were read off the official download/listing page; [A] were estimated or from secondary sources. Full notes in `subagent-datasets-2026-06-29.md`.

| Dataset | Type | Size (full) | Demo-friendly (<5 GB)? | Single-scene demo | Access / license | URL |
|---|---|---|---|---|---|---|
| **3DGS `tandt_db`** (T&T truck/train + DeepBlending) | multi-view, in+outdoor | **650 MB** [V] | **YES — best demo** | truck/train ~0.2–0.3 GB [A] | open `wget`, no reg | https://repo-sam.inria.fr/fungraph/3d-gaussian-splatting/datasets/input/tandt_db.zip |
| **nerfstudio "poster"** | single capture (tutorial) | **715 MB** [V] | **YES — best single scene** | this *is* one scene | open (`ns-download-data`) | https://docs.nerf.studio/quickstart/existing_dataset.html |
| **TUM-RGBD** (freiburg) | RGB-D indoor SLAM | ~39–50 GB total | **YES per-seq** | **fr1_xyz 0.47 GB**, fr1_desk 0.36 GB [V] | open, .tgz | https://cvg.cit.tum.de/data/datasets/rgbd-dataset/download |
| **Replica** (NICE-SLAM/SplaTAM render) | RGB-D indoor (synthetic) | **Replica.zip = 12 GB** [V] | full NO; **1 scene ~1–1.5 GB** YES | room0/office0 ~1–1.5 GB [A] | open | https://cvg-data.inf.ethz.ch/nice-slam/data/Replica.zip |
| **7-Scenes** (Microsoft) | RGB-D indoor relocalization | ~12–20 GB [A] | partly | per-scene ~0.5–3 GB [A] | open, NC click-through | https://www.microsoft.com/en-us/research/project/rgb-d-dataset-7-scenes/ |
| **ETH3D SLAM** | RGB-D + stereo + IMU | ~30–60 GB [A] | **YES per-seq** | per-seq ~0.2–2 GB [A] | open, py downloader | https://www.eth3d.net/slam_datasets |
| **Tanks & Temples** | multi-view recon | 100s GB raw [A] | subset yes | NeRF subset ~1–4 GB [A] | open, reg for full GT | https://www.tanksandtemples.org/ |
| **Mip-NeRF 360** | multi-view object+unbounded | ~8 GB; HF JPG mirror **3.01 GB** [V] | borderline (mirror YES) | per-scene ~0.3–1.5 GB [A] | open | http://storage.googleapis.com/gresearch/refraw360/360_v2.zip |
| **MPI Sintel** | optical flow + depth | depth GT **1.5 GB** [V]; flow ~5–6 GB [A] | **YES (depth GT)** | n/a (frame-pair) | open | http://sintel.is.tue.mpg.de/ |
| **ScanNet** | RGB-D indoor (1513 scans) | ~1.3 TB [A] | **NO** | per-scan ~1.5–3 GB [A] | **signed TOS** | http://www.scan-net.org/ |
| **ScanNet++** | RGB-D + laser + DSLR | **~1.5 TB default** (9 TB w/33 MP) [V] | **NO** | ~1.49 GB/scene avg [V] | **registration + TOS** | https://kaldir.vc.in.tum.de/scannetpp/ |
| **Oxford Spires** | LiDAR + 3× fisheye (2024/25) | 100s GB (24 seq) [A] | **NO** | per-seq >5 GB [A] | open, **CC BY-NC-SA** | https://dynamic.robots.ox.ac.uk/datasets/oxford-spires/ |
| **KITTI** (odometry) | outdoor driving, LiDAR+cam | gray 22 / color 65 / velodyne 80 GB [V] | **NO** | monolithic | registration, CC BY-NC-SA | https://www.cvlibs.net/datasets/kitti/eval_odometry.php |
| **KITTI-360** | 360° driving | **~707 GB total** [V] | **NO** | drives still large [A] | **login req** | https://www.cvlibs.net/datasets/kitti-360/ |

**Best small demo picks (free, <5 GB, no registration):** (1) **`tandt_db` 650 MB** [V] — the canonical 3DGS/NeRF demo, COLMAP-ready; (2) **nerfstudio `poster` 715 MB** [V] — single scene; (3) **TUM-RGBD `fr1_xyz` 0.47 GB** [V] — dense RGB-D SLAM. Honorable mentions: a single Replica scene (~1–1.5 GB), Sintel depth GT (1.5 GB) for a flow/depth panel.

---

## 4. Web-stack recommendation

Full detail in `_sub_web_stack.md`. The architecture is a **thin server-rendered-geometry model**: Python FastAPI + GPU does the reconstruction; the browser renders geometry and drives controls. This matches how the whole 3D-foundation-model community ships (nerfstudio, VGGT, gsplat, lingbot-map).

**Layer-by-layer pick:**

1. **Primary viewer — `viser`** (Apache-2.0, `pip install viser`, ~2.6k★, v1.0.30) [V]. A Python-served three.js web client over websockets: `add_point_cloud`, `add_mesh`, **`add_gaussian_splats`**, `add_camera_frustum`, frames/splines/images, and a full GUI builder (sliders/dropdowns/tabs) wired to Python callbacks; works over SSH. *It is purpose-built for exactly this app shape.* Fit with FastAPI: viser runs its own server/websocket — mount it alongside FastAPI (separate port or sub-app); FastAPI owns REST/jobs/uploads/auth, viser owns the live 3D scene + scene GUI.
2. **Bespoke front-end (when you outgrow viser's built-in renderer) — `three.js` (r185, MIT, 113k★) + `Spark` (MIT, v2.1.0) for splats** [V]. Spark is the production-grade, World-Labs-backed three.js 3DGS renderer (multi-splat scenes, animation, streamable LOD, formats PLY/SPZ/SPLAT/SOG/`.rad`), **WebGL2 by deliberate choice** for ~98% device coverage. FastAPI just serves `.ply`/`.spz` files or a tiled stream.
3. **Massive raw LiDAR (100M+ pts) — `Potree`** (BSD-2, octree streaming) [V], served as a static octree from FastAPI. Note Potree 1.8.2 is stale (Dec-2023); the WebGPU successor **Potree-Next** is research-grade — don't depend on it in production yet. Alternative for moderate scattered clouds with data-driven coloring: **deck.gl `PointCloudLayer`** (Apache-2.0) [V].
4. **Inference placement — SERVER-SIDE for the heavy model** [V reasoning]. Run VGGT / pointmap / lingbot-map on the FastAPI GPU box; a ~1B-param ViT is not browser-feasible in 2026 (VGGT's own browser demo is Gradio). **Optional client-side extras via `transformers.js` + ORT-Web (WebGPU):** Depth-Anything-V2-Small preview, segmentation, embeddings — enhancement only, never the main path. **Avoid WebNN** (Origin-Trial only). WebGPU is Baseline as of Jan 2026, so a WebGPU splat path (Babylon/PlayCanvas/WGPU radix-sort) is increasingly safe when scenes are huge.
5. **Dev-time inspection side-channel (optional) — `rerun`** (Apache-2.0/MIT, ~11k★, WebGPU/wgpu) [V] for logging pipeline intermediates (per-frame clouds, camera tracks, tensors). Less suited than viser as the polished embeddable app viewer; API still has breaking changes.

**WebGL2 vs WebGPU for splatting** [V]: splats must be depth-sorted every frame (back-to-front alpha); WebGL2 sorts on CPU/WASM (the scene-size cap), WebGPU moves the sort to a GPU radix sort (~2 ms/frame, research renderers). The production leader (Spark) stays WebGL2 for reach; SuperSplat/Babylon/PlayCanvas offer WebGPU for big scenes.

**Point cloud vs Gaussian splats vs mesh** (which representation in the viewer): **point cloud / pointmap** for the live feed-forward output and raw LiDAR (cheapest, instant, no sort); **3DGS** for the refined photorealistic scene (best fidelity, needs the splat renderer + sort); **mesh** when a watertight deliverable is needed (extract via 2DGS/TSDF).

---

## 5. Downloadable assets (papers + demo data)

| Asset | What | arXiv PDF / URL |
|---|---|---|
| 3DGS (Kerbl 2023) | original 3DGS paper | https://arxiv.org/pdf/2308.04079 |
| **VGGT** (CVPR'25 Best Paper) | feed-forward geometry transformer | https://arxiv.org/pdf/2503.11651 |
| Pi3 (π³, ICLR'26) | reference-free pointmaps | https://arxiv.org/pdf/2507.13347 |
| DUSt3R | pointmap regression | https://arxiv.org/pdf/2312.14132 |
| MASt3R | matching + metric pointmaps | https://arxiv.org/pdf/2406.09756 |
| MASt3R-SLAM (CVPR'25) | real-time dense pointmap SLAM | https://arxiv.org/pdf/2412.12392 |
| VGGT-SLAM (NeurIPS'25) | SL(4) submap SLAM | https://arxiv.org/pdf/2505.12549 |
| lingbot-map (Apr'26) | streaming GCT SLAM (Apache-2.0) | https://arxiv.org/pdf/2604.14141 |
| SplaTAM (CVPR'24) | RGB-D Gaussian SLAM | https://arxiv.org/pdf/2312.02126 |
| MonoGS (CVPR'24) | Gaussian Splatting SLAM | https://arxiv.org/pdf/2312.06741 |
| LoopSplat (3DV'25) | loop closure via splat registration | https://arxiv.org/pdf/2408.10154 |
| 2DGS (SIGGRAPH'24) | surfels for surfaces/mesh | https://arxiv.org/pdf/2403.17888 |
| MapAnything (Meta'25) | universal metric recon (Apache ckpt) | https://arxiv.org/pdf/2509.13414 |
| MoGe-2 | monocular metric pointmap (MIT) | https://arxiv.org/pdf/2507.02546 |
| **SLAM survey** (Tosi et al.) | NeRF + 3DGS SLAM survey | https://arxiv.org/pdf/2402.13255 |
| **DEMO DATA — `tandt_db` 650 MB** [V] | T&T + DeepBlending COLMAP | https://repo-sam.inria.fr/fungraph/3d-gaussian-splatting/datasets/input/tandt_db.zip |
| **DEMO DATA — nerfstudio poster 715 MB** [V] | single NeRF/3DGS scene | `ns-download-data nerfstudio --capture-name=poster` |
| **DEMO DATA — TUM fr1_xyz 0.47 GB** [V] | dense RGB-D SLAM sequence | https://cvg.cit.tum.de/data/datasets/rgbd-dataset/download |

**Runnable model weights (single consumer GPU):** `facebook/VGGT-1B` (+ `VGGT-1B-Commercial` for commercial) ~4–5 GB; `robbyant/lingbot-map` one ckpt ~4.63 GB (Apache-2.0); `yyfz233/Pi3` ~3.8 GB (code BSD-3, weights NC); `Ruicheng/moge-2-vitl-normal` ~1.3 GB (MIT); `facebook/map-anything-apache` ~1–2 GB (Apache); `onnx-community/depth-anything-v2-small` (Apache, for in-browser). Re-confirm exact bytes + weight licenses on the HF "Files" tab before download — code and weights are frequently licensed separately (VGGT, Pi3, Depth Anything).

---

## 6. Recommendation — the most advanced yet practical representation + viewer combo

**Representation (dual-track):**
- **Live feed-forward view + LiDAR:** **point clouds / pointmaps** (VGGT / lingbot-map / MASt3R-SLAM output). Cheapest to stream and render, no per-frame sort, instant.
- **Refined photorealistic scene:** **3D Gaussian Splatting via `gsplat` (Apache-2.0)** — never ship the INRIA reference code in product (non-commercial) [V].
- **Mesh deliverable:** **2DGS** (planar surfels → clean surface extraction) when a watertight mesh is needed.

**Engine (server-side, FastAPI + GPU):**
- **Snapshot mode** (upload N photos / a short clip → instant scene): **VGGT** — CVPR'25 Best Paper, <1 s, outputs pose+depth+pointmap+tracks, ~13.6k★, 5-line `from_pretrained("facebook/VGGT-1B")` API; use **VGGT-1B-Commercial** to clear the license [V].
- **Live streaming mode** (the hero feature: video → live 3D + trajectory): **lingbot-map** (Apache-2.0 on code *and* weights, ~20 FPS over 10k+ frames, ships a viser viewer, sky-mask ONNX) [V], with **MASt3R-SLAM** (15 FPS, loop closure) or **VGGT-SLAM** as alternates if lingbot-map's native stack (PyTorch 2.8 / CUDA 12.8 / FlashInfer / Kaolin) proves hard to containerize.
- **Single-image / low-VRAM preview tier:** **MoGe-2** (MIT, metric pointmap, ~1.3 GB, ~60 ms/frame) [V].
- **LiDAR-inertial hardware path (if in scope):** **Gaussian-LIC2** (GPL-3) for fused LiDAR+IMU+cam SLAM, or **KISS-ICP/KISS-SLAM** (MIT, `pip`) for pure-LiDAR odometry [V].

**Viewer:** **viser** for the research workbench *now* (one library = point clouds + splats + meshes + cameras + GUI, Apache-2.0, the community default) [V]; **three.js + Spark** (WebGL2, MIT) for the productized public front-end; **Potree** for billion-point LiDAR. All heavy inference server-side; **Depth Anything V2 Small** (transformers.js + WebGPU) as an optional client-side instant preview.

**Why this is the frontier-yet-shippable choice:** it pairs the literal CVPR'25 Best Paper (VGGT) and the newest Apache-licensed streaming-SLAM foundation model (lingbot-map) with the community-standard Python-served viewer (viser) and the production WebGL2 splat renderer (Spark) — every piece is real, downloadable, runs on one consumer GPU, and most are commercially clean (gsplat/Spark/viser/MoGe-2/MapAnything-apache/VGGT-Commercial). The only deliberate research-only dependencies (INRIA 3DGS, DUSt3R/MASt3R, Pi3 weights) are references, not shipped code.

---

## 7. Claim ledger (selected non-trivial claims)

| Claim | Status | Source |
|---|---|---|
| 3DGS original code = custom NON-COMMERCIAL (Inria+MPII), contact stip-sophia.transfert@inria.fr | **V** | graphdeco-inria LICENSE.md |
| VGGT = CVPR'25 Best Paper; feed-forward; <1 s; pose+depth+pointmap+tracks; ~13.6k★; default NC + commercial ckpt | **V** | facebookresearch/vggt README + CVF |
| SplaTAM Replica 0.36 / TUM 5.48; ~2.1k★; BSD-3 | **V** | SplaTAM paper + repo |
| MonoGS Replica 0.32 / TUM RGB-D 1.47 / mono 3.96; up to 10 FPS (4090); CVPR'24 Highlight+Best Demo | **V** | MonoGS paper HTML + repo |
| LoopSplat Replica 0.26 best; ScanNet++ 2.05 vs SplaTAM 89.41 | **V** | LoopSplat paper HTML |
| Photo-SLAM real-time on Jetson AGX Orin; GPL-3 | **V** | Photo-SLAM repo |
| GS-ICP-SLAM ~100 FPS; MIT | **V-claim** | GS_ICP_SLAM repo |
| MASt3R-SLAM 15 FPS, loop closure, no fixed camera model; CVPR'25 | **V** | repo + arXiv 2412.12392 |
| VGGT-SLAM aligns VGGT submaps on SL(4); NeurIPS'25; MIT-SPARK | **V** | repo + arXiv 2505.12549 |
| lingbot-map Apache-2.0 (code+weights), ~20 FPS / 10k+ frames, viser viewer, one ckpt 4.63 GB | **V** | repo README + HF + arXiv 2604.14141 |
| Gaussian-LIC/LIC2, GS-LIVM, LIV-GaussMap = genuine LIVO SLAM (fuse LiDAR for pose) vs Street/DrivingGaussian = driving NVS (LiDAR prior only) | **V** | per-repo READMEs |
| Primary survey: Tosi et al. arXiv 2402.13255 | **V** | arXiv |
| viser Apache-2.0, ~2.6k★, Python-served three.js, splats+clouds+meshes+cameras+GUI | **V** | nerfstudio-project/viser |
| Spark MIT, ~3.3k★, three.js, deliberately WebGL2, v2 LOD + .rad | **V** | sparkjsdev/spark + worldlabs blog |
| transformers.js v3 + ORT-Web run Depth-Anything-V2-Small on WebGPU (working video example) | **V** | HF blog + onnx-community card |
| WebGPU Baseline Jan 2026 (Chrome/Edge/Firefox/Safari 26+); WebNN Origin-Trial only | **V** | caniuse + web.dev + gpuweb status |
| VGGT-class ~1B ViT not browser-feasible in 2026; VGGT browser demo = Gradio (server-side) | **V (demo) / A (verdict)** | vggt repo + reasoning |
| tandt_db = 650 MB; nerfstudio poster = 715 MB; TUM fr1_xyz = 0.47 GB; Replica.zip = 12 GB; ScanNet++ ~1.5 TB | **V** | official pages |
| gsplat Apache-2.0 ~5.3k★; 2DGS/Mip-Splatting/Scaffold-GS 3DGS-derived; Pi3 code BSD-3 / weights CC-BY-NC | **V** | per-repo pages |

---

## 8. Sources

**Representations / feed-forward**
- 3DGS: https://github.com/graphdeco-inria/gaussian-splatting · LICENSE https://github.com/graphdeco-inria/gaussian-splatting/blob/main/LICENSE.md · https://arxiv.org/abs/2308.04079
- gsplat (Apache-2.0): https://github.com/nerfstudio-project/gsplat
- 2DGS: https://github.com/hbb1/2d-gaussian-splatting · https://arxiv.org/abs/2403.17888 · Mip-Splatting: https://github.com/autonomousvision/mip-splatting · Scaffold-GS: https://github.com/city-super/Scaffold-GS
- VGGT: https://github.com/facebookresearch/vggt · https://arxiv.org/abs/2503.11651 · CVF https://openaccess.thecvf.com/content/CVPR2025/html/Wang_VGGT_Visual_Geometry_Grounded_Transformer_CVPR_2025_paper.html
- DUSt3R: https://github.com/naver/dust3r · https://arxiv.org/abs/2312.14132 · MASt3R: https://github.com/naver/mast3r · https://arxiv.org/abs/2406.09756
- Pi3: https://github.com/yyfz/Pi3 · https://arxiv.org/abs/2507.13347 · pixelSplat: https://github.com/dcharatan/pixelsplat · MVSplat: https://github.com/donydchen/mvsplat · Splatt3R: https://github.com/btsmart/splatt3r · AnySplat: https://github.com/InternRobotics/AnySplat
- lingbot-map: https://arxiv.org/abs/2604.14141 · https://github.com/robbyant/lingbot-map · https://huggingface.co/robbyant/lingbot-map
- CUT3R: https://github.com/CUT3R/CUT3R · StreamVGGT: https://github.com/wzzheng/StreamVGGT · VGGT-Long: https://github.com/DengKaiCQ/VGGT-Long · MapAnything: https://github.com/facebookresearch/map-anything · Depth Anything 3: https://github.com/ByteDance-Seed/Depth-Anything-3
- MoGe / MoGe-2: https://github.com/microsoft/MoGe · https://arxiv.org/abs/2507.02546 · Depth Anything V2: https://github.com/DepthAnything/Depth-Anything-V2 · Metric3D: https://github.com/YvanYin/Metric3D · UniDepth: https://github.com/lpiccinelli-eth/UniDepth

**SLAM**
- SplaTAM: https://github.com/spla-tam/SplaTAM · https://arxiv.org/abs/2312.02126 · MonoGS: https://github.com/muskie82/MonoGS · https://arxiv.org/abs/2312.06741
- Gaussian-SLAM: https://github.com/VladimirYugay/Gaussian-SLAM · https://arxiv.org/abs/2312.10070 · Photo-SLAM: https://github.com/HuajianUP/Photo-SLAM · https://arxiv.org/abs/2311.16728
- GS-ICP-SLAM: https://github.com/Lab-of-AI-and-Robotics/GS_ICP_SLAM · https://arxiv.org/abs/2403.12550 · RTG-SLAM: https://github.com/MisEty/RTG-SLAM · https://arxiv.org/abs/2404.19706
- LoopSplat: https://github.com/GradientSpaces/LoopSplat · https://arxiv.org/abs/2408.10154 · Splat-SLAM: https://github.com/google-research/Splat-SLAM · https://arxiv.org/abs/2405.16544 · HI-SLAM2: https://arxiv.org/abs/2411.17982 · GauS-SLAM: https://arxiv.org/abs/2505.01934
- MASt3R-SLAM: https://github.com/rmurai0610/MASt3R-SLAM · https://arxiv.org/abs/2412.12392 · VGGT-SLAM: https://github.com/MIT-SPARK/VGGT-SLAM · https://arxiv.org/abs/2505.12549
- iMAP https://arxiv.org/abs/2103.12352 · NICE-SLAM https://github.com/cvg/nice-slam · Co-SLAM https://github.com/HengyiWang/Co-SLAM · Point-SLAM https://github.com/eriksandstroem/Point-SLAM · NeRF-SLAM https://github.com/ToniRV/NeRF-SLAM
- Gaussian-LIC: https://github.com/APRIL-ZJU/Gaussian-LIC · https://arxiv.org/abs/2404.06926 · GS-LIVM: https://github.com/xieyuser/GS-LIVM · LIV-GaussMap: https://github.com/sheng00125/LIV-GaussMap · Street Gaussians: https://github.com/zju3dv/street_gaussians · DrivingGaussian: https://github.com/VDIGPKU/DrivingGaussian
- LiDAR odometry: KISS-ICP https://github.com/PRBonn/kiss-icp · KISS-SLAM https://github.com/PRBonn/kiss-slam · FAST-LIO https://github.com/hku-mars/FAST_LIO · Point-LIO https://github.com/hku-mars/Point-LIO · CT-ICP https://github.com/jedeschaud/ct_icp · GLIM https://github.com/koide3/glim · MAD-ICP https://github.com/rvp-group/mad-icp
- **Survey:** Tosi et al. https://arxiv.org/abs/2402.13255 · Collaborative-3DGS-SLAM https://arxiv.org/abs/2510.23988 · 3DGS-in-Robotics https://arxiv.org/abs/2410.12262 · Awesome-3DGS-SLAM https://github.com/KwanWaiPang/Awesome-3DGS-SLAM · All-3R-SLAM https://github.com/3D-Vision-World/All-3R-SLAM-in-this-Repo

**Web stack**
- three.js https://github.com/mrdoob/three.js · viser https://github.com/nerfstudio-project/viser · https://viser.studio/main/ · rerun https://github.com/rerun-io/rerun
- Spark https://github.com/sparkjsdev/spark · https://sparkjs.dev/ · World Labs 2.0 https://www.worldlabs.ai/blog/spark-2.0 · GaussianSplats3D https://github.com/mkkellogg/GaussianSplats3D · SuperSplat https://github.com/playcanvas/supersplat · Babylon.js GS https://doc.babylonjs.com/features/featuresDeepDive/mesh/gaussianSplatting · antimatter15/splat https://github.com/antimatter15/splat
- deck.gl PointCloudLayer https://deck.gl/docs/api-reference/layers/point-cloud-layer · Potree https://github.com/potree/potree · CesiumGS https://github.com/CesiumGS/cesium · 3D-Tiles-GS-LOD https://cesium.com/blog/2026/04/27/3d-gaussian-splats-lod/
- transformers.js https://github.com/huggingface/transformers.js · v3 blog https://huggingface.co/blog/transformersjs-v3 · Depth-Anything-V2 ONNX https://huggingface.co/onnx-community/depth-anything-v2-small · ONNX Runtime Web https://github.com/microsoft/onnxruntime · WebGPU status https://caniuse.com/webgpu · https://web.dev/blog/webgpu-supported-major-browsers

**Datasets**
- tandt_db https://repo-sam.inria.fr/fungraph/3d-gaussian-splatting/datasets/input/tandt_db.zip · TUM-RGBD https://cvg.cit.tum.de/data/datasets/rgbd-dataset/download · Replica https://cvg-data.inf.ethz.ch/nice-slam/data/Replica.zip · 7-Scenes https://www.microsoft.com/en-us/research/project/rgb-d-dataset-7-scenes/ · ScanNet++ https://kaldir.vc.in.tum.de/scannetpp/ · ETH3D https://www.eth3d.net/slam_datasets · Mip-NeRF 360 https://jonbarron.info/mipnerf360/ · Sintel http://sintel.is.tue.mpg.de/ · KITTI https://www.cvlibs.net/datasets/kitti/ · KITTI-360 https://www.cvlibs.net/datasets/kitti-360/ · Oxford Spires https://dynamic.robots.ox.ac.uk/datasets/oxford-spires/ · nerfstudio data https://docs.nerf.studio/quickstart/existing_dataset.html

---

*Compiled 2026-06-29 for `wip/lidar3d/research/`. Star counts and benchmark numbers are point-in-time; re-confirm each license (code AND weights, often separate) at integration time. Sibling raw-research files: `_sub_gaussian_slam.md`, `_sub_representations.md`, `_sub_web_stack.md`, `subagent-datasets-2026-06-29.md`, `feedforward-3d-foundation-models-2026-06-29.md`, `subagent-odometry-2026-06-29.md`, `subagent-segmentation-foundation-2026-06-29.md`, `_subagent-lingbot-map.md`.*
