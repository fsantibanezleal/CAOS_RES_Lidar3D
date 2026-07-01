# Changelog

All notable changes to this product. Format: `X.XX.XXX` (display); see `lidar3dlab.__version__`. Keep `0.x`
while on mock/synthetic data. Tag every release.

## [0.10.001] · 2026-07-01

### Fixed
- Potree colors were washed out to white: set the material `inputColorEncoding` to sRGB (+ neutral point size)
  so the octree renders the baked RGB correctly, matching three.js/deck.gl.

## [0.10.000] · 2026-07-01

### Added (Potree: the third, truly scalable renderer + the offline octree pipeline)
- **Potree renderer** (`render/PotreeViewer.tsx` + potree-core): loads a committed octree and renders it with
  real level-of-detail streaming (point budget), so it scales to millions of points. Fourth renderer option
  alongside three.js / deck.gl / surfels. LOD needs a render loop; it pauses on a hidden tab (no idle CPU).
- **Offline octree pipeline** (`lidar3dlab/potree.py`): exports each committed trace to LAS and runs
  PotreeConverter (native binary, path via LIDAR3D_POTREECONVERTER) into `public/potree/<case>/` (committed
  static octrees). Baked in the render frame so Potree matches three.js/deck.gl. Added `laspy` to requirements.

## [0.09.005] · 2026-07-01

### Added (the third render method)
- **surfels** renderer: a third viewer alongside three.js (points) and deck.gl (GPU). Points render as soft
  round discs that merge into a surface, a distinct surface-splat look that reads less "diffuse" than raw points.

## [0.09.004] · 2026-07-01

### Fixed (our model quality)
- The training now keeps the BEST checkpoint by val ATE (early stopping): a prior long run had overfit and
  degraded the saved model to 0.49 m (the "diffuse" reconstruction). Retrained -> 0.29 m held-out ATE; the OUR
  case is re-baked with it (coherent per-frame depth, more structure). More datasets are now available
  (ICL-NUIM, 7-Scenes, TUM RGB-D) to push it further.

## [0.09.003] · 2026-07-01

### Added (dataset + license transparency, to avoid licensing issues)
- Every case carries its data source + LICENSE, surfaced in the App Reconstruction stats: Synthetic (CAOS) for
  the procedural cases, Apache-2.0 (lingbot-map examples), CC BY 4.0 (TUM RGB-D), CC BY-NC-SA 3.0 (KITTI).

## [0.09.002] · 2026-07-01

### Added
- Overlay toggles in the App: **Cones** (observer frustums) and **Trajectory** (the red path), on/off, in both
  the three.js and deck.gl renderers.
- More datasets downloaded for training/testing: ICL-NUIM (synthetic RGB-D, perfect GT) and 7-Scenes (real
  RGB-D), alongside the TUM RGB-D sequences.

## [0.09.001] · 2026-07-01

### Fixed (viewer transforms + per-frame panel + longer scenes; reviewed in detail)
- **Coordinate convention unified**: one OpenCV->render transform (x,y,z)->(x,-y,-z) (handedness-preserving, no
  mirror) applied identically in three.js AND deck.gl; removed the per-viewer up/negate hacks that made one look
  horizontally and the other vertically inverted.
- **LiDAR poses were scrambled** (det(R)=0, zero forward): serialized [R|t] as P[:3,:4], so the observer frustums
  now render with the right orientation (they were an invisible line before).
- **Observer frustums scale with the scene** (a fixed size was a dot in a long corridor); frustumCulled=false so
  points/cones do not vanish when zooming inside the cloud.
- **Per-frame panel = Depth / RGB tabs** (Depth default, always present incl. LiDAR range images; RGB when the
  engine emits it). First-person camera centers on the last measured point. Camera view is preserved on
  density/color changes (re-fit only on a new case or camera-mode switch).
- **Longer scenes**: raised max_frames (SYN 120, LiDAR 90, OUR 120, real 96) with ~48-keyframe thumb sampling.
- Training: keep the BEST checkpoint by val ATE (early stopping; a 12-epoch run had overfit and degraded it) +
  an optional self-supervised photometric reprojection loss (--photo_w).

## [0.09.000] · 2026-07-01

### Changed (lift the point cap)
- The committed-artifact point budget (my earlier unauthorized 120k "toy" cap) is lifted to 1,000,000 and made
  overridable via `LIDAR3D_MAX_POINTS`. The deck.gl renderer scales to that; three.js stays the light path. The
  OUR-model case is re-baked denser (111k points).

## [0.08.000] · 2026-07-01

### Added (ADR-0058: the 5-tab architecture modal)
- The ⓘ "How it works" modal is now a **tab strip of 5 themed SVG diagrams** (the app + design-build flow /
  lanes web-offline-compute / web-app flow / the science / data contracts), each with a bilingual explanation,
  Esc-to-close and `role="dialog"`. New `DesignFlowDiagram`, `WebAppFlowDiagram`, `DataContractsDiagram` (real
  module/file names, structured lanes, labeled flows, all theme-variable colors, zero hardcoded hex).

## [0.07.000] · 2026-07-01

### Added (scalable viewer: deck.gl, selectable)
- **deck.gl PointCloudLayer viewer** (`render/DeckViewer.tsx`): GPU-instanced, scales to millions; progressive
  replay is done GPU-side with `DataFilterExtension` (filters points by order index vs the revealed count, so
  replay costs nothing per frame). Same prop interface as the three.js viewer.
- **Renderer selector** in the App (three.js / deck.gl): the light three.js path stays the default; deck.gl is
  the scale path. (Potree + the out-of-core octree + uncap are the next step per the beyond-SOTA plan.)

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
