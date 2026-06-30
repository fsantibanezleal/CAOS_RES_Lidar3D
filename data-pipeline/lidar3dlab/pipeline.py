"""The offline pipeline orchestrator + CLI (ADR-0057). Runs the named stages per case, applies CONTRACT 1,
writes the compact artifact + manifest (CONTRACT 2) and a flat index.json.

    python -m lidar3dlab.pipeline                 # all cases (real ones need the GPU + LIDAR3D_DATA_ROOT/MODELS_ROOT)
    python -m lidar3dlab.pipeline SYN_orbit       # the synthetic CPU case (CI-safe)
    python -m lidar3dlab.pipeline oxford --seed 7
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

from . import __version__, registry
from .core.manifest import build_index
from .io.contract import validate_rows
from .io.formats import write_json
from .stages import evaluate, export, feature_extraction, infer, preprocess, refine, train

REPO_ROOT = Path(__file__).resolve().parents[2]
DERIVED = REPO_ROOT / "data" / "derived"
MANIFESTS = DERIVED / "manifests"

STAGES = ("preprocess", "feature_extraction", "train", "infer", "refine", "evaluate", "export")


def _row(spec) -> dict:
    return {"case_id": spec.case_id, "source_dir": spec.source_dir, "max_frames": spec.max_frames,
            "image_size": spec.image_size, "decimation": spec.decimation, "conf_quantile": spec.conf_quantile,
            "synthetic": spec.synthetic, "kv_window": spec.kv_window, "scale_frames": spec.scale_frames,
            "camera_iters": spec.camera_iters, "modality": spec.modality}


def precompute(case_id: str, seed: int = 42) -> dict:
    case = registry.get_case(case_id)
    rep = validate_rows([_row(case.params)])      # CONTRACT 1 (bring-your-own-data gate)
    if not rep.accepted:
        return {"case_id": case_id, "skipped": True, "reason": rep.rejected}
    spec = rep.accepted[0]

    t0 = time.perf_counter()
    prepared = preprocess.run(spec)
    feats = feature_extraction.run(spec, prepared)
    train.run()                                   # dormant: the engine is the pretrained foundation model
    result = infer.run(spec, seed)
    result, refine_info = refine.run(result)
    metrics = evaluate.run(result)
    metrics["n_quality_frames"] = len(feats)
    run_ms = (time.perf_counter() - t0) * 1000.0

    if spec.modality == "lidar":
        model = "open3d point-to-plane ICP" + (" (synthetic scans)" if spec.synthetic else " (real LiDAR scans)")
    elif spec.synthetic:
        model = "synthetic-corridor (CPU)"
    else:
        model = "lingbot-map (arXiv:2604.14141)"
    engine = {"package": "lidar3dlab", "version": __version__, "model": model,
              "pretrained": (spec.modality == "camera" and not spec.synthetic)}
    return export.run(case=case, params=spec, result=result, refine_info=refine_info, seed=seed,
                      run_ms=run_ms, flags=rep.flagged, metrics=metrics, engine=engine,
                      derived_dir=str(DERIVED), manifests_dir=str(MANIFESTS))


def run_all(seed: int = 42) -> list[dict]:
    entries: list[dict] = []
    for c in registry.list_cases():
        m = precompute(c.id, seed=seed)
        if m.get("skipped"):
            print(f"  SKIP {c.id}: data not available ({m['reason']})")
            continue
        entries.append({"case_id": c.id, "category": c.category, "manifest_path": f"manifests/{c.id}.json"})
    write_json(MANIFESTS / "index.json", build_index(entries))
    return entries


def main() -> None:
    ap = argparse.ArgumentParser(prog="lidar3dlab.pipeline")
    ap.add_argument("case", nargs="?", default="all", help="a case id, or 'all'")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    if args.case == "all":
        entries = run_all(args.seed)
        print(f"precomputed {len(entries)} cases -> {DERIVED}")
        for e in entries:
            print(f"  {e['case_id']:16s} [{e['category']}]")
        print(f"index -> {MANIFESTS / 'index.json'}")
    else:
        m = precompute(args.case, args.seed)
        if m.get("skipped"):
            print(f"SKIPPED {args.case}: data not available ({m['reason']})")
        else:
            print(f"precomputed {args.case}: lane={m['lane']} bytes={m['artifact']['bytes']} "
                  f"metrics={m['metrics']} -> {DERIVED / m['artifact']['path']}")


if __name__ == "__main__":
    main()
