# 05 · The SOTA lineage: DUSt3R, VGGT, lingbot-map

This page places the engine in its field. The whole family solves 3D reconstruction by **regressing geometry
directly from pixels with a transformer, no per-scene optimization at inference** (the "pointmap regression"
lineage). Reading it explains *why* lingbot-map looks the way it does: every component ([02](02_geometric-context-transformer.md))
is inherited from a specific ancestor, and its novelty is precisely the streaming machinery the ancestors
lacked. Full survey with claim-marking: `docs/research/feedforward-3d-foundation-models.md`.

---

## 1. The one-paragraph history

**DUSt3R** (Dec 2023) started it: regress a **pointmap** (per-pixel XYZ in a common frame) from an image
**pair**, replacing the classic SfM/MVS pipeline and its calibration/pose priors. **MASt3R** (Jun 2024) added
a **metric** local-feature matching head; **MASt3R-SLAM** (Dec 2024) turned that prior into a real-time SLAM
front-end. The field then split: (a) **scale to many views in one offline pass**, culminating in **VGGT**
(CVPR'25 best paper), which predicts *all* 3D attributes (pose, depth, pointmap, tracks) in under a second;
and (b) **online / streaming with memory**, through **Spann3R** (spatial memory), **CUT3R** (persistent
recurrent state), and **StreamVGGT** (causal VGGT with a KV cache). 2025–26 pushed three more frontiers:
**reference-free permutation-equivariant** geometry (**pi3**), **universal metric** reconstruction that
ingests optional priors (**MapAnything**, Meta), and **minimal-modeling SOTA** (**Depth Anything 3**). The
seed engine **lingbot-map** (Apr 2026) sits at the **streaming-SLAM apex** of branch (b): it wraps the
VGGT/DINOv2 backbone in a **Geometric Context Transformer** and sustains ~20 FPS over 10,000+ frames.

## 2. What each step added

| Model | Date | The one thing it added | What lingbot-map inherits |
|---|---|---|---|
| **DUSt3R** | 2023-12 | pointmap regression from an image **pair**; kills the need for calibration/pose priors | the pointmap representation ([03](03_pointmaps-and-geometry.md)); self-calibration |
| **MASt3R** | 2024-06 | a **metric** matching head; scales toward thousands of images | metric output (metric depth + scale) |
| **MASt3R-SLAM** | 2024-12 | real-time dense **SLAM** front-end (15 FPS) from the MASt3R prior | the "feed-forward prior as a SLAM front-end" idea |
| **Spann3R** | 2024-08 | **spatial memory** (online, no global alignment) | the notion of a persistent streaming **state** |
| **CUT3R** | 2025-01 | **persistent recurrent state**; online **metric** pointmaps + pose | streaming causal operation; metric online recon |
| **VGGT** | 2025-03 (best paper) | **all** 3D attributes in one pass, <1 s; **DINOv2 + alternating attention** | the **backbone + 24 alternating-attention blocks** ([02 §2–3](02_geometric-context-transformer.md)) |
| **Fast3R** | 2025-03 | 1000+ views in one forward pass (offline) | evidence that many-view single-pass works |
| **pi3 / Pi3** | 2025-07 | **reference-free, permutation-equivariant** geometry; SOTA pose/depth | robustness of frozen-backbone geometry regression |
| **StreamVGGT** | 2025-07 | **causal** VGGT with a **KV cache** (low latency) | the causal-attention + **KV-cache** streaming mechanism ([02 §6](02_geometric-context-transformer.md)) |
| **MapAnything** | 2025-09 (Meta) | **universal metric** recon that ingests **optional priors** (depth/intrinsics/pose) | the "accept priors / fuse modalities" direction (informs [06 D2](06_novel-agenda.md)) |
| **Depth Anything 3** | 2025-11 | **minimal modeling** SOTA (+44% pose vs VGGT) | evidence the backbone prior is the main lever |
| **lingbot-map** *(seed)* | 2026-04 | **streaming apex**: Geometric Context Attention (anchor + window + 6-token memory) + **two-stream paged KV cache**, 20 FPS / 10k+ frames | (this is the engine) |

The two ancestors that matter most for reading the code are **VGGT** (the backbone and alternating-attention
trunk are VGGT's) and **StreamVGGT** (the causal + KV-cache streaming pattern is that branch). lingbot-map's
*own* contribution is the **three-context partition** and the **paged cache** that make streaming cheap over
very long sequences, plus the **anchor metric-scale** grounding.

## 3. The axes that separate them

- **Feed-forward vs optimization.** All of the above are feed-forward in the core path (no bundle adjustment
  at inference). Some pair a feed-forward front-end with an optimization back-end (DUSt3R/MASt3R multi-view
  global aligner; MASt3R-SLAM and VGGT-Long add loop closure). lingbot-map's core is pure feed-forward, and
  it explicitly has **no** optimization back-end, which is the gap [06 D4](06_novel-agenda.md) probes.
- **Streaming vs offline.** Offline (DUSt3R, VGGT, Fast3R, pi3, MapAnything, DA3) see the whole clip; they
  cannot run on a live camera and are not bounded-memory. Streaming (Spann3R, CUT3R, StreamVGGT, lingbot-map)
  are causal and bounded-memory. Only the streaming branch can drive the (dormant) live lane.
- **Camera-only vs prior-conditioned.** Most are RGB-only. MapAnything and AMB3R accept optional depth /
  intrinsics / pose priors and can fuse a LiDAR/depth channel, the natural template for the lab's cross-modal
  work ([06 D2](06_novel-agenda.md)).
- **Scale.** Monocular RGB is scale-ambiguous; the metric-capable models (MASt3R, CUT3R, MapAnything,
  lingbot-map) each resolve scale somehow. lingbot-map resolves it from the **anchor point cloud**
  ([02 §4.1](02_geometric-context-transformer.md#41-anchor-context-coordinate-grounding-metric-scale)).

## 4. Where lingbot-map wins (verified figures)

From the paper's tables (`docs/research/lingbot-map-deep-dive.md`, marked verified there):

- **Oxford-Spires, sparse 320 frames:** ATE **6.42** (vs VGGT 24.78, CUT3R 18.16, VIPE-optim 10.52); AUC@30
  **75.16**. Online beats offline + optimization.
- **Oxford-Spires, dense 3,840 frames:** ATE **7.11** (only **+0.69** over sparse) at **20.29 FPS**, while
  CUT3R degrades 18.16 to 32.47 and Wint3R 21.10 to 32.90 at 3.88 FPS. **Long-sequence stability is the headline.**
- **ETH3D:** pose ATE 0.22, reconstruction **F1 98.98** (next best 77.28). **7-Scenes:** ATE 0.08, F1 80.39.
  **Tanks & Temples:** ATE 0.20, AUC@30 92.80.
- **Ablation:** anchor init + context tokens + Video-RoPE each help (ATE 8.59 down to 5.98). Window $k=64$ beats
  full causal on accuracy *and* is 1.7× faster, 2.7× less memory.

It reports beating VGGT, DA3, Pi3, Fast3R (offline); DroidSLAM, MegaSAM, VIPE (optimization); and
StreamVGGT, SLAM3R, Spann3R, CUT3R, Wint3R (streaming). The **dense ATE = 7.11 on Oxford-Spires** is the
number the lab's novel agenda measures against ([06](06_novel-agenda.md)): the honest bar is a reproducible
reduction of *that* number from a frozen-backbone add-on.

## 5. Why this is the right seed for a research lab

It is the newest (2026-04), is **feed-forward** (real-time-ish, demo-able), ships **Apache-2.0** weights (one
~4.63 GB checkpoint suffices for inference), and, decisively, its **stated limitations are a real research
agenda** rather than a re-implementation exercise: no loop closure, lossy long-term memory, no test-time
optimization. A lab adds value exactly there ([06](06_novel-agenda.md)).

## 6. References (arXiv / DOI)

| Method | arXiv | Venue |
|---|---|---|
| **lingbot-map** (seed) | [2604.14141](https://arxiv.org/abs/2604.14141) | 2026-04, Apache-2.0 |
| VGGT | [2503.11651](https://arxiv.org/abs/2503.11651) | CVPR 2025 (best paper) |
| DUSt3R | [2312.14132](https://arxiv.org/abs/2312.14132) | CVPR 2024 |
| MASt3R | [2406.09756](https://arxiv.org/abs/2406.09756) | ECCV 2024 |
| MASt3R-SLAM | [2412.12392](https://arxiv.org/abs/2412.12392) | CVPR 2025 |
| Spann3R | [2408.16061](https://arxiv.org/abs/2408.16061) | 3DV 2025 |
| CUT3R | [2501.12387](https://arxiv.org/abs/2501.12387) | CVPR 2025 (oral) |
| Fast3R | [2501.13927](https://arxiv.org/abs/2501.13927) | CVPR 2025 |
| pi3 / Pi3 | [2507.13347](https://arxiv.org/abs/2507.13347) | ICLR 2026 |
| StreamVGGT | [2507.11539](https://arxiv.org/abs/2507.11539) | ICLR 2026 |
| MapAnything (Meta) | [2509.13414](https://arxiv.org/abs/2509.13414) | 2025-09 |
| Depth Anything 3 (ByteDance) | [2511.10647](https://arxiv.org/abs/2511.10647) | ICLR 2026 |
| KISS-ICP (LiDAR, [04](04_lidar-odometry.md)) | [2209.15397](https://arxiv.org/abs/2209.15397) | RA-L 2023 |

The paper PDFs are not committed (public arXiv docs, repo kept lean); fetch on demand per
`docs/research/references.md`.
