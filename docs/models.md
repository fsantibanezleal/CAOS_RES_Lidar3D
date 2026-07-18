# Models

Our own, trainable, model-agnostic reconstruction stack, built around **Estela** (our depth+pose net), and the
full honest record of every model and every experiment run in this lab. The engine is model-agnostic (a registry
behind one `reconstruct(spec, seed) -> ReconResult` contract, `data-pipeline/lidar3dlab/model/agnostic.py`); this
theme documents the models that plug into it and the history of training them, so no experiment or negative result
is ever lost.

| # | Page | What it establishes |
|---|---|---|
| 01 | [Estela: the own depth+pose model](models/01_own-depth-pose.md) | our from-scratch depth+pose network in full: the two interchangeable backbones (scratch UNet / pretrained ResNet-18), the aleatoric depth head, the Siamese pose head, the se(3) exponential, the losses, the ATE metric |
| 02 | [Model history](models/02_model-history.md) | the complete chronological record of every model/experiment: backbone, data, held-out ATE, points, what was deployed, and every negative result, so the history is preserved |
| 03 | [Experiments log](models/03_experiments-log.md) | the machine-readable `experiments.jsonl` schema (one row per training epoch, never truncated), how to read it, and how the web Experiments page renders it |
| 04 | [Datasets](models/04_datasets.md) | the model data: training datasets (TUM x11, ICL-NUIM, 7-Scenes), formats, the real per-dataset intrinsics, licenses, and the bigger-data roadmap |
| 05 | [Estela-W: windowed pose-graph (M-C)](models/05_windowed-pose-graph.md) | the multi-frame extension: a relative-pose measurement per window edge (consecutive + skip) fused by a differentiable pose-graph solve, the training-path pivot (supervise the measurements directly, solve forward-only at inference), and the fused-vs-chain evaluation |
| 06 | [Track B: RGB + sensor depth](models/06_rgbd-track-b.md) | the two-track model family (RGB-only vs RGB+depth); the `rgbd-sensor` engine (SIFT + PnP on Kinect depth, metric by construction, 0.034-0.098 m validated vs 0.28 m RGB-only), why sensor depth removes the monocular-scale blocker, and the honest limitations |

## Where the models live

- **Code:** `data-pipeline/lidar3dlab/model/nets/own_depthpose.py` (the network), `model/own_engine.py` (inference
  behind the contract), `train/train_depthpose.py` (training + evaluation + the experiments log).
- **Weights:** under `LIDAR3D_MODELS_ROOT/own-depthpose/` (never a machine path). Two files are kept per training:
  a per-backbone archive `own-depthpose-<backbone>.pt` (never clobbered by a different backbone) and the canonical
  `own-depthpose.pt` that the engine loads. This is deliberate: switching backbone never destroys the other's best
  checkpoint.
- **History:** `models/own-depthpose/experiments.jsonl` (auto-appended every epoch) plus
  [Model history](models/02_model-history.md) (the curated narrative including pre-log runs).

## The principle

The lab exists to *explore* reconstruction models from scratch, not to wrap a vendored product. Every model here is
ours to train and change. The one place we reuse external weights is an optional ImageNet backbone (a generic vision
feature extractor, not a reconstruction product); the depth decoder, the confidence head, the pose head, the se(3)
math and the whole training loop remain ours. Both the pure-from-scratch and the pretrained-backbone variants ship
behind the same forward signature so they are directly comparable, and both are kept.
