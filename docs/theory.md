# Theory

The deep, self-contained theory of the streaming 3D reconstruction lab. Every claim here is grounded in the
vendored engine (`third_party/lingbot-map`), the lab's engines (`data-pipeline/lidar3dlab/model/`), or the
primary literature (`docs/research/`). Read top to bottom for the full argument; each page also stands alone.

| # | Page | What it establishes |
|---|---|---|
| 01 | [Streaming reconstruction, formalized](theory/01_streaming-reconstruction.md) | the online-SLAM problem as feed-forward regression: inputs, outputs, causality, and the three-way tension (geometric accuracy vs temporal consistency vs compute) |
| 02 | [The Geometric Context Transformer](theory/02_geometric-context-transformer.md) | the GCT/GCA in full: DINOv2 backbone, alternating attention, the three contexts, the attention mask, the paged KV cache, the token-count complexity proof, the metric-scale anchor |
| 03 | [Pointmaps and geometry](theory/03_pointmaps-and-geometry.md) | pointmaps, the `absT_quaR_FoV` pose encoding, camera-to-world, the depth→world unprojection equation, intrinsics self-calibration, confidence filtering |
| 04 | [LiDAR odometry](theory/04_lidar-odometry.md) | point-to-plane ICP, the linearized normal equations, scan-to-scan registration, drift, why KISS-ICP is the SOTA option, camera-vs-LiDAR modalities |
| 05 | [The SOTA lineage](theory/05_sota-lineage.md) | DUSt3R → MASt3R → VGGT → pi3 → MapAnything → lingbot-map: what each added, a comparison table, arXiv references |
| 06 | [The novel agenda (D1–D5)](theory/06_novel-agenda.md) | five research directions on the frozen state: hypothesis, method, feasibility on 8–24 GB, and the benchmark+metric that would prove each; the honest bar |

## Reading order by goal

- **Understand the engine end to end:** 01 → 02 → 03.
- **Understand the second modality:** 04.
- **Place the engine in the field:** 05.
- **Understand what this lab adds beyond SOTA:** 06 (after 02, 03, 04).

## Conventions

- Equations use `$...$` (inline) and `$$...$$` (block).
- Symbols are consistent across pages: $I_t$ = frame at time $t$; $\hat P_t$ = camera-to-world pose;
  $\hat D_t$ = dense depth; $M$ = image tokens per frame; $T$ = total frames; $n$ = anchor frames;
  $k$ = pose-reference window; $s$ = metric scale.
- Heavy paths (weights, datasets) are referred to by the env-var names `LIDAR3D_MODELS_ROOT` and
  `LIDAR3D_DATA_ROOT`, never by machine paths.
- Facts marked from the literature carry an arXiv id; facts from the engine carry a file reference.
