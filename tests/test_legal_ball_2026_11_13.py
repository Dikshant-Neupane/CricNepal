"""Pin: the 2026-11-13 legal-ball economy switch.

The forecaster and the roster scorecard used to drop wide/no-ball
rows entirely, so wide/no-ball RUNS never counted against the bowler
(priors 6.56 / 6.81 / 8.79). The legal-ball definition counts those
runs but not the delivery:

    bowler runs = runs_off_bat + runs_extras, except byes/legbyes
                  deliveries where bowler runs = runs_off_bat only
    economy     = bowler runs / legal balls * 6

Priors are now 6.73 / 6.92 / 8.89 (pinned independently by the A8
test in tests/test_audit_2026_11_12.py, which recomputes them from
the shipped data). This file pins the behaviour that test cannot:
the phase function on extras, the roster rewrite, the Khatri grade
move, and the shipped phase export reproducing from the function.
"""

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.analytics.s3_performance_forecaster import (
    PHASE_PRIORS,
    forecast_bowlers_phase_aware,
)

ROOT = Path(__file__).resolve().parent.parent


def _extras_frame() -> tuple[pd.DataFrame, pd.DataFrame]:
    """One bowler, one phase-season, with every extras kind.

    5 legal balls, 1 run off the bat each (5 bowler runs); 1 bye
    delivery, 4 bye runs off the bat 0 (legal ball, 0 bowler runs);
    1 wide, 1 run (not a ball, 1 bowler run); 1 no-ball, 1 run off
    the bat + 1 penalty run (not a ball, 2 bowler runs).
    Legal balls 6, bowler runs 8 -> economy 8.00.
    The old dropped-rows definition would have read 9 runs off 6
    legal balls -> 9.00 (bye runs counted, wide/no-ball runs lost).
    """
    rows = []
    for i in range(5):
        rows.append({
            "match_id": "M1", "bowler_name": "Bowler X", "phase": "Death",
            "runs_off_bat": 1, "runs_extras": 0,
            "runs_total": 1, "extras_type": np.nan,
        })
    rows.append({
        "match_id": "M1", "bowler_name": "Bowler X", "phase": "Death",
        "runs_off_bat": 0, "runs_extras": 4,
        "runs_total": 4, "extras_type": "byes",
    })
    rows.append({
        "match_id": "M1", "bowler_name": "Bowler X", "phase": "Death",
        "runs_off_bat": 0, "runs_extras": 1,
        "runs_total": 1, "extras_type": "wides",
    })
    rows.append({
        "match_id": "M1", "bowler_name": "Bowler X", "phase": "Death",
        "runs_off_bat": 1, "runs_extras": 1,
        "runs_total": 2, "extras_type": "noballs",
    })
    bbb = pd.DataFrame(rows)
    matches = pd.DataFrame({"match_id": ["M1"], "season": ["S1"]})
    return bbb, matches


def test_phase_function_counts_extras_as_legal_ball():
    bbb, matches = _extras_frame()
    result = forecast_bowlers_phase_aware(bbb, matches)
    assert len(result) == 1
    row = result.iloc[0]
    assert int(row["s1_balls"]) == 6  # bye is legal; wide/no-ball are not
    assert row["s1_economy_raw"] == pytest.approx(8.00)
    # shrunk toward the Death prior 8.89 with k=60, 6 balls:
    # w = 6/66 -> 8.00 * 6/66 + 8.89 * 60/66 = 8.81
    assert row["s1_economy_shrunk"] == pytest.approx(8.81, abs=0.01)


def test_phase_function_zero_legal_balls_carries_no_evidence():
    """A phase-season of only wides has balls 0 and NaN economy, and
    does not blend the prior into the projection as if it were data."""
    rows = [{
        "match_id": "M1", "bowler_name": "Wide Only", "phase": "Middle",
        "runs_off_bat": 0, "runs_extras": 1,
        "runs_total": 1, "extras_type": "wides",
    }]
    bbb = pd.DataFrame(rows)
    matches = pd.DataFrame({"match_id": ["M1"], "season": ["S1"]})
    result = forecast_bowlers_phase_aware(bbb, matches)
    row = result.iloc[0]
    assert int(row["s1_balls"]) == 0
    assert pd.isna(row["s1_economy_raw"])
    assert pd.isna(row["s1_economy_shrunk"])
    assert row["s3_economy_proj"] == PHASE_PRIORS["Middle"]


def _legal_ball_economies() -> pd.DataFrame:
    bbb = pd.read_parquet(ROOT / "data/final/parquet/ball_by_ball.parquet")
    matches = pd.read_parquet(ROOT / "data/final/parquet/matches.parquet")[
        ["match_id", "season"]]
    b = bbb.merge(matches, on="match_id", how="left")
    b = b[b["season"].isin(["S1", "S2"])].copy()
    b["is_legal"] = ~b["extras_type"].isin(["wides", "noballs"])
    b["bowl_runs"] = b["runs_off_bat"] + b["runs_extras"]
    byes = b["extras_type"].isin(["byes", "legbyes"])
    b.loc[byes, "bowl_runs"] = b.loc[byes, "runs_off_bat"]
    agg = (
        b.groupby(["bowler_name", "season"])
        .agg(legal_balls=("is_legal", "sum"), bowl_runs=("bowl_runs", "sum"))
        .reset_index()
    )
    agg["economy"] = agg["bowl_runs"] / agg["legal_balls"] * 6
    return agg


def test_roster_economies_are_legal_ball():
    """Every roster bowling row's economy_rate must equal the
    legal-ball economy recomputed from the shipped ball-by-ball
    data (179 rows; DJ Malan S2 bowled 3 legal balls in the data but
    is listed as a Batter with 0 balls in the roster, so he has no
    bowling row and is excluded here)."""
    agg = _legal_ball_economies()
    for path in (
        ROOT / "data/player_rosters/npl_player_rosters_20260521.csv",
        ROOT / "data/player_rosters/npl_player_rosters_canonical.csv",
    ):
        roster = pd.read_csv(path)
        roster["season_key"] = roster["season"].str.replace("Season ", "S")
        bowlers = roster[roster["balls_bowled"] > 0]
        merged = bowlers.merge(
            agg, left_on=["player_name", "season_key"],
            right_on=["bowler_name", "season"], how="left",
        )
        assert merged["economy"].notna().all(), f"{path.name}: unmatched rows"
        assert np.allclose(
            merged["economy_rate"], merged["economy"], rtol=0, atol=0.011
        ), f"{path.name}: economy_rate is not the legal-ball economy"
        # internally consistent: economy == runs / balls * 6
        assert np.allclose(
            merged["economy_rate"],
            (merged["runs_conceded"] / merged["balls_bowled"] * 6).round(2),
            rtol=0, atol=0.001,
        ), f"{path.name}: economy_rate != runs_conceded / balls_bowled * 6"


def test_khatri_grade_moved_to_a_b():
    """The audit predicted this move: Bipin Khatri's S2 economy
    6.22 -> 6.63 under the legal-ball definition drops his S3
    composite 70.8 -> 64.8, priority 9 -> 8, Grade A -> Grade A/B."""
    roster = pd.read_csv(
        ROOT / "data/player_rosters/npl_player_rosters_20260521.csv")
    khatri = roster[roster["player_name"] == "Bipin Khatri"]
    s2 = khatri[khatri["season"] == "Season 2"].iloc[0]
    assert s2["economy_rate"] == pytest.approx(6.63)
    assert int(s2["balls_bowled"]) == 104  # legal balls, was 111
    forecast = pd.read_csv(ROOT / "data/exports/s3_bowler_forecast.csv")
    row = forecast[forecast["player_name"] == "Bipin Khatri"].iloc[0]
    assert row["npl_grade"] == "Grade A/B"
    assert int(row["priority"]) == 8
    assert row["s3_composite_score"] == pytest.approx(64.8)


def test_phase_export_reproduces_from_function():
    """The shipped phase export must be what the pinned regenerator
    produces (function rows minus the S3-only export restriction)."""
    bbb = pd.read_parquet(ROOT / "data/final/parquet/ball_by_ball.parquet")
    matches = pd.read_parquet(ROOT / "data/final/parquet/matches.parquet")
    out = forecast_bowlers_phase_aware(bbb, matches, k=60)
    out = out.sort_values(["bowler_name", "phase"]).reset_index(drop=True)
    path = ROOT / "scripts" / "regenerate_s3_bowler_forecast.py"
    spec = importlib.util.spec_from_file_location("regen_phase", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    export = module.restrict_export(out)
    shipped = pd.read_csv(
        ROOT / "data/exports/s3_phase_bowler_forecast.csv")
    assert list(export.columns) == list(shipped.columns)
    assert len(export) == len(shipped) == 311
    for col in export.columns:
        a, b = export[col], shipped[col]
        if pd.api.types.is_numeric_dtype(a) and pd.api.types.is_numeric_dtype(b):
            assert np.allclose(
                a.to_numpy(dtype=float), b.to_numpy(dtype=float),
                rtol=0, atol=1e-9, equal_nan=True,
            ), f"col {col}: mismatch"
        else:
            assert list(a) == list(b), f"col {col}: mismatch"
