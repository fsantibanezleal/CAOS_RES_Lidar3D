# Changelog

All notable changes to this product. Format: `X.XX.XXX` (display) — see `lidar3dlab.__version__`. Keep `0.x`
while on mock/synthetic data. Tag every release.

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
