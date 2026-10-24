"""Phase 2 (accuracy build) tests: frozen-log integrity for the A1
shadow locks, temperature calibration (A2), pre-registration drift
alarm (A3), and matchday validation / dry-run isolation (A4)."""
import importlib.util
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.prediction import elo as E  # noqa: E402
from src.prediction import engine  # noqa: E402
from src.prediction import model as M  # noqa: E402
from src.prediction import priors as P  # noqa: E402
from src.prediction import simulator as S  # noqa: E402

PRED = ROOT / "data/predictions"

# The 28 originally locked v1 rows (match_id -> p_team_1_win), captured
# from the pre-A1 frozen log. Any change to these rows is a breach of
# the append-only rule.
ORIGINAL_P1 = {
    's3_2026_01': 0.4799, 's3_2026_02': 0.5144, 's3_2026_03': 0.5003,
    's3_2026_04': 0.4532, 's3_2026_05': 0.4718, 's3_2026_06': 0.5152,
    's3_2026_07': 0.4698, 's3_2026_08': 0.4641, 's3_2026_09': 0.4963,
    's3_2026_10': 0.4715, 's3_2026_11': 0.4501, 's3_2026_12': 0.5148,
    's3_2026_13': 0.5271, 's3_2026_14': 0.4693, 's3_2026_15': 0.4866,
    's3_2026_16': 0.4492, 's3_2026_17': 0.4968, 's3_2026_18': 0.4975,
    's3_2026_19': 0.496, 's3_2026_20': 0.4723, 's3_2026_21': 0.4496,
    's3_2026_22': 0.5112, 's3_2026_23': 0.4689, 's3_2026_24': 0.4773,
    's3_2026_25': 0.5005, 's3_2026_26': 0.4841, 's3_2026_27': 0.5008,
    's3_2026_28': 0.5245}


def _log():
    return pd.read_csv(PRED / "frozen_log.csv")


def _prereg():
    d = json.loads((PRED / "preregistration_s3.json").read_text())
    consts = dict(d["constants"])
    for a in d.get("amendments", []):  # amendments override by field
        consts[a["field"]] = a["after"]
    return consts


def _lock_matchday():
    spec = importlib.util.spec_from_file_location(
        "lock_matchday", ROOT / "scripts/lock_matchday.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ------------------------------------------------------------- A1 integrity
def test_original_p1_rows_unchanged():
    log = _log()
    p1 = log[log["stage"] == "P1_preseason_expected_xi"]
    assert len(p1) == 28
    got = dict(zip(p1["match_id"], p1["p_team_1_win"]))
    assert got == ORIGINAL_P1
    assert (p1["model_version"] == "v1").all()


def test_sim_shadow_rows_present_and_valid():
    log = _log()
    sim = log[log["stage"] == "SIM_shadow_preseason"]
    assert len(sim) == 28
    assert set(sim["match_id"]) == set(ORIGINAL_P1)
    assert (sim["model_version"] == "sim_v1").all()
    assert sim["p_team_1_win"].between(0, 1, inclusive="neither").all()
    assert sim["p_logistic_challenger"].isna().all()
    for feats in sim["features_json"].map(json.loads):
        assert feats["n_sims"] == 10000


def test_stage_contracts_for_new_stages():
    sim_spec = engine.STAGE_INPUTS["SIM_shadow_preseason"]
    assert sim_spec["system"] == "shadow_simulator"
    assert "toss_decision" in sim_spec["forbidden"]
    assert engine.STAGE_INPUTS["P1_post_XI"]["requires"] == ["announced_xi"]
    with pytest.raises(ValueError):
        engine.validate_stage_inputs(
            "P1_post_XI", {"announced_xi": {}, "toss_decision": "field"})


# ------------------------------------------------------------- A2 temperature
def test_temperature_bounds_and_identity():
    assert float(M.apply_temperature(0.5)) == pytest.approx(0.5)
    out = M.apply_temperature([0.001, 0.999])
    assert out[0] >= M.CLIP[0] and out[1] <= M.CLIP[1]
    ident = M.apply_temperature([0.2, 0.7], T=1.0)
    assert list(ident) == pytest.approx([0.2, 0.7])


def test_temperature_constant_matches_records():
    rec = json.loads((PRED / "model_v1_1.json").read_text())
    assert M.TEMPERATURE_V1_1 == rec["calibration"]["temperature_T"]
    assert M.TEMPERATURE_V1_1 == _prereg()["temperature_v1_1"]


# ------------------------------------------------------------- A3 drift alarm
def test_preregistration_drift_alarm():
    """If a code constant changes without a preregistration amendment,
    this test fails -- that is the point of it."""
    c = _prereg()
    assert E.INITIAL_ELO == c["elo_initial"]
    assert E.DEFAULT_K == c["elo_k"]
    assert E.DEFAULT_SEASON_REGRESSION == c["elo_season_regression"]
    assert E.MOV_CAP == c["elo_mov_cap"]
    assert M.BLEND_K == c["blend_k"]
    assert M.BLEND_W_ELO == c["blend_w_elo"]
    assert list(M.CLIP) == c["clip"]
    assert M.TEMPERATURE_V1_1 == c["temperature_v1_1"]
    assert P.K_BAT == c["priors_k_bat"]
    assert P.K_BOWL == c["priors_k_bowl"]
    assert P.HALF_LIFE_DAYS == c["priors_half_life_days"]
    code_t = {label: t for _f, (label, t) in P.COMPETITIONS.items()}
    assert code_t == c["translation_factors"]
    assert S.K_BAT_SIM == c["sim_k_bat"]
    assert S.K_BOWL_SIM == c["sim_k_bowl"]
    mv1 = json.loads((PRED / "model_v1.json").read_text())
    assert mv1["chase"]["logit_shift_team_batting_second"] == \
        pytest.approx(c["chase_logit_shift"])
    assert engine.MODEL_VERSION == "v1"


# ------------------------------------------------------------- A4 matchday
def _example_xi(mod):
    master = pd.read_csv(PRED / "player_master.csv")
    fixtures = pd.read_csv(ROOT / "data/fixtures/s3_fixtures.csv")
    df = pd.read_csv(ROOT / "data/matchday/example_xi.csv")
    return mod.resolve_players(df, master), fixtures, master


def test_matchday_example_xi_validates():
    mod = _lock_matchday()
    resolved, fixtures, master = _example_xi(mod)
    fx = fixtures[fixtures["match_id"] == "s3_2026_03"].iloc[0]
    xi = mod.validate_xi(resolved, fx, master)
    assert all(len(v) == 11 for v in xi.values())


def test_matchday_rejects_bad_xis():
    mod = _lock_matchday()
    resolved, fixtures, master = _example_xi(mod)
    fx = fixtures[fixtures["match_id"] == "s3_2026_03"].iloc[0]
    team = fx["team_1_name"]
    ten = resolved[~((resolved["team"] == team)
                      & (resolved["batting_position"] == 11))]
    with pytest.raises(ValueError):  # 10 players
        mod.validate_xi(ten, fx, master)
    dup = resolved.copy()
    dup.loc[dup["team"] == team, "player"] = (
        dup[dup["team"] == team]["player"].iloc[0])
    dup = mod.resolve_players(dup.drop(columns=["player_key"]), master)
    with pytest.raises(ValueError):  # duplicates
        mod.validate_xi(dup, fx, master)
    wrong = resolved.copy()
    other = master[master["team"] == fx["team_2_name"]].iloc[0]
    i = wrong[wrong["team"] == team].index[0]
    wrong.loc[i, "player_key"] = other["player_key"]
    with pytest.raises(ValueError):  # player from the other squad
        mod.validate_xi(wrong, fx, master)


def test_matchday_dry_run_writes_only_to_temp(tmp_path):
    mod = _lock_matchday()
    before = len(_log())
    resolved, fixtures, master = _example_xi(mod)
    fx = fixtures[fixtures["match_id"] == "s3_2026_03"].iloc[0]
    xi = mod.validate_xi(resolved, fx, master)
    frame = mod.compute_p1_post_xi(ROOT, "s3_2026_03", xi)
    n = engine.lock_predictions(tmp_path, frame, "P1_post_XI",
                                model_version="v1.1")
    assert n == 1
    tmp_log = pd.read_csv(tmp_path / "data/predictions/frozen_log.csv")
    assert tmp_log.iloc[0]["stage"] == "P1_post_XI"
    assert tmp_log.iloc[0]["model_version"] == "v1.1"
    assert len(_log()) == before  # production log untouched
