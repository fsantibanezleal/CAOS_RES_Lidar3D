"""Pipeline smoke + determinism: the synthetic case regenerates deterministically (same seed -> identical
artifact bytes) and produces a sensible colored cloud + trajectory, on CPU, with no GPU/model."""
import json

from lidar3dlab import pipeline


def test_synthetic_deterministic_same_seed():
    a = pipeline.precompute("SYN_orbit", seed=7)
    b = pipeline.precompute("SYN_orbit", seed=7)
    assert a["artifact"]["bytes"] == b["artifact"]["bytes"], "synthetic bake is not deterministic"
    trace = json.loads((pipeline.DERIVED / a["artifact"]["path"]).read_text(encoding="utf-8"))
    assert trace["schema"].startswith("lidar3d.recon/")
    assert trace["n_points"] > 1000, "implausibly few points"
    assert trace["summary"]["path_length_m"] > 0, "no camera trajectory"
    assert len(trace["points_b64"]) > 0 and len(trace["colors_b64"]) > 0, "missing cloud / colors"


def test_synthetic_runs_on_cpu_precompute():
    m = pipeline.precompute("SYN_orbit", seed=1)
    assert m["lane"] == "precompute"
    assert m["engine"]["pretrained"] is False  # synthetic engine, not the pretrained model
