# Architecture: overview

Lidar 3D (`CAOS_RES_Lidar3D`) is a **streaming 3D reconstruction lab**. It turns an ordered stream of RGB
frames into a camera trajectory, dense metric depth, and a fused RGB point cloud, feed-forward and with no
per-scene optimization, and it does so honestly: the heavy reconstruction is baked offline on a GPU, the
committed artifact is the source of truth, and the public web app only replays it.

The product is an instance of the CAOS product-repo archetype (ADR-0057): offline-pipeline-heavy,
backend-optional, deploying as a static deterministic-replay viewer. The archetype base is **frozen** (folder
layout, the two data contracts, the staged-pipeline names, the gate, the manifest/trace shape, the CI guards);
the per-product surface is only the **core**: the reconstruction engines in `model/`, the stage bodies, the
`frontend/` visualizations, and the cases + content. This document is the map of the whole thing.

## Two engines, one pipeline

Lidar 3D carries two real reconstruction engines behind one uniform pipeline, dispatched by
`SequenceSpec.modality`:

1. **Camera modality (`lingbot-map`).** The binding SOTA engine (arXiv:2604.14141, vendored Apache-2.0 under
   `third_party/lingbot-map`). A DINOv2-ViT (frozen, patch-14) backbone followed by 24 alternating
   frame / cross-frame attention blocks (the VGGT design), driven by **Geometric Context Attention** over
   three contexts (anchor context, a pose-reference window, and a trajectory memory), served by a paged KV
   cache. It emits `pose_enc` + dense **metric** `depth` + `depth_conf` per frame. There is no `world_points`
   key: we unproject depth into world points ourselves (see below). It is a ~1B-parameter model that needs a
   CUDA GPU and a 4.6 GB checkpoint, so it never runs in a browser.
2. **LiDAR modality (Open3D ICP odometry).** The second engine that makes the name "Lidar 3D" honest: it
   consumes actual LiDAR scans (the camera engine reconstructs LiDAR-*like* clouds from video). Frame-to-frame
   point-to-plane ICP odometry (`model/lidar.py`) registers scans and accumulates a height-colored map plus
   the odometry trajectory. KISS-ICP, the SOTA LiDAR-only odometry, is pinned in requirements and swappable
   behind the same interface.

A third **synthetic** engine (`model/synthetic.py`) is a procedural corridor flythrough. It is not a fake: it
runs the exact same per-frame-depth to unproject to fuse path as the camera engine, in milliseconds on CPU,
so the pipeline, contracts, gate, export, and web replay stay identical without a GPU or the checkpoint. It is
what CI smoke-tests, and it powers the App's "Synthetic" source with a genuinely colored/textured cloud.

## The four layers

The archetype separates concerns into four layers. Nothing in a higher layer knows the machine-specific facts
of a lower one; that separation is what lets the pieces move independently.

| Layer | Where | What it owns |
|---|---|---|
| **Ingestion** | `data-pipeline/lidar3dlab/io/` | what a valid input is: the `SequenceSpec` schema, CONTRACT 1 (`contract.py`), the standard format readers/writers (`formats.py`) |
| **Engine + pipeline** | `data-pipeline/lidar3dlab/{model,stages,core}/` | the two reconstruction engines, the named staged pipeline, the gate, the deterministic RNG, the manifest/trace builders |
| **Artifact** | `data/derived/` (committed) | the compact trace per case + the manifest + a flat `index.json`, governed by CONTRACT 2 |
| **Replay / render** | `frontend/` | the React + three.js SPA that loads only manifests + artifacts and replays them; the dormant `app/` FastAPI live lane |

Heavy assets (the checkpoint, raw sequences) live outside git, resolved from `LIDAR3D_MODELS_ROOT` /
`LIDAR3D_DATA_ROOT`; the committed compact artifacts under `data/derived/` are the only large-ish thing in
the repo, and they stay small by budget (see [08](08_data-contracts.md)).

## The three lanes

The archetype defines three execution lanes (ADR-0054). For this product exactly one of them, replay, is the
public surface, because the engine is not browser-feasible.

| Lane | Runs where | Deps | Status |
|---|---|---|---|
| **OFFLINE / precompute** | `data-pipeline/lidar3dlab` on a local GPU | `data-pipeline/requirements.txt` (torch, open3d, matplotlib, opencv) | active: bakes the committed artifacts |
| **REPLAY** | `frontend/` static SPA on GitHub Pages | none at request time | active: the public default, live at `lidar3d.fasl-work.com` |
| **LIVE** | `app/` local-GPU FastAPI | `requirements-api.txt` | dormant: the 1B ViT is not browser-feasible; real-time only on a GPU host |

There is a deliberate asymmetry with the lighter CAOS labs (SimLab, PINN-Lab) that ship a Pyodide/WASM
browser-live engine. Here the gate (see [03](03_the-gate.md)) classifies **every** case as `precompute`,
because even the synthetic engine imports matplotlib (not Pyodide-safe) and the real engine needs torch + a
GPU. `lidar3dlab/live.py` is intentionally just a marker recording that fact, so the frozen base stays
uniform; do not add a Pyodide engine there.

## The flow

```
                     LIDAR3D_MODELS_ROOT (checkpoint)   LIDAR3D_DATA_ROOT (raw sequences / scans)
                                     \                          /
  data/raw or a CSV of sequences ->   [ CONTRACT 1: io/contract.py ]   (bring-your-own-data gate:
                                                   |                     accept / reject-with-reason / flag)
                                                   v
    preprocess -> feature_extraction -> train(dormant) -> infer(dispatch camera|lidar|synthetic)
                                                   |
                                       refine(Open3D clean/mesh) -> evaluate(honest metrics)
                                                   |
                                                   v
                              [ CONTRACT 2: core/trace.py + core/manifest.py ]
                              compact base64 RGB cloud + camera trajectory + frame_offsets
                              + depth thumbs + a manifest (params, seed, lane, gate, bytes)
                                                   |
                                                   v
                      data/derived/<case>/trace.json + manifests/<case>.json + index.json  (COMMITTED)
                                                   |
                        copy-data.mjs overlays data/derived -> frontend/public/data
                                                   |
                                                   v
                     frontend/ SPA replays it  (contract.types.ts mirrors CONTRACT 2 -> tsc guards drift)
                                                   |
                                                   v
                            GitHub Pages: lidar3d.fasl-work.com  (deploy-pages.yml)
```

## depth to world

The camera engine emits depth + pose + self-calibrated intrinsics, not world points, so we unproject
ourselves (`model/geometry.py :: unproject_depth`). For pixel `(u, v)` with metric depth `D`, camera
intrinsics `(fx, fy, cx, cy)`, and camera-to-world pose `(R_c2w, t_c2w)`:

```
X_world = R_c2w [ (u - cx)/fx * D ,  (v - cy)/fy * D ,  D ]^T  +  t_c2w
```

Points are confidence-filtered (drop the lowest `conf_quantile` fraction), colored from the source pixel,
decimated by a stride, and emitted ordered by frame so the web can replay the build-up. The camera engine's
metric scale is fixed by the anchor context: `s = mean L2 norm of the anchor cloud`, so the trajectory
lengths reported in the manifest are in metres.

## Frozen base vs rework

- **Frozen (never re-litigated per product):** the folder layout, both data contracts, the staged-pipeline
  stage names and signatures, the gate, the manifest/trace schema, the two-venv split, the cases-by-category
  mechanism, and the CI guards. Any area may be *dormant* (with a README saying so), for example `app/` and
  the VPS deploy templates.
- **Rework (the only per-product surface):** the engines in `model/` and the stage bodies (the science), the
  `frontend/` visualizations, and the cases + content + calibration.

## Read next

- [02: determinism and the trace](02_determinism-and-trace.md): why a bake is a pure function of
  `(params, seed)`, what the trace artifact contains, and the LiDAR non-determinism caveat.
- [03: the gate](03_the-gate.md): `classify_lane`, why every case is precompute, and the budgets.
- [04: the lanes](04_lanes.md): offline / replay / live in depth, and the dependency + implementation split.
- [05: the staged pipeline](05_staged-pipeline.md): every stage's input/output contract and the dispatch.
- [06: model evaluation](06_model-evaluation.md): what we measure, why there is no faked ATE, the honesty policy.
- [07: deploy](07_deploy.md): Pages, the workflow, the custom domain, the env/secrets model.
- [08: the two data contracts](08_data-contracts.md): both contracts in full, including the TS mirror.

Binding decision: [ADR-0057](../../../conventions/architecture/0-archetype/ADR-0057-product-repo-archetype.md).
