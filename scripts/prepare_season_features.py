"""Per-bowler per-season phase features from ball-by-ball data.

Target definition (unified with scripts/audit_model_comparison.py):
  legal ball  = extras_type NOT IN ('wides', 'noballs')
  bowler runs = runs_off_bat + runs_extras, except byes/legbyes
                deliveries where bowler runs = runs_off_bat only
  economy     = bowler_runs / legal_balls * 6
All three phases (powerplay, middle, death) are aggregated: the
middle overs are 46% of NPL balls and were previously dropped from
the "overall economy" entirely (audit A1/A5, 2026-11-12).

A bowler with no legal balls in a phase gets NaN for that phase's
economy, never 0.0: 0.0 would read as a perfect economy and poison
every downstream model (audit A6).

Input resolution (audit A7): the canonical normalized file is not
in the repo on a fresh clone, so when it is absent we fall back to
the shipped final parquet (data/final/parquet/ball_by_ball.parquet),
the same fallback the dashboard loaders already use. The fallback
is logged, never silent.
"""
import os
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent


def _normalized_bbb() -> Path:
    return ROOT / "data" / "normalized" / "ball_by_ball_normalized.parquet"


def _final_bbb() -> Path:
    return ROOT / "data" / "final" / "parquet" / "ball_by_ball.parquet"


def _normalized_matches() -> Path:
    return ROOT / "data" / "normalized" / "matches_normalized.parquet"


def _final_matches() -> Path:
    return ROOT / "data" / "final" / "parquet" / "matches.parquet"


def resolve_ball_parquet() -> Path:
    """Canonical normalized file if present, else the shipped final parquet."""
    if _normalized_bbb().exists():
        return _normalized_bbb()
    if _final_bbb().exists():
        print(f"Warning: {_normalized_bbb()} not found (fresh clone) — "
              f"falling back to {_final_bbb()}.")
        return _final_bbb()
    raise FileNotFoundError(
        f"Neither {_normalized_bbb()} nor {_final_bbb()} exists. "
        "Run the cricsheet ingest first (see README).")


def resolve_matches_parquet() -> Path:
    if _normalized_matches().exists():
        return _normalized_matches()
    if _final_matches().exists():
        print(f"Warning: {_normalized_matches()} not found — "
              f"falling back to {_final_matches()}.")
        return _final_matches()
    raise FileNotFoundError(
        f"Neither {_normalized_matches()} nor {_final_matches()} exists.")


def _bowler_runs(df: pd.DataFrame) -> pd.Series:
    """Runs charged to the bowler. Falls back to runs_total when the
    extras columns are absent (older normalized files)."""
    if {"runs_off_bat", "runs_extras", "extras_type"} <= set(df.columns):
        runs = df["runs_off_bat"] + df["runs_extras"]
        byes = df["extras_type"].isin(["byes", "legbyes"])
        runs = runs.where(~byes, df["runs_off_bat"])
        return runs
    print("Warning: extras columns missing; using runs_total as bowler runs.")
    return df["runs_total"]


def _legal_mask(df: pd.DataFrame) -> pd.Series:
    if "extras_type" in df.columns:
        return ~df["extras_type"].isin(["wides", "noballs"])
    return pd.Series(True, index=df.index)


def prepare(ball_parquet=None, matches_parquet=None, out_csv=None):
    ball_parquet = Path(ball_parquet) if ball_parquet else resolve_ball_parquet()
    matches_parquet = (Path(matches_parquet) if matches_parquet
                       else resolve_matches_parquet())
    out_csv = out_csv or os.path.join(ROOT, "data", "per_bowler_season_features.csv")
    balls = pd.read_parquet(ball_parquet)
    matches = pd.read_parquet(matches_parquet)
    # keep match_id -> season mapping
    match_season = matches[['match_id', 'season']]
    balls = balls.merge(match_season, on='match_id', how='left')
    balls["bowl_runs"] = _bowler_runs(balls)
    balls["is_legal"] = _legal_mask(balls)

    def agg_phase(df, phase_name):
        p = df[df['phase'].str.lower() == phase_name]
        legal = p[p["is_legal"]]
        g = legal.groupby(['bowler_name', 'season']).agg(
            balls=('ball', 'count'),
            dots=('is_dot_ball', 'sum'),
        ).reset_index()
        # Runs are summed over ALL deliveries in the phase: wides and
        # no-balls concede runs (counted here) but are not legal balls
        # (excluded from the balls count above). Byes/legbyes runs are
        # already excluded from bowl_runs.
        runs = (p.groupby(['bowler_name', 'season'])['bowl_runs'].sum()
                .reset_index().rename(columns={'bowl_runs': 'runs'}))
        g = g.merge(runs, on=['bowler_name', 'season'], how='left')
        # wickets can fall on wides/no-balls (e.g. stumped off a wide):
        # count them over all deliveries, not just legal ones.
        wk = p.groupby(['bowler_name', 'season'])['is_wicket'].sum().reset_index()
        g = g.merge(wk, on=['bowler_name', 'season'], how='left')
        g[f'{phase_name}_econ'] = g['runs'] / (g['balls'] / 6)
        g[f'{phase_name}_dot_pct'] = g['dots'] / g['balls'] * 100
        return g[['bowler_name', 'season', f'{phase_name}_econ',
                  f'{phase_name}_dot_pct', 'balls']].rename(
                      columns={'balls': f'{phase_name}_balls'})

    pp = agg_phase(balls, 'powerplay')
    mid = agg_phase(balls, 'middle')
    death = agg_phase(balls, 'death')

    merged = pp.merge(mid, on=['bowler_name', 'season'], how='outer')
    merged = merged.merge(death, on=['bowler_name', 'season'], how='outer')
    # Balls and dot% default to 0 when a bowler never bowled a phase;
    # economies stay NaN (a missing phase is unknown, not 0.0).
    for phase in ('powerplay', 'middle', 'death'):
        merged[f'{phase}_balls'] = merged[f'{phase}_balls'].fillna(0).astype(int)
        merged[f'{phase}_dot_pct'] = merged[f'{phase}_dot_pct'].fillna(0)
    merged = merged.rename(columns={'bowler_name': 'bowler'})
    merged.to_csv(out_csv, index=False)
    print('Wrote season features to', out_csv)


if __name__ == '__main__':
    prepare()
