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
        # w = 600 / (600 + 60) = 0.909 → shrunk ≈ 5.0 * 0.909 + 6.65 * 0.091 ≈ 5.15
        assert abs(result - 5.0) < 0.5

    def test_small_sample_favours_prior(self):
        """With very few balls the shrunk value should be close to the prior."""
        result = shrink_to_phase_prior(5.0, 6, "Powerplay", k=60)
        # w = 6 / (6 + 60) = 0.09 → shrunk ≈ 5.0 * 0.09 + 6.65 * 0.91 ≈ 6.50
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
            "bowler_name", "phase", "s1_economy_raw", "s2_economy_raw",
            "s1_economy_shrunk", "s2_economy_shrunk", "s3_economy_proj",
            "specialist_flag",
        ]
        for col in required:
            assert col in result.columns, f"Missing column: {col}"

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
