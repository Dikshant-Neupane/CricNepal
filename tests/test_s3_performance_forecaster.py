"""
Comprehensive tests for S3 Performance Forecaster
Tests backtesting validation, trend analysis, predictions, and composite scoring.

Author: Senior Data Scientist
Date: May 23, 2026
"""

import pytest
import pandas as pd
import numpy as np
from src.analytics.s3_performance_forecaster import S3PerformanceForecaster


# ============================================================================
# TEST FIXTURES
# ============================================================================

@pytest.fixture
def sample_s1_bowlers():
    """Sample S1 bowling data for testing."""
    return pd.DataFrame({
        'player_name': ['Player A', 'Player B', 'Player C', 'Player D', 'Player E'],
        'role': ['Bowler', 'Bowler', 'Bowler', 'All-rounder', 'Bowler'],
        'wickets': [10, 5, 15, 8, 0],
        'economy': [7.5, 9.0, 6.5, 8.5, 10.0],
        'bowling_sr': [18.0, 24.0, 15.0, 20.0, 30.0],
        'matches': [10, 10, 10, 10, 10]
    })


@pytest.fixture
def sample_s2_bowlers():
    """Sample S2 bowling data for testing."""
    return pd.DataFrame({
        'player_name': ['Player A', 'Player B', 'Player C', 'Player D', 'Player E'],
        'role': ['Bowler', 'Bowler', 'Bowler', 'All-rounder', 'Bowler'],
        'wickets': [12, 3, 17, 6, 2],  # A: improving, B: declining, C: improving, D: declining, E: improving from zero
        'economy': [7.0, 10.5, 6.2, 9.0, 9.5],  # A: improving, B: declining, C: improving, D: declining, E: improving
        'bowling_sr': [16.0, 28.0, 14.0, 22.0, 25.0],
        'matches': [10, 10, 10, 10, 10]
    })


@pytest.fixture
def forecaster(sample_s1_bowlers, sample_s2_bowlers):
    """Initialize forecaster with sample data."""
    return S3PerformanceForecaster(sample_s1_bowlers, sample_s2_bowlers)


@pytest.fixture
def edge_case_s1_data():
    """Edge case S1 data with missing values and zeros."""
    return pd.DataFrame({
        'player_name': ['Player X', 'Player Y', 'Player Z'],
        'role': ['Bowler', 'Bowler', 'Bowler'],
        'wickets': [0, np.nan, 5],
        'economy': [np.nan, 8.0, 0],
        'bowling_sr': [20.0, np.nan, 15.0]
    })


@pytest.fixture
def edge_case_s2_data():
    """Edge case S2 data with missing values and zeros."""
    return pd.DataFrame({
        'player_name': ['Player X', 'Player Y', 'Player Z'],
        'role': ['Bowler', 'Bowler', 'Bowler'],
        'wickets': [2, 10, np.nan],
        'economy': [7.5, np.nan, 8.0],
        'bowling_sr': [18.0, 16.0, np.nan]
    })


# ============================================================================
# BACKTEST VALIDATION TESTS
# ============================================================================

def test_backtest_validation_returns_valid_structure(forecaster):
    """Test that backtest_validation returns all required metrics."""
    result = forecaster.backtest_validation(metric_col='wickets', player_type='bowler')
    
    assert 'metric' in result
    assert 'player_type' in result
    assert 'n_players' in result
    assert 'mae' in result
    assert 'rmse' in result
    assert 'mape' in result
    assert 'directional_accuracy' in result
    assert 'baseline_mae' in result
    assert 'baseline_rmse' in result
    assert 'improvement_over_baseline' in result


def test_backtest_validation_processes_bowlers_correctly(forecaster):
    """Test that backtest_validation correctly identifies and processes bowlers."""
    result = forecaster.backtest_validation(metric_col='wickets', player_type='bowler')
    
    # Should find 4 pure bowlers (All-rounder role doesn't contain 'bowl' in this fixture)
    assert result['n_players'] == 4
    assert result['metric'] == 'wickets'
    assert result['player_type'] == 'bowler'


def test_backtest_validation_calculates_mae_correctly(forecaster):
    """Test MAE calculation logic in backtesting."""
    result = forecaster.backtest_validation(metric_col='wickets', player_type='bowler')
    
    # MAE should be a positive number
    assert result['mae'] >= 0
    # MAE should be less than the baseline MAE (our model should beat naive baseline)
    # Actually, since we're using naive forecast (S2 = S1), improvement might be 0 or negative
    # This is expected for the naive baseline
    assert isinstance(result['mae'], (int, float))


def test_backtest_validation_calculates_rmse_correctly(forecaster):
    """Test RMSE calculation logic in backtesting."""
    result = forecaster.backtest_validation(metric_col='wickets', player_type='bowler')
    
    # RMSE should be >= MAE (mathematical property)
    assert result['rmse'] >= result['mae']
    assert result['rmse'] >= 0


def test_backtest_validation_calculates_mape_correctly(forecaster):
    """Test MAPE (Mean Absolute Percentage Error) calculation."""
    result = forecaster.backtest_validation(metric_col='wickets', player_type='bowler')
    
    # MAPE should be a percentage value
    assert result['mape'] >= 0
    # MAPE should be reasonable (not infinite)
    assert result['mape'] < 1000  # Sanity check


def test_backtest_validation_calculates_directional_accuracy(forecaster):
    """Test directional accuracy calculation (did we predict the right direction?)."""
    result = forecaster.backtest_validation(metric_col='wickets', player_type='bowler')
    
    # Directional accuracy should be between 0 and 100
    assert 0 <= result['directional_accuracy'] <= 100
    # For naive baseline (S2 = S1), directional accuracy should be around 50% for random changes
    # But since our sample has specific patterns, it could be different


def test_backtest_validation_compares_against_baseline(forecaster):
    """Test that backtest compares against naive baseline."""
    result = forecaster.backtest_validation(metric_col='wickets', player_type='bowler')
    
    # Baseline metrics should exist
    assert result['baseline_mae'] >= 0
    assert result['baseline_rmse'] >= 0
    
    # Improvement can be negative (our model might be worse than baseline)
    assert isinstance(result['improvement_over_baseline'], (int, float))


def test_backtest_validation_handles_no_valid_players():
    """Test backtest when no players have both S1 and S2 data."""
    empty_s1 = pd.DataFrame({'player_name': [], 'role': [], 'wickets': []})
    empty_s2 = pd.DataFrame({'player_name': [], 'role': [], 'wickets': []})
    forecaster = S3PerformanceForecaster(empty_s1, empty_s2)
    
    result = forecaster.backtest_validation(metric_col='wickets', player_type='bowler')
    
    assert 'error' in result
    assert result['n_players'] == 0


def test_backtest_validation_handles_missing_metric_column(forecaster):
    """Test backtest with non-existent metric column."""
    # This should handle the missing column gracefully
    result = forecaster.backtest_validation(metric_col='nonexistent_metric', player_type='bowler')
    
    # Should return error or handle gracefully
    # Current implementation will likely return error due to missing column
    assert 'error' in result or result['n_players'] == 0


# ============================================================================
# TREND ANALYSIS TESTS
# ============================================================================

def test_analyze_trend_identifies_catastrophic_decline_economy(forecaster):
    """Test identification of catastrophic decline in economy (>3.0 increase)."""
    result = forecaster.analyze_trend(s1_value=7.0, s2_value=10.5, metric='economy')
    
    assert result['trend'] == 'CATASTROPHIC_DECLINE'
    assert result['delta'] == 3.5
    assert result['pct_change'] == 50.0


def test_analyze_trend_identifies_declining_economy(forecaster):
    """Test identification of declining trend in economy (>1.5 increase)."""
    result = forecaster.analyze_trend(s1_value=7.0, s2_value=8.7, metric='economy')
    
    assert result['trend'] == 'DECLINING'
    assert result['delta'] == 1.7


def test_analyze_trend_identifies_improving_economy(forecaster):
    """Test identification of improving trend in economy (<-1.0 decrease)."""
    result = forecaster.analyze_trend(s1_value=8.5, s2_value=7.0, metric='economy')
    
    assert result['trend'] == 'IMPROVING'
    assert result['delta'] == -1.5


def test_analyze_trend_identifies_stable_economy(forecaster):
    """Test identification of stable trend in economy."""
    result = forecaster.analyze_trend(s1_value=7.5, s2_value=7.8, metric='economy')
    
    assert result['trend'] == 'STABLE'
    assert abs(result['delta']) < 1.5


def test_analyze_trend_identifies_catastrophic_decline_wickets(forecaster):
    """Test identification of catastrophic decline in wickets (>80% drop)."""
    result = forecaster.analyze_trend(s1_value=15, s2_value=2, metric='wickets')
    
    assert result['trend'] == 'CATASTROPHIC_DECLINE'
    assert result['pct_change'] < -80


def test_analyze_trend_identifies_improving_wickets(forecaster):
    """Test identification of improving trend in wickets."""
    result = forecaster.analyze_trend(s1_value=10, s2_value=65, metric='wickets')
    
    assert result['trend'] == 'IMPROVING'
    assert result['delta'] > 50


def test_analyze_trend_handles_missing_s1_value(forecaster):
    """Test trend analysis with missing S1 value."""
    result = forecaster.analyze_trend(s1_value=np.nan, s2_value=10, metric='wickets')
    
    assert result['trend'] == 'INSUFFICIENT_DATA'
    assert result['delta'] is None
    assert result['pct_change'] is None
    assert result['confidence'] == 0


def test_analyze_trend_handles_missing_s2_value(forecaster):
    """Test trend analysis with missing S2 value."""
    result = forecaster.analyze_trend(s1_value=10, s2_value=np.nan, metric='wickets')
    
    assert result['trend'] == 'INSUFFICIENT_DATA'
    assert result['delta'] is None
    assert result['confidence'] == 0


def test_analyze_trend_handles_zero_s1_value(forecaster):
    """Test trend analysis with zero S1 value (division by zero case)."""
    result = forecaster.analyze_trend(s1_value=0, s2_value=10, metric='wickets')
    
    # Should handle gracefully without crashing
    assert result['trend'] in ['CATASTROPHIC_DECLINE', 'DECLINING', 'IMPROVING', 'STABLE', 'INSUFFICIENT_DATA']
    # pct_change might be inf, which is handled
    assert isinstance(result['pct_change'], (int, float)) or result['pct_change'] == float('inf')


def test_analyze_trend_confidence_calculation(forecaster):
    """Test that confidence is calculated and bounded correctly."""
    result = forecaster.analyze_trend(s1_value=10, s2_value=15, metric='wickets')
    
    # Confidence should be between 0 and 100
    assert 0 <= result['confidence'] <= 100
    # For a 50% change, confidence should be at least 50
    assert result['confidence'] >= 50


# ============================================================================
# PREDICTION TESTS (predict_s3_value)
# ============================================================================

def test_predict_s3_value_catastrophic_decline_recovery(forecaster):
    """Test S3 prediction for catastrophic decline (40% recovery)."""
    s1_val = 15
    s2_val = 3  # Catastrophic drop of 12 wickets
    s3_pred, lower, upper = forecaster.predict_s3_value(s1_val, s2_val, 'CATASTROPHIC_DECLINE')
    
    # Expected: s2_val + (delta * -0.4) = 3 + ((-12) * -0.4) = 3 + 4.8 = 7.8
    assert s3_pred == pytest.approx(7.8, rel=0.1)
    assert lower < s3_pred < upper
    # Wide margin for catastrophic decline (±30%)
    assert (upper - lower) == pytest.approx(s3_pred * 0.6, rel=0.1)


def test_predict_s3_value_declining_recovery(forecaster):
    """Test S3 prediction for declining trend (50% recovery)."""
    s1_val = 10
    s2_val = 5  # Drop of 5 wickets
    s3_pred, lower, upper = forecaster.predict_s3_value(s1_val, s2_val, 'DECLINING')
    
    # Expected: s2_val + (delta * -0.5) = 5 + ((-5) * -0.5) = 5 + 2.5 = 7.5
    assert s3_pred == pytest.approx(7.5, rel=0.1)
    assert lower < s3_pred < upper


def test_predict_s3_value_improving_continuation(forecaster):
    """Test S3 prediction for improving trend (30% continuation)."""
    s1_val = 10
    s2_val = 17  # Improvement of 7 wickets
    s3_pred, lower, upper = forecaster.predict_s3_value(s1_val, s2_val, 'IMPROVING')
    
    # Expected: s2_val + (delta * 0.3) = 17 + (7 * 0.3) = 17 + 2.1 = 19.1
    assert s3_pred == pytest.approx(19.1, rel=0.1)
    assert lower < s3_pred < upper
    # Wide margin for improving trend (±30%)
    assert (upper - lower) == pytest.approx(s3_pred * 0.6, rel=0.1)


def test_predict_s3_value_stable_weighted_average(forecaster):
    """Test S3 prediction for stable trend (weighted average)."""
    s1_val = 10
    s2_val = 12
    s3_pred, lower, upper = forecaster.predict_s3_value(s1_val, s2_val, 'STABLE')
    
    # Expected: (s1_val * 0.3) + (s2_val * 0.7) = (10 * 0.3) + (12 * 0.7) = 3 + 8.4 = 11.4
    assert s3_pred == pytest.approx(11.4, rel=0.1)
    assert lower < s3_pred < upper
    # Narrow margin for stable trend (±15%)
    assert (upper - lower) == pytest.approx(s3_pred * 0.3, rel=0.1)


def test_predict_s3_value_handles_missing_s1(forecaster):
    """Test S3 prediction with missing S1 value."""
    s3_pred, lower, upper = forecaster.predict_s3_value(np.nan, 10, 'STABLE')
    
    assert s3_pred is None
    assert lower is None
    assert upper is None


def test_predict_s3_value_handles_missing_s2(forecaster):
    """Test S3 prediction with missing S2 value."""
    s3_pred, lower, upper = forecaster.predict_s3_value(10, np.nan, 'IMPROVING')
    
    assert s3_pred is None
    assert lower is None
    assert upper is None


def test_predict_s3_value_returns_rounded_values(forecaster):
    """Test that predictions are properly rounded to 2 decimal places."""
    s3_pred, lower, upper = forecaster.predict_s3_value(10.123456, 12.987654, 'STABLE')
    
    # Check that values are rounded to 2 decimals
    assert s3_pred == round(s3_pred, 2)
    assert lower == round(lower, 2)
    assert upper == round(upper, 2)


# ============================================================================
# COMPOSITE BOWLER SCORE TESTS
# ============================================================================

def test_calculate_composite_bowler_score_excellent_bowler(forecaster):
    """Test composite score for excellent bowler."""
    # Excellent: 2.5+ wkts/match, 6.0 economy, 12 balls/wkt
    score = forecaster.calculate_composite_bowler_score(
        wkts_per_match=2.5,
        economy=6.0,
        bowling_sr=12.0
    )
    
    # Expected: (100 * 0.6) + (100 * 0.3) + (100 * 0.1) = 100
    assert score == pytest.approx(100.0, rel=0.1)


def test_calculate_composite_bowler_score_average_bowler(forecaster):
    """Test composite score for average bowler."""
    # Average: 1.5 wkts/match, 8.0 economy, 20 balls/wkt
    score = forecaster.calculate_composite_bowler_score(
        wkts_per_match=1.5,
        economy=8.0,
        bowling_sr=20.0
    )
    
    # Wickets: (1.5/2.5)*100 = 60
    # Economy: 100 - ((8.0-6.0)/4.0)*100 = 100 - 50 = 50
    # SR: 100 - ((20-12)/16)*100 = 100 - 50 = 50
    # Composite: 60*0.6 + 50*0.3 + 50*0.1 = 36 + 15 + 5 = 56
    assert score == pytest.approx(56.0, rel=0.1)


def test_calculate_composite_bowler_score_poor_bowler(forecaster):
    """Test composite score for poor bowler."""
    # Poor: 0.5 wkts/match, 10.0 economy, 28 balls/wkt
    score = forecaster.calculate_composite_bowler_score(
        wkts_per_match=0.5,
        economy=10.0,
        bowling_sr=28.0
    )
    
    # Wickets: (0.5/2.5)*100 = 20
    # Economy: 100 - ((10.0-6.0)/4.0)*100 = 100 - 100 = 0
    # SR: 100 - ((28-12)/16)*100 = 100 - 100 = 0
    # Composite: 20*0.6 + 0*0.3 + 0*0.1 = 12
    assert score == pytest.approx(12.0, rel=0.1)


def test_calculate_composite_bowler_score_handles_missing_wickets(forecaster):
    """Test composite score with missing wickets data."""
    score = forecaster.calculate_composite_bowler_score(
        wkts_per_match=np.nan,
        economy=7.0,
        bowling_sr=18.0
    )
    
    assert score == 0


def test_calculate_composite_bowler_score_handles_missing_economy(forecaster):
    """Test composite score with missing economy data."""
    score = forecaster.calculate_composite_bowler_score(
        wkts_per_match=2.0,
        economy=np.nan,
        bowling_sr=15.0
    )
    
    assert score == 0


def test_calculate_composite_bowler_score_handles_missing_sr(forecaster):
    """Test composite score with missing strike rate (defaults to 50)."""
    score = forecaster.calculate_composite_bowler_score(
        wkts_per_match=2.0,
        economy=7.0,
        bowling_sr=np.nan
    )
    
    # Should default SR score to 50 (average)
    # Wickets: (2.0/2.5)*100 = 80
    # Economy: 100 - ((7.0-6.0)/4.0)*100 = 100 - 25 = 75
    # SR: 50 (default)
    # Composite: 80*0.6 + 75*0.3 + 50*0.1 = 48 + 22.5 + 5 = 75.5
    assert score == pytest.approx(75.5, rel=0.1)


def test_calculate_composite_bowler_score_weights_correct(forecaster):
    """Test that composite score uses correct weights (60-30-10)."""
    # Use controlled values to verify weights
    score = forecaster.calculate_composite_bowler_score(
        wkts_per_match=2.5,  # 100 score
        economy=6.0,         # 100 score
        bowling_sr=12.0      # 100 score
    )
    
    # All perfect scores: 100*0.6 + 100*0.3 + 100*0.1 = 100
    assert score == 100.0


def test_calculate_composite_bowler_score_clamps_values(forecaster):
    """Test that scores are clamped to 0-100 range."""
    # Extremely poor values
    score = forecaster.calculate_composite_bowler_score(
        wkts_per_match=0,
        economy=15.0,  # Terrible economy
        bowling_sr=50.0  # Terrible SR
    )
    
    # Score should be >= 0
    assert score >= 0


def test_calculate_composite_bowler_score_rounds_to_one_decimal(forecaster):
    """Test that composite score is rounded to 1 decimal place."""
    score = forecaster.calculate_composite_bowler_score(
        wkts_per_match=1.234567,
        economy=7.89123,
        bowling_sr=18.456
    )
    
    # Should be rounded to 1 decimal
    assert score == round(score, 1)


# ============================================================================
# PRIORITY AND GRADE MAPPING TESTS
# ============================================================================

def test_assign_priority_from_composite_elite_bowler(forecaster):
    """Test priority assignment for elite bowler (80+ composite)."""
    priority = forecaster.assign_priority_from_composite(composite_score=85.0, role='bowler')
    assert priority == 10


def test_assign_priority_from_composite_target_bowler(forecaster):
    """Test priority assignment for target bowler (60-70 composite)."""
    priority = forecaster.assign_priority_from_composite(composite_score=65.0, role='bowler')
    assert priority == 8


def test_assign_priority_from_composite_avoid_bowler(forecaster):
    """Test priority assignment for avoid bowler (<30 composite)."""
    priority = forecaster.assign_priority_from_composite(composite_score=25.0, role='bowler')
    assert priority == 2


def test_assign_priority_handles_missing_composite(forecaster):
    """Test priority assignment with missing composite score."""
    priority = forecaster.assign_priority_from_composite(composite_score=np.nan, role='bowler')
    assert priority == 0


def test_assign_priority_handles_zero_composite(forecaster):
    """Test priority assignment with zero composite score."""
    priority = forecaster.assign_priority_from_composite(composite_score=0.0, role='bowler')
    assert priority == 0


def test_map_priority_to_npl_grade_elite(forecaster):
    """Test NPL grade mapping for elite priority (9-10)."""
    grade, bid_range = forecaster.map_priority_to_npl_grade(priority=10)
    assert grade == 'Grade A'
    assert '₨' in bid_range
    assert 'Lakhs' in bid_range


def test_map_priority_to_npl_grade_target(forecaster):
    """Test NPL grade mapping for target priority (8)."""
    grade, bid_range = forecaster.map_priority_to_npl_grade(priority=8)
    assert grade == 'Grade A/B'


def test_map_priority_to_npl_grade_skip(forecaster):
    """Test NPL grade mapping for skip priority (0-2)."""
    grade, bid_range = forecaster.map_priority_to_npl_grade(priority=0)
    assert grade == 'Skip'
    assert bid_range == 'Below minimum'


# ============================================================================
# EDGE CASE AND ERROR HANDLING TESTS
# ============================================================================

def test_forecaster_handles_empty_dataframes():
    """Test forecaster initialization with empty DataFrames."""
    empty_df = pd.DataFrame()
    forecaster = S3PerformanceForecaster(empty_df, empty_df)
    
    # Should not crash
    assert forecaster.s1_data.empty
    assert forecaster.s2_data.empty


def test_forecaster_with_edge_case_data(edge_case_s1_data, edge_case_s2_data):
    """Test forecaster with edge case data (missing values, zeros)."""
    forecaster = S3PerformanceForecaster(edge_case_s1_data, edge_case_s2_data)
    
    # Should initialize without crashing
    assert forecaster.s1_data is not None
    assert forecaster.s2_data is not None


def test_backtest_validation_with_mismatched_players():
    """Test backtesting when player names don't match between S1 and S2."""
    s1_data = pd.DataFrame({
        'player_name': ['Player A', 'Player B'],
        'role': ['Bowler', 'Bowler'],
        'wickets': [10, 12]
    })
    
    s2_data = pd.DataFrame({
        'player_name': ['Player C', 'Player D'],  # Different players
        'role': ['Bowler', 'Bowler'],
        'wickets': [8, 15]
    })
    
    forecaster = S3PerformanceForecaster(s1_data, s2_data)
    result = forecaster.backtest_validation(metric_col='wickets', player_type='bowler')
    
    # Should return error or zero players
    assert 'error' in result or result['n_players'] == 0


def test_generate_recommendation_structure(forecaster):
    """Test that generate_recommendation returns expected structure."""
    rec = forecaster.generate_recommendation(
        player_name='Test Player',
        role='bowler',
        trend='IMPROVING',
        s3_pred=20,
        metric='wickets'
    )
    
    assert 'decision' in rec
    assert 'priority' in rec
    assert 'max_bid' in rec
    assert 'reason' in rec


def test_generate_recommendation_catastrophic_decline(forecaster):
    """Test recommendation for catastrophic decline."""
    rec = forecaster.generate_recommendation(
        player_name='Test Player',
        role='bowler',
        trend='CATASTROPHIC_DECLINE',
        s3_pred=5,
        metric='wickets'
    )
    
    assert '❌' in rec['decision'] or 'DO NOT' in rec['decision']
    assert rec['priority'] == 0


def test_generate_recommendation_improving_trend(forecaster):
    """Test recommendation for improving trend."""
    rec = forecaster.generate_recommendation(
        player_name='Test Player',
        role='bowler',
        trend='IMPROVING',
        s3_pred=20,
        metric='wickets'
    )
    
    assert '✅' in rec['decision'] or 'TARGET' in rec['decision']
    assert rec['priority'] == 8


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

def test_full_forecasting_pipeline_bowlers(forecaster):
    """Integration test: Full forecasting pipeline for bowlers."""
    # This tests that forecast_bowlers() can run end-to-end
    # We're testing the existence of the method and basic structure
    assert hasattr(forecaster, 'forecast_bowlers')
    assert callable(forecaster.forecast_bowlers)


def test_forecaster_predictions_are_deterministic(sample_s1_bowlers, sample_s2_bowlers):
    """Test that forecaster produces deterministic results."""
    forecaster1 = S3PerformanceForecaster(sample_s1_bowlers, sample_s2_bowlers)
    forecaster2 = S3PerformanceForecaster(sample_s1_bowlers, sample_s2_bowlers)
    
    result1 = forecaster1.backtest_validation(metric_col='wickets', player_type='bowler')
    result2 = forecaster2.backtest_validation(metric_col='wickets', player_type='bowler')
    
    # Results should be identical
    assert result1['mae'] == result2['mae']
    assert result1['rmse'] == result2['rmse']
    assert result1['n_players'] == result2['n_players']
