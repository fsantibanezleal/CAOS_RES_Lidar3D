# Experiments log

Every training epoch appends one JSON line to `models/own-depthpose/experiments.jsonl`. The file is never
truncated, so it is a complete, append-only ledger of training runs. It feeds both the curated
[Model history](02_model-history.md) narrative and the web **Experiments** page, so the history stays visible in
the product, not just in the repo.

## Schema (one row per epoch)

| Field | Meaning |
|---|---|
| `ts` | ISO timestamp when the epoch finished |
| `backbone` | `scratch` or `resnet18` |
| `epoch` | 0-based epoch index |
| `val_ate` | held-out Absolute Trajectory Error this epoch, metres (lower = better) |
| `best_ate` | best ATE so far in this run |
| `is_best` | whether this epoch improved and was checkpointed |
| `params_M` | model parameter count, millions |
| `base` | decoder width |
| `size` | training image size (px) |
| `lr` | learning rate |
| `use_icl` | whether ICL-NUIM perfect-depth pairs were included |
| `train_pairs` | number of training pairs |
| `val_seq` | held-out sequence name |

## Example

```json
{"ts":"2026-07-01T08:09:08","backbone":"resnet18","epoch":0,"val_ate":0.6002,"best_ate":0.6002,
 "is_best":true,"params_M":12.774,"base":32,"size":224,"lr":0.0001,"use_icl":true,
 "train_pairs":7329,"val_seq":"rgbd_dataset_freiburg3_long_office_household"}
```

## How the web uses it

A trimmed snapshot of this ledger is shipped as a frontend artifact and rendered on the Experiments page as the
"Model history" table (backbone, data, ATE, deployed). Rows that predate the log (the early scratch runs M1–M6) are
backfilled with `"source":"backfilled"` so the on-site table is complete. The gate for flipping a row to *deployed*
is a verified screenshot comparison against the live reconstruction, never the ATE number alone.

## Reproducing a run

```bash
# from data-pipeline/, with LIDAR3D_DATA_ROOT + LIDAR3D_MODELS_ROOT set
python -m lidar3dlab.train.train_depthpose --backbone resnet18 --use_icl \
  --epochs 10 --batch 6 --lr 1e-4 --size 224
```

The best checkpoint lands at `LIDAR3D_MODELS_ROOT/own-depthpose/own-depthpose-resnet18.pt` (archive) and
`own-depthpose.pt` (canonical, loaded by the engine). Then re-bake our case and compare before deploying.
