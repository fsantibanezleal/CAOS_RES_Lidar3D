# 06 · The novel agenda (D1–D5)

The lab does not merely *use* SOTA; it pursues lingbot-map's three stated gaps and two natural extensions,
each as a **frozen-backbone add-on** on the well-structured geometric-context state
([02 §9](02_geometric-context-transformer.md#9-what-this-buys-the-lab-and-where-it-stops)). This page states
each direction as a falsifiable research plan: hypothesis, method, feasibility on an 8–24 GB GPU, and the
benchmark + metric that would show a win. Labs are exploratory; a null result is a valid result and is kept.

The engine's own limitations (`docs/research/lingbot-map-deep-dive.md` §7) anchor the agenda:

1. **No explicit loop closure**: drift on revisits is uncorrected.
2. **Trajectory-memory compression** loses fine detail over tens of thousands of frames.
3. **No test-time optimization**: no per-scene refinement of geometry.

---

## The honest bar (read first)

A direction "wins" only if it produces a **reproducible ATE reduction on Oxford-Spires dense** (the paper's
own hardest, headline benchmark: ATE **7.11** over 3,840 frames at 20.29 FPS; [05 §4](05_sota-lineage.md))
**from a frozen-backbone add-on**, i.e. without retraining the ~1B DINOv2/GCT trunk (which cost ~37k
GPU-hours and is out of reach). Everything below is measured against that bar. Secondary metrics (F1 on
ETH3D, RPE, revisit-consistency) support the story but do not replace it. Claims are cross-checked against the
**actual engine output**, never merely asserted; overclaiming a "planned" result as done is a defect.

Common feasibility fact used throughout: the backbone runs the 8 GB-safe config
([guide 03](../guides/03_gpu-lane.md), peak ~7.1 GB). Any add-on must fit in the **remaining** headroom of an
8–24 GB card, which is why every direction below is a **small head or a graph/optimizer on the emitted state**,
not a change to the trunk.

---

## D1 · Learned loop-closure + pose-graph head on the frozen state

**Gap addressed:** #1 (no loop closure). This is the flagship.

**Hypothesis.** The frozen geometric-context state already contains a place-recognizable signature per frame
(the 6 special tokens that lingbot-map keeps as trajectory memory,
[02 §4.3](02_geometric-context-transformer.md#43-trajectory-memory-long-range-drift-correction)). A light
learned head on those tokens can (a) detect revisits and (b) supply loop constraints to a pose-graph
optimizer that corrects accumulated drift, **without** touching the backbone.

**Method.**
1. **Descriptor head.** Train a small MLP/attention head mapping a frame's special tokens (or a pooled patch
   summary) to an $L^2$-normalized global descriptor $d_i \in \mathbb{R}^{128}$; contrastive loss with
   revisit pairs mined from sequences that revisit (the `loop` case is exactly this).
2. **Loop detection.** Nearest-neighbor search over $\{d_i\}$ (FAISS); a candidate $(i,j)$ is a loop if
   $\lVert d_i - d_j\rVert < \tau$ and geometrically verified (a quick ICP / relative-pose check between the
   two frames' clouds gives the loop transform $\Delta_{ij}$).
3. **Pose-graph optimization.** Build a graph with odometry edges (consecutive $\hat P$) and loop edges
   $\Delta_{ij}$; minimize
   $$
   \sum_{(a,b)\in\text{odom}} \rho\big(\lVert \log(\hat P_a^{-1}\hat P_b \, Z_{ab}^{-1})\rVert^2_{\Sigma}\big)
   \;+\; \sum_{(i,j)\in\text{loops}} \rho\big(\lVert \log(\hat P_i^{-1}\hat P_j \, \Delta_{ij}^{-1})\rVert^2_{\Sigma}\big)
   $$
   with a robust kernel $\rho$ (g2o / GTSAM / Ceres). This redistributes drift so the trajectory closes.

**Feasibility (8–24 GB).** Very high. The descriptor head is $\ll$ 10 M params; the pose graph is CPU (g2o).
No backbone gradients. This is precisely how **KISS-SLAM** upgrades KISS-ICP ([04 §7](04_lidar-odometry.md)),
so the recipe is proven on the LiDAR side; here it operates on the camera engine's state.

**Benchmark + metric.** Oxford-Spires **dense** and the `loop` revisit case. Win = **ATE drop** vs the
no-loop baseline (target: measurably below 7.11 on dense; and a visible seam-closing on `loop`). Secondary:
revisit-consistency (distance between the two world positions assigned to the same place before/after
closure). Ablation must show the gain is the loop head, not incidental.

---

## D2 · LiDAR-odometry-as-teacher cross-modal distillation

**Gap addressed:** metric/scale robustness; complements #3. Natural given the lab's two modalities
([04 §8](04_lidar-odometry.md)).

**Hypothesis.** A metric, lighting-invariant LiDAR trajectory (KISS-ICP) is a strong **teacher** for the
camera engine's pose head on sequences where both sensors are present (KITTI-360, Waymo, Oxford-Spires has
LiDAR). Distilling the LiDAR pose/scale signal into a **small adapter** on the frozen camera state should
tighten scale and reduce drift on hard (textureless / low-light) segments, without retraining the trunk.

**Method.** On paired camera+LiDAR sequences, run KISS-ICP to get teacher poses $P^{\text{lidar}}_i$
(metric). Train a small residual **pose-adapter** $\delta_\theta$ on the frozen camera state to minimize a
relative-pose distillation loss
$\sum_i \lVert \log\big((\hat P_i\,\delta)^{-1} P^{\text{lidar}}_i\big)\rVert^2$ plus a scale-consistency term
matching the anchor scale $s$ to LiDAR metres. Optionally a **prior-conditioned** variant in the spirit of
MapAnything ([05 §3](05_sota-lineage.md)): feed sparse LiDAR depth as an extra token stream at inference.

**Feasibility (8–24 GB).** High for the adapter route (frozen trunk, teacher precomputed offline on CPU). The
prior-conditioning route is heavier (touches attention inputs) and is a stretch goal.

**Benchmark + metric.** Oxford-Spires dense (has LiDAR) and a KITTI-360 split. Win = ATE/RPE reduction and
**scale-error reduction** (ratio of estimated to true trajectory length approaching 1) vs the camera-only baseline,
especially on the hardest segments. Honest control: verify the camera engine was actually scale-drifting
there before crediting the teacher.

---

## D3 · Retrieval-augmented long-term memory

**Gap addressed:** #2 (lossy 6-token memory).

**Hypothesis.** The 6-token-per-frame compression discards detail needed over tens of thousands of frames. A
**retrieval** mechanism, an external key-value store of richer (but rarely accessed) per-frame features, can
re-inject high-fidelity context on demand when the current frame matches a stored place, recovering detail the
compression lost, at bounded per-frame cost.

**Method.** Maintain an external store: key = the D1 descriptor $d_i$, value = a compact but richer feature
(e.g. a small set of the frame's patch tokens, or a learned code). On each frame, retrieve top-$m$ matches and
attend to their values in an added cross-attention layer (frozen trunk; only the retrieval-attention head is
trained). This is a memory *augmentation*, not a replacement, so it composes with the existing window +
6-token memory.

**Feasibility (8–24 GB).** Medium. The store lives in CPU RAM / on disk (FAISS + memmap); only the retrieved
$m$ values touch the GPU. Care needed so retrieval stays within the per-frame budget (bounded $m$, async
prefetch). Risk: extra latency could break the real-time property, so the metric must include FPS.

**Benchmark + metric.** Oxford-Spires dense and the longest available sequences. Win = ATE/F1 improvement on
**late** frames (where compression hurts most) **at maintained FPS**. Report the accuracy–latency trade curve;
a gain that halves FPS is not a win against the real-time bar.

---

## D4 · Test-time refiner

**Gap addressed:** #3 (no test-time optimization).

**Hypothesis.** A lightweight per-scene refinement stage on top of the feed-forward map, a **pose-graph /
bundle-adjustment polish** and/or a **textured-surface / 3DGS** fit, can improve geometry the single forward
pass leaves rough, without any learning, purely as an optimizer at inference.

**Method.** Two composable layers, both already scaffolded in the lab. (a) **Geometric polish:** a short
bundle adjustment over the emitted poses + a subset of points minimizing reprojection/point-to-plane
residuals (seeded by the feed-forward estimate, so few iterations). (b) **Surface refinement:** the `refine`
stage (`stages/refine.py`) already voxel-downsamples, removes statistical outliers, and estimates normals via
Open3D and flags `mesh_ready`; the natural extensions are a **textured Poisson mesh** (Open3D, CPU) and an
optional **3D Gaussian Splatting** fit (needs `nvcc`, a separate GPU lane). This is what makes the output "not
look like a bare LiDAR map."

**Feasibility (8–24 GB).** Geometric polish + Poisson meshing: high (CPU / modest GPU, already partially
implemented). 3DGS: medium, and gated on `nvcc` availability, so it is an optional lane, not the default.

**Benchmark + metric.** Oxford-Spires dense + ETH3D (reconstruction F1). Win for the geometric polish = ATE
reduction vs the un-refined pass; win for surface refinement = F1 / completeness improvement and a visibly
textured mesh. Cost must be reported (refinement is per-scene, so seconds-to-minutes is acceptable, unlike the
streaming path).

---

## D5 · Uncertainty / multi-hypothesis

**Gap addressed:** robustness and honest failure signaling; supports all of the above.

**Hypothesis.** The depth head already emits a confidence ([03 §6](03_pointmaps-and-geometry.md)); a
principled **uncertainty** model (and, where the scene is ambiguous, a **multi-hypothesis** pose) would let
the system down-weight unreliable geometry in fusion and in the D1 pose graph, and flag frames where the
reconstruction should not be trusted.

**Method.** Calibrate the emitted confidence against actual error (reliability diagram) and use it as the edge
weight $\Sigma$ in D1's pose graph. For ambiguous motion (e.g. featureless corridors, the LiDAR slip case of
[04 §8](04_lidar-odometry.md)), maintain a small set of pose hypotheses and prune by later evidence. Train
only a small calibration/uncertainty head on the frozen state.

**Feasibility (8–24 GB).** High for calibration + uncertainty-weighted fusion (negligible compute).
Multi-hypothesis tracking is a stretch goal (bookkeeping, modest cost).

**Benchmark + metric.** Win = ATE reduction **when uncertainty is used to weight** D1's graph (an ablation:
uniform vs calibrated weights), plus a **calibration** result (predicted uncertainty tracks true error). This
direction is judged partly as an enabler: its value is the ATE it unlocks in D1/D2.

---

## Priority and dependencies

- **D1** is the flagship (directly attacks the headline gap; proven recipe from KISS-SLAM; highest feasibility).
  **D5** feeds D1 (uncertainty-weighted edges).
- **D2** stands alone and exploits the lab's second modality; strong if the camera engine genuinely
  scale-drifts on the target sequences.
- **D4** (geometric polish + the already-scaffolded surface refinement) is the most self-contained "does the
  output look/measure better" win and needs no learning.
- **D3** is the most research-risky (real-time budget) and is sequenced after D1's descriptor exists (it reuses
  it as the retrieval key).

Every direction is validated rigorously, adversarially (refute the hypothesis, negative-control the positives)
before it is believed, and the honest experiment record, including null results, is the product.
