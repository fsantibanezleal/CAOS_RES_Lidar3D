"""CONTRACT 2 — artifact (pipeline -> web). The manifest is the authoritative, versioned record of a baked case:
its params, seed, engine+version, the compact artifact pointer + byte size, the lane/gate verdict, flags from
CONTRACT 1, and the evaluation metrics. The web loads ONLY manifests + artifacts; frontend/src/lib/contract.types.ts
mirrors this schema so a drift fails the build. A flat index.json inventories every case (ADR-0057 default)."""
from __future__ import annotations

from typing import Any

from .. import __version__
from .trace import TRACE_SCHEMA

MANIFEST_SCHEMA = "example.manifest/v2"
INDEX_SCHEMA = "example.index/v1"


def build_case_manifest(
    *,
    case: Any,
    params: Any,
    seed: int,
    artifact_rel: str,
    trace_bytes: int,
    gate: dict,
    flags: list[dict],
    metrics: dict,
) -> dict:
    # Deterministic: a pure function of (params, seed). No wall-clock here (would dirty git on re-run) — the
    # lane/gate verdict + budgets carry the lane decision; live timing is measured in the browser, not committed.
    return {
        "schema": MANIFEST_SCHEMA,
        "case_id": case.id,
        "category": case.category,
        "real_or_synthetic": case.real_or_synthetic,
        "expected_band": case.expected_band,
        "engine": {"package": "lidar3dlab", "version": __version__, "model": "SIR (EXAMPLE — replace per product)"},
        "params": {"beta": params.beta, "gamma": params.gamma, "N": params.N, "I0": params.I0, "days": params.days},
        "seed": seed,
        "artifact": {"path": artifact_rel, "format": "json", "trace_schema": TRACE_SCHEMA, "bytes": trace_bytes},
        "lane": gate["lane"],
        "gate": gate,
        "flags": flags,
        "metrics": metrics,
    }


def build_index(entries: list[dict]) -> dict:
    """entries: [{case_id, category, manifest_path}] -> the flat authoritative inventory."""
    return {
        "schema": INDEX_SCHEMA,
        "engine_version": __version__,
        "n_cases": len(entries),
        "cases": sorted(entries, key=lambda e: e["case_id"]),
    }
