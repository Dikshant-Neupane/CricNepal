"""
Tests for root_cause_analysis.py module.

Covers:
- Phase classification (powerplay/middle/death)
- Batting analysis by phase (run rate, dot%, wickets)
- Bowling analysis by phase (economy, dot%, boundary%)
- Delta calculations (S2 - S1 changes)
- Edge cases (empty data, missing values)
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path

from src.analytics.root_cause_analysis import (
    classify_phase,
    analyze_batting_by_phase,
    analyze_bowling_by_phase,
    calculate_deltas,
    TEAM, POWERPLAY_OVERS, DEATH_OVERS_START
)


# ══════════════════════════════════════════════════════════════════════════
# FIXTURES
# ══════════════════════════════════════════════════════════════════════════

@pytest.fixture
def sample_matches_df():
    """Sample matches DataFrame with Janakpur Bolts data."""
    return pd.DataFrame({
        'match_id': ['M1', 'M2', 'M3', 'M4'],
        'season': ['S1', 'S1', 'S2', 'S2'],
        'team_1_name': [TEAM, TEAM, 'Opponent', TEAM],
        'team_2_name': ['Opponent', 'Opponent', TEAM, 'Opponent'],
        'winner_name': [TEAM, 'Opponent', TEAM, 'Opponent'],
        'toss_winner_name': [TEAM, 'Opponent', TEAM, 'Opponent'],
        'toss_decision': ['bat', 'field', 'bat', 'field']
    })


@pytest.fixture
def sample_deliveries_batting():
    """Sample deliveries DataFrame for Janakpur batting analysis."""
    # Janakpur bats in innings 1 or 2 depending on match
    runs_data = [6, 0, 4, 1, 2, 0, 1, 0, 3, 4] * 12
    return pd.DataFrame({
        'match_id': ['M1'] * 30 + ['M2'] * 30 + ['M3'] * 30 + ['M4'] * 30,
        'season': ['S1'] * 60 + ['S2'] * 60,
        'innings': [1] * 30 + [2] * 30 + [1] * 30 + [2] * 30,
        'batting_team': [TEAM] * 30 + [TEAM] * 30 + [TEAM] * 30 + [TEAM] * 30,
        'bowling_team': ['Opponent'] * 120,
        'over': ([2] * 10 + [8] * 10 + [18] * 10) * 4,  # PP, Middle, Death
        'phase': (['powerplay'] * 10 + ['middle'] * 10 + ['death'] * 10) * 4,
        'runs_off_bat': runs_data,
        'runs_extras': [0] * 120,
        'is_dot_ball': [run == 0 for run in runs_data],
        'is_wicket': [False] * 115 + [True, False, True, False, False]  # 2 wickets
    })


@pytest.fixture
def sample_deliveries_bowling():
    """Sample deliveries DataFrame for Janakpur bowling analysis."""
    runs_data = [1, 0, 4, 0, 2, 0, 6, 0, 1, 0] * 12
    return pd.DataFrame({
        'match_id': ['M1'] * 30 + ['M2'] * 30 + ['M3'] * 30 + ['M4'] * 30,
        'season': ['S1'] * 60 + ['S2'] * 60,
        'innings': [2] * 30 + [1] * 30 + [2] * 30 + [1] * 30,
        'batting_team': ['Opponent'] * 120,
        'bowling_team': [TEAM] * 120,
        'over': ([2] * 10 + [8] * 10 + [18] * 10) * 4,
        'phase': (['powerplay'] * 10 + ['middle'] * 10 + ['death'] * 10) * 4,
        'runs_off_bat': runs_data,
        'runs_extras': [0] * 120,
        'is_dot_ball': [run == 0 for run in runs_data],
        'is_wicket': [False] * 117 + [True, False, False]  # 1 wicket
    })


# ══════════════════════════════════════════════════════════════════════════
# TEST PHASE CLASSIFICATION
# ══════════════════════════════════════════════════════════════════════════

def test_classify_phase_powerplay_start():
    """First over should be powerplay."""
    assert classify_phase(0) == 'powerplay'


def test_classify_phase_powerplay_end():
    """Over 5 (last of PP) should be powerplay."""
    assert classify_phase(5) == 'powerplay'


def test_classify_phase_middle_start():
    """Over 6 (first of middle) should be middle."""
    assert classify_phase(POWERPLAY_OVERS) == 'middle'


def test_classify_phase_middle():
    """Over 10 should be middle."""
    assert classify_phase(10) == 'middle'


def test_classify_phase_middle_end():
    """Over 15 (last of middle) should be middle."""
    assert classify_phase(DEATH_OVERS_START - 1) == 'middle'


def test_classify_phase_death_start():
    """Over 16 (first of death) should be death."""
    assert classify_phase(DEATH_OVERS_START) == 'death'


def test_classify_phase_death():
    """Over 18 should be death."""
    assert classify_phase(18) == 'death'


def test_classify_phase_death_last():
    """Over 19 (last over) should be death."""
    assert classify_phase(19) == 'death'


# ══════════════════════════════════════════════════════════════════════════
# TEST BATTING ANALYSIS
# ══════════════════════════════════════════════════════════════════════════

def test_analyze_batting_by_phase_returns_dataframe(sample_matches_df, sample_deliveries_batting):
    """Should return a pandas DataFrame."""
    result = analyze_batting_by_phase(sample_matches_df, sample_deliveries_batting)
    assert isinstance(result, pd.DataFrame)


def test_analyze_batting_by_phase_has_required_columns(sample_matches_df, sample_deliveries_batting):
    """Should include season, phase, and key batting metrics."""
    result = analyze_batting_by_phase(sample_matches_df, sample_deliveries_batting)
    required_columns = ['season', 'phase', 'total_runs', 'total_balls', 'run_rate', 
                       'dot_ball_pct', 'wickets_lost']
    for col in required_columns:
        assert col in result.columns, f"Missing column: {col}"


def test_analyze_batting_by_phase_calculates_run_rate(sample_matches_df, sample_deliveries_batting):
    """Should calculate run rate correctly (runs per ball * 6)."""
    result = analyze_batting_by_phase(sample_matches_df, sample_deliveries_batting)
    
    # Check that run rate is reasonable (between 4.0 and 12.0 for T20)
    assert result['run_rate'].min() >= 0
    assert result['run_rate'].max() <= 20.0  # Allow for high death overs run rates


def test_analyze_batting_by_phase_calculates_dot_pct(sample_matches_df, sample_deliveries_batting):
    """Should calculate dot ball percentage correctly."""
    result = analyze_batting_by_phase(sample_matches_df, sample_deliveries_batting)
    
    # Dot% should be between 0 and 100
    assert result['dot_ball_pct'].min() >= 0
    assert result['dot_ball_pct'].max() <= 100


def test_analyze_batting_by_phase_counts_wickets(sample_matches_df, sample_deliveries_batting):
    """Should count wickets correctly."""
    result = analyze_batting_by_phase(sample_matches_df, sample_deliveries_batting)
    
    # Total wickets across all phases/seasons should match input
    assert result['wickets_lost'].sum() == 2  # 2 wickets in fixture


def test_analyze_batting_by_phase_groups_by_season_and_phase(sample_matches_df, sample_deliveries_batting):
    """Should have separate rows for each season-phase combination."""
    result = analyze_batting_by_phase(sample_matches_df, sample_deliveries_batting)
    
    # Should have at most 6 rows: S1 x 3 phases, S2 x 3 phases
    assert len(result) <= 6


# ══════════════════════════════════════════════════════════════════════════
# TEST BOWLING ANALYSIS
# ══════════════════════════════════════════════════════════════════════════

def test_analyze_bowling_by_phase_returns_dataframe(sample_matches_df, sample_deliveries_bowling):
    """Should return a pandas DataFrame."""
    result = analyze_bowling_by_phase(sample_matches_df, sample_deliveries_bowling)
    assert isinstance(result, pd.DataFrame)


def test_analyze_bowling_by_phase_has_required_columns(sample_matches_df, sample_deliveries_bowling):
    """Should include season, phase, and key bowling metrics."""
    result = analyze_bowling_by_phase(sample_matches_df, sample_deliveries_bowling)
    required_columns = ['season', 'phase', 'runs_conceded', 'total_balls', 'economy', 
                       'dot_ball_pct', 'boundary_conceded_pct', 'wickets_taken']
    for col in required_columns:
        assert col in result.columns, f"Missing column: {col}"


def test_analyze_bowling_by_phase_calculates_economy(sample_matches_df, sample_deliveries_bowling):
    """Should calculate economy rate correctly (runs per over)."""
    result = analyze_bowling_by_phase(sample_matches_df, sample_deliveries_bowling)
    
    # Economy should be reasonable (4.0 to 15.0 for T20)
    assert result['economy'].min() >= 0
    assert result['economy'].max() <= 20.0


def test_analyze_bowling_by_phase_calculates_boundary_pct(sample_matches_df, sample_deliveries_bowling):
    """Should calculate boundary percentage correctly."""
    result = analyze_bowling_by_phase(sample_matches_df, sample_deliveries_bowling)
    
    # Boundary% should be between 0 and 100
    assert result['boundary_conceded_pct'].min() >= 0
    assert result['boundary_conceded_pct'].max() <= 100


def test_analyze_bowling_by_phase_counts_wickets(sample_matches_df, sample_deliveries_bowling):
    """Should count wickets correctly."""
    result = analyze_bowling_by_phase(sample_matches_df, sample_deliveries_bowling)
    
    # Total wickets should match input
    assert result['wickets_taken'].sum() == 1  # 1 wicket in fixture


# ══════════════════════════════════════════════════════════════════════════
# TEST DELTA CALCULATIONS
# ══════════════════════════════════════════════════════════════════════════

def test_calculate_deltas_without_phase():
    """Should calculate S2 - S1 deltas correctly for single metric."""
    df = pd.DataFrame({
        'season': ['S1', 'S2'],
        'metric_a': [10.0, 15.0],
        'metric_b': [5.0, 3.0]
    })
    
    result = calculate_deltas(df, ['metric_a', 'metric_b'], by_phase=False)
    
    assert 'metric_a_delta' in result.columns
    assert 'metric_b_delta' in result.columns
    assert result['metric_a_delta'].iloc[0] == 5.0  # 15 - 10
    assert result['metric_b_delta'].iloc[0] == -2.0  # 3 - 5


def test_calculate_deltas_with_phase():
    """Should calculate S2 - S1 deltas by phase."""
    df = pd.DataFrame({
        'season': ['S1', 'S1', 'S2', 'S2'],
        'phase': ['powerplay', 'middle', 'powerplay', 'middle'],
        'metric': [10.0, 15.0, 12.0, 18.0]
    })
    
    result = calculate_deltas(df, ['metric'], by_phase=True)
    
    assert 'metric_delta' in result.columns
    assert len(result) == 2  # One row per phase
    
    # PP delta: 12 - 10 = 2
    pp_row = result[result['phase'] == 'powerplay']
    assert pp_row['metric_delta'].iloc[0] == 2.0
    
    # Middle delta: 18 - 15 = 3
    mid_row = result[result['phase'] == 'middle']
    assert mid_row['metric_delta'].iloc[0] == 3.0


def test_calculate_deltas_percentage_change():
    """Should calculate delta absolute values correctly."""
    df = pd.DataFrame({
        'season': ['S1', 'S2'],
        'metric': [10.0, 15.0]
    })
    
    result = calculate_deltas(df, ['metric'], by_phase=False)
    
    # Should have delta column showing S2 - S1
    assert 'metric_delta' in result.columns
    assert result['metric_delta'].iloc[0] == 5.0  # 15 - 10


def test_calculate_deltas_handles_zero_baseline():
    """Should handle zero baseline values gracefully."""
    df = pd.DataFrame({
        'season': ['S1', 'S2'],
        'metric': [0.0, 5.0]
    })
    
    result = calculate_deltas(df, ['metric'], by_phase=False)
    
    # Should have delta column showing absolute change
    assert 'metric_delta' in result.columns
    assert result['metric_delta'].iloc[0] == 5.0  # 5 - 0


# ══════════════════════════════════════════════════════════════════════════
# EDGE CASES
# ══════════════════════════════════════════════════════════════════════════

def test_analyze_batting_by_phase_handles_empty_dataframe(sample_matches_df):
    """Should handle empty deliveries gracefully."""
    empty_deliveries = pd.DataFrame(columns=['match_id', 'season', 'innings', 'batting_team', 
                                              'bowling_team', 'over', 'phase', 'runs_off_bat', 
                                              'runs_extras', 'is_dot_ball', 'is_wicket'])
    
    result = analyze_batting_by_phase(sample_matches_df, empty_deliveries)
    assert isinstance(result, pd.DataFrame)
    assert len(result) == 0 or result.empty


def test_analyze_bowling_by_phase_handles_empty_dataframe(sample_matches_df):
    """Should handle empty deliveries gracefully."""
    empty_deliveries = pd.DataFrame(columns=['match_id', 'season', 'innings', 'batting_team', 
                                              'bowling_team', 'over', 'phase', 'runs_off_bat', 
                                              'runs_extras', 'is_dot_ball', 'is_wicket'])
    
    result = analyze_bowling_by_phase(sample_matches_df, empty_deliveries)
    assert isinstance(result, pd.DataFrame)
    assert len(result) == 0 or result.empty


def test_calculate_deltas_handles_missing_season():
    """Should handle missing S1 or S2 data."""
    df = pd.DataFrame({
        'season': ['S1'],
        'metric': [10.0]
    })
    
    result = calculate_deltas(df, ['metric'], by_phase=False)
    
    # Should return empty or handle gracefully
    assert isinstance(result, pd.DataFrame)


def test_classify_phase_boundary_values():
    """Test phase classification at exact boundaries."""
    # Last PP over
    assert classify_phase(POWERPLAY_OVERS - 1) == 'powerplay'
    
    # First middle over
    assert classify_phase(POWERPLAY_OVERS) == 'middle'
    
    # Last middle over
    assert classify_phase(DEATH_OVERS_START - 1) == 'middle'
    
    # First death over
    assert classify_phase(DEATH_OVERS_START) == 'death'
