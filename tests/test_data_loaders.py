import pytest
import pandas as pd
from src.dashboard.services.data_loaders import (
    load_matches_normalized,
    load_ball_by_ball_normalized,
    load_npl_rosters,
    load_matchup_stats
)

def test_load_matches_normalized():
    df = load_matches_normalized()
    assert df is not None, "Matches dataset failed to load."
    assert isinstance(df, pd.DataFrame)
    assert not df.empty, "Matches dataset is empty."
    
def test_load_ball_by_ball_normalized():
    df = load_ball_by_ball_normalized()
    assert df is not None, "Ball-by-ball dataset failed to load."
    assert isinstance(df, pd.DataFrame)
    assert not df.empty, "Ball-by-ball dataset is empty."
    
def test_load_npl_rosters():
    df = load_npl_rosters()
    assert df is not None, "Rosters failed to load."
    assert isinstance(df, pd.DataFrame)
    
def test_load_matchup_stats():
    # Provide dummy strings to ensure it runs and returns the default schema
    stats = load_matchup_stats("Unknown Batter", "Unknown Bowler")
    assert stats is not None
    assert "score" in stats
    assert "ci_lower" in stats
