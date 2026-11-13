"""Dead-code cleanup, 2026-11-13 (Task 3).

Pins the removals and the two reachable-code fixes made in the same change:
- 15 files deleted: src/dashboard/components/bar_chart.py,
  src/dashboard/services/s3_recommendation.py, and 13 orphaned scripts
  under scripts/ (no caller, no test, no pipeline step, no doc references
  them; 5 of the scripts could not run at all because their inputs do not
  exist: models/s1_to_s2_model.joblib, models/s1_to_s2_lgbm.joblib,
  data/team_elo.csv, deliverables/s3_bowler_shortlist_sos.csv,
  deliverables/s3_bowler_predictions.csv).
- _hand_card removed from bowling_intelligence.py (never called; expected
  keys economy/strike_rate that _hand_split_rows never produces).
- s3_strategic_analysis.py no longer loads the batter forecast it never used.
- _generate_insights in batting_intelligence.py no longer raises IndexError
  when the S2 death or S2 powerplay row is missing from the phase export.
- The two live D:/ fallback paths (normalize_data.py, team_decline_analysis.py)
  and the stale D:/ default in src/config/paths.py docstring are gone.
"""
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]

REMOVED_FILES = [
    "src/dashboard/components/bar_chart.py",
    "src/dashboard/services/s3_recommendation.py",
    "scripts/era_split_analysis.py",
    "scripts/filter_retained.py",
    "scripts/generate_ceo_shortlist_from_filtered.py",
    "scripts/generate_s3_shortlist.py",
    "scripts/inspect_parquet.py",
    "scripts/pre_data_preflight.py",
    "scripts/predict_s3_from_s2.py",
    "scripts/predict_s3_lgbm.py",
    "scripts/recompute_shortlist_with_sos.py",
    "scripts/refresh_production_assets.py",
    "scripts/select_sos_shortlist.py",
    "scripts/train_predict_model.py",
    "scripts/rank_s3_predictions.py",
]


@pytest.mark.parametrize("rel", REMOVED_FILES)
def test_removed_dead_file_is_gone(rel):
    assert not (ROOT / rel).exists(), f"{rel} was removed as dead code"


def test_no_live_d_drive_paths():
    """The two live D:/ fallbacks and the stale paths.py docstring are gone."""
    for rel in [
        "src/preprocessing/normalize_data.py",
        "src/dashboard/page_modules/team_decline_analysis.py",
        "src/config/paths.py",
    ]:
        assert "D:/" not in (ROOT / rel).read_text(encoding="utf-8"), rel


def test_hand_card_removed_and_hand_rows_use_live_keys():
    from src.dashboard.page_modules import bowling_intelligence as bi

    assert not hasattr(bi, "_hand_card")
    # The live producer returns econ/wkts/balls, never economy/strike_rate,
    # which is why _hand_card (expecting the latter) could never have worked.
    rows = bi._hand_split_rows()
    assert rows, "hand-split rows should exist for the shipped dataset"
    assert set(rows[0]) == {"hand", "balls", "econ", "wkts"}


def test_strategic_analysis_loads_only_the_bowler_forecast():
    from src.dashboard.page_modules import s3_strategic_analysis as sa

    assert not hasattr(sa, "_load_s3_forecasts")
    forecast = sa._load_s3_bowler_forecast()
    assert forecast is not None and not forecast.empty
    assert {"phase", "s3_economy_proj"} <= set(forecast.columns)


def _phase_frame(rows):
    return pd.DataFrame(
        rows,
        columns=[
            "season",
            "phase",
            "total_runs",
            "total_balls",
            "run_rate",
            "strike_rate",
            "dot_ball_pct",
            "boundary_pct",
            "fours",
            "sixes",
            "wickets_lost",
        ],
    )


def _row(season, phase, sr, boundary=10.0, dot=50.0):
    return [season, phase, 100, 60, 10.0, sr, dot, boundary, 5, 2, 3]


def test_generate_insights_without_s2_death_row_does_not_raise():
    from src.dashboard.page_modules.batting_intelligence import _generate_insights

    df = _phase_frame(
        [
            _row("S1", "powerplay", 117.1),
            _row("S1", "middle", 120.3),
            _row("S1", "death", 125.2),
            _row("S2", "powerplay", 104.7),
            _row("S2", "middle", 112.5),
            # No S2 death row: the old code raised IndexError in the else branch.
        ]
    )
    insights = _generate_insights(df)
    assert insights["insight"] == "Batting depth concerns. No S2 death-overs data."


def test_generate_insights_without_s2_powerplay_row_does_not_raise():
    from src.dashboard.page_modules.batting_intelligence import _generate_insights

    df = _phase_frame(
        [
            _row("S1", "powerplay", 117.1),
            _row("S1", "middle", 120.3),
            _row("S1", "death", 125.2),
            # No S2 powerplay row: the old code raised IndexError evaluating
            # s2_pp['strike_rate'].values[0] inside the if condition.
            _row("S2", "middle", 112.5),
            _row("S2", "death", 133.3, boundary=14.4),
        ]
    )
    insights = _generate_insights(df)
    assert insights["insight"].startswith("Batting depth concerns. Death overs strike rate: 133.3")


def test_generate_insights_real_export_unchanged():
    """On the shipped phase export the fixed function returns the same insight."""
    from src.dashboard.page_modules.batting_intelligence import _generate_insights

    df = pd.read_csv(ROOT / "data/exports/s1_vs_s2_batting_by_phase.csv")
    insights = _generate_insights(df)
    assert insights["insight"] == (
        "Death overs remain strongest phase (SR: 133.3) with 14.4% boundary rate."
    )
