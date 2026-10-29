#!/usr/bin/env python3
"""Regenerate the data/final parquet copies from the canonical layer
(plan task 1.2).

data/normalized is CANONICAL (docs/DATA_DICTIONARY.md). The
data/final/parquet duplicates of the match and delivery tables had
drifted into a stale second source: innings summaries entirely
missing and the Kathmandu franchise split across two spellings
("Gurkhas" there, "Gorkhas" in canonical and in the whole prediction
system). This script makes the final copies exact copies of
canonical for the two duplicated tables, and aligns team identity in
the derived final artefacts (match_lineups, player_innings), which
have no normalized counterpart, by renaming variant spellings to the
canonical ones. No measurement is recomputed or altered.

One measurement wrinkle: normalized's STORED innings overs do not
follow the NRR convention — all-out innings are stored at the overs
actually faced instead of the full 20, and other innings use a
notation that disagrees with the legal-ball count (50 of 128 innings
differ; stored runs agree with the deliveries on all 128). Served
with the stored values, Janakpur's S1 NRR reads +0.492 instead of
the verified +0.139. The served matches copy therefore carries
innings summaries DERIVED from the canonical ball-by-ball with the
same convention the dashboard backfill has always applied
(legal-ball overs; all-out = 20 overs; super overs excluded) —
identical to the numbers the dashboard served before this sync.
Registered as CONF-003; the ingest-side fix is post-season.

Two identity wrinkles found during the 2026-10-29 sync, handled
here for the SERVED copies and registered in the conflicts register:
(1) normalized's own team_1_id/team_2_id columns carry both
Kathmandu IDs (team_kathmandu_gorkhas / team_kathmandu_gurkhas) —
the final copy aligns IDs to the canonical one, but the upstream
ingest still emits both (register entry; ingest-side fix is a
separate, post-season change — the canonical source is not patched
by hand mid-season). (2) player_innings carried a spacing variant
"Sudur Paschim Royals" for canonical "Sudurpaschim Royals".

Re-runnable: safe to run after every normalized rebuild.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
FINAL = ROOT / "data" / "final" / "parquet"
NORMALIZED = ROOT / "data" / "normalized"

CANONICAL_NAME = "Kathmandu Gorkhas"
VARIANT_NAME = "Kathmandu Gurkhas"
NAME_ALIASES = {VARIANT_NAME: CANONICAL_NAME,
                "Sudur Paschim Royals": "Sudurpaschim Royals"}
ID_ALIASES = {"team_kathmandu_gurkhas": "team_kathmandu_gorkhas"}
TEAM_COLUMNS = {
    "matches.parquet": ["team_1_name", "team_2_name", "winner_name",
                        "toss_winner_name"],
    "ball_by_ball.parquet": ["batting_team", "bowling_team"],
    "match_lineups.parquet": ["team_name"],
    "player_innings.parquet": ["team_name"],
}


def _align(df: pd.DataFrame, columns: list[str], aliases: dict) -> int:
    changed = 0
    for column in columns:
        if column not in df.columns:
            continue
        for variant, canonical in aliases.items():
            mask = df[column] == variant
            changed += int(mask.sum())
            df.loc[mask, column] = canonical
    return changed


def _derived_summaries(deliveries: pd.DataFrame) -> dict:
    """Innings summaries from deliveries, NRR convention (the same
    convention as src/dashboard/services/data_source's backfill):
    legal-ball overs, an all-out innings counts the full 20 overs,
    super-over innings (>2) excluded."""
    bbb = deliveries[deliveries["innings"] <= 2].copy()
    bbb["legal"] = ~bbb["extras_type"].isin(["wides", "noballs"])
    bbb["wkt"] = bbb["is_wicket"] & (bbb["dismissal_type"] != "retired hurt")
    agg = (bbb.groupby(["match_id", "innings", "batting_team"],
                       as_index=False)
           .agg(runs=("runs_total", "sum"), legal=("legal", "sum"),
                wkts=("wkt", "sum")))
    out = {}
    for r in agg.itertuples():
        overs = 20.0 if r.wkts >= 10 else r.legal / 6.0
        out[(r.match_id, r.innings)] = (r.batting_team, float(r.runs), overs)
    return out


def main() -> int:
    deliveries_all = pd.read_parquet(
        NORMALIZED / "ball_by_ball_normalized.parquet")
    summaries = _derived_summaries(deliveries_all)

    matches = pd.read_parquet(NORMALIZED / "matches_normalized.parquet")
    n_ids = _align(matches, ["team_1_id", "team_2_id"], ID_ALIASES)
    n_summ = 0
    for idx, row in matches.iterrows():
        for inn in (1, 2):
            rec = summaries.get((row["match_id"], inn))
            if rec is None:
                continue
            team, runs, overs = rec
            matches.at[idx, f"innings_{inn}_team"] = team
            matches.at[idx, f"innings_{inn}_runs"] = runs
            matches.at[idx, f"innings_{inn}_overs"] = overs
            n_summ += 1
    # Served-schema compatibility: the legacy served file stored
    # innings wickets as float64, and the cricsheet ingest's append
    # path aligns fresh rows against the served dtypes (a fresh
    # no-result row can carry NaN wickets, which a non-nullable int64
    # cast rejects). Keep the float dtype in the served projection;
    # canonical keeps int64.
    for col in ("innings_1_wickets", "innings_2_wickets"):
        matches[col] = matches[col].astype("float64")
    matches.to_parquet(FINAL / "matches.parquet", index=False)
    print(f"matches.parquet := normalized ({len(matches)} rows; "
          f"{n_ids} team-ID cells aligned to canonical; {n_summ} "
          "innings summaries derived from canonical ball-by-ball)")

    deliveries = pd.read_parquet(NORMALIZED / "ball_by_ball_normalized.parquet")
    deliveries.to_parquet(FINAL / "ball_by_ball.parquet", index=False)
    print(f"ball_by_ball.parquet := normalized ({len(deliveries)} rows)")

    for filename in ("match_lineups.parquet", "player_innings.parquet"):
        path = FINAL / filename
        df = pd.read_parquet(path)
        changed = _align(df, TEAM_COLUMNS[filename], NAME_ALIASES)
        df.to_parquet(path, index=False)
        print(f"{filename}: {changed} team-name cells aligned to canonical")

    names: set[str] = set()
    for filename, columns in TEAM_COLUMNS.items():
        df = pd.read_parquet(FINAL / filename)
        for column in columns:
            names |= set(df[column].dropna().unique())
    print(f"team names across served final layer: {len(names)} -> {sorted(names)}")
    if len(names) != 8 or VARIANT_NAME in names:
        print("ERROR: canonical check failed", file=sys.stderr)
        return 1
    served = pd.read_parquet(FINAL / "matches.parquet")
    ids = set(served["team_1_id"].dropna()) | set(served["team_2_id"].dropna())
    if "team_kathmandu_gurkhas" in ids or len(ids) != 8:
        print(f"ERROR: served team IDs not canonical: {sorted(ids)}",
              file=sys.stderr)
        return 1
    print(f"team IDs across served matches: {len(ids)} (canonical)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
