"""CONTRACT 1 (ingestion) tests: a good synthetic spec validates; bad inputs are rejected with a reason
(never silently coerced); short real sequences are flagged."""
from lidar3dlab.io.contract import validate_rows


def test_synthetic_spec_accepted():
    rep = validate_rows([{"case_id": "s", "source_dir": "synthetic://x", "synthetic": True, "max_frames": 24}])
    assert rep.ok and len(rep.accepted) == 1 and rep.accepted[0].synthetic and not rep.rejected


def test_missing_source_rejected():
    rep = validate_rows([{"case_id": "a"}])  # no source_dir
    assert len(rep.accepted) == 0 and len(rep.rejected) == 1
    assert "missing" in rep.rejected[0]["reason"]


def test_missing_real_dir_rejected_not_coerced():
    rep = validate_rows([{"case_id": "a", "source_dir": "/definitely/not/here"}])
    assert len(rep.accepted) == 0 and "not found" in rep.rejected[0]["reason"]


def test_out_of_range_knob_rejected():
    rep = validate_rows([{"case_id": "a", "source_dir": "synthetic://x", "synthetic": True, "max_frames": 1}])
    assert len(rep.accepted) == 0  # max_frames=1 is below the [8,2000] range
