#!/usr/bin/env python
"""Record a PROVISIONAL result (winner only) for a Season 3 fixture.

Provisional results bridge the cricsheet publication lag (Season 2
measured median: 8 days) so in-season ratings do not sit frozen at
pre-season values while results already exist. Policy:
docs/PREDICTION_SYSTEM.md, "Provisional results (source-of-truth
policy)"; Pre-registration Amendment #6.

Strict by design:
- match_id must exist in data/fixtures/s3_fixtures.csv;
- winner must be one of the two fixture teams;
- a source description (official source: CAN / NPL official post /
  broadcast) is required -- no source, no record;
- winner ONLY: no margin is captured (margin columns stay blank),
  so provisional matches move Elo with the neutral MOV = 1.0;
- one effective result per match: a duplicate is refused unless
  --supersede-correction "reason" is given, which appends a NEW row
  marked correction_of (the file is append-only; nothing is edited
  in place);
- captured_at defaults to now in Asia/Kathmandu.

Once the match is ingested from cricsheet, the canonical record wins:
the provisional row is reported as superseded and ignored by the
ratings computation (src/prediction/provisional.py). A provisional
winner that disagrees with the ingested winner is flagged as a
data-quality warning in the refresh status, never silently resolved.
"""
import argparse
import csv
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.prediction import provisional as PV  # noqa: E402


def kathmandu_now() -> datetime:
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("Asia/Kathmandu"))
    except Exception:  # no tzdata: Kathmandu is a fixed UTC+05:45
        return datetime.now(timezone(timedelta(hours=5, minutes=45)))


def record_result(root, match_id: str, winner: str, source: str,
                  captured_at: str | None = None,
                  supersede_correction: str | None = None) -> dict:
    """Validate and append one provisional result row. Returns the
    row written. Raises ValueError on any contract violation."""
    root = Path(root)
    fixtures = pd.read_csv(root / "data/fixtures/s3_fixtures.csv")
    fx = fixtures[fixtures["match_id"] == match_id]
    if not len(fx):
        raise ValueError(f"unknown match_id {match_id!r} "
                         f"(not in s3_fixtures.csv)")
    fx = fx.iloc[0]
    teams = (fx["team_1_name"], fx["team_2_name"])
    if winner not in teams:
        raise ValueError(f"winner {winner!r} is not one of the fixture "
                         f"teams {teams}")
    if not source or not str(source).strip():
        raise ValueError("a source description is required "
                         "(official source the result was captured from)")
    path = PV.provisional_path(root)
    existing = PV.load_provisional(root)
    eff = PV.effective_rows(existing)
    dup = eff[eff["match_id"] == match_id] if len(eff) else eff
    correction_of, correction_reason = "", ""
    if len(dup):
        if not supersede_correction:
            raise ValueError(
                f"a provisional result already exists for {match_id} "
                f"(winner: {dup.iloc[0]['winner_team_name']}). Refusing "
                f"a duplicate; pass --supersede-correction \"reason\" "
                f"to append a correction row instead.")
        correction_of, correction_reason = match_id, supersede_correction
    row = {"match_id": match_id, "winner_team_name": winner,
           "margin_runs": "", "margin_wickets": "",
           "source": str(source).strip(),
           "captured_at": captured_at or kathmandu_now().isoformat(timespec="seconds"),
           "status": "provisional", "superseded_by_cricsheet": "false",
           "correction_of": correction_of,
           "correction_reason": correction_reason}
    path.parent.mkdir(parents=True, exist_ok=True)
    new_file = not path.exists()
    with path.open("a", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=PV.PROVISIONAL_COLUMNS)
        if new_file:
            w.writeheader()
        w.writerow(row)
    return row


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--match-id", required=True)
    ap.add_argument("--winner", required=True,
                    help="exact fixture team name of the winner")
    ap.add_argument("--source", required=True,
                    help="official source description (CAN / NPL post / broadcast)")
    ap.add_argument("--captured-at",
                    help="ISO timestamp with timezone (default: now, Asia/Kathmandu)")
    ap.add_argument("--supersede-correction", metavar="REASON",
                    help="append a correction row for a match that "
                         "already has a provisional result")
    args = ap.parse_args()
    row = record_result(ROOT, args.match_id, args.winner, args.source,
                        captured_at=args.captured_at,
                        supersede_correction=args.supersede_correction)
    print(f"provisional result recorded: {row['match_id']} -> "
          f"{row['winner_team_name']} (captured {row['captured_at']}, "
          f"source: {row['source']})")
