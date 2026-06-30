"""Stage 3 — train: intentionally a documented NO-OP for this product. The reconstruction engine is the
PRETRAINED lingbot-map foundation model (Apache-2.0), used as-is; there is no per-product surrogate to fit.
The stage name is kept (frozen base) and records that fact in the manifest. A future ONNX distillation of a
sub-model (e.g. a low-VRAM single-image preview) would live here."""
from __future__ import annotations


def run(*_args, **_kwargs) -> dict:
    return {"model": "lingbot-map", "pretrained": True, "trained_here": False,
            "note": "foundation model used as-is; no surrogate training (dormant stage, ADR-0057)"}
