"""
Tests for `src.analytics.opposition_strength_analysis`.

Covers Elo math invariants, end-to-end behaviour against the real dataset,
and basic sanity of the season summary / bootstrap helpers.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.analytics.opposition_strength_analysis import (  # noqa: E402
    DEFAULT_K,
    INITIAL_ELO,
    TEAM,
    _expected,
    bootstrap_wae,
    compute_elo_history,
    opposition_strength_for_team,
    season_summary,
)


# --------------------------------------------------------------------------- #
# Elo math invariants
# --------------------------------------------------------------------------- #

def test_expected_is_one_half_for_equal_ratings():
    assert _expected(1500, 1500) == pytest.approx(0.5)


def test_expected_is_monotonic_in_rating_difference():
    # Higher rating implies higher expected score
    assert _expected(1600, 1500) > 0.5
    assert _expected(1400, 1500) < 0.5


def test_expected_pair_sums_to_one():
    a, b = 1450.0, 1620.0
    assert _expected(a, b) + _expected(b, a) == pytest.approx(1.0)


def test_elo_400_point_lead_gives_known_expected():
    """A 400-point Elo gap is the canonical ~10:1 expected odds (about 0.909)."""
    assert _expected(1900, 1500) == pytest.approx(10 / 11, abs=1e-6)


# --------------------------------------------------------------------------- #
# Tiny synthetic dataset
# --------------------------------------------------------------------------- #

def _make_synthetic_matches() -> pd.DataFrame:
    """Two-team, two-match synthetic dataset where Team A wins both."""
    return pd.DataFrame(
        [
            {
                "match_id": "m1",
                "season": "S1",
                "match_date": "2024-01-01",
                "team_1_name": "A",
                "team_2_name": "B",
                "winner_name": "A",
                "result_status": "normal",
            },
            {
                "match_id": "m2",
                "season": "S1",
                "match_date": "2024-01-02",
                "team_1_name": "A",
                "team_2_name": "B",
                "winner_name": "A",
                "result_status": "normal",
            },
        ]
    )


def test_elo_history_starts_at_initial():
    matches = _make_synthetic_matches()
    history = compute_elo_history(matches)
    first = history.iloc[0]
    assert first["team_1_pre"] == INITIAL_ELO
    assert first["team_2_pre"] == INITIAL_ELO


def test_elo_history_zero_sum_per_match():
    """Standard Elo with no draw inflation: r1_post + r2_post == r1_pre + r2_pre."""
    matches = _make_synthetic_matches()
    history = compute_elo_history(matches)
    for _, row in history.iterrows():
        if pd.isna(row["score_team_1"]):
            continue
        pre_sum = row["team_1_pre"] + row["team_2_pre"]
        post_sum = row["team_1_post"] + row["team_2_post"]
        assert post_sum == pytest.approx(pre_sum, abs=1e-9)


def test_elo_winner_rating_increases():
    matches = _make_synthetic_matches()
    history = compute_elo_history(matches)
    first = history.iloc[0]
    assert first["team_1_post"] > first["team_1_pre"]
    assert first["team_2_post"] < first["team_2_pre"]


def test_elo_repeat_wins_compound():
    """Winning twice should leave the winner above their post-first-match rating."""
    matches = _make_synthetic_matches()
    history = compute_elo_history(matches)
    assert history.iloc[1]["team_1_post"] > history.iloc[0]["team_1_post"]


def test_first_match_delta_matches_k_factor():
    """At equal ratings a win should move the winner exactly K/2 points."""
    matches = _make_synthetic_matches()
    history = compute_elo_history(matches, k=20.0)
    first = history.iloc[0]
    assert first["team_1_post"] - first["team_1_pre"] == pytest.approx(10.0, abs=1e-6)


def test_tie_splits_score_evenly():
    matches = _make_synthetic_matches()
    matches.loc[0, "winner_name"] = None
    matches.loc[0, "result_status"] = "tie"
    history = compute_elo_history(matches)
    first = history.iloc[0]
    # With equal ratings, a tie returns expected score, so no change at all
    assert first["team_1_post"] == pytest.approx(first["team_1_pre"], abs=1e-9)
    assert first["team_2_post"] == pytest.approx(first["team_2_pre"], abs=1e-9)


def test_season_shrinkage_pulls_back_to_initial():
    """Across a season boundary, full shrinkage = full reset."""
    df = pd.DataFrame(
        [
            {
                "match_id": "m1",
                "season": "S1",
                "match_date": "2024-01-01",
                "team_1_name": "A",
                "team_2_name": "B",
                "winner_name": "A",
                "result_status": "normal",
            },
            {
                "match_id": "m2",
                "season": "S2",
                "match_date": "2024-06-01",
                "team_1_name": "A",
                "team_2_name": "B",
                "winner_name": "A",
                "result_status": "normal",
            },
        ]
    )
    history = compute_elo_history(df, season_shrinkage=1.0)
    second = history.iloc[1]
    # With full shrinkage, both teams should start S2 at the prior mean
    assert second["team_1_pre"] == pytest.approx(INITIAL_ELO, abs=1e-9)
    assert second["team_2_pre"] == pytest.approx(INITIAL_ELO, abs=1e-9)


# --------------------------------------------------------------------------- #
# End-to-end behaviour against the real normalized dataset
# --------------------------------------------------------------------------- #

@pytest.fixture(scope="module")
def real_matches() -> pd.DataFrame:
    return pd.read_parquet(
        Path(__file__).resolve().parent.parent / "data" / "normalized" / "matches_normalized.parquet"
    )


def test_real_dataset_elo_history_one_row_per_match(real_matches):
    history = compute_elo_history(real_matches)
    assert len(history) == len(real_matches)


def test_real_dataset_jab_summary_has_both_seasons(real_matches):
    history = compute_elo_history(real_matches)
    opp = opposition_strength_for_team(history, TEAM)
    summary = season_summary(opp)
    assert set(summary["season"].tolist()) == {"S1", "S2"}


def test_real_dataset_wae_signs_match_intuition(real_matches):
    """JAB won 7/10 in S1 and 1/7 in S2. WAE should be positive in S1 and
    very negative in S2 unless the opposition was wildly different.
    """
    history = compute_elo_history(real_matches)
    opp = opposition_strength_for_team(history, TEAM)
    summary = season_summary(opp).set_index("season")
    assert summary.loc["S1", "wins_above_expected"] > 0
    assert summary.loc["S2", "wins_above_expected"] < 0


def test_bootstrap_ci_brackets_observed(real_matches):
    history = compute_elo_history(real_matches)
    opp = opposition_strength_for_team(history, TEAM)
    boot = bootstrap_wae(opp, n_iter=500, seed=7)
    for _, row in boot.iterrows():
        assert row["wae_ci_lo"] <= row["wae_observed"] <= row["wae_ci_hi"]


def test_default_k_is_set():
    """Make sure DEFAULT_K is a sane positive number; protects against
    accidental edits."""
    assert 0 < DEFAULT_K <= 64
