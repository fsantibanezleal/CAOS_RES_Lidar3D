# Docs: the product wiki

The navigable, complete internal wiki for **Lidar 3D**, a streaming 3D reconstruction lab (ADR-0056:
authored as the product is built, not bolted on at the end). The staged pipeline plus its two enforced data
contracts plus its validation are the primary product; the web app is a projection of a validated subset.

Lidar 3D turns an ordered RGB stream into a camera trajectory, dense metric depth, and a fused RGB point
cloud, feed-forward and with no per-scene optimization, built around **lingbot-map** (arXiv:2604.14141,
Apache-2.0), with a second real engine (Open3D ICP LiDAR odometry) and a CPU synthetic engine for CI. It is
an instance of the CAOS product-repo archetype (ADR-0057), deploying as a static deterministic-replay site at
`lidar3d.fasl-work.com`.

## Map

- **[architecture/](architecture.md)**: how the repo works, in depth. The two engines, the four layers, the
  three lanes, determinism + the trace, the live/precompute gate, the staged pipeline, model evaluation, the
  two data contracts, and deploy. Start here to understand the system.
- **[frameworks/](frameworks.md)**: one card per research-chosen engine/library (what/why, install, config,
  usage, honesty). The [lingbot-map card](frameworks/lingbot-map/README.md) is the binding SOTA engine, pinned
  in `data-pipeline/requirements.txt`.
- **[guides/](guides.md)**: runnable how-tos. Run the precompute pipeline, bring your own data, the GPU lane,
  run the (dormant) API, and the in-app architecture modal.
- **[cases/](cases.md)**: the CATEGORY taxonomy + the coverage matrix + one page per documented case. The App
  shows one case; Experiments/Benchmark summarize across categories.
- **[theory/](theory.md)** (the theory surface): the deep, self-contained theory of the lab. Streaming
  reconstruction formalized, the [Geometric Context Transformer](theory/02_geometric-context-transformer.md)
  in full (backbone, alternating attention, the three contexts, the paged KV cache, the metric-scale anchor),
  pointmaps + the depth-to-world geometry, LiDAR odometry, the SOTA lineage, and the novel agenda beyond SOTA.

## Honesty + data policy

- Numbers come from the engine and the committed artifacts, never from a claim. Metrics that need ground truth
  (ATE/RPE) are reported only when GT exists; otherwise `None` + a stated reason (no faked accuracy). The paper's
  SOTA numbers are cited as the paper's, separate from this lab's own measurements. See
  [architecture/06](architecture/06_model-evaluation.md).
- The synthetic engine is clearly labelled synthetic; it is a real procedural reconstruction, not a stand-in
  pretending to be a camera bake. The LiDAR lane's non-determinism is disclosed
  ([architecture/02](architecture/02_determinism-and-trace.md)).
- Public compact derived artifacts are committed (`data/derived/`); raw/private sources and the checkpoint stay
  out of git (resolved from `LIDAR3D_DATA_ROOT` / `LIDAR3D_MODELS_ROOT`), per ADR-0050/0055. The two data
  contracts ([architecture/08](architecture/08_data-contracts.md)) govern raw-to-pipeline and pipeline-to-web.
