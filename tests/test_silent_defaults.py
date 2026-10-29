"""Plan 1.3 — silent defaults killed (criteria D7).

Before this change, two layers invented numbers for missing data:

- ``compute_season_kpis`` coerced overs with ``fillna(20.0)`` and
  ``replace(0, 20.0)`` and runs with ``fillna(0)``, so a match whose
  innings summary was missing silently counted as a full 20 overs.
- The parquet transform in ``data_source`` substituted ``0`` runs and
  ``20.0`` overs for NaN innings summaries.

Missing now stays missing: rows that cannot contribute to NRR are
excluded from the NRR aggregation, counted, and surfaced through a
``data_quality`` flag on the KPI dict. Hand-checks:

- Played match 180/170 in 20/20 overs plus a match with overs_faced
  missing (runs 100/190): old code filled 20 overs and reported
  (280/40) - (360/40) = -2.0. Correct: the incomplete match is
  excluded, NRR = (180/20) - (170/20) = +0.5, flagged incomplete.
- A no-result row (0 runs, 0.0 overs) is not a 20-over innings: old
  code replaced 0 overs with 20 and dragged NRR from +0.5 to +0.25.
"""
import math

import pandas as pd
import pytest

from src.dashboard.services.metrics import compute_season_kpis, compute_team_kpis


def _row(season, runs_for, runs_against, overs_faced, overs_bowled, result="W"):
    return {
        "season": season,
        "competition_name": "NPL",
        "result": result,
        "runs_for": runs_for,
        "runs_against": runs_against,
        "overs_faced": overs_faced,
        "overs_bowled": overs_bowled,
    }


def test_missing_overs_excluded_and_flagged_not_filled_with_20() -> None:
    df = pd.DataFrame([
        _row("S1", 180, 170, 20.0, 20.0),
        _row("S1", 100, 190, None, 20.0, result="L"),
    ])
    s1 = compute_season_kpis(df)["S1"]
    assert s1["nrr"] == pytest.approx(0.5)
    assert s1["data_quality"] == "incomplete"
    assert s1["nrr_missing_rows"] == 1
    assert s1["nrr_excluded"] == 1


def test_no_result_row_does_not_drag_nrr() -> None:
    df = pd.DataFrame([
        _row("S2", 160, 150, 20.0, 20.0),
        _row("S2", 0, 0, 0.0, 0.0, result="NR"),
    ])
    s2 = compute_season_kpis(df)["S2"]
    # The NR match still counts in n / results, just not in NRR.
    assert s2["n"] == 2
    assert s2["nrr"] == pytest.approx(0.5)
    assert s2["nrr_no_innings_rows"] == 1
    assert s2["data_quality"] == "incomplete"


def test_complete_season_reports_ok_and_unchanged_nrr() -> None:
    df = pd.DataFrame([
        _row("S1", 200, 150, 20.0, 20.0),
        _row("S1", 180, 160, 20.0, 20.0),
    ])
    s1 = compute_season_kpis(df)["S1"]
    assert s1["nrr"] == pytest.approx(1.75)
    assert s1["data_quality"] == "ok"
    assert s1["nrr_excluded"] == 0


def test_all_rows_missing_gives_none_nrr_not_a_number() -> None:
    df = pd.DataFrame([_row("S1", None, None, None, None)])
    s1 = compute_season_kpis(df)["S1"]
    assert s1["nrr"] is None
    assert s1["data_quality"] == "incomplete"


def test_team_kpis_flags_incomplete_inputs() -> None:
    df = pd.DataFrame([
        _row("S1", 180, 170, 20.0, 20.0),
        _row("S1", 100, 190, None, 20.0, result="L"),
    ])
    kpis = compute_team_kpis(df)
    assert kpis["nrr"] == pytest.approx(0.5)
    assert kpis["data_quality"] == "incomplete"


def test_parquet_transform_keeps_missing_innings_missing(tmp_path, monkeypatch) -> None:
    """A matches.parquet row with NaN innings summaries must surface
    NaN runs/overs in the dashboard records, not 0 / 20.0."""
    from src.dashboard.services import data_source

    matches = pd.DataFrame([{
        "match_id": "m1",
        "season": "S2",
        "team_1_name": "Janakpur Bolts",
        "team_2_name": "Pokhara Avengers",
        "innings_1_team": None,
        "innings_1_runs": None,
        "innings_1_overs": None,
        "innings_2_team": None,
        "innings_2_runs": None,
        "innings_2_overs": None,
        "winner_name": None,
        "match_type": "League",
        "tournament_name": "NPL",
        "opposition_strength": None,
    }])
    parquet_dir = tmp_path / "parquet"
    parquet_dir.mkdir()
    matches.to_parquet(parquet_dir / "matches.parquet", index=False)
    monkeypatch.setattr(data_source, "PARQUET_DATA_PATH", str(parquet_dir))

    df = data_source._load_from_parquet()
    assert len(df) == 1
    rec = df.iloc[0]
    assert math.isnan(rec["runs_for"])
    assert math.isnan(rec["overs_faced"])
    assert math.isnan(rec["overs_bowled"])
