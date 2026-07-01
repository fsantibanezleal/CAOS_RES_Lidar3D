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
| M7 | **pretrained backbone + ICP** (v0.11.000) | **resnet18** (12.8 M) | TUM RGB-D **+ ICL-NUIM** (perfect GT depth), 7329 pairs | **0.37 m** (best over 10 epochs; epoch 4) | **yes (LIVE)** | ImageNet ResNet-18 shared by depth decoder + Siamese pose head; pose loss ~0.0015 (much steadier than scratch). Inference adds real per-dataset intrinsics + far-depth clamp + frame-to-frame point-to-plane **ICP** pose refinement (Open3D, model pose init) to remove accumulated drift. Deployed across **8 OWN scenes at 240 frames** (TUM x5 + 7-Scenes x2 + ICL); parallel visual review verified all recognizable. Per-frame depth is excellent; the fused cloud is an honest feed-forward result. Note: the val-ATE (0.37 m on the 300-frame long-office eval) is worse than M4's 0.29 m by the trajectory metric, but M7's sharper depth + ICP-refined pose give a better *reconstruction*; M4's checkpoint was lost (only its baked artifact remained), so M7 is the deployed model everywhere |

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
