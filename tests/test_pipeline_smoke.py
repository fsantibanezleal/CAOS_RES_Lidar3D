"""Pipeline smoke + determinism: a case regenerates deterministically (same seed -> identical artifact), the
degenerate control runs without crashing, and run_all writes the flat index."""
import json

from lidar3dlab import pipeline, registry


def test_case_deterministic_same_seed():
    a = pipeline.precompute("EX02_epidemic", seed=7)
    b = pipeline.precompute("EX02_epidemic", seed=7)
    assert a["artifact"]["bytes"] == b["artifact"]["bytes"]
    trace = json.loads((pipeline.DERIVED / a["artifact"]["path"]).read_text(encoding="utf-8"))
    assert trace["summary"]["peak_I"] > 0


def test_degenerate_control_runs():
    m = pipeline.precompute("CTRL_degenerate", seed=1)  # I0=0 -> no dynamics, must not crash
    trace = json.loads((pipeline.DERIVED / m["artifact"]["path"]).read_text(encoding="utf-8"))
    assert trace["summary"]["peak_I"] == 0.0
    assert trace["summary"]["attack_rate"] == 0.0


def test_run_all_writes_index():
    entries = pipeline.run_all(seed=42)
    assert len(entries) == len(registry.list_cases()) >= 4
    idx = json.loads((pipeline.MANIFESTS / "index.json").read_text(encoding="utf-8"))
    assert idx["n_cases"] == len(entries)
    assert idx["schema"].startswith("example.index/")
