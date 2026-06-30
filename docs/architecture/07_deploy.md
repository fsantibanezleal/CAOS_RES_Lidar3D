# Deploy

Default = **GitHub Pages, static** (ADR-0055): `.github/workflows/deploy-pages.yml` regenerates the artifacts
deterministically, builds the SPA (`copy-data.mjs` overlays `data/derived`), and deploys `frontend/dist`. No
backend at request time. See [`deploy/pages.md`](../../deploy/pages.md).

The VPS path (systemd + nginx, in `deploy/`) is **dormant** — activated only when `app/` is (an ADR-0002
trigger). `ci.yml` keeps the base honest on every push: ruff + pytest + a pipeline smoke + `check_artifacts.py`
(CONTRACT 2) + guards that fail on a tracked `.env`/venv/native-or-heavy binary/raw data/leaked machine path.
