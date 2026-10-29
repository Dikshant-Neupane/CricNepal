"""Plan 4.2/4.3 — out-of-sample WPA production path (criteria P1-P6).

The legacy production pipeline trained on all deliveries and scored
the same rows, filled every innings' first-ball baseline with 0.50
(so innings 2 never inherited innings 1), and never produced an
exact terminal probability (audit R1/I-04). These tests pin the
rebuilt construction:

- walk-forward by match: a match is scored only by a model trained
  on strictly earlier dates; later data cannot change its numbers;
- decided innings-2 states are exactly 1.0 / 0.0;
- the WPA chain telescopes per innings, and exactly on the
  fixed-referent chain for the whole match;
- perspective is P(batting team wins) in both innings (plan 4.3).
"""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.analytics import win_probability_model as wp

ROOT = Path(__file__).resolve().parent.parent


def _mini_match(match_id: str, date: str, winner: str,
                inn1_runs: int = 12, inn2_runs: int = 8) -> tuple[dict, list]:
    match = {"match_id": match_id, "match_date": date,
             "winner_name": winner, "season": "S1"}
    rows = []
    for inn, (bat, bowl, total) in enumerate(
            [("Team A", "Team B", inn1_runs), ("Team B", "Team A", inn2_runs)],
            start=1):
        per = max(total // 12, 0)
        rem = total - per * 12
        for i in range(12):
            rows.append({
                "match_id": match_id, "innings": inn,
                "over": i // 6, "ball": (i % 6) + 1,
                "batting_team": bat, "bowling_team": bowl,
                "batter_name": f"{bat} batter", "bowler_name": f"{bowl} bowler",
                "runs_off_bat": per + (rem if i == 0 else 0),
                "runs_extras": 0,
                "runs_total": per + (rem if i == 0 else 0),
                "is_wicket": 0,
            })
    return match, rows


def _mini_dataset(n_matches: int = 8):
    matches, rows = [], []
    for k in range(n_matches):
        winner = "Team A" if k % 2 == 0 else "Team B"
        m, r = _mini_match(f"M{k}", f"2025-01-{k + 1:02d}", winner,
                           inn1_runs=10 + k, inn2_runs=6 + k)
        matches.append(m)
        rows.extend(r)
    return pd.DataFrame(rows), pd.DataFrame(matches)


def test_walk_forward_skips_matches_without_enough_history() -> None:
    deliveries, matches = _mini_dataset()
    states = wp.predict_walk_forward(deliveries, matches,
                                     min_train_matches=2)
    scored = set(states["match_id"])
    # Dates 1-2 have < 2 earlier matches; from date 3 on all score.
    assert scored == {f"M{k}" for k in range(2, 8)}
    assert states["p_win"].between(0, 1).all()


def test_walk_forward_later_data_cannot_change_a_match() -> None:
    deliveries, matches = _mini_dataset()
    full = wp.predict_walk_forward(deliveries, matches,
                                   min_train_matches=2, match_ids=["M5"])
    truncated_matches = matches[matches["match_date"] <= "2025-01-06"]
    truncated_deliveries = deliveries[
        deliveries["match_id"].isin(truncated_matches["match_id"])]
    part = wp.predict_walk_forward(truncated_deliveries, truncated_matches,
                                   min_train_matches=2, match_ids=["M5"])
    pd.testing.assert_series_equal(
        full["p_win"].reset_index(drop=True),
        part["p_win"].reset_index(drop=True))


def test_decided_states_are_forced_to_the_outcome() -> None:
    states = pd.DataFrame([
        {"innings": 2, "runs_required": 0, "balls_remaining": 30,
         "wickets_cumulative": 3, "p_win": 0.42},   # target reached
        {"innings": 2, "runs_required": 5, "balls_remaining": 0,
         "wickets_cumulative": 3, "p_win": 0.42},   # balls exhausted
        {"innings": 2, "runs_required": 5, "balls_remaining": 30,
         "wickets_cumulative": 10, "p_win": 0.42},  # all out
        {"innings": 2, "runs_required": 5, "balls_remaining": 30,
         "wickets_cumulative": 3, "p_win": 0.42},   # still live
        {"innings": 1, "runs_required": 0, "balls_remaining": 0,
         "wickets_cumulative": 10, "p_win": 0.42},  # innings 1: untouched
    ])
    out = wp._force_decided_states(states)
    assert out["p_win"].tolist() == [1.0, 0.0, 0.0, 0.42, 0.42]


@pytest.fixture(scope="module")
def real_match_states() -> pd.DataFrame:
    matches = pd.read_parquet(ROOT / "data/normalized/matches_normalized.parquet")
    deliveries = pd.read_parquet(
        ROOT / "data/normalized/ball_by_ball_normalized.parquet")
    s2 = matches[matches["season"] == "S2"].copy()
    s2["match_date"] = pd.to_datetime(s2["match_date"])
    target = s2.sort_values("match_date")["match_id"].iloc[-1]
    states = wp.predict_walk_forward(deliveries, matches,
                                     min_train_matches=4,
                                     match_ids=[target])
    states = wp._force_decided_states(states)
    return wp.add_wpa_columns(states)


def test_real_match_probability_invariants(real_match_states) -> None:
    st = real_match_states
    assert len(st) > 100
    # P1: probabilities are probabilities.
    assert st["p_win"].between(0, 1).all()
    inn1 = st[st["innings"] == 1]
    inn2 = st[st["innings"] == 2]
    p1_final = inn1["p_win"].iloc[-1]
    winner = inn2["match_winner"].iloc[0]
    inn2_batting = inn2["batting_team"].iloc[0]
    outcome_batting = 1.0 if inn2_batting == winner else 0.0

    # P4 + perspective (P2): the terminal innings-2 probability is the
    # batting team's exact outcome.
    assert inn2["p_win"].iloc[-1] == outcome_batting

    # P3: innings 2 opens at the complement of innings 1's final
    # probability (continuity under the batting-team perspective).
    assert inn2["prev_p_win"].iloc[0] == pytest.approx(1.0 - p1_final)

    # P5: telescoping, per innings and on the fixed-referent chain.
    assert inn1["wpa_batting"].sum() == pytest.approx(p1_final - 0.50)
    assert inn2["wpa_batting"].sum() == pytest.approx(
        outcome_batting - (1.0 - p1_final))
    first_team = inn1["batting_team"].iloc[0]
    outcome_first = 1.0 if first_team == winner else 0.0
    assert st["wpa_first_team"].sum() == pytest.approx(outcome_first - 0.50)
