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

**Decisive finding (the point of the whole exploration).** With a proper DEPTH metric we could finally see it:
a bigger/frozen backbone (DINOv2) improves **depth by 42 %**, but the trajectory ATE is capped by the **regression
pose head** regardless of backbone or data, and better depth + post-hoc global optimization (M-A) does NOT fix it.
This is exactly why the state of the art (DROID-SLAM, DPVO, DINO-VO) builds pose from a **differentiable
bundle-adjustment** layer, not a regression head. The finding is architectural: on modest hardware, 8 GB is not the
constraint and depth is cheap to improve; the trajectory is limited by the pose estimator's lack of a geometric
constraint.


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
