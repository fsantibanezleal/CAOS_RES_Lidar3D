# 03 · The GPU lane (the 8 GB-safe config)

The real camera engine, lingbot-map, is a ~1B-parameter DINOv2 ViT with a 4.6 GB checkpoint and needs a CUDA
GPU. This guide is the exact, validated configuration that runs it on an **8 GB** card (RTX 4070 Laptop,
verified 2026-06-29, peak **~7.1 GB**), the meaning of every knob, the memory/quality trade-off, and the
FlashInfer-vs-SDPA note. The synthetic and LiDAR lanes need none of this (CPU only).

---

## 1. The problem it solves

Upstream defaults are datacenter-sized: window $k=64$ needs **~13.28 GB** VRAM, and full-causal attention
needs **~36 GB** (`docs/research/lingbot-map-deep-dive.md` §6). To fit 8 GB you must shrink the window,
offload to CPU, drop precision to bf16, and use the dependency-free SDPA attention backend. The lab wires all
of this in `data-pipeline/lidar3dlab/model/lingbot.py`.

## 2. The exact knobs

Set on the `GCTStream` and in the streaming call (`lingbot.py:reconstruct`). Defaults for the real cases come
from `SequenceSpec` (`io/schema.py`).

| Knob | 8 GB value | Where | Effect |
|---|---|---|---|
| `use_sdpa` | **True** | `GCTStream(use_sdpa=True)` | use `torch.nn.functional.scaled_dot_product_attention` with a dict KV cache instead of FlashInfer paged kernels. No `nvcc`/build needed. Slower, numerically equivalent. |
| `kv_cache_sliding_window` | **16** | `kv_window` in `SequenceSpec` (default 16) | keep only the 16 most recent frames at full image-token resolution ([theory 02 §4.2](../theory/02_geometric-context-transformer.md#42-pose-reference-window-dense-geometric-cues)). Dominant VRAM lever. |
| `kv_cache_scale_frames` | **8** | `scale_frames` (default 8) | the anchor/scale block kept resident forever (grounds the world frame + metric scale). |
| `camera_num_iterations` | **1** | `camera_iters` (default 1) | camera-head refinement steps; 1 = fastest (upstream default 4). |
| dtype | **bf16** | computed in `reconstruct` | `bfloat16` when the GPU is SM80+; halves activation memory. Falls back to fp32 on older GPUs / CPU. |
| CPU offload | **on** | `inference_streaming(output_device=cpu)` | per-frame predictions are moved to CPU as they are produced, so peak GPU memory is O(scale)+O(1) frames, not O(S). Images can also live on CPU and be sliced-then-moved per frame. |
| `image_size` | 518 (or lower) | `image_size` (default 518) | working resolution; lower ⇒ fewer patch tokens ⇒ less memory (fewer points too). |
| `PYTORCH_CUDA_ALLOC_CONF` | `expandable_segments:True` | set at import in `lingbot.py` | reduces allocator fragmentation on long runs. |

Baking parameters that shape the committed artifact (not VRAM): `decimation` (keep every Nth pixel, default 6
for real cases; smaller cloud), `conf_quantile` (drop the lowest-confidence fraction, default 0.30,
[theory 03 §6](../theory/03_pointmaps-and-geometry.md#6-confidence-filtering-and-fusion)), `max_frames` (cap
processed, default 48 for the real cases).

## 3. The memory / quality trade-off

Every knob that saves memory costs something:

- **Smaller `kv_window`** (64 down to 16): the biggest saving, but a shorter pose-reference window means fewer
  full-resolution recent frames for correspondence, so local pose/depth accuracy is somewhat lower than the
  paper's datacenter numbers. The anchor + 6-token trajectory memory still give global grounding.
- **`camera_num_iterations=1`**: faster, slightly less pose refinement per frame.
- **bf16**: negligible quality change for a large accuracy budget saving; standard.
- **Lower `image_size` / higher `decimation`**: fewer points, coarser cloud; a smaller committed artifact.
- **CPU offload**: no quality cost, only a modest speed cost (host↔device copies).

Net: on 8 GB you get a genuine, correct reconstruction, just at lower FPS and slightly lower peak accuracy
than the headline "20 FPS / datacenter" figure. That is the right trade for a research workbench that
**bakes offline** anyway (the browser never touches the GPU).

## 4. The SDPA / no-FlashInfer note

FlashInfer is the fast paged-KV-cache attention kernel and is what takes upstream throughput from ~10.5 FPS to
~20 FPS ([theory 02 §6](../theory/02_geometric-context-transformer.md#6-the-paged-kv-cache)). **It must be
built against a CUDA toolkit (`nvcc`)**, which is frequently unavailable (no CUDA toolkit installed, only the
runtime). In that case do **not** try to install FlashInfer; set `use_sdpa=True`. The engine then uses
`SDPABlock`/`SDPAAttention` with a dict-based KV cache and PyTorch's fused SDPA, which:

- needs **no extra dependency** and runs on any CUDA GPU,
- implements the **same** sliding-window + scale-frame eviction and the same cross-frame special-token
  retention (`SDPAAttention._apply_kv_cache_eviction`), so it is **numerically equivalent** to the FlashInfer
  path, just without the paged-memory speedup,
- is the lab's default for the 8 GB lane.

FlashInfer's own `_sanity_check` (`flashinfer_cache.py`) and the SDPA path are kept behavior-compatible on
purpose; you can switch backends by the single `use_sdpa` flag with no other change.

## 5. Install (real cases only)

On a CUDA box, in the isolated env (never global), pin the CUDA build and the vendored engine per the engine
card (`docs/frameworks/lingbot-map/`): a torch CUDA build, the `third_party/lingbot-map` package (editable),
Open3D, matplotlib, pillow, opencv. FlashInfer is **optional** (skip it and use SDPA). Then export
`LIDAR3D_MODELS_ROOT` (weights) and `LIDAR3D_DATA_ROOT` (sequences) and bake a real case
([guide 01](01_precompute-pipeline.md)). The committed artifacts are produced offline regardless of lane, so
the public product still deploys as a static replay.

## 6. Reproducibility note

The lab bakes real cases with a fixed `--seed` (default 42) and stores the verdict + deterministic budgets,
not wall-clock, so a re-bake on the same hardware/params reproduces the artifact. FPS and VRAM figures are
hardware-specific; the ~7.1 GB peak and the "verified on RTX 4070 Laptop" claim are recorded in the README and
should be re-measured on any new target GPU rather than assumed.
