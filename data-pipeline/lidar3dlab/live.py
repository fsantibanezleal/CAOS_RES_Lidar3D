"""LIVE lane — NOT browser-feasible for this product (dormant per ADR-0057).

lingbot-map is a ~1B-parameter ViT needing a CUDA GPU + a 4.6 GB checkpoint, so there is NO Pyodide/WASM
browser-live engine here (unlike the lighter SimLab/PINN-Lab labs; even the synthetic engine pulls
matplotlib, which is not Pyodide-safe). The product's two ACTIVE lanes are:

  - OFFLINE / precompute -> `data-pipeline/lidar3dlab/stages` (this package): bakes the committed artifacts.
  - REPLAY (web default) -> `frontend/` replays those artifacts (the public GitHub Pages surface, Lane B).

The real-time "live" lane is the LOCAL-GPU API in `app/` (dormant by default): on a machine with the GPU +
model it streams a fresh reconstruction over WebSocket. This module is intentionally a marker so the frozen
base stays uniform — do NOT add a Pyodide engine here.
"""
from __future__ import annotations

LIVE_LANE = "no browser lane (heavy GPU model); real-time = local-GPU API in app/ (dormant)"
