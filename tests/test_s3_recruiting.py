"""
Tests for the S3 recruiting page and its supporting deliverables.

The page itself requires Streamlit's runtime (`st.session_state`, `st.columns`,
etc.) so we don't try to fully execute `render_s3_recruiting()` here. What we
*can* test cheaply and meaningfully:

1. The module imports without error and exposes the expected helpers.
2. `_load_data()` returns a DataFrame with the columns the page reads.
3. The shortlist matrix CSV is internally consistent (units, score ranges).
4. The ridge predictions CSV satisfies its model-selection invariants
   (final == shrinkage when ridge lost CV; intervals bracket the point;
   width narrows with more balls).
5. The model comparison CSV is present and contains the expected models.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DELIV = PROJECT_ROOT / "deliverables"
SHORTLIST_CSV = DELIV / "janakpur_s3_shortlist_matrix.csv"
RIDGE_CSV = DELIV / "s3_predictions_ridge_ranked.csv"
MODEL_COMP_CSV = DELIV / "s3_model_comparison.csv"


pytestmark = pytest.mark.skipif(
    not (SHORTLIST_CSV.exists() and RIDGE_CSV.exists()),
    reason="S3 deliverable CSVs not generated; run scripts/ridge_primary_model.py "
    "and scripts/shortlist_matrix.py first.",
)


# --------------------------------------------------------------------------- #
# Module-level: import + surface
# --------------------------------------------------------------------------- #

def test_module_imports_cleanly():
    """Importing the page must not raise (catches NameError / SyntaxError)."""
    mod = importlib.import_module("src.dashboard.page_modules.s3_recruiting")
    importlib.reload(mod)
    assert callable(mod.render_s3_recruiting)
    assert callable(mod._load_data)
    assert mod.MIN_VOLUME_FOR_SHORTLIST >= 12


def test_load_data_returns_expected_columns():
    """Page reads these columns; if any go missing the page silently breaks."""
    from src.dashboard.page_modules.s3_recruiting import _load_data

    df = _load_data()
    assert df is not None and not df.empty
    expected = {
        "player_name",
        "shortlist_score",
        "shortlist_tier",
        "sos_economy",
        "dot_ball_pct",
        "death_econ_raw",
        "balls_bowled",
        "pred_s3_final",
        "pred_s3_shrinkage",
        "pred_s3_low",
        "pred_s3_high",
        "s2_balls",
        "confidence_tier",
    }
    missing = expected - set(df.columns)
    assert not missing, f"Missing expected columns: {missing}"


# --------------------------------------------------------------------------- #
# Shortlist matrix CSV invariants
# --------------------------------------------------------------------------- #

@pytest.fixture(scope="module")
def shortlist() -> pd.DataFrame:
    return pd.read_csv(SHORTLIST_CSV)


def test_shortlist_dot_ball_pct_in_percent_units(shortlist):
    """The earlier bug double-multiplied by 100 producing values in the 1000s.

    A balls-weighted dot-ball percentage must lie in [0, 100].
    """
    s = shortlist["dot_ball_pct"].dropna()
    assert s.min() >= 0
    assert s.max() <= 100, (
        "dot_ball_pct exceeds 100 — the *100 unit bug has regressed in "
        "scripts/shortlist_matrix.py"
    )


def test_shortlist_score_columns_in_0_to_10_range(shortlist):
    """Every per-criterion score column should be on a 0-10 scale post-normalisation."""
    score_cols = [c for c in shortlist.columns if c.startswith("score_")]
    assert score_cols, "No score_* columns found"
    for c in score_cols:
        s = shortlist[c].dropna()
        assert s.min() >= -1e-6, f"{c} below 0: {s.min()}"
        assert s.max() <= 10 + 1e-6, f"{c} above 10: {s.max()}"


def test_shortlist_score_is_weighted_combination_of_score_columns(shortlist):
    """`shortlist_score` should equal sum(weight * score_*); a smoke test that
    weight changes propagate end-to-end."""
    weights = {
        "score_sos_economy": 0.30,
        "score_dot_ball_pct": 0.15,
        "score_death_economy": 0.20,
        "score_balls_bowled": 0.20,
        "score_econ_trend_s1_s2": 0.05,
        "score_age_factor": 0.05,
        "score_bowling_type_fit": 0.05,
    }
    # If weights changed in the script, this test is the canary
    expected = sum(shortlist[c].fillna(0) * w for c, w in weights.items())
    assert (expected - shortlist["shortlist_score"]).abs().max() < 1e-6


def test_shortlist_tiers_are_valid_labels(shortlist):
    valid = {"TIER-1 PRIORITY", "TIER-2 CONSIDER", "TIER-3 MONITOR"}
    assert set(shortlist["shortlist_tier"].dropna().unique()).issubset(valid)


# --------------------------------------------------------------------------- #
# Ridge predictions CSV invariants
# --------------------------------------------------------------------------- #

@pytest.fixture(scope="module")
def ridge_predictions() -> pd.DataFrame:
    return pd.read_csv(RIDGE_CSV)


def test_ridge_csv_has_predictive_interval_columns(ridge_predictions):
    """The dashboard renders intervals; they must exist."""
    for col in ("pred_s3_low", "pred_s3_high", "pred_s3_shrinkage", "pred_s3_final"):
        assert col in ridge_predictions.columns, f"Missing column: {col}"


def test_predictive_intervals_bracket_point_estimate(ridge_predictions):
    """For every row with a prediction, low <= point <= high."""
    df = ridge_predictions.dropna(
        subset=["pred_s3_low", "pred_s3_high", "pred_s3_shrinkage"]
    )
    assert (df["pred_s3_low"] <= df["pred_s3_shrinkage"]).all()
    assert (df["pred_s3_shrinkage"] <= df["pred_s3_high"]).all()


def test_interval_width_narrows_with_more_balls(ridge_predictions):
    """Mean interval width should be smaller for HIGH than LOW confidence tiers.

    This is the fundamental property of a Bayesian shrinkage interval: more
    data, less prior dependence, narrower interval.
    """
    df = ridge_predictions.dropna(subset=["pred_s3_low", "pred_s3_high"])
    df = df.assign(width=df["pred_s3_high"] - df["pred_s3_low"])
    by_tier = df.groupby("confidence_tier")["width"].mean()
    assert "HIGH (≥60 balls)" in by_tier.index
    assert "LOW (12–29 balls)" in by_tier.index
    assert by_tier["HIGH (≥60 balls)"] < by_tier["LOW (12–29 balls)"], (
        f"HIGH-confidence intervals should be tighter than LOW-confidence; "
        f"got HIGH={by_tier['HIGH (≥60 balls)']:.2f}, "
        f"LOW={by_tier['LOW (12–29 balls)']:.2f}"
    )


def test_pred_s3_final_equals_shrinkage_when_ridge_loses_cv(ridge_predictions):
    """Per the methodology box: when ridge loses LOO-CV, `pred_s3_final` is
    set equal to `pred_s3_shrinkage`. Verify the invariant holds across the
    whole pool (rather than relying on the prose alone).
    """
    df = ridge_predictions.dropna(subset=["pred_s3_final", "pred_s3_shrinkage"])
    diff = (df["pred_s3_final"] - df["pred_s3_shrinkage"]).abs()
    # If ridge had won we'd assert the opposite. The model-comparison CSV
    # tells us which case we're in.
    if MODEL_COMP_CSV.exists():
        comp = pd.read_csv(MODEL_COMP_CSV).set_index("model")
        ridge_mse = comp.loc["Ridge (LOO-CV)", "loo_mse"]
        shrink_mse = comp.loc["Shrinkage estimator", "loo_mse"]
        if ridge_mse < shrink_mse:
            pytest.skip("Ridge beat shrinkage; this invariant doesn't apply")
    assert diff.max() < 1e-9, (
        f"pred_s3_final should equal pred_s3_shrinkage when ridge loses CV; "
        f"max diff = {diff.max():.6f}"
    )


def test_confidence_tiers_are_consistent_with_ball_counts(ridge_predictions):
    """Spot-check the tier labels against `s2_balls`."""
    for _, row in ridge_predictions.iterrows():
        tier = row["confidence_tier"]
        balls = row["s2_balls"]
        if tier == "HIGH (≥60 balls)":
            assert balls >= 60
        elif tier == "MEDIUM (30–59 balls)":
            assert 30 <= balls < 60
        elif tier == "LOW (12–29 balls)":
            assert 12 <= balls < 30


# --------------------------------------------------------------------------- #
# Model comparison CSV
# --------------------------------------------------------------------------- #

def test_model_comparison_csv_exists_and_has_expected_models():
    if not MODEL_COMP_CSV.exists():
        pytest.skip("Model comparison CSV not generated yet")
    comp = pd.read_csv(MODEL_COMP_CSV)
    expected_models = {
        "Naive (carry S1 forward)",
        "Regression-to-mean",
        "Shrinkage estimator",
        "Ridge (LOO-CV)",
    }
    assert expected_models.issubset(set(comp["model"]))
    # MSE is always non-negative and small enough that "the ridge MSE looks
    # plausible" is a sanity check
    assert (comp["loo_mse"] >= 0).all()
    assert (comp["loo_mse"] < 100).all()


def test_league_prior_in_model_comparison_matches_displayed_value():
    """The league prior the dashboard cites must come from the data."""
    if not MODEL_COMP_CSV.exists() or not RIDGE_CSV.exists():
        pytest.skip("Required CSVs not generated yet")
    comp = pd.read_csv(MODEL_COMP_CSV)
    ridge = pd.read_csv(RIDGE_CSV)
    cited_prior = float(comp["league_prior"].iloc[0])
    # Sanity: cited prior should be within a couple of runs of the mean
    # shrinkage prediction, since the latter is reliability-weighted blends
    # toward the former.
    if "pred_s3_shrinkage" in ridge.columns:
        mean_pred = ridge["pred_s3_shrinkage"].dropna().mean()
        assert abs(cited_prior - mean_pred) < 1.5, (
            f"League prior in model comparison ({cited_prior}) is too far from "
            f"the mean shrinkage prediction ({mean_pred})"
        )
