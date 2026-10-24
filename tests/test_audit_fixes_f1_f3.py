"""Tests for the F1-F3 integrity audit fixes (2026-10-24).

F1: Elo constants were selected on the S2 set also reported as the
    backtest (selection-on-test). Audit artefact + bound + Amendment #3.
F2: the coin baseline's spurious "accuracy" (0.34375 = the S2 team_1
    win share under the p>=0.5 tie rule) is now null by definition;
    the tie rule is uniform and explicit.
F3: "updates after every match" corrected to published-and-ingested
    cadence; as-of sidecar (predictions_status.json) + dashboard line.
"""
import importlib.util
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.prediction import elo as E  # noqa: E402
from src.prediction.metrics import (accuracy, coin_baseline_metrics,  # noqa: E402
                                    per_match_correct)

PRED = ROOT / "data" / "predictions"


# ---------------------------------------------------------------- F1
@pytest.fixture(scope="module")
def elo_audit():
    return json.loads((PRED / "elo_selection_audit.json").read_text())


def test_f1_provenance_and_bound(elo_audit):
    prov = elo_audit["provenance"]
    # the restricted grid recomputed by the audit reproduces the saved
    # elo_tuning.csv surface exactly -- the provenance claim is checkable
    assert all(r["reproduces_saved"] for r in prov["restricted_grid_recomputed"])
    assert prov["restricted_grid_argmin"]["k"] == 20.0
    assert prov["restricted_grid_argmin"]["season_regression"] == 0.40
    assert prov["restricted_grid_range"] == pytest.approx(0.004955, abs=1e-5)
    grid = elo_audit["s2_full_grid"]
    assert grid["ll_at_chosen_20_0.40"] == pytest.approx(0.6888483, abs=1e-6)
    assert grid["selection_bound"] == pytest.approx(
        prov["restricted_grid_range"], abs=1e-9)
    assert grid["selection_bound_outer_full_grid_range"] > grid["selection_bound"]


def test_f1_s1_only_reselection_and_decision(elo_audit):
    sel = elo_audit["s1_only_selection"]
    assert sel["chosen_k"] == 28.0  # selected within Season 1 only
    assert abs(sel["difference_s1k_minus_chosen_on_s2"]) <= 0.002
    assert sel["branch"] == "within_0.002_or_better"
    assert "keep" in elo_audit["decision"]["action"]
    assert elo_audit["decision"]["standing_rule"].startswith(
        "Future parameter selection must be nested")
    # shipped constants unchanged by the audit
    assert E.DEFAULT_K == 20.0 and E.DEFAULT_SEASON_REGRESSION == 0.40


def test_f1_s2_ll_spot_check(elo_audit):
    matches = pd.read_parquet(ROOT / "data/normalized/matches_normalized.parquet")
    hist = E.compute_history(matches, k=20.0, season_regression=0.40)
    ev = hist[(hist["season"] == "S2") & hist["score_team_1"].notna()]
    from src.prediction.metrics import log_loss
    assert log_loss(ev["expected_team_1"], ev["score_team_1"]) == pytest.approx(
        elo_audit["s2_full_grid"]["ll_at_chosen_20_0.40"], abs=1e-9)


def test_f1_amendment_3_recorded():
    md = (ROOT / "docs/PREREGISTRATION_S3.md").read_text()
    assert "Amendment #3" in md and "selection-on-test" in md
    d = json.loads((PRED / "preregistration_s3.json").read_text())
    a3 = next(a for a in d["amendments"] if a["id"] == 3)
    assert a3["field"] == "elo_parameter_provenance"
    assert a3["after"]["changed"] is False
    assert a3["after"]["k"] == 20.0 and a3["after"]["season_regression"] == 0.40


# ---------------------------------------------------------------- F2
def test_f2_coin_baseline_is_definitional():
    c = coin_baseline_metrics(32)
    assert c["accuracy"] is None
    assert c["log_loss"] == pytest.approx(math.log(2))
    assert c["brier"] == 0.25
    assert "accuracy_note" in c


def test_f2_backtest_metrics_coin_fixed():
    m = json.loads((PRED / "backtest_metrics.json").read_text())
    coin = m["baseline_coin"]
    assert coin["accuracy"] is None and "accuracy_note" in coin
    assert coin["log_loss"] == pytest.approx(math.log(2))
    assert coin["brier"] == 0.25
    # the bootstrap blocks added by the R4 pass are untouched
    assert "champion_vs_elo_bootstrap" in m
    assert "simulator_vs_champion_bootstrap" in m


def test_f2_tie_rule_synthetic():
    # exact 0.5 picks team_1 by convention and is scored normally
    assert accuracy([0.5, 0.5], [1, 0]) == 0.5
    assert accuracy([0.5], [1]) == 1.0
    assert accuracy([0.5], [0]) == 0.0
    assert per_match_correct([0.5], [1]).tolist() == [1.0]
    assert per_match_correct([0.5], [0]).tolist() == [0.0]


def test_f2_tie_audit_on_saved_backtests():
    bt = pd.read_csv(PRED / "backtest_s2.csv")
    stored = json.loads((PRED / "backtest_metrics.json").read_text())
    cols = {"champion_blend": "p_blend", "challenger_logistic_raw": "p_raw",
            "baseline_higher_elo": "p_elo", "baseline_chase_heuristic": "p_chase"}
    expected_ties = {"p_blend": 0, "p_raw": 0, "p_elo": 0, "p_chase": 3}
    y = bt["y"].to_numpy()
    for name, col in cols.items():
        p = bt[col].to_numpy()
        assert int((p == 0.5).sum()) == expected_ties[col], name
        # every stored accuracy reproduces under the uniform tie rule
        assert accuracy(p, y) == pytest.approx(stored[name]["accuracy"]), name
    # what the old "coin accuracy" actually was: the team_1 win share
    assert y.mean() == pytest.approx(0.34375)
    sim = pd.read_csv(PRED / "backtest_simulator.csv")
    sj = json.loads((PRED / "backtest_simulator.json").read_text())
    assert int((sim["p_sim_team_1"] == 0.5).sum()) == 0
    assert accuracy(sim["p_sim_team_1"], sim["y"]) == pytest.approx(
        sj["simulator"]["accuracy"])


# ---------------------------------------------------------------- F3
def _refresh_module():
    spec = importlib.util.spec_from_file_location(
        "refresh_predictions", ROOT / "scripts" / "refresh_predictions.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_f3_status_sidecar_matches_normalized_data():
    status = json.loads((PRED / "predictions_status.json").read_text())
    matches = pd.read_parquet(ROOT / "data/normalized/matches_normalized.parquet")
    assert status["data_as_of"] == str(pd.to_datetime(
        matches["match_date"]).max().date())
    assert status["n_matches_ingested"] == len(matches)


def test_f3_status_writer_uses_max_match_date(tmp_path):
    mod = _refresh_module()
    (tmp_path / "data/normalized").mkdir(parents=True)
    (tmp_path / "data/predictions").mkdir(parents=True)
    m = pd.DataFrame({"match_date": ["2025-11-17", "2025-12-13", "2024-11-30"],
                      "season": ["S2", "S2", "S1"]})
    m.to_parquet(tmp_path / "data/normalized/matches_normalized.parquet")
    st = mod.write_predictions_status(tmp_path)
    assert st["data_as_of"] == "2025-12-13"
    assert st["n_matches_ingested"] == 3
    on_disk = json.loads(
        (tmp_path / "data/predictions/predictions_status.json").read_text())
    assert on_disk["data_as_of"] == "2025-12-13"


def test_f3_claims_corrected_and_amendment_4():
    runbook = (ROOT / "docs/PREDICTION_SYSTEM.md").read_text()
    assert "Data publication lag" in runbook
    assert "median\n8 days" in runbook or "median 8" in runbook
    assert "published and ingested" in runbook
    md = (ROOT / "docs/PREREGISTRATION_S3.md").read_text()
    assert "Amendment #4" in md
    d = json.loads((PRED / "preregistration_s3.json").read_text())
    a4 = next(a for a in d["amendments"] if a["id"] == 4)
    assert a4["field"] == "update_cadence"
    assert a4["after"]["measured_s2_lag_days"]["median"] == 8


def test_f3_dashboard_shows_ratings_as_of(tmp_path):
    from streamlit.testing.v1 import AppTest
    script = tmp_path / "render_mp.py"
    script.write_text(
        "import sys\nsys.path.insert(0, r'%s')\n"
        "from src.dashboard.page_modules.match_predictions import "
        "render_match_predictions\nrender_match_predictions()\n" % ROOT)
    at = AppTest.from_file(str(script), default_timeout=180).run()
    assert not at.exception
    status = json.loads((PRED / "predictions_status.json").read_text())
    assert any(f"Ratings as of: {status['data_as_of']}" in c.value
               for c in at.caption)
