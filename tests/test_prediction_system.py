"""Tests for the pre-match prediction system (src/prediction/*)."""
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.prediction import elo as E  # noqa: E402
from src.prediction import engine, model as M, simulator as S  # noqa: E402

PRED = ROOT / "data" / "predictions"


# ---------- fixtures ----------
@pytest.fixture(scope="module")
def fixtures():
    return pd.read_csv(ROOT / "data/fixtures/s3_fixtures.csv")


def test_fixtures_integrity(fixtures):
    assert len(fixtures) == 32
    league = fixtures[fixtures.stage == "League"]
    assert len(league) == 28
    pairs = [tuple(sorted([a, b])) for a, b in zip(league.team_1_name, league.team_2_name)]
    assert len(set(pairs)) == 28  # single round-robin: every pair once
    counts = pd.Series(pairs).explode().value_counts()
    assert (counts == 7).all() and len(counts) == 8
    d = pd.to_datetime(fixtures.match_date)
    assert d.min() >= pd.Timestamp("2026-10-26") and d.max() <= pd.Timestamp("2026-11-21")
    m3 = fixtures[fixtures.match_number == 3].iloc[0]
    assert {m3.team_1_name, m3.team_2_name} == {"Janakpur Bolts", "Karnali Yaks"}
    assert m3.match_date == "2026-10-27"
    playoffs = fixtures[fixtures.stage != "League"]
    assert len(playoffs) == 4 and playoffs.team_1_name.isna().all()


# ---------- player master + priors ----------
def test_player_master():
    m = pd.read_csv(PRED / "player_master.csv")
    assert len(m) == 133 and m.player_key.is_unique
    assert m.groupby("team").size().to_dict() == {
        "Biratnagar Kings": 18, "Chitwan Rhinos": 16, "Janakpur Bolts": 17,
        "Karnali Yaks": 16, "Kathmandu Gorkhas": 17, "Lumbini Lions": 16,
        "Pokhara Avengers": 17, "Sudurpaschim Royals": 16}
    assert set(m.role) <= {"Batter", "Bowler", "All-rounder", "Wicketkeeper"}
    # unsourced fields are null, never invented
    assert m[m.cricsheet_registry_id.isna()]["missing_fields"].str.contains(
        "cricsheet_registry_id").all()


def test_player_priors():
    p = pd.read_csv(PRED / "player_priors.csv")
    assert len(p) == 133
    assert (p.bat_index > 0).all() and (p.prior_bowl_econ > 0).all()
    deb = p[p.prior_group == "debutant"]
    assert len(deb) > 0 and np.allclose(deb.bat_index, 1.0)  # league-mean prior
    assert set(p.prior_group) <= {"npl_experienced", "external_pro", "debutant"}
    ext = p[p.prior_group == "external_pro"]
    assert (deb.uncertainty == 1.5).all()  # widest: no data, 1.5x widening
    assert (ext.uncertainty > 0).all()


# ---------- canonical Elo ----------
@pytest.fixture(scope="module")
def matches():
    return pd.read_parquet(ROOT / "data/normalized/matches_normalized.parquet")


def test_elo_properties(matches):
    assert E.expected(1500, 1500) == 0.5
    assert E.expected(1900, 1500) == pytest.approx(10 / 11)
    assert E.expected(1600, 1500) + E.expected(1500, 1600) == pytest.approx(1.0)
    hist = E.compute_history(matches)
    assert len(hist) == 64 and hist.match_id.notna().all() and hist.season.notna().all()
    # zero-sum updates (same MOV multiplier for both teams)
    delta = (hist.team_1_post - hist.team_1_pre) + (hist.team_2_post - hist.team_2_pre)
    assert np.allclose(delta, 0.0, atol=1e-9)
    reg = E.regress({"A": 1700.0, "B": 1300.0}, 0.4)
    assert reg["A"] == pytest.approx(1620.0) and reg["B"] == pytest.approx(1380.0)
    cur = E.current_ratings(matches)
    assert len(cur) == 8 and all(1300 < v < 1700 for v in cur.values())


def test_compute_team_elo_rolling_has_ids(matches, tmp_path):
    spec = importlib.util.spec_from_file_location(
        "compute_team_elo", ROOT / "scripts" / "compute_team_elo.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mp = tmp_path / "matches.parquet"
    matches.to_parquet(mp)
    mod.compute_elo(str(mp), str(tmp_path / "team_elo.csv"))
    rolling = pd.read_csv(tmp_path / "rolling_team_elo.csv")
    assert len(rolling) == 64
    assert rolling.match_id.notna().all() and rolling.season.notna().all()


# ---------- model ----------
def test_blend_and_p2_bounds():
    p = M.blend_probability(0.6, 0.05, 0.05)
    assert 0.05 <= p <= 0.95 and p > 0.55
    chase = {"chase_win_rate": 0.524, "n": 63,
             "logit_shift_team_batting_second": 0.0953}
    # team_1 bats second -> team_1 probability rises
    assert M.p2_adjust(0.5, False, chase) > 0.5
    assert M.p2_adjust(0.5, True, chase) < 0.5


def test_backtest_champion_not_worse_than_coin():
    metrics = json.loads((PRED / "backtest_metrics.json").read_text())
    assert metrics["champion_blend"]["log_loss"] < metrics["baseline_coin"]["log_loss"]
    assert metrics["champion_blend"]["n"] == 32
    # the fitted logistic challenger is honestly recorded as worse
    assert (metrics["challenger_logistic_raw"]["log_loss"]
            > metrics["baseline_higher_elo"]["log_loss"])


def test_expected_xi_constraints():
    priors = pd.read_csv(PRED / "player_priors.csv")
    for team, squad in priors.groupby("team"):
        xi = engine.select_expected_xi(squad)
        assert len(xi) == 11 and len(set(xi)) == 11
        rows = squad[squad.player_key.isin(xi)]
        if (squad.role == "Wicketkeeper").any():
            assert (rows.role == "Wicketkeeper").sum() >= 1


# ---------- frozen log ----------
def test_frozen_log_is_append_only(tmp_path):
    preds = pd.DataFrame([{
        "match_id": "s3_2026_99", "team_1_name": "A", "team_2_name": "B",
        "p_team_1_win": 0.55, "p_elo": 0.54, "p_logistic_challenger": 0.5,
        "features_json": "{}"}])
    assert engine.lock_predictions(tmp_path, preds, "P1") == 1
    assert engine.lock_predictions(tmp_path, preds, "P1") == 0  # duplicate refused
    assert engine.lock_predictions(tmp_path, preds, "P2") == 1  # new stage ok
    log = pd.read_csv(tmp_path / "data/predictions/frozen_log.csv")
    assert len(log) == 2


def test_frozen_log_production_rows():
    log = pd.read_csv(PRED / "frozen_log.csv")
    assert (log.stage == "P1_preseason_expected_xi").sum() == 28
    assert log.match_id.is_unique and log.timestamp_locked.notna().all()
    assert log.p_team_1_win.between(0.05, 0.95).all()


# ---------- simulator ----------
def test_simulator_output_ranges(matches):
    bb = pd.read_parquet(ROOT / "data/normalized/ball_by_ball_normalized.parquet")
    reg = json.loads((PRED / "registry_map.json").read_text())["names"]
    dists = S.build_distributions(bb, reg)
    for ph in S.PHASES:
        assert dists[ph]["collective"].sum() == pytest.approx(1.0)
    ln = pd.read_parquet(ROOT / "data/final/parquet/match_lineups.parquet")
    m = ln[ln.match_id == "espn_1462596"]
    xi = {t: list(g.sort_values("xi_position").cricsheet_registry_id)
          for t, g in m.groupby("team_name")}
    teams = sorted(xi)
    res = S.simulate_match(xi[teams[0]], xi[teams[1]], xi[teams[1]], xi[teams[0]],
                           dists, {}, n_sims=500, seed=3)
    assert 0.0 <= res["p_team_1_win"] <= 1.0
    assert 80 < res["mean_score_1"] < 230 and 80 < res["mean_score_2"] < 230


def test_match_lineups_backfilled():
    ln = pd.read_parquet(ROOT / "data/final/parquet/match_lineups.parquet")
    assert ln.match_id.nunique() == 64
    assert len(ln) == 64 * 22
    assert ln.cricsheet_registry_id.notna().all()
