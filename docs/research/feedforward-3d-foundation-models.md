# State of the Art: Feed-Forward 3D/4D Scene-Reconstruction Foundation Models (the "Pointmap Regression" Lineage)

**Survey for the "Lidar 3D" research lab + interactive web app.**
**Seed model:** lingbot-map (arXiv:2604.14141, "Geometric Context Transformer for Streaming 3D Reconstruction").
**Date:** 2026-06-29. **Author:** research analyst (Lucy).

> Claim-marking convention used throughout: **[V]** = verified (seen on a primary source: the paper HTML/PDF, the GitHub README, or the HF model card). **[A]** = assumed / inferred (cross-source plausible but not directly confirmed on a primary page in this pass). Numbers in benchmark tables are **[V]** unless tagged.

---

## 1. Executive summary

**The lineage in one paragraph.** This family solves 3D reconstruction by *regressing geometry directly from pixels with a transformer*, with **no per-scene optimization** (no bundle adjustment, no NeRF/3DGS fitting at inference). It begins with **DUSt3R** (Dec 2023), which regresses a *pointmap* (per-pixel XYZ in a common frame) from an image **pair**, replacing the classic SfM/MVS pipeline. **MASt3R** (Jun 2024) adds a metric local-feature matching head; **MASt3R-SLAM** (Dec 2024) turns it into a real-time SLAM front-end. The field then split along two axes: (a) **scaling to many views** in one pass, *offline/global*: **Fast3R**, **MV-DUSt3R**, and the landmark **VGGT** (CVPR 2025 best paper) which predicts *all* 3D attributes (pose, depth, pointmap, tracks) in <1 s; and (b) **online/streaming** with *memory*: **Spann3R** (spatial memory), **CUT3R** (persistent recurrent state), **StreamVGGT**/**STream3R** (causal-attention VGGT with KV-cache), **LONG3R** (memory-gated long sequences). 2025-2026 then pushed three frontiers: **reference-free permutation-equivariant** geometry (**π³/Pi3**), **universal metric** reconstruction that ingests optional priors (**MapAnything**, Meta; **MoGe-2** for monocular metric), and **minimal-modeling SOTA** (**Depth Anything 3**, ByteDance; **AMB3R**, CVPR'26, feed-forward + sparse-volume backend). The **seed model lingbot-map** sits at the *streaming-SLAM* apex of (b): it wraps a VGGT/DINOv2 backbone in a **Geometric Context Transformer** (core = **Geometric Context Attention** over an anchor context, a k=64 pose-reference window, and a 6-token-per-frame trajectory memory, served by a **paged KV cache**), sustaining ~20 FPS over 10,000+ frames.

**Timeline (camera-only feed-forward pointmap models):**

| Date | Model | Milestone |
|---|---|---|
| 2023-12 | **DUSt3R** | pairwise pointmap regression; kills calibration/pose priors |
| 2024-06 | **MASt3R** | + metric matching head; thousands of images |
| 2024-08 | **Spann3R** | + spatial memory → online, no global alignment |
| 2024-10 | **MoGe** | monocular affine-invariant pointmap |
| 2024-12 | **MASt3R-SLAM** | real-time dense SLAM (15 FPS) from MASt3R prior |
| 2025-01 | **CUT3R** | persistent recurrent state; online metric pointmaps |
| 2025-03 | **VGGT** | **CVPR'25 best paper**; all 3D attributes in one pass, <1 s |
| 2025-03 | **Fast3R** | 1000+ images in one forward pass (offline) |
| 2025-07 | **π³ / Pi3** | reference-free, permutation-equivariant; SOTA pose/depth |
| 2025-07 | **MoGe-2** | monocular **metric** scale + sharp detail |
| 2025-07 | **StreamVGGT** / **LONG3R** | causal/streaming VGGT; long-sequence memory |
| 2025-07 | **VGGT-Long** | chunk+loop+align → kilometre-scale sequences |
| 2025-09 | **MapAnything** (Meta) | universal metric recon, ingests optional priors |
| 2025-11 | **Depth Anything 3** | minimal modeling; new SOTA (+44% pose vs VGGT) |
| 2025-11 | **AMB3R** (CVPR'26) | feed-forward metric + sparse-volume backend, beats SLAM/SfM |
| 2026-04 | **lingbot-map** *(seed)* | streaming GCT + 2-stream paged KV cache; 20 FPS / 10k+ frames |

**Bottom line for the app:** the methods with *real, downloadable, runnable-on-one-GPU* weights that matter most are **VGGT**, **π³/Pi3**, **MoGe-2**, **CUT3R/StreamVGGT** (streaming), **MapAnything** (metric, Apache option), **Depth Anything 3** (multi-size, incl. Small), and the seed **lingbot-map** (streaming SLAM, Apache-2.0, 4.63 GB). See §5 for the ranked recommendation.

---

## 2. Comparison table

Legend: **FF** = feed-forward (no per-scene optimization). **Stream** = online/incremental (vs offline global pass). **Cam-only** unless noted. Backbone "DINOv2 ViT-L" means a frozen/finetuned DINOv2 Large encoder.

| Method | Year/Venue | arXiv | Output | Stream? | FF? | Backbone | Weights + size | License | Repo (stars) |
|---|---|---|---|---|---|---|---|---|---|
| **DUSt3R** | 2023-12 / CVPR'24 | 2312.14132 | pointmap (pair), pose, depth | No (needs global align for >2) | Yes (pair); align = optimization | DINOv2 ViT-L enc + ViT-B dec | `naver/DUSt3R_ViTLarge_BaseDecoder_512_dpt` ~2.6 GB [A] | CC-BY-NC-SA 4.0 | naver/dust3r (7.2k) |
| **MASt3R** | 2024-06 / ECCV'24 | 2406.09756 | pointmap + metric local features (matching) | No | Yes (pair) | DINOv2 ViT-L + matching head | `naver/MASt3R_ViTLarge_BaseDecoder_512_catmlpdpt_metric` ~2.6 GB [A] | CC-BY-NC-SA 4.0 | naver/mast3r |
| **MASt3R-SLAM** | 2024-12 / CVPR'25 | 2412.12392 | poses + dense geometry (SLAM) | **Yes (15 FPS)** | front-end FF; back-end optimizes | MASt3R prior | uses MASt3R ckpt | CC-BY-NC (code) [A] | rmurai0610/MASt3R-SLAM |
| **Spann3R** | 2024-08 / 3DV'25 | 2408.16061 | per-frame global pointmap | **Yes (real-time)** | Yes | DUSt3R + spatial memory net | ~2.6 GB (from DUSt3R) [A] | check repo (non-permissive) [A] | HengyiWang/spann3r (1.1k) |
| **MoGe** | 2024-10 / CVPR'25 Oral | 2410.19115 | monocular affine-invariant pointmap + mask | n/a (single img) | Yes | DINOv2 ViT-L | `Ruicheng/moge-vitl` ~1.3 GB [A] | MIT (code) | microsoft/MoGe |
| **MoGe-2** | 2025-07 | 2507.02546 | monocular **metric** pointmap + normal + depth | n/a (single img) | Yes | DINOv2 ViT-L + metric head | `Ruicheng/moge-2-vitl-normal` ~1.3 GB [A] | MIT (code); weights license unclear | microsoft/MoGe |
| **CUT3R** | 2025-01 / CVPR'25 Oral | 2501.12387 | online metric pointmaps + pose (persistent state) | **Yes (online)** | Yes | ViT (DUSt3R-style) recurrent | `cut3r_512_dpt_4_64.pth` ~2 GB [A] (Google Drive) | non-commercial [A] | CUT3R/CUT3R (1.34k) |
| **VGGT** | 2025-03 / **CVPR'25 Best Paper** | 2503.11651 | pose + depth + pointmap + 3D tracks | No (offline; can chunk) | Yes (<1 s) | DINOv2 ViT-L (alternating attn) | `facebook/VGGT-1B` (1 B params) ~4-5 GB [A] | non-commercial; `VGGT-1B-Commercial` for commercial | facebookresearch/vggt (13.6k) |
| **Fast3R** | 2025-03 / CVPR'25 | 2501.13927 | dense pointmaps for 1000+ views | No (single pass, offline) | Yes | DUSt3R-style + global fusion TF | HF ckpt ~2-3 GB [A] | FAIR NC [A] | facebookresearch/fast3r |
| **π³ / Pi3** | 2025-07 / ICLR'26 | 2507.13347 | local pointmaps + affine-inv poses + conf (reference-free) | No (offline; very fast 57 FPS) | Yes | DINOv2 (959 M params) | `yyfz233/Pi3` ~3.8 GB [A]; `yyfz233/Pi3X` | BSD-3 (code), CC-BY-NC-4.0 (weights) | yyfz/Pi3 (2k) |
| **StreamVGGT** | 2025-07 / ICLR'26 | 2507.11539 | streaming pose+depth+pointmap (causal) | **Yes (low-latency)** | Yes | VGGT distilled, causal attn + KV-cache | HF ckpt ~4-5 GB [A] | check repo [A] | wzzheng/StreamVGGT |
| **LONG3R** | 2025-07 / ICCV'25 | 2507.18255 | streaming pointmaps, long seq | **Yes (real-time)** | Yes | recurrent + 3D spatio-temporal memory | HF ckpt [A] | check repo [A] | zgchen33/LONG3R |
| **VGGT-Long** | 2025-07 / ICRA'26 [A] | 2507.16443 | km-scale poses + recon (chunk+loop+align) | system over VGGT | Yes (per chunk) | VGGT + loop-closure backend | uses VGGT ckpt | check repo [A] | DengKaiCQ/VGGT-Long |
| **MapAnything** | 2025-09 (Meta) | 2509.13414 | metric depth/rays/pose/scale, accepts priors | No (offline) | Yes | DINOv2 @518px | `facebook/map-anything-apache` (~1-2 GB [A]) | **Apache-2.0** (apache ckpt) / CC-BY-NC | facebookresearch/map-anything (3.5k) |
| **Depth Anything 3 (DA3)** | 2025-11 / ICLR'26 (ByteDance) | 2511.10647 | depth-ray geometry, pose, any-view | No (offline) | Yes | plain DINO ViT (S/B/L/Giant) | DA3-Small … DA3-Giant on HF [A] | check repo [A] | ByteDance-Seed/Depth-Anything-3 |
| **AMB3R** | 2025-11 / CVPR'26 | 2511.20343 | metric pointmap+pose+depth; VO/SfM extensible | online VO mode | Yes | sparse-volume backend + TF | HF ckpt [A] | check repo [A] | HengyiWang/amb3r |
| **lingbot-map** *(seed)* | 2026-04 | **2604.14141** | streaming pointmap + pose + depth + conf (metric, SLAM) | **Yes (~20 FPS, 10k+ frames)** | Yes | **DINOv2 ViT (frozen, patch-14) + 24 alt-attn blocks** (VGGT design) | `robbyant/lingbot-map` 3 ckpts, **~13 GB total** (~4.63 GB each) | **Apache-2.0** | robbyant/lingbot-map (~8.6k) |

> Sizes tagged **[A]** are inferred from architecture (e.g. ViT-L ≈ 300 M params ≈ 1.2-1.4 GB fp32; 1 B params ≈ 4-5 GB) or from typical checkpoint sizes; only **lingbot-map (4.63 GB)** and **VGGT (1 B params)** were size-confirmed on a primary page in this pass. arXiv IDs for VGGT (2503.11651) and Fast3R (2501.13927) are widely-attributed **[A]**; MASt3R (2406.09756) per NAVER. Verify exact bytes on the HF "Files" tab before download.

---

## 3. Deep dive: lingbot-map (the seed model)

**Paper:** "Geometric Context Transformer for Streaming 3D Reconstruction", arXiv:**2604.14141** (v1, mid-April 2026). **[V]**
**Authors:** Lin-Zhuo Chen, Jian Gao, Yihang Chen, Ka Leong Cheng, Yipengjing Sun, Liangxiao Hu, Nan Xue, Xing Zhu, Yujun Shen, Yao Yao, Yinghao Xu. **[V]**
**Repo:** github.com/robbyant/lingbot-map · **Weights:** huggingface.co/robbyant/lingbot-map (+ ModelScope). **License: Apache-2.0** (code and weights). **[V]**

### 3.1 What it is
A **feed-forward 3D foundation model for streaming reconstruction**: given a video stream it recovers **camera poses and dense point clouds** online, optimizing for geometric accuracy, temporal consistency, and compute efficiency simultaneously. It is explicitly *SLAM-motivated* but **no test-time optimization / bundle adjustment** in the core path. It builds on the **VGGT / DINOv2** backbone (the same lineage as the CVPR'25 best paper). **[V]**

### 3.2 The Geometric Context Transformer / Geometric Context Attention (GCA)
The paper's core mechanism is **Geometric Context Attention (GCA)** (the architecture is the "Geometric Context Transformer"). Each new frame attends to three specialized contexts, each solving a distinct SLAM failure mode. *Note on naming:* the paper's verbatim term is a **paged KV cache** over two token populations; **"two-stream paged KV cache"** (as in the project brief) is an accurate framing of those two populations but is **not** a literal phrase in the paper. **[V from arXiv html v2]**

1. **Anchor Context — coordinate grounding + metric scale.** The first **n ≪ N** frames receive **full mutual attention** plus a **learnable anchor token**; this fixes the *global coordinate frame*. The **metric scale** is set from the anchor point cloud as `s = mean ‖x‖₂` (mean L2 norm of anchor points). New frames attend to anchors so every prediction lands in one consistent metric world frame. **[V]**
2. **Pose-Reference Window — dense geometric cues.** A **sliding window of the k = 64 most recent frames**, kept at **full image-token resolution**, supplying rich local geometry / short-baseline correspondence for accurate relative pose + local pointmaps; trained with a relative-pose loss. (README CLI exposes `--window_size` e.g. 128 and `--overlap_keyframes` e.g. 16.) **[V]**
3. **Trajectory Memory — long-range drift correction.** For **all older frames** (beyond the window) the model retains **only 6 context tokens per frame** (camera + anchor + register tokens), ordered by **Video RoPE**. This compact long-horizon memory corrects accumulated drift without a full optimization back-end. **[V]**

### 3.3 The paged KV cache (the efficiency core)
To sustain **~20 FPS at 518×378 over 10,000+ frames**, GCA cannot keep full bidirectional attention over all frames (cost grows with sequence length). The efficiency comes from a **paged KV cache** over the **two token populations** above **[V]**:
- Past frames' KV (key/value) tensors are **paged** (fixed-size blocks) rather than one growing contiguous tensor, so memory is bounded and reusable. On each new frame the cache **updates only the newly appended tokens** instead of recomputing attention over the whole history. **[V]**
- The **two token populations** are: (a) the **full-image tokens** of the k=64-frame Pose-Reference Window (short-horizon, dense, high-churn), and (b) the **6-token-per-frame** Trajectory-Memory/Anchor representation (long-horizon, sparse, stable). Splitting them keeps the dense stream small/fast while the long stream persists cheaply — this is what the brief calls "two-stream". **[V populations / [A] "stream" terminology.]**
- Implementation: the README requires **FlashInfer** "for paged KV cache attention" — the paged-attention kernel is the real runtime path. **[V]**

Net effect (verified): incremental paged updates take throughput from **~10.5 FPS → ~20 FPS** at 518×378, with **~80× lower per-frame compute growth than naive causal attention** as the sequence extends past 10k frames. **[V]**

### 3.4 Backbone, inputs / outputs
- **Backbone:** **DINOv2-initialized ViT**, **patch size 14**, kept **frozen**, followed by **24 alternating frame / cross-frame attention blocks** (the VGGT alternating-attention design). Exact ViT size is **not stated** in the paper — likely ViT-L, **unverified**. **[V except ViT size = [A]]**
- **Input:** RGB video stream (or image folder), **518×378** working resolution; optional **sky mask** via bundled `skyseg.onnx` (ONNX sky-segmentation) to drop sky pixels that corrupt geometry. **[V]**
- **Output (metric):** streaming **pointmaps**, **camera-to-world poses** (trajectory), **depth**, and **confidence**, accumulated in one common metric frame. **[V]**

### 3.5 Benchmarks (datasets + verified numbers)
Evaluated on a broad SLAM/recon suite **[V]**: **Oxford-Spires**, **ETH3D**, **7-Scenes**, **Tanks & Temples**, plus the released eval scripts also cover **KITTI**, **VBR**, **Droid-W**, **TUM-Dynamics**, **NRGBD**. It reports **beating CUT3R, VGGT, π³/Pi3, Stream3R and Wint3R** on these. Sample verified figures: **ETH3D F1 = 98.98**, **7-Scenes ATE = 0.08**. **[V]** (TUM-RGBD / KITTI / Sintel absolute numbers were *not* in the fetched tables — do **not** cite those without re-reading the PDF.)

### 3.6 How to run it (from the GitHub README) **[V]**

**Environment + dependency stack** (exactly as documented):
- **Python 3.10**, **PyTorch 2.8.0 + CUDA 12.8** (`torchvision==0.23.0`)
- **FlashInfer** (`flashinfer-python`) — paged-KV-cache attention kernel
- **viser** — browser-based 3D viewer
- **Open3D ≥ 0.19** — offline rendering
- **Kaolin** (NVIDIA) — GPU voxelization / frustum culling (install pinned to `torch-2.8.0_cu128`)
- **onnxruntime / onnxruntime-gpu** — ONNX sky-segmentation
- `pyyaml`, `numpy<2`
- CUDA extension build for offline render: `demo_render/render_cuda_ext` (`python setup.py build_ext --inplace`)

**Install:**
```bash
conda create -n lingbot-map python=3.10 -y && conda activate lingbot-map
pip install torch==2.8.0 torchvision==0.23.0 --index-url https://download.pytorch.org/whl/cu128
pip install -e .                                   # core
pip install --index-url https://pypi.org/simple flashinfer-python
pip install -e ".[vis]"                             # viser viewer
pip install -e ".[vis,render]" && pip install onnxruntime-gpu   # offline render + sky seg
pip install --index-url https://pypi.org/simple kaolin -f https://nvidia-kaolin.s3.us-east-2.amazonaws.com/torch-2.8.0_cu128.html
cd demo_render/render_cuda_ext && python setup.py build_ext --inplace
```

**Run (interactive single scene):**
```bash
python demo.py --model_path /path/lingbot-map-long.pt --image_folder example/courthouse --mask_sky
```
**Run (long video, windowed):**
```bash
python demo.py --model_path /path/lingbot-map-long.pt --video_path video.mp4 --fps 10 \
  --mode windowed --window_size 128 --overlap_keyframes 16 --keyframe_interval 2
```
**Run (offline batch render, the 25k-frame walkthrough):**
```bash
python demo_render/batch_demo.py --video_path indoor_travel.MP4 --output_folder out/ \
  --model_path /path/lingbot-map.pt --config demo_render/config/indoor.yaml \
  --mode windowed --window_size 128 --keyframe_interval 13 --overlap_keyframes 8 --sky_mask_dir out/sky_masks
```

**Hardware / VRAM:** README emphasizes ~20 FPS @ 518×378 over 10k+ frames but does not print an absolute VRAM floor. Memory controls: `--offload_to_cpu` (**on by default**), `--num_scale_frames 2` (lowers activation peak). An external reference cites feasibility on an **RTX 4060 8 GB**. **[V] flags / [A] 8 GB feasibility.**

**Weights:** three `.pt` (PyTorch) checkpoints on HF `robbyant/lingbot-map` (mirror `agramoi/lingbot-map`, + ModelScope), **~13.02 GB total** **[V]**:
- `lingbot-map.pt` — **4.63 GB** (base)
- `lingbot-map-long.pt` — **4.63 GB** (long-sequence streaming; used in demos)
- `lingbot-map-stage1.pt` — **4.76 GB** (stage-1 / intermediate)

You only need **one** for inference (typically `lingbot-map-long.pt`, ~4.63 GB), not all three. GitHub repo ~**8.6k stars** at time of survey. **[V]**

---

## 4. DOWNLOADABLE ASSETS (top ~8 to implement)

Exact PDF URL pattern is `https://arxiv.org/pdf/<id>`; weights are HF repo ids unless noted. Sizes **[A]** unless tagged.

| # | Method | arXiv PDF | Weights (HF repo id / source) | Approx size | Demo data |
|---|---|---|---|---|---|
| 1 | **lingbot-map** | https://arxiv.org/pdf/2604.14141 | `robbyant/lingbot-map` (3 ckpts; `agramoi` + ModelScope mirrors) | **~13.02 GB total [V]** (one ckpt ~4.63 GB) | `example/courthouse`; Tanks&Temples-style clips in repo |
| 2 | **VGGT** | https://arxiv.org/pdf/2503.11651 | `facebook/VGGT-1B` (research) · `facebook/VGGT-1B-Commercial` | ~4-5 GB (1 B params) | demo images in repo; Co3D for eval |
| 3 | **π³ / Pi3** | https://arxiv.org/pdf/2507.13347 | `yyfz233/Pi3` · `yyfz233/Pi3X` | ~3.8 GB (959 M params) | HF Space demo; example_mm |
| 4 | **MoGe-2** | https://arxiv.org/pdf/2507.02546 | `Ruicheng/moge-2-vitl-normal` (+`moge-2-vitl`) | ~1.3 GB (ViT-L) | single-image demos; HF Space |
| 5 | **MapAnything** | https://arxiv.org/pdf/2509.13414 | `facebook/map-anything-apache` (Apache) · `facebook/map-anything` (NC) | ~1-2 GB | repo demos; RobustMVD eval |
| 6 | **CUT3R** | https://arxiv.org/pdf/2501.12387 | `cut3r_512_dpt_4_64.pth` (Google Drive) · `cut3r_224_linear_4.pth` | ~2 GB | repo demo videos |
| 7 | **StreamVGGT** | https://arxiv.org/pdf/2507.11539 | HF + Tsinghua Cloud (see `wzzheng/StreamVGGT`) | ~4-5 GB | repo demo; 7-Scenes/NRGBD |
| 8 | **Depth Anything 3** | https://arxiv.org/pdf/2511.10647 | DA3-Small/Base/Large/Giant on HF (`ByteDance-Seed/Depth-Anything-3`) | Small ~0.1 GB → Giant several GB | repo demos |
| (alt) | **DUSt3R** | https://arxiv.org/pdf/2312.14132 | `naver/DUSt3R_ViTLarge_BaseDecoder_512_dpt` | ~2.6 GB | repo demo pairs |

---

## 5. RECOMMENDATION — top 3 to implement NOW

Goal: a **real interactive web app** ("Lidar 3D": reconstruct 3D from video/images), runnable on a single consumer GPU (ideally with CPU-offload), with **genuine downloadable weights** and a permissive-enough license.

### #1 — lingbot-map (the seed) — *the streaming centerpiece*
**Why:** It is purpose-built for exactly the app's use case — **streaming video → live metric 3D + camera trajectory at ~20 FPS over 10k+ frames** — and it is the *only* model here that is both (a) the newest SLAM-grade streaming design (paged-KV-cache Geometric Context Attention) and (b) **Apache-2.0 on both code and weights**, so it is commercially clean. You only download **one ~4.63 GB checkpoint** to run (all three total ~13 GB). It ships a **viser** browser viewer out of the box, which maps directly onto a web app, and a sky-mask ONNX step that improves outdoor quality. Verified to beat CUT3R/VGGT/Pi3/Stream3R on ETH3D/7-Scenes/Oxford-Spires/Tanks&Temples (e.g. ETH3D F1 98.98, 7-Scenes ATE 0.08).
**VRAM/CPU:** `--offload_to_cpu` on by default + `--num_scale_frames 2`; external report claims **RTX 4060 8 GB** feasible **[A]**. Plan for **8-12 GB VRAM** for live, more for the 25k-frame offline render. CPU-only inference is not the design target (FlashInfer/Kaolin/CUDA exts are CUDA-bound) — treat CPU as offload, not standalone.
**Watch-outs:** heavy native stack (PyTorch 2.8 / CUDA 12.8 / FlashInfer / Kaolin / CUDA build) — pin a Docker image. Verify the numeric benchmarks from the PDF before publishing claims (README had no inline table).

### #2 — VGGT — *the proven, well-supported backbone for the "drop a few photos / a clip" path*
**Why:** CVPR'25 **best paper**, **13.6k stars**, the most battle-tested feed-forward model, reconstructs pose+depth+pointmap+**tracks** in **<1 s**, and has a clean `from_pretrained("facebook/VGGT-1B")` 5-line API. It is the backbone lingbot-map itself builds on, so sharing it across the app is architecturally coherent. For commercial use there is a dedicated **VGGT-1B-Commercial** checkpoint, removing the license blocker. Excellent for the *offline/"snapshot"* mode of the app (upload N images → instant scene) complementing lingbot-map's *streaming* mode.
**VRAM/CPU:** 1 B params; runs comfortably on **≥12 GB** for moderate view counts; supports chunking; hundreds of views need more. CPU-offload possible but slow.

### #3 — MoGe-2 — *the single-image / cold-start + lightweight tier*
**Why:** The cheapest, most permissive (**MIT** code), **metric-scale monocular** model — one image → metric pointmap + normals + depth on a **DINOv2 ViT-L (~1.3 GB)** at ~60 ms/frame on a 3090/A100. It is the ideal **fallback/preview** path: instant single-frame 3D when there is no video, a thumbnail/cold-start before the streaming model warms up, and a low-VRAM tier for weaker clients. Pairs naturally with #1/#2.
**VRAM/CPU:** ViT-L fits in **4-6 GB**; the most CPU-tolerant of the three (still GPU-preferred).

**Honorable mentions / when to upgrade:**
- **π³/Pi3** — if you want the **best pose/depth accuracy** for the offline multi-image path (beats VGGT and CUT3R on Sintel ATE 0.074 vs 0.167 vs 0.217; ETH3D acc 0.194 vs 0.280) and 57 FPS throughput — **but weights are CC-BY-NC-4.0** (non-commercial), so research/app-demo only.
- **MapAnything (Apache ckpt)** — if you need **metric, prior-conditioned** reconstruction (feed known intrinsics/poses/depth) with a commercial-clean license.
- **Depth Anything 3** — if you want a **single family across sizes** (Small for cheap clients → Giant for quality) and current top accuracy (claimed +44% pose / +25% geometry over VGGT).
- **CUT3R / StreamVGGT** — alternative streaming engines if lingbot-map's native stack proves hard to containerize; CUT3R is online+metric with a persistent state; StreamVGGT is a causal VGGT with KV-cache (close to VGGT accuracy, online).

**Suggested app architecture:** **lingbot-map** for *live streaming reconstruction* (the hero feature) · **VGGT** (Commercial ckpt) for *offline multi-image "instant scene"* · **MoGe-2** for *single-image preview / low-VRAM tier*. All three share the **DINOv2/VGGT** lineage, so a single weights-management + preprocessing layer serves all.

---

## 6. Key benchmark numbers captured (verified from sources)

**π³/Pi3 vs baselines — camera pose, Sintel (lower = better)** [V, from Pi3 paper html v2]:
- ATE: **π³ 0.074** · VGGT 0.167 · CUT3R 0.217 · DUSt3R 0.371
- RPE-trans: π³ 0.040 · VGGT 0.062 · CUT3R 0.070
- RPE-rot: π³ 0.282 · VGGT 0.491 · CUT3R 0.636

**π³ — point map, ETH3D (lower = better)** [V]: Acc(mean) **π³ 0.194** · VGGT 0.280 · CUT3R 0.617; Comp(mean) π³ 0.210 · VGGT 0.305.
**π³ — video depth, Sintel, scale-only** [V]: AbsRel **π³ 0.233** · VGGT 0.299 · CUT3R 0.417; δ<1.25 π³ 0.664 · VGGT 0.638.
**π³ spec** [V]: 959 M params, DINOv2 backbone, 57.4 FPS on KITTI (A800).

**StreamVGGT vs CUT3R — reconstruction (lower = better)** [V]: 7-Scenes Acc 0.129 mean / 0.056 med; NRGBD Acc 0.084 mean / 0.044 med; "surpasses CUT3R on 7-Scenes and NRGBD". Trained on 14 datasets incl. Sintel, Bonn, KITTI, NYU-v2, ScanNet, 7-Scenes, NRGBD.

**Depth Anything 3** [V claim from abstract]: new SOTA on its visual-geometry benchmark, **+44.3% camera-pose accuracy and +25.1% geometric accuracy over VGGT** (avg).

**VGGT** [V]: reconstructs in **<1 s**; SOTA on camera pose, multi-view depth, dense point cloud, 3D tracking; 1 B params; DINOv2 backbone.

**Fast3R** [V]: 1000+ images one forward pass; up to 1500 views on one A100; 251.1 FPS at 108×224×224.

**MASt3R-SLAM** [V]: 15 FPS, globally-consistent poses + dense geometry, no fixed camera model.

**lingbot-map (seed)** [V]: **~20 FPS @ 518×378 over 10k+ frames** (10.5→20 via paged updates; ~80× lower per-frame growth than causal attn); **ETH3D F1 98.98**, **7-Scenes ATE 0.08**; beats CUT3R, VGGT, π³, Stream3R, Wint3R on Oxford-Spires/ETH3D/7-Scenes/Tanks&Temples.

> All other quantitative claims (DUSt3R/MASt3R absolute numbers, MoGe-2 metric error, AMB3R vs SLAM) were **not** read off a primary table in this pass — pull from the respective PDFs before publishing.

---

## 7. Camera-only vs camera+depth/LiDAR; FF vs optimization; streaming vs offline

- **Camera-only (RGB) feed-forward:** DUSt3R, MASt3R, Spann3R, CUT3R, VGGT, Fast3R, π³, StreamVGGT, LONG3R, MoGe(-2), DA3, lingbot-map. None *require* depth/LiDAR.
- **Accept optional depth/intrinsics/pose priors (still RGB-first):** **MapAnything** (depth, intrinsics, poses, rays), **AMB3R** (metric backend), G-CUT3R, Pow3R, Pi3X (optional pose/depth conditioning). These can *fuse* a LiDAR/depth channel — relevant if "Lidar 3D" later ingests real LiDAR.
- **Pure feed-forward (no per-scene optimization at inference):** VGGT, Fast3R, π³, CUT3R, Spann3R, StreamVGGT, MoGe(-2), DA3, MapAnything, lingbot-map core path.
- **Feed-forward front-end + optimization back-end:** DUSt3R/MASt3R *multi-view* (global aligner), MASt3R-SLAM (loop closure + 2nd-order opt), VGGT-Long (loop closure align), VGGT-SLAM.
- **Streaming / online (incremental, bounded memory):** Spann3R, CUT3R, StreamVGGT, STream3R, LONG3R, MASt3R-SLAM, AMB3R-VO, **lingbot-map**.
- **Offline / global (one big pass, or many-view batch):** DUSt3R, MASt3R, Fast3R, VGGT, π³, MapAnything, DA3 (these *can* be chunked, but are not natively bounded-memory streaming).

---

## 8. Sources (URLs consulted)

**Seed model (lingbot-map):**
- https://arxiv.org/abs/2604.14141 · https://arxiv.org/html/2604.14141v1 · https://arxiv.org/pdf/2604.14141
- https://github.com/robbyant/lingbot-map · https://raw.githubusercontent.com/robbyant/lingbot-map/main/README.md
- https://huggingface.co/robbyant/lingbot-map · https://huggingface.co/agramoi/lingbot-map
- https://www.alphaxiv.org/abs/2604.14141 · https://huggingface.co/papers/2604.14141 · https://papers.cool/arxiv/2604.14141

**Core lineage:**
- DUSt3R: https://arxiv.org/abs/2312.14132 · https://github.com/naver/dust3r · https://huggingface.co/naver/DUSt3R_ViTLarge_BaseDecoder_512_dpt
- MASt3R: https://arxiv.org/abs/2406.09756 · https://europe.naverlabs.com/blog/mast3r-matching-and-stereo-3d-reconstruction/
- MASt3R-SLAM: https://arxiv.org/abs/2412.12392 · https://edexheim.github.io/mast3r-slam/
- Spann3R: https://arxiv.org/abs/2408.16061 · https://github.com/HengyiWang/spann3r
- CUT3R: https://arxiv.org/abs/2501.12387 · https://github.com/CUT3R/CUT3R · https://cut3r.github.io/
- VGGT: https://github.com/facebookresearch/vggt · https://openaccess.thecvf.com/content/CVPR2025/html/Wang_VGGT_Visual_Geometry_Grounded_Transformer_CVPR_2025_paper.html
- Fast3R: https://github.com/facebookresearch/fast3r · https://opencv.org/blog/fast3r/
- π³/Pi3: https://arxiv.org/abs/2507.13347 · https://arxiv.org/html/2507.13347v2 · https://github.com/yyfz/Pi3 · https://yyfz.github.io/pi3/
- StreamVGGT: https://arxiv.org/abs/2507.11539 · https://github.com/wzzheng/StreamVGGT · https://wzzheng.net/StreamVGGT/
- LONG3R: https://arxiv.org/abs/2507.18255 · https://github.com/zgchen33/LONG3R
- VGGT-Long: https://arxiv.org/abs/2507.16443 · https://github.com/DengKaiCQ/VGGT-Long
- MoGe / MoGe-2: https://arxiv.org/abs/2410.19115 · https://arxiv.org/abs/2507.02546 · https://github.com/microsoft/MoGe · https://huggingface.co/Ruicheng/moge-2-vitl-normal
- MapAnything: https://arxiv.org/abs/2509.13414 · https://arxiv.org/html/2509.13414v2 · https://github.com/facebookresearch/map-anything
- Depth Anything 3: https://arxiv.org/abs/2511.10647 · https://depth-anything-3.github.io/ · https://github.com/ByteDance-Seed/Depth-Anything-3
- AMB3R: https://arxiv.org/abs/2511.20343 · https://github.com/HengyiWang/amb3r

**Surveys / indexes (cross-check):**
- Survey "Advances in Feed-Forward 3D Reconstruction and View Synthesis": https://arxiv.org/html/2507.14501v1
- "All-3R-SLAM-in-this-Repo" index: https://github.com/3D-Vision-World/All-3R-SLAM-in-this-Repo
- awesome-dust3r: https://github.com/ruili3/awesome-dust3r

---

## 9. Open items to verify before building (don't ship on [A])
1. **Exact weight sizes** (HF "Files" tab) for VGGT, Pi3, MapAnything, StreamVGGT, DA3, CUT3R — only lingbot-map (4.63 GB) and VGGT (1 B params) confirmed here.
2. **lingbot-map numeric benchmarks** — partial figures captured (ETH3D F1 98.98, 7-Scenes ATE 0.08); read the *full* ATE/RPE/Acc tables (KITTI/TUM/Sintel rows) from arXiv:2604.14141 PDF before citing those — they were not in the fetched tables.
3. **arXiv IDs** for VGGT (2503.11651) and Fast3R (2501.13927) — widely attributed, confirm on abstract page.
4. **License of weights** for Spann3R, CUT3R, StreamVGGT, LONG3R, DA3, AMB3R — repos read as "check" here; confirm commercial vs NC before any product use.
5. **CPU-offload reality** for lingbot-map on 8 GB — the RTX 4060 claim is [A]; benchmark on your target GPU.
