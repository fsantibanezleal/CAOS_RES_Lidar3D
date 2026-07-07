# Model history

The complete, honest chronological record of every model and every experiment run in this lab, including negative
results and superseded checkpoints. The purpose is that no experiment is ever lost: what was tried, what it scored,
what was deployed, and why. Held-out ATE is RMS trajectory error in metres on the TUM `freiburg3_long_office_
household` sequence (~300 pairs), aligned with Umeyama; lower is better. The machine-readable per-epoch log lives in
`models/own-depthpose/experiments.jsonl` (see [Experiments log](03_experiments-log.md)).

## Timeline

| # | Run | Backbone | Data | Held-out ATE | Deployed? | Notes |
|---|---|---|---|---|---|---|
| M1 | first own model (v0.06.000) | scratch (2.2 M) | TUM RGB-D, 5 seq (~9.9k frames) | **~0.20 m** | yes (superseded) | first honest from-scratch depth+pose; baked the OUR desk case |
| M2 | long run, no early-stop | scratch | TUM RGB-D | **0.49 m** | no | *overfit*: a long run degraded ATE, this was the "diffuse" look; motivated best-checkpoint early stopping |
| M3 | photometric run | scratch + photo loss | TUM RGB-D | (crashed) | no | self-supervised photometric loss with predicted pose; crashed without saving |
| M4 | early-stopping retrain (v0.09.004) | scratch | TUM RGB-D | **0.29 m** | **yes (LIVE)** | added best-checkpoint early stopping; re-baked the OUR case (coherent per-frame depth, more structure). **This baked artifact is what the site currently serves.** |
| M5 | extra-losses experiment (v0.10.x) | scratch + photo + smooth + cosine LR + higher LR | TUM RGB-D | **0.29 → 0.56 m** | no | HONEST negative result: the extra losses + high LR destabilised pose and *hurt* ATE; reverted to simple supervised |
| M6 | simple retrain + conf 0.6 | scratch (base 32) | TUM RGB-D | **0.4344 m** | no (reverted) | run-to-run instability landed worse than M4; re-baked OUR case with `conf_quantile=0.6` (54,665 pts, down from 128k), but 0.43 m pose was still diffuse, so the re-bake was reverted to keep M4 (0.29 m) live. Note: this run overwrote the M4 *checkpoint*; M4's *baked artifact* is preserved in git |
| M7 | **pretrained backbone + ICP** (v0.11.000) | **resnet18** (12.8 M) | TUM RGB-D **+ ICL-NUIM** (perfect GT depth), 7329 pairs | **0.37 m** (best over 10 epochs; epoch 4) | yes (superseded by M8) | ImageNet ResNet-18 shared by depth decoder + Siamese pose head; pose loss ~0.0015 (much steadier than scratch). Inference adds real per-dataset intrinsics + far-depth clamp + frame-to-frame point-to-plane **ICP** pose refinement (Open3D, model pose init) to remove accumulated drift. First OWN deployment across **8 OWN scenes at 240 frames** (TUM x5 + 7-Scenes x2 + ICL); parallel visual review verified all recognizable. Per-frame depth is excellent; the fused cloud is an honest feed-forward result. |
| M8 | **best recovery run** (v0.12.001) | **resnet18** (12.8 M) | TUM RGB-D (winning 4-seq subset) + ICL-NUIM, ~11k pairs | **0.28 m** (best over 12 epochs; epoch 9) | **yes (LIVE)** | Same ResNet-18 + Siamese architecture, retrained after R4 (correlation head) and R5 (11-seq) both failed to beat the ceiling and after a checkpoint-clobber incident lost the 0.37 m weights. The winning 4-seq subset (`--seqs`) + 12 epochs landed **0.28 m** held-out ATE, the best OWN model to date. Re-baked across all 8 OWN scenes (ICP ladder). Unique timestamped archive so it can never be lost. |

## Refinement + pose-head experiments (v0.12.x)

| # | Run | Change | Result | Kept? |
|---|---|---|---|---|
| R1 | ICP refinement | frame-to-frame point-to-plane ICP on the model poses | tighter local trajectory, recognizable clouds | **yes (default)** |
| R2 | D1 global pose-graph + loop closure | Open3D multiway odometry + loop-closure edges + global optimization | over-constrains single-area indoor sweeps at ~0.37 m pose accuracy (241 loop edges on desk); tight trajectory but not cleaner cloud | implemented, **opt-in** |
| R3 | TSDF volumetric fusion | KinectFusion-style denoised surface | fuses SPARSELY at ~0.37 m pose accuracy (frames disagree, desk fell to 4.6k pts); needs sub-voxel poses | implemented, **opt-in** |
| R4 | **Correlation pose head** | RAFT/TartanVO-style local cost volume replacing the Siamese pooled-feature head | **NEGATIVE**: per-pair pose loss dropped (0.0008) but held-out ATE got WORSE (0.63 -> 0.80 m over epochs) — good local pose, worse accumulation. Not deployed | archived, not default |
| R5 | more data (TUM 5 -> 11 seq) | retrain the Siamese head on ~16k pairs (was ~7k) + ICL | **did NOT help**: plateaued at 0.68 m (the extra harder sequences hurt the specific long_office eval); confirms the architectural ceiling | no |
| R6 | **best recovery run** | retrain the Siamese head on the winning 4-seq TUM subset + ICL (11k pairs), 12 epochs | **0.28 m** held-out ATE (beats the old 0.37 m); the best OWN model to date | **yes (LIVE, M8)** |
| R7 | **frozen DINOv2 ViT-B backbone** (DepthAnything recipe: DINOv2 + DPT decoder) | 89.6 M total / **only 3.0 M trainable / 0.65 GB VRAM** (proves 8 GB is NOT the constraint) | pose ATE 0.61 m (worse, head-limited) but **depth-AbsRel 0.22 vs the ResNet's 0.38 = 42 % better DEPTH** (measured with the new metric) | archived; depth-superior |
| R8 | **M-A: DINOv2 depth + D1 global pose-graph** | bake with the better depth + the global pose-graph, no new training | did NOT give a clean surface: the 0.61 m raw-pose init is too poor for the global BA, which over-constrained (359 loop edges, path blew up to 7 m) | no |
| R9 | **M-B: single-pair differentiable geometric pose** | a metric-depth-seeded geometric pose head (soft 3D correspondences -> weighted Procrustes/SVD, `pose_head=geo`); frozen depth, only 0.08 M trainable | **NEGATIVE**: the per-pair pose loss dropped to 0.009 (good LOCAL pose) but the accumulated ATE was **1.21 m** (far worse than the regression 0.28 m). Single-pair geometry accumulates coherent per-pair bias | archived, not deployed |
| R10 | **grow the backbone: DINOv2 ViT-L @448** (308 M total, frozen backbone + DPT decoder; batch 4, 6 epochs, TUM+ICL) | test whether a *bigger* backbone than ViT-B improves depth further (#23) | **NEGATIVE / overfits**: best **depth-AbsRel 0.2665 at epoch 0**, then it DEGRADED every epoch (0.28 by ep5) while the train NLL kept dropping (-0.71) = classic overfitting on the limited data. Better than ResNet (0.38) but **worse than ViT-B (0.22)**. Finding: on this data size, ViT-B is the depth sweet spot; a bigger backbone overfits, it is not a free win. Best ATE 0.73 m (head-limited pose, as expected). Also surfaced + fixed the `num_workers=0` DataLoader (GPU was 4% util; now 94%, 2.7x faster). | archived, not deployed |
| R11 | **ViT-L @448 again, lower LR** (1e-4, 3x lower, vs R10's overfit) | does a lower LR stop the overfitting so ViT-L can beat ViT-B? | **NEGATIVE (confirms R10)**: best **depth-AbsRel 0.2614 at epoch 0** (marginally better than R10's 0.2665), then the SAME overfit pattern (ep1 0.297, ep2 0.279) while train NLL kept dropping. Two LRs now confirm ViT-L overfits the 16 320 pairs regardless; **ViT-B (0.22) is the depth sweet spot for this data size**. Killed at epoch 3 (result clear). | archived, not deployed |

**Decisive finding (the point of the whole exploration).** With a proper DEPTH metric we could finally see it:
a bigger/frozen backbone (DINOv2) improves **depth by 42 %**, but the trajectory ATE is **capped by the per-pair
accumulation**, not the backbone, the data, or even the pose-head family: regression 0.28 m, correlation 0.63 m,
DINOv2 0.61 m, single-pair geometry (M-B) 1.21 m. Every per-pair estimator, however good locally (M-B's per-pair loss
hit 0.009), drifts because small per-pair errors accumulate coherently over the trajectory. This is exactly why the
state of the art (DROID-SLAM, DPVO, DINO-VO) does **multi-frame bundle adjustment** (jointly optimizing a window of
poses for global consistency), not single-pair estimation. On modest hardware 8 GB is not the constraint and depth is
cheap; the trajectory needs **joint multi-frame optimization**. The building blocks are in place (a validated
differentiable Procrustes/BA core, metric-depth seeding, the inference-time ICP + global pose-graph); the next step is
**M-C: a windowed multi-frame differentiable BA** (DPVO-lite). Note: the deployed regression + inference-ICP model
(M8, 0.28 m) remains the practical best for the per-pair approach.

**M-C core implemented + validated (#22).** `model/nets/window_ba.py` is the differentiable
**windowed pose-graph optimiser**: given per-edge relative-pose measurements over a window (consecutive AND
non-consecutive skip edges) with confidences, it solves for the absolute poses jointly by a few Gauss-Newton
iterations (autograd Jacobian, differentiable linear solve, se(3) tangent updates). Synthetic self-test (6-frame
window, ~2 deg / 3 cm per-edge noise): chained single-pair drift **0.0775 m** vs windowed PGO **0.0304 m = 61 %
less drift**, and gradients flow back to the measurements (the geo head can be trained THROUGH the optimiser).
This is the mechanism the decisive finding pointed to, proven in isolation.

**M-C trained + evaluated (#22, the definitive run) = Estela-W.** Built the training path:
`WindowDepthPose.measure_edges` (depth + a per-edge geometric measurement), `TartanGroundWindows` / `TUMWindows`
(N-frame windows), and `train/train_window.py`. The training-path pivot: back-propagating through `window_pgo`
(a second-order differentiable solve) went NaN with an untrained head, so the trainer supervises the per-edge
measurements DIRECTLY (first-order, stable) and runs `window_pgo` forward-only at inference. Also fixed a real bug
in the core (`window_edges` emitted `(i, distance)` instead of the frame pair `(i, i+j)`; latent because the tests
built edges by hand). Trained on TartanGround + TUM windows (warm-started from the M8 depth net), evaluated on the
held-out TUM `long_office`:
- **The fusion works**: `window_pgo` cuts per-window drift **45 %** vs chaining the SAME measurements (0.254 m vs
  0.464 m; 18 % on TartanGround) and halves the full-trajectory ATE (3.16 m vs 6.01 m); per-edge error fell to
  ~0.20 m with no NaN.
- **But it does NOT beat M8**: absolute ATE 3.16 m is an order of magnitude above the deployed per-pair M8
  (0.28 m), because it fuses the *geometric* front-end (M-B, ~1.2 m-class per pair), not the Siamese + ICP head.
  The windowed BA is validated as a drift reducer, but the front-end is the ceiling; the next step is to fuse the
  Siamese / ICP-refined edges. `window-mc.pt` is kept separate (own-depthpose.pt = M8 stays LIVE). Full write-up:
  [Estela-W](05_windowed-pose-graph.md).

**Refinement-mode ATE benchmark (2026-07-04, `train/eval_refine_modes.py`).** A direct, honest test of the
inference refinement ladder on the held-out `long_office`: run M8's per-frame depth + relative pose once, then
re-run `_refine_trajectory` under each mode and measure umeyama ATE. The **raw model pose chain reproduces exactly
0.28 m** (0.2815 m), which validates the benchmark, and it is the **BEST** mode: on consecutive frames ICP 0.65 m,
windowed BA 0.63 m, global PGO 0.73 m; at the bake's stride-2 raw 0.91 m, ICP 1.21 m, window 1.10 m, global
1.15 m. So every geometric refinement, initialised by the already-good learned poses, DRIFTS on the noisy monocular
depth and WORSENS the trajectory. The windowed BA consistently beats plain ICP (by 9 to 31 %) but never beats raw.
Two conclusions: (1) geometric post-processing cannot break the ceiling, the ceiling IS the learned front-end, so
effort goes to a stronger learned front-end (better pose/depth/matching) or the pointmap paradigm, not more BA;
(2) the shipped ICP-for-bake improves LOCAL cloud consistency but worsens GLOBAL ATE, a real tradeoff, so flipping
the bake default to raw is a cloud-quality-vs-ATE judgment that needs a visual check, not an automatic flip.

**Pointmap-paradigm probe (2026-07-06, re-scored on corrected poses): lingbot matches Estela in SHAPE up to
scale; the gap is METRIC SCALE.** To test whether a pointmap model (which predicts geometry + pose jointly and
sidesteps the per-pair ceiling) wins on our indoor scenes, we ran the vendored `lingbot` engine (VGGT-style
GCTStream, ~7 GB, 4.6 GB checkpoint) on 3 TUM scenes (matched first 150 frames) and measured trajectory ATE.

- **Rigid-only Umeyama is unfair to a monocular method:** lingbot is up-to-scale (recovered scale 2.7x to 8.8x;
  its cloud reads ~1.5 m for a ~5 m room), so rigid alignment destroys a shape-correct wrong-scale trajectory.
  The standard monocular protocol is Sim(3) (scale + rigid). (Note: these numbers were first measured on the #77
  backwards-pose bug; re-scored here on the corrected c2w poses. Sim(3) is scale/rotation invariant, so the
  figures barely moved, but the raw camera trajectory is now the real one.)
- **Sim(3) ATE, corrected poses (vs Estela raw metric ATE, same frames):**

  | scene | lingbot Sim(3) | Estela raw (metric) |
  |---|---|---|
  | long_office | **0.104 m** | 0.131 m |
  | freiburg1_desk | 0.157 m | 0.136 m |
  | freiburg2_pioneer | **0.082 m** | 0.031 m |

  So the general-purpose lingbot, NOT fine-tuned on TUM, matches or beats our TUM-trained model's trajectory
  SHAPE on 2 of 3 scenes out of the box, with drift-free streaming over its fixed three-tier memory. What it
  lacks is absolute METRIC scale, the same blocker as the DA-V2 geometric-pose path (the P1 scale finding).
- The cloud remains diffuse at the per-point level vs Estela's conf-filtered cloud, and per-scene metric scale is
  still required for a deployable bake (our product renders metric scenes), so the practical conclusions stand:
  Estela stays deployed, and SCALE is the single blocker across every path.

Honest conclusion: the 0.28 m per-pair ceiling is not broken by geometric post-processing; the pointmap engine
already matches Estela in shape and would beat it with a metric-scale anchor. Everything converges on ONE
problem, per-scene monocular metric scale, and the scale-learnability diagnostic (below) shows that problem has
no RGB-only solution.

**Scale-learnability diagnostic (2026-07-06): the RGB-only metric scale has no learnable signal.** Before
building a learned scale head for Track A, we measured whether the metric-scale error is even learnable: per
frame, the true correction is `s = median(GT_depth) / median(DA-V2_depth)` over co-valid pixels. Result: the
correct scale is a well-defined per-SCENE constant (desk 0.68, office 1.00, pioneer 0.59) with only 9-14%
within-scene drift, but those per-scene constants are NOT predictable from a single RGB frame, and monocular
vision provably cannot observe absolute scale. So a pure-RGB scale head has no reliable input; it would need a
metric anchor. **Conclusion (retires the learned-scale-head idea): the ~0.02-0.03 m oracle ceiling is reachable
ONLY with a metric anchor, i.e. a depth sensor (Track B, shipped) or an external cue (camera height / IMU /
reference object). Track A stays honestly up-to-scale.** `wip/lidar3d/exp_scale_learnability.py` in the mgmt repo.

**Anchor-hybrid (lingbot shape + a metric anchor): NEGATIVE, scene-dependent.** One more Track A attempt: scale
lingbot's up-to-scale trajectory by a metric anchor derived from Estela's own chain (aggregate path length, and
the median per-pair step ratio), then measure rigid metric ATE. On corrected poses:

| scene | Estela raw | lingbot Sim(3) bound | + path-length anchor | + median-step anchor |
|---|---|---|---|---|
| long_office | 0.131 | 0.104 | 0.181 | **0.106** |
| freiburg1_desk | 0.136 | 0.157 | 0.199 | 0.188 |
| freiburg2_pioneer | 0.031 | 0.082 | 0.118 | 0.127 |

The median-step anchor reaches the shape bound on `long_office` (0.106 m, ~19% better than Estela there), but is
WORSE than Estela on desk and pioneer. It is not robust, so it is not productized: the anchor is only as good as
the Estela chain it borrows from, and that varies per scene. Documented as a negative; Track B (a real sensor)
remains the only reliable metric path.


**Checkpoint-loss lesson (repeated).** Running two Siamese runs with the same backbone tag overwrote the 0.37 m
checkpoint with a killed-early run's worse checkpoint (0.77 m). The *deployed* artifacts (v0.11.000) are safe (baked +
committed), but the 0.37 m weights were lost. Fixed for good: every run now writes a **unique timestamped archive**
(`own-depthpose-<variant>-<runid>.pt`), so no run can ever clobber another's best again.

**The honest conclusion (v0.12.x).** A clean fused surface is bounded by pose accuracy, not by post-processing. ICP,
D1 and TSDF are all implemented; D1/TSDF become the default once the pose model crosses sub-voxel accuracy. The
correlation pose head did not help. The remaining lever being pursued is more/broader training data on the proven
Siamese head, then (future) a pose head that regresses to the *accumulated* trajectory, not just per-pair.

## Reading the appearance vs the number

The "diffuse cloud" complaint is dominated by **pose drift**, not depth noise: the per-frame depth of the from-
scratch model is already coherent, but accumulated pose error spreads the frames apart. This is why:

- best-checkpoint early stopping helped (M2 → M4): it stops before pose overfits;
- the extra losses hurt (M5): they destabilised pose;
- the pretrained backbone (M7) is the chosen lever: a stronger encoder gives sharper depth *and*, via the Siamese
  pose head, a much lower pose loss, attacking the drift directly.

The OUR case reconstructs a short (~60-frame) desk sweep, so its accumulated drift is far below the ~300-frame
held-out ATE; the visible reconstruction can be tighter than the ATE alone implies.

## Checkpoint retention policy

Since M6 accidentally overwrote M4's checkpoint, training now writes **two** files per run: a per-backbone archive
`own-depthpose-<backbone>.pt` (never clobbered by a different backbone) plus the canonical `own-depthpose.pt` the
engine loads. A different backbone can never destroy another's best checkpoint again. Baked artifacts (the served
point clouds and Potree octrees) are committed to git, so even a lost checkpoint leaves the deployed reconstruction
recoverable from history.

## What "deployed" means here

Deploy is gated on *verified improvement*: a new model is baked into the OUR case and screenshot-compared against the
live version. It replaces the live artifact only if it is genuinely sharper/tighter. M6 failed this gate and was
reverted; M4 remains live until M7 (or a later run) verifiably beats it.
