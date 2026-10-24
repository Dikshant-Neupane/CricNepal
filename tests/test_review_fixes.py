"""Tests for the review-response fixes R1-R4 (three-system separation,
fixture start-time reconciliation, simulator audit, uncertainty)."""
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.prediction import engine  # noqa: E402
from src.prediction import metrics as MT  # noqa: E402

PRED = ROOT / "data" / "predictions"


def _load_script(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------- R1: fixture start times ----------
@pytest.fixture(scope="module")
def fixtures():
    return pd.read_csv(ROOT / "data/fixtures/s3_fixtures.csv")


def test_fixture_start_times_present_or_blank_with_reason(fixtures):
    for _, r in fixtures.iterrows():
        if isinstance(r.start_time_local, str) and r.start_time_local:
            assert r.start_time_local in ("12:30", "17:00")
            assert isinstance(r.start_time_source, str) and r.start_time_source
            assert isinstance(r.start_time_accessed, str) and r.start_time_accessed
            assert "VERIFIED" in r.start_time_verification
        else:  # blank is allowed ONLY with an explicit reason recorded
            assert isinstance(r.start_time_verification, str)
            assert "UNVERIFIED" in r.start_time_verification


def test_fixture_start_time_slots(fixtures):
    by_num = fixtures.set_index("match_number")
    assert by_num.loc[1, "start_time_local"] == "17:00"   # single-match opener
    assert by_num.loc[2, "start_time_local"] == "12:30"   # double-header, first
    assert by_num.loc[3, "start_time_local"] == "17:00"   # double-header, second (Bolts v Karnali)
    assert by_num.loc[32, "start_time_local"] == "17:00"  # Final, single-match day
    # every double-header day follows 12:30 then 17:00, in fixture order
    for date, g in fixtures.groupby("match_date"):
        times = list(g.sort_values("match_number").start_time_local)
        assert times == (["17:00"] if len(g) == 1 else ["12:30", "17:00"]), date


# ---------- R2a: stage input contracts ----------
def test_p1_contract_refuses_toss_inputs():
    feats = {"elo_diff": 0.1, "xi_batting_diff": 0.0, "xi_bowling_diff": 0.0,
             "form_nrr_diff": 0.0, "rest_diff": 0.0}
    engine.validate_stage_inputs("P1", feats)  # clean P1 inputs pass
    for stage in ("P1", "P1_preseason_expected_xi"):
        with pytest.raises(ValueError):
            engine.validate_stage_inputs(stage, {**feats, "toss_winner_name": "A"})
        with pytest.raises(ValueError):
            engine.validate_stage_inputs(stage, {**feats, "toss_decision": "bat"})


def test_p1_feature_set_has_no_toss():
    from src.prediction import model as M
    assert not any("toss" in f for f in M.FEATURES_P1)
    assert not (set(engine.STAGE_INPUTS["P1"]["allowed"]) & set(engine.TOSS_FIELDS))
    assert set(engine.STAGE_INPUTS["P2"]["requires"]) == {
        "toss_winner_name", "toss_decision"}


def test_p2_contract_requires_valid_toss():
    chase = {"chase_win_rate": 0.524, "n": 63,
             "logit_shift_team_batting_second": 0.0953}
    with pytest.raises(ValueError):
        engine.validate_stage_inputs("P2", {})
    with pytest.raises(ValueError):
        engine.validate_stage_inputs("P2", {"toss_winner_name": "A"})
    with pytest.raises(ValueError):
        engine.p2_probability(0.5, "A", "B", "A", "spin", chase)
    with pytest.raises(ValueError):
        engine.p2_probability(0.5, "A", "B", "C", "bat", chase)
    # winner chose to field -> team_2 bats first if winner is team_2... A wins
    # toss and bats: team_1 bats first, so team_1 probability falls (chase premium)
    assert engine.p2_probability(0.5, "A", "B", "A", "bat", chase) < 0.5
    assert engine.p2_probability(0.5, "A", "B", "A", "field", chase) > 0.5


def test_lock_predictions_rejects_unknown_stage(tmp_path):
    preds = pd.DataFrame([{"match_id": "x1", "team_1_name": "A",
                           "team_2_name": "B", "p_team_1_win": 0.5,
                           "p_elo": 0.5, "p_logistic_challenger": 0.5,
                           "features_json": "{}"}])
    with pytest.raises(ValueError):
        engine.lock_predictions(tmp_path, preds, "P9")


# ---------- R2b: per-stage scoring separation ----------
def test_scoring_is_per_stage_never_pooled():
    sp = _load_script("score_predictions")
    log = pd.DataFrame([
        {"match_id": "s3_2026_01", "stage": "P1", "team_1_name": "A",
         "team_2_name": "B", "p_team_1_win": 0.6, "p_elo": 0.55},
        {"match_id": "s3_2026_01", "stage": "P2", "team_1_name": "A",
         "team_2_name": "B", "p_team_1_win": 0.65, "p_elo": 0.55},
    ])
    matches = pd.DataFrame([{
        "season": "S3", "match_date": "2026-10-26", "team_1_name": "A",
        "team_2_name": "B", "winner_name": "A", "innings_2_team": "B"}])
    fixtures = pd.DataFrame([{
        "match_id": "s3_2026_01", "match_date": "2026-10-26",
        "team_1_name": "A", "team_2_name": "B"}])
    sdf = sp.build_scored(log, matches, fixtures)
    assert len(sdf) == 2
    by_stage = sp.metrics_by_stage(sdf)
    assert set(by_stage) == {"P1", "P2"}          # exactly the stages present
    assert not any(k.lower() in ("all", "pooled", "overall", "total")
                   for k in by_stage)              # no pooled entry, ever
    for entry in by_stage.values():               # baselines kept per stage
        assert {"model", "elo_baseline", "chase_baseline"} <= set(entry)


# ---------- R2c: in-play evaluation file ----------
def test_inplay_evaluation_structure():
    ev = json.loads((PRED / "inplay_wp_evaluation.json").read_text())
    assert ev["system"] == "in_play_win_probability"
    assert ev["comparable_to_prematch_metrics"] is False
    assert "NOT comparable" in ev["header_note"]
    assert ev["train_season"] == "S1" and ev["test_season"] == "S2"
    assert set(ev["by_innings"]) == {"1", "2"}
    for blk in [ev["overall"], *ev["by_innings"].values()]:
        assert 0.0 < blk["log_loss"] < 0.7 and 0.0 < blk["brier"] < 0.25
        assert blk["n_matches"] == 32 and blk["n_deliveries"] == blk["n"]


# ---------- R3: identical-set + bootstrap reproducibility ----------
def test_compare_match_sets_logic():
    audit = _load_script("audit_simulator")
    same = audit.compare_match_sets({"a": ["m1", "m2"], "b": ["m2", "m1"]})
    assert same["identical"] and same["intersection_size"] == 2
    diff = audit.compare_match_sets({"a": ["m1", "m2"], "b": ["m1", "m3"]})
    assert not diff["identical"]
    assert diff["pair_differences"]["a vs b"]["only_in_first"] == ["m2"]
    assert diff["pair_differences"]["a vs b"]["only_in_second"] == ["m3"]


def test_simulator_audit_outputs():
    a = json.loads((PRED / "simulator_audit.json").read_text())
    assert a["identical_set_check"]["identical"] is True
    assert a["identical_set_check"]["sizes"]["simulator_backtest"] == 32
    statuses = {i["item"]: i["status"] for i in a["leakage_checklist"]}
    assert any(s == "FLAG" for s in statuses.values())  # flags are not hidden
    ci = a["bootstrap"]["simulator_minus_champion_logloss"]
    # verdict must follow the pre-committed rule from the CI itself
    expected = "advantage not established" if ci["ci_includes_zero"] else \
        "advantage established on this backtest (still requires frozen-log confirmation before promotion)"
    assert a["verdict"] == expected


def test_paired_bootstrap_reproducible():
    rng = np.random.default_rng(0)
    diffs = rng.normal(-0.03, 0.2, size=32)
    r1 = MT.paired_bootstrap(diffs, n_resamples=2000, seed=42)
    r2 = MT.paired_bootstrap(diffs, n_resamples=2000, seed=42)
    assert r1 == r2  # fixed seed -> identical result
    assert r1["ci_low"] <= r1["mean_diff"] <= r1["ci_high"]
    assert 0.0 <= r1["prob_a_better"] <= 1.0
    zero = MT.paired_bootstrap(np.zeros(32), n_resamples=100, seed=1)
    assert zero["mean_diff"] == 0.0 and zero["ci_includes_zero"]


# ---------- R4: headline uncertainty recorded ----------
def test_backtest_metrics_has_bootstrap_fields():
    bm = json.loads((PRED / "backtest_metrics.json").read_text())
    b = bm["champion_vs_elo_bootstrap"]
    assert b["n_matches"] == 32 and b["seed"] == 42
    assert b["ci_low"] <= b["mean_diff"] <= b["ci_high"]
    # additive only: the original headline numbers are untouched
    assert bm["champion_blend"]["log_loss"] == pytest.approx(0.6891, abs=1e-3)
    assert bm["baseline_higher_elo"]["log_loss"] == pytest.approx(0.6888, abs=1e-3)
