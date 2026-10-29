"""Plan 5.5 — bootstrap CIs on every quoted metric difference (V4).

The headline S2 comparisons already ship CIs in
backtest_metrics.json; the live S3 scorecard showed the four series'
log-losses side by side with no uncertainty on their difference.
The Hub now computes the champion-vs-Elo paired bootstrap over the
matches scored so far (match-level resampling, fixed seed).
"""
import numpy as np
import pandas as pd
import pytest

from src.dashboard.page_modules.season3_hub import _champion_vs_elo_ci


def _scored(n: int = 12, champ_p: float = 0.7, elo_p: float = 0.55,
            seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    y = (rng.random(n) < 0.5).astype(float)
    return pd.DataFrame({
        "team_1": ["A"] * n,
        "winner": np.where(y == 1, "A", "B"),
        "champion": champ_p, "elo": elo_p,
    })


def test_identical_series_give_zero_difference() -> None:
    df = _scored(champ_p=0.6, elo_p=0.6)
    out = _champion_vs_elo_ci(df)
    assert out is not None
    assert out["n"] == 12
    assert out["mean_diff"] == pytest.approx(0.0)
    assert out["ci_low"] <= 0.0 <= out["ci_high"]
    assert out["includes_zero"] is True


def test_better_series_has_negative_logloss_difference() -> None:
    # Champion near the outcome, Elo near the coin: on a large enough
    # scored set the CI must sit below zero.
    rng = np.random.default_rng(1)
    n = 60
    y = (rng.random(n) < 0.5).astype(float)
    df = pd.DataFrame({
        "team_1": ["A"] * n,
        "winner": np.where(y == 1, "A", "B"),
        "champion": np.where(y == 1, 0.9, 0.1),
        "elo": 0.5,
    })
    out = _champion_vs_elo_ci(df)
    assert out["mean_diff"] < 0
    assert out["ci_high"] < 0
    assert out["includes_zero"] is False


def test_no_scored_matches_returns_none() -> None:
    assert _champion_vs_elo_ci(_scored().iloc[0:0]) is None
    df = _scored()
    df["champion"] = np.nan
    assert _champion_vs_elo_ci(df) is None


def test_deterministic_for_same_inputs() -> None:
    df = _scored()
    assert _champion_vs_elo_ci(df) == _champion_vs_elo_ci(df)
