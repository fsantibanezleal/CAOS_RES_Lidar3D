# 02 · Bring your own data (CONTRACT 1)

The lab is a **tool**, not just a replay of baked cases: you can point it at your **own** RGB sequence or LiDAR
scans. The door is **CONTRACT 1**, the ingestion gate (`data-pipeline/lidar3dlab/io/contract.py`,
`validate_rows`). This guide is the exact contract for reconstruction input: what a valid job is, and what
passes, rejects, or gets flagged. Nothing is ever silently coerced.

---

## 1. What a valid input is

A reconstruction job is one **`SequenceSpec`** (`io/schema.py`): a source of ordered frames (or scans) plus
the inference knobs. The minimum you must supply is a `case_id` and a `source_dir`
(`REQUIRED_COLUMNS = ("case_id", "source_dir")`).

- **Camera (default modality).** `source_dir` is a folder of ordered RGB frames
  (`.png/.jpg/.jpeg`), intrinsics-free (the engine self-calibrates,
  [theory 03 §5](../theory/03_pointmaps-and-geometry.md)). Frames are read in sorted filename order, so
  zero-pad your names (`frame_00001.png`, …). Drop the folder under `data/raw/` (git-ignored) or point
  `LIDAR3D_DATA_ROOT` at it.
- **LiDAR (`modality="lidar"`).** `source_dir` is a folder of `.bin` (KITTI Velodyne `xyzi` float32),
  `.npy` (`[N,≥3]`), `.ply`, or `.pcd` scans (see [guide 07](07_lidar-modality.md)).
- **Synthetic (`synthetic=true`).** No real data; the procedural engine builds the scene. Used for the CI
  controls (`SYN_orbit`, `LID_synthetic`).

The knobs (all optional, defaults from `SequenceSpec`): `max_frames` (cap processed, 8 GB-safe),
`image_size`, `decimation`, `conf_quantile`, `kv_window`, `scale_frames`, `camera_iters`, `modality`. Their
meaning and safe values are in [guide 03](03_gpu-lane.md).

## 2. The policy: accept / reject / flag

`validate_rows` applies an **explicit** policy per row and returns a `ContractReport` with three lists. The
pipeline runs only accepted rows; a rejected case is skipped (not faked); a flagged case runs but the flag is
recorded in the manifest.

### REJECT (with a reason) if any of:

| Condition | Reason | Source |
|---|---|---|
| missing/empty `case_id` or `source_dir` | `missing/empty columns: [...]` | `REQUIRED_COLUMNS` |
| (real) `source_dir` is not a directory | `source_dir not found: ...` | `os.path.isdir` |
| (real) fewer than 8 frames | `only N frames; need >= 8` | `MIN_FRAMES = 8` (need the anchor/scale block) |
| (real) more than 20,000 frames | `N frames > 20000 (beyond training range)` | `MAX_FRAMES_HARD` (use windowed mode + a different case) |
| any knob out of range (or NaN) | `name=v out of [lo,hi]` | `RANGES` (below) |

Knob ranges (`RANGES`), outside ⇒ reject:

- `max_frames ∈ [8, 2000]` (frames processed; the 8 GB-safe cap),
- `image_size ∈ [140, 1036]` px working resolution,
- `decimation ∈ [1, 32]` keep every Nth pixel,
- `conf_quantile ∈ [0.0, 0.95]` fraction of low-confidence pixels dropped.

Note the NaN guard is written `if v != v or not (lo <= v <= hi)`: NaN is rejected explicitly (it fails the
`v != v` test), so a malformed numeric never slips through as "in range".

### FLAG (accepted, recorded) if:

- (real) fewer than 16 frames, giving `short sequence (N frames): weak trajectory` (`FEW_FRAMES_FLAG = 16`). Short
  sequences give a weak trajectory but are still runnable, so they are flagged, not rejected.

### ACCEPT otherwise

An accepted row becomes a `SequenceSpec` with `max_frames` capped to the frames actually available
(`min(max_frames, n_frames)` for real sequences). That spec flows through the pipeline
([guide 01](01_precompute-pipeline.md)).

## 3. How to run your own case

Two ways to feed a row into the contract:

1. **Register it as a case** (recommended, reproducible): add a `Case` to `cases/example_case.py` with your
   `SequenceSpec` and a category, then `python -m lidar3dlab.pipeline <your_case_id>`
   (see [guide 06](06_add-an-engine-or-case.md)). This is how the built-in cases work: the registry rows are
   validated by the same `validate_rows` inside `pipeline.precompute`.
2. **Ad hoc**: construct the row dict (a `case_id`, `source_dir`, and any knobs) and call
   `validate_rows([row])`, then feed the accepted spec through the stages. Useful for one-off external data.

Either way the artifact + manifest come out exactly like a built-in case and replay in the SPA.

## 4. When your data does not fit

If your input is legitimately different (a new frame format, a new sanity rule), **extend CONTRACT 1
deliberately**, and its test (`tests/test_contract.py`), rather than loosening a bound to make bad data pass.
The contract is the honesty boundary: it is meant to reject bad geometry input, not to be widened until
anything passes. Document any change in `data/README.md`.

## 5. Why this makes the product real

Because the gate is explicit and testable, the same engine that baked `oxford` will ingest **your** street
walk or **your** LiDAR run and either produce a real reconstruction or tell you exactly why it will not. That
"applicable to new data, with a stated contract" property is what separates a tool from a canned demo.
