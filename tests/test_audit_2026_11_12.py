"""Tests for the 2026-11-12 CricNepal audit fixes.

Each test fails on the pre-audit code and passes after the fix.
Audit evidence: docs/AUDIT_2026_11_12.md,
data/predictions/model_comparison_audit.json.

  A1  ridge _season_agg excludes the middle overs (46% of balls) from
      the "overall economy" target.
  A2  ridge build_paired_dataset carries a leaky column: s1_econ_trend
      is built from the S2 target (r2 - r1).
  A3  ridge S3 feature mapping sends s1_economy / s1_sos_econ / s1_balls
      to 0.0 (the S2 aggregate frame has raw_economy / sos_adj_economy /
      total_balls, not s2_economy / s2_sos_econ / s2_balls).
  A4  ridge baselines use the S2 (target-season) league mean.
  A5  prepare_season_features aggregates only powerplay + death.
  A6  prepare_season_features fills a missing phase economy with 0.0.
  A7  build_tu_par_tables.load() crashes on a fresh clone: the
      normalized ball-by-ball file is not in the repo.
  A8  PHASE_PRIORS (6.87 / 7.02 / 9.12) do not reproduce from the
      shipped S1+S2 ball-by-ball data under the stated definition.
  A9  train_model_lgbm tunes 7 hyperparameters on n~37 and cannot
      even be imported (lightgbm is not installed).
  A10 coin_baseline_metrics hardcodes an S2-specific note.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts import build_tu_par_tables as tu  # noqa: E402
from scripts import prepare_season_features as psf  # noqa: E402
from scripts import ridge_primary_model as rpm  # noqa: E402
from src.analytics.s3_performance_forecaster import PHASE_PRIORS  # noqa: E402
from src.prediction.metrics import coin_baseline_metrics  # noqa: E402


# ---------------------------------------------------------------- A1
def test_ridge_season_agg_includes_middle_overs():
    """total_balls and raw economy must cover all three phases."""
    g = pd.DataFrame([{
        "powerplay_balls": 60, "powerplay_econ": 6.0, "powerplay_dot_pct": 40.0,
        "middle_balls": 60, "middle_econ": 7.0, "middle_dot_pct": 35.0,
        "death_balls": 60, "death_econ": 9.0, "death_dot_pct": 30.0,
    }])
    out = rpm._season_agg(g)
    assert int(out["total_balls"]) == 180
    # (6*60 + 7*60 + 9*60) / 180 = 7.333...
    assert float(out["raw_economy"]) == pytest.approx(22.0 / 3.0, abs=1e-6)
    assert float(out["middle_econ"]) == pytest.approx(7.0)
    assert int(out["middle_balls"]) == 60


# ---------------------------------------------------------------- A2
def _agg_frame():
    rows = []
    for season, raw, pp, mid, dth in (
            (1, 7.5, 6.5, 7.0, 9.0), (2, 7.0, 6.0, 7.0, 8.5)):
        rows.append({"player_name": "Bowler A", "season_norm": season,
                     "total_balls": 120, "raw_economy": raw,
                     "sos_adj_economy": raw,
                     "pp_econ": pp, "pp_balls": 40, "pp_dot_pct": 40.0,
                     "middle_econ": mid, "middle_balls": 40,
                     "middle_dot_pct": 35.0,
                     "death_econ": dth, "death_balls": 40,
                     "death_dot_pct": 30.0})
    return pd.DataFrame(rows)


def test_ridge_paired_dataset_has_no_leaky_column():
    paired = rpm.build_paired_dataset(_agg_frame())
    assert len(paired) == 1
    assert "s1_econ_trend" not in paired.columns


# ---------------------------------------------------------------- A3
def test_ridge_s3_feature_mapping_uses_real_s2_columns():
    """The S2 aggregate frame's columns are raw_economy /
    sos_adj_economy / total_balls; the mapping must read those, not
    the non-existent s2_economy / s2_sos_econ / s2_balls."""
    row = pd.Series({
        "total_balls": 100, "raw_economy": 7.0, "sos_adj_economy": 7.1,
        "pp_econ": 6.5, "pp_balls": 60, "pp_dot_pct": 40.0,
        "middle_econ": 7.0, "middle_balls": 50, "middle_dot_pct": 35.0,
        "death_econ": 9.0, "death_balls": 40, "death_dot_pct": 30.0,
    })
    feat_cols = ["s1_economy", "s1_sos_econ", "s1_balls",
                 "s1_pp_econ", "s1_pp_balls", "s1_pp_dot_pct",
                 "s1_middle_econ", "s1_middle_balls", "s1_middle_dot_pct",
                 "s1_death_econ", "s1_death_balls", "s1_death_dot_pct"]
    fv = rpm.s2_feature_vector(row, feat_cols)
    assert fv["s1_economy"] == pytest.approx(7.0)
    assert fv["s1_sos_econ"] == pytest.approx(7.1)
    assert fv["s1_balls"] == pytest.approx(100.0)
    assert fv["s1_pp_econ"] == pytest.approx(6.5)
    assert fv["s1_middle_econ"] == pytest.approx(7.0)
    assert fv["s1_death_econ"] == pytest.approx(9.0)


# ---------------------------------------------------------------- A4
def test_ridge_baselines_use_prior_season_league_mean():
    """Baselines predicting S2 from S1 must be centred on the S1
    league mean, never the S2 (target-season) mean."""
    paired = pd.DataFrame({
        "s1_economy": [6.0, 8.0], "s1_balls": [60, 60],
        "s2_economy": [6.5, 7.5],
    })
    # Constructed case: with the prior-season mean 7.0, RTM predicts
    # [6.5, 7.5], exactly the S2 values, so MSE is 0.
    bl = rpm.compute_baselines(paired, league_avg=7.0)
    assert bl["rtm_mse"] == pytest.approx(0.0)
    # and the helper that main() uses must pick the S1 mean:
    assert rpm.prior_season_league_mean(_agg_frame(), season_norm=1) == pytest.approx(7.5)
    assert rpm.prior_season_league_mean(_agg_frame(), season_norm=2) == pytest.approx(7.0)


# ---------------------------------------------------------------- A5 + A6
def _mini_bbb():
    rows = []

    def ball(phase, bowler, runs_off_bat, runs_extras=0, extras_type=np.nan):
        rows.append({"match_id": "M1", "ball": 1, "phase": phase,
                     "bowler_name": bowler,
                     "runs_total": runs_off_bat + runs_extras,
                     "runs_off_bat": runs_off_bat,
                     "runs_extras": runs_extras,
                     "extras_type": extras_type, "is_dot_ball": 0,
                     "is_wicket": 0})

    # Bowler A, Powerplay: 6 legal balls, 1 run each -> econ 6.0.
    # Plus 1 wide (+1 run): not a legal ball, but the run IS conceded
    # by the bowler, so it counts in the numerator: 7 runs / 6 balls.
    for _ in range(6):
        ball("Powerplay", "Bowler A", 1)
    ball("Powerplay", "Bowler A", 0, runs_extras=1, extras_type="wides")
    # Bowler A, Middle: 6 legal balls, bat runs 1,1,1,1,1,2 = 7 runs.
    # Plus 1 bye ball: legal (counts as a ball) but 0 bowler runs,
    # so middle = 7 legal balls, 7 bowler runs -> econ 6.0.
    for r in [1, 1, 1, 1, 1, 2]:
        ball("Middle", "Bowler A", r)
    ball("Middle", "Bowler A", 0, runs_extras=1, extras_type="byes")
    # Bowler A, Death: 6 legal balls, runs 1,1,1,1,1,4 = 9 -> econ 9.0.
    for r in [1, 1, 1, 1, 1, 4]:
        ball("Death", "Bowler A", r)
    # Bowler B: powerplay only, never bowled death.
    for _ in range(12):
        ball("Powerplay", "Bowler B", 1)
    return pd.DataFrame(rows)


def test_prepare_season_features_includes_middle_and_legal_balls(tmp_path):
    bbb_path = tmp_path / "bbb.parquet"
    m_path = tmp_path / "matches.parquet"
    out_path = tmp_path / "out.csv"
    _mini_bbb().to_parquet(bbb_path, index=False)
    pd.DataFrame([{"match_id": "M1", "season": "S1"}]).to_parquet(m_path, index=False)
    psf.prepare(str(bbb_path), str(m_path), str(out_path))
    out = pd.read_csv(out_path)
    assert {"middle_econ", "middle_balls", "middle_dot_pct"} <= set(out.columns)
    a = out[out["bowler"] == "Bowler A"].iloc[0]
    # Legal balls only in the denominator; wide/no-ball runs DO count
    # in the numerator (the bowler concedes them), bye runs do not.
    # Powerplay: 6 legal balls, 6 bat runs + 1 wide run = 7 runs -> 7.0.
    assert int(a["powerplay_balls"]) == 6
    assert float(a["powerplay_econ"]) == pytest.approx(7.0)
    # Middle: 7 legal balls (incl. the bye ball), 7 bowler runs -> 6.0.
    assert int(a["middle_balls"]) == 7
    assert float(a["middle_econ"]) == pytest.approx(6.0)
    assert int(a["death_balls"]) == 6
    assert float(a["death_econ"]) == pytest.approx(9.0)
    b = out[out["bowler"] == "Bowler B"].iloc[0]
    # no death balls -> NaN, never 0.0 (0.0 would read as a perfect economy)
    assert pd.isna(b["death_econ"])


def test_prepare_season_features_falls_back_to_final_parquet(tmp_path, monkeypatch):
    """On a fresh clone the normalized ball-by-ball file is absent;
    the resolver must fall back to the shipped final parquet."""
    monkeypatch.setattr(psf, "ROOT", tmp_path)
    (tmp_path / "data" / "final" / "parquet").mkdir(parents=True)
    (tmp_path / "data" / "normalized").mkdir(parents=True)
    final = ROOT / "data" / "final" / "parquet" / "ball_by_ball.parquet"
    (tmp_path / "data" / "final" / "parquet" / "ball_by_ball.parquet"
     ).write_bytes(final.read_bytes())
    assert psf.resolve_ball_parquet() == (
        tmp_path / "data" / "final" / "parquet" / "ball_by_ball.parquet")


# ---------------------------------------------------------------- A7
def test_tu_par_tables_load_falls_back_to_final_parquet(tmp_path, monkeypatch):
    """load() must work on a fresh clone, where only the final
    parquet (not the normalized ball-by-ball file) is shipped."""
    monkeypatch.setattr(tu, "ROOT", tmp_path)
    (tmp_path / "data" / "final" / "parquet").mkdir(parents=True)
    (tmp_path / "data" / "normalized").mkdir(parents=True)
    for src, dst in [
            ("data/final/parquet/ball_by_ball.parquet",
             "data/final/parquet/ball_by_ball.parquet"),
            ("data/normalized/matches_normalized.parquet",
             "data/normalized/matches_normalized.parquet")]:
        (tmp_path / dst).write_bytes((ROOT / src).read_bytes())
    matches, bbb = tu.load()
    assert len(matches) == 76
    assert len(bbb) > 0
    assert {"season", "slot"} <= set(bbb.columns)


# ---------------------------------------------------------------- A8
def test_phase_priors_match_shipped_s1_s2_data():
    """PHASE_PRIORS must reproduce from the shipped S1+S2
    ball-by-ball data under the legal-ball definition (switched
    2026-11-13 from the old dropped-rows definition): bowler runs =
    runs_off_bat + runs_extras, except byes/legbyes deliveries where
    bowler runs = runs_off_bat only, over legal balls only."""
    bbb = pd.read_parquet(ROOT / "data/final/parquet/ball_by_ball.parquet")
    matches = pd.read_parquet(ROOT / "data/final/parquet/matches.parquet")[
        ["match_id", "season"]]
    b = bbb.merge(matches, on="match_id", how="left")
    s12 = b[b["season"].isin(["S1", "S2"])].copy()
    s12["is_legal"] = ~s12["extras_type"].isin(["wides", "noballs"])
    s12["bowl_runs"] = s12["runs_off_bat"] + s12["runs_extras"]
    byes = s12["extras_type"].isin(["byes", "legbyes"])
    s12.loc[byes, "bowl_runs"] = s12.loc[byes, "runs_off_bat"]
    for phase, g in s12.groupby("phase"):
        recomputed = float(g["bowl_runs"].sum() / g["is_legal"].sum() * 6)
        assert PHASE_PRIORS[phase] == pytest.approx(recomputed, abs=0.05)


# ---------------------------------------------------------------- A9
def test_lgbm_refuses_tiny_n(tmp_path, monkeypatch, capsys):
    """At n < 100 a 7-hyperparameter GBM search is not a verifiable
    predictor; the script must refuse and point at Ridge."""
    import scripts.train_model_lgbm as lgbm
    monkeypatch.setattr(lgbm, "DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setattr(lgbm, "MODELS_DIR", str(tmp_path / "models"))
    monkeypatch.setattr(lgbm, "DELIVERABLES", str(tmp_path / "deliverables"))
    (tmp_path / "data").mkdir()
    rows = [{"player_name": f"P{i}", "s1_economy": 7.0 + i * 0.1,
             "s2_economy": 7.0 + i * 0.05} for i in range(20)]
    pd.DataFrame(rows).to_csv(
        tmp_path / "data" / "extended_per_bowler_features.csv", index=False)
    lgbm.main()
    out = capsys.readouterr().out
    assert "100" in out and "ridge_primary_model" in out
    assert not list((tmp_path / "models").glob("*.joblib"))


# ---------------------------------------------------------------- A10
def test_coin_note_has_no_hardcoded_season():
    note = coin_baseline_metrics(12)["accuracy_note"]
    assert "S2" not in note
    assert "0.34375" not in note
