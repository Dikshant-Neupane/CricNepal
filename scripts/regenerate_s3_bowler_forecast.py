"""Regenerate the S3 phase bowler forecast export.

Generation step for data/exports/s3_phase_bowler_forecast.csv (pinned
2026-11-13, after the audit found the shipped file was an orphan):

    python scripts/regenerate_s3_bowler_forecast.py

Method: forecast_bowlers_phase_aware with k=60 (the verified best
shrinkage constant; k=30/60/150 are indistinguishable, audit
2026-11-12) on the shipped ball-by-ball data
(data/final/parquet/ball_by_ball.parquet + matches.parquet).
S3 is partial (12 of 23 matches ingested as of 2026-11-12); the
projection uses S1+S2 only — S3 rows in the ball-by-ball file do
not enter any projection.

Known caveat, kept deliberately visible: the function iterates over
every (bowler, phase) group in the ball-by-ball file, so bowlers
who only appear in S3 get a row whose projection is just the phase
prior (59 rows in the 2026-11-13 run, 370 total vs 311 shipped).
Those rows carry s1_balls == s2_balls == 0 and no history; a
follow-up may restrict the export to bowlers with S1 or S2 balls.
Do not silently drop them here — the row count is part of the
regeneration record.
"""

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.analytics.s3_performance_forecaster import forecast_bowlers_phase_aware

K = 60


def main() -> None:
    bbb = pd.read_parquet(ROOT / "data" / "final" / "parquet" / "ball_by_ball.parquet")
    matches = pd.read_parquet(ROOT / "data" / "final" / "parquet" / "matches.parquet")
    n_s3_matches = int((matches["season"] == "S3").sum())
    print(f"ball-by-ball rows: {len(bbb)}; matches: S3={n_s3_matches} (partial season)")

    out = forecast_bowlers_phase_aware(bbb, matches, k=K)
    out = out.sort_values(["bowler_name", "phase"]).reset_index(drop=True)
    s3_only = int(((out["s1_balls"] == 0) & (out["s2_balls"] == 0)).sum())

    target = ROOT / "data" / "exports" / "s3_phase_bowler_forecast.csv"
    out.to_csv(target, index=False)
    print(f"Wrote {len(out)} rows to {target} (k={K}; S3-only prior rows: {s3_only})")

    bohara = out[(out["bowler_name"] == "A Bohara") & (out["phase"] == "Death")]
    if not bohara.empty:
        row = bohara.iloc[0]
        blend = round(0.4 * row["s1_economy_shrunk"] + 0.6 * row["s2_economy_shrunk"], 2)
        print(
            f"A Bohara Death: s1_balls={int(row['s1_balls'])} "
            f"s2_balls={int(row['s2_balls'])} proj={row['s3_economy_proj']} "
            f"blend={blend} match={blend == row['s3_economy_proj']}"
        )


if __name__ == "__main__":
    main()
