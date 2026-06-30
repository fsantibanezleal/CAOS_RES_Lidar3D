"""LiDAR modality: the synthetic LiDAR case registers scans via Open3D point-to-plane ICP and produces a
height-colored map + a recovered trajectory, on CPU (CI-safe). The second real engine of the lab."""
from lidar3dlab import pipeline


def test_synthetic_lidar_odometry():
    m = pipeline.precompute("LID_synthetic", seed=1)
    assert m["lane"] == "precompute"
    assert "ICP" in m["engine"]["model"], "expected the LiDAR ICP engine label"
    assert m["metrics"]["n_points"] > 5000, "implausibly few registered points"
    assert m["metrics"]["path_length_m"] > 0.5, "ICP recovered no motion"
