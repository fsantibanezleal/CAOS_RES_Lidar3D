# 01 · Bake a case end to end (the precompute pipeline)

How to turn a frame sequence (or LiDAR scans) into a committed, replayable artifact. This is the **active,
primary** lane of the lab (ADR-0057): the real engine runs offline, writes a compact trace + manifest, and the
frontend replays it. There is **no root `run_app.py`**; the pipeline is `python -m lidar3dlab.pipeline
<case>`.

---

## 1. Environment

The heavy engine (torch + a 4.6 GB checkpoint + a CUDA GPU) is isolated; the synthetic/CI lane needs none of
it. Use the repo's isolated envs (never a global interpreter):

```bash
scripts/setup.ps1          # Windows; or: bash scripts/setup.sh
```

This builds the Python 3.12 `.venv` (+ the pipeline env), installs the deps, and installs the package
editable. For the **real camera** cases you additionally need:

- the **GPU** deps (torch CUDA build, the vendored engine, Open3D; FlashInfer optional) installed on a CUDA
  box (see [guide 03](03_gpu-lane.md)),
- the **weights** and **data** roots exported as env vars (values come from the vault-provisioned
  `.env`, never hard-coded):
  - `LIDAR3D_MODELS_ROOT`: holds `lingbot-map/lingbot-map.pt` (resolved by `config.checkpoint_path()`),
  - `LIDAR3D_DATA_ROOT`: holds the real example sequences under `lingbot-map-examples/<seq>/` and any LiDAR
    folders (resolved by `config.sequence_dir()`).

If those are unset, the ingestion contract simply **REJECTS** a missing source cleanly (nothing crashes at
import; `config.py`), so the synthetic cases always work and the real ones are skipped with a reason.

## 2. Bake

```bash
# The CI-safe synthetic camera case (CPU, no GPU/model). Proves the whole pipeline end to end.
.venv/Scripts/python.exe -m lidar3dlab.pipeline SYN_orbit

# The synthetic LiDAR case (CPU, Open3D ICP odometry; see guide 07).
.venv/Scripts/python.exe -m lidar3dlab.pipeline LID_synthetic

# A real camera sequence (needs the GPU + the env roots).
LIDAR3D_MODELS_ROOT=… LIDAR3D_DATA_ROOT=… .venv/Scripts/python.exe -m lidar3dlab.pipeline oxford --seed 42

# Everything (real cases auto-skip when data/weights are absent).
.venv/Scripts/python.exe -m lidar3dlab.pipeline           # 'all'
```

Outputs land in `data/derived/<case>/trace.json`, `data/derived/manifests/<case>.json`, and the flat
`data/derived/manifests/index.json`. The run is **deterministic in `(params, seed)`**: same seed ⇒ the same
committed artifact (wall-clock is deliberately not stored, so re-runs do not dirty git).

## 3. The stage flow

`pipeline.precompute(case_id, seed)` runs the fixed stages (`pipeline.py`, `STAGES`):

| Stage | Module | What it does here |
|---|---|---|
| CONTRACT 1 gate | `io/contract.py` | validates the `SequenceSpec` row; **rejects** bad input with a reason, **flags** short sequences, else **accepts** ([guide 02](02_bring-your-own-data.md)). A rejected case is skipped, not faked. |
| `preprocess` | `stages/preprocess.py` | prepares the accepted sequence (frame listing / normalization). |
| `feature_extraction` | `stages/feature_extraction.py` | cheap per-frame quality signals (luma, sharpness proxy) yielding `n_quality_frames`. |
| `train` | `stages/train.py` | **dormant**: the engine is a pretrained foundation model; nothing is trained. |
| `infer` | `stages/infer.py` | dispatches by modality/synthetic: LiDAR ICP (`model/lidar`), synthetic corridor (`model/synthetic`), or the real lingbot-map engine (`model/lingbot`, lazy torch import). Emits a `ReconResult` (poses + dense depth + fused colored cloud + trajectory). |
| `refine` | `stages/refine.py` | color/texture/mesh layer: Open3D voxel-downsample + statistical-outlier removal + normals (the textured-mesh hook); degrades gracefully to the colored cloud if Open3D is absent. |
| `evaluate` | `stages/evaluate.py` | trajectory + cloud metrics; **honest** ATE = "no GT" when the sequence carries no ground truth. |
| `export` | `stages/export.py` | CONTRACT 2: writes the compact `trace.json` + the case manifest, records the measured lane/gate verdict (always `precompute` here), byte size, CONTRACT-1 flags, refine info, metrics, engine card. |

The engine label in the manifest is set truthfully per case (`pipeline.py`): `open3d point-to-plane ICP
(...)` for LiDAR, `synthetic-corridor (CPU)` for the synthetic camera case, `lingbot-map (arXiv:2604.14141)`
for real camera, with `pretrained=True` only for the real camera path.

Deep engine internals: [theory 02–04](../theory.md). Stage roles at the architecture level:
[`architecture/05_precompute-pipeline.md`](../architecture/05_precompute-pipeline.md).

## 4. Check + test

```bash
.venv/Scripts/python.exe -m pytest        # ruff + the SYN_orbit smoke + the LiDAR test + contract/manifest tests
scripts/smoke.ps1                          # CONTRACT 2: index <-> manifests <-> artifacts are consistent
python scripts/check_artifacts.py          # the drift guard
```

CI runs the synthetic case as its smoke, so a green CI means the full staged path + both contracts + the gate
still work without a GPU.

## 5. Then the frontend

```bash
cd frontend && npm install && npm run build && npm run preview
```

`copy-data.mjs` enforces the artifact contract when copying `data/derived` into the SPA; a shape drift between
`io/schema.py` and `frontend/src/lib/contract.types.ts` fails `tsc`. Screenshot-verify every panel (App
sources/modes, both themes, the ⓘ modal) before any deploy.
