# The two data contracts

A product is only real if data flows through two **enforced** contracts. Both are CI-checked.

## CONTRACT 1 — ingestion (`raw → pipeline`) — the *bring-your-own-data* gate
`data-pipeline/lidar3dlab/io/contract.py`. Declares the required schema (columns, units, ranges) + an explicit
**outlier policy** (reject / clip / flag). A dataset is accepted iff it passes; bad rows are rejected **with a
reason**, never silently coerced; suspicious-but-plausible rows are flagged (the flag is recorded in the
manifest). This is what lets a third party point the tool at THEIR data instead of only replaying baked cases.

EXAMPLE (SIR): columns `case_id,beta,gamma,N,I0[,days]`; ranges per `RANGES`; reject NaN/Inf/out-of-range/`I0>N`;
flag `R0>20`. Full table: [`data/README.md`](../../data/README.md).

## CONTRACT 2 — artifact (`pipeline → web`)
`data-pipeline/lidar3dlab/core/{trace.py, manifest.py}`. Every run writes a compact trace (`example.trace/v1`) +
a manifest (`example.manifest/v2`) recording params, seed, engine+version, the artifact byte size, the measured
**[lane/gate](03_the-gate.md)** verdict, the Contract-1 flags, and the evaluation metrics. A flat
`data/derived/manifests/index.json` inventories every case.

**Enforcement:** `frontend/src/lib/contract.types.ts` mirrors this schema — a drift fails `tsc`. `scripts/check_artifacts.py`
(run in CI) verifies index→manifests→artifacts exist, byte sizes match, and lane==gate. The web loads **only** these
artifacts; it never recomputes (except the optional live lane, which emits the same trace schema).

## Why this matters
Without Contract 1 the app can't be applied to new data (it's a demo). Without Contract 2 the web can silently
drift from what the pipeline produced. The contracts are the seam that makes the product a tool, not a slideshow.
