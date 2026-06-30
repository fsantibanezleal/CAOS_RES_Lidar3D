"""Stage 6 — export (CONTRACT 2): write the compact trace artifact + the case manifest. Records the measured
lane/gate verdict (always 'precompute' here — the engine is not browser-runnable), the artifact byte size,
the CONTRACT-1 flags, the refine info and the evaluation metrics."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ..core.gate import classify_lane
from ..core.manifest import build_case_manifest
from ..core.trace import build_trace
from ..io.formats import write_json


def run(*, case: Any, params: Any, result: Any, refine_info: dict, seed: int, run_ms: float,
        flags: list[dict], metrics: dict, engine: dict, derived_dir: str, manifests_dir: str) -> dict:
    trace = build_trace(result, refine_info)
    artifact_rel = f"{case.id}/trace.json"
    trace_bytes = write_json(Path(derived_dir) / artifact_rel, trace)
    # the lingbot/synthetic engines are NOT Pyodide-safe (torch / matplotlib / opencv) -> precompute lane.
    wheels = ({"numpy", "matplotlib", "pillow"} if params.synthetic
              else {"torch", "numpy", "matplotlib", "pillow", "opencv-python"})
    gate = classify_lane(pure_python=False, wheels=wheels, run_ms=run_ms, trace_bytes=trace_bytes)
    manifest = build_case_manifest(
        case=case, params=params, seed=seed, artifact_rel=artifact_rel, trace_bytes=trace_bytes,
        gate=gate, flags=flags, metrics=metrics, engine=engine, refine=refine_info,
    )
    write_json(Path(manifests_dir) / f"{case.id}.json", manifest)
    return manifest
