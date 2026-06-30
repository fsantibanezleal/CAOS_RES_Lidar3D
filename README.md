# CAOS_RES_Lidar3D — streaming 3D reconstruction lab

> **Lidar 3D** is a research lab + interactive web workbench at the frontier of **feed-forward 3D scene
> reconstruction**: it turns a video (or, later, a LiDAR) stream into a **camera trajectory + dense
> metric depth + a live point cloud**, in real time, with **no per-scene optimization**. The hero engine
> is **lingbot-map** (arXiv:2604.14141), the 2026 state of the art for *streaming* feed-forward
> reconstruction, run live on the local GPU and streamed to the browser.

Research repo (ADR-0050): local-first, deploy class `none`, heavy models/data on `E:` (never in git).
Status **v0.01.000** — the real streaming core is built and screenshot-verified; the full 6-page
workbench is in progress (see [Roadmap](#roadmap)).

![workbench](docs/assets/workbench.png)

## What works today (verified 2026-06-29)

- **Real engine, real data, live.** The vendored `lingbot-map` model runs frame-by-frame on the local
  **RTX 4070 (8 GB)** and streams each frame's geometry over a WebSocket to a three.js viewer. Validated
  on the real `oxford` sequence: 28 frames → **249k-point cloud**, **3.21 m** camera path, 7.1 GB VRAM,
  ~1–3 FPS. Not a baked replay — each frame is computed on demand.
- **Interactive workbench:** source selector (4 real sequences), live point cloud + camera-frustum
  trajectory + live depth map + live stats, orbit controls, point-size / decimation / confidence /
  frame-count controls, light·dark, EN·ES, and an in-app architecture modal (ADR-0058).

## Why this lab (the SOTA, in brief)

Feed-forward "pointmap" models (DUSt3R → MASt3R → **VGGT** (CVPR'25 best paper) → π³ → MapAnything →
**lingbot-map**) have replaced classic SfM/MVS/bundle-adjustment with a single transformer forward pass.
**lingbot-map** is the apex of the *streaming* branch (a Geometric Context Transformer with a paged KV
cache, ~20 FPS over 10k+ frames, Apache-2.0). The lab uses it for real and pursues its **stated gaps**
as a novel agenda: **loop closure**, **LiDAR fusion**, **test-time refinement**. Full survey + decisions:
the dossier in `_CAOS_MANAGE/wip/lidar3d/` and [`docs/research/`](docs/research/).

## Quickstart (needs the local NVIDIA GPU)

```bash
# 1. Models (~14 GB, Apache-2.0) -> E:\_Models\3D_Spatial_Reconstruction\lingbot-map\
hf download robbyant/lingbot-map --local-dir E:/_Models/3D_Spatial_Reconstruction/lingbot-map
# 2. Demo data (301 MB) -> E:\_Datos\3D_Spatial_Reconstruction\lingbot-map-examples\  (the 4 sequences)
# 3. Environment (Python 3.12 .venv + torch cu126 + vendored lingbot-map)
scripts/setup.ps1            # Windows   (or: bash scripts/setup.sh)
# 4. Run
.venv/Scripts/python.exe run_app.py     # -> http://127.0.0.1:8120
```

Smoke tests: `python scripts/validate_lingbot.py …` (offline recon + PLY), `python scripts/test_engine.py`
(engine generator), `python scripts/test_ws.py` (end-to-end WebSocket).

## Engine roster

| Engine | Role | License | State |
|---|---|---|---|
| **lingbot-map** | live streaming video → metric 3D (hero) | Apache-2.0 | **wired** |
| KISS-ICP | real LiDAR odometry | MIT | planned (phase 3) |
| VGGT (Commercial) | offline multi-image "instant scene" | commercial-clean | planned (phase 2) |
| MoGe-2 | single-image preview / low-VRAM | MIT (code) | planned (phase 2) |
| gsplat | optional 3DGS refinement | Apache-2.0 | planned (phase 3) |

## Layout

```
app/            FastAPI backend: config, geometry, server, engines/ (base + lingbot + registry)
web/            three.js viewer + SimLab-style shell (index.html, css/, js/)
scripts/        setup/dev (.ps1+.sh), validate_lingbot.py, test_engine.py, test_ws.py
third_party/    vendored lingbot-map source (Apache-2.0, code only)
docs/           research/ (paper library + reports), wiki (in progress)
data/           manifest -> E: (heavy data never in git)
```

## Roadmap

- **Phase 1 (done):** real streaming `LingbotEngine` + WebSocket + three.js App, screenshot-verified.
- **Phase 2:** full 6-page SimLab shell (Introduction / Methodology / Implementation / Experiments /
  Benchmark) authored from the research; VGGT + MoGe-2 engines; upload + synthetic sources; export.
- **Phase 3 (novel agenda):** loop closure / pose-graph; KISS-ICP LiDAR fusion; gsplat refinement.
- **Phase 4:** offline Benchmark runs + reproduced SOTA tables; complete `docs/` wiki (ADR-0056).

## Credits / licenses

Built around **lingbot-map** ("Geometric Context Transformer for Streaming 3D Reconstruction",
arXiv:2604.14141, Apache-2.0), vendored under `third_party/lingbot-map/` (see its `LICENSE.txt`). This
repo is private research; engine licenses are tracked per-engine above (some weights are non-commercial,
flagged for any future product use).
