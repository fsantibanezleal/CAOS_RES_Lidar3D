# 01 · Streaming 3D reconstruction, formalized

This page states precisely the problem the lab solves, why it is hard, and what "solving it feed-forward"
means. It is the foundation for [02 (the transformer)](02_geometric-context-transformer.md) and
[03 (the geometry)](03_pointmaps-and-geometry.md).

---

## 1. The problem

A monocular RGB camera moves through a static (or mostly static) scene and emits frames one at a time:

$$
I_1, I_2, \dots, I_t, \dots \qquad I_t \in \mathbb{R}^{H \times W \times 3}.
$$

At each time $t$, immediately after $I_t$ arrives and using only the frames seen so far
$\{I_1, \dots, I_t\}$, the system must output:

- a camera pose $\hat P_t \in SE(3)$, expressed **camera-to-world** (the transform that maps a point in
  the camera frame of view $t$ into a single shared world frame),
- a dense **metric** depth map $\hat D_t \in \mathbb{R}_{>0}^{H \times W}$,
- a per-pixel confidence / uncertainty map $\hat C_t \in \mathbb{R}^{H \times W}$,
- and, by reprojection (see [03](03_pointmaps-and-geometry.md)), a colored world-frame point cloud
  $\hat X_t \subset \mathbb{R}^3$.

The union $\bigcup_{\tau \le t} \hat X_\tau$ is the reconstructed map; the sequence
$\{\hat P_\tau\}_{\tau \le t}$ is the estimated trajectory. This is exactly the output of a **SLAM** system
(Simultaneous Localization And Mapping), but produced by a single forward pass of a neural network rather
than by an optimization loop.

Formally the engine is a causal map

$$
f_\theta:\ (I_1, \dots, I_t) \ \longmapsto\ (\hat P_t,\ \hat D_t,\ \hat C_t),
$$

with a bounded internal **state** $\mathcal{S}_t$ that summarizes the past, so that in practice

$$
(\hat P_t,\ \hat D_t,\ \hat C_t,\ \mathcal{S}_t) = g_\theta(I_t,\ \mathcal{S}_{t-1}).
$$

The whole research problem is the design of $\mathcal{S}_t$: rich enough to keep the map globally consistent
over tens of thousands of frames, small enough to update in real time. [02](02_geometric-context-transformer.md)
is the answer lingbot-map gives.

## 2. Causality

**Causal** means $\hat P_t$ may depend on $I_1, \dots, I_t$ but **not** on any $I_{t'}$ with $t' > t$. This
is the defining constraint that separates *streaming / online* reconstruction from *offline / global*
reconstruction:

- **Offline** methods (DUSt3R, VGGT, pi3, MapAnything, see [05](05_sota-lineage.md)) see the whole clip at
  once. They can attend bidirectionally, run a global bundle adjustment or a global alignment, and are not
  bound by a per-frame latency budget. They cannot run on a live camera.
- **Streaming** methods (CUT3R, StreamVGGT, lingbot-map) must commit to $\hat P_t$ before $I_{t+1}$ exists.
  A wrong early pose can only be *corrected later* through whatever memory the state carries; it cannot be
  retro-actively re-optimized in the core path.

Causality is enforced architecturally in the engine by an attention mask (each frame attends only to past
frames and itself) and by a **KV cache** that stores past keys/values and never the future
(`third_party/lingbot-map/lingbot_map/layers/attention.py`, `CausalAttention.forward`). The mask
construction is analyzed in [02 §5](02_geometric-context-transformer.md#5-the-attention-mask).

## 3. The three-way tension

A streaming reconstructor is pulled in three directions at once. Any two are easy; all three simultaneously
is the frontier.

### 3.1 Geometric accuracy

Low error on the trajectory and the map. The standard trajectory metric is the **Absolute Trajectory Error**
(ATE): align the estimated trajectory $\{\hat t_\tau\}$ to ground truth $\{t_\tau^\star\}$ by the best rigid
(or $Sim(3)$, when scale is free) transform $g$, then

$$
\mathrm{ATE} = \sqrt{\frac{1}{T} \sum_{\tau=1}^{T} \big\lVert g(\hat t_\tau) - t_\tau^\star \big\rVert_2^2 }.
$$

Relative Pose Error (RPE) measures local drift over a fixed horizon $\Delta$:

$$
\mathrm{RPE}_\Delta = \Big\lVert (\hat P_\tau^{-1}\hat P_{\tau+\Delta}) \ominus (P_\tau^{\star-1}P_{\tau+\Delta}^\star)\Big\rVert,
$$

split into a translational and a rotational component (rotation reported in degrees). Map quality is scored by
precision/recall F-score against a reference cloud (as in lingbot-map's reported **ETH3D F1 = 98.98**).

### 3.2 Temporal consistency

Successive outputs must agree: $\hat P_t$ and $\hat P_{t+1}$ should compose smoothly, and a point seen in
two frames should land at (nearly) the same world coordinate both times. An accurate-but-jittery estimator is
useless for a map because re-observed geometry does not fuse. Temporal consistency is what the
**trajectory memory** (a compact record of every past frame) and **Video-RoPE ordering** buy
(see [02 §4](02_geometric-context-transformer.md#4-the-three-contexts)).

The hardest sub-problem is **drift**: small per-frame pose errors $\epsilon_\tau$ accumulate. In a pure
scan-to-scan chain (as in the LiDAR engine, [04](04_lidar-odometry.md)) the world pose is a running product

$$
\hat P_t = \prod_{\tau=1}^{t} \Delta \hat P_\tau, \qquad \Delta \hat P_\tau \approx P_\tau^{\star} \, (P_{\tau-1}^{\star})^{-1} \cdot \exp(\epsilon_\tau),
$$

so errors compound and the estimate wanders from truth even when each *relative* step is good. The
engineering options against drift are (a) attend to more of the past (memory), (b) recognize a revisited
place and close the loop, (c) re-optimize at test time. lingbot-map does (a) and explicitly does **not** do
(b) or (c); those absences are the lab's research openings (see [06](06_novel-agenda.md)).

### 3.3 Compute

Real time means a per-frame budget. lingbot-map targets **~20 FPS at 518×378** and must hold that rate over
**10,000+ frames** (`docs/research/lingbot-map-deep-dive.md`). The naive obstacle is that global attention
over the full history costs $O(T^2)$ in tokens: as $T$ grows the per-frame cost grows without bound. A
streaming engine must make the per-frame cost (nearly) **constant in $T$**. The quantitative argument, and
how the three-context design achieves it, is [02 §6](02_geometric-context-transformer.md#6-complexity-the-token-count-argument).

### 3.4 Why the three conflict

- More accuracy usually wants more context (attend to more frames at full resolution): costs compute.
- More temporal consistency wants long memory: costs compute and, if compressed, costs accuracy.
- More compute headroom wants shorter context and coarser memory: costs accuracy and consistency.

The GCT is a specific, learned trade point: a short **full-resolution** window for local accuracy, a
**heavily compressed** long memory for consistency, and a paged cache so the update stays constant-time.

## 4. Feed-forward vs optimization

Classic SLAM (ORB-SLAM, DROID-SLAM) and structure-from-motion (COLMAP) solve, at inference, a non-linear
least-squares problem, minimizing reprojection or photometric residuals by bundle adjustment. That is an
**optimization at test time**: iterative, scene-specific, no learned prior beyond hand-designed features.

Feed-forward reconstruction (the DUSt3R-to-lingbot-map lineage, [05](05_sota-lineage.md)) instead **regresses**
geometry directly:

$$
(\hat P_t,\hat D_t) = f_\theta(\cdot), \qquad \theta \text{ fixed after training.}
$$

No per-scene optimization runs at inference. The prior lives entirely in $\theta$, learned once over large
multi-view datasets (lingbot-map: two stages, ~37k GPU-hours, 29 datasets;
`docs/research/lingbot-map-deep-dive.md`). Consequences that shape this lab:

- **Speed / demo-ability.** One forward pass per frame; no solver to converge. This is why a browser
  workbench that *replays* the result is coherent, and why the (dormant) live lane is even conceivable.
- **A frozen prior is a fixed asset.** Because $\theta$ is fixed and the intermediate **geometric-context
  state** is a well-defined tensor, the lab can bolt *new* heads onto that state without retraining the
  backbone. This is the mechanism behind the entire novel agenda ([06](06_novel-agenda.md)): loop closure,
  cross-modal distillation, retrieval memory, and a test-time refiner are all **frozen-backbone add-ons**.
- **The failure modes move.** Optimization SLAM fails by non-convergence or bad initialization; feed-forward
  fails by distribution shift and by *lacking* the mechanisms (loop closure, test-time refinement) that
  optimization SLAM has. The honest research question, therefore, is whether a *learned* module on the frozen
  state can recover those mechanisms cheaply.

## 5. What the lab instantiates

The lab wraps the real engine in a deterministic staged pipeline and a replay web app (ADR-0057). The
pipeline turns a validated frame sequence (a `SequenceSpec`,
`data-pipeline/lidar3dlab/io/schema.py`) into a committed artifact:

`preprocess, feature_extraction, train(dormant), infer, refine, evaluate, export`.

`infer` dispatches by modality/synthetic flag (`data-pipeline/lidar3dlab/stages/infer.py`) to one of three
engines that all emit the same `ReconResult` (poses + dense depth + fused colored cloud + trajectory), so the
contracts, gate, export and web replay are identical across:

- the **lingbot-map** camera engine (real, GPU) for `oxford / university / loop / courthouse`,
- a **synthetic corridor** CPU engine (`SYN_orbit`) that exercises the exact same
  depth-then-unproject-then-fuse path with no GPU (CI-safe),
- the **LiDAR ICP** engine ([04](04_lidar-odometry.md)) for `LID_synthetic` / `kitti_lidar`.

The rest of the theory section explains each of these engines in depth.
