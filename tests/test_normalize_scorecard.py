"""
Tests for the scorecard backfill in `src.preprocessing.normalize_data`.

The upstream Cric_Data parquet ships `innings_X_*` columns 100% null
(verified during the 2026-05-28 audit). The normalize step now reconstructs
those columns from ball-by-ball aggregates so downstream pages don't need
to re-derive NRR every render. These tests pin the invariants of that
reconstruction.
"""

from __future__ import annotations

import pandas as pd
import pytest

from src.preprocessing.normalize_data import backfill_scorecard_from_bbb


def _bbb(rows):
    return pd.DataFrame(
        rows,
        columns=[
            "match_id",
            "innings",
            "over",
            "batting_team",
            "runs_total",
            "runs_extras",
            "is_wicket",
        ],
    )


@pytest.fixture
def synth_match_and_bbb():
    """One match, two innings, hand-rolled ball-by-ball.

    Innings 1: Team A, 100 runs (95 bat + 5 extras), 8 wickets, 12 balls
    Innings 2: Team B, 105 runs (100 bat + 5 extras), 4 wickets, 13 balls
    """
    match = pd.DataFrame(
        [
            {
                "match_id": "m1",
                "team_1_name": "A",
                "team_2_name": "B",
                "season": "S1",
                # All innings_X columns null — the upstream-data condition we
                # want to simulate.
                "innings_1_team": None,
                "innings_1_runs": None,
                "innings_1_wickets": None,
                "innings_1_overs": None,
                "innings_1_extras": None,
                "innings_2_team": None,
                "innings_2_runs": None,
                "innings_2_wickets": None,
                "innings_2_overs": None,
                "innings_2_extras": None,
            }
        ]
    )

    rows = []
    # Innings 1: 12 balls, 95 bat + 5 extras = 100 runs, 8 wickets
    for i in range(12):
        rows.append(("m1", 1, i // 6, "A", 8 if i < 11 else 10,
                     0 if i < 11 else 5, 1 if i < 8 else 0))
    # Innings 2: 13 balls, 100 bat + 5 extras = 105 runs, 4 wickets
    for i in range(13):
        rows.append(("m1", 2, i // 6, "B",
                     8 if i < 12 else 5,
                     0 if i < 12 else 5,
                     1 if i < 4 else 0))
    bbb = _bbb(rows)
    # Make the runs_total column actually total
    return match, bbb


# --------------------------------------------------------------------------- #
# Behaviour
# --------------------------------------------------------------------------- #

def test_backfill_populates_team_columns(synth_match_and_bbb):
    match, bbb = synth_match_and_bbb
    out = backfill_scorecard_from_bbb(match, bbb)
    assert out.iloc[0]["innings_1_team"] == "A"
    assert out.iloc[0]["innings_2_team"] == "B"


def test_backfill_runs_match_bbb_sum(synth_match_and_bbb):
    match, bbb = synth_match_and_bbb
    out = backfill_scorecard_from_bbb(match, bbb)
    expected_inn1 = bbb[bbb["innings"] == 1]["runs_total"].sum()
    expected_inn2 = bbb[bbb["innings"] == 2]["runs_total"].sum()
    assert out.iloc[0]["innings_1_runs"] == expected_inn1
    assert out.iloc[0]["innings_2_runs"] == expected_inn2


def test_backfill_wickets_capped_at_ten():
    """Even if the bbb has 11+ wicket flags (data error), cap at 10."""
    match = pd.DataFrame([{"match_id": "m1",
                           "innings_1_team": None, "innings_1_runs": None,
                           "innings_1_wickets": None, "innings_1_overs": None,
                           "innings_1_extras": None,
                           "innings_2_team": None, "innings_2_runs": None,
                           "innings_2_wickets": None, "innings_2_overs": None,
                           "innings_2_extras": None}])
    rows = [("m1", 1, 0, "A", 1, 0, 1) for _ in range(15)]
    bbb = _bbb(rows)
    out = backfill_scorecard_from_bbb(match, bbb)
    assert out.iloc[0]["innings_1_wickets"] == 10


def test_backfill_does_not_overwrite_existing_values():
    """If upstream populates innings_X_runs, our backfill must not clobber it."""
    match = pd.DataFrame([{"match_id": "m1",
                           "innings_1_team": "A_existing",
                           "innings_1_runs": 999.0,
                           "innings_1_wickets": 7,
                           "innings_1_overs": 18.5,
                           "innings_1_extras": 12,
                           "innings_2_team": None, "innings_2_runs": None,
                           "innings_2_wickets": None, "innings_2_overs": None,
                           "innings_2_extras": None}])
    rows = [("m1", 1, 0, "A_bbb", 6, 0, 0) for _ in range(6)]
    bbb = _bbb(rows)
    out = backfill_scorecard_from_bbb(match, bbb)
    # Existing values should be preserved
    assert out.iloc[0]["innings_1_team"] == "A_existing"
    assert out.iloc[0]["innings_1_runs"] == 999.0
    assert out.iloc[0]["innings_1_wickets"] == 7


def test_backfill_handles_empty_bbb():
    """If bbb is empty, the matches frame is returned unchanged."""
    match = pd.DataFrame([{"match_id": "m1", "innings_1_runs": None}])
    empty_bbb = pd.DataFrame(
        columns=["match_id", "innings", "over", "batting_team",
                 "runs_total", "runs_extras", "is_wicket"]
    )
    out = backfill_scorecard_from_bbb(match, empty_bbb)
    assert out.iloc[0]["innings_1_runs"] is None or pd.isna(out.iloc[0]["innings_1_runs"])


def test_real_data_has_no_remaining_nulls():
    """End-to-end check against the real normalized parquet."""
    m = pd.read_parquet("data/normalized/matches_normalized.parquet")
    for col in [
        "innings_1_team", "innings_1_runs", "innings_1_wickets", "innings_1_overs",
        "innings_2_team", "innings_2_runs", "innings_2_wickets", "innings_2_overs",
    ]:
        assert m[col].isna().sum() == 0, f"{col} still has nulls in normalized data"
