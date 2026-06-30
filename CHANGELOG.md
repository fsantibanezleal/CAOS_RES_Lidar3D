# Changelog

All notable changes to CAOS_RES_Lidar3D. Format: `X.XX.XXX` (per conventions/versioning.md).

## [0.01.000] - 2026-06-29
### Added
- Initial research lab: deep SOTA research (feed-forward 3D reconstruction, LiDAR SLAM, 3DGS + web viz),
  17-paper reference library, and the lingbot-map deep dive.
- Vendored `lingbot-map` (arXiv:2604.14141, Apache-2.0) and validated it runs on the local RTX 4070
  (8 GB) on the real `oxford` sequence (28 frames, 249k-point cloud, 3.21 m path, 7.1 GB VRAM).
- Real streaming backend: `LingbotEngine` drives the model frame-by-frame; FastAPI server streams each
  frame's geometry over a WebSocket. 8 GB-safe config (SDPA, CPU-offload, window=16, bf16).
- Interactive three.js workbench: live point cloud + camera-frustum trajectory + live depth + stats,
  source selector, orbit + controls, light/dark, EN/ES, architecture modal (ADR-0058).
- Screenshot-verified end-to-end (zero JS errors).

### Notes
- Research repo (ADR-0050): local-first, deploy `none`; heavy models/data on E: (never in git).
