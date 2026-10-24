"""Tests for the provisional-results policy (Amendment #6).

Provisional results are winner-only manual captures (official source,
timestamped) that bridge the cricsheet publication lag. Canonical
cricsheet data is the source of truth: on ingestion a provisional row
is superseded; a winner disagreement is flagged, never fatal; MOV
for provisional matches is the neutral 1.0 (no margin captured).

All tests run on synthetic temp trees -- production data is only
read, never written (the lock test asserts the production frozen
log's hash is unchanged across a temp-tree lock).
"""
import hashlib
import importlib.util
import json
import shutil
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.prediction import elo as E  # noqa: E402
from src.prediction import engine  # noqa: E402
from src.prediction import provisional as PV  # noqa: E402

PRED = ROOT / "data" / "predictions"
FIXTURES = pd.read_csv(ROOT / "data/fixtures/s3_fixtures.csv")
MATCH_COLS = ["match_id", "season", "match_date", "team_1_name",
              "team_2_name", "winner_name", "innings_1_runs",
              "innings_2_runs"]


def _script(name):
    spec = importlib.util.spec_from_file_location(
        name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _prov_row(match_id, winner, source="CAN official post",
              captured="2026-10-26T19:05:00+05:45"):
    row = {c: "" for c in PV.PROVISIONAL_COLUMNS}
    row.update({"match_id": match_id, "winner_team_name": winner,
                "source": source, "captured_at": captured,
                "status": "provisional", "superseded_by_cricsheet": "false"})
    return row


def _root_with_fixtures(tmp_path):
    (tmp_path / "data/fixtures").mkdir(parents=True)
    FIXTURES.to_csv(tmp_path / "data/fixtures/s3_fixtures.csv", index=False)
    return tmp_path


# ---------------------------------------------------------- record_result
def test_record_result_validation(tmp_path):
    rr = _script("record_result")
    root = _root_with_fixtures(tmp_path)
    fx = FIXTURES[FIXTURES.match_id == "s3_2026_01"].iloc[0]
    with pytest.raises(ValueError):
        rr.record_result(root, "s3_2026_99", fx.team_1_name, "CAN")
    with pytest.raises(ValueError):
        rr.record_result(root, "s3_2026_01", "Not A Team", "CAN")
    with pytest.raises(ValueError):
        rr.record_result(root, "s3_2026_01", fx.team_1_name, "  ")
    row = rr.record_result(root, "s3_2026_01", fx.team_1_name,
                           "CAN official post",
                           captured_at="2026-10-26T20:00:00+05:45")
    assert row["status"] == "provisional"
    assert row["margin_runs"] == "" and row["margin_wickets"] == ""
    assert row["superseded_by_cricsheet"] == "false"
    # duplicate refused...
    with pytest.raises(ValueError):
        rr.record_result(root, "s3_2026_01", fx.team_2_name, "CAN")
    # ...unless it is an explicit correction, appended as a new row
    rr.record_result(root, "s3_2026_01", fx.team_2_name, "NPL broadcast",
                     captured_at="2026-10-26T21:00:00+05:45",
                     supersede_correction="first capture named the loser")
    eff = PV.effective_rows(PV.load_provisional(root))
    assert len(eff) == 1
    assert eff.iloc[0]["winner_team_name"] == fx.team_2_name
    assert eff.iloc[0]["correction_of"] == "s3_2026_01"


# ---------------------------------------------------------- ratings math
def test_provisional_ratings_math_by_hand():
    fixtures = pd.DataFrame([{
        "match_id": "fx1", "season": "S3", "match_date": "2026-10-26",
        "team_1_name": "A", "team_2_name": "B"}])
    prov = pd.DataFrame([_prov_row("fx1", "A")])
    empty = pd.DataFrame(columns=MATCH_COLS)
    ratings, info = PV.ratings_with_provisional(
        empty, fixtures, prov, base={"A": 1500.0, "B": 1500.0})
    # even match, MOV = 1.0 (neutral): delta = K * 1.0 * (1 - 0.5) = 10
    assert ratings["A"] == pytest.approx(1510.0)
    assert ratings["B"] == pytest.approx(1490.0)
    assert info["ratings_basis"] == "canonical+provisional"
    assert info["n_provisional_applied"] == 1
    # asymmetric: underdog win moves more, by exactly K*(1-E)
    ratings2, _ = PV.ratings_with_provisional(
        empty, fixtures, pd.DataFrame([_prov_row("fx1", "B")]),
        base={"A": 1600.0, "B": 1500.0})
    e_b = E.expected(1500.0, 1600.0)
    assert ratings2["B"] == pytest.approx(1500.0 + 20.0 * (1 - e_b))
    assert ratings2["A"] == pytest.approx(1600.0 - 20.0 * (1 - e_b))
    # no provisional rows -> canonical, ratings untouched
    ratings3, info3 = PV.ratings_with_provisional(
        empty, fixtures, pd.DataFrame(columns=PV.PROVISIONAL_COLUMNS),
        base={"A": 1500.0, "B": 1500.0})
    assert ratings3 == {"A": 1500.0, "B": 1500.0}
    assert info3["ratings_basis"] == "canonical"


# ------------------------------------------------- supersession / flagging
def _ingested_for(fixture_row, winner):
    return pd.DataFrame([{
        "match_id": "ing_1", "season": "S3",
        "match_date": fixture_row["match_date"],
        "team_1_name": fixture_row["team_1_name"],
        "team_2_name": fixture_row["team_2_name"],
        "winner_name": winner,
        "innings_1_runs": None, "innings_2_runs": None}], columns=MATCH_COLS)


def test_supersession_and_disagreement_flag():
    fx = FIXTURES[FIXTURES.match_id == "s3_2026_01"].iloc[0]
    fixtures = FIXTURES[FIXTURES.match_id == "s3_2026_01"]
    matches = _ingested_for(fx, fx.team_1_name)
    # provisional winner DISAGREES with the ingested winner
    prov = pd.DataFrame([_prov_row("s3_2026_01", fx.team_2_name)])
    ratings, info = PV.ratings_with_provisional(matches, fixtures, prov)
    # canonical wins: provisional ignored, ratings are the canonical base
    assert ratings == PV.base_ratings(matches, fixtures)
    assert info["n_provisional_applied"] == 0
    assert info["superseded_match_ids"] == ["s3_2026_01"]
    assert len(info["provisional_disagreements"]) == 1  # flagged, not fatal
    # agreeing provisional: superseded, no disagreement
    prov2 = pd.DataFrame([_prov_row("s3_2026_01", fx.team_1_name)])
    _, info2 = PV.ratings_with_provisional(matches, fixtures, prov2)
    assert info2["superseded_match_ids"] == ["s3_2026_01"]
    assert info2["provisional_disagreements"] == []


# ------------------------------------------- lock_matchday basis (temp tree)
def test_lock_matchday_records_provisional_basis(tmp_path):
    lm = _script("lock_matchday")
    for sub in ("data/normalized", "data/predictions", "data/fixtures",
                "data/results"):
        (tmp_path / sub).mkdir(parents=True, exist_ok=True)
    shutil.copy(ROOT / "data/normalized/matches_normalized.parquet",
                tmp_path / "data/normalized/matches_normalized.parquet")
    for f in ("player_priors.csv", "model_v1.json", "frozen_log.csv"):
        shutil.copy(PRED / f, tmp_path / "data/predictions" / f)
    shutil.copy(ROOT / "data/fixtures/s3_fixtures.csv",
                tmp_path / "data/fixtures/s3_fixtures.csv")
    fx1 = FIXTURES[FIXTURES.match_id == "s3_2026_01"].iloc[0]
    pd.DataFrame([_prov_row("s3_2026_01", fx1.team_1_name)]).to_csv(
        tmp_path / "data/results/provisional_results.csv", index=False)

    prod_hash_before = hashlib.md5(
        (PRED / "frozen_log.csv").read_bytes()).hexdigest()
    ctx = engine.load_context(tmp_path)
    assert ctx["provisional_info"]["n_provisional_applied"] == 1
    assert ctx["provisional_info"]["ratings_basis"] == "canonical+provisional"
    xi = {t: ctx["xi_by_team"][t] for t in
          ("Janakpur Bolts", "Karnali Yaks")}
    frame = lm.compute_p1_post_xi(tmp_path, "s3_2026_03", xi, ctx=ctx)
    n = engine.lock_predictions(tmp_path, frame, "P1_post_XI",
                                model_version="v1.1")
    assert n == 1
    log = pd.read_csv(tmp_path / "data/predictions/frozen_log.csv")
    row = log[(log.match_id == "s3_2026_03") & (log.stage == "P1_post_XI")]
    assert len(row) == 1
    feats = json.loads(row.iloc[0]["features_json"])
    assert feats["ratings_basis"] == "canonical+provisional"
    assert feats["n_provisional_applied"] == 1
    assert feats["data_as_of"] == "2025-12-13"
    # the production frozen log was never touched
    assert hashlib.md5((PRED / "frozen_log.csv").read_bytes()).hexdigest() \
        == prod_hash_before


# ------------------------------------------------------- status sidecar
def test_status_sidecar_provisional_fields(tmp_path):
    rp = _script("refresh_predictions")
    for sub in ("data/normalized", "data/fixtures", "data/results",
                "data/predictions"):
        (tmp_path / sub).mkdir(parents=True, exist_ok=True)
    shutil.copy(ROOT / "data/normalized/matches_normalized.parquet",
                tmp_path / "data/normalized/matches_normalized.parquet")
    shutil.copy(ROOT / "data/fixtures/s3_fixtures.csv",
                tmp_path / "data/fixtures/s3_fixtures.csv")
    rows = []
    for mid in ("s3_2026_01", "s3_2026_02"):
        fx = FIXTURES[FIXTURES.match_id == mid].iloc[0]
        rows.append(_prov_row(mid, fx.team_1_name))
    pd.DataFrame(rows).to_csv(
        tmp_path / "data/results/provisional_results.csv", index=False)
    st = rp.write_predictions_status(tmp_path)
    assert st["n_provisional"] == 2
    assert st["ratings_basis"] == "canonical+provisional"
    assert st["latest_provisional_match_date"] == "2026-10-27"
    assert st["data_as_of"] == "2025-12-13"
    # and with no provisional file at all: canonical, zeros
    (tmp_path / "data/results/provisional_results.csv").unlink()
    st2 = rp.write_predictions_status(tmp_path)
    assert st2["n_provisional"] == 0
    assert st2["ratings_basis"] == "canonical"
    assert st2["latest_provisional_match_date"] is None


# ------------------------------------------- production state stays clean
def test_production_provisional_file_is_empty_and_canonical():
    prov = PV.load_provisional(ROOT)
    assert len(PV.effective_rows(prov)) == 0  # header only: no results yet
    ctx = engine.load_context(ROOT)
    assert ctx["provisional_info"]["ratings_basis"] == "canonical"
    assert ctx["provisional_info"]["n_provisional_applied"] == 0
