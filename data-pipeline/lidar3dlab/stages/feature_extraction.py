"""Stage 2 — feature_extraction: cheap per-frame quality signals (mean luma, sharpness) on sampled frames.
Low luma / low sharpness mark frames whose geometry is unreliable. Light; skipped for synthetic cases."""
from __future__ import annotations

from ..io.schema import FrameFeature, SequenceSpec


def run(spec: SequenceSpec, prepared: dict) -> list[FrameFeature]:
    frames = prepared.get("frames") or []
    if spec.synthetic or not frames:
        return []
    import cv2
    out: list[FrameFeature] = []
    step = max(1, len(frames) // 8)
    for i in range(0, len(frames), step):
        img = cv2.imread(frames[i])
        if img is None:
            continue
        g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        out.append(FrameFeature(idx=i, mean_luma=float(g.mean() / 255.0),
                                sharpness=float(cv2.Laplacian(g, cv2.CV_64F).var())))
    return out
