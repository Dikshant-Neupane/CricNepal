"""Tests for the pre-season hardening pass (H1-H5).

H1: ledger manifest builds and verifies; tampering is detected.
H2: outcome classification for scoring (super over / DLS / no result /
    tied with no decider) and metrics ignoring excluded matches.
H3: dashboard XI data-quality computation on the real files.
H4: player resolution log integrity.
"""
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.prediction import metrics as MET  # noqa: E402

PRED = ROOT / "data" / "predictions"


def _load_script(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------- H1
def _mini_tree(tmp_path):
    """A minimal repo-shaped tree holding the manifest's inputs."""
    blm = _load_script("build_ledger_manifest")
    for rel in [blm.FROZEN_LOG, *blm.SNAPSHOTS]:
        dest = tmp_path / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / rel, dest)
    env = ["-c", "user.email=test@example.com", "-c", "user.name=test"]
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(["git", *env, "-C", str(tmp_path), "add", "-A"], check=True)
    subprocess.run(["git", *env, "-C", str(tmp_path), "commit", "-qm", "x"],
                   check=True)
    manifest = blm.build_manifest(tmp_path)
    out = tmp_path / "data/predictions/ledger_manifest.json"
    out.write_text(json.dumps(manifest, indent=1))
    return blm, tmp_path


def test_manifest_builds_and_verifies(tmp_path):
    blm, tree = _mini_tree(tmp_path)
    lines, ok = blm.verify_manifest(tree)
    assert ok, lines
    assert any("frozen_log.sha256: MATCH" in line for line in lines)
    manifest = json.loads(
        (tree / "data/predictions/ledger_manifest.json").read_text())
    stages = manifest["frozen_log"]["stages"]
    assert stages["P1_preseason_expected_xi"]["rows"] == 28
    assert stages["SIM_shadow_preseason"]["rows"] == 28
    assert manifest["frozen_log"]["rows"] == 56


def test_manifest_verify_detects_tampering(tmp_path):
    blm, tree = _mini_tree(tmp_path)
    with open(tree / blm.FROZEN_LOG, "a") as f:
        f.write("\n")  # any change to the locked log must be caught
    lines, ok = blm.verify_manifest(tree)
    assert not ok
    assert any("frozen_log.sha256: MISMATCH" in line for line in lines)


# ---------------------------------------------------------------- H2
def _scoring_frames():
    sp = _load_script("score_predictions")
    log = pd.DataFrame([
        {"match_id": mid, "stage": "P1", "team_1_name": "A", "team_2_name": "B",
         "p_team_1_win": 0.6, "p_elo": 0.55}
        for mid in ("m_super_elim", "m_super_winner", "m_dls", "m_nores", "m_tie")])

    def m(date, winner, status, **kw):
        d = {"season": "S3", "match_date": date, "team_1_name": "A",
             "team_2_name": "B", "winner_name": winner,
             "innings_2_team": "B", "result_status": status}
        d.update(kw)
        return d
    matches = pd.DataFrame([
        m("2026-10-26", None, "tie", eliminator="B"),   # super over, decider in eliminator
        m("2026-10-27", "B", "tie"),                    # super over, winner recorded
        m("2026-10-28", "A", "DLS (D/L)"),              # DLS result, declared winner
        m("2026-10-29", None, "no result"),             # abandoned
        m("2026-10-30", None, "tie"),                   # tied, no decider
    ])
    fixtures = pd.DataFrame([
        {"match_id": mid, "match_date": d, "team_1_name": "A", "team_2_name": "B"}
        for mid, d in zip(("m_super_elim", "m_super_winner", "m_dls",
                           "m_nores", "m_tie"),
                          ("2026-10-26", "2026-10-27", "2026-10-28",
                           "2026-10-29", "2026-10-30"))])
    return sp, sp.build_scored(log, matches, fixtures)


def test_outcome_classification_rules():
    _, sdf = _scoring_frames()
    cls = dict(zip(sdf["match_id"], sdf["outcome_classification"]))
    assert cls["m_super_elim"] == MET.OUTCOME_SCORED
    assert cls["m_super_winner"] == MET.OUTCOME_SCORED
    assert cls["m_dls"] == MET.OUTCOME_SCORED
    assert cls["m_nores"] == MET.OUTCOME_EXCLUDED_NO_RESULT
    assert cls["m_tie"] == MET.OUTCOME_EXCLUDED_TIED
    y = dict(zip(sdf["match_id"], sdf["actual_team_1_win"]))
    assert y["m_super_elim"] == 0 and y["m_super_winner"] == 0 and y["m_dls"] == 1
    assert pd.isna(y["m_nores"]) and pd.isna(y["m_tie"])
    reasons = dict(zip(sdf["match_id"], sdf["exclusion_reason"]))
    assert reasons["m_nores"] and reasons["m_tie"]  # never silently dropped


def test_metrics_ignore_excluded_matches():
    sp, sdf = _scoring_frames()
    by_stage = sp.metrics_by_stage(sdf)
    # G1: grouped by canonical horizon; stored string "P1" -> P1_CONFIRMED_XI
    assert by_stage["P1_CONFIRMED_XI"]["n"] == 3  # only the three scored matches
    assert by_stage["P1_CONFIRMED_XI"]["stage"] == "P1"
    summary = sp.outcome_classification_summary(sdf)
    assert summary["counts"]["scored"]["matches"] == 3
    assert summary["counts"]["excluded_no_result"]["matches"] == 1
    assert summary["counts"]["excluded_tied_no_decider"]["matches"] == 1
    assert {e["match_id"] for e in summary["excluded_matches"]} == {"m_nores", "m_tie"}


# ---------------------------------------------------------------- H3
def test_dashboard_xi_data_quality_on_real_files():
    from src.dashboard.page_modules import match_predictions as mp
    master = pd.read_csv(PRED / "player_master.csv")
    priors = pd.read_csv(PRED / "player_priors.csv")
    dq = mp.expected_xi_unresolved(master, priors)
    assert set(dq) == set(priors["team"].unique()) and len(dq) == 8
    # independent recomputation straight from the two source files
    from src.prediction import engine
    unresolved = set(master.loc[master["cricsheet_registry_id"].isna(),
                                "player_key"])
    for team, squad in priors.groupby("team"):
        xi = engine.select_expected_xi(squad)
        assert dq[str(team)] == sum(1 for k in xi if k in unresolved)
    # the two players resolved in H4 must no longer be counted anywhere
    assert "player_charith_asalanka" not in unresolved
    assert "player_sahan_arachchige" not in unresolved
    assert "not a validated high-accuracy predictor" in mp.STANDING_LABEL


def test_dashboard_page_renders_with_label(tmp_path):
    from streamlit.testing.v1 import AppTest
    script = tmp_path / "render_mp.py"
    script.write_text(
        "import sys\nsys.path.insert(0, r'%s')\n"
        "from src.dashboard.page_modules.match_predictions import "
        "render_match_predictions\nrender_match_predictions()\n" % ROOT)
    at = AppTest.from_file(str(script), default_timeout=180).run()
    assert not at.exception
    assert any("Prospective evaluation" in w.value for w in at.warning)
    assert any("XI data quality" in list(df.value.columns)
               for df in at.dataframe)


# ---------------------------------------------------------------- H4
def test_resolution_log_integrity():
    log_path = PRED / "player_resolution_log.csv"
    assert log_path.exists()
    log = pd.read_csv(log_path)
    master = pd.read_csv(PRED / "player_master.csv")
    by_key = master.set_index("player_key")
    assert len(log) == 2
    for _, r in log.iterrows():
        assert isinstance(r["evidence"], str) and len(r["evidence"]) > 50
        row = by_key.loc[r["player_key"]]
        assert row["cricsheet_registry_id"] == r["resolved_id"]
        assert row["registry_id_matched_name"] == r["registry_matched_name"]
        assert "cricsheet_registry_id" not in str(row["missing_fields"])
    assert master["cricsheet_registry_id"].isna().sum() == 23
