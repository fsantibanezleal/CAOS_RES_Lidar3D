# data/ — manifest (heavy data lives OUTSIDE git, on E:)

Per ADR-0050, datasets and model weights are NOT committed. They live on the E: scratch volume and
are referenced here. Reproduce by downloading to the same paths (or override via `.env`).

## Models (`E:\_Models\3D_Spatial_Reconstruction\`)
| Item | Path | Size | Source | License |
|---|---|---|---|---|
| lingbot-map checkpoints | `lingbot-map/lingbot-map{,-long,-stage1}.pt` | ~14 GB | `hf download robbyant/lingbot-map` | Apache-2.0 |

## Datasets (`E:\_Datos\3D_Spatial_Reconstruction\`)
| Item | Path | Size | Note |
|---|---|---|---|
| lingbot-map example sequences | `lingbot-map-examples/{oxford,university,loop,courthouse}` | 301 MB | real demo inputs (PNG frames) shipped with the model repo |

## Phase 3 (LiDAR, download when wired)
NewerCollege / a SemanticKITTI sequence / nuScenes-mini (~4 GB) / Pandaset (HF, CC-BY-4.0) → for the
KISS-ICP + LiDAR-fusion tabs. Keep >10 GB datasets on E: only.
