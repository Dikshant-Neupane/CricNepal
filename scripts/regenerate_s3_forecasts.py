"""Regenerate the S3 bowler and batter forecasts (pinned 2026-11-13).

Generation step for data/exports/s3_bowler_forecast.csv,
data/exports/s3_batter_forecast.csv and the NPL_Grade_A/B/C_Targets.csv
files:

    python scripts/regenerate_s3_forecasts.py

Method: S3PerformanceForecaster on the in-repo roster
(data/player_rosters/npl_player_rosters_20260521.csv), S1/S2 splits,
exactly as the archived scripts/archive/run_s3_forecaster.py did —
except the input path is repo-relative (the archive hardcoded
D:/Cric_Data/...) and its sys.path insert pointed at a directory
that does not exist. The forecaster class's own main() is a
commented-out placeholder, so this script is the only live writer.

Why regenerate now (2026-11-13): the shipped files predate commit
bcad4f1, which fixed analyze_trend() — the CATASTROPHIC_DECLINE
branch was unreachable dead code because DECLINING was checked
first. The prediction drift is exactly 6 rows, all steep decliners
(pct_change < -80) that now take the -0.4 recovery instead of -0.5:
K Mahato s3_wickets_pred 7.92 -> 6.75, and 5 batters (BKEL
Milantha, D Bohara, JA Kolsawala, P Shrestha, Shankar Rana) whose
priority moves 2 -> 0 (CAUTION -> DO NOT RETAIN). Separately, the
bowler confidence-interval strings change on ~20 rows: the shipped
ranges used flat 15% margins, while the current v2.2 code uses
magnitude-and-volatility margins (economy max(0.5, 12% of pred,
0.4 x volatility); wickets max(2.0, 25% of pred, 0.5 x volatility)).
No grade file changes: K Mahato stays Grade C (composite 33.6 ->
30.5, priority 3 either way) and the grade files keep 12 / 5 / 2
rows, range strings aside.

Deliberately NOT changed here: the forecaster's inputs are the
roster scorecard economies (runs_conceded / balls_bowled x 6,
all-phase). Switching inputs to the corrected legal-ball economies
(mean |difference| 0.28) is a separate definition change — see the
audit open questions — and would move grades (e.g. Bipin Khatri
Grade A -> Grade A/B). This script pins reproducibility of the
current code only.
"""

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.analytics.s3_performance_forecaster import S3PerformanceForecaster

ROSTER = ROOT / "data" / "player_rosters" / "npl_player_rosters_20260521.csv"
EXPORT_DIR = ROOT / "data" / "exports"


def load_and_prepare_data():
    """Load the roster and split into S1 and S2, as the archived writer did."""
    df = pd.read_csv(ROSTER)
    df["season_num"] = df["season"].astype(str).str.replace("Season ", "").astype(int)
    s1_data = df[df["season_num"] == 1].copy()
    s2_data = df[df["season_num"] == 2].copy()

    column_mapping = {
        "playing_role": "role",
        "runs_scored": "runs",
        "wickets_taken": "wickets",
        "economy_rate": "economy",
    }
    for data in (s1_data, s2_data):
        for col, new_col in column_mapping.items():
            if col in data.columns:
                data.rename(columns={col: new_col}, inplace=True)
        # Batting average = runs / dismissals (dismissals approximated
        # by batting matches, as the archived writer did).
        data["average"] = data["runs"] / data["batting_matches"].replace(0, 1)
        data["average"] = data["average"].fillna(0)
        if "bowling_matches" not in data.columns:
            data["bowling_matches"] = data.apply(
                lambda row: 8 if (not pd.isna(row.get("wickets", float("nan"))) and row.get("wickets", 0) > 0) else 0,
                axis=1,
            )
        if "balls_bowled" not in data.columns and "overs_bowled" in data.columns:
            data["balls_bowled"] = data["overs_bowled"] * 6
    return s1_data, s2_data


def write_grade_files(bowlers: pd.DataFrame) -> dict:
    """Grade target files, same filters as the archived writer."""
    written = {}
    for grade in ("Grade A", "Grade B", "Grade C"):
        subset = bowlers[bowlers["npl_grade"].str.contains(grade, na=False)].sort_values(
            "priority", ascending=False
        )
        target = EXPORT_DIR / f"NPL_Grade_{grade.split()[-1]}_Targets.csv"
        subset.to_csv(target, index=False)
        written[grade] = len(subset)
    return written


def main() -> None:
    s1_data, s2_data = load_and_prepare_data()
    print(f"Roster: S1={len(s1_data)} S2={len(s2_data)} records from {ROSTER}")
    forecaster = S3PerformanceForecaster(s1_data, s2_data)
    results = forecaster.generate_full_forecast(export_path=str(EXPORT_DIR))
    grades = write_grade_files(results["bowlers"])
    print(f"Bowler forecast: {len(results['bowlers'])} players; "
          f"batter forecast: {len(results['batters'])} players")
    print(f"Grade files: {grades}")


if __name__ == "__main__":
    main()
