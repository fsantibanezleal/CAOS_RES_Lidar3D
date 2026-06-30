"""CONTRACT 1 — ingestion (raw -> pipeline). The *bring-your-own-data* gate.

Declares what a valid reconstruction input is: an ordered folder of RGB frames + the inference knobs, with
an EXPLICIT policy. A sequence is ACCEPTED iff it passes; bad inputs are REJECTED with a reason (never
silently coerced); plausible-but-suspicious inputs are FLAGGED (accepted, manifest records the flag). This
is what lets the product be pointed at NEW footage instead of only replaying baked cases. Doc: data/README.md.
"""
from __future__ import annotations

import glob
import os
from dataclasses import dataclass
from typing import Any

from .schema import SequenceSpec

REQUIRED_COLUMNS: tuple[str, ...] = ("case_id", "source_dir")
IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".PNG", ".JPG")

# operationally plausible ranges; outside => REJECT
MIN_FRAMES = 8                  # need at least the anchor/scale block
MAX_FRAMES_HARD = 20_000        # beyond training range; reject (use windowed mode + a different case)
RANGES: dict[str, tuple[float, float, str]] = {
    "max_frames": (8, 2000, "frames processed (8 GB-safe cap)"),
    "image_size": (140, 1036, "px working resolution"),
    "decimation": (1, 32, "keep every Nth pixel"),
    "conf_quantile": (0.0, 0.95, "fraction of low-confidence pixels dropped"),
}
FEW_FRAMES_FLAG = 16            # very short sequences give weak trajectories => FLAG (not reject)


@dataclass
class ContractReport:
    accepted: list[SequenceSpec]
    rejected: list[dict[str, Any]]
    flagged: list[dict[str, Any]]

    @property
    def ok(self) -> bool:
        return len(self.accepted) > 0

    def summary(self) -> str:
        return f"{len(self.accepted)} accepted, {len(self.rejected)} rejected, {len(self.flagged)} flagged"


def count_frames(source_dir: str) -> int:
    return len(sum([glob.glob(os.path.join(source_dir, f"*{e}")) for e in IMAGE_EXTS], []))


def validate_rows(raw_rows: list[dict[str, Any]]) -> ContractReport:
    """Apply CONTRACT 1 to raw rows (e.g. from a CSV manifest of sequences). Deterministic given the data."""
    accepted: list[SequenceSpec] = []
    rejected: list[dict[str, Any]] = []
    flagged: list[dict[str, Any]] = []

    for i, row in enumerate(raw_rows):
        cid = str(row.get("case_id", f"row{i}"))
        missing = [c for c in REQUIRED_COLUMNS if not row.get(c)]
        if missing:
            rejected.append({"row": i, "case_id": cid, "reason": f"missing/empty columns: {missing}"})
            continue

        synthetic = bool(row.get("synthetic", False))
        source_dir = str(row["source_dir"])

        # numeric knobs (defaults from SequenceSpec; validated against RANGES)
        def _num(key: str, default: float) -> float:
            try:
                return float(row.get(key, default))
            except (TypeError, ValueError):
                return float("nan")
        knobs = {k: _num(k, getattr(SequenceSpec, "__dataclass_fields__")[k].default)
                 for k in ("max_frames", "image_size", "decimation", "conf_quantile")}
        bad: list[str] = []
        for name, (lo, hi, _u) in RANGES.items():
            v = knobs[name]
            if v != v or not (lo <= v <= hi):     # NaN or out of range
                bad.append(f"{name}={v:g} out of [{lo:g},{hi:g}]")

        # the actual frames (skipped for synthetic procedural cases)
        if synthetic:
            n_frames = int(knobs["max_frames"])
        else:
            if not os.path.isdir(source_dir):
                rejected.append({"row": i, "case_id": cid, "reason": f"source_dir not found: {source_dir}"})
                continue
            n_frames = count_frames(source_dir)
            if n_frames < MIN_FRAMES:
                rejected.append({"row": i, "case_id": cid,
                                 "reason": f"only {n_frames} frames; need >= {MIN_FRAMES}"})
                continue
            if n_frames > MAX_FRAMES_HARD:
                rejected.append({"row": i, "case_id": cid,
                                 "reason": f"{n_frames} frames > {MAX_FRAMES_HARD} (beyond training range)"})
                continue
        if bad:
            rejected.append({"row": i, "case_id": cid, "reason": "; ".join(bad)})
            continue

        if not synthetic and n_frames < FEW_FRAMES_FLAG:
            flagged.append({"case_id": cid, "flag": f"short sequence ({n_frames} frames): weak trajectory"})

        accepted.append(SequenceSpec(
            case_id=cid, source_dir=source_dir, n_frames=n_frames,
            max_frames=int(min(knobs["max_frames"], n_frames if not synthetic else knobs["max_frames"])),
            image_size=int(knobs["image_size"]), decimation=int(knobs["decimation"]),
            conf_quantile=float(knobs["conf_quantile"]),
            kv_window=int(row.get("kv_window", 16)), scale_frames=int(row.get("scale_frames", 8)),
            camera_iters=int(row.get("camera_iters", 1)), synthetic=synthetic,
            modality=str(row.get("modality", "camera")),
        ))
    return ContractReport(accepted=accepted, rejected=rejected, flagged=flagged)
