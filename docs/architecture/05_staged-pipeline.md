# Architecture: the staged pipeline

The offline lane runs a fixed sequence of named stages. The stage **names and signatures are frozen** (part
of the archetype); the stage **bodies are the per-product science**. `data-pipeline/lidar3dlab/pipeline.py`
orchestrates them and is also the CLI:

```
python -m lidar3dlab.pipeline                 # all cases (real ones need the GPU + LIDAR3D_* env)
python -m lidar3dlab.pipeline SYN_orbit       # the synthetic CPU case (CI-safe)
python -m lidar3dlab.pipeline oxford --seed 7
```

## The order

```
CONTRACT 1 (io/contract.py: validate_rows)
        |
        v
preprocess -> feature_extraction -> train(dormant) -> infer(dispatch) -> refine -> evaluate -> export
                                                                                                   |
                                                                                                   v
                                                                             CONTRACT 2 (trace + manifest)
```

`pipeline.precompute(case_id, seed)` fetches the case from the registry, runs its `SequenceSpec` through
CONTRACT 1, and if accepted wraps the stages, timing the whole run with `time.perf_counter` to feed the gate.
`run_all` iterates every case, skipping (with a printed reason) any whose data is not present, then writes
`index.json`. The `STAGES` tuple in `pipeline.py` is the canonical order:
`("preprocess", "feature_extraction", "train", "infer", "refine", "evaluate", "export")`.

## CONTRACT 1: the ingestion gate (before the stages)

Before any stage runs, the case's params go through `io/contract.py :: validate_rows`, the
bring-your-own-data gate. It accepts a valid sequence, rejects a bad one *with a reason*, and flags a
plausible-but-suspicious one (recorded in the manifest). Full detail in [08](08_data-contracts.md). The key
point here: a case that fails ingestion never reaches the engine; `precompute` returns `{"skipped": True,
"reason": ...}` and the pipeline moves on. This is what lets the same pipeline run over the shipped cases and
over a third party's own footage.

## Stage-by-stage

Each stage has a clear input/output contract. The `SequenceSpec` (validated params) and the seed thread
through; the typed objects passed between stages (`SequenceSpec`, `FrameFeature`, `ReconResult`) are the
inter-stage contract, defined in `io/schema.py`.

### 1. preprocess (`stages/preprocess.py`)
- **In:** `SequenceSpec`. **Out:** `{"frames": [ordered paths], "synthetic": bool}`.
- Resolves and sanity-checks the sequence's frame files (CONTRACT 1 already validated the schema; this
  resolves the actual ordered `png/jpg` paths capped at `max_frames`). Raises `FileNotFoundError` if a
  non-synthetic sequence has no frames. A no-op for synthetic procedural cases (returns empty frames).

### 2. feature_extraction (`stages/feature_extraction.py`)
- **In:** `SequenceSpec` + the prepared dict. **Out:** `list[FrameFeature]`.
- Cheap per-frame quality signals on a subsample (every `len/8`-th frame): `mean_luma` (0..1 brightness; low
  means unreliable geometry) and `sharpness` (variance-of-Laplacian, a focus / motion-blur proxy), computed
  with opencv. Skipped for synthetic cases. The count of quality frames is later attached to the metrics as
  `n_quality_frames`. This stage is diagnostic: it does not gate the reconstruction, it characterizes the
  input.

### 3. train (`stages/train.py`): dormant no-op
- **In:** nothing. **Out:** a fixed info dict `{"model": "lingbot-map", "pretrained": True, "trained_here":
  False, "note": ...}`.
- Deliberately a documented no-op. The reconstruction engine is the **pretrained** lingbot-map foundation
  model (Apache-2.0), used as-is; there is no per-product surrogate to fit. The stage name is kept (frozen
  base) and records that fact. A future ONNX distillation of a sub-model (for example a low-VRAM single-image
  depth preview) would live here. See [06](06_model-evaluation.md) for why this being a no-op is honest rather
  than a gap.

### 4. infer (`stages/infer.py`): the dispatch
- **In:** `SequenceSpec` + seed. **Out:** `ReconResult` (raw, undecimated: `poses_c2w` [S,12], `points`
  [P,3] float32 world XYZ, `colors` [P,3] uint8, `per_frame`, `path_length`, bbox, `depth_thumbs`).
- This is the heart. It dispatches on the spec and imports the engine **lazily** so the light lanes never pull
  torch:

```python
def run(spec, seed=42):
    if spec.modality == "lidar":
        from ..model.lidar import reconstruct        # Open3D point-to-plane ICP odometry
    elif spec.synthetic:
        from ..model.synthetic import reconstruct    # procedural corridor, numpy only, CPU
    else:
        from ..model.lingbot import reconstruct      # lingbot-map, torch + GPU + checkpoint
    return reconstruct(spec, seed)
```

  - **Camera (`model/lingbot.py`):** loads the ordered frames, preprocesses to `image_size` at patch-14,
    builds `GCTStream` with the 8 GB-safe config, runs `inference_streaming`, converts `pose_enc` to
    extrinsics + intrinsics, inverts to camera-to-world, and unprojects each frame's depth (confidence-filtered
    at `conf_quantile`, decimated, colored from the source pixel) into the fused world cloud. Emits depth
    thumbnails for a few keyframes.
  - **LiDAR (`model/lidar.py`):** reads scans (synthetic corridor sweep, or real `.bin/.npy/.ply/.pcd`),
    registers frame-to-frame with Open3D point-to-plane ICP (voxel-downsampled, normals estimated),
    accumulates the registered height-colored map + trajectory.
  - **Synthetic (`model/synthetic.py`):** generates a textured tunnel depth+RGB per frame and runs the same
    unproject/fuse path on CPU.

### 5. refine (`stages/refine.py`): the texture / surface layer
- **In:** `ReconResult`. **Out:** `(ReconResult, refine_info)`.
- The raw cloud is already RGB-colored from the frames; refine *cleans* it when Open3D is available: voxel
  downsample + statistical outlier removal (`nb_neighbors=16, std_ratio=2.0`) + normal estimation, which is
  the hook for a textured Poisson mesh (the answer to "it should not look like a bare LiDAR map"). It
  **degrades gracefully**: if Open3D is not installed it keeps the colored cloud and records
  `{"refined": False, "reason": "open3d unavailable..."}`. So a CPU-only or CI environment still produces a
  real, colored artifact. 3DGS is an optional future lane that needs `nvcc`.

### 6. evaluate (`stages/evaluate.py`): validation
- **In:** `ReconResult`. **Out:** a metrics dict.
- Trajectory + cloud-quality metrics: `n_points`, `n_frames`, `path_length_m`, `bbox_extent_m`, `mean_conf`.
  ATE/RPE are reported as `None` with a `gt` note, because the bundled example sequences carry no
  ground-truth poses, so those are honestly "no GT" rather than faked. This honesty policy is the subject of
  [06](06_model-evaluation.md). `pipeline.precompute` then attaches `n_quality_frames` from stage 2.

### 7. export (`stages/export.py`): CONTRACT 2
- **In:** everything above (case, params, result, refine_info, seed, run_ms, flags, metrics, engine).
  **Out:** the manifest dict (also written to disk).
- Builds the compact trace (`core/trace.py`), writes `data/derived/<case>/trace.json` and records its byte
  size, runs the gate with the engine's real (non-Pyodide-safe) wheel set to get the `precompute` verdict,
  builds the manifest (`core/manifest.py`), and writes `manifests/<case>.json`. This is the seam to the web
  (see [08](08_data-contracts.md)).

## The engine label is chosen in the orchestrator

`pipeline.precompute` sets the engine metadata that lands in the manifest, modality-aware:

- LiDAR: `"open3d point-to-plane ICP (synthetic scans)"` or `"... (real LiDAR scans)"`.
- Synthetic camera: `"synthetic-corridor (CPU)"`.
- Real camera: `"lingbot-map (arXiv:2604.14141)"`.

with `pretrained = (modality == "camera" and not synthetic)`. So the manifest always states which of the three
engines produced the artifact, and whether it is the pretrained foundation model.

## See also

- [08: the two data contracts](08_data-contracts.md): CONTRACT 1 (ingestion) and CONTRACT 2 (artifact) in full.
- [06: model evaluation](06_model-evaluation.md): why `train` is a no-op and ATE is not faked.
- [02: determinism and the trace](02_determinism-and-trace.md): how the seed makes the whole chain reproducible.
