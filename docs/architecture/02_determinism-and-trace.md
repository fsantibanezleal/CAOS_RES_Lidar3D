# Architecture: determinism and the trace artifact

The product's honesty rests on one invariant: **the committed artifact is the source of truth, and the web
only replays it.** For that to mean anything, the artifact has to be reproducible and self-describing. This
document covers the determinism contract, the shape of the trace, and the one place where we deliberately do
not claim determinism (the LiDAR ICP lane).

## A bake is a pure function of (params, seed)

Every reconstruction is driven by a single seeded RNG made in one place: `core/rng.py :: make_rng(seed)`
returns `numpy.random.default_rng(seed)`. No stage, engine, or helper is allowed to touch a global or
implicit RNG; every random draw threads a generator derived from that seed. The synthetic engine seeds its
jitter and its scan sampling from `seed`, and the pipeline's default seed is `42` (`--seed N` overrides it).

Because the inputs are fully captured by `(params, seed)` and nothing else, re-running the same case must
produce the same artifact byte-for-byte for the CPU lanes. This is what makes the committed `trace.json`
trustworthy: it is not a screenshot of one run, it is the run, and anyone with the same seed and params can
regenerate it.

## The manifest carries no wall-clock and no absolute paths

A determinism claim is only credible if re-running does not dirty git on every invocation. Two design rules
enforce that:

- **No wall-clock in the artifact.** The gate measures `run_ms` to make the live-vs-precompute decision, but
  `classify_lane` deliberately does **not** store it (see [03](03_the-gate.md)); the manifest records the
  deterministic *budgets* and the verdict instead. There is no timestamp field anywhere in the trace or
  manifest.
- **No absolute paths.** The manifest records a **source label**, never a path:
  `manifest.build_case_manifest` calls `_source_label(params)`, which returns `"synthetic"` for procedural
  cases or `os.path.basename(source_dir)` (for example `"oxford"`) for real ones. The real sequence folders
  and the checkpoint live outside git under `LIDAR3D_DATA_ROOT` / `LIDAR3D_MODELS_ROOT`; those machine-specific
  strings never enter a committed file. A CI guard greps tracked files for leaked local paths and fails the
  build if it finds one (see [07](07_deploy.md)).

The consequence: two people on two machines, given the same seed and the same input sequence, commit an
identical manifest. There is nothing environment-specific to drift.

## The trace: the web-replay artifact (CONTRACT 2)

`core/trace.py :: build_trace(result, refine_info)` produces the compact JSON the SPA replays. It is a
decimated, RGB-colored world point cloud plus the camera trajectory plus per-frame bookkeeping. Binary arrays
are base64 so the file stays compact and the browser can decode them into typed arrays directly.

```
trace.json  (schema: "lidar3d.recon/v1")
  case_id, n_frames, n_points
  points_b64   : base64 Float32  [n_points * 3]   world XYZ
  colors_b64   : base64 Uint8     [n_points * 3]   RGB 0..255
  poses_b64    : base64 Float32  [n_frames * 12]  camera-to-world, row-major 3x4
  per_frame[]  : { idx, conf_mean, n_points, depth_min, depth_max }
  path_length  : metric trajectory length (m)
  bbox_min, bbox_max
  depth_thumbs[] : a few { idx, png_b64 } keyframes (data:image/png;base64,...)
  refine       : the refine-stage info block
  summary      : { n_points, n_frames, path_length_m }
```

Two details matter for the replay:

- **Ordering preserves the reconstruction.** Points are emitted **ordered by frame**, and the trace carries a
  cumulative `frame_offsets` array (built from the per-frame `n_points`): "how many points have been revealed
  up to and including frame i". That is what lets the frontend animate the cloud building up frame by frame (a
  genuine replay of the reconstruction, not a static dump). Any decimation is done with a **stride**, never a
  shuffle, so the frame ordering survives.
- **A hard point budget.** `MAX_POINTS = 120_000`. If the fused cloud is larger, `build_trace` decimates with
  a stride `ceil(n / MAX_POINTS)` and recomputes the per-frame counts from the kept indices, so `frame_offsets`
  stays consistent with the decimated cloud. This keeps the committed artifact web-sized. (The manifest also
  records the resulting `trace_bytes`; the gate's separate 256 KB budget is about live-lane eligibility, not
  this replay budget, see [03](03_the-gate.md).)

The manifest (`core/manifest.py`, schema `lidar3d.manifest/v1`) wraps the trace with the reproducibility
metadata: the source label, the inference knobs, the seed, the engine + version, the artifact pointer +
byte size, the lane/gate verdict, the CONTRACT-1 flags, the refine info, and the metrics. A flat
`index.json` (schema `lidar3d.index/v1`) inventories every case. Full schemas are in
[08: data contracts](08_data-contracts.md).

## Determinism is enforced, not asserted

- `frontend/src/lib/contract.types.ts` mirrors the trace + manifest shapes; a drift makes `tsc` fail, so the
  web literally cannot ship reading a shape the pipeline does not produce.
- `scripts/check_artifacts.py` (run in CI) verifies index to manifests to artifacts all exist, that each
  artifact's on-disk byte size matches the manifest's recorded `bytes`, and that `manifest.lane == gate.lane`.
  A byte drift or a mislabeled lane fails the build.
- The pipeline smoke in CI regenerates the synthetic case (`python -m lidar3dlab.pipeline SYN_orbit`) and then
  runs the artifact check, so a change that breaks determinism for the CPU lane is caught on every push.

## The LiDAR non-determinism caveat (stated honestly)

We claim determinism for the camera/synthetic CPU lanes. We do **not** claim bit-exact determinism for the
LiDAR ICP lane across bakes. Open3D's registration uses multi-threaded nearest-neighbour and normal
estimation whose reductions are order-sensitive, so `registration_icp` can converge to marginally different
transforms run-to-run on the same input. The synthetic LiDAR scans are seeded (`_synthetic_scans` seeds from
`seed + i` per scan), so the *inputs* are reproducible, but the ICP *solution* is not guaranteed identical to
the last decimal.

This is a deliberate, documented exception rather than a bug we hide. The camera lane, which is the flagship,
remains deterministic; the LiDAR lane is honest about being a real, threaded registration engine. The
manifest still records everything needed to understand and re-run it; it just does not promise the bytes will
match. If exact reproducibility of a LiDAR bake is ever required, pin Open3D to single-threaded execution
before the bake and note it in that case's manifest.

## See also

- [03: the gate](03_the-gate.md): the measured budgets and why `run_ms` is used but not stored.
- [05: the staged pipeline](05_staged-pipeline.md): where the seed threads through each stage.
- [08: the two data contracts](08_data-contracts.md): the full trace + manifest + index schemas and the TS mirror.
