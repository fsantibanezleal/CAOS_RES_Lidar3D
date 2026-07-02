# Preprints

LaTeX manuscripts that document the research in depth, so all relevant information is persisted in a citable,
self-contained form (not only in the code + `docs/`). Each subfolder is one manuscript.

| Folder | Manuscript | Status |
|---|---|---|
| `01-lidar3d-system/` | **Lidar3D: streaming monocular 3D reconstruction on modest hardware.** The full system, methodology, data, and measured results (depth is cheap, pose is the bottleneck). | draft, tracks the live state |
| `02-metric-seeded-ba-pose/` | **Metric-depth-seeded differentiable bundle adjustment for monocular VO.** The methodological proposal / innovation (our edge over regression pose heads). | proposal draft |

## Build

Each folder is a standalone LaTeX article:

```bash
cd preprints/01-lidar3d-system
pdflatex main.tex && bibtex main && pdflatex main.tex && pdflatex main.tex
```

No LaTeX toolchain is required to read them; the `.tex` is the source of record. Keep them in sync with
`docs/models/` (the model history, the experiment line) and `models/own-depthpose/experiments.jsonl` (the ledger)
as experiments land, so the manuscripts are the persistent, in-depth narrative of where the research is.
