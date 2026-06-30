# docs/ — Lidar 3D documentation wiki

Navigable docs authored as the lab is versioned (ADR-0056). Current state: the **research library**
is complete; the per-theme deep wiki (theory / equations / data-contract / tool-usage) is authored in
Phase 2 alongside the 6-page app.

## Sections

- [`research/`](research/) — **the reference library**: 17 paper PDFs + the four SOTA survey reports
  (feed-forward 3D, LiDAR SLAM, 3DGS + web viz, the lingbot-map deep dive). Start at
  [`research/README.md`](research/README.md).
- `assets/` — figures (the verified workbench screenshots).
- *(Phase 2)* `theory/` — streaming reconstruction formalism (pose/depth/pointmap, the GCT, KV cache).
- *(Phase 2)* `frameworks/lingbot-map/` — how the engine is called, the 8 GB-safe config, gotchas.
- *(Phase 2)* `data/` — the data contract (sources, intrinsics-free input, depth → world unprojection).

## The project dossier (thinking layer)

The figured-out research, proposal and plan live in `_CAOS_MANAGE/wip/lidar3d/` (and graduate to
`_CAOS_MANAGE/plans/lidar3d/`). This repo holds the **code + the committed reference library**.
