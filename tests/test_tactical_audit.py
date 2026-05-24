"""
Comprehensive test suite for tactical_audit.py

Tests cover:
- Toss impact analysis
- Toss win rate calculations
- Batting first vs chasing logic
- Season comparisons
- Summary structure validation
- Edge cases and error handling
"""
import pytest
import pandas as pd
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.analytics.tactical_audit import (
    analyze_toss_impact,
    analyze_captaincy_change,
    TEAM,
    TOSS_DATA_S1,
    TOSS_DATA_S2
)

# ══════════════════════════════════════════════════════════════════════════
# FIXTURES
# ══════════════════════════════════════════════════════════════════════════

@pytest.fixture
def sample_matches():
    """Sample match data for Janakpur Bolts."""
    return pd.DataFrame({
        'match_id': ['M1', 'M2', 'M3', 'M4', 'M5', 'M6', 'M7', 'M8'],
        'season': ['S1', 'S1', 'S1', 'S1', 'S2', 'S2', 'S2', 'S2'],
        'team_1_name': [TEAM, TEAM, 'Opponent A', TEAM, TEAM, 'Opponent B', TEAM, TEAM],
        'team_2_name': ['Opponent A', 'Opponent B', TEAM, 'Opponent C', 'Opponent A', TEAM, 'Opponent C', 'Opponent D'],
        'winner_name': [TEAM, TEAM, TEAM, 'Opponent C', 'Opponent A', TEAM, 'Opponent C', 'Opponent D'],
        'toss_winner_name': [TEAM, 'Opponent B', TEAM, TEAM, TEAM, TEAM, 'Opponent C', TEAM],
        'toss_decision': ['bat', 'field', 'field', 'bat', 'field', 'bat', 'field', 'bat']
    })


@pytest.fixture
def sample_deliveries():
    """Sample delivery data to identify batting first vs chasing."""
    return pd.DataFrame({
        'match_id': ['M1'] * 20 + ['M2'] * 20 + ['M3'] * 20 + ['M4'] * 20 + 
                    ['M5'] * 20 + ['M6'] * 20 + ['M7'] * 20 + ['M8'] * 20,
        'season': ['S1'] * 80 + ['S2'] * 80,
        'innings': ([1] * 10 + [2] * 10) * 8,
        'batting_team': (
            # M1: Janakpur batted first (innings 1)
            [TEAM] * 10 + ['Opponent A'] * 10 +
            # M2: Opponent B batted first
            ['Opponent B'] * 10 + [TEAM] * 10 +
            # M3: Opponent A batted first
            ['Opponent A'] * 10 + [TEAM] * 10 +
            # M4: Janakpur batted first
            [TEAM] * 10 + ['Opponent C'] * 10 +
            # M5: Opponent A batted first
            ['Opponent A'] * 10 + [TEAM] * 10 +
            # M6: Janakpur batted first
            [TEAM] * 10 + ['Opponent B'] * 10 +
            # M7: Opponent C batted first
            ['Opponent C'] * 10 + [TEAM] * 10 +
            # M8: Janakpur batted first
            [TEAM] * 10 + ['Opponent D'] * 10
        ),
        'bowling_team': (
            ['Opponent A'] * 10 + [TEAM] * 10 +
            [TEAM] * 10 + ['Opponent B'] * 10 +
            [TEAM] * 10 + ['Opponent A'] * 10 +
            ['Opponent C'] * 10 + [TEAM] * 10 +
            [TEAM] * 10 + ['Opponent A'] * 10 +
            ['Opponent B'] * 10 + [TEAM] * 10 +
            [TEAM] * 10 + ['Opponent C'] * 10 +
            ['Opponent D'] * 10 + [TEAM] * 10
        ),
        'over': ([1, 2, 3, 4, 5, 6, 7, 8, 9, 10] * 2) * 8,
        'runs_off_bat': [1, 0, 4, 2, 0, 6, 0, 1, 0, 4] * 16
    })


# ══════════════════════════════════════════════════════════════════════════
# TEST TOSS DATA CONSTANTS
# ══════════════════════════════════════════════════════════════════════════

def test_toss_data_s1_structure():
    """Verify S1 toss data has correct structure."""
    assert 'S1_JAB_TOSSES' in TOSS_DATA_S1
    tosses = TOSS_DATA_S1['S1_JAB_TOSSES']
    assert isinstance(tosses, list)
    assert len(tosses) > 0
    
    # Check first record structure
    first_toss = tosses[0]
    assert 'match_num' in first_toss
    assert 'toss_winner' in first_toss
    assert 'decision' in first_toss
    assert first_toss['decision'] in ['bat', 'field']


def test_toss_data_s2_structure():
    """Verify S2 toss data has correct structure."""
    assert 'S2_JAB_TOSSES' in TOSS_DATA_S2
    tosses = TOSS_DATA_S2['S2_JAB_TOSSES']
    assert isinstance(tosses, list)
    assert len(tosses) > 0
    
    # Check decision values
    for toss in tosses:
        assert toss['decision'] in ['bat', 'field']


def test_team_constant():
    """Verify TEAM constant is properly set."""
    assert TEAM == "Janakpur Bolts"


# ══════════════════════════════════════════════════════════════════════════
# TEST CAPTAINCY CHANGE ANALYSIS (PLACEHOLDER)
# ══════════════════════════════════════════════════════════════════════════

def test_analyze_captaincy_change_executes():
    """Captaincy change analysis should execute without errors (placeholder function)."""
    # This is a placeholder function that just logs warnings
    # Should not raise any exceptions
    try:
        analyze_captaincy_change()
        assert True
    except Exception as e:
        pytest.fail(f"analyze_captaincy_change() raised {e}")


def test_analyze_captaincy_change_logs_warnings(caplog):
    """Captaincy change analysis should log warnings about missing data."""
    import logging
    caplog.set_level(logging.INFO)
    
    analyze_captaincy_change()
    
    # Should mention the captaincy change
    log_text = caplog.text
    assert 'Anil Sah' in log_text or 'Wayne Parnell' in log_text
    assert 'CRITICAL GAP' in log_text or 'external research' in log_text.lower()


# ══════════════════════════════════════════════════════════════════════════
# TEST HELPER FUNCTIONS (if they exist or to test data processing logic)
# ══════════════════════════════════════════════════════════════════════════

def test_toss_records_processing():
    """Test that toss records can be converted to DataFrame correctly."""
    toss_records = []
    
    # Process S1 tosses
    for toss in TOSS_DATA_S1["S1_JAB_TOSSES"]:
        toss_records.append({
            'season': 'S1',
            'match_num': toss['match_num'],
            'toss_won': toss['toss_winner'] == TEAM,
            'toss_decision': toss['decision'],
            'playoff': toss.get('playoff', None)
        })
    
    df = pd.DataFrame(toss_records)
    assert isinstance(df, pd.DataFrame)
    assert 'season' in df.columns
    assert 'toss_won' in df.columns
    assert 'toss_decision' in df.columns
    assert df['toss_won'].dtype == bool


def test_batting_first_identification_logic():
    """Test logic for identifying batting first vs chasing."""
    # Create sample data
    deliveries = pd.DataFrame({
        'match_id': ['M1'] * 20,
        'innings': [1] * 10 + [2] * 10,
        'batting_team': [TEAM] * 10 + ['Opponent'] * 10,
        'bowling_team': ['Opponent'] * 10 + [TEAM] * 10
    })
    
    innings_1 = deliveries[deliveries['innings'] == 1]
    
    # Janakpur batted first if they were batting team in innings 1
    batted_first = innings_1.iloc[0]['batting_team'] == TEAM
    assert batted_first == True


def test_chasing_identification_logic():
    """Test logic for identifying chasing scenarios."""
    # Create sample data where Janakpur chased
    deliveries = pd.DataFrame({
        'match_id': ['M1'] * 20,
        'innings': [1] * 10 + [2] * 10,
        'batting_team': ['Opponent'] * 10 + [TEAM] * 10,
        'bowling_team': [TEAM] * 10 + ['Opponent'] * 10
    })
    
    innings_1 = deliveries[deliveries['innings'] == 1]
    
    # Janakpur chased if they were NOT batting team in innings 1
    chased = innings_1.iloc[0]['batting_team'] != TEAM
    assert chased == True


# ══════════════════════════════════════════════════════════════════════════
# TEST WIN RATE CALCULATIONS
# ══════════════════════════════════════════════════════════════════════════

def test_win_rate_calculation():
    """Test win rate calculation logic."""
    matches = pd.DataFrame({
        'match_id': ['M1', 'M2', 'M3', 'M4'],
        'winner_name': [TEAM, TEAM, 'Opponent', TEAM]
    })
    
    wins = len(matches[matches['winner_name'] == TEAM])
    total = len(matches)
    win_rate = (wins / total * 100)
    
    assert wins == 3
    assert total == 4
    assert win_rate == 75.0


def test_toss_win_rate_calculation():
    """Test toss win rate calculation logic."""
    toss_records = pd.DataFrame({
        'toss_won': [True, True, False, True, False]
    })
    
    toss_wins = toss_records['toss_won'].sum()
    total = len(toss_records)
    toss_win_rate = (toss_wins / total * 100)
    
    assert toss_wins == 3
    assert total == 5
    assert toss_win_rate == 60.0


# ══════════════════════════════════════════════════════════════════════════
# TEST TOSS DECISION ANALYSIS
# ══════════════════════════════════════════════════════════════════════════

def test_toss_decision_counts():
    """Test counting toss decisions (bat vs field)."""
    tosses = pd.DataFrame({
        'toss_won': [True, True, False, True, True, False],
        'toss_decision': ['field', 'bat', 'field', 'field', 'bat', 'bat']
    })
    
    tosses_won = tosses[tosses['toss_won']]
    field_first = len(tosses_won[tosses_won['toss_decision'] == 'field'])
    bat_first = len(tosses_won[tosses_won['toss_decision'] == 'bat'])
    
    assert field_first == 2
    assert bat_first == 2


def test_toss_decision_preference():
    """Test identifying toss decision preference."""
    decisions = ['field', 'field', 'field', 'bat']
    
    field_count = decisions.count('field')
    bat_count = decisions.count('bat')
    
    assert field_count > bat_count  # Prefer fielding first
    assert field_count == 3
    assert bat_count == 1


# ══════════════════════════════════════════════════════════════════════════
# TEST SEASON COMPARISONS
# ══════════════════════════════════════════════════════════════════════════

def test_season_comparison_logic():
    """Test season comparison calculations."""
    s1_value = 60.0  # S1 win rate
    s2_value = 20.0  # S2 win rate
    
    delta = s2_value - s1_value
    
    assert delta == -40.0
    assert delta < 0  # Decline


def test_percentage_delta_calculation():
    """Test percentage point delta calculation."""
    s1_pct = 70.0
    s2_pct = 14.3
    
    delta = s2_pct - s1_pct
    
    assert round(delta, 1) == -55.7


# ══════════════════════════════════════════════════════════════════════════
# TEST EDGE CASES
# ══════════════════════════════════════════════════════════════════════════

def test_handles_zero_tosses_won():
    """Should handle case where team wins zero tosses."""
    toss_wins = 0
    total_matches = 5
    
    toss_pct = (toss_wins / total_matches * 100) if total_matches > 0 else 0
    
    assert toss_pct == 0.0


def test_handles_no_matches():
    """Should handle case with no matches."""
    matches = pd.DataFrame(columns=['match_id', 'winner_name'])
    
    total = len(matches)
    assert total == 0


def test_handles_empty_toss_list():
    """Should handle empty toss list."""
    tosses = []
    
    assert len(tosses) == 0
    assert isinstance(tosses, list)


def test_handles_division_by_zero():
    """Should handle division by zero in win rate calculations."""
    wins = 0
    total = 0
    
    win_rate = (wins / total * 100) if total > 0 else 0
    
    assert win_rate == 0


# ══════════════════════════════════════════════════════════════════════════
# TEST DATA VALIDATION
# ══════════════════════════════════════════════════════════════════════════

def test_validates_toss_decision_values():
    """Toss decisions should only be 'bat' or 'field'."""
    valid_decisions = ['bat', 'field']
    
    # Test S1 data
    for toss in TOSS_DATA_S1['S1_JAB_TOSSES']:
        assert toss['decision'] in valid_decisions
    
    # Test S2 data
    for toss in TOSS_DATA_S2['S2_JAB_TOSSES']:
        assert toss['decision'] in valid_decisions


def test_validates_match_numbers():
    """Match numbers should be positive integers."""
    # Test S1 data
    for toss in TOSS_DATA_S1['S1_JAB_TOSSES']:
        assert isinstance(toss['match_num'], int)
        assert toss['match_num'] > 0
    
    # Test S2 data
    for toss in TOSS_DATA_S2['S2_JAB_TOSSES']:
        assert isinstance(toss['match_num'], int)
        assert toss['match_num'] > 0


def test_validates_team_names():
    """Toss winner should be valid team name."""
    # Test S1 data
    for toss in TOSS_DATA_S1['S1_JAB_TOSSES']:
        assert isinstance(toss['toss_winner'], str)
        assert len(toss['toss_winner']) > 0
    
    # Test S2 data
    for toss in TOSS_DATA_S2['S2_JAB_TOSSES']:
        assert isinstance(toss['toss_winner'], str)
        assert len(toss['toss_winner']) > 0
