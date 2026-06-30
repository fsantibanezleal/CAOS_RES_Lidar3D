# References (paper library)

The paper PDFs are **not committed** (kept lean for the public repo; they are public arXiv documents). Fetch
them on demand into `docs/research/papers/` with:

```bash
bash docs/research/papers/_download_papers.sh
```

## Core lineage (feed-forward 3D reconstruction)

| Method | arXiv | Note |
|---|---|---|
| **lingbot-map** (seed engine) | [2604.14141](https://arxiv.org/abs/2604.14141) | Geometric Context Transformer, streaming SLAM, Apache-2.0 |
| VGGT (CVPR'25 best paper) | [2503.11651](https://arxiv.org/abs/2503.11651) | all 3D attributes in one pass |
| DUSt3R | [2312.14132](https://arxiv.org/abs/2312.14132) | pairwise pointmap regression |
| MASt3R / MASt3R-SLAM | [2406.09756](https://arxiv.org/abs/2406.09756) / [2412.12392](https://arxiv.org/abs/2412.12392) | metric matching; real-time SLAM |
| CUT3R · StreamVGGT · Spann3R | [2501.12387](https://arxiv.org/abs/2501.12387) · [2507.11539](https://arxiv.org/abs/2507.11539) · [2408.16061](https://arxiv.org/abs/2408.16061) | streaming/online |
| π³ · MapAnything · MoGe-2 · Depth Anything 3 | [2507.13347](https://arxiv.org/abs/2507.13347) · [2509.13414](https://arxiv.org/abs/2509.13414) · [2507.02546](https://arxiv.org/abs/2507.02546) · [2511.10647](https://arxiv.org/abs/2511.10647) | reference-free / metric / monocular / multi-size |

## LiDAR + neural rendering (the other modalities)

KISS-ICP (LiDAR odometry) · Open3D (registration) · SplaTAM / MonoGS (Gaussian SLAM) · 3DGS / gsplat. Full
surveys: [`feedforward-3d-foundation-models.md`](feedforward-3d-foundation-models.md),
[`lidar-slam-and-perception.md`](lidar-slam-and-perception.md),
[`gaussian-splatting-slam-and-web-viz.md`](gaussian-splatting-slam-and-web-viz.md).
