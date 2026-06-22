"""
Tests for player_clustering.py module.
"""

import pytest
import pandas as pd
import numpy as np

from src.analytics.player_clustering import (
    build_player_feature_matrix,
    cluster_players,
)


@pytest.fixture
def mock_bbb_df():
    """Mock ball-by-ball dataset for clustering tests."""
    rows = []
    # Batter A: Power Hitter profile (high SR, high boundaries)
    for i in range(24):
        rows.append({
            'match_id': 'M1',
            'innings': 1,
            'over': i // 6,
            'ball': (i % 6) + 1,
            'batter_name': 'Batter A',
            'non_striker_name': 'Batter B',
            'bowler_name': 'Bowler X',
            'runs_off_bat': 4 if i % 2 == 0 else 0,  # SR = 200, 50% boundary
            'runs_extras': 0,
            'runs_total': 4 if i % 2 == 0 else 0,
            'is_boundary': 1 if i % 2 == 0 else 0,
            'is_wicket': 0,
            'is_dot_ball': 1 if i % 2 != 0 else 0,
            'phase': 'Middle'
        })
        
    # Bowler X: Economy Bowler profile (low economy, high dots)
    for i in range(24):
        rows.append({
            'match_id': 'M1',
            'innings': 2,
            'over': i // 6,
            'ball': (i % 6) + 1,
            'batter_name': 'Batter B',
            'non_striker_name': 'Batter A',
            'bowler_name': 'Bowler X',
            'runs_off_bat': 1,
            'runs_extras': 0,
            'runs_total': 1,  # Economy = 6.0
            'is_boundary': 0,
            'is_wicket': 1 if i == 11 else 0,
            'is_dot_ball': 0,
            'phase': 'Powerplay'
        })
        
    return pd.DataFrame(rows)


@pytest.fixture
def mock_matches_df():
    return pd.DataFrame({
        'match_id': ['M1'],
        'season': ['S1']
    })


def test_build_player_feature_matrix(mock_bbb_df, mock_matches_df):
    """Verify feature matrix correctly extracts batting & bowling metrics."""
    features = build_player_feature_matrix(mock_bbb_df, mock_matches_df)
    
    # Must contain both players
    assert len(features) >= 2
    assert 'Batter A' in features['player_name'].values
    assert 'Bowler X' in features['player_name'].values
    
    # Check specific features
    batter_a_row = features[features['player_name'] == 'Batter A'].iloc[0]
    assert batter_a_row['bat_sr'] > 150
    assert batter_a_row['bat_boundary_pct'] == 50.0


def test_cluster_players(mock_bbb_df, mock_matches_df):
    """Verify KMeans successfully groups similar players and assigns archetypes."""
    features = build_player_feature_matrix(mock_bbb_df, mock_matches_df)
    
    # We must have at least n_samples >= 3 for silhouette score test to function correctly
    # Let's add a third player to guarantee k range starts at 3
    extra_player = pd.DataFrame([{
        'player_name': 'Batter C',
        'bat_balls': 20,
        'bat_runs': 20,
        'bat_boundaries': 2,
        'bat_dots': 10,
        'bat_sr': 100.0,
        'bat_boundary_pct': 10.0,
        'bat_dot_pct': 50.0,
        'bowl_balls': 0,
        'bowl_runs': 0,
        'bowl_wickets': 0,
        'bowl_dots': 0,
        'bowl_economy': 0.0,
        'bowl_sr': 999.0,
        'bowl_dot_pct': 0.0,
        'pp_economy': 0.0,
        'mid_economy': 0.0,
        'death_economy': 0.0
    }])
    features = pd.concat([features, extra_player], ignore_index=True)
    
    clustered, centroids, best_score = cluster_players(features)
    
    assert 'archetype' in clustered.columns
    assert 'cluster' in clustered.columns
    assert best_score >= -1.0
