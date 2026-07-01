# Changelog

All notable changes to this product. Format: `X.XX.XXX` (display); see `lidar3dlab.__version__`. Keep `0.x`
while on mock/synthetic data. Tag every release.

## [0.06.000] · 2026-07-01

### Added (OUR own trainable model + model-agnostic engine + a real training surface)
- **model-agnostic engine registry** (`model/agnostic.py`): every reconstructor runs behind one contract
  (control / classical / SOTA-reference / OURS); the App selects the model, the pipeline honors `spec.engine`
  end-to-end (fixed a bug where CONTRACT 1 dropped it, so every case silently ran the vendored SOTA).
- **OUR own from-scratch depth+pose model** (`model/nets/own_depthpose.py`, 2.2M params: UNet metric depth +
  learned aleatoric confidence + PoseNet with our own se(3) exp), **trained on the GPU** on real TUM RGB-D
  (`train/`), ~0.2 m held-out ATE; served behind the agnostic contract (`model/own_engine.py`). Not vendored.
- **OUR own geometry** (`model/geom.py`), unit-tested against a ground-truth cube so the "reconstruction built
  behind the camera" bug is provably impossible.
- Downloaded 5 TUM RGB-D sequences (~9.9k RGB-D frames + GT) to the scratch volume for training/exploration.

### Added (App viewer + per-frame panel)
- Camera modes: orbit / first-person (follows the player) / top. `logarithmicDepthBuffer` + scene-scaled
  near/far so points DO NOT vanish when zooming to point level.
- Per-frame Depth (+ RGB when the engine emits it) view that FOLLOWS the player (no separate slider); stats
  moved to the right panel.

### Fixed (ADR compliance)
- References are now per-section `<Refs>` with inline linked `<Cite>` (ADR-0017 §4); removed the banned
  bottom-of-page bibliography dump.
- The architecture button is the ⓘ icon only; layout no longer overflows below the footer; synthetic camera
  moves into what it images (was translating backward).

## [0.05.000] · 2026-06-30

### Added (ADR compliance + deep content: header/footer/modal + tabbed pages)
- **Header** now uses real SVG icons (GitHub, personal site, portfolio, architecture, theme) instead of glyph
  word-links, and shows the app version; **footer** shows the version too (ADR-0016).
- **Architecture modal** (ADR-0058): the ASCII lane sketch is replaced by a high-quality, theme-aware SVG of
  the three lanes and the data flow. New reusable `Diagrams.tsx` (lanes, the GCT network, the attention
  context) and an `Icons.tsx` SVG set.
- **Every content page is now tabbed and deep** (ADR-0016): sub-tabs, KaTeX equations, inline citations, and a
  shared bibliography (`References.tsx`, 25 sourced refs).
  - Methodology: State of the art (the DUSt3R to VGGT to lingbot-map lineage, per-method table), Networks (the
    frozen DINOv2 backbone, the 24 alternating blocks, the heads, with the GCT diagram), Geometric Context (the
    three-tier attention with the token-count argument and diagram), and Geometry (SE(3) pose, the boxed
    depth-to-world unprojection, the LiDAR ICP objective).
  - Benchmark: results per model as a ladder (classical ICP / KISS-ICP, SOTA lingbot-map, novel D1 to D3) plus
    the reported per-model ATE table and this lab measured numbers, honestly labelled.
  - Introduction, Implementation, Experiments (with the D1 to D5 novel agenda) reworked into sub-tabs.

### Fixed
- Removed em-dash separators and prose arrows across the frontend (a stray template `architecture.ts.txt`,
  two code comments, the empty-value markers) to match the house style.

## [0.04.000] · 2026-06-30

### Added (App workbench: replay the reconstruction + viewer controls)
- **Replay**: each case auto-plays the reconstruction building up frame by frame (the streaming process
  generating), with a Replay button + a scrub slider. It runs a single pass then stops and pauses on a hidden
  tab (no idle CPU). Backed by a new `frame_offsets` field in the trace (CONTRACT 2): the cumulative point
  count per frame, so the web reveals points in exact frame order.
- **Point-density control**: a slider that starts LOW (fewer drawn points for a fluid first load) and rises to
  full detail; it resets to low on reload so the page never opens under heavy load. Each user raises it as far
  as their machine handles.
- **Color mode**: a toggle between RGB (camera texture) and a LiDAR height ramp; it defaults to the ramp for
  LiDAR cases (no camera) and to RGB for camera cases.

### Fixed
- `trace.py` now actually emits `frame_offsets` (it was computed then dropped from the returned dict); when
  per-frame provenance is inconsistent it falls back to an even per-frame split (points are still in frame order).
- Viewer first paint: `preserveDrawingBuffer` + a `ResizeObserver` so a settled static frame stays painted
  instead of compositing blank.

## [0.03.000] · 2026-06-30

### Added (the LiDAR modality — makes "Lidar 3D" honest, a second real engine)
- `model/lidar.py`: a **LiDAR odometry engine** (Open3D point-to-plane ICP) that registers LiDAR scans
  frame-to-frame and accumulates a height-colored map + trajectory. KISS-ICP (SOTA LiDAR-only odometry) is
  pinned and swappable behind the same interface. Synthetic scans (CI-safe) + a real-scan path
  (`.bin/.npy/.ply`, resolved via `LIDAR3D_DATA_ROOT`).
- `SequenceSpec.modality` (`camera` | `lidar`); `infer` dispatches on it; new cases `LID_synthetic` (CPU/CI)
  + `kitti_lidar` (real-data hook). Verified: `LID_synthetic` = 72k-pt ICP-registered map, 30 scans, ~5 m.
- `refine` now runs Open3D (voxel + outlier + normals) when available (cleaner cloud; mesh-ready).
- Pinned `open3d` + `kiss-icp` in the precompute requirements; engine label is modality-aware. Screenshot-verified.

## [0.02.000] · 2026-06-30

### Changed (rebuild from the template, replacing the non-compliant first build)
- Replaced the EXAMPLE SIR engine with the real product: the **lingbot-map** streaming reconstruction engine
  (arXiv:2604.14141, vendored Apache-2.0) wired into the frozen staged pipeline, plus a synthetic CPU engine
  for CI. Stage names + both data contracts kept.
- `io/schema` (`SequenceSpec`, `ReconResult`) + `io/contract` (RGB-sequence ingestion gate); `config`
  resolves the model/data roots from the **environment** (no personal paths versioned; the API never returns
  an absolute path).
- New `refine` stage (the texture/color layer); `train` is a documented dormant no-op (pretrained engine).
- CONTRACT 2 trace = a compact base64 RGB-colored point cloud + camera trajectory + depth thumbnails.

### Added
- Frontend (ADR-0016 + ADR-0058): a 6-page React/Vite shell with a **three.js RGB point-cloud viewer**
  (color/texture, not a bare LiDAR map), camera-frustum trajectory, per-frame depth, EN/ES, light/dark, the
  ⓘ architecture modal, and KaTeX content. Screenshot-verified.
- Cases: `SYN_orbit` (CPU/CI) + `oxford/university/loop/courthouse` (real, GPU-baked); `docs/frameworks/lingbot-map`.
- Tests + CI adapted (the synthetic case is the smoke); the CONTRACT-2 + base-integrity guards stay.

### Verified
- `SYN_orbit` bakes on CPU (deterministic); `oxford` = 193k-pt RGB cloud, 3.13 m, lane=precompute, ~7.1 GB peak.
- ruff clean, pytest green, frontend builds (tsc + vite), 5 cases manifest-to-artifact consistent.

## [0.01.000] — 2026-06-20

### Added
- Initial instantiation from the CAOS product-repo template (ADR-0057).
- Offline `data-pipeline/` (`lidar3dlab`): the two data contracts (ingestion + artifact), the named staged
  pipeline (preprocess → feature_extraction → train → infer → evaluate → export), the seeded RNG, the compact
  trace, the manifest, and the measured live-vs-precompute gate.
- EXAMPLE engine: a deterministic SIR epidemic (numpy-only, Pyodide-safe) — **replace with the product's
  research-chosen SOTA engine**.
- Cases-by-category registry (4 regimes + 1 degenerate control); a live-lane entrypoint (`live.py`); tests for
  both contracts + pipeline determinism.
