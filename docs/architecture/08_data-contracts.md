# Architecture: the two data contracts

A product is only real if data flows through two **enforced** contracts: one governing what may enter the
pipeline, and one governing what the web is allowed to read. Both are checked (in CI and by the TypeScript
compiler). Without CONTRACT 1 the app is a demo that can only replay canned cases; without CONTRACT 2 the web
can silently drift from what the pipeline produced. The contracts are the seams that make Lidar 3D a tool
rather than a slideshow.

---

## CONTRACT 1: ingestion (raw to pipeline), the bring-your-own-data gate

Source: `data-pipeline/lidar3dlab/io/contract.py` (+ the `SequenceSpec` schema in `io/schema.py`). This is
what lets the product be pointed at NEW footage instead of only replaying baked cases.

### What a valid input is

A reconstruction input is an **ordered folder of RGB frames** (intrinsics-free) plus the inference knobs, or a
folder of LiDAR scans for the LiDAR modality, described by a `SequenceSpec`. In practice a batch of sequences
is a CSV/list of rows with at least `case_id` and `source_dir`. `validate_rows(raw_rows)` applies the contract
row by row and returns a `ContractReport(accepted, rejected, flagged)`.

### The `SequenceSpec` (one validated operating point)

| Field | Default | Meaning |
|---|---|---|
| `case_id` | (required) | the case identifier |
| `source_dir` | (required) | folder of ordered RGB frames (png/jpg), or LiDAR scans |
| `n_frames` | (from source) | frames available in the source |
| `max_frames` | 64 | frames processed (8 GB-safe cap) |
| `image_size` | 518 | working resolution (loader handles the patch-14 multiple) |
| `kv_window` | 16 | lingbot sliding KV window (8 GB-safe) |
| `scale_frames` | 8 | the anchor / scale block size |
| `camera_iters` | 1 | camera-head refinement steps (1 = faster) |
| `decimation` | 6 | keep every Nth pixel for the committed cloud |
| `conf_quantile` | 0.30 | drop the lowest-confidence fraction of pixels |
| `synthetic` | False | a procedural CPU case (CI-safe; no GPU/model) |
| `modality` | "camera" | "camera" (lingbot / synthetic) or "lidar" (ICP odometry on scans) |

### The explicit policy: accept / reject-with-reason / flag

A sequence is **accepted** iff it passes; a bad one is **rejected with a reason** (never silently coerced); a
plausible-but-suspicious one is **flagged** (accepted, and the flag is recorded in the manifest). The
mechanics:

- **Required columns.** Missing/empty `case_id` or `source_dir` to reject
  (`"missing/empty columns: [...]"`).
- **Frame-count bounds (real, non-synthetic).** `source_dir` must exist (else reject `"source_dir not
  found"`). `MIN_FRAMES = 8` (need at least the anchor/scale block) to reject if fewer. `MAX_FRAMES_HARD =
  20_000` (beyond the model's training range) to reject if more, with the advice to use windowed mode + a
  different case.
- **Numeric-knob ranges** (`RANGES`): each of `max_frames` (8..2000), `image_size` (140..1036), `decimation`
  (1..32), `conf_quantile` (0.0..0.95) must be finite and in range; a NaN or out-of-range value to reject
  (`"<name>=<v> out of [lo,hi]"`). The check `if v != v or not (lo <= v <= hi)` rejects NaN correctly (a NaN is
  never `>=` anything), a specific guard against silently accepting a bad number.
- **Flag, not reject.** `FEW_FRAMES_FLAG = 16`: a real sequence shorter than 16 frames is accepted but
  flagged `"short sequence (N frames): weak trajectory"`, because it will give a weak trajectory without being
  invalid.
- **Synthetic bypass.** Synthetic procedural cases skip the on-disk frame checks (there is no folder to read);
  `n_frames` comes from the knobs.

`ContractReport.ok` is true iff at least one sequence was accepted; `precompute` returns `{"skipped": True,
"reason": rejected}` for a case that fails, so a bad input never reaches the engine. The full range table is
documented in `data/README.md`.

### Why this is the "bring-your-own-data" gate

Because the policy is explicit and mechanical, a third party can point the pipeline at their own sequences: a
valid folder is accepted and reconstructed, a bad one comes back with a precise reason, a marginal one is
processed but flagged. That is the difference between a tool and a fixed demo.

---

## CONTRACT 2: artifact (pipeline to web)

Source: `data-pipeline/lidar3dlab/core/{trace.py, manifest.py}`, written by `stages/export.py`. Every run
produces a compact trace + a manifest; a flat `index.json` inventories every case. The web loads **only** these.

### The trace (`lidar3d.recon/v1`)

The decimated, RGB-colored world point cloud + camera trajectory + per-frame bookkeeping. Binary arrays are
base64 (Float32 xyz, Uint8 rgb, Float32 poses) to stay compact; a hard `MAX_POINTS = 120_000` budget applies
(stride-decimated, order preserved). Points are ordered by frame with cumulative `frame_offsets` so the web
can replay the build-up. Full shape and the ordering/decimation rules are in
[02: determinism and the trace](02_determinism-and-trace.md).

### The manifest (`lidar3d.manifest/v1`)

The authoritative, versioned record of a baked case. `build_case_manifest` produces (a pure function of
`(params, seed)`, no wall-clock, no absolute path):

```
{
  schema: "lidar3d.manifest/v1",
  case_id, category, real_or_synthetic, expected_band,
  engine: { package, version, model, pretrained },
  params: { source,              # a LABEL ("synthetic" or a sequence name), never a path
            n_frames, max_frames, image_size, kv_window, scale_frames, decimation, conf_quantile },
  seed,
  artifact: { path, format: "json", trace_schema: "lidar3d.recon/v1", bytes },
  lane: "precompute",            # here, always
  gate: { lane, pure_python, wheels[], trace_bytes, run_ms_budget, trace_bytes_budget, reasons[] },
  flags: [ ... ],                # the CONTRACT-1 flags for this case
  refine: { refined, method?, voxel?, n_in?, n_out?, mesh_ready?, reason? },
  metrics: { n_points, n_frames, path_length_m, bbox_extent_m, mean_conf,
             ate_m: null, rpe_trans: null, rpe_rot: null, gt: "none ...", n_quality_frames }
}
```

### The index (`lidar3d.index/v1`)

```
{ schema: "lidar3d.index/v1", engine_version, n_cases, cases: [ { case_id, category, manifest_path } ] }
```

`build_index` sorts the cases by id, so the inventory is stable.

### The outlier / flag policy travels into CONTRACT 2

The CONTRACT-1 verdict is not lost after ingestion: `rep.flagged` is threaded through `precompute` to
`export.run` and stored in the manifest's `flags` field. So a case that was accepted-but-flagged (for example
a short sequence) carries that flag in its committed manifest, and the web can surface it. The two contracts
are joined, not separate silos.

---

## Enforcement: the TypeScript mirror and the CI check

CONTRACT 2 is enforced at **two** independent points:

1. **Build-time type check.** `frontend/src/lib/contract.types.ts` mirrors the trace + manifest + index
   shapes exactly (`PerFrame`, `DepthThumb`, `RefineInfo`, `TraceSummary`, `Trace`, `ArtifactRef`,
   `GateVerdict`, `EngineInfo`, `CaseManifest`, `CaseIndexEntry`, `CaseIndex`, plus the `b64ToF32` / `b64ToU8`
   decoders). If the Python schema and the TS interface drift, `tsc` fails and the SPA cannot build. The web
   literally cannot ship reading a shape the pipeline does not produce. The file header states this is the
   whole point of the mirror.

2. **CI drift guard.** `scripts/check_artifacts.py` (stdlib only, so it runs in CI without installing the
   package) verifies: `index.json` exists and references every case; each manifest exists; each artifact
   exists and is non-empty; each artifact's on-disk byte size **matches** the manifest's recorded `bytes`; and
   `manifest.gate.lane == manifest.lane`. Any mismatch prints `CONTRACT 2 DRIFT:` with the offending entries
   and exits non-zero. This is wired into `ci.yml` and `scripts/smoke.*`.

The two together mean the web reads only what the pipeline produced, the shapes cannot silently diverge, and a
mislabeled lane or a stale artifact fails the build.

## Why this matters

- Without CONTRACT 1, the app cannot be applied to new data: it becomes a canned demo.
- Without CONTRACT 2 (and its enforcement), the web can drift from the pipeline and start showing something the
  engine never produced.

These are the seams that make the product real. Everything the SPA renders came through them.

## See also

- [02: determinism and the trace](02_determinism-and-trace.md): the trace shape, the point budget, the ordering.
- [03: the gate](03_the-gate.md): the `gate` block inside the manifest.
- [05: the staged pipeline](05_staged-pipeline.md): where ingestion runs and where export writes CONTRACT 2.
- `data/README.md`: the full CONTRACT-1 range table.
