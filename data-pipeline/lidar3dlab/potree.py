"""Build a Potree v2 octree from a committed trace, for the Potree LOD web viewer (the third-and-scalable
renderer). Exports the RGB cloud to a binary PLY, then runs PotreeConverter (a native binary; path via
LIDAR3D_POTREECONVERTER) to produce an octree (metadata.json + octree.bin + hierarchy.bin) under
frontend/public/potree/<case>/ (committed static assets served by the SPA). This is the offline conversion step
of the precompute pipeline.

Coordinate note: the web renderers map OpenCV world (Y-down, Z-forward) -> render frame (x,-y,-z). We bake the
octree already in the render frame so Potree matches three.js/deck.gl exactly.
"""
from __future__ import annotations

import base64
import json
import os
import subprocess
import tempfile
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]


def potreeconverter() -> str:
    """Path to the native PotreeConverter binary. Set LIDAR3D_POTREECONVERTER to your local install; falls back to
    `PotreeConverter` on PATH (no machine-specific path is baked into this public repo)."""
    return os.environ.get("LIDAR3D_POTREECONVERTER", "PotreeConverter")


def _write_las(pts: np.ndarray, cols: np.ndarray, path: Path) -> None:
    """LAS 1.2 point-format-2 (XYZ + 16-bit RGB). PotreeConverter's PLY reader is unreliable; LAS is its native
    format and parses correctly."""
    import laspy
    h = laspy.LasHeader(point_format=2, version="1.2")
    h.offsets = pts.min(0)
    h.scales = [0.001, 0.001, 0.001]
    las = laspy.LasData(h)
    las.x, las.y, las.z = pts[:, 0], pts[:, 1], pts[:, 2]
    c16 = cols.astype(np.uint16) << 8                    # LAS RGB is 16-bit
    las.red, las.green, las.blue = c16[:, 0], c16[:, 1], c16[:, 2]
    las.write(str(path))


def build(case_id: str, out_root: str | Path) -> Path:
    d = json.load(open(REPO / "data" / "derived" / case_id / "trace.json"))
    pts = np.frombuffer(base64.b64decode(d["points_b64"]), "<f4").reshape(-1, 3).astype(np.float64).copy()
    cols = np.frombuffer(base64.b64decode(d["colors_b64"]), np.uint8).reshape(-1, 3)
    pts[:, 1] *= -1.0                                    # OpenCV -> render frame (match three.js / deck.gl)
    pts[:, 2] *= -1.0
    out = Path(out_root) / case_id
    if out.exists():
        for p in sorted(out.glob("*")):
            p.unlink()
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=os.environ.get("LIDAR3D_PC_TMP", None)) as tmp:
        las = Path(tmp) / f"{case_id}.las"
        _write_las(pts, cols, las)
        subprocess.run([potreeconverter(), "-i", str(las), "-o", str(out)], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    return out


def build_all(out_root: str | Path) -> list[str]:
    done = []
    for tr in sorted((REPO / "data" / "derived").glob("*/trace.json")):
        cid = tr.parent.name
        try:
            build(cid, out_root)
            done.append(cid)
        except Exception as e:  # noqa: BLE001
            print(f"  SKIP {cid}: {e}")
    return done


if __name__ == "__main__":
    import sys
    root = REPO / "frontend" / "public" / "potree"
    if len(sys.argv) > 1:
        print("built:", build(sys.argv[1], root))
    else:
        print("built:", build_all(root))
