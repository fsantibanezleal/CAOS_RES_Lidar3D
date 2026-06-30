# Guide — instantiate a new product from this template

1. **Copy** the template tree into the new product repo (its own git repo; code-repo flow `task/* → develop → main`).
2. **Rename** the package `lidar3dlab` → `<slug>lab` (the folder + all imports + `pyproject.toml`
   `[tool.setuptools.packages.find].where`/name + the scripts' `-m lidar3dlab.pipeline` + docs).
3. **Replace the EXAMPLE engine**: `<slug>lab/model/` + the bodies of `stages/{preprocess,feature_extraction,train,
   infer,evaluate}` with your research-chosen SOTA engine. **Keep the stage names + both contracts.**
4. **Write CONTRACT 1** (`io/contract.py`) for YOUR raw data — required columns, units, ranges, explicit outlier
   policy — plus a tiny `data/examples/` sample that passes it; document it in `data/README.md`. Update
   `tests/test_contract.py`.
5. **Define cases-by-category** in `cases/` + `registry.py` (a varied matrix across your real axes + negative/sanity
   controls). Document them in `docs/cases/`.
6. **Pin your engines** in `data-pipeline/requirements.txt` (or `-gpu`/`-api`) and add a card per engine in
   `docs/frameworks/<NN>_<tool>/` (the deep research, made binding — no toy substitute).
7. **Mirror the contract**: if your trace/manifest shape changed, update `frontend/src/lib/contract.types.ts`
   (a drift fails `tsc`); build the visualizations in `frontend/src/render` + `App.tsx`.
8. **Activate only the lanes you need.** Leave the rest dormant with a README marker ("this solution does not
   require it at the moment") — e.g. `app/` for a static product; `frontend/` for a pipeline-only product.
9. **Verify**: `scripts/setup` → `scripts/precompute` → `pytest` → `cd frontend && npm run build`. CI guards green.
10. **Version** from day 1: `CHANGELOG.md` (`X.XX.XXX`, `0.x` while synthetic) + a tag per release.
11. **Ship the Architecture modal** (ADR-0058, MANDATORY): copy `frontend/src/architecture.ts.txt` â
    `architecture.ts`, specialise the product-specific SVGs (`public/svg/tech/01-the-app.svg`,
    `04-the-science.svg`) + tab copy, pass `architecture` to the `AppShell` config in `main.tsx`, and pin
    `@fasl-work/caos-app-shell` `^0.1.2`. See [guide 05](05_architecture-modal.md). Verified in screenshot-verify.

The base is frozen — you should be editing only the **core** (engine/stages, visualizations, cases/content),
never the structure, contracts, env or deploy. If you find yourself editing the base, that's the smell ADR-0057
exists to remove.
