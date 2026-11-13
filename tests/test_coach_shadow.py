"""Coach shadow series (Pre-registration Amendment #7).

Guards: the frozen log is never modified; adjustments match the
frozen rule on the registered samples; the shadow file covers
exactly the 28 locked league fixtures and stays inside the clip.
"""
import hashlib
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).parent.parent
# Re-pinned 2026-11-13: the previously pinned file (md5 e02cea1d...,
# 70 rows, pinned 2026-11-07) is a byte-exact prefix of the current
# log; the only additions since are six P2_post_toss lock rows
# appended by the lock scripts — Matches 19, 20, 21, 22, 23, 24
# (commits 024da0c, e5c0c8b, c3ffad4, 19d81a1, 363c437, fa64889;
# toss winner/decision and p values agree with each commit
# message), taking the P2 count to nineteen and the log to 76 rows.
# No earlier row changed.
FROZEN_MD5_AT_REGISTRATION = "1f2c723bebe484a11c42a9f8b2d41013"


def test_frozen_log_untouched():
    md5 = hashlib.md5((ROOT / "data/predictions/frozen_log.csv").read_bytes()).hexdigest()
    assert md5 == FROZEN_MD5_AT_REGISTRATION


def test_adjustments_match_rule():
    from scripts.coach_shadow import adjustments, coach_adjustment

    assert coach_adjustment(0, 0) == 0.0
    adj = adjustments()
    assert adj["Lumbini Lions"] == pytest_approx(1.67)
    assert adj["Kathmandu Gorkhas"] == pytest_approx(0.89)
    assert adj["Karnali Yaks"] == pytest_approx(-0.69)
    assert adj["Janakpur Bolts"] == pytest_approx(-1.04)
    for team in ["Sudurpaschim Royals", "Biratnagar Kings", "Chitwan Rhinos", "Pokhara Avengers"]:
        assert adj[team] == 0.0


def pytest_approx(v):
    import pytest

    return pytest.approx(v, abs=0.01)


def test_shadow_file_shape_and_bounds():
    shadow = pd.read_csv(ROOT / "data/predictions/coach_shadow.csv")
    assert len(shadow) == 28
    assert (shadow.stage == "COACH_shadow_preseason").all()
    assert shadow.match_id.is_unique
    assert shadow.p_team_1_win.between(0.05, 0.95).all()
    # The registered claim: coach adjustments move probabilities by
    # less than half a percentage point on every fixture.
    assert (shadow.p_team_1_win - shadow.p_champion).abs().max() < 0.005
