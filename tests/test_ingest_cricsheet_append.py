"""Regression tests for scripts/ingest_cricsheet.py --append mode.

Found by the 2026-10-22 S3 dry-run: appending to the production parquets
crashed on schema drift (production match_date holds datetime.date
objects, all-null columns carry degenerate dtypes, timestamps are real
datetimes), and player_innings / phase_summary were never maintained.
These tests build production-shaped parquets in a tmp dir and append a
minimal synthetic cricsheet match.
"""
import importlib.util
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location(
    "ingest_cricsheet", ROOT / "scripts" / "ingest_cricsheet.py")
ingest = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ingest)


def _mini_match_json():
    """One innings of two overs; Team A 14/1, small but schema-complete."""
    def dlv(batter, bowler, ns, br, er=0, wk=None):
        d = {"batter": batter, "bowler": bowler, "non_striker": ns,
             "runs": {"batter": br, "extras": er, "total": br + er}}
        if wk:
            d["wickets"] = [wk]
        return d
    overs = [
        {"over": 0, "deliveries": [
            dlv("A One", "B One", "A Two", 4), dlv("A One", "B One", "A Two", 1),
            dlv("A Two", "B One", "A One", 0,
                wk={"kind": "bowled", "player_out": "A Two"}),
            dlv("A Three", "B One", "A One", 2), dlv("A Three", "B One", "A One", 1),
            dlv("A One", "B One", "A Three", 6)]},
        {"over": 1, "deliveries": [
            dlv("A Three", "B Two", "A One", 0), dlv("A Three", "B Two", "A One", 0),
            dlv("A Three", "B Two", "A One", 0), dlv("A Three", "B Two", "A One", 0),
            dlv("A Three", "B Two", "A One", 0), dlv("A Three", "B Two", "A One", 0)]},
    ]
    return {"meta": {"data_version": "1.0"},
            "info": {"dates": ["2026-10-27"], "teams": ["Team A", "Team B"],
                     "toss": {"winner": "Team A", "decision": "bat"},
                     "outcome": {"winner": "Team A", "by": {"runs": 14}},
                     "event": {"name": "Nepal Premier League", "match_number": 99},
                     "venue": "TU Ground", "city": "Kirtipur", "gender": "male",
                     "match_type": "T20", "player_of_match": ["A One"],
                     "players": {"Team A": ["A One", "A Two", "A Three"],
                                 "Team B": ["B One", "B Two"]},
                     "registry": {"people": {}}},
            "innings": [{"team": "Team A", "overs": overs}]}


def _production_matches():
    """One existing row carrying the production parquet's type quirks."""
    prod = pd.read_parquet(ROOT / "data/final/parquet/matches.parquet").head(1)
    return prod


def _production_bbb():
    return pd.read_parquet(ROOT / "data/final/parquet/ball_by_ball.parquet").head(50)


@pytest.fixture()
def project(tmp_path, monkeypatch):
    pdir = tmp_path / "parquet"
    pdir.mkdir(parents=True)
    _production_matches().to_parquet(pdir / "matches.parquet", index=False)
    _production_bbb().to_parquet(pdir / "ball_by_ball.parquet", index=False)
    # production-shaped empty derived tables
    for name in ("player_innings", "phase_summary"):
        pd.read_parquet(ROOT / "data/final/parquet" / f"{name}.parquet").head(0).to_parquet(
            pdir / f"{name}.parquet", index=False)
    jdir = tmp_path / "incoming"
    jdir.mkdir()
    (jdir / "9990002.json").write_text(json.dumps(_mini_match_json()))
    monkeypatch.setattr(ingest, "PARQUET_DIR", pdir)
    monkeypatch.setattr(sys, "argv", ["ingest", str(jdir), "--append"])
    return pdir


def test_append_matches_production_schema(project):
    ingest.main()
    m = pd.read_parquet(project / "matches.parquet")
    assert len(m) == 2
    s3 = m[m.match_id == "espn_9990002"].iloc[0]
    assert s3.season == "S3"
    assert s3.match_date == date(2026, 10, 27)  # date object, not str
    assert s3.innings_1_runs == 14
    assert isinstance(s3.ingestion_timestamp, datetime)


def test_append_is_idempotent_and_continues_sequence(project):
    ingest.main()
    b1 = pd.read_parquet(project / "ball_by_ball.parquet")
    ingest.main()
    b2 = pd.read_parquet(project / "ball_by_ball.parquet")
    assert len(b2) == len(b1) == 50 + 12
    assert b2.ball_sequence.is_unique
    assert b2.ball_sequence.max() == 50 + 12


def test_append_derives_player_innings_and_phase_summary(project):
    ingest.main()
    pi = pd.read_parquet(project / "player_innings.parquet")
    fx = pi[pi.match_id == "espn_9990002"]
    one = fx[(fx.player_name == "A One") & (fx.player_role == "batter")].iloc[0]
    assert one.runs_scored == 11 and one.balls_faced == 3  # 4+1+6, faced all
    assert one.dismissed is False or one.dismissed == False  # noqa: E712
    bowler = fx[(fx.player_name == "B One") & (fx.player_role == "bowler")].iloc[0]
    assert bowler.wickets_taken == 1 and bowler.balls_bowled == 6
    assert bowler.economy_rate == pytest.approx(14.0)
    two = fx[(fx.player_name == "A Two")].iloc[0]
    assert bool(two.dismissed) is True and two.dismissal_phase == "Powerplay"
    ps = pd.read_parquet(project / "phase_summary.parquet")
    pp = ps[(ps.match_id == "espn_9990002") & (ps.phase == "Powerplay")].iloc[0]
    assert pp.balls_bowled == 12 and pp.runs_scored == 14.0 and pp.wickets == 1.0
