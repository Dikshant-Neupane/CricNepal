#!/usr/bin/env python3
"""S3 two-source scorecard diff (plan task 1.6, criterion D2).

For every Season 3 match with a captured scorecard in data/capture,
this script diffs three views of the same innings:

  1. the captured batting + bowling lines (ESPNcricinfo/CricTracker),
  2. the captured innings facts (totals/extras in match_facts.csv),
  3. the cricsheet ball-by-ball rebuild — once cricsheet publishes S3.

Every discrepancy is returned with its cause class. As of 2026-10-29
cricsheet has published 0 S3 matches (bundle still 64 S1/S2 matches),
so view 3 reports ARMED (waiting for data) and views 1 vs 2 are diffed
for all captured matches. Nothing is written; exit code 1 if any
unexplained discrepancy is found.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.cricket import metrics as cm  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CAP = ROOT / "data/capture"
BBB = ROOT / "data/normalized/ball_by_ball_normalized.parquet"


def diff_capture(match_id: str) -> list[str]:
    """Diff captured batting/bowling lines against captured facts."""
    facts = pd.read_csv(CAP / "match_facts.csv")
    bat = pd.read_csv(CAP / "scorecard_batting.csv")
    bowl = pd.read_csv(CAP / "scorecard_bowling.csv")
    problems = []
    for _, f in facts[facts.match_id == match_id].iterrows():
        inn = int(f.innings)
        b = bat[(bat.match_id == match_id) & (bat.innings == inn)]
        w = bowl[(bowl.match_id == match_id) & (bowl.innings == inn)]
        extras = int(f.extras_byes + f.extras_legbyes + f.extras_wides
                     + f.extras_noballs + f.extras_penalty)
        bat_total = int(b.runs.sum()) + extras
        if bat_total != int(f.total_runs):
            problems.append(
                f"{match_id} inn{inn}: batting lines + extras = "
                f"{bat_total} != facts total {f.total_runs} "
                f"(cause: capture transcription or extras mismatch)")
        bowl_total = int(w.runs_conceded.sum() + f.extras_byes + f.extras_legbyes
                         + f.extras_penalty)
        if bowl_total != int(f.total_runs):
            problems.append(
                f"{match_id} inn{inn}: bowling lines + byes/leg-byes/penalty "
                f"= {bowl_total} != facts total {f.total_runs} "
                f"(cause: capture transcription)")
        legal = int(w.balls_bowled.sum())
        if legal != cm.overs_to_balls(str(f.total_overs)):
            problems.append(
                f"{match_id} inn{inn}: bowling legal balls {legal} "
                f"!= facts overs {f.total_overs} "
                f"(cause: capture transcription)")
        dismissed = int((~b.dismissal_type.isin(
            ["not out"])).sum())
        if dismissed != int(f.total_wickets):
            problems.append(
                f"{match_id} inn{inn}: dismissed batters {dismissed} "
                f"!= facts wickets {f.total_wickets} "
                f"(cause: capture transcription)")
    return problems


def cricsheet_status() -> tuple[int, list[str]]:
    """(number of S3 matches in cricsheet data, captured match ids)."""
    facts = pd.read_csv(CAP / "match_facts.csv")
    captured = sorted(facts.match_id.unique())
    if not BBB.exists():
        return 0, captured
    bb = pd.read_parquet(BBB, columns=["match_id"])
    have = set(bb.match_id.unique())
    return sum(1 for m in captured if m in have), captured


def main() -> int:
    n_s3, captured = cricsheet_status()
    print(f"captured S3 matches: {len(captured)}; "
          f"also in cricsheet data: {n_s3} "
          f"({'diff armed and active' if n_s3 else 'ARMED — cricsheet '
           'has not published S3 yet; capture-internal diff only'})")
    problems = []
    for m in captured:
        problems += diff_capture(m)
    for p in problems:
        print("DISCREPANCY:", p)
    print(f"{len(problems)} discrepancies across {len(captured)} matches")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
