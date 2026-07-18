# Architecture: the three lanes in depth

The archetype defines three execution lanes (ADR-0054). This document describes each one for Lidar 3D
specifically, and, crucially, how the archetype keeps the **dependency separation** and the **implementation
separation** clean so that a heavy offline engine never leaks into the browser bundle and a dormant lane never
weighs on the active ones.

```
   +-----------------------------+        +---------------------------+        +--------------------------+
   |  offline / precompute       |        |  REPLAY  (public default) |        |  LIVE  (dormant)         |
   |  data-pipeline/lidar3dlab   |  bake  |  frontend/  static SPA    |  ---   |  app/  FastAPI local-GPU |
   |  local GPU + checkpoint     | -----> |  GitHub Pages             |        |  real-time streaming     |
   |  requirements.txt (torch,   |  data/ |  no deps at request time  |        |  requirements-api.txt    |
   |  open3d, matplotlib, cv2)   | derived|  lidar3d.fasl-work.com     |        |  not browser-feasible    |
   +-----------------------------+        +---------------------------+        +--------------------------+
        writes committed artifacts             reads committed artifacts           (only on a GPU host)
```

## Lane A: offline / precompute (active)

This is where the real reconstruction happens. It runs the `lidar3dlab` package in a local Python 3.12
`.venv` on a machine with a CUDA GPU, and it bakes the committed artifacts under `data/derived/`.

- **Entrypoint:** `python -m lidar3dlab.pipeline <case|all> [--seed N]` (or `scripts/precompute.{ps1,sh}`).
- **Dependencies:** `data-pipeline/requirements.txt`, the heavy set: torch (matched to the local CUDA driver),
  the vendored lingbot-map engine, Open3D, KISS-ICP, matplotlib, opencv, pillow. These are deliberately kept
  in the pipeline requirements file and nowhere near the frontend.
- **Inputs, resolved from the environment:** the checkpoint from `LIDAR3D_MODELS_ROOT/lingbot-map/`, raw
  sequences / LiDAR scans from `LIDAR3D_DATA_ROOT`. Neither path is ever committed; `config.py` reads them
  from env and falls back to empty repo-relative defaults so nothing crashes at import when they are unset (the
  ingestion contract then simply rejects the missing source, cleanly).
- **Hardware reality:** the flagship camera engine is validated on an RTX 4070 Laptop (8 GB) with an 8 GB-safe
  configuration (`use_sdpa=True`, CPU-offload via `output_device='cpu'`, `kv_cache_sliding_window=16`,
  `camera_num_iterations=1`, bf16 aggregator), peak ~7.1 GB. The synthetic and LiDAR-synthetic cases run on
  CPU in well under a second, which is what makes them CI-safe.
- **Output:** for each case, `data/derived/<case>/trace.json` + `data/derived/manifests/<case>.json`, plus a
  regenerated `data/derived/manifests/index.json`. These are committed. They are the source of truth.

## Lane B: REPLAY (active, the public surface)

The replay lane is the static React + Vite + three.js SPA in `frontend/`. It is the public default and the
only lane the end user touches, served on GitHub Pages at `lidar3d.fasl-work.com`.

- **No dependencies at request time.** The SPA is a static bundle plus the JSON artifacts. There is no server,
  no Python, no model in the browser.
- **What it does:** loads `index.json`, then a selected case's manifest, then its trace, decodes the base64
  arrays into typed arrays, and renders the RGB-colored point cloud in a three.js viewer with a camera-frustum
  trajectory, per-frame depth thumbnails, and reconstruction stats. Because the trace carries `frame_offsets`,
  the App can replay the cloud building up frame by frame.
- **The build-time overlay:** `frontend/copy-data.mjs` (a Vite prebuild step) copies `data/derived` into
  `frontend/public/data` so the static site serves the committed artifacts. `public/data` is a build-time
  overlay and is git-ignored; the canonical copies live in `data/derived`. The App loads only manifests +
  artifacts, and `contract.types.ts` mirrors CONTRACT 2 so any schema drift fails `tsc` at build time.
- **Always the fallback.** By ADR-0054, replay is what makes the product functional no matter what the gate
  decides. A product can ship with every case precompute (as this one does) and still be fully usable, because
  replay is always present.

## Lane C: LIVE (dormant)

The real-time "live" lane for this product is **not** a browser lane. The engine is a ~1B-parameter ViT that
needs a CUDA GPU and a 4.6 GB checkpoint, so there is no Pyodide/WASM engine here (and even the synthetic
engine pulls matplotlib, which is not Pyodide-safe, see [03](03_the-gate.md)). The live lane is instead the
dormant local-GPU FastAPI in `app/`.

- **What it would be:** on a machine with the GPU + model, `app/` streams a fresh reconstruction of the user's
  own footage over the network (a WebSocket stream of poses + depth + points), a thin layer over the same
  `lidar3dlab` engine, never a re-implementation.
- **Status:** dormant by default. `app/` is a scaffold; `requirements-api.txt` is not installed in the normal
  flow. Activate it only on an ADR-0002 trigger (server-side processing of uploaded data, auth-gated private
  data, paid heavy compute). When activated, its endpoints serve the same committed artifacts read-only unless
  and until the streaming reconstruction is wired.
- **The marker:** `lidar3dlab/live.py` is intentionally a one-line constant recording that there is no browser
  lane and that real-time is the dormant `app/`. It keeps the frozen base uniform across the CAOS labs (which
  do have a `live.py` entrypoint) without pretending a WASM engine exists.

## Dependency separation (why the lanes do not contaminate each other)

The archetype keeps three requirements files apart, and this is load-bearing:

| File | Lane | Contains |
|---|---|---|
| `data-pipeline/requirements.txt` | offline | torch, lingbot-map, open3d, kiss-icp, matplotlib, opencv, pillow (heavy, GPU) |
| `frontend/package.json` | replay | React, Vite, three.js, KaTeX (no Python at all) |
| `requirements-api.txt` | live (dormant) | FastAPI + uvicorn, a thin read-only layer |
| `requirements-dev.txt` | CI/tests | ruff, pytest (+ the editable package) |

The frontend has no Python dependency; the offline heavy stack never enters the browser bundle; the dormant
API's deps are not pulled in normal development. That is why the public SPA stays small and the CI stays fast
even though the offline engine is enormous.

## Implementation separation (lazy imports keep the light lanes light)

Inside `lidar3dlab`, the dispatch is arranged so that importing the package, or running the synthetic CI lane,
never pulls torch or Open3D:

- `stages/infer.py :: run` dispatches on the spec: `modality == "lidar"` imports `model.lidar` (Open3D),
  `synthetic` imports `model.synthetic` (numpy only), otherwise it imports `model.lingbot` (torch) **inside
  the branch**. The imports are function-local, so the synthetic path never touches torch.
- `model/lingbot.py` imports the vendored `lingbot_map` engine and torch only when `reconstruct` is called.
- `model/geometry.py` is pure numpy (with a lazy matplotlib/PIL import only inside `depth_to_png_b64`), so the
  tests and the synthetic lane stay light.

The net effect: CI can install just the pipeline + dev requirements, run the synthetic bake, and validate the
whole contract chain without a GPU, a checkpoint, or a torch import on the hot path.

## See also

- [01: overview](01_overview.md): the four layers and the flow diagram.
- [03: the gate](03_the-gate.md): why the browser-live lane is not applicable here.
- [05: the staged pipeline](05_staged-pipeline.md): the dispatch inside `infer` and every stage's job.
- [07: deploy](07_deploy.md): how the replay lane reaches GitHub Pages.
