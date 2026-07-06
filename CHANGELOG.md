# Changelog

All notable changes to this product. Format: `X.XX.XXX` (display); see `lidar3dlab.__version__`. Keep `0.x`
while on mock/synthetic data. Tag every release.

## [0.13.008] · 2026-07-06

### Fixed
- **RGB-video scenarios reconstructed backwards (#77).** The lingbot engine inverted the decoded pose encoding,
  treating camera-to-world extrinsics as world-to-camera; the camera faced opposite to the walking direction and
  the trajectory was jagged and inflated. Measured on the oxford walk: cos(forward, motion) -0.48 and a 13.9 m
  path before; +0.79 and a smooth 5.5 m path after using the decoded matrices directly. oxford / university /
  loop / courthouse re-baked (+ octrees): forward alignment now +0.79 / +0.86 / +0.89 (courthouse ~0 as expected,
  the camera orbits a facade sideways). First-person verified in-app: the camera looks down the street in the
  walking direction.

## [0.13.007] · 2026-07-06

### Added
- **The LIVE lane is ACTIVE**: `app/` FastAPI now exposes POST `/api/live/reconstruct` (run any registered
  engine on a folder of YOUR frames or a TUM-layout RGB-D root, next to your GPU) and GET `/api/live/health`
  (CUDA + engine detection). End-to-end tested: 30 RGB-D frames reconstruct in ~2.3 s (rgbd-sensor, RTX 4070).

### Changed
- README rewritten to state the real product: the scenario-first App, the measured 5x3 method matrix, the
  two-track framing (Estela is OURS; lingbot-map is the pointmap SOTA reference, not the product core), why
  the public web is replay (engines need CUDA) and how to run live mode, verified-bakes summary (24 cases).
- docs + engine-module + App i18n hints updated: the offline lane bakes with ALL engines (not "the lingbot
  engine"), and the live lane is active with the exact command.

## [0.13.006] · 2026-07-06

### Added
- The 3-method matrix on ALL 5 TUM scenarios: DICP_tum_desk2 / _xyz / _pioneer baked (+ octrees), 24 cases.
- The measured matrix (240 frames, umeyama rigid ATE, metres):
  desk A 0.137 / B 0.041 / ICP 0.063 · office A 0.198 / B 0.077 / ICP 0.041 · desk2 A 0.119 / B 0.016 / ICP 0.075
  · xyz A 0.184 / B 0.025 / ICP 0.020 · pioneer A 0.115 / B 0.039 / ICP 0.128. Track B wins 3/5, depth-ICP 2/5,
  honest per-scenario tradeoffs preserved.

### Changed
- App defaults (Felipe 2026-07-06): point density FULL, point size at a THIRD of the slider range, RGB color
  for every case (LiDAR shows its height ramp under the Height label), and the default method per scenario is
  Track B when available, else Track A, else the remaining method (applies on page load and scenario change);
  surfels is the default renderer.

### Fixed
- Surfels blank on a cold production mount: a late layout pass could clear the drawing buffer after the last
  render; a bounded 3 s warm-up repaint window after data load fixes the first paint (render-on-demand after,
  self-terminating). The disc sprite is also built per WebGL context instead of module-cached (a cached texture
  could hold a handle from a disposed context).

## [0.13.005] · 2026-07-05

### Fixed
- **First-person camera is now the TRUE sensor point of view in every renderer** (Felipe: deck.gl and surfels
  did not keep the real POV). three.js/surfels placed the eye BEHIND the sensor looking at it (a chase-cam);
  now the eye sits AT the frame's camera center looking along its real forward axis. deck.gl orbited a target
  from a fixed angle; now the OrbitView rotation is derived from the camera's actual heading (elevation +
  azimuth from the backward vector, deck's negated orbit sense handled) and the zoom solves the eye distance
  from the canvas height so the eye lands exactly at the sensor center. Potree already used the true POV; all
  four renderers now agree.

## [0.13.004] · 2026-07-05

### Changed
- **No autoplay; land on the full rendered scene.** Selecting a scenario or method now shows the COMPLETE
  reconstruction at 100% immediately (directly comparable across methods); the replay animation and the
  frame scrub are user-initiated only. Removes the on-load auto-replay (which also violated the standing
  no-autoplay rule).
- Cones overlay disabled by default: the first view is the clean cloud (+ the thin trajectory line); every
  overlay is opt-in.

## [0.13.003] · 2026-07-05

### Added
- **Classical depth-only method on RGB-D scenarios** (Felipe: "apply the classic method too, so we can compare
  all outcomes"): new `depth-icp` engine, frame-to-frame point-to-plane ICP on the SENSOR depth alone (no RGB in
  the pose estimation; RGB colors the display only), the same registration the LiDAR-only scenario runs. Cases
  DICP_tum_desk + DICP_tum_office (+ octrees), so the desk and office scenarios now offer the full method matrix:
  Track A (RGB-only, learned) / Track B (RGB + depth, geometric) / classical depth-only ICP (baseline).
- Honest measured comparison on the same frames: desk = Track B 0.034 m beats depth-ICP 0.063; office =
  depth-ICP 0.041 m beats Track B 0.085 (dense ICP absorbs Kinect noise at range better than sparse PnP
  back-projection). Neither dominates; the matrix shows real tradeoffs, not a rigged ladder.

## [0.13.002] · 2026-07-05

### Changed
- **Scenario -> Method model in the App** (Felipe's correction: a scenario is the INPUT DATA; a track is a METHOD
  applied to it). The selector is now "Scenario (input data)" grouped by what was captured (RGB + depth / RGB only /
  LiDAR only / synthetic), and a "Method (what its data supports)" chip row offers every method the scenario's
  data supports: RGB+depth scenarios offer Track A (uses only the RGB) AND Track B (integrates the sensor depth);
  RGB-only scenarios offer Track A alone (Track B not applicable without a sensor); LiDAR-only scenarios run
  classical point-to-plane ICP odometry (no camera, no track); synthetic controls validate the pipeline.

### Added
- Track B baked for the remaining TUM RGB-D scenarios: RGBD_tum_desk2, RGBD_tum_xyz, RGBD_tum_pioneer (+ Potree
  octrees), so every TUM scenario now offers both methods (19 cases total).

## [0.13.001] · 2026-07-05

### Added
- **First-level Track selector in the App** (Felipe's ask: "so I can be sure about what to expect"): chips
  All / Track A · RGB / Track B · RGB-D / LiDAR / Control filter the case list, each with an expectation hint
  (Track A: scale is INFERRED, the hard problem, 0.28 m; Track B: scale is MEASURED by the sensor, 0.024-0.085 m
  with honest holes; LiDAR: laser only, no RGB stream, height-colored map; Control: pipeline validation).
- Case categories restructured into the explicit two-track taxonomy (track A Estela x8, track A pointmap
  reference x4, track B Kinect x2, sensor-only LiDAR, control), carried through manifests, index, and bakes.
- Potree octrees for both RGBD cases (never built) and rebuilt for oxford/university/loop/courthouse/
  LID_synthetic/SYN_orbit whose octrees predated the re-baked traces.

### Fixed
- LiDAR cases: the cloud color chip now says "Height" (the baked colors are a height ramp, there is no camera),
  with an explanatory hint; the depth toggle recolors by camera distance, which looked like a lie when the chip
  said "RGB".

## [0.13.000] · 2026-07-05

### Added
- **Track B: RGB + sensor depth (the two-track model family).** New `rgbd-sensor` engine (SIFT + PnP RANSAC on
  the real Kinect depth, metric by construction, so the monocular-scale blocker disappears at the source) with
  the M-C differentiable windowed pose-graph fusing the metric edges (its first production use; a further 7-26%
  drift cut over the plain chain). Cases `RGBD_tum_office` + `RGBD_tum_desk` mirror the RGB-only `OWN_*` scenes
  for an honest side-by-side: 0.024-0.085 m ATE vs 0.28 m RGB-only. Docs: `docs/models/06_rgbd-track-b.md`.
- The model name **Estela** across the presentation surface (Footer, Benchmark, Methodology, Implementation,
  ArchModal, manifests, README, preprint); the windowed variant is Estela-W.
- Site content for the 2026-07-04 research campaign (EN/ES): model-history rows M-C (Estela-W, fusion -45%
  per-window drift, front-end is the ceiling), EXP (the honest probes: geometric post-processing worsens the
  deployed trajectory; the vendored pointmap ties Estela in shape under Sim(3) but is up-to-scale; the DA-V2
  oracle shows a ~10x ceiling blocked only by the measured monocular scale ambiguity), RGBD (Track B live);
  the Benchmark ladder Track B row; Experiments Track A/B case entries.
- `train/eval_refine_modes.py`: reusable refinement-ladder ATE benchmark (raw / ICP / windowed BA / global PGO).
- 4 engine tests (chain pose-hold, fusion-equals-chain, short-sequence fallback, RGB-D root contract).

### Fixed
- Per-frame panel empty on the lingbot scenes: oxford/university/loop/courthouse re-baked with the current
  engine (49 RGB + 49 depth keyframes; the stale bakes carried 4 depth and 0 RGB).
- LiDAR cases now explain the missing RGB tab ("the sensor is a laser, there is no RGB stream") instead of
  silently hiding it.
- Latent frame double-count in CONTRACT 1 on case-insensitive filesystems (`*.png` + `*.PNG` globbed
  separately); counts deduped by path set, courthouse manifest corrected.
- CONTRACT 1 + preprocess accept a TUM RGB-D sequence ROOT (frames under `rgb/`).

## [0.12.003] · 2026-07-03

### Fixed
- Potree render background did not react to a light/dark theme toggle: its render loop captured the `dark`
  prop at mount, so a toggle only took effect after a reload. Read the theme from a ref updated each render,
  so Potree now matches three.js / surfels / deck.gl on a hot toggle (#43).
- Orbit camera consistency across renderers (#38 follow-up): deck.gl orbited from a mirrored azimuth (it "looked
  the other way"); its `rotationOrbit` is negated vs three.js's, so it now uses -27deg / 22deg to view from the
  same direction as three.js's (0.5,0.45,1). Potree framed the orbit from the padded octree bounding box (larger
  than the cloud, so it looked "from higher up"); it now frames from the actual cloud OBB with three.js's 0.55
  radius factor. All four renderers now share the same orbit orientation and framing.

## [0.12.002] · 2026-07-03

### Fixed
- Coordinate system: the OpenCV-world to render-frame transform `(x,-y,-z)` was duplicated inline in every
  renderer; unified it into `lib/coords.ts` (the single source of truth) consumed by three.js, surfels, Potree
  and deck.gl. The top view differed (three.js/surfels/Potree drew a 45-degree "diamond" from a diagonal camera
  offset, deck.gl was axis-aligned); aligned all four to an axis-aligned top so they match.

### Added
- OBB diagnostic overlay (a **Box (OBB)** toggle): an axis-aligned bounding box of the final cloud plus an RGB
  axis triad, drawn by every renderer from the shared transform, to compare the coordinate frame across them.
- `coords.test.ts`: 14 vitest cases for the transform (mapping, handedness, pose, OBB).

## [0.12.001] · 2026-07-02

### Changed
- Deploy **M8**, the best recovery model: 0.28 m held-out ATE (beats M7's 0.37 m). Re-baked all 8 OWN scenes
  and their Potree octrees with it, for ~2x higher depth confidence and tighter trajectories.

### Added
- `--seqs` training filter to reproduce a specific TUM subset (recovers the winning 5-sequence model).

## [0.12.000] · 2026-07-02

### Added
- Correlation pose head (RAFT/TartanVO-style local cost volume between frame features) as a `--pose_head`
  option, targeting the pose-accuracy bottleneck that global pooling discards; wired through training /
  checkpoint / meta / engine.
- A layer-by-layer architecture reference (encoder/decoder/pose-head shapes, channels, param counts) for both
  backbones; a local usage guide (train → bake → refinement ladder → add-scene → verify) and a datasets page.

### Changed
- Benchmark now reflects reality: OUR depth+pose model is in the ladder (LIVE, ~0.37 m held-out ATE), D1
  loop-closure + TSDF marked IMPLEMENTED. Replaced the template SIR placeholder in `cases/README` with the real
  14 scenarios (8 OWN, 4 held-out). Documents the R1–R5 experiments incl. the correlation-head negative result.

## [0.11.000] · 2026-07-01

### Added
- Bake **8 OWN scenes** (240 frames: TUM ×5 + 7-Scenes ×2 + ICL) with a pretrained **ResNet-18** backbone
  (shared encoder + Siamese pose head), real per-dataset intrinsics, and frame-to-frame point-to-plane **ICP**
  pose refinement (Open3D) for a sharper fused cloud. Rebuilt the index to 14 cases + Potree octrees.
- Deep model documentation (architecture, aleatoric depth, Siamese pose, SE(3), ATE) + full model history
  including negative results, in both the repo and the web Experiments page.

### Fixed
- Preserve the camera across config/mode changes in all renderers (remember + restore the orbit; only re-fit
  on a new case). Potree honours the colour toggle and states it renders the full LOD map.

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
