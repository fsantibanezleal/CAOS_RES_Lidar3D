# Architecture

The deep, navigable wiki for how Lidar 3D works: a streaming 3D reconstruction lab that bakes reconstructions
offline on a GPU, commits the artifact as the source of truth, and replays it in a static web app. Read in
order for the full picture, or jump to a topic.

- [01: overview](architecture/01_overview.md): the whole system, the two engines, the four layers, the three
  lanes, the flow diagram, and the depth-to-world unprojection.
- [02: determinism and the trace](architecture/02_determinism-and-trace.md): a bake is a pure function of
  `(params, seed)`; the compact trace artifact; the LiDAR non-determinism caveat.
- [03: the gate](architecture/03_the-gate.md): `classify_lane`, why every case is precompute, the budgets, and
  the CI enforcement.
- [04: the lanes](architecture/04_lanes.md): offline / replay / live in depth, with the dependency and
  implementation separation that keeps them from contaminating each other.
- [05: the staged pipeline](architecture/05_staged-pipeline.md): every stage's input/output contract, what it
  does, and the `infer` dispatch across the three engines.
- [06: model evaluation](architecture/06_model-evaluation.md): what we measure, why there is no faked ATE, why
  `train` is an honest no-op, the honesty policy.
- [07: deploy](architecture/07_deploy.md): GitHub Pages, the workflow, why CI does not re-bake, the custom
  domain, and the env/secrets model.
- [08: the two data contracts](architecture/08_data-contracts.md): CONTRACT 1 (ingestion) and CONTRACT 2
  (artifact) in full, including the outlier policy, the manifest/trace/index schemas, and the TypeScript mirror.

The engine card lives in [frameworks/lingbot-map](frameworks/lingbot-map/README.md); the theory behind it
(the GCT architecture, the three-tier context, the geometry, the SOTA lineage) is in [theory/](theory.md).

Binding decision: [ADR-0057](../../conventions/architecture/0-archetype/ADR-0057-product-repo-archetype.md).
