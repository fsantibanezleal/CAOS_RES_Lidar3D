"""The offline pipeline orchestrator + CLI (ADR-0057). Runs the named stages per case, applies CONTRACT 1, writes
the compact artifact + manifest (CONTRACT 2) and a flat index.json.

    python -m lidar3dlab.pipeline            # all cases
    python -m lidar3dlab.pipeline EX02_epidemic --seed 7
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

from . import registry
from .core.manifest import build_index
from .core.rng import make_rng
from .io.contract import validate_rows
from .io.formats import write_json
from .io.schema import SIRParams
from .stages import evaluate, export, infer, train

# data-pipeline/lidar3dlab/pipeline.py -> parents[2] = repo root (works under `pip install -e .` too)
REPO_ROOT = Path(__file__).resolve().parents[2]
DERIVED = REPO_ROOT / "data" / "derived"
MANIFESTS = DERIVED / "manifests"
MODELS = REPO_ROOT / "models"

STAGES = ("preprocess", "feature_extraction", "train", "infer", "evaluate", "export")


def _train_model() -> dict:
    # didactic surrogate: train on the non-degenerate case params; held-out eval uses a disjoint synthetic draw
    params = [c.params for c in registry.list_cases() if c.params.I0 > 0]
    return train.run(params, str(MODELS))


def _holdout_params(seed: int) -> list[SIRParams]:
    rng = make_rng(seed + 999)  # disjoint from training => leakage-safe
    out: list[SIRParams] = []
    for i in range(20):
        out.append(SIRParams(f"_holdout{i}", beta=float(rng.uniform(0.15, 1.2)),
                             gamma=float(rng.uniform(0.15, 0.40)), N=100_000.0, I0=50.0))
    return out


def precompute(case_id: str, seed: int = 42, model: dict | None = None) -> dict:
    case = registry.get_case(case_id)
    if model is None:
        model = _train_model()
    t0 = time.perf_counter()
    # run CONTRACT 1 on the case params (proves the gate + carries flags); a real product reads raw data here
    rep = validate_rows([{"case_id": case.params.case_id, "beta": case.params.beta, "gamma": case.params.gamma,
                          "N": case.params.N, "I0": case.params.I0, "days": case.params.days}])
    params = rep.accepted[0] if rep.accepted else case.params
    result = infer.run(params)
    metrics = evaluate.run(model, _holdout_params(seed))
    run_ms = (time.perf_counter() - t0) * 1000.0
    return export.run(case=case, params=params, result=result, seed=seed, run_ms=run_ms,
                      flags=rep.flagged, metrics=metrics, derived_dir=str(DERIVED), manifests_dir=str(MANIFESTS))


def run_all(seed: int = 42) -> list[dict]:
    model = _train_model()
    entries = []
    for c in registry.list_cases():
        precompute(c.id, seed=seed, model=model)
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
            print(f"  {e['case_id']:20s} [{e['category']}]")
        print(f"index -> {MANIFESTS / 'index.json'}")
    else:
        m = precompute(args.case, args.seed)
        print(f"precomputed {args.case}: lane={m['lane']} bytes={m['artifact']['bytes']} "
              f"metrics={m['metrics']} -> {DERIVED / m['artifact']['path']}")


if __name__ == "__main__":
    main()
