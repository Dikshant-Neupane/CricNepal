"""Plan task 9 (criteria D4, D6): ingest-layer fixes for CONF-002
and CONF-003. These change FUTURE ingest behaviour only; no stored
canonical row is patched here.

CONF-003: cricsheet ingest counted every delivery row (wides and
no-balls included) into the stored innings overs. Stored overs must
follow the NRR convention: legal balls only.
CONF-002: normalization unified team NAMES (Kathmandu Gurkhas ->
Gorkhas) but never the team-ID columns, leaving one franchise under
two IDs. The ID mapping is derived from the same name mapping.
"""
import importlib.util
import json
from pathlib import Path

import pandas as pd

from src.preprocessing.normalize_data import normalize_team_names

ROOT = Path(__file__).resolve().parent.parent


def _ingest():
    spec = importlib.util.spec_from_file_location(
        "ingest_cricsheet", ROOT / "scripts/ingest_cricsheet.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _dlv(batter_runs=0, extras=None, wicket=None):
    ex = extras or {}
    d = {"batter": "Bat One", "non_striker": "Bat Two",
         "bowler": "Bowl One",
         "runs": {"batter": batter_runs,
                  "extras": sum(ex.values()),
                  "total": batter_runs + sum(ex.values())}}
    if ex:
        d["extras"] = ex
    if wicket:
        d["wickets"] = [wicket]
    return d


def _synthetic_match(tmp_path):
    deliveries = [
        _dlv(1), _dlv(0, wicket={"kind": "bowled",
                                 "player_out": "Bat One"}),
        _dlv(4), _dlv(0, extras={"wides": 1}), _dlv(2),
        _dlv(0, extras={"noballs": 1}), _dlv(1), _dlv(0),
    ]  # 6 legal balls + 1 wide + 1 no-ball = 1.0 overs, 10 runs, 1 wkt
    data = {
        "info": {
            "teams": ["Team A", "Team B"],
            "dates": ["2026-01-01"],
            "toss": {"winner": "Team A", "decision": "field"},
            "outcome": {"winner": "Team B", "by": {"runs": 5}},
            "event": {"name": "Nepal Premier League", "match_number": 1},
            "players": {"Team A": ["Bat One", "Bat Two"],
                        "Team B": ["Bowl One"]},
        },
        "innings": [
            {"team": "Team A",
             "overs": [{"over": 0, "deliveries": deliveries}]},
            {"team": "Team B",
             "overs": [{"over": 0, "deliveries": [_dlv(6)]}]},
        ],
    }
    p = tmp_path / "999999.json"
    p.write_text(json.dumps(data))
    return p


def test_ingest_counts_legal_balls_only(tmp_path):
    mod = _ingest()
    row, deliveries, _lineups = mod.parse_match(
        _synthetic_match(tmp_path), "test_run")
    assert row["innings_1_overs"] == 1.0  # not 1.2 (8 rows)
    assert row["innings_1_runs"] == 10
    assert row["innings_1_wickets"] == 1
    # delivery rows themselves are all preserved
    assert len([d for d in deliveries if d["innings"] == 1]) == 8


def test_normalize_unifies_team_id_with_name():
    df = pd.DataFrame({
        "team_1_name": ["Kathmandu Gurkhas"],
        "team_1_id": ["team_kathmandu_gurkhas"],
        "team_2_name": ["Sudur Paschim Royals"],
        "team_2_id": ["team_sudur_paschim_royals"],
        "venue_id": ["team_kathmandu_gurkhas"],  # control: not a team col
    })
    out = normalize_team_names(df)
    assert out.loc[0, "team_1_name"] == "Kathmandu Gorkhas"
    assert out.loc[0, "team_1_id"] == "team_kathmandu_gorkhas"
    assert out.loc[0, "team_2_id"] == "team_sudurpaschim_royals"
    assert out.loc[0, "venue_id"] == "team_kathmandu_gurkhas"


def test_normalize_without_id_columns_still_works():
    df = pd.DataFrame({"team_1_name": ["Kathmandu Gurkhas"]})
    out = normalize_team_names(df)
    assert out.loc[0, "team_1_name"] == "Kathmandu Gorkhas"
