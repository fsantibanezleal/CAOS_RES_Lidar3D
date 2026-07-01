# 06 · Add an engine or a case

How to extend the lab with a new reconstruction **engine** (a new `model/`) or a new **case** (a new operating
point in the taxonomy), without touching the frozen base. The two are separate: an engine is *how* geometry is
produced; a case is *what* sequence is run and in which category. The dispatch that ties them together is the
**modality/synthetic** switch in `stages/infer.py`.

---

## 1. The engine contract

Every engine is a single function

```python
def reconstruct(spec: SequenceSpec, seed: int = 42) -> ReconResult: ...
```

that takes a validated `SequenceSpec` and returns a `ReconResult` (`io/schema.py`): per-frame camera-to-world
poses (`poses_c2w`, `[S,12]`), a fused world point cloud (`points` `[P,3]` f32 + `colors` `[P,3]` u8), the
`per_frame` list (idx, conf_mean, n_points, depth_min/max), `path_length`, `bbox_min/max`, and a few
`depth_thumbs`. As long as an engine emits that, the contracts, gate, export, and web replay are identical, so
the whole rest of the pipeline is engine-agnostic. Three engines exist today:

- `model/lingbot.py`: the real streaming camera engine (GPU, lazy torch import).
- `model/synthetic.py`: a procedural corridor CPU engine (CI-safe, no GPU/model).
- `model/lidar.py`: Open3D point-to-plane ICP on scans ([guide 07](07_lidar-modality.md)).

Shared, torch-free geometry (unprojection, trajectory length, depth thumbnails) is in `model/geometry.py`;
reuse it so a new engine stays light and consistent.

## 2. The modality dispatch

`stages/infer.py` picks the engine from the spec (nothing else in the pipeline changes):

```python
def run(spec, seed=42):
    if spec.modality == "lidar":
        from ..model.lidar import reconstruct
    elif spec.synthetic:
        from ..model.synthetic import reconstruct
    else:
        from ..model.lingbot import reconstruct
    return reconstruct(spec, seed)
```

So the routing keys are `SequenceSpec.modality` (`"camera"` | `"lidar"`) and `SequenceSpec.synthetic`. Imports
are **lazy** on purpose: the synthetic/CI lane must never pull torch or the vendored engine.

## 3. Add a new engine

1. **Write** `data-pipeline/lidar3dlab/model/<engine>.py` with `reconstruct(spec, seed) -> ReconResult`.
   Import heavy deps **inside** the function (lazy), reuse `geometry.py`, and honor the 8 GB-safe knobs on the
   `spec` if it is a GPU engine ([guide 03](03_gpu-lane.md)).
2. **Route to it.** Either reuse an existing modality (e.g. another camera engine behind a new flag) or add a
   new branch in `stages/infer.py`. If you add a new modality string, thread it through `SequenceSpec`
   (`io/schema.py`), the `_row` projection and the engine label in `pipeline.py`, and CONTRACT 1's accepted
   `modality` field (`io/contract.py`).
3. **Label it truthfully** in the manifest: extend the engine-label block in `pipeline.precompute` so the
   manifest's `model` string and `pretrained` flag describe the real engine (honesty: a synthetic engine is
   labeled synthetic, a pretrained model is labeled pretrained).
4. **Pin + document.** Pin the engine's deps in the appropriate `requirements-*.txt` and add a card under
   `docs/frameworks/<engine>/` (the deep research, made binding, no toy substitute). If the engine changes the
   `ReconResult`/trace shape, update `frontend/src/lib/contract.types.ts` **in the same change** (a drift fails
   `tsc`) and the viewer in `frontend/src/render` + `App.tsx`.
5. **Test.** Add a smoke like `tests/test_lidar.py` / the `SYN_orbit` smoke that runs the engine on a tiny,
   deterministic input on CPU where possible.

Do **not** modify `third_party/lingbot-map/` to add an engine; vendor a new upstream under `third_party/`
instead, and wrap it in a `model/` module.

## 4. Add a case (by category)

Cases live in `cases/example_case.py` as `Case(id, category, params: SequenceSpec, expected_band,
real_or_synthetic)` and are exposed through `registry.py`. Categories are the reconstruction problem-type
taxonomy; the App shows **one** selected case, while Experiments/Benchmark show cross-case summaries **by
category**. Current cases:

| id | category | modality | notes |
|---|---|---|---|
| `SYN_orbit` | synthetic camera (CPU, CI) | camera, synthetic | procedural corridor; the CI smoke |
| `LID_synthetic` | synthetic LiDAR (CPU, CI) | lidar, synthetic | ICP odometry down a corridor |
| `kitti_lidar` | real LiDAR (KITTI-style) | lidar | folder of `.bin`/`.npy`/`.ply`; bakes when present |
| `oxford` | real: outdoor walk | camera (GPU) | lingbot-map example seq |
| `university` | real: courtyard | camera (GPU) | lingbot-map example seq |
| `loop` | real: revisit (loop closure) | camera (GPU) | showcases the drift / loop-closure gap |
| `courthouse` | real: facade orbit | camera (GPU) | lingbot-map example seq |

To add a case:

1. **Append a `Case`** with a `SequenceSpec`. Real camera sequences use the `_real(seq, max_frames)` helper
   (which resolves `source_dir` via `sequence_dir(seq)` under `LIDAR3D_DATA_ROOT`, never an absolute path).
   Synthetic cases set `synthetic=True` and a `synthetic://...` source; LiDAR cases set `modality="lidar"`.
2. **Choose the category** to reflect a real axis of the taxonomy (a new problem type gets a new category;
   variants of an existing one share it). Include negative/sanity controls where meaningful (the two synthetic
   cases are the CI controls).
3. **Write the `expected_band`**: what a domain expert should see (e.g. "forward tunnel; ~5 m path; runs on
   CPU in <1 s"), so validation can check reality, not just that files exist.
4. **Bake + document**: `python -m lidar3dlab.pipeline <id>` and add/refresh the case page under
   `docs/cases/`. The registry row is validated by the same CONTRACT 1 as any external data
   ([guide 02](02_bring-your-own-data.md)).

## 5. Guardrails

- Keep the stage **names** and both contracts; edit only bodies (ADR-0057).
- New GPU engines/cases must still leave the **synthetic CI lane** green (no torch import on that path).
- Label everything honestly in the manifest; never present a synthetic engine as a real one.
- After any change that moves the trace/manifest shape, re-verify `tsc` + the CONTRACT-2 drift guard +
  screenshot-verify the affected panels.
