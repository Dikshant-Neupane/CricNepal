#!/usr/bin/env python3
"""Validate a hand-entered scorecard (fast lane) before it is trusted.

Reads the capture-pack files in data/capture/ (or paths given on the
command line) for one match and checks, per innings, that the entry
CLOSES arithmetically:

  1. sum(batter runs) + all extras == innings total
  2. counted dismissals == innings wickets (<= 10); a dismissal counts
     unless it is 'not out' or 'retired hurt'
  3. sum(bowler runs conceded) + byes + leg-byes == innings total
     (bowlers are charged wides/no-ball penalties, never byes)
  4. sum(bowler balls) == legal balls implied by total_overs
  5. batting positions are 1..N with no duplicates, <= 11 rows

Usage:
  python scripts/scorecard_check.py --match-id S3-M03 \
      [--facts data/capture/match_facts.csv] \
      [--batting data/capture/scorecard_batting.csv] \
      [--bowling data/capture/scorecard_bowling.csv]
Exit code 0 = every check passed for every innings in match_facts.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
NON_WICKET = {"not out", "retired hurt", "did not bat", ""}


def overs_to_balls(overs: float) -> int:
    whole = int(overs)
    return whole * 6 + round((overs - whole) * 10)


def check_innings(facts: pd.Series, bat: pd.DataFrame, bowl: pd.DataFrame) -> list[str]:
    problems = []
    extras = (facts.extras_byes + facts.extras_legbyes + facts.extras_wides
              + facts.extras_noballs + facts.extras_penalty)
    bat_runs = int(bat.runs.sum())
    if bat_runs + int(extras) != int(facts.total_runs):
        problems.append(
            f"batting closure: batters {bat_runs} + extras {int(extras)} "
            f"!= total {int(facts.total_runs)}")
    dism = bat.dismissal_type.fillna("").str.strip().str.lower()
    wkts = int((~dism.isin(NON_WICKET)).sum())
    if wkts != int(facts.total_wickets):
        problems.append(f"wickets: counted dismissals {wkts} != {int(facts.total_wickets)}")
    if int(facts.total_wickets) > 10:
        problems.append("wickets exceed 10")
    bowl_runs = int(bowl.runs_conceded.sum())
    if bowl_runs + int(facts.extras_byes) + int(facts.extras_legbyes) != int(facts.total_runs):
        problems.append(
            f"bowling closure: bowlers {bowl_runs} + byes {int(facts.extras_byes)} "
            f"+ leg-byes {int(facts.extras_legbyes)} != total {int(facts.total_runs)}")
    legal = overs_to_balls(float(facts.total_overs))
    bowled = int(bowl.balls_bowled.sum())
    if bowled != legal:
        problems.append(f"balls: bowlers bowled {bowled} != legal balls {legal} "
                        f"from {facts.total_overs} overs")
    pos = bat.batting_pos.tolist()
    if len(pos) > 11 or sorted(pos) != list(range(1, len(pos) + 1)):
        problems.append(f"batting positions invalid: {sorted(pos)}")
    return problems


def validate(match_id: str, facts_p: Path, bat_p: Path, bowl_p: Path) -> int:
    facts = pd.read_csv(facts_p)
    bat = pd.read_csv(bat_p)
    bowl = pd.read_csv(bowl_p)
    rows = facts[facts.match_id == match_id]
    if rows.empty:
        print(f"FAIL: no match_facts rows for {match_id}")
        return 1
    failed = 0
    for _, f in rows.iterrows():
        b = bat[(bat.match_id == match_id) & (bat.innings == f.innings)]
        w = bowl[(bowl.match_id == match_id) & (bowl.innings == f.innings)]
        problems = check_innings(f, b, w)
        if problems:
            failed += 1
            print(f"FAIL innings {int(f.innings)}:")
            for p in problems:
                print(f"  - {p}")
        else:
            print(f"PASS innings {int(f.innings)}: entry closes "
                  f"({int(f.total_runs)}/{int(f.total_wickets)} in {f.total_overs} overs)")
    return 1 if failed else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--match-id", required=True)
    ap.add_argument("--facts", default=str(ROOT / "data/capture/match_facts.csv"))
    ap.add_argument("--batting", default=str(ROOT / "data/capture/scorecard_batting.csv"))
    ap.add_argument("--bowling", default=str(ROOT / "data/capture/scorecard_bowling.csv"))
    a = ap.parse_args()
    return validate(a.match_id, Path(a.facts), Path(a.batting), Path(a.bowling))


if __name__ == "__main__":
    sys.exit(main())
