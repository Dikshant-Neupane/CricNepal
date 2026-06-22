"""
Tests for win_probability_model.py module.
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path

from src.analytics.win_probability_model import WinProbabilityModel, compute_and_export_wpa

@pytest.fixture
def mock_matches_df():
    """Mock matches dataset for testing."""
    return pd.DataFrame({
        'match_id': ['M1', 'M2'],
        'season': ['S1', 'S2'],
        'team_1_name': ['Janakpur Bolts', 'Janakpur Bolts'],
        'team_2_name': ['Opponent A', 'Opponent B'],
        'winner_name': ['Opponent A', 'Opponent B']
    })

@pytest.fixture
def mock_bbb_df():
    """Mock ball-by-ball dataset for testing."""
    # 2 matches, 2 innings, 12 balls per innings for simplicity
    rows = []
    
    # Match 1: Janakpur Bolts (batting innings 1, bowling innings 2) vs Opponent A. Bolts won.
    for i in range(12):
        rows.append({
            'match_id': 'M1',
            'innings': 1,
            'over': i // 6,
            'ball': (i % 6) + 1,
            'batting_team': 'Janakpur Bolts',
            'bowling_team': 'Opponent A',
            'batter_name': 'Batter A',
            'bowler_name': 'Bowler X',
            'runs_off_bat': 1 if i != 5 else 6,
            'runs_extras': 0,
            'runs_total': 1 if i != 5 else 6,
            'is_wicket': 0
        })
    for i in range(12):
        rows.append({
            'match_id': 'M1',
            'innings': 2,
            'over': i // 6,
            'ball': (i % 6) + 1,
            'batting_team': 'Opponent A',
            'bowling_team': 'Janakpur Bolts',
            'batter_name': 'Batter Y',
            'bowler_name': 'Bowler B',
            'runs_off_bat': 0,
            'runs_extras': 0,
            'runs_total': 0,
            'is_wicket': 1 if i == 5 else 0
        })
        
    # Match 2: Janakpur Bolts (bowling innings 1, batting innings 2) vs Opponent B. Opponent B won.
    for i in range(12):
        rows.append({
            'match_id': 'M2',
            'innings': 1,
            'over': i // 6,
            'ball': (i % 6) + 1,
            'batting_team': 'Opponent B',
            'bowling_team': 'Janakpur Bolts',
            'batter_name': 'Batter Z',
            'bowler_name': 'Bowler B',
            'runs_off_bat': 2,
            'runs_extras': 0,
            'runs_total': 2,
            'is_wicket': 0
        })
    for i in range(12):
        rows.append({
            'match_id': 'M2',
            'innings': 2,
            'over': i // 6,
            'ball': (i % 6) + 1,
            'batting_team': 'Janakpur Bolts',
            'bowling_team': 'Opponent B',
            'batter_name': 'Batter A',
            'bowler_name': 'Bowler Y',
            'runs_off_bat': 1,
            'runs_extras': 0,
            'runs_total': 1,
            'is_wicket': 1 if i == 11 else 0
        })
        
    return pd.DataFrame(rows)

def test_build_match_states(mock_bbb_df, mock_matches_df):
    """Verify build_match_states adds correct feature columns."""
    wp_model = WinProbabilityModel()
    states = wp_model.build_match_states(mock_bbb_df, mock_matches_df)
    
    # Required columns for training
    required_cols = [
        'is_batting_team_winner', 'balls_remaining', 'runs_cumulative',
        'wickets_cumulative', 'required_run_rate', 'current_run_rate'
    ]
    for col in required_cols:
        assert col in states.columns, f"Missing column: {col}"
        
    # Check that balls_remaining is correctly decremented
    assert states['balls_remaining'].iloc[0] == 119
    assert states['balls_remaining'].iloc[11] == 108

def test_model_training_and_prediction(mock_bbb_df, mock_matches_df):
    """Verify models train cleanly and return valid predictions."""
    wp_model = WinProbabilityModel()
    wp_model.train(mock_bbb_df, mock_matches_df)
    
    assert wp_model._is_trained
    
    states = wp_model.build_match_states(mock_bbb_df, mock_matches_df)
    probs = wp_model.predict_delivery_probs(states)
    
    assert len(probs) == len(mock_bbb_df)
    assert probs.min() >= 0.0
    assert probs.max() <= 1.0
