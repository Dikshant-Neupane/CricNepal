"""Display-correctness fixes (2026-10-24 QA pass, final batch).

- Bowling page: the batter-hand split and tactical directives were
  permanent "unavailable" placeholders; both are now computed from data.
- Player form table: avg economy / strike rate were means of per-match
  rates, which contradicted the same page's guidance (a bowler shown at
  9.44 whose true aggregate economy was ~6.0). They are aggregates now.
- Dashboard KPI cards carried a sparkline drawn from random numbers.
"""
from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).parent.parent / "app.py")


def test_hand_split_computed_from_data():
    from src.dashboard.page_modules.bowling_intelligence import _hand_split_rows

    rows = _hand_split_rows()
    assert {r["hand"] for r in rows} == {"Left-hand batters", "Right-hand batters"}
    by_hand = {r["hand"]: r for r in rows}
    # Verified against ball-by-ball: S2 Janakpur bowling conceded more
    # per over to left-handers (8.63) than right-handers (7.30).
    assert by_hand["Left-hand batters"]["econ"] == pytest.approx(8.63, abs=0.05)
    assert by_hand["Right-hand batters"]["econ"] == pytest.approx(7.30, abs=0.05)


def test_tactical_directives_derive_from_phases():
    from src.dashboard.page_modules.bowling_intelligence import _tactical_directives

    phases = [
        {"name": "POWERPLAY (1–6)", "econ": "7.10", "dot": "38.0%", "wkts": "12"},
        {"name": "DEATH (16–20)", "econ": "10.20", "dot": "25.0%", "wkts": "20"},
    ]
    out = _tactical_directives(phases)
    assert len(out) == 3
    assert any("DEATH" in d and "10.20" in d for d in out)
    assert _tactical_directives([]) == []


def test_form_table_uses_aggregate_economy_and_strike_rate():
    from src.dashboard.services.player_form import build_player_form_table

    base = {
        "player_name": "Test Bowler",
        "team_name": "Janakpur Bolts",
        "player_role": "Bowler",
        "runs_scored": 0,
        "balls_faced": 0,
        "strike_rate": 0.0,
        "economy_rate": 0.0,
    }
    # Spell A: 1 over, 20 conceded (rate 20.0). Spell B: 4 overs, 20
    # conceded (rate 5.0). Mean of rates = 12.5; true aggregate = 8.0.
    rows = [
        {**base, "match_id": f"m{i}", "balls_bowled": bb, "runs_conceded": rc,
         "wickets_taken": 1, "economy_rate": rc / (bb / 6)}
        for i, (bb, rc) in enumerate([(6, 20), (24, 20)])
    ]
    innings = pd.DataFrame(rows)
    matches = pd.DataFrame(
        {
            "match_id": ["m0", "m1"],
            "match_date": pd.to_datetime(["2025-11-20", "2025-11-22"]),
            "season": ["S2", "S2"],
            "tournament_name": ["Nepal Premier League", "Nepal Premier League"],
            "winner_name": ["Janakpur Bolts", "Janakpur Bolts"],
        }
    )
    table = build_player_form_table(innings, matches, team_name="Janakpur Bolts",
                                    n_recent=10, min_matches=1)
    assert len(table) == 1
    assert table.iloc[0]["avg_economy"] == pytest.approx(8.0)


def test_bowling_page_shows_split_and_directives():
    at = AppTest.from_file(APP)
    at.session_state["active_page"] = "bowling_analysis"
    at.run(timeout=180)
    assert len(at.exception) == 0
    md = " ".join(m.value or "" for m in at.markdown)
    assert "Left-hand batters" in md
    assert "Most expensive phase" in md
    assert "Detailed batter hand splits unavailable." not in md


def test_dashboard_has_no_random_sparkline_or_hardcoded_banner():
    at = AppTest.from_file(APP)
    at.session_state["active_page"] = "dashboard"
    at.run(timeout=180)
    assert len(at.exception) == 0
    md = " ".join(m.value or "" for m in at.markdown)
    assert "polyline" not in md  # the random sparkline svg is gone
    assert "AI forecasts ready" not in md
    assert "recruiting shortlist" in md  # computed banner instead
