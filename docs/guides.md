# Guides

Runnable, internal how-tos for operating the lab: instantiate, bake a case, point it at your own data, run the
GPU lane, run the (dormant) API, ship the architecture modal, add an engine or a case, and bake LiDAR. These
are specific to CAOS_RES_Lidar3D (not the generic template): the examples use the real cases, the real engine
knobs, and the real contracts. Heavy paths are referred to by the env-var names `LIDAR3D_MODELS_ROOT` and
`LIDAR3D_DATA_ROOT`, never machine paths.

| # | Guide | When you need it |
|---|---|---|
| 00 | [Instantiate](guides/00_instantiate.md) | how this repo was created from the template + the rework surface you may touch |
| 01 | [Precompute pipeline](guides/01_precompute-pipeline.md) | bake a case end to end: env setup, the stage flow, the CLI |
| 02 | [Bring your own data (CONTRACT 1)](guides/02_bring-your-own-data.md) | point it at your own RGB sequence or LiDAR scans; what passes / rejects / flags |
| 03 | [GPU lane](guides/03_gpu-lane.md) | the 8 GB-safe config, the exact knobs, the memory/quality trade-off, the SDPA-no-FlashInfer note |
| 04 | [Run the API](guides/04_run-the-api.md) | the dormant `app/` live lane; how it would stream |
| 05 | [Architecture modal (ADR-0058)](guides/05_architecture-modal.md) | what the in-app ⓘ "How it works" modal must show |
| 06 | [Add an engine or a case](guides/06_add-an-engine-or-case.md) | add a new `model/` engine + a case-by-category; the modality dispatch |
| 07 | [LiDAR modality](guides/07_lidar-modality.md) | bake LiDAR: synthetic + real `.bin`/`.npy`/`.ply`; the KISS-ICP swap |
| 08 | [Train and run OUR model](guides/08_train-and-run-the-own-model.md) | the full local workflow: train the depth+pose net, bake, tune the ICP/D1/TSDF refinement ladder, add a scene, verify |

Related theory: the engine internals are in [`docs/theory/`](theory.md); the repo mechanics (contracts,
determinism, gate, deploy) are in [`docs/architecture/`](architecture.md); the engine card is in
[`docs/frameworks/lingbot-map/`](frameworks.md).
