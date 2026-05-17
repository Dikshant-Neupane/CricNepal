import pandas as pd

from src.dashboard.services.metrics import (
    compute_team_kpis,
    compute_weighted_form_index,
    compute_season_win_pct,
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
