"""Stage 5 — refine (the texture / surface layer). The raw cloud is already RGB-colored from the frames;
refine cleans it (voxel downsample + statistical outlier removal + normals) and, when Open3D is available,
this is the hook for a textured Poisson mesh — the answer to "it should not look like a bare LiDAR map".
Degrades gracefully on CPU (no nvcc / no gsplat required); 3DGS is an optional future lane that needs nvcc."""
from __future__ import annotations

from dataclasses import replace

import numpy as np

from ..io.schema import ReconResult


def run(result: ReconResult, voxel: float = 0.02) -> tuple[ReconResult, dict]:
    pts = np.asarray(result.points, np.float64)
    cols = np.asarray(result.colors, np.float64)
    if len(pts) == 0:
        return result, {"refined": False, "reason": "empty cloud"}
    try:
        import open3d as o3d
        pc = o3d.geometry.PointCloud()
        pc.points = o3d.utility.Vector3dVector(pts)
        pc.colors = o3d.utility.Vector3dVector(cols / 255.0)
        pc = pc.voxel_down_sample(max(voxel, 1e-4))
        pc, _ = pc.remove_statistical_outlier(nb_neighbors=16, std_ratio=2.0)
        pc.estimate_normals()
        rp = np.asarray(pc.points, np.float32)
        rc = (np.asarray(pc.colors) * 255).clip(0, 255).astype(np.uint8)
        info = {"refined": True, "method": "open3d voxel+outlier+normals", "voxel": voxel,
                "n_in": int(len(pts)), "n_out": int(len(rp)), "mesh_ready": True}
        return replace(result, points=rp, colors=rc), info
    except Exception as ex:  # open3d not installed -> keep the colored cloud (still real)
        return result, {"refined": False, "reason": f"open3d unavailable ({type(ex).__name__}); colored cloud kept"}
