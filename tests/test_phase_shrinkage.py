"""
Tests for phase-aware shrinkage in s3_performance_forecaster.py.
"""

import pytest
import pandas as pd
import numpy as np

from src.analytics.s3_performance_forecaster import (
    shrink_to_phase_prior,
    forecast_bowlers_phase_aware,
    PHASE_PRIORS,
)


class TestShrinkToPhasePrior:
    """Unit tests for the James-Stein style shrinkage function."""

    def test_zero_balls_returns_prior(self):
        """With zero balls the estimate should collapse to the phase prior."""
        result = shrink_to_phase_prior(5.0, 0, "Death")
        assert result == PHASE_PRIORS["Death"]

    def test_nan_economy_returns_prior(self):
        result = shrink_to_phase_prior(np.nan, 30, "Middle")
        assert result == PHASE_PRIORS["Middle"]

    def test_large_sample_favours_observed(self):
        """With very many balls the shrunk value should approach the observed."""
        result = shrink_to_phase_prior(5.0, 600, "Powerplay", k=60)
        # w = 600 / (600 + 60) = 0.909 → shrunk ≈ 5.0 * 0.909 + 6.56 * 0.091 ≈ 5.15
        assert abs(result - 5.0) < 0.5

    def test_small_sample_favours_prior(self):
        """With very few balls the shrunk value should be close to the prior."""
        result = shrink_to_phase_prior(5.0, 6, "Powerplay", k=60)
        # w = 6 / (6 + 60) = 0.09 → shrunk ≈ 5.0 * 0.09 + 6.56 * 0.91 ≈ 6.42
        assert abs(result - PHASE_PRIORS["Powerplay"]) < 1.0

    def test_unknown_phase_uses_global_fallback(self):
        """Unknown phases should fall back to the 8.30 global prior."""
        result = shrink_to_phase_prior(np.nan, 0, "Unknown")
        assert result == 8.30

    def test_exact_formula(self):
        """Verify the exact shrinkage formula: w * obs + (1 - w) * prior."""
        obs, balls, k = 10.0, 30, 60
        phase = "Death"
        prior = PHASE_PRIORS[phase]
        w = balls / (balls + k)
        expected = round(w * obs + (1 - w) * prior, 2)
        result = shrink_to_phase_prior(obs, balls, phase, k=k)
        assert result == expected


class TestForecastBowlersPhaseAware:
    """Integration tests for the full phase-aware forecasting pipeline."""

    @pytest.fixture
    def mini_bbb(self):
        """Minimal ball-by-ball data for two bowlers across two seasons."""
        rows = []
        # Bowler A: 30 powerplay balls in S1 (econ ~6.0), 30 in S2 (econ ~7.0)
        for i in range(30):
            rows.append({
                "match_id": "M1",
                "innings": 1,
                "over": i // 6,
                "ball": (i % 6) + 1,
                "bowler_name": "Bowler A",
                "batter_name": "Bat X",
                "batting_team": "Opp",
                "bowling_team": "JAB",
                "runs_total": 1,  # 30 runs off 30 balls = 6.0 econ
                "is_wicket": 0,
                "phase": "Powerplay",
            })
        for i in range(30):
            rows.append({
                "match_id": "M3",
                "innings": 1,
                "over": i // 6,
                "ball": (i % 6) + 1,
                "bowler_name": "Bowler A",
                "batter_name": "Bat Y",
                "batting_team": "Opp",
                "bowling_team": "JAB",
                "runs_total": 1 if i < 25 else 2,  # ~7.0 econ
                "is_wicket": 0,
                "phase": "Powerplay",
            })
        return pd.DataFrame(rows)

    @pytest.fixture
    def mini_matches(self):
        return pd.DataFrame({
            "match_id": ["M1", "M3"],
            "season": ["S1", "S2"],
        })

    def test_returns_dataframe(self, mini_bbb, mini_matches):
        result = forecast_bowlers_phase_aware(mini_bbb, mini_matches)
        assert isinstance(result, pd.DataFrame)

    def test_has_required_columns(self, mini_bbb, mini_matches):
        result = forecast_bowlers_phase_aware(mini_bbb, mini_matches)
        required = [
            "bowler_name", "phase", "s1_balls", "s1_economy_raw",
            "s1_economy_shrunk", "s2_balls", "s2_economy_raw",
            "s2_economy_shrunk", "s3_economy_proj", "specialist_flag",
        ]
        for col in required:
            assert col in result.columns, f"Missing column: {col}"

    def test_balls_columns_are_legal_ball_counts(self, mini_bbb, mini_matches):
        """s1_balls / s2_balls must be present and count legal balls.

        The dashboard (s3_strategic_analysis.py) requires s2_balls and
        skips the S3 bowling section with a warning without it, so a
        regeneration from this function must carry both columns.
        Bowler A bowled 30 balls in each season in the fixture.
        """
        result = forecast_bowlers_phase_aware(mini_bbb, mini_matches)
        assert len(result) == 1
        row = result.iloc[0]
        assert int(row["s1_balls"]) == 30
        assert int(row["s2_balls"]) == 30

    def test_specialist_flag_values(self, mini_bbb, mini_matches):
        result = forecast_bowlers_phase_aware(mini_bbb, mini_matches)
        valid_flags = {"SPECIALIST", "LIABILITY", "AVERAGE"}
        assert set(result["specialist_flag"].unique()).issubset(valid_flags)

    def test_shrunk_values_between_raw_and_prior(self, mini_bbb, mini_matches):
        """Shrunk economy should lie between the raw value and the phase prior."""
        result = forecast_bowlers_phase_aware(mini_bbb, mini_matches)
        for _, row in result.iterrows():
            prior = PHASE_PRIORS.get(row["phase"], 8.30)
            raw = row["s2_economy_raw"]
            shrunk = row["s2_economy_shrunk"]
            if pd.notna(raw):
                lo = min(raw, prior)
                hi = max(raw, prior)
                assert lo - 0.01 <= shrunk <= hi + 0.01, (
                    f"Shrunk {shrunk} not between raw {raw} and prior {prior}"
                )

    def test_function_still_returns_s3_only_rows(self, mini_bbb, mini_matches):
        """The core function returns ALL rows, including S3-only bowlers.

        The export restriction lives in the generation script, not
        here: a bowler who only appears in S3 gets a prior-only
        projection (s1_balls == s2_balls == 0) from the function,
        and the script drops that row from the shipped export.
        """
        rows = mini_bbb.to_dict("records")
        for i in range(12):
            rows.append({
                "match_id": "M5",
                "innings": 1,
                "over": i // 6,
                "ball": (i % 6) + 1,
                "bowler_name": "Bowler S3-only",
                "batter_name": "Bat Z",
                "batting_team": "Opp",
                "bowling_team": "JAB",
                "runs_total": 1,
                "is_wicket": 0,
                "phase": "Death",
            })
        bbb = pd.DataFrame(rows)
        matches = pd.DataFrame({
            "match_id": ["M1", "M3", "M5"],
            "season": ["S1", "S2", "S3"],
        })
        result = forecast_bowlers_phase_aware(bbb, matches)
        s3_only = result[(result["bowler_name"] == "Bowler S3-only")]
        assert len(s3_only) == 1
        row = s3_only.iloc[0]
        assert int(row["s1_balls"]) == 0
        assert int(row["s2_balls"]) == 0
        assert row["s3_economy_proj"] == PHASE_PRIORS["Death"]


class TestExportRestriction:
    """The shipped export excludes S3-only bowlers (script-level filter)."""

    @staticmethod
    def _load_script():
        import importlib.util
        from pathlib import Path

        path = Path(__file__).resolve().parent.parent / "scripts" / "regenerate_s3_bowler_forecast.py"
        spec = importlib.util.spec_from_file_location("regen_s3_bowler_forecast", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_restrict_export_drops_s3_only_rows(self):
        """A row with s1_balls == s2_balls == 0 is dropped; history rows kept."""
        frame = pd.DataFrame([
            {"bowler_name": "Has S1", "phase": "Death", "s1_balls": 30, "s2_balls": 0},
            {"bowler_name": "Has S2", "phase": "Middle", "s1_balls": 0, "s2_balls": 55},
            {"bowler_name": "S3 only", "phase": "Middle", "s1_balls": 0, "s2_balls": 0},
            {"bowler_name": "S3 only", "phase": "Death", "s1_balls": 0, "s2_balls": 0},
        ])
        module = self._load_script()
        export = module.restrict_export(frame)
        assert len(export) == 2
        assert set(export["bowler_name"]) == {"Has S1", "Has S2"}
        assert ((export["s1_balls"] == 0) & (export["s2_balls"] == 0)).sum() == 0

    def test_export_count_is_function_rows_minus_s3_only(self):
        """Export rows == function rows minus S3-only rows, on a small frame."""
        frame = pd.DataFrame([
            {"bowler_name": f"B{i}", "phase": "Death", "s1_balls": 10, "s2_balls": 10}
            for i in range(5)
        ] + [
            {"bowler_name": f"S{i}", "phase": "Middle", "s1_balls": 0, "s2_balls": 0}
            for i in range(3)
        ])
        module = self._load_script()
        export = module.restrict_export(frame)
        n_s3_only = int(((frame["s1_balls"] == 0) & (frame["s2_balls"] == 0)).sum())
        assert len(export) == len(frame) - n_s3_only == 5
