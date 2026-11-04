"""Plan 1.2 — data/normalized is the canonical layer (criterion D4).

Before this change, data/final/parquet carried a stale second copy
of the match and delivery tables: innings summaries entirely
missing, and the Kathmandu franchise split across two spellings
("Gurkhas" in the final copy, "Gorkhas" in canonical normalized and
everywhere in the prediction system), so any page reading the final
copy silently fragmented one team into two. The final duplicates are
now regenerated from normalized by
scripts/sync_final_from_normalized.py, and derived final artefacts
carry the canonical spelling.
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
FINAL = ROOT / "data" / "final" / "parquet"
NORMALIZED = ROOT / "data" / "normalized"

TEAM_COLUMNS = {
    "matches.parquet": ["team_1_name", "team_2_name", "winner_name",
                        "toss_winner_name"],
    "ball_by_ball.parquet": ["batting_team", "bowling_team"],
    "match_lineups.parquet": ["team_name"],
    "player_innings.parquet": ["team_name"],
}


def _team_names() -> set[str]:
    names: set[str] = set()
    for filename, columns in TEAM_COLUMNS.items():
        df = pd.read_parquet(FINAL / filename)
        for column in columns:
            names |= set(df[column].dropna().unique())
    return names


def test_served_data_has_exactly_eight_teams() -> None:
    names = _team_names()
    assert len(names) == 8, names
    assert "Kathmandu Gorkhas" in names
    assert "Kathmandu Gurkhas" not in names


def test_served_matches_team_ids_are_canonical() -> None:
    final = pd.read_parquet(FINAL / "matches.parquet")
    ids = set(final["team_1_id"].dropna()) | set(final["team_2_id"].dropna())
    assert len(ids) == 8, ids
    assert "team_kathmandu_gorkhas" in ids
    assert "team_kathmandu_gurkhas" not in ids


def test_final_matches_equal_normalized() -> None:
    final = pd.read_parquet(FINAL / "matches.parquet")
    canonical = pd.read_parquet(NORMALIZED / "matches_normalized.parquet")
    assert len(final) == len(canonical) == 76
    merged = final.merge(canonical, on="match_id", suffixes=("_f", "_n"))
    for column in ("team_1_name", "team_2_name", "winner_name"):
        a, b = merged[f"{column}_f"], merged[f"{column}_n"]
        assert ((a == b) | (a.isna() & b.isna())).all(), column
    # Innings summaries are populated now. Runs equal canonical's
    # stored values (they agree with the deliveries on all innings);
    # overs follow the NRR convention derived from the canonical
    # ball-by-ball (CONF-003: canonical's stored overs do not).
    assert merged["innings_1_runs_n"].notna().all()
    assert (merged["innings_1_runs_f"] == merged["innings_1_runs_n"]).all()
    deliveries = pd.read_parquet(
        NORMALIZED / "ball_by_ball_normalized.parquet")
    bbb = deliveries[deliveries["innings"] <= 2].copy()
    bbb["legal"] = ~bbb["extras_type"].isin(["wides", "noballs"])
    bbb["wkt"] = bbb["is_wicket"] & (bbb["dismissal_type"] != "retired hurt")
    agg = (bbb.groupby(["match_id", "innings"])
           .agg(legal=("legal", "sum"), wkts=("wkt", "sum")))
    final_idx = final.set_index("match_id")
    for (match_id, inn), r in agg.iterrows():
        expected = 20.0 if r["wkts"] >= 10 else r["legal"] / 6.0
        assert final_idx.loc[match_id, f"innings_{inn}_overs"] == expected
