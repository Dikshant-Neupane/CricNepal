"""P1 dashboard fixes (2026-10-24 QA pass).

- Phase & Strength and Player Archetypes were complete modules that were
  never wired into the router, so both showed "Module In Progress".
- Player Profiles, Settings and Support were stubs; they are now real
  pages (profiles computed from innings data, settings = live status,
  support = sources/methodology/reporting).
- Matchup Engine presented a fabricated 50/100 "Balanced Matchup" on zero
  data (the loader hardcoded score=50 for empty matchups) and its season
  filter labels were wrong ("2024" filtered to S2; "2023" to S1).
"""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).parent.parent / "app.py")


@pytest.mark.parametrize(
    "key",
    ["phase_analysis", "player_archetypes", "player_profiles", "settings", "support"],
)
def test_former_stub_pages_render_real_content(key):
    at = AppTest.from_file(APP)
    at.session_state["active_page"] = key
    at.run(timeout=180)
    assert len(at.exception) == 0
    md = " ".join(m.value or "" for m in at.markdown)
    assert "Module In Progress" not in md


def test_matchup_no_data_has_no_score():
    from src.dashboard.services.data_loaders import load_matchup_stats

    stats = load_matchup_stats("No Such Batter", "No Such Bowler", "All", 0)
    assert stats is not None
    assert stats["score"] is None
    assert stats["balls_faced"] == 0
    assert stats["confidence"] == "No Data (0 Balls)"


def test_matchup_season_filter_maps_to_correct_season():
    import pandas as pd

    from src.config.paths import PARQUET_DIR
    from src.dashboard.services.data_loaders import load_matchup_stats

    bbb = pd.read_parquet(PARQUET_DIR / "ball_by_ball.parquet")
    matches = pd.read_parquet(
        PARQUET_DIR / "matches.parquet", columns=["match_id", "season"]
    )
    bbb = bbb.merge(matches, on="match_id", how="left")
    counts = (
        bbb.groupby(["batter_name", "bowler_name", "season"])
        .size()
        .unstack(fill_value=0)
    )
    s1_only = counts[(counts.get("S1", 0) >= 6) & (counts.get("S2", 0) == 0)]
    assert not s1_only.empty
    batter, bowler = s1_only.index[0]

    s1_stats = load_matchup_stats(batter, bowler, "S1 (2024)", 0)
    assert s1_stats["balls_faced"] >= 6
    assert s1_stats["score"] is not None

    s2_stats = load_matchup_stats(batter, bowler, "S2 (2025)", 0)
    assert s2_stats["balls_faced"] == 0
    assert s2_stats["score"] is None


def test_matchup_page_shows_insufficient_data_state():
    at = AppTest.from_file(APP)
    at.session_state["active_page"] = "matchup_engine"
    at.run(timeout=180)
    assert len(at.exception) == 0
    md = " ".join(m.value or "" for m in at.markdown)
    # Default pair is below the default 30-ball threshold, so the page must
    # show the insufficient-data state rather than a numeric verdict.
    assert "Insufficient Data" in md
    assert "Balanced Matchup" not in md
