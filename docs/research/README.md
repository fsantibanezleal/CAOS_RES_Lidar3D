# Research library — Lidar 3D

The committed paper + report library (ADR-0050: PDFs are a first-class backup in a private repo).

## Survey reports (authored 2026-06-29)

| Report | Scope |
|---|---|
| [`feedforward-3d-foundation-models.md`](feedforward-3d-foundation-models.md) | The pointmap lineage DUSt3R→VGGT→π³→MapAnything→lingbot-map (17 methods, benchmarks, weights, licenses). |
| [`lidar-slam-and-perception.md`](lidar-slam-and-perception.md) | LiDAR odometry/SLAM (KISS-ICP, FAST-LIO…), perception (PTv3, SphereFormer), foundation (Sonata), datasets. |
| [`gaussian-splatting-slam-and-web-viz.md`](gaussian-splatting-slam-and-web-viz.md) | 3DGS/NeRF SLAM (SplaTAM, MonoGS…), the web viewer stack (viser / three.js / Spark / Potree), datasets. |
| [`lingbot-map-deep-dive.md`](lingbot-map-deep-dive.md) | Full analysis of the seed engine (architecture, results, run recipe, gaps). |

## Paper PDFs (`papers/`)

17 arXiv PDFs (~274 MB). Key ones: `2604.14141` (lingbot-map, seed), `2503.11651` (VGGT),
`2507.13347` (π³), `2509.13414` (MapAnything), `2511.10647` (Depth Anything 3), `2501.12387` (CUT3R),
`2507.11539` (StreamVGGT), plus DUSt3R/MASt3R(-SLAM)/Spann3R/Fast3R/MoGe-2/LONG3R/VGGT-Long/AMB3R and a
feed-forward survey. Re-fetch with `bash papers/_download_papers.sh`.

> The full SOTA *synthesis* + engineering decisions (engine roster, web stack, novel agenda) live in
> the project dossier `_CAOS_MANAGE/wip/lidar3d/sota-synthesis-2026-06-29.md`.
