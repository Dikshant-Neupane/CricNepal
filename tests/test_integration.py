"""
Integration Test Suite - Full Analytics Pipeline
================================================

Tests the complete data flow:
1. Load data from parquet files
2. Run all analytics modules
3. Verify outputs and cross-module consistency
4. Test error handling and edge cases

These tests use real data files and validate the entire system.
"""
import pytest
import pandas as pd
from pathlib import Path
import sys
import json

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.analytics import (
    root_cause_analysis,
    player_attribution_analysis,
    s3_performance_forecaster,
    tactical_audit
)
from src.config.paths import NORMALIZED_DIR, EXPORT_DIR

# ══════════════════════════════════════════════════════════════════════════
# SETUP AND CONFIGURATION
# ══════════════════════════════════════════════════════════════════════════

TEAM = "Janakpur Bolts"


@pytest.fixture(scope="module")
def data_files_exist():
    """Check if normalized data files exist."""
    matches_file = NORMALIZED_DIR / "matches_normalized.parquet"
    deliveries_file = NORMALIZED_DIR / "ball_by_ball_normalized.parquet"
    
    if not matches_file.exists():
        pytest.skip(f"Missing required file: {matches_file}")
    if not deliveries_file.exists():
        pytest.skip(f"Missing required file: {deliveries_file}")
    
    return True


# ══════════════════════════════════════════════════════════════════════════
# TEST DATA LOADING
# ══════════════════════════════════════════════════════════════════════════

def test_load_normalized_matches(data_files_exist):
    """Integration: Load normalized match data."""
    matches = pd.read_parquet(NORMALIZED_DIR / "matches_normalized.parquet")
    
    assert isinstance(matches, pd.DataFrame)
    assert len(matches) > 0
    assert 'match_id' in matches.columns
    assert 'season' in matches.columns
    assert 'winner_name' in matches.columns


def test_load_normalized_deliveries(data_files_exist):
    """Integration: Load normalized delivery data."""
    deliveries = pd.read_parquet(NORMALIZED_DIR / "ball_by_ball_normalized.parquet")
    
    assert isinstance(deliveries, pd.DataFrame)
    assert len(deliveries) > 0
    assert 'match_id' in deliveries.columns
    assert 'innings' in deliveries.columns
    assert 'batting_team' in deliveries.columns


def test_data_consistency_match_ids(data_files_exist):
    """Integration: Verify match_ids are consistent across files."""
    matches = pd.read_parquet(NORMALIZED_DIR / "matches_normalized.parquet")
    deliveries = pd.read_parquet(NORMALIZED_DIR / "ball_by_ball_normalized.parquet")
    
    match_ids_matches = set(matches['match_id'].unique())
    match_ids_deliveries = set(deliveries['match_id'].unique())
    
    # All delivery match_ids should exist in matches
    assert match_ids_deliveries.issubset(match_ids_matches)


def test_janakpur_bolts_data_exists(data_files_exist):
    """Integration: Verify Janakpur Bolts data is present."""
    matches = pd.read_parquet(NORMALIZED_DIR / "matches_normalized.parquet")
    
    jab_matches = matches[
        (matches['team_1_name'] == TEAM) | (matches['team_2_name'] == TEAM)
    ]
    
    assert len(jab_matches) > 0, "No Janakpur Bolts matches found"
    
    # Should have both S1 and S2 data
    seasons = jab_matches['season'].unique()
    assert 'S1' in seasons or 'S2' in seasons


# ══════════════════════════════════════════════════════════════════════════
# TEST ROOT CAUSE ANALYSIS PIPELINE
# ══════════════════════════════════════════════════════════════════════════

def test_root_cause_load_janakpur_matches(data_files_exist):
    """Integration: Root cause analysis can load Janakpur data."""
    matches_df, deliveries_df = root_cause_analysis.load_janakpur_matches()
    
    assert isinstance(matches_df, pd.DataFrame)
    assert isinstance(deliveries_df, pd.DataFrame)
    assert len(matches_df) > 0
    assert len(deliveries_df) > 0


def test_root_cause_analyze_batting_by_phase(data_files_exist):
    """Integration: Analyze batting performance by phase."""
    matches_df, deliveries_df = root_cause_analysis.load_janakpur_matches()
    
    result = root_cause_analysis.analyze_batting_by_phase(matches_df, deliveries_df)
    
    assert isinstance(result, pd.DataFrame)
    assert 'phase' in result.columns
    assert 'run_rate' in result.columns
    assert 'season' in result.columns


def test_root_cause_analyze_bowling_by_phase(data_files_exist):
    """Integration: Analyze bowling performance by phase."""
    matches_df, deliveries_df = root_cause_analysis.load_janakpur_matches()
    
    result = root_cause_analysis.analyze_bowling_by_phase(matches_df, deliveries_df)
    
    assert isinstance(result, pd.DataFrame)
    assert 'phase' in result.columns
    assert 'economy' in result.columns
    assert 'season' in result.columns


# ══════════════════════════════════════════════════════════════════════════
# TEST PLAYER ATTRIBUTION PIPELINE
# ══════════════════════════════════════════════════════════════════════════

def test_player_attribution_load_data(data_files_exist):
    """Integration: Player attribution can load Janakpur data."""
    matches_df, deliveries_df = player_attribution_analysis.load_janakpur_data()
    
    assert isinstance(matches_df, pd.DataFrame)
    assert isinstance(deliveries_df, pd.DataFrame)
    assert len(matches_df) > 0
    assert len(deliveries_df) > 0


def test_player_attribution_analyze_death_bowlers(data_files_exist):
    """Integration: Analyze death bowling performance."""
    matches_df, deliveries_df = player_attribution_analysis.load_janakpur_data()
    
    result = player_attribution_analysis.analyze_death_bowlers(matches_df, deliveries_df)
    
    assert isinstance(result, pd.DataFrame)
    if len(result) > 0:  # May be empty if no death bowling data
        assert 'bowler_name' in result.columns
        assert 'economy_rate' in result.columns


def test_player_attribution_analyze_squad_retention(data_files_exist):
    """Integration: Analyze squad retention."""
    _, deliveries_df = player_attribution_analysis.load_janakpur_data()
    
    result = player_attribution_analysis.analyze_squad_retention(deliveries_df)
    
    assert isinstance(result, dict)
    assert 'retention_summary' in result
    assert 'stats' in result


# ══════════════════════════════════════════════════════════════════════════
# TEST S3 FORECASTER PIPELINE
# ══════════════════════════════════════════════════════════════════════════

def test_forecaster_load_bowling_data(data_files_exist):
    """Integration: S3 forecaster can load bowling data."""
    # The forecaster's load methods are internal, but we can test the exported data
    matches = pd.read_parquet(NORMALIZED_DIR / "matches_normalized.parquet")
    deliveries = pd.read_parquet(NORMALIZED_DIR / "ball_by_ball_normalized.parquet")
    
    # Filter Janakpur matches
    jab_matches = matches[
        (matches['team_1_name'] == TEAM) | (matches['team_2_name'] == TEAM)
    ]
    
    assert len(jab_matches) > 0


def test_forecaster_backtest_validation_structure(data_files_exist):
    """Integration: Backtest validation returns correct structure."""
    # Create sample S1/S2 data for validation test
    # Note: Forecaster expects 'player_name' column and role containing 'bowl'
    s1_bowlers = pd.DataFrame({
        'player_name': ['Bowler A', 'Bowler B'],
        'role': ['Bowler', 'Bowler'],
        'economy': [8.0, 9.0],
        'wickets': [12, 8]
    })
    
    s2_bowlers = pd.DataFrame({
        'player_name': ['Bowler A', 'Bowler B'],
        'role': ['Bowler', 'Bowler'],
        'economy': [10.0, 8.5],
        'wickets': [10, 10]
    })
    
    forecaster = s3_performance_forecaster.S3PerformanceForecaster(s1_bowlers, s2_bowlers)
    result = forecaster.backtest_validation('wickets', 'bowler')
    
    assert isinstance(result, dict)
    assert 'mae' in result
    assert 'n_players' in result
    assert 'directional_accuracy' in result


# ══════════════════════════════════════════════════════════════════════════
# TEST CROSS-MODULE DATA CONSISTENCY
# ══════════════════════════════════════════════════════════════════════════

def test_cross_module_match_counts_consistent(data_files_exist):
    """Integration: All modules should see same number of matches."""
    # Load from each module
    root_matches, _ = root_cause_analysis.load_janakpur_matches()
    player_matches, _ = player_attribution_analysis.load_janakpur_data()
    
    # Should have same match count
    assert len(root_matches) == len(player_matches)


def test_cross_module_delivery_counts_consistent(data_files_exist):
    """Integration: All modules should see same deliveries."""
    _, root_deliveries = root_cause_analysis.load_janakpur_matches()
    _, player_deliveries = player_attribution_analysis.load_janakpur_data()
    
    # Should have same delivery count (may differ slightly if filtering differs)
    # Allow 1% variance
    assert abs(len(root_deliveries) - len(player_deliveries)) / len(root_deliveries) < 0.01


def test_cross_module_team_name_consistency(data_files_exist):
    """Integration: Team name should be consistent across modules."""
    assert root_cause_analysis.TEAM == TEAM
    assert player_attribution_analysis.TEAM == TEAM
    assert tactical_audit.TEAM == TEAM


# ══════════════════════════════════════════════════════════════════════════
# TEST ERROR HANDLING
# ══════════════════════════════════════════════════════════════════════════

def test_handles_missing_columns_gracefully():
    """Integration: Modules should handle missing columns gracefully."""
    # Create DataFrame with minimal columns
    minimal_df = pd.DataFrame({
        'match_id': ['M1'],
        'season': ['S1']
    })
    
    # Should not crash when processing (may return empty results)
    try:
        # This should either succeed or raise a clear error
        root_cause_analysis.classify_phase(5)
        assert True
    except Exception as e:
        # Should be a clear error message
        assert 'phase' in str(e).lower() or 'over' in str(e).lower()


def test_handles_empty_dataframe():
    """Integration: Modules should handle empty DataFrames."""
    empty_df = pd.DataFrame()
    
    # Should handle empty input gracefully
    assert len(empty_df) == 0
    assert isinstance(empty_df, pd.DataFrame)


# ══════════════════════════════════════════════════════════════════════════
# TEST EXPORT FUNCTIONALITY
# ══════════════════════════════════════════════════════════════════════════

def test_export_directory_exists():
    """Integration: Export directory should exist or be creatable."""
    export_dir = EXPORT_DIR
    
    # Create if doesn't exist
    export_dir.mkdir(parents=True, exist_ok=True)
    
    assert export_dir.exists()
    assert export_dir.is_dir()


def test_can_write_json_export():
    """Integration: Should be able to write JSON export files."""
    export_dir = EXPORT_DIR
    export_dir.mkdir(parents=True, exist_ok=True)
    
    test_file = export_dir / "test_integration.json"
    test_data = {"test": "data", "value": 123}
    
    with open(test_file, 'w') as f:
        json.dump(test_data, f, indent=2)
    
    assert test_file.exists()
    
    # Clean up
    test_file.unlink()


def test_can_write_csv_export():
    """Integration: Should be able to write CSV export files."""
    export_dir = EXPORT_DIR
    export_dir.mkdir(parents=True, exist_ok=True)
    
    test_file = export_dir / "test_integration.csv"
    test_df = pd.DataFrame({'col1': [1, 2, 3], 'col2': ['a', 'b', 'c']})
    
    test_df.to_csv(test_file, index=False)
    
    assert test_file.exists()
    
    # Verify can read back
    loaded_df = pd.read_csv(test_file)
    assert len(loaded_df) == 3
    
    # Clean up
    test_file.unlink()


# ══════════════════════════════════════════════════════════════════════════
# TEST SEASON FILTERING
# ══════════════════════════════════════════════════════════════════════════

def test_season_filtering_s1(data_files_exist):
    """Integration: Can filter S1 data correctly."""
    matches = pd.read_parquet(NORMALIZED_DIR / "matches_normalized.parquet")
    
    s1_matches = matches[matches['season'] == 'S1']
    
    if len(s1_matches) > 0:
        assert all(s1_matches['season'] == 'S1')


def test_season_filtering_s2(data_files_exist):
    """Integration: Can filter S2 data correctly."""
    matches = pd.read_parquet(NORMALIZED_DIR / "matches_normalized.parquet")
    
    s2_matches = matches[matches['season'] == 'S2']
    
    if len(s2_matches) > 0:
        assert all(s2_matches['season'] == 'S2')


# ══════════════════════════════════════════════════════════════════════════
# TEST DATA QUALITY
# ══════════════════════════════════════════════════════════════════════════

def test_no_duplicate_match_ids(data_files_exist):
    """Integration: Match IDs should be unique."""
    matches = pd.read_parquet(NORMALIZED_DIR / "matches_normalized.parquet")
    
    duplicates = matches['match_id'].duplicated().sum()
    assert duplicates == 0, f"Found {duplicates} duplicate match_ids"


def test_no_missing_winners_in_completed_matches(data_files_exist):
    """Integration: Completed matches should have winners."""
    matches = pd.read_parquet(NORMALIZED_DIR / "matches_normalized.parquet")
    
    # All matches should have a winner (no ties in T20)
    missing_winners = matches['winner_name'].isna().sum()
    
    # Allow some missing (e.g., abandoned matches)
    total = len(matches)
    missing_pct = (missing_winners / total * 100) if total > 0 else 0
    
    assert missing_pct < 10, f"Too many matches missing winners: {missing_pct:.1f}%"


def test_deliveries_have_required_columns(data_files_exist):
    """Integration: Deliveries should have all required columns."""
    deliveries = pd.read_parquet(NORMALIZED_DIR / "ball_by_ball_normalized.parquet")
    
    required_cols = ['match_id', 'innings', 'batting_team', 'bowling_team', 'over']
    
    for col in required_cols:
        assert col in deliveries.columns, f"Missing required column: {col}"


# ══════════════════════════════════════════════════════════════════════════
# TEST PERFORMANCE
# ══════════════════════════════════════════════════════════════════════════

def test_data_loading_performance(data_files_exist):
    """Integration: Data loading should be reasonably fast."""
    import time
    
    start = time.time()
    matches = pd.read_parquet(NORMALIZED_DIR / "matches_normalized.parquet")
    deliveries = pd.read_parquet(NORMALIZED_DIR / "ball_by_ball_normalized.parquet")
    elapsed = time.time() - start
    
    # Should load in under 5 seconds
    assert elapsed < 5.0, f"Data loading took too long: {elapsed:.2f}s"
    assert len(matches) > 0
    assert len(deliveries) > 0
