# 00 · How this repo was instantiated (and the rework surface)

This is not the generic "copy the template" note (that lives in the archetype docs). It records how
**CAOS_RES_Lidar3D specifically** was produced from `template_repo_product` (ADR-0057), what was reworked, and
exactly which surface you are allowed to touch when you continue the work. The point of the archetype is that
the **base is frozen**; you edit only the **core** (engine, stages, visualizations, cases, content).

---

## 1. What the template provided (frozen base)

The archetype ships a working skeleton: the staged-pipeline scaffold (`preprocess, feature_extraction,
train, infer, refine, evaluate, export`), the two data contracts (ingestion + artifact manifest), the
determinism/trace machinery, the measured live-vs-precompute gate, the React 19 + Vite + three.js + KaTeX
frontend shell with the 6-page layout and the ADR-0058 architecture modal, the dormant `app/` FastAPI lane,
CI (ruff + pytest + guards), and the docs tree. All of that is **structure you do not edit**. If you find
yourself editing the base, that is the smell ADR-0057 exists to remove.

## 2. What was reworked for this product (the core)

The template's EXAMPLE engine was an SIR epidemic simulator. Instantiating Lidar3D replaced the *core* while
keeping every stage name and both contracts:

1. **Package rename** `<slug>lab` to `lidar3dlab` (folder, imports, `pyproject.toml`, the `-m lidar3dlab.pipeline`
   entrypoint, docs).
2. **Real engine, vendored.** The 2026 SOTA streaming reconstructor **lingbot-map** (arXiv:2604.14141,
   Apache-2.0) was vendored under `third_party/lingbot-map/` and wrapped, not re-implemented, in
   `lidar3dlab/model/lingbot.py`. Two more engines were written behind the same `ReconResult` interface: a
   **synthetic corridor** CPU engine (`model/synthetic.py`, CI-safe, no GPU/model) and a **LiDAR ICP** engine
   (`model/lidar.py`, Open3D point-to-plane, KISS-ICP-swappable). Shared pure-NumPy geometry is in
   `model/geometry.py`.
3. **Stage bodies** were specialized to reconstruction (`stages/infer.py` dispatches by modality/synthetic
   flag; `stages/refine.py` does the color/texture/mesh-hook layer; `stages/evaluate.py` reports honest ATE
   "no GT" when the example sequences carry none), while `train.run()` is **dormant** because the engine is a
   pretrained foundation model (nothing to train).
4. **CONTRACT 1 rewritten for reconstruction input** (`io/contract.py`): the ingestion gate now validates an
   ordered folder of RGB frames + the inference knobs (see [guide 02](02_bring-your-own-data.md)). The typed
   inter-stage objects are `SequenceSpec` and `ReconResult` (`io/schema.py`).
5. **Cases-by-category** were defined (`cases/example_case.py` + `registry.py`): a synthetic camera control, a
   synthetic LiDAR control, a real LiDAR hook, and four real camera sequences (see
   [guide 06](06_add-an-engine-or-case.md)).
6. **Engine card** written under `docs/frameworks/lingbot-map/` and the research surveys under
   `docs/research/`; the engine is **pinned** in the pipeline requirements (the deep research, made binding).
7. **Frontend visualizations** built for this domain: a three.js RGB-colored point-cloud viewer + camera
   frustum trajectory + per-frame depth panel + stats, plus the ADR-0058 modal specialized to the
   reconstruction algorithm (see [guide 05](05_architecture-modal.md)).
8. **Lanes activated selectively.** The **offline/precompute** lane and the public **replay** frontend are
   active; the browser-**live** (Pyodide) lane is impossible here (a ~1B ViT + a 4.6 GB checkpoint is not
   browser-feasible, and even the synthetic engine pulls matplotlib, which is not Pyodide-safe), so `live.py`
   is a marker and the real-time lane is the dormant local-GPU `app/` (see [guide 04](04_run-the-api.md)).

## 3. The rework surface (what you may edit)

| Area | Path | Edit? |
|---|---|---|
| Engines | `data-pipeline/lidar3dlab/model/{lingbot,synthetic,lidar,geometry}.py` | **yes** (core) |
| Stage bodies | `data-pipeline/lidar3dlab/stages/*` | **yes** (keep the names) |
| Cases / registry | `.../cases/example_case.py`, `.../registry.py` | **yes** |
| Ingestion contract | `.../io/contract.py` (+ `tests/test_contract.py`) | **yes, deliberately** ([guide 02](02_bring-your-own-data.md)) |
| Vendored engine | `third_party/lingbot-map/` | **no** (upstream, Apache-2.0; patch only with a recorded reason) |
| Visualizations | `frontend/src/render/`, `App.tsx`, `architecture.ts` | **yes** |
| Contracts shape | `io/schema.py` + mirror `frontend/src/lib/contract.types.ts` | edit **together** (a drift fails `tsc`) |
| Base structure, gate, determinism, deploy, env | everything else | **no** |

## 4. Verify after any rework

`scripts/setup`, then bake the CI-safe synthetic case (`python -m lidar3dlab.pipeline SYN_orbit`), then
`pytest` (ruff + the synthetic smoke + the CONTRACT-2 drift guard + the base-integrity guards: no `.env`, no
venv/binaries, no leaked machine paths), then `cd frontend && npm run build`. Then screenshot-verify the frontend
(every panel in every source/mode, both themes, the modal) before any deploy. See
[guide 01](01_precompute-pipeline.md).

## 5. Version + docs discipline

Version from day 1 (`CHANGELOG.md`, `X.XX.XXX`, `0.x` while any case is synthetic, a tag per release; current
status v0.02.000). Author the wiki **as you work**, not at the end (ADR-0056): this `docs/theory/` +
`docs/guides/` set is that wiki.
