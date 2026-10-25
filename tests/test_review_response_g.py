"""Tests for the third-review response pass (G1, G2, G3, G5).

G1: canonical stage registry (review S13) — "P1" named two different
    information sets; horizons now have canonical names in
    src/prediction/stages.py and stored strings resolve through it.
G2: as-of invariance (review S12) — adding later matches must not
    change any earlier match's ratings, features or forecast inputs.
G3: role-source verification (review S12) — no prediction-path input
    reads the legacy enriched profiles' primary_role (constant
    'Batter' for all 188 rows); roles come from the S3 player master.
G5: WPA labelling (S15) + leave-one-match-out influence (S11).
"""
import importlib.util
import json
import sys
import zipfile
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from src.prediction import elo as E  # noqa: E402
from src.prediction import engine  # noqa: E402
from src.prediction import model as M  # noqa: E402
from src.prediction import priors as P  # noqa: E402
from src.prediction import stages as STAGES  # noqa: E402

PRED = ROOT / "data" / "predictions"
ZIP_DIR = ROOT.parent / ".scratch" / "predbuild"
S2_ASOF = date(2025, 11, 17)  # Season 2 start = the backtest's as-of date


def _load_script(name):
    spec = importlib.util.spec_from_file_location(
        name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def matches():
    return pd.read_parquet(ROOT / "data/normalized/matches_normalized.parquet")


@pytest.fixture(scope="module")
def order(matches):
    """Match IDs in the production (match_date, match_id) order."""
    return list(E.compute_history(matches)["match_id"])


# ------------------------------------------------------------------- G1
def test_registry_mapping_is_total_over_frozen_log():
    log = pd.read_csv(PRED / "frozen_log.csv")
    present = set(log["stage"].unique())
    assert present == {"P1_preseason_expected_xi", "SIM_shadow_preseason"}
    canonicals = {STAGES.canonical_stage(s) for s in present}
    assert canonicals == {"P0_PRESEASON", "SIM_SHADOW"}
    # every stored string maps to exactly one canonical name (a dict
    # lookup — totality is the assertion that none of these raised)


def test_registry_mapping_table_and_reverse():
    assert STAGES.canonical_stage("P1_preseason_expected_xi") == "P0_PRESEASON"
    assert STAGES.canonical_stage("P1_post_XI") == "P1_CONFIRMED_XI"
    assert STAGES.canonical_stage("P1") == "P1_CONFIRMED_XI"   # contract alias
    assert STAGES.canonical_stage("P2_post_toss") == "P2_POST_TOSS"
    assert STAGES.canonical_stage("P2") == "P2_POST_TOSS"      # contract alias
    assert STAGES.canonical_stage("SIM_shadow_preseason") == "SIM_SHADOW"
    assert STAGES.stored_stage("P0_PRESEASON") == "P1_preseason_expected_xi"
    assert STAGES.stored_stage("P1_CONFIRMED_XI") == "P1_post_XI"
    assert STAGES.stored_stage("P2_POST_TOSS") == "P2_post_toss"
    assert STAGES.stored_stage("SIM_SHADOW") == "SIM_shadow_preseason"
    for stored in ("P1_preseason_expected_xi", "P1_post_XI",
                   "P2_post_toss", "SIM_shadow_preseason"):
        assert STAGES.stored_stage(STAGES.canonical_stage(stored)) == stored


def test_registry_unknown_stage_raises():
    with pytest.raises(ValueError):
        STAGES.canonical_stage("P9")
    with pytest.raises(ValueError):
        STAGES.canonical_stage("P1_preseason")  # near-miss is still unknown
    with pytest.raises(ValueError):
        STAGES.stored_stage("INPLAY")           # never locked in the log
    with pytest.raises(ValueError):
        STAGES.stored_stage("P3")


def test_registry_covers_engine_contracts_exactly():
    # The engine's stage contracts and the registry must name the same
    # universe of stage strings — no contract without a canonical home,
    # no registered string the engine would refuse.
    assert set(engine.STAGE_INPUTS) == set(STAGES.STAGE_TO_CANONICAL)


def test_scoring_groups_by_canonical_horizon():
    sp = _load_script("score_predictions")
    stages_rows = [("m1", "P1_preseason_expected_xi"), ("m2", "P1"),
                   ("m3", "P1_post_XI"), ("m4", "P2_post_toss")]
    log = pd.DataFrame([
        {"match_id": mid, "stage": st, "team_1_name": "A", "team_2_name": "B",
         "p_team_1_win": 0.6, "p_elo": 0.55} for mid, st in stages_rows])
    matches = pd.DataFrame([
        {"season": "S3", "match_date": f"2026-10-{26 + i}", "team_1_name": "A",
         "team_2_name": "B", "winner_name": "A", "innings_2_team": "B"}
        for i in range(4)])
    fixtures = pd.DataFrame([
        {"match_id": mid, "match_date": f"2026-10-{26 + i}",
         "team_1_name": "A", "team_2_name": "B"}
        for i, (mid, _st) in enumerate(stages_rows)])
    sdf = sp.build_scored(log, matches, fixtures)
    by = sp.metrics_by_stage(sdf)
    assert set(by) == {"P0_PRESEASON", "P1_CONFIRMED_XI", "P2_POST_TOSS"}
    # the two spellings of the confirmed-XI horizon are ONE horizon
    assert by["P1_CONFIRMED_XI"]["n"] == 2
    assert by["P1_CONFIRMED_XI"]["stored_stages"] == ["P1", "P1_post_XI"]
    assert by["P0_PRESEASON"]["stage"] == "P1_preseason_expected_xi"
    assert by["P1_CONFIRMED_XI"]["canonical_horizon"] == "P1_CONFIRMED_XI"
    assert "Pre-season" in by["P0_PRESEASON"]["canonical_label"]


def test_scoring_unknown_stage_raises():
    sp = _load_script("score_predictions")
    sdf = pd.DataFrame([{
        "match_id": "mX", "stage": "P9", "team_1_name": "A",
        "team_2_name": "B", "p_team_1_win": 0.6, "p_elo": 0.55,
        "p_chase_baseline": 0.5, "actual_team_1_win": 1,
        "outcome_classification": "scored"}])
    with pytest.raises(ValueError):
        sp.metrics_by_stage(sdf)


def test_preregistration_amendment_5_mirrors_registry():
    d = json.loads((PRED / "preregistration_s3.json").read_text())
    a5 = next(a for a in d["amendments"] if a["id"] == 5)
    assert a5["field"] == "stage_nomenclature"
    assert a5["after"]["canonical_to_stored"] == {
        **STAGES.CANONICAL_TO_STAGE, "INPLAY": None}
    assert a5["after"]["constants_changed"] is False
    assert "Amendment #5" in (ROOT / "docs/PREREGISTRATION_S3.md").read_text()


# ------------------------------------------------------------------- G2
def test_g2a_elo_truncation_invariance(matches, order):
    """Recomputing Elo on data truncated inside S2 must reproduce every
    earlier match's pre-match ratings / expected score EXACTLY."""
    full = E.compute_history(matches).set_index("match_id")
    for cut in (32, 40, 48, 56, 63):
        keep = set(order[:cut])
        h = E.compute_history(matches[matches["match_id"].isin(keep)])
        assert set(h["match_id"]) == keep
        h = h.set_index("match_id")
        for col in ("team_1_pre", "team_2_pre", "expected_team_1"):
            assert (h[col] == full.loc[h.index, col]).all(), (cut, col)


def test_g2b_aggregate_date_filter_synthetic(tmp_path):
    """The shared aggregation date filter: a match on/after the
    reference date contributes nothing; one before it does."""
    def match_json(d, bat, bowl, pid_bat, pid_bowl):
        return {"info": {"dates": [d.isoformat()],
                         "registry": {"people": {bat: pid_bat, bowl: pid_bowl}}},
                "innings": [{"team": "X", "overs": [{"over": 0, "deliveries": [
                    {"batter": bat, "bowler": bowl,
                     "runs": {"batter": 1, "extras": 0, "total": 1}}]}]}]}
    zp = tmp_path / "fake_json.zip"
    with zipfile.ZipFile(zp, "w") as z:
        z.writestr("a.json", json.dumps(match_json(
            date(2025, 1, 10), "A Bat", "A Bowl", "id_before_bat", "id_before_bowl")))
        z.writestr("b.json", json.dumps(match_json(
            date(2025, 12, 1), "B Bat", "B Bowl", "id_after_bat", "id_after_bowl")))
    agg = P.aggregate_cricsheet({zp: "NPL"}, ref_date=S2_ASOF,
                                cutoff=S2_ASOF - timedelta(days=3 * 365))
    ids = set(agg["registry_id"])
    assert "id_before_bat" in ids and "id_before_bowl" in ids
    assert "id_after_bat" not in ids and "id_after_bowl" not in ids


def test_g2b_priors_asof_cutoff_npl_data_verified():
    """Data-verified on the bundle that contains Season 2 itself: an
    independent scan of the raw NPL files, date-restricted by the test,
    reproduces the aggregation's decay-weighted totals exactly — and
    the cutoff demonstrably bites (all 32 S2 matches are on/after it).
    player_history.csv retains no dates, so this verifies the as-of
    behaviour at the aggregation level the backtest actually uses."""
    zp = ZIP_DIR / "npl_json.zip"
    cutoff = S2_ASOF - timedelta(days=3 * 365)
    tot_bat = tot_bowl = 0.0
    n_before = n_after = 0
    with zipfile.ZipFile(zp) as z:
        for name in z.namelist():
            if not name.endswith(".json"):
                continue
            d = json.loads(z.read(name))
            try:
                mdate = date.fromisoformat(d["info"]["dates"][0])
            except Exception:
                continue
            if mdate < cutoff:
                continue
            if mdate >= S2_ASOF:
                n_after += 1
                continue
            n_before += 1
            w = 0.5 ** ((S2_ASOF - mdate).days / P.HALF_LIFE_DAYS)
            for inn in d.get("innings", []):
                for over in inn.get("overs", []):
                    for dlv in over.get("deliveries", []):
                        ex = dlv.get("extras", {})
                        if "wides" not in ex:
                            tot_bat += w
                        if "wides" not in ex and "noballs" not in ex:
                            tot_bowl += w
    assert n_before == 32 and n_after == 32  # S1 in, S2 out — filter bites
    agg = P.aggregate_cricsheet({zp: "NPL"}, ref_date=S2_ASOF, cutoff=cutoff)
    allrows = agg[agg["phase"] == "ALL"]
    assert float(allrows["bat_balls"].sum()) == pytest.approx(tot_bat, abs=1e-6)
    assert float(allrows["bowl_balls"].sum()) == pytest.approx(tot_bowl, abs=1e-6)


@pytest.fixture(scope="module")
def priors_s2():
    bt = _load_script("backtest_prediction")
    lineups = pd.read_parquet(ROOT / "data/final/parquet/match_lineups.parquet")
    return bt._priors_asof(S2_ASOF, lineups)


@pytest.fixture(scope="module")
def xi_by_match():
    lineups = pd.read_parquet(ROOT / "data/final/parquet/match_lineups.parquet")
    out = {}
    for (mid, team), g in lineups.groupby(["match_id", "team_name"]):
        out.setdefault(mid, {})[team] = list(g["cricsheet_registry_id"])
    return out


def test_g2c_backtest_features_truncation_invariance(matches, order,
                                                    priors_s2, xi_by_match):
    """For sampled S2 matches, features recomputed from data truncated
    to the matches before them (production (date, match_id) order)
    must equal the production backtest_s2.csv row."""
    bt = pd.read_csv(PRED / "backtest_s2.csv").set_index("match_id")
    pos = {mid: i for i, mid in enumerate(order)}
    for mid in (order[i] for i in (32, 36, 41, 47, 55, 63)):
        keep = set(order[:pos[mid] + 1])
        sub = matches[matches["match_id"].isin(keep)]
        h = E.compute_history(sub)
        f = M.build_features(sub, h, xi_by_match, priors_s2)
        row = f[f["match_id"] == mid].iloc[0]
        prod = bt.loc[mid]
        for col in M.FEATURES_P1:
            assert float(row[col]) == pytest.approx(float(prod[col]), abs=1e-9), \
                (mid, col)
        hrow = h[h["match_id"] == mid].iloc[0]
        p_elo = float(E.expected(hrow["team_1_pre"], hrow["team_2_pre"]))
        assert p_elo == pytest.approx(float(prod["p_elo"]), abs=1e-12)
        p_blend = M.blend_probability(p_elo, float(row["xi_batting_diff"]),
                                      float(row["xi_bowling_diff"]))
        assert p_blend == pytest.approx(float(prod["p_blend"]), abs=1e-9)


# ------------------------------------------------------------------- G3
# Prediction-path files: everything that can feed a prediction number.
PREDICTION_PATH_FILES = [
    *sorted((ROOT / "src/prediction").glob("*.py")),
    *[ROOT / "scripts" / n for n in (
        "build_player_master.py", "build_player_priors.py",
        "backtest_prediction.py", "backtest_simulator.py",
        "lock_matchday.py", "predict_fixtures.py", "simulate_fixtures.py",
        "refresh_predictions.py", "fit_temperature.py", "audit_simulator.py",
        "audit_elo_selection.py", "evaluate_inplay_wp.py",
        "cross_league_check.py", "estimate_translation.py",
        "build_ledger_manifest.py", "score_predictions.py")],
]


def test_g3_no_prediction_input_reads_legacy_primary_role():
    read_patterns = ('["primary_role"]', "['primary_role']",
                     'get("primary_role")', "get('primary_role')")
    for path in PREDICTION_PATH_FILES:
        text = path.read_text()
        for pat in read_patterns:
            assert pat not in text, f"{path.name} reads legacy primary_role"
        if path.name != "players.py":
            # the legacy enriched file may only be touched by the
            # player-master builder (which ignores primary_role)
            assert "enriched_players" not in text, path.name


def test_g3_master_roles_sourced_varied_and_consumed():
    master = pd.read_csv(PRED / "player_master.csv")
    assert master["role"].value_counts().to_dict() == {
        "All-rounder": 51, "Bowler": 42, "Batter": 32, "Wicketkeeper": 18}
    assert set(master["role_source"]) == {"s3_roster.playing_role"}
    # the role column actually consumed downstream (priors -> XI
    # selector / simulator priors) is the master's, per player_key
    priors = pd.read_csv(PRED / "player_priors.csv")
    merged = priors.set_index("player_key")["role"].to_dict()
    for _, r in master.iterrows():
        assert merged[r["player_key"]] == r["role"]
    assert priors["role"].nunique() == 4


def test_g3_legacy_role_field_is_constant_by_construction():
    # WHY the legacy field must never be used: it carries no signal.
    legacy = pd.read_csv(
        ROOT / "data/player_profiles/enriched_players_20260521.csv")
    assert len(legacy) == 237  # 188 legacy + 49 sourced S3 profile rows (2026-10-24 enrichment)
    assert legacy["primary_role"].nunique() == 1
    assert legacy["primary_role"].iloc[0] == "Batter"


# ------------------------------------------------------------------- G5
def test_g5_lomo_influence_recorded_and_consistent():
    audit = _load_script("audit_simulator")
    y = np.array([1, 0, 1, 0])
    pa = np.array([0.6, 0.4, 0.7, 0.3])
    out = audit.lomo_influence(pa, np.full(4, 0.5), y, ["a", "b", "c", "e"])
    assert out["n"] == 4 and out["max_abs_change"] >= 0
    assert out["most_influential_match"] in {"a", "b", "c", "e"}
    saved = json.loads((PRED / "simulator_audit.json").read_text())
    lomo = saved["lomo_influence"]
    assert set(lomo) == {"simulator_minus_champion_logloss",
                         "champion_minus_elo_logloss"}
    for entry in lomo.values():
        assert entry["n"] == 32 and entry["max_abs_change"] >= 0
        assert entry["most_influential_match"].startswith("espn_")
    # LOMO's full-sample difference is the bootstrap's mean difference
    boot = saved["bootstrap"]["simulator_minus_champion_logloss"]
    assert lomo["simulator_minus_champion_logloss"]["full_mean_diff"] == \
        pytest.approx(boot["mean_diff"], abs=1e-12)
    champ = saved["champion_minus_elo_logloss"]
    assert lomo["champion_minus_elo_logloss"]["full_mean_diff"] == \
        pytest.approx(champ["mean_diff"], abs=1e-12)


def test_g5_wpa_page_labelled_and_renders(tmp_path):
    from streamlit.testing.v1 import AppTest
    import src.dashboard.page_modules.win_probability as wp
    assert "Exploratory historical estimates" in wp.WPA_NOTE
    assert "Match Predictions" in wp.WPA_NOTE
    script = tmp_path / "render_wp.py"
    script.write_text(
        "import sys\nsys.path.insert(0, r'%s')\n"
        "from src.dashboard.page_modules.win_probability import "
        "render_win_probability\nrender_win_probability()\n" % ROOT)
    at = AppTest.from_file(str(script), default_timeout=180).run()
    assert not at.exception
    assert any("Exploratory historical estimates" in i.value for i in at.info)
