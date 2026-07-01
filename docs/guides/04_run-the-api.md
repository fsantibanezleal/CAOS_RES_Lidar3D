# 04 · Run the API (the dormant live lane)

The lab has three lanes (ADR-0057): **offline/precompute** (active, the primary product), **replay** (active,
the public GitHub Pages SPA), and **live** (dormant). This guide is about the live lane, `app/`. Read it to
understand what it would do and how it would stream; it is **off by default** and deliberately so.

---

## 1. Why live is dormant here

For most CAOS products "live" means a Pyodide/WASM engine running in the browser. **That is impossible for
this product**: lingbot-map is a ~1B-parameter ViT needing a CUDA GPU + a 4.6 GB checkpoint, and even the
synthetic engine pulls matplotlib, which is not Pyodide-safe. So there is **no browser-live engine**
(`data-pipeline/lidar3dlab/live.py` is intentionally just a marker; do not add a Pyodide engine there). The
measured live-vs-precompute gate ([architecture 03](../architecture/03_the-gate.md)) therefore classifies
every case as `precompute`, and the public web app is pure replay.

The genuine "live" experience for this product is a **local-GPU API**: on a machine that has the GPU + the
weights, `app/` would stream a fresh reconstruction of your own footage. It is dormant because the public
product does not need it and running a ~1B model is not a free public service (an ADR-0002 activation
trigger).

## 2. What the dormant `app/` provides today

`app/` is a thin, read-only FastAPI layer over the committed artifacts (`app/main.py`, `app/routers/`,
`app/services/`): endpoints like `GET /api/cases`, `/api/cases/{id}/manifest`, `/api/cases/{id}/trace`, and
`/health` serve the **same** `data/derived` artifacts the pipeline baked. It is a convenience server, never a
re-implementation of the engine, and it is not deployed by default (the public surface is the static SPA).

To run the read-only server locally:

```bash
# pin fastapi/uvicorn in requirements-api.txt, install into .venv, then:
uvicorn app.main:app --reload
```

## 3. How the true streaming lane would work (activation design)

Activating real-time reconstruction is a deliberate extension, not a default. The design that fits the engine:

1. **Trigger + deps.** An ADR-0002 trigger (server-side processing of uploaded footage on a GPU host).
   Install the GPU deps (the 8 GB-safe stack of [guide 03](03_gpu-lane.md)) into the API env and set
   `LIDAR3D_MODELS_ROOT` / `LIDAR3D_DATA_ROOT`.
2. **Load once.** On startup, load `GCTStream` with the 8 GB-safe knobs and the checkpoint (as
   `model/lingbot.py` does), keep it resident on the GPU.
3. **Stream over WebSocket.** The engine is already frame-by-frame causal: `inference_streaming` processes the
   anchor block first, then streams one frame at a time with the KV cache
   ([theory 02](../theory/02_geometric-context-transformer.md)). A WebSocket endpoint would, per client:
   - accept frames as they arrive (an uploaded clip decoded at N FPS, or a live feed),
   - for each frame call the single-frame forward, unproject the depth to world points
     ([theory 03](../theory/03_pointmaps-and-geometry.md)), confidence-filter + decimate, and push the
     incremental `{pose, new_points, depth_thumb, stats}` delta to the client,
   - the client renders the growing cloud + trajectory in three.js (the same viewer the replay uses).
   `clean_kv_cache()` is called per new sequence; `keyframe_interval > 1` and `kv_window` bound memory for
   long streams.
4. **Backpressure + limits.** One reconstruction per GPU at a time (the model is large); queue or reject
   concurrent sessions; cap `max_frames`. The CONTRACT-1 gate ([guide 02](02_bring-your-own-data.md)) still
   validates uploaded footage before it touches the engine.

## 4. Discipline even with a backend

Keep the data-pipeline + contract discipline: the API serves what the pipeline baked, and any live stream runs
the **same** engine + geometry + contracts as the offline lane, so results are consistent between "replay a
baked case" and "reconstruct my clip live." Deploy the activated server via the dormant VPS templates in
`deploy/`. Until a real trigger exists, leave `app/` dormant with its README marker.
