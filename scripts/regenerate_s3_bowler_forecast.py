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

Export restriction (2026-11-13, user decision): the EXPORT excludes
bowlers with no S1 or S2 history (s1_balls == 0 and s2_balls == 0).
Those 59 rows in the 2026-11-13 run are bowlers who only appear in S3,
so their projection is just the phase prior — no evidence behind it —
and 21 Middle ones sat inside the 92-row workhorse list. The core
function forecast_bowlers_phase_aware still returns all rows for
analysis and tests; only the shipped export is restricted. See
restrict_export() below.
"""

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.analytics.s3_performance_forecaster import forecast_bowlers_phase_aware

K = 60


def restrict_export(df: pd.DataFrame) -> pd.DataFrame:
    """Rows the shipped export carries: bowlers with S1 or S2 balls.

    Excludes S3-only bowlers (s1_balls == 0 and s2_balls == 0), whose
    projection is just the phase prior with no history behind it.
    This is an export-only filter — forecast_bowlers_phase_aware
    still returns all rows, so analysis and tests see the full set.
    """
    return df[(df["s1_balls"] > 0) | (df["s2_balls"] > 0)].reset_index(drop=True)


def main() -> None:
    bbb = pd.read_parquet(ROOT / "data" / "final" / "parquet" / "ball_by_ball.parquet")
    matches = pd.read_parquet(ROOT / "data" / "final" / "parquet" / "matches.parquet")
    n_s3_matches = int((matches["season"] == "S3").sum())
    print(f"ball-by-ball rows: {len(bbb)}; matches: S3={n_s3_matches} (partial season)")

    out = forecast_bowlers_phase_aware(bbb, matches, k=K)
    out = out.sort_values(["bowler_name", "phase"]).reset_index(drop=True)
    s3_only = int(((out["s1_balls"] == 0) & (out["s2_balls"] == 0)).sum())
    export = restrict_export(out)

    target = ROOT / "data" / "exports" / "s3_phase_bowler_forecast.csv"
    export.to_csv(target, index=False)
    print(
        f"Wrote {len(export)} rows to {target} (k={K}; function rows: "
        f"{len(out)}; S3-only prior rows excluded from export: {s3_only})"
    )

    bohara = export[(export["bowler_name"] == "A Bohara") & (export["phase"] == "Death")]
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
