"""Geometry correctness (our own `model/geom.py`). These assertions make the "reconstruction built behind the
camera / moving backward" bug impossible: a known ground-truth cube must round-trip, and every reconstructed
point must lie IN FRONT of the camera along its forward axis."""
import numpy as np

from lidar3dlab.model import geom


def test_project_unproject_roundtrip_and_forward():
    # a known ground-truth cube, placed IN FRONT of a camera at the origin (z = 4..6)
    g = np.array([[x, y, z] for x in (-1, 1) for y in (-1, 1) for z in (4.0, 6.0)], np.float64)
    eye = np.array([0.0, 0.0, 0.0])
    target = np.array([0.0, 0.0, 5.0])
    c2w = geom.look_at(eye, target)
    K = geom.intrinsics_from_fov(640, 480, 60.0)

    uv, d = geom.project(g, K, c2w)
    assert np.all(d > 0), "the cube is in front of the camera, depths must be positive"

    fx, fy, cx, cy = K[0, 0], K[1, 1], K[0, 2], K[1, 2]
    cam = np.stack([(uv[:, 0] - cx) / fx * d, (uv[:, 1] - cy) / fy * d, d], -1)
    back = cam @ c2w[:3, :3].T + c2w[:3, 3]
    assert np.allclose(back, g, atol=1e-4), "project->unproject must recover the exact world points"

    # the camera forward points TOWARD the scene (a backward reconstruction would violate this)
    assert np.dot(geom.camera_forward(c2w), target - eye) > 0


def test_unproject_image_places_points_in_front():
    K = geom.intrinsics_from_fov(64, 48, 60.0)
    depth = np.full((48, 64), 5.0, np.float32)
    eye = np.array([0.0, 0.0, 0.0])
    c2w = geom.look_at(eye, np.array([0.0, 0.0, 5.0]))
    pts, cols = geom.unproject(depth, K, c2w)
    assert len(pts) == 48 * 64
    assert len(cols) == len(pts)
    fwd = geom.camera_forward(c2w)
    assert np.all((pts - eye) @ fwd > 0), "every reconstructed point must be ahead of the camera"


def test_invert_se3_is_true_inverse():
    c2w = geom.look_at(np.array([1.0, 2.0, 3.0]), np.array([0.0, 0.0, 0.0]))
    w2c = geom.invert_se3(c2w)
    assert np.allclose(w2c @ c2w, np.eye(4), atol=1e-9)
