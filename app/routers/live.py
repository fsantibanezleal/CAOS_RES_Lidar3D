"""LIVE lane: real-time reconstruction of YOUR OWN footage on the machine's GPU.

POST a folder of ordered RGB frames (or a TUM-layout RGB-D root) and get back the reconstruction (poses +
cloud summary + optional full trace) computed by any registered engine. This is the ACTIVE local-GPU lane:
it cannot run inside the static public page (the engines need CUDA), so you run this API next to your GPU:

    uvicorn app.main:app --port 8000
    curl -X POST localhost:8000/api/live/reconstruct -H "Content-Type: application/json" \
         -d '{"source_dir": "C:/footage/my_sweep", "engine": "own-depthpose", "max_frames": 120}'

Engines: `own-depthpose` (Estela, RGB-only), `rgbd-sensor` (Track B, TUM-layout RGB-D root),
`depth-icp` (classical depth-only), `lingbot` (pointmap SOTA reference; needs the vendored checkpoint).
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

REPO_ROOT = Path(__file__).resolve().parents[2]
_DP = str(REPO_ROOT / "data-pipeline")
if _DP not in sys.path:  # the API imports the engine package in-place (no install step)
    sys.path.insert(0, _DP)

router = APIRouter(prefix="/api/live")


class LiveRequest(BaseModel):
    source_dir: str = Field(description="folder of ordered RGB frames, or a TUM-layout RGB-D sequence root")
    engine: str = Field(default="own-depthpose", description="own-depthpose | rgbd-sensor | depth-icp | lingbot")
    max_frames: int = Field(default=120, ge=8, le=2000)
    include_trace: bool = Field(default=False, description="include the full point cloud in the response")
    intrinsics: str = Field(default="", description='optional "fx,fy,cx,cy,W,H" native-pixel intrinsics')


@router.get("/health")
def health() -> dict:
    """Which engines can run HERE (GPU presence decides the heavy ones)."""
    from lidar3dlab.model.agnostic import KIND, available
    cuda = False
    try:
        import torch
        cuda = bool(torch.cuda.is_available())
    except Exception:  # noqa: BLE001 (no torch in this env)
        pass
    return {"engines": available(), "kinds": KIND, "cuda": cuda,
            "note": "own-depthpose/lingbot need CUDA; rgbd-sensor/depth-icp run on CPU (slower)"}


@router.post("/reconstruct")
def reconstruct(req: LiveRequest) -> dict:
    from lidar3dlab.io.schema import SequenceSpec
    from lidar3dlab.model.agnostic import get_engine

    src = Path(req.source_dir)
    if not src.exists():
        raise HTTPException(status_code=400, detail=f"source_dir not found: {src}")
    spec = SequenceSpec(case_id=f"LIVE_{src.name}", source_dir=str(src), n_frames=0,
                        max_frames=req.max_frames, decimation=2, engine=req.engine,
                        intrinsics=req.intrinsics, max_render_depth=6.0)
    t0 = time.perf_counter()
    try:
        r = get_engine(req.engine)(spec, 42)
    except KeyError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except FileNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    ms = (time.perf_counter() - t0) * 1000.0
    out: dict = {
        "case_id": r.case_id, "engine": req.engine, "n_frames": r.n_frames,
        "n_points": int(len(r.points)), "path_length_m": round(float(r.path_length), 3),
        "bbox_min": r.bbox_min, "bbox_max": r.bbox_max, "run_ms": round(ms, 1),
        "poses_c2w": [[round(float(v), 6) for v in row] for row in r.poses_c2w.tolist()],
    }
    if req.include_trace:
        import base64
        out["points_b64"] = base64.b64encode(r.points.astype("float32").tobytes()).decode()
        out["colors_b64"] = base64.b64encode(r.colors.astype("uint8").tobytes()).decode()
    return out
