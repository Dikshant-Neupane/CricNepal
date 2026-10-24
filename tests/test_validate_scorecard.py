"""Scorecard validator: a closing entry passes, a broken one fails."""
import pandas as pd

from scripts.scorecard_check import check_innings, overs_to_balls


def _innings(bat_runs=150):
    facts = pd.Series({
        "innings": 1, "total_runs": 160, "total_wickets": 2,
        "total_overs": 20.0, "extras_byes": 2, "extras_legbyes": 3,
        "extras_wides": 4, "extras_noballs": 1, "extras_penalty": 0})
    bat = pd.DataFrame([
        {"batting_pos": 1, "runs": bat_runs, "dismissal_type": "c X b Y"},
        {"batting_pos": 2, "runs": 0, "dismissal_type": "b Y"},
        {"batting_pos": 3, "runs": 0, "dismissal_type": "not out"},
    ])
    bowl = pd.DataFrame([
        {"balls_bowled": 60, "runs_conceded": 80},
        {"balls_bowled": 60, "runs_conceded": 75},
    ])
    return facts, bat, bowl


def test_overs_to_balls():
    assert overs_to_balls(20.0) == 120
    assert overs_to_balls(17.3) == 105


def test_closing_entry_passes():
    facts, bat, bowl = _innings()
    assert check_innings(facts, bat, bowl) == []


def test_broken_entry_fails_with_reasons():
    facts, bat, bowl = _innings(bat_runs=140)
    problems = check_innings(facts, bat, bowl)
    assert any("batting closure" in p for p in problems)
