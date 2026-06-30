# data-pipeline/ — the offline engine (`lidar3dlab`)

Rename `lidar3dlab` → `<slug>lab` per product. The **single source of physics/algorithm truth**; `frontend/` and
`app/` consume it, never re-implement it. Its own venv: **`.venv-pipeline`** (heavy SOTA engines, local-only).

## Layout (the package lives directly under `data-pipeline/`)
- `lidar3dlab/pipeline.py` — orchestrator + CLI (`python -m lidar3dlab.pipeline [all|<case>] [--seed N]`)
- `lidar3dlab/registry.py` — cases grouped by CATEGORY · `lidar3dlab/live.py` — Pyodide live entrypoint
- `lidar3dlab/io/` — `contract.py` (**CONTRACT 1**) · `formats.py` (standard readers/writers) · `schema.py` (types)
- `lidar3dlab/core/` — `rng.py` (seeded determinism) · `trace.py` · `manifest.py` (**CONTRACT 2**) · `gate.py`
- `lidar3dlab/model/` — the shared pure-Python core (Pyodide-safe); EXAMPLE = SIR
- `lidar3dlab/stages/` — `preprocess → feature_extraction → train → infer → evaluate → export`
- `lidar3dlab/cases/` — documented cases

Setup + run: `scripts/setup.{sh,ps1}` then `scripts/precompute.{sh,ps1}`. See
[../docs/architecture/05_precompute-pipeline.md](../docs/architecture/05_precompute-pipeline.md).
