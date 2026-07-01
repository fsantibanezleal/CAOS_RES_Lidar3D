# 02 · The Geometric Context Transformer (GCT / GCA)

The engine at the heart of the lab. This page explains the architecture in full: the frozen DINOv2 backbone,
the 24 alternating-attention blocks, the three-tier geometric context, the attention mask that partitions
them, the paged KV cache that makes it real-time, the complexity argument (with the token math), and the
metric-scale anchor. All references are to the vendored engine under `third_party/lingbot-map/`.

Prereq: [01 (the streaming problem)](01_streaming-reconstruction.md). Sequel: [03 (the geometry of the
outputs)](03_pointmaps-and-geometry.md).

---

## 1. Overview

lingbot-map (arXiv:2604.14141, "Geometric Context Transformer for Streaming 3D Reconstruction", Apache-2.0)
recovers per-frame camera pose + dense metric depth + confidence from a causal video stream, holding
**~20 FPS over 10,000+ frames at 518×378** with **no per-scene optimization and no loop closure**. It is the
2026 SOTA among streaming feed-forward reconstructors ([05](05_sota-lineage.md)).

The forward path per frame is:

```
I_t ──▶ DINOv2 ViT patch-14 (frozen)  ──▶ per-patch tokens (M ≈ 500)
                                              │  + camera token + 4 register tokens + 1 scale/anchor token
                                              ▼
        24 blocks, ALTERNATING:
          • Frame Attention        (within-frame refinement, full attention over one frame's tokens)
          • Geometric Context Attention (cross-frame, causal, over the 3 contexts + paged KV cache)
                                              │
                             ┌────────────────┼───────────────────┐
                             ▼                ▼                   ▼
                       Camera head       Depth (DPT) head     confidence
                        pose_enc          metric depth          conf
                        (cam-to-world)
```

Concretely, `GCTStream` (`lingbot_map/models/gct_stream.py`) is built from a `GCTBase`
(`lingbot_map/models/gct_base.py`) with an `AggregatorStream` trunk
(`lingbot_map/aggregator/stream.py`) and three prediction heads (`lingbot_map/heads/`). The lab instantiates
it in `data-pipeline/lidar3dlab/model/lingbot.py` with the 8 GB-safe knobs of [03/guide 03](../guides/03_gpu-lane.md).

## 2. The DINOv2 backbone (frozen)

The patch embedding is `dinov2_vitl14_reg` (`GCTBase.__init__` default `patch_embed='dinov2_vitl14_reg'`,
`embed_dim=1024`): a DINOv2 ViT-Large with register tokens, patch size **14**, kept **frozen**. DINOv2 is a
self-supervised vision foundation model; its patch features are strong, general geometric descriptors, which
is why the whole DUSt3R, VGGT, lingbot-map lineage builds on it ([05](05_sota-lineage.md)).

At 518×378, patch-14 gives roughly $\lceil 518/14 \rceil \times \lceil 378/14 \rceil = 37 \times 27 \approx 999$
patch tokens; the deep-dive uses "$M \approx 500$" as the order-of-magnitude figure and the code's
resolution-dependent count is `(img_size // patch_size)**2 + num_special_tokens`
(`AggregatorStream._get_flashinfer_manager`). Freezing the backbone matters for this lab: the geometric
prior is fixed, so **new heads can be attached to the aggregated state without disturbing it**
([06](06_novel-agenda.md)).

Each frame contributes, beyond its $M$ patch tokens, a small set of **special tokens**
(`AggregatorStream._setup_special_tokens`):

| token | count | role |
|---|---|---|
| camera token | 1 | carries the frame's pose information into the camera head |
| register tokens | 4 | DINOv2-style scratch tokens (attention sinks / global bookkeeping) |
| scale (anchor) token | 1 | learnable; grounds the world frame + metric scale on the anchor block |

So `num_special_tokens = 1 + 4 + 1 = 6` and `patch_start_idx = 6` (the token layout is `[camera, reg×4,
scale, patch_0 … patch_{M-1}]`). These 6 are exactly the tokens that survive into the long-term
**trajectory memory** (§4.3).

## 3. Alternating attention (the VGGT design)

The 24-block trunk alternates two attention types (`AggregatorStream._build_blocks` builds parallel
`frame_blocks` and `global_blocks`; the VGGT alternating-attention pattern):

- **Frame Attention** (`frame_blocks`, standard `Block` + 2D RoPE): full self-attention **within a single
  frame's tokens**. Refines per-frame features; no cross-frame information. Spatial position is injected by
  2D Rotary Position Embedding (`RotaryPositionEmbedding2D`, `lingbot_map/layers/rope.py`).
- **Geometric Context Attention** (`global_blocks`, `FlashInferBlock` or `SDPABlock`): **cross-frame, causal**
  attention over the three contexts of §4, served by the paged KV cache of §6. This is where the streaming
  geometry reasoning happens.

Alternating them lets the network interleave "clean up what this frame sees" with "reconcile this frame
against the map so far," 12 times each. The heads read from a *list* of aggregated token tensors taken at
selected depths (`_aggregate_features(..., selected_idx=[4, 11, 17, 23])`): the depth (DPT) head and camera
head fuse features from four points in the trunk, not just the last layer.

## 4. The three contexts

Geometric Context Attention is the paper's core idea: on a new frame, cross-frame attention does not see "all
past frames equally." The past is partitioned into three tiers, each solving a distinct SLAM failure mode,
each kept at a different fidelity. This is the mechanism that reconciles accuracy, consistency, and compute
([01 §3](01_streaming-reconstruction.md#3-the-three-way-tension)).

| Tier | What it is | Tokens kept per frame | Fidelity | Role |
|---|---|---|---|---|
| **Anchor context** | the first $n$ frames ($n \ll T$; $n=8$ scale frames in the lab config) | full image tokens **+** learnable anchor/scale token, full mutual attention | highest, fixed | fixes the **world coordinate frame** and the **metric scale** |
| **Pose-reference window** | the $k$ most recent frames ($k=64$ default; **16** in the 8 GB lane) | full image tokens (~$M$/frame) | high, sliding | **dense local geometry**: short-baseline correspondence for accurate relative pose + local depth |
| **Trajectory memory** | every older frame (beyond the window) | **6 tokens** (camera + 4 register + scale); image tokens discarded | compressed, persistent | cheap **long-range drift anchoring**, ordered by Video-RoPE |

### 4.1 Anchor context: coordinate grounding + metric scale

The first block of frames (the "scale frames") receives **full bidirectional attention among themselves**
plus the learnable **scale/anchor token**. This block establishes a single consistent world frame that every
later frame is expressed in. Crucially it also sets **absolute metric scale**: monocular reconstruction is
scale-ambiguous, so the model reads scale off the anchor point cloud as the mean radius

$$
s \;=\; \frac{1}{|X_{\text{anchor}}|} \sum_{x \in X_{\text{anchor}}} \lVert x \rVert_2 ,
$$

i.e. the average distance of the anchor 3D points from the origin. Every subsequent depth/pose prediction is
produced consistent with this $s$, so the whole reconstruction is in one metric world frame rather than each
frame being independently up-to-scale. In the streaming loop the scale frames are processed together first
(Phase 1, `GCTStream.inference_streaming`: `num_frame_per_block = scale_frames`), then the remaining frames
stream one at a time (Phase 2). Anchor frames are **never evicted** from the cache (§6), so their grounding
persists for the whole sequence.

### 4.2 Pose-reference window: dense geometric cues

The $k$ most recent frames are kept at **full image-token resolution**. Short baselines between nearby views
give the strongest correspondence signal, so this window is where accurate **relative pose** and sharp
**local depth** come from. lingbot-map trains a relative-pose loss over all pairs inside the window and
ablates $k=64$ as beating full-causal attention on accuracy *and* being 1.7× faster / 2.7× lighter
(`docs/research/lingbot-map-deep-dive.md`). The window slides: as a new frame enters, the oldest window frame
is demoted to trajectory memory (its full image tokens are dropped, its 6 special tokens are retained). In
the lab's 8 GB lane the window is shrunk to $k=16$ (`kv_cache_sliding_window=16`).

### 4.3 Trajectory memory: long-range drift correction

For **all** frames older than the window, the model keeps only the **6 special tokens** per frame (the
camera, register, and scale tokens: `evicted_k[..., camera_token_idx:scale_token_idx+1, :]` in the eviction
code). Image tokens are discarded. These 6-token summaries are a compact record of the entire past that lets
the current frame anchor against long-ago geometry, correcting slow drift, without paying to attend to every
past pixel. They are ordered in time by **Video-RoPE** (3D rotary position embedding over the temporal axis,
`enable_3d_rope=True`, `WanRotaryPosEmbed`, `AggregatorStream._init_3d_rope`), so the memory is
sequence-aware rather than a bag of tokens. This lossy compression is deliberate and is one of the paper's
stated limitations: fine detail is lost over tens of thousands of frames
(`docs/research/lingbot-map-deep-dive.md` §7), which motivates the lab's retrieval-augmented memory idea
([06 D3](06_novel-agenda.md)).

## 5. The attention mask

The cross-frame attention is built to realize exactly the partition of §4. In the SDPA path
(`CausalAttention.forward` and `SDPAAttention.forward` in `lingbot_map/layers/attention.py`) the effective
boolean mask over (query frame, key frame) pairs is assembled from three pieces:

1. **Causal base.** A frame may attend to itself and earlier frames only; future frames are masked. This is
   the `block_mask` (upper-triangular in frame order).
2. **Sliding window.** Each query frame $i$ may attend to key frames in
   $[\max(0, i - w + 1),\ i]$, where $w$ is the window in frames
   (`window_size_in_frames = sliding_window_size * num_frame_per_block`):
   ```
   sliding_mask[:, :, q_start:q_end, k_start:k_end] = True   # k_start = window_start_frame * frame_seqlen
   ```
   combined with the causal base by logical AND (`mask = mask & sliding_mask`).
3. **Anchor / scale override.** The first `num_frame_for_scale` frames are made globally visible: every query
   may attend to them, and they attend fully to each other
   (`mask[:, :, q_start:q_end, :num_frame_for_scale*frame_seqlen] = True` and the block
   `mask[:, :, :S_scale, :S_scale] = True`). This is what keeps the world frame and metric scale reachable
   from anywhere in the sequence regardless of the window.

The net visible set for query frame $i$ is therefore

$$
\mathcal{V}(i) \;=\; \underbrace{\{1,\dots,n\}}_{\text{anchor}}\; \cup\; \underbrace{\{\max(1,i-k+1),\dots,i\}}_{\text{window (full tokens)}}\; \cup\; \underbrace{\{n+1,\dots,i-k\}}_{\text{older frames (6 tokens each)}} .
$$

In the FlashInfer path (§6) the *same* visibility is realized not by a dense mask but by which **pages** are
present in the cache: eviction physically removes the image tokens of out-of-window frames while retaining
their special tokens, so the paged attention naturally attends to exactly $\mathcal{V}(i)$ with no explicit
mask (`compute_attention(..., causal=False)` because "the causal constraint is enforced by KV cache
contents, not by mask").

## 6. The paged KV cache

To hold ~20 FPS the cross-frame attention cannot recompute over the whole history each frame; it caches past
keys/values and updates incrementally. The subtlety is that the visible set $\mathcal{V}(i)$ has two very
different populations, and storing them naively (one growing contiguous tensor) both wastes memory and pays
realloc cost. lingbot-map uses a **two-stream paged cache**
(`lingbot_map/layers/flashinfer_cache.py`, `FlashInferKVCacheManager`):

- **Patch stream (recyclable).** One fixed-size **page per frame** holds that frame's ~$M$ patch tokens.
  Scale frames go to `scale_patch_pages` (never evicted, capped at `scale_frames`); recent frames go to
  `live_window_patch_pages` (evicted when the deque exceeds `sliding_window`, the page recycled to a free
  list). `page_size = patches_per_frame` exactly (no zero padding) on the FA2 backend; rounded up to the next
  power of two on FA3.
- **Special stream (append-only, never recycled).** The 6 special tokens of **every** frame are packed
  contiguously: one special page holds $\lfloor \text{page\_size}/6 \rfloor$ frames (e.g. 42 frames per page
  at page_size 256). These are the trajectory-memory tokens; they persist for the whole run.

Physical layout per block: `kv_caches[block] : [max_num_pages, 2, page_size, H, D]` (dim 1 is K=0/V=1). The
visible page table is assembled in strict order **scale, then window, then special**
(`build_visible_page_table`), so only the final page can be partially full and
`paged_kv_last_page_len` describes the tail without a custom mask. Per frame step the FlashInfer wrapper's
`plan()` is called **once** (on block 0) and `run()` reused for every block, since all blocks share the same
page structure. Attention is `flashinfer.BatchPrefillWithPagedKVCacheWrapper`; RoPE is applied to K
**before** caching so it need not be recomputed on read.

**Keyframe / non-keyframe.** A frame can attend to `[cache + current]` but choose **not** to persist its own
KV (`_set_skip_append(True)`), which caps memory growth to $\sim 1/\text{keyframe\_interval}$; the FlashInfer
path implements this by a temporary append + `rollback_last_frame`, the SDPA path by a `_skip_append` flag.
The lab bakes with `keyframe_interval=1` (every frame is a keyframe) but the mechanism is what makes 25k-frame
offline renders feasible.

**Backends.** FlashInfer (paged kernels) is the fast default and is what takes throughput from **~10.5 FPS to
~20 FPS** (`docs/research/lingbot-map-deep-dive.md`). It requires a CUDA toolkit / `nvcc` to build, which is
often unavailable; the engine therefore ships an **SDPA fallback** (`use_sdpa=True`, `SDPAAttention` with a
dict-based cache and `torch.nn.functional.scaled_dot_product_attention`) that runs on any CUDA GPU with no
extra deps. The lab's 8 GB lane uses SDPA (see [guide 03](../guides/03_gpu-lane.md)); it is slower but
numerically equivalent.

## 7. Complexity: the token-count argument

This is why the design is real-time over long sequences. Let $M$ = image tokens per frame, $T$ = frames so
far, $n$ = anchor frames, $k$ = window frames, and 6 = special tokens per memory frame.

**Naive causal attention.** Frame $t$ attends to all $M$ tokens of all $\le t$ frames, so the per-frame
key/value count is

$$
Q_{\text{naive}}(t) \;=\; M\,t \quad\Longrightarrow\quad O(M\,T)\ \text{per frame},\ \ O(M\,T^2)\ \text{total}.
$$

This grows without bound in $t$: at $T = 10^4$ and $M \approx 500$ that is $\approx 5\times 10^6$ tokens for
the *last* frame alone.

**Geometric Context Attention.** Frame $t$ attends to the anchor ($n$ frames at full $M$), the window ($k$
frames at full $M$), and the memory ($t - n - k$ older frames at 6 tokens each):

$$
Q_{\text{GCA}}(t) \;=\; (n + k)\,M \;+\; 6\,(t - n - k) \;\le\; (n+k)\,M + 6\,T .
$$

The first term $(n+k)M$ is a **constant** (independent of $t$); the second is **linear in $T$ but with a tiny
coefficient (6)**. Plugging the deep-dive's numbers $M \approx 500$, $n=3$, $k=16$, $T = 10^4$:

$$
Q_{\text{GCA}} \approx (3+16)\cdot 500 + 6\cdot 10^4 = 9{,}500 + 60{,}000 \approx 7\times 10^4 \ \text{tokens},
$$

versus $Q_{\text{naive}} \approx 5\times 10^6$: a **~80× reduction**, matching the paper's stated figure.
Because the dominant $(n+k)M$ part is constant and the paged cache updates only the newly appended tokens
each frame, the **per-frame cost is effectively constant in $T$** for the accuracy-critical part, which is
exactly what a real-time streaming engine needs. Memory follows the same accounting: the patch pages are
capped at $n+k+\text{headroom}$ (`max_patch_pages = scale_frames + sliding_window + 16`), and only the small
special stream grows.

## 8. Outputs and the heads

The trunk output (a list of aggregated token tensors) feeds three heads (`GCTBase._predict_*`):

- **Camera head** (`CameraCausalHead`, `dim_in = 2*embed_dim`): emits the **pose encoding** `pose_enc`
  $\in \mathbb{R}^{S\times 9}$, the compact `absT_quaR_FoV` form decoded in [03](03_pointmaps-and-geometry.md).
  It refines the pose iteratively; the number of refinement steps is `camera_num_iterations` (default 4,
  set to **1** in the 8 GB lane for speed).
- **Depth head** (`DPTHead`, `output_dim=2`, `activation="exp"`, `conf_activation="expp1"`): emits dense
  **metric depth** and a **confidence** map. The DPT (dense prediction transformer) head reassembles
  multi-scale trunk features into a full-resolution map.
- **Point head** (also a `DPTHead`, when enabled): emits world points directly; the lab's export path instead
  reconstructs the cloud by unprojecting the depth head's output ([03](03_pointmaps-and-geometry.md)), which
  is equivalent and keeps the geometry explicit.

The lab consumes `pred["pose_enc"]`, `pred["depth"]`, and `pred["depth_conf"]`
(`data-pipeline/lidar3dlab/model/lingbot.py`), decodes poses + intrinsics, unprojects each frame's depth to
world points, confidence-filters, and fuses into one colored cloud. That geometry is [03](03_pointmaps-and-geometry.md).

## 9. What this buys the lab (and where it stops)

The GCT gives the lab a **frozen, well-structured geometric state**: after the trunk, every frame is
represented by its patch tokens plus 6 persistent special tokens, all in one metric world frame. That state
is the substrate the novel agenda operates on. The engine's own stated gaps, all visible in this page, are:

- **no loop closure** (the mask never re-links a revisited place; drift on revisits is uncorrected), see [06 D1](06_novel-agenda.md),
- **lossy 6-token memory** (fine long-range detail is dropped), see [06 D3](06_novel-agenda.md),
- **no test-time optimization** (the core path is pure regression), see [06 D4](06_novel-agenda.md).

Those are the openings; the rest of the theory section builds toward them.
