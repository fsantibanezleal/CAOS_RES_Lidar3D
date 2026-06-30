# LingBot-Map — deep dive (seed model for the Lidar3D research lab)

**Date:** 2026-06-29 · **Source:** arXiv:2604.14141 (HTML v1), GitHub `Robbyant/lingbot-map`, HF `robbyant/lingbot-map`
**Status of facts:** *verified* against the arXiv HTML + GitHub/HF README unless marked *assumed*.

LingBot-Map is the seed Felipe handed for this lab: a **feed-forward 3D foundation model for streaming
3D reconstruction**. It recovers per-frame **camera pose + dense metric depth + point cloud** from a
*causal* video stream (current and past frames only, no future), staying stable over **10,000+ frames**
at **~20 FPS @ 518×378**, with **no per-scene optimization and no loop closure**. It is the current
(2026-04) SOTA among *online/streaming* feed-forward reconstructors.

---

## 1. Problem: streaming 3D reconstruction

Given frames arriving one at a time `{I_1,…,I_t}`, output at each `t` the absolute camera pose `P̂_t`
(camera-to-world, 6-DOF), a dense depth map `D̂_t`, an uncertainty map, and (by reprojection) a point
cloud — **causally**, with a **compact** streaming state, at high FPS, drift-free over very long runs.
This is the SLAM problem cast as a single feed-forward network (no bundle adjustment, no optimization).

## 2. Architecture — Geometric Context Transformer (GCT)

**Backbone:** DINOv2 ViT, patch 14. Per frame the token set is:
`M` image tokens (≈500 at 518×378) + 1 camera token + 4 register tokens + 1 learnable anchor token.
**Trunk:** 24 layers **alternating** *Frame Attention* (within-frame refinement) and *Geometric Context
Attention* (cross-frame reasoning). **Heads:** camera head → `P̂_t`; depth head → `D̂_t` (+ uncertainty).

The novelty is the **three-tier context** the cross-frame attention sees (this is what keeps state
compact while preserving long-range geometry):

| Tier | What it is | Tokens kept | Role |
|---|---|---|---|
| **Anchor context** | first `n` frames (`n≪N`, n=3 default) | full image tokens + learnable anchor token | fixes the **world coordinate frame + absolute scale** |
| **Pose-reference window** | the `k` most recent frames (k=64 default; 16–64 in train) | full image tokens (≈500/frame) | **dense local geometry**; relative-pose loss over all pairs in-window |
| **Trajectory memory** | every older frame | compressed to **6 context tokens** each (camera + 4 register + anchor), image tokens discarded | cheap **long-range** drift anchoring; ordered by **Video RoPE** |

**Per-frame context size:** `(n+k)·M + 6T` — a constant part `(n+k)·M` plus a *linear-in-T but tiny*
`6T`. Versus causal attention's `M·T + 6T`. For M≈500, n=3, k=16, T=10,000 → **~7×10⁴ vs ~5×10⁶ tokens
(≈80× reduction)**. A structured attention mask partitions the three context types.

**Paged KV cache (FlashInfer):** paged layout avoids cache-realloc overhead → **~20 FPS** vs ~10.5 FPS
for a contiguous-layout PyTorch baseline. **SDPA fallback exists when FlashInfer is unavailable**
(important for us — see §6).

## 3. I/O

- **In:** RGB video frames (intrinsics implicit in the ViT encoding — *self-calibrating*).
- **Out per frame:** absolute pose `P̂_t` (cam-to-world), dense **metric** depth `D̂_t`, per-pixel
  uncertainty `Σ_D`, and a point cloud via depth+pose reprojection.

## 4. Training (context, not something we'll redo)

Two stages, **~37k GPU-hours total** (FSDP, bf16, gradient checkpointing, Ulysses context-parallel ×16,
TorchTitan):
- **Stage 1 — base, offline, bidirectional/global attention.** 160K it, ~21.5k GPU-h, 2–24 views, **29
  datasets** (BlendedMVS, HyperSim, MegaDepth, CO3D, Objaverse, TartanAir/V2, VirtualKITTI, Replica,
  ScanNet/++, MatrixCity, Aria, …). Checkpoint shipped as `lingbot-map-stage1.pt` (bidirectional).
- **Stage 2 — streaming, causal, GCA.** 160K it, ~15.4k GPU-h, views **24→320** (progressive), window
  `k∈[16,64]`, up-weighted video data (TartanAir/Ground, MatrixCity, **Waymo, KITTI-360**, ScanNet++,
  Gibson, Matterport3D, HM3D). "Foldback video sampler". Ships as `lingbot-map.pt` / `lingbot-map-long.pt`.

**Loss:** `L = λ_d·L_depth + λ_abs·L_abs-pose + λ_rel·L_rel-pose` (relative pose over all in-window pairs).

## 5. Results (verified, selected)

- **Oxford Spires, sparse 320 frames** — ATE **6.42** (vs VGGT 24.78, CUT3R 18.16, VIPE-optim 10.52);
  AUC@30 **75.16** (next best DA3 56.68). **Online beats offline + optimization methods.**
- **Oxford Spires, dense 3,840 frames** — ATE **7.11** (ΔATE only **+0.69** vs sparse), at **20.29 FPS**.
  CUT3R degrades 18.16→32.47, Wint3R 21.10→32.90 at 3.88 FPS. **This long-sequence stability is the
  headline.**
- **ETH3D:** pose ATE 0.22, **reconstruction F1 98.98** (next best 77.28). **7-Scenes:** ATE 0.08, F1
  80.39. **Tanks&Temples:** ATE 0.20, AUC@30 92.80. **NRGBD:** F1 64.26.
- **Ablation:** anchor init + context tokens + Video RoPE each help (ATE 8.59→5.98). Window k=64 beats
  full causal on accuracy *and* is 1.7× faster, 2.7× less memory.

**Baselines it beats:** VGGT, DA3, Pi3, Fast3R (offline); DroidSLAM, MegaSAM, VIPE (optimization);
StreamVGGT, SLAM3R, InfiniteVGGT, Spann3R, Stream3R, CUT3R, TTT3R, Wint3R (streaming).

## 6. Running it — practical facts that bind our implementation

**Memory:** default window k=64 → **13.28 GB VRAM**; full-causal → 36 GB. → On our **RTX 4070 Laptop
(8 GB VRAM)** we must reduce `k` (e.g. 16–24), use **CPU offloading** (README supports it), lower
resolution, and the **SDPA fallback** (no FlashInfer, since no CUDA toolkit/`nvcc` here to build it).
Expect well under 20 FPS locally — fine for a research workbench; the headline FPS assumes a datacenter GPU.

**Two inference modes:**
- **Direct** (default): pure causal accumulation, stable to ~3,000 frames (~10× train length).
- **VO mode**: overlapping windows + per-window state reset + **Sim(3) alignment** between windows →
  arbitrarily long (tens of thousands of frames), at the cost of boundary alignment error.

**Stack (from GitHub README):** PyTorch 2.8.0 / CUDA 12.8, **FlashInfer** (paged KV; SDPA fallback),
ONNX Runtime (sky segmentation), NVIDIA **Kaolin** (batch render), **Open3D** (point cloud), FFmpeg,
**viser** browser viewer (default port 8080). Keyframe interval + windowed inference for long video.

**Checkpoints (HF `robbyant/lingbot-map`, Apache-2.0, 28.06 GB total):**
`lingbot-map.pt` (4.63 GB, balanced) · `lingbot-map-long.pt` (4.63 GB, long sequences) ·
`lingbot-map-stage1.pt` (4.76 GB, bidirectional/offline). Stored on an external scratch volume under
`$LIDAR3D_MODELS_ROOT/lingbot-map/` (never in git).

## 7. Author-stated limitations (→ our differentiation opportunities)

1. **No explicit loop closure** — drift on revisits not corrected. *(We can add loop closure / pose-graph.)*
2. **Trajectory-memory compression loses fine detail** over tens of thousands of frames.
3. **No test-time optimization** — no per-scene refinement of geometry.

These three are exactly where a research lab adds value: **loop closure + global pose-graph**, **fusion
with LiDAR/depth priors**, and an **optional refinement (3DGS / BA) stage** on top of the feed-forward map.

## 8. Why this is the right seed

It is the newest (2026-04), is **feed-forward** (real-time-ish, no optimization → demo-able in a
browser), ships **Apache-2.0 weights**, has a **viser** viewer we can build the web app around, and its
**stated gaps** (loop closure, LiDAR fusion, refinement) give the lab a real, novel research agenda
rather than a re-implementation. See `proposal.md` for how the lab is built around it.
