# The live-vs-precompute gate

`data-pipeline/lidar3dlab/core/gate.py :: classify_lane()`. A case runs **live** in the browser (Pyodide) iff —
by MEASUREMENT, never by hand-wave:

- it is **pure-Python**, AND
- its wheels are a subset of the Pyodide-safe set (`LIVE_WHEELS`, e.g. `{numpy}`), AND
- `run_ms ≤ RUN_MS_GATE` (interaction budget), AND
- `trace_bytes ≤ TRACE_BYTES_GATE` (small artifact).

Otherwise the case is **precompute**: the offline pipeline bakes the artifact and the SPA replays it. Either way,
a committed artifact always exists, so the site replays instantly on first paint (ADR-0054).

The verdict + the measured numbers are written into the manifest (`gate` field) and CI fails if `manifest.lane`
disagrees with the gate — so a heavy model can never be mislabeled "live". The EXAMPLE SIR case is pure-Python +
numpy + small ⇒ classified `live`.
