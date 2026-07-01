# Architecture: the live-vs-precompute gate

The gate is the mechanism that decides, per case, whether the reconstruction can run **live** in the browser
(Pyodide) or must be **precomputed** offline and replayed. For Lidar 3D the answer is always the same,
`precompute`, but the point of the gate is that this verdict is a **measurement written into the manifest and
checked by CI**, not a hand-wave. A heavy model can never be mislabeled "live", and the record of *why* it is
precompute travels with every case.

Source: `data-pipeline/lidar3dlab/core/gate.py :: classify_lane()`. Binding decision: ADR-0054.

## The rule

A case runs **live** if and only if all four conditions hold:

1. it is **pure-Python** (`pure_python=True`), AND
2. its wheels are a subset of the Pyodide-safe set `LIVE_WHEELS = {"numpy"}`, AND
3. its runtime is within the interaction budget: `run_ms <= RUN_MS_GATE` (`1500.0` ms), AND
4. its artifact is small: `trace_bytes <= TRACE_BYTES_GATE` (`256 * 1024` = 262144 bytes).

If any condition fails, the case is **precompute**: the offline pipeline bakes the artifact and the SPA
replays it. `classify_lane` accumulates a human-readable `reasons[]` list for every failed condition, so the
manifest says exactly why. Either way a committed artifact always exists, so the site replays instantly on
first paint (that is the ADR-0054 guarantee: replay is always the fallback).

```python
classify_lane(pure_python=..., wheels=..., run_ms=..., trace_bytes=...) -> {
    "lane": "live" | "precompute",
    "pure_python": bool,
    "wheels": sorted(wheels),
    "trace_bytes": int,
    "run_ms_budget": 1500.0,
    "trace_bytes_budget": 262144,
    "reasons": [ ... ],       # one string per failed condition
}
```

## Why every Lidar 3D case is precompute

The verdict is set in `stages/export.py`, which calls `classify_lane` with the real facts of each engine:

- **Camera (`lingbot-map`) cases.** `pure_python=False`; wheels `{"torch", "numpy", "matplotlib", "pillow",
  "opencv-python"}`. Three of the four conditions fail immediately (not pure-Python; wheels not Pyodide-safe;
  and the model needs a CUDA GPU + a 4.6 GB checkpoint that could never load in WASM). A real bake also blows
  the 256 KB budget: the `oxford` trace is ~2.85 MB. So it is precompute, and the manifest's `reasons` records
  "not pure-python", the offending wheels, the runtime over budget, and the byte overflow.
- **Synthetic cases.** Still `pure_python=False` with wheels `{"numpy", "matplotlib", "pillow"}`. Even though
  the synthetic engine runs in milliseconds on CPU, **matplotlib is not Pyodide-safe** (it is used for the
  depth-thumbnail PNGs and the height colormap), so the wheel-subset check fails and the case is precompute.
  This is why the synthetic engine, though light, still does not qualify as a browser-live lane.
- **LiDAR cases.** `pure_python=False`; the engine imports Open3D (native). Precompute.

This is the deliberate asymmetry with the lighter CAOS labs (SimLab, PINN-Lab), which ship a genuine
Pyodide/WASM live engine because their compute is numpy-only and small. Lidar 3D's engine is a ~1B-parameter
ViT, so the browser-live lane is simply not applicable. `lidar3dlab/live.py` is a one-line marker recording
that; do not add a Pyodide engine there. The real-time "live" lane for this product is the dormant local-GPU
FastAPI in `app/`, not the browser (see [04](04_lanes.md)).

## The budgets, and why run_ms is measured but not stored

`RUN_MS_GATE` (1500 ms) is an interaction budget: a live browser recompute has to feel instant, so anything
slower is precompute regardless of the other checks. `TRACE_BYTES_GATE` (256 KB) is the payload a live/replay
step is allowed to hand the renderer per interaction.

The pipeline measures the real offline `run_ms` (in `pipeline.precompute`, wrapping the stages with
`time.perf_counter`) and passes it to the gate for the **decision**. But `classify_lane` intentionally does
**not** put `run_ms` in its output. The reason is the determinism contract ([02](02_determinism-and-trace.md)):
the committed manifest must be a pure function of `(params, seed)`, and a wall-clock number would change on
every re-run and dirty git. So the manifest stores the *deterministic budgets* and the *verdict*, and the
actual live runtime, when a live lane exists, is measured separately in the browser at run time.

Note the two byte thresholds are different things: the gate's 256 KB `TRACE_BYTES_GATE` gates **live
eligibility**, while `core/trace.py`'s 120,000-point / larger-file budget gates the **replay artifact size**.
A precompute case can (and does) ship a multi-megabyte trace for replay while still being correctly classified
precompute; it just fails the live budget, which is exactly the intent.

## Enforcement

The verdict is not advisory. `scripts/check_artifacts.py` (run in CI) fails if `manifest.gate.lane` disagrees
with `manifest.lane` for any case. Combined with the byte-size check, this means the manifest cannot claim a
lane the gate did not assign, and cannot point at an artifact whose size does not match. The gate is a
measurement with teeth.

## See also

- [02: determinism and the trace](02_determinism-and-trace.md): why `run_ms` is used but not stored.
- [04: the lanes](04_lanes.md): what offline / replay / live actually are for this product.
- [06: model evaluation](06_model-evaluation.md): the other place "measured, not claimed" is load-bearing.
