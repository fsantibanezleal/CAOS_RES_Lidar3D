# Framework — lingbot-map (the reconstruction engine)

The binding SOTA engine for this product (ADR-0057: the deep research is binding, not decoration). It is
vendored under [`third_party/lingbot-map/`](../../../third_party/lingbot-map/) (Apache-2.0) and actually
called by [`data-pipeline/lidar3dlab/model/lingbot.py`](../../../data-pipeline/lidar3dlab/model/lingbot.py).

## What / why

**lingbot-map** ("Geometric Context Transformer for Streaming 3D Reconstruction", arXiv:2604.14141) is a
feed-forward 3D foundation model: it turns a video stream into per-frame **camera pose + dense metric
depth + a point cloud**, causally, with **no per-scene optimization**, at ~20 FPS over 10k+ frames on a
datacenter GPU. It is the 2026 apex of the *streaming* feed-forward lineage (DUSt3R → VGGT → lingbot-map)
and is **Apache-2.0 on code and weights**, which is why it was chosen over π³/CUT3R (non-commercial weights).

The core is a DINOv2-backed ViT with 24 alternating frame / cross-frame attention blocks, driven by
**Geometric Context Attention**: an anchor context (coordinate frame + metric scale), a pose-reference
window (dense local geometry), and a trajectory memory (6 tokens/frame for long-range drift), served by a
paged KV cache. Full analysis: [`docs/research/lingbot-map-deep-dive.md`](../../research/lingbot-map-deep-dive.md).

## Install (the precompute lane)

```bash
# torch matching the local driver (this host: CUDA 12.6 -> cu126), then the vendored engine (no PyPI dep)
pip install torch==2.8.0 torchvision==0.23.0 --index-url https://download.pytorch.org/whl/cu126
pip install -e third_party/lingbot-map --no-deps          # Apache-2.0, vendored
```
FlashInfer is **not** built here (no CUDA toolkit) — the engine uses its SDPA fallback (`use_sdpa=True`).

## Configure (8 GB-safe, validated on an RTX 4070 Laptop)

`model/lingbot.py` builds `GCTStream` with: `use_sdpa=True`, CPU-offload (`output_device='cpu'`),
`kv_cache_sliding_window=16`, `kv_cache_scale_frames=8`, `camera_num_iterations=1`, bf16 aggregator. Peak
**~7.1 GB**. The per-`SequenceSpec` knobs (`max_frames`, `image_size`, `decimation`, `conf_quantile`)
control the memory/quality trade-off. The checkpoint path is resolved from `LIDAR3D_MODELS_ROOT` (env, never
hardcoded).

## Runnable example

```bash
# offline bake of a real sequence (needs the GPU + the env paths from the vault)
LIDAR3D_MODELS_ROOT=… LIDAR3D_DATA_ROOT=… python -m lidar3dlab.pipeline oxford
# -> data/derived/oxford/{trace.json} + manifests/oxford.json  (193k-pt RGB cloud, 3.13 m, lane=precompute)
```

The model emits `pose_enc` + `depth` + `depth_conf` (no `world_points` key), so the engine unprojects depth
with the self-calibrated intrinsics and the camera-to-world pose itself
([`model/geometry.py`](../../../data-pipeline/lidar3dlab/model/geometry.py)), colouring each point with its
source pixel and filtering by confidence.

## License / honesty

Apache-2.0 (engine). The bundled example sequences ship with the model repo. Reported SOTA numbers
(Oxford-Spires ATE 6.42, ETH3D F1 98.98) are the **paper's**, cited as such; this lab reports only what it
measures on its own hardware (see the Benchmark page).
