"""Plan 1.5 — player_of_match is populated from the cricsheet bundle.

The canonical table shipped null 64/64 although the cricsheet NPL
bundle carries info.player_of_match for every match and the ingest
captures it. Populated 2026-10-29 by
scripts/populate_player_of_match.py with the ingest's own semantics
(first listed name, raw cricsheet surface form; id = "player_" +
lowercased name with underscores). Spot values below are read from
the bundle itself (1462596.json, 1462640.json, 1462642.json).
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent


def _matches() -> pd.DataFrame:
    return pd.read_parquet(
        ROOT / "data/normalized/matches_normalized.parquet")


def test_player_of_match_populated_for_all_matches() -> None:
    df = _matches()
    assert df["player_of_match"].notna().all()
    assert df["player_of_match_id"].notna().all()


def test_player_of_match_spot_values_match_the_bundle() -> None:
    df = _matches().set_index("match_id")
    assert df.loc["espn_1462596", "player_of_match"] == "BKEL Milantha"
    assert df.loc["espn_1462640", "player_of_match"] == "Sohail Tanvir"
    assert df.loc["espn_1462642", "player_of_match"] == "DS Airee"
    assert (df.loc["espn_1462596", "player_of_match_id"]
            == "player_bkel_milantha")


def test_player_of_match_id_is_the_ingest_slug() -> None:
    df = _matches()
    expected = ("player_" + df["player_of_match"].str.strip().str.lower()
                .str.replace(" ", "_"))
    assert (df["player_of_match_id"] == expected).all()
