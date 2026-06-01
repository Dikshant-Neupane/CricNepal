import pandas as pd

from src.dashboard.services.metrics import (
    compute_team_kpis,
    compute_weighted_form_index,
    compute_season_win_pct,
    compute_season_kpis,
    compute_season_delta,
    compute_form_index,
)


def _sample_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "season": "S1",
                "competition_name": "NPL Season 1",
                "result": "W",
                "runs_for": 180,
                "runs_against": 170,
                "overs_faced": 20.0,
                "overs_bowled": 20.0,
            },
            {
                "season": "S2",
                "competition_name": "NPL Season 2",
                "result": "L",
                "runs_for": 150,
                "runs_against": 168,
                "overs_faced": 20.0,
                "overs_bowled": 20.0,
            },
            {
                "season": "S2",
                "competition_name": "NPL Season 2",
                "result": "NR",
                "runs_for": 0,
                "runs_against": 0,
                "overs_faced": 0.0,
                "overs_bowled": 0.0,
            },
        ]
    )


def test_compute_team_kpis_basic() -> None:
    df = _sample_df()
    kpis = compute_team_kpis(df)

    assert kpis["matches"] == 3
    assert kpis["wins"] == 1
    assert kpis["losses"] == 1
    assert kpis["no_results"] == 1
    assert kpis["win_pct"] == 33.3


def test_compute_weighted_form_index_uses_competition_weights() -> None:
    df = _sample_df()
    # weighted points = 0.15*1 + 0.50*0 + 0.50*0.5 = 0.40
    # total weight = 1.15 -> form = 34.8
    assert compute_weighted_form_index(df) == 34.8


def test_compute_season_win_pct_handles_missing_season() -> None:
    df = _sample_df()
    assert compute_season_win_pct(df, "S1") == 100.0
    assert compute_season_win_pct(df, "UNKNOWN") == 0.0


# Day 3 enhancement tests - compute_season_kpis

def test_compute_season_kpis_returns_per_season_metrics() -> None:
    df = _sample_df()
    season_kpis = compute_season_kpis(df)
    
    assert "S1" in season_kpis
    assert "S2" in season_kpis
    
    s1 = season_kpis["S1"]
    assert s1["n"] == 1
    assert s1["wins"] == 1
    assert s1["losses"] == 0
    assert s1["win_pct"] == 100.0
    
    s2 = season_kpis["S2"]
    assert s2["n"] == 2
    assert s2["wins"] == 0
    assert s2["losses"] == 2


def test_compute_season_kpis_calculates_nrr_correctly() -> None:
    df = pd.DataFrame([
        {
            "season": "S1",
            "competition_name": "NPL Season 1",
            "result": "W",
            "runs_for": 200,
            "runs_against": 150,
            "overs_faced": 20.0,
            "overs_bowled": 20.0,
        },
        {
            "season": "S1",
            "competition_name": "NPL Season 1",
            "result": "W",
            "runs_for": 180,
            "runs_against": 160,
            "overs_faced": 20.0,
            "overs_bowled": 20.0,
        }
    ])
    
    season_kpis = compute_season_kpis(df)
    s1 = season_kpis["S1"]
    
    # NRR = (runs_for/overs_faced) - (runs_against/overs_bowled)
    # NRR = (380/40) - (310/40) = 9.5 - 7.75 = 1.75
    assert s1["nrr"] == 1.75


def test_compute_season_kpis_handles_empty_dataframe() -> None:
    df = pd.DataFrame()
    season_kpis = compute_season_kpis(df)
    assert season_kpis == {}


# Day 3 enhancement tests - compute_season_delta

def test_compute_season_delta_calculates_differences() -> None:
    season_kpis = {
        "S1": {"n": 10, "wins": 7, "losses": 3, "win_pct": 70.0, "nrr": 0.5},
        "S2": {"n": 7, "wins": 2, "losses": 5, "win_pct": 28.6, "nrr": -0.3},
    }
    
    delta = compute_season_delta(season_kpis, "S1", "S2")
    
    assert delta["win_pct_delta"] == -41.4  # 28.6 - 70.0
    assert delta["nrr_delta"] == -0.8  # -0.3 - 0.5
    assert delta["matches_delta"] == -3  # 7 - 10


def test_compute_season_delta_handles_missing_seasons() -> None:
    season_kpis = {"S1": {"n": 10, "wins": 7, "losses": 3, "win_pct": 70.0, "nrr": 0.5}}
    
    delta = compute_season_delta(season_kpis, "S1", "S2")
    
    # Should use 0.0 defaults for missing S2
    assert delta["win_pct_delta"] == -70.0
    assert delta["nrr_delta"] == -0.5
    assert delta["matches_delta"] == -10


# Day 3 enhancement tests - compute_form_index

def test_compute_form_index_calculates_recent_win_rate() -> None:
    df = pd.DataFrame([
        {"result": "W", "match_date": "2026-01-01"},
        {"result": "W", "match_date": "2026-01-02"},
        {"result": "L", "match_date": "2026-01-03"},
        {"result": "W", "match_date": "2026-01-04"},
        {"result": "L", "match_date": "2026-01-05"},
        {"result": "W", "match_date": "2026-01-06"},  # Most recent
    ])
    
    # Last 5 matches: W, W, L, W, L = 3/5 = 60%
    form = compute_form_index(df, n_recent=5)
    assert form == 60.0


def test_compute_form_index_handles_fewer_matches_than_requested() -> None:
    df = pd.DataFrame([
        {"result": "W"},
        {"result": "W"},
    ])
    
    # Only 2 matches but asking for last 5 -> 2/2 = 100%
    form = compute_form_index(df, n_recent=5)
    assert form == 100.0


def test_compute_form_index_handles_empty_dataframe() -> None:
    df = pd.DataFrame()
    form = compute_form_index(df, n_recent=5)
    assert form == 0.0


def test_compute_form_index_uses_match_date_for_ordering() -> None:
    df = pd.DataFrame([
        {"result": "L", "match_date": "2026-01-01"},
        {"result": "L", "match_date": "2026-01-02"},
        {"result": "W", "match_date": "2026-01-03"},
        {"result": "W", "match_date": "2026-01-04"},
        {"result": "W", "match_date": "2026-01-05"},
    ])
    
    # Last 3 matches (by date): W, W, W = 3/3 = 100%
    form = compute_form_index(df, n_recent=3)
    assert form == 100.0
