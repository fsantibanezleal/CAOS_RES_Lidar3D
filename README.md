# CAOS_RES_Lidar3D — streaming 3D reconstruction lab

[![CI](https://img.shields.io/github/actions/workflow/status/fsantibanezleal/CAOS_RES_Lidar3D/ci.yml?branch=main&label=CI)](https://github.com/fsantibanezleal/CAOS_RES_Lidar3D/actions)
[![License](https://img.shields.io/github/license/fsantibanezleal/CAOS_RES_Lidar3D)](LICENSE)
[![Version](https://img.shields.io/github/v/tag/fsantibanezleal/CAOS_RES_Lidar3D?label=version&sort=semver)](https://github.com/fsantibanezleal/CAOS_RES_Lidar3D/tags)
[![Live demo](https://img.shields.io/badge/demo-live-2ea44f)](https://lidar3d.fasl-work.com)

> **Lidar 3D** turns a video stream into a camera trajectory, dense metric depth, and an RGB point cloud,
> feed-forward and in real time, with **no per-scene optimization**. It is built around **lingbot-map**
> (arXiv:2604.14141), the 2026 state of the art for *streaming* feed-forward reconstruction (Apache-2.0),
> instantiated from the CAOS product archetype (ADR-0057).

![Lidar 3D workbench](docs/assets/workbench.png)

Research repo: local-first, heavy models/data on a scratch volume (env-resolved, never in git).
**Status: v0.12.001 (live).** Eight real scenes reconstructed by Estela, our own depth+pose net (0.28 m
held-out ATE) with inference-time ICP refinement, replayed in-browser across four renderers; live
reconstruction runs on a local GPU.

## Three lanes (ADR-0057)

The engine is a ~1B-parameter ViT needing a GPU, so it is not browser-feasible. The lab separates:

| Lane | What | Where |
|---|---|---|
| **Offline / precompute** | the real lingbot-map engine bakes committed artifacts | `data-pipeline/lidar3dlab/stages` (GPU) |
| **Replay (public web)** | the static SPA renders those artifacts | `frontend/` (GitHub Pages, Lane B) |
| **Live (dormant)** | real-time reconstruction of your own footage | `app/` local-GPU API |

## Quickstart

```bash
# 1. Environment (Python 3.12 .venv + the precompute deps; torch + the vendored engine per docs/frameworks/lingbot-map)
scripts/setup.ps1                                   # or: bash scripts/setup.sh
# 2. Bake the synthetic CPU case (no GPU/model needed) — proves the pipeline end-to-end
.venv/Scripts/python.exe -m lidar3dlab.pipeline SYN_orbit
# 3. Bake a real sequence (needs the GPU + the env paths from the vault)
LIDAR3D_MODELS_ROOT=… LIDAR3D_DATA_ROOT=… .venv/Scripts/python.exe -m lidar3dlab.pipeline oxford
# 4. The replay web app
cd frontend && npm install && npm run build && npm run preview
```

There is **no root `run_app.py`**: the pipeline is `python -m lidar3dlab.pipeline <case>`; the live API is
the dormant `app/`. The frontend replays the committed artifacts (`copy-data.mjs` enforces the artifact
contract).

## What works (verified 2026-06-30)

- **Real engine in a compliant staged pipeline**: `preprocess → feature_extraction → train(dormant) →
  infer → refine(color/texture) → evaluate → export`, with the two enforced data contracts (RGB-sequence
  ingestion + the artifact manifest, mirrored by the TS types) and the measured lane gate.
- **Verified bakes**: `SYN_orbit` (synthetic, CPU, CI-safe) and the real sequences `oxford / university /
  loop / courthouse` on an RTX 4070 (8 GB-safe: SDPA, CPU-offload, window=16, bf16). oxford = 193k-pt RGB
  cloud, 3.13 m, lane=precompute. No personal paths are ever committed.
- **Frontend (ADR-0016 + ADR-0058)**: a 6-page shell (App / Introduction / Methodology / Implementation /
  Experiments / Benchmark), header with nav + github/personal/portfolio icons + EN/ES + light/dark + the ⓘ
  architecture modal, footer; the App is a workbench with a **three.js RGB-colored point-cloud viewer** +
  camera-frustum trajectory + per-frame depth + stats. Screenshot-verified, zero JS errors.
- **Tests + CI**: ruff + pytest (the synthetic case is the CI smoke) + the CONTRACT-2 drift guard + the
  base-integrity guards (no `.env`, no venv/binaries, no leaked machine paths).

## Layout (instantiated from `template_repo_product`, ADR-0057)

```
data-pipeline/lidar3dlab/   engine + staged pipeline: io/{schema,contract,formats} · core/{gate,manifest,
                            trace,rng} · model/{geometry,synthetic,lingbot} · stages/* · cases · pipeline.py
frontend/                   the replay SPA (React 19 + Vite + three.js + KaTeX)
app/                        dormant FastAPI live lane
data/derived + manifests/   committed compact artifacts (CONTRACT 2)
docs/                       architecture · frameworks/lingbot-map · cases · guides · research (surveys)
tests/ · .github/workflows/ pytest + ruff + pipeline smoke + guards
third_party/lingbot-map/    the vendored engine (Apache-2.0)
```

## Roadmap (the novel agenda)

Beyond using SOTA, the lab pursues lingbot-map's three stated gaps: **loop closure** (pose-graph over the
trajectory memory), **camera↔LiDAR fusion**, and **test-time refinement** (textured mesh / 3DGS). Each is
evaluated rigorously, null results kept. See `docs/research/` for the published surveys and findings.

## Credits / license

Built around **lingbot-map** (arXiv:2604.14141, Apache-2.0), vendored under `third_party/`. This repository
is licensed under **Apache-2.0** (see `LICENSE`). The vendored engine and any model weights keep their own
licenses, tracked per-engine (some are non-commercial, flagged before any product use).
