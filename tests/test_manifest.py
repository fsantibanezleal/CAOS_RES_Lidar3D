"""CONTRACT 2 (artifact) tests: the manifest points to a real artifact with the recorded byte size, the lane
verdict is consistent with the gate, and NO absolute path is leaked into the committed manifest."""
from lidar3dlab import pipeline


def test_manifest_matches_artifact_and_gate():
    m = pipeline.precompute("SYN_orbit", seed=7)
    artifact = pipeline.DERIVED / m["artifact"]["path"]
    assert artifact.exists(), "manifest points to a non-existent artifact"
    assert artifact.stat().st_size == m["artifact"]["bytes"], "manifest byte size drifted from the artifact"
    assert m["schema"].startswith("lidar3d.manifest/")
    assert m["lane"] == m["gate"]["lane"], "manifest lane disagrees with the gate verdict"
    # the lingbot/synthetic engines are not Pyodide-safe => must be precompute, never live
    assert m["lane"] == "precompute", f"expected precompute, got {m['lane']} ({m['gate']['reasons']})"


def test_no_absolute_path_leaked():
    m = pipeline.precompute("SYN_orbit", seed=7)
    src = m["params"]["source"]
    assert "/" not in src and "\\" not in src and ":" not in src, f"leaked a path in the manifest: {src!r}"
