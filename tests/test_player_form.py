"""Tests for Season 3 player form scoring and role guidance."""

from __future__ import annotations

import pandas as pd

from src.dashboard.services.player_form import (
    build_player_form_table,
    classify_form_band,
    summarize_selection_decisions,
)


def _sample_matches() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"match_id": "m1", "match_date": "2024-12-01", "season": "S1", "tournament_name": "NPL Season 1", "winner_name": "Janakpur Bolts"},
            {"match_id": "m2", "match_date": "2024-12-05", "season": "S2", "tournament_name": "NPL Season 2", "winner_name": "Janakpur Bolts"},
            {"match_id": "m3", "match_date": "2025-01-10", "season": "S2", "tournament_name": "KP Oli Cup", "winner_name": "Janakpur Bolts"},
            {"match_id": "m4", "match_date": "2025-01-15", "season": "S2", "tournament_name": "President Cup", "winner_name": "Janakpur Bolts"},
        ]
    )


def _sample_player_innings() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"match_id": "m1", "player_name": "A Batter", "team_name": "Janakpur Bolts", "player_role": "Batter", "runs_scored": 35, "balls_faced": 28, "strike_rate": 125.0, "balls_bowled": 0, "wickets_taken": 0, "economy_rate": None},
            {"match_id": "m2", "player_name": "A Batter", "team_name": "Janakpur Bolts", "player_role": "Batter", "runs_scored": 48, "balls_faced": 30, "strike_rate": 160.0, "balls_bowled": 0, "wickets_taken": 0, "economy_rate": None},
            {"match_id": "m3", "player_name": "A Batter", "team_name": "Janakpur Bolts", "player_role": "Batter", "runs_scored": 40, "balls_faced": 26, "strike_rate": 153.8, "balls_bowled": 0, "wickets_taken": 0, "economy_rate": None},
            {"match_id": "m1", "player_name": "B Bowler", "team_name": "Janakpur Bolts", "player_role": "Bowler", "runs_scored": 4, "balls_faced": 4, "strike_rate": 100.0, "balls_bowled": 24, "wickets_taken": 1, "economy_rate": 7.5},
            {"match_id": "m2", "player_name": "B Bowler", "team_name": "Janakpur Bolts", "player_role": "Bowler", "runs_scored": 2, "balls_faced": 3, "strike_rate": 66.7, "balls_bowled": 24, "wickets_taken": 2, "economy_rate": 6.8},
            {"match_id": "m4", "player_name": "B Bowler", "team_name": "Janakpur Bolts", "player_role": "Bowler", "runs_scored": 0, "balls_faced": 0, "strike_rate": 0.0, "balls_bowled": 24, "wickets_taken": 0, "economy_rate": 9.4},
            {"match_id": "m2", "player_name": "C Utility", "team_name": "Janakpur Bolts", "player_role": "All-rounder", "runs_scored": 18, "balls_faced": 15, "strike_rate": 120.0, "balls_bowled": 12, "wickets_taken": 1, "economy_rate": 7.0},
            {"match_id": "m3", "player_name": "C Utility", "team_name": "Janakpur Bolts", "player_role": "All-rounder", "runs_scored": 12, "balls_faced": 11, "strike_rate": 109.1, "balls_bowled": 18, "wickets_taken": 1, "economy_rate": 8.0},
            {"match_id": "m4", "player_name": "C Utility", "team_name": "Janakpur Bolts", "player_role": "All-rounder", "runs_scored": 8, "balls_faced": 10, "strike_rate": 80.0, "balls_bowled": 12, "wickets_taken": 0, "economy_rate": 9.5},
        ]
    )


def test_classify_form_band_thresholds():
    assert classify_form_band(75.0) == "In Form"
    assert classify_form_band(60.0) == "Stable"
    assert classify_form_band(45.0) == "Risky"
    assert classify_form_band(30.0) == "Out of Form"


def test_build_player_form_table_returns_rankable_output():
    result = build_player_form_table(_sample_player_innings(), _sample_matches(), n_recent=3, min_matches=3)

    assert not result.empty
    assert result.iloc[0]["player_name"] == "A Batter"
    assert set(result["player_name"]) == {"A Batter", "B Bowler", "C Utility"}
    assert {"raw_form_score", "weighted_form_score", "form_band", "recommended_role", "role_recommendation"}.issubset(result.columns)


def test_weighted_form_prioritizes_higher_value_competitions():
    matches = pd.DataFrame(
        [
            {"match_id": "npl_1", "match_date": "2025-01-01", "season": "S2", "tournament_name": "NPL Season 2", "winner_name": "Janakpur Bolts"},
            {"match_id": "pres_1", "match_date": "2025-01-02", "season": "S2", "tournament_name": "President Cup", "winner_name": "Janakpur Bolts"},
            {"match_id": "npl_2", "match_date": "2025-01-03", "season": "S2", "tournament_name": "NPL Season 2", "winner_name": "Janakpur Bolts"},
            {"match_id": "pres_2", "match_date": "2025-01-04", "season": "S2", "tournament_name": "President Cup", "winner_name": "Janakpur Bolts"},
            {"match_id": "npl_3", "match_date": "2025-01-05", "season": "S2", "tournament_name": "NPL Season 2", "winner_name": "Janakpur Bolts"},
            {"match_id": "pres_3", "match_date": "2025-01-06", "season": "S2", "tournament_name": "President Cup", "winner_name": "Janakpur Bolts"},
        ]
    )
    player_innings = pd.DataFrame(
        [
            {"match_id": "npl_1", "player_name": "High Tier", "team_name": "Janakpur Bolts", "player_role": "Batter", "runs_scored": 45, "balls_faced": 30, "strike_rate": 150.0, "balls_bowled": 0, "wickets_taken": 0, "economy_rate": None},
            {"match_id": "pres_1", "player_name": "High Tier", "team_name": "Janakpur Bolts", "player_role": "Batter", "runs_scored": 10, "balls_faced": 12, "strike_rate": 83.3, "balls_bowled": 0, "wickets_taken": 0, "economy_rate": None},
            {"match_id": "npl_2", "player_name": "High Tier", "team_name": "Janakpur Bolts", "player_role": "Batter", "runs_scored": 42, "balls_faced": 28, "strike_rate": 150.0, "balls_bowled": 0, "wickets_taken": 0, "economy_rate": None},
            {"match_id": "pres_2", "player_name": "Low Tier", "team_name": "Janakpur Bolts", "player_role": "Batter", "runs_scored": 44, "balls_faced": 28, "strike_rate": 157.1, "balls_bowled": 0, "wickets_taken": 0, "economy_rate": None},
            {"match_id": "npl_3", "player_name": "Low Tier", "team_name": "Janakpur Bolts", "player_role": "Batter", "runs_scored": 12, "balls_faced": 16, "strike_rate": 75.0, "balls_bowled": 0, "wickets_taken": 0, "economy_rate": None},
            {"match_id": "pres_3", "player_name": "Low Tier", "team_name": "Janakpur Bolts", "player_role": "Batter", "runs_scored": 46, "balls_faced": 30, "strike_rate": 153.3, "balls_bowled": 0, "wickets_taken": 0, "economy_rate": None},
        ]
    )

    result = build_player_form_table(player_innings, matches, n_recent=3, min_matches=3)
    high_tier = result[result["player_name"] == "High Tier"].iloc[0]
    low_tier = result[result["player_name"] == "Low Tier"].iloc[0]

    assert high_tier["weighted_form_score"] > low_tier["weighted_form_score"]


def test_role_recommendation_references_s1_s2_delta():
    result = build_player_form_table(_sample_player_innings(), _sample_matches(), n_recent=3, min_matches=3)
    batter = result[result["player_name"] == "A Batter"].iloc[0]

    assert "S2" in batter["role_recommendation"]
    assert "S1" in batter["role_recommendation"]
    assert batter["recommended_role"].lower() in batter["role_recommendation"].lower()


def test_selection_summary_returns_three_decision_blocks():
    result = build_player_form_table(_sample_player_innings(), _sample_matches(), n_recent=3, min_matches=3)
    summary = summarize_selection_decisions(result)

    assert len(summary) == 3
    assert [item["label"] for item in summary] == ["Insight", "Risk", "Recommended Action"]
