# Architecture: deploy

The product deploys as a **static deterministic-replay site on GitHub Pages** (ADR-0055, Pages-first). There
is no backend at request time. The public URL is `lidar3d.fasl-work.com`. This document covers the deploy
workflow, the one subtlety that makes it correct (no CI re-bake), the custom domain, and the env/secrets model.

## The default: GitHub Pages, static

The SPA plus the committed CONTRACT-2 artifacts are served statically. The workflow is
`.github/workflows/deploy-pages.yml`, triggered on push to `main` (or manually via `workflow_dispatch`):

1. **checkout** the repo (which already contains the committed `data/derived` artifacts).
2. **setup Node 20**, cache npm keyed on `frontend/package-lock.json`.
3. **build the SPA:** `cd frontend && npm ci && npm run build`. The build's prebuild step, `copy-data.mjs`,
   overlays `data/derived` into `frontend/public/data` and inlines the `lidar3dlab` sources into
   `public/pyodide/sources.json` (the latter is vestigial for this product, since there is no browser-live
   lane, but it is harmless and keeps the archetype uniform).
4. **upload** `frontend/dist` as the Pages artifact.
5. **deploy** it with `actions/deploy-pages@v4`.

`concurrency: group: pages, cancel-in-progress: true` ensures only the latest deploy runs. The Vite config
uses `base: './'` (a relative base) so the bundle works on a project-site path.

## The critical subtlety: CI does not re-bake

The deploy workflow **builds the SPA from the already-committed artifacts; it never re-runs the pipeline.**
This is deliberate and is called out in the workflow comment. The real cases were baked offline on a GPU that
GitHub Actions does not have (no CUDA GPU, and the 4.6 GB checkpoint is not in git). If CI re-ran
`python -m lidar3dlab.pipeline all`, every real case would be **skipped** for lack of data, and the deploy
would silently drop `oxford/university/loop/courthouse`, leaving only the synthetic cases. So the committed
`data/derived` artifacts **are** the replay source, and the deploy job's only job is to bundle them.

This is why the determinism contract ([02](02_determinism-and-trace.md)) matters operationally: because a bake
is a pure function of `(params, seed)` and carries no wall-clock or absolute paths, committing the artifact is
safe and re-baking on the GPU host reproduces it. The GPU host bakes and commits; CI ships what was committed.

## The separate CI workflow keeps the base honest

`.github/workflows/ci.yml` (on push to `main`/`develop` and on PRs) is the guard, distinct from deploy. It has
two jobs:

- **test:** install the pipeline + dev requirements + the editable package, run `ruff`, run `pytest`,
  regenerate the synthetic case (`python -m lidar3dlab.pipeline SYN_orbit`), then run
  `scripts/check_artifacts.py` (the CONTRACT-2 drift guard: index to manifests to artifacts all exist, byte
  sizes match, lane == gate).
- **guards:** the base-integrity checks the archetype forbids regressing on:
  - a real `.env` must never be tracked (only `.env.example`);
  - no venv, native binaries, or heavy model blobs tracked (`.venv`, `.dll/.so/.dylib/.pt/.pth`);
  - no raw/heavy data tracked (`.parquet/.h5/.hdf5/.nc/.mat/.npy`), only compact derived artifacts;
  - no leaked local machine path in tracked sources (a grep for the local repo root prefix), so a personal
    path can never enter git.

These are what let the repo commit artifacts and secrets-config-by-reference without ever committing the heavy
assets or a machine-specific path.

## Enabling Pages and the custom domain

- **Once per product:** repo Settings to Pages to Source = "GitHub Actions".
- **Custom domain:** set it via the API, not the CNAME file alone. A `CNAME` file does **not** set the domain
  on Actions-based deploys; it must be set with
  `gh api PUT repos/<owner>/<repo>/pages -f cname=lidar3d.fasl-work.com` (cname only, no `https_enforced`),
  then redeploy, or the domain 404s. This is a known gotcha recorded in the CAOS_MANAGE reference notes. DNS
  is the wildcard `*.fasl-work.com` already provisioned, so no per-app DNS work is needed.

## The env / secrets model

No secrets live in the repo. Machine-specific and heavy-asset paths come from the environment:

- `LIDAR3D_MODELS_ROOT`: where the lingbot-map checkpoint lives (outside git). `config.py` resolves the
  checkpoint as `LIDAR3D_MODELS_ROOT/lingbot-map/<ckpt>`.
- `LIDAR3D_DATA_ROOT`: where raw sequences / LiDAR scans live (outside git).
- `LIDAR3D_LINGBOT_CKPT`: the checkpoint filename (default `lingbot-map.pt`).

`config.py` reads these from the environment and falls back to empty repo-relative defaults if unset, so
nothing crashes at import; a missing source is simply rejected by CONTRACT 1. Real values are provisioned into
a gitignored `.env` from the CAOS_MANAGE vault (`credentials/app-env/lidar3d.env`); `.env.example` carries only
generic placeholders and states that most of it matters **only** if the dormant `app/` backend is activated.
None of these env values, and no derived absolute path, ever enters a committed file (the CI guard enforces
it).

## The dormant VPS path

`deploy/` also holds systemd + nginx templates (`fasl-<slug>.service`, `<domain>.nginx`) for a VPS deploy.
These are **dormant**, used only if the `app/` backend is activated (an ADR-0002 trigger). This product does
not need them; they are kept as a one-switch on-ramp. The default and current deploy is Pages, static.

## See also

- [02: determinism and the trace](02_determinism-and-trace.md): why committing the artifact is safe.
- [04: the lanes](04_lanes.md): the replay lane the deploy ships, and the dormant live lane.
- `deploy/pages.md` and `deploy/README.md`: the operational deploy notes.
