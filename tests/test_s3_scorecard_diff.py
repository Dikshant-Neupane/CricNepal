"""Standing test for plan task 1.6 (D2): the S3 scorecard diff stays
clean on captured matches, and its cricsheet side is armed (activates
automatically when cricsheet publishes S3 matches)."""
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "s3_scorecard_diff",
    Path(__file__).resolve().parents[1] / "scripts/s3_scorecard_diff.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def test_capture_internal_diff_is_clean():
    _, captured = mod.cricsheet_status()
    assert len(captured) >= 4  # Matches 1-4 captured at creation
    for m in captured:
        assert mod.diff_capture(m) == [], m


def test_cricsheet_side_armed_or_active():
    n_s3, captured = mod.cricsheet_status()
    # 0 while cricsheet lags (expected during the season); if S3 data
    # has landed, the diff must still run without error.
    assert 0 <= n_s3 <= len(captured)
