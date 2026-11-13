"""Recompute the roster scorecard bowling columns under the legal-ball
definition (pinned 2026-11-13).

    python scripts/recompute_roster_legal_ball_economies.py

Why: the roster (data/player_rosters/npl_player_rosters_20260521.csv)
recorded scorecard economies as runs_total over ALL deliveries bowled
(wides and no-balls counted as balls, bye/legbye runs counted against
the bowler). The forecaster now uses the proper legal-ball definition
(bowler runs / legal balls * 6), so the roster input to
scripts/regenerate_s3_forecasts.py is recomputed on the same basis:

    bowler runs  = runs_off_bat + runs_extras, except byes/legbyes
                   deliveries where bowler runs = runs_off_bat only
    balls bowled = legal balls (extras_type not in wides/noballs)
    economy_rate = bowler runs / legal balls * 6

For each S1/S2 roster row with balls_bowled > 0 this rewrites
runs_conceded, balls_bowled, overs_bowled (= round(legal/6, 1), the
roster's existing convention) and economy_rate (= round(..., 2)),
from the shipped ball-by-ball data
(data/final/parquet/ball_by_ball.parquet + matches.parquet). All 179
bowling rows match a (bowler_name, season) group in that data, and
wickets_taken already agrees with it exactly, so no row is dropped
and no name is unmatched. S3 rows carry no stats yet and are
untouched; batting columns are untouched.

The canonical roster (npl_player_rosters_canonical.csv) gets the
same four columns rewritten on its S1/S2 rows: it is NOT regenerated
here via scripts/build_player_registry.py, because that builder's
output currently differs from the dated roster on S3 rows (421 vs
391 rows), and re-running it would mix this definition change with
unrelated S3 churn.

Pinned by tests/test_legal_ball_2026_11_13.py, which recomputes the
economies from the ball-by-ball data independently.
"""

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

ROSTER = ROOT / "data" / "player_rosters" / "npl_player_rosters_20260521.csv"
CANONICAL = ROOT / "data" / "player_rosters" / "npl_player_rosters_canonical.csv"


def legal_ball_aggregates() -> pd.DataFrame:
    """Per (bowler_name, season) legal balls and bowler runs, S1+S2."""
    bbb = pd.read_parquet(ROOT / "data" / "final" / "parquet" / "ball_by_ball.parquet")
    matches = pd.read_parquet(ROOT / "data" / "final" / "parquet" / "matches.parquet")[
        ["match_id", "season"]
    ]
    b = bbb.merge(matches, on="match_id", how="left")
    b = b[b["season"].isin(["S1", "S2"])].copy()
    b["is_legal"] = ~b["extras_type"].isin(["wides", "noballs"])
    b["bowl_runs"] = b["runs_off_bat"] + b["runs_extras"]
    byes = b["extras_type"].isin(["byes", "legbyes"])
    b.loc[byes, "bowl_runs"] = b.loc[byes, "runs_off_bat"]
    agg = (
        b.groupby(["bowler_name", "season"])
        .agg(legal_balls=("is_legal", "sum"), bowl_runs=("bowl_runs", "sum"))
        .reset_index()
    )
    return agg


def rewrite(path: Path, agg: pd.DataFrame) -> dict:
    """Rewrite the four bowling columns on S1/S2 rows with balls > 0."""
    roster = pd.read_csv(path)
    roster["season_key"] = roster["season"].str.replace("Season ", "S")
    merged = roster.merge(
        agg, left_on=["player_name", "season_key"],
        right_on=["bowler_name", "season"], how="left",
        suffixes=("", "_agg"),
    )
    mask = (merged["balls_bowled"] > 0) & merged["season_key"].isin(["S1", "S2"])
    unmatched = merged[mask & merged["legal_balls"].isna()]
    if len(unmatched):
        raise SystemExit(
            f"{path.name}: {len(unmatched)} bowling rows have no "
            "ball-by-ball group; refusing to rewrite. "
            f"First: {unmatched[['player_name', 'season']].head().to_dict('records')}"
        )
    old_econ = merged.loc[mask, "economy_rate"].astype(float)
    new_econ = (
        merged.loc[mask, "bowl_runs"] / merged.loc[mask, "legal_balls"] * 6
    ).round(2)
    delta = (new_econ - old_econ).abs()
    merged.loc[mask, "runs_conceded"] = merged.loc[mask, "bowl_runs"].astype(int)
    merged.loc[mask, "balls_bowled"] = merged.loc[mask, "legal_balls"].astype(int)
    merged.loc[mask, "overs_bowled"] = (merged.loc[mask, "legal_balls"] / 6).round(1)
    merged.loc[mask, "economy_rate"] = new_econ
    out = merged.drop(columns=["season_key", "bowler_name", "season_agg",
                               "legal_balls", "bowl_runs"])
    out.to_csv(path, index=False)
    return {
        "rows": int(mask.sum()),
        "changed_economy": int((delta > 0).sum()),
        "mean_abs_delta": round(float(delta.mean()), 3),
        "max_abs_delta": round(float(delta.max()), 3),
    }


def main() -> None:
    agg = legal_ball_aggregates()
    print(f"ball-by-ball bowler-seasons S1+S2: {len(agg)}")
    for path in (ROSTER, CANONICAL):
        stats = rewrite(path, agg)
        print(f"{path.name}: {stats}")
    khatri = pd.read_csv(ROSTER)
    print(khatri[khatri["player_name"] == "Bipin Khatri"][
        ["season", "balls_bowled", "runs_conceded", "economy_rate"]
    ].to_string(index=False))


if __name__ == "__main__":
    main()
