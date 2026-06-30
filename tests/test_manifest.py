"""CONTRACT 2 (artifact) tests: the manifest points to a real artifact with the recorded byte size, and the lane
verdict is consistent with the gate."""
from lidar3dlab import pipeline


def test_manifest_matches_artifact_and_gate():
    m = pipeline.precompute("EX02_epidemic", seed=7)
    artifact = pipeline.DERIVED / m["artifact"]["path"]
    assert artifact.exists(), "manifest points to a non-existent artifact"
    assert artifact.stat().st_size == m["artifact"]["bytes"], "manifest byte size drifted from the artifact"
    assert m["schema"].startswith("example.manifest/")
    assert m["lane"] in ("live", "precompute")
    assert m["gate"]["lane"] == m["lane"], "manifest lane disagrees with the gate verdict"
    # the example SIR case is pure-python + numpy + small => must be classified LIVE
    assert m["lane"] == "live", f"expected live lane, got {m['lane']} ({m['gate']['reasons']})"
