#!/usr/bin/env python
"""Prediction refresh -- runs inside refresh_all.py AFTER Elo.

What it does (and does not do):
- Rebuilds canonical Elo outputs (ratings/history/tuning).
- If the cricsheet zip dir is available, rebuilds player history + priors
  (this is how player posteriors update after each S3 match whose
  cricsheet data has been published and ingested: the in-season bundle
  ingest runs before refresh_all). Cricsheet publication lags the match
  itself -- measured on Season 2 at a median of 8 days -- so updates
  follow publication, not the final ball. See "Data publication lag"
  in docs/PREDICTION_SYSTEM.md.
- Writes data/predictions/predictions_status.json: the as-of stamp
  (latest published match date in the normalized data + matches
  ingested) that the dashboard displays as "Ratings as of". The stamp
  is a sidecar: upcoming_predictions.csv probabilities are NOT touched
  by it (that file mirrors locked/expected probabilities and must stay
  byte-stable between refreshes of the same data).
- Regenerates UNLOCKED upcoming-fixture probabilities. Ratings for
  those forecasts are provisional-aware (engine.load_context): any
  winner-only provisional results in data/results/provisional_
  results.csv advance ratings across the cricsheet lag, and the
  status sidecar reports the basis (Amendment #6).
- Re-scores the frozen log (read-only on the log).
- NEVER writes to, rewrites, or deletes frozen-log rows.
- Coefficients/champion are NOT refit here. Checkpoint rule: after S3
  matches 10 and 20, a refit may be PROPOSED (pooled Bayesian-style update)
  and is promoted only if it beats the frozen champion on since-checkpoint
  frozen-log log-loss. See docs/PREDICTION_SYSTEM.md.
"""
import datetime
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.prediction import provisional as PV  # noqa: E402


def write_predictions_status(root: Path = ROOT) -> dict:
    """As-of stamp for everything the refresh produces (F3 fix).

    data_as_of = the maximum match date present in the normalized
    matches (i.e. the latest match cricsheet has published and we have
    ingested); n_matches_ingested = rows in that table. Written to
    data/predictions/predictions_status.json, which the dashboard
    reads for its "Ratings as of" line. This NEVER rewrites
    upcoming_predictions.csv -- its probabilities stay byte-stable;
    only the sidecar stamp moves.
    """
    matches = pd.read_parquet(root / "data/normalized/matches_normalized.parquet")
    dates = pd.to_datetime(matches["match_date"])
    # Provisional state (Amendment #6): winner-only manual results
    # bridge the publication lag. The same reconciliation the ratings
    # use is reported here: how many provisional results are currently
    # applied on top of canonical data, which have been superseded by
    # ingested cricsheet records, and any winner disagreement between
    # a provisional capture and the canonical record (a data-quality
    # WARNING -- surfaced, never silently resolved, never fatal).
    fixtures_path = root / "data/fixtures/s3_fixtures.csv"
    prov = PV.load_provisional(root)
    if fixtures_path.exists():
        rec = PV.reconcile(matches, pd.read_csv(fixtures_path), prov)
    else:  # minimal synthetic tree: no fixtures, nothing to reconcile
        rec = {"applied": [], "superseded": [], "disagreements": []}
    for d in rec["disagreements"]:
        print(f"WARNING (provisional): {d['match_id']}: {d['issue']} "
              f"(provisional: {d.get('provisional_winner')}, "
              f"ingested: {d.get('ingested_winner')})")
    status = {
        "data_as_of": str(dates.max().date()),
        "n_matches_ingested": int(len(matches)),
        "matches_by_season": {str(k): int(v) for k, v in
                              matches["season"].value_counts()
                              .sort_index().items()},
        "generated_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        "ratings_basis": "canonical+provisional" if rec["applied"]
                         else "canonical",
        "n_provisional": len(rec["applied"]),
        "latest_provisional_match_date":
            max((e["match_date"] for e in rec["applied"]), default=None),
        "provisional_applied_match_ids":
            [e["match_id"] for e in rec["applied"]],
        "provisional_superseded_match_ids":
            [e["match_id"] for e in rec["superseded"]],
        "provisional_disagreements": rec["disagreements"],
        "note": "Ratings, priors and regenerated forecasts reflect "
                "matches published by cricsheet and ingested as of "
                "data_as_of. Cricsheet publication lags real time "
                "(Season 2 measured median: 8 days), so this date can "
                "trail the latest played match. Winner-only provisional "
                "results (Amendment #6) advance ratings across the lag "
                "with a neutral margin multiplier; canonical cricsheet "
                "data supersedes them on arrival.",
    }
    out = root / "data/predictions/predictions_status.json"
    out.write_text(json.dumps(status, indent=1))
    return status

if __name__ == "__main__":
    py = sys.executable
    def run(script, *a):
        r = subprocess.run([py, str(ROOT / script), *a], capture_output=True, text=True)
        tail = (r.stdout.strip().splitlines() or [""])[-1]
        print(f"[{script}] {tail}")
        if r.returncode != 0:
            print(r.stdout[-2000:], r.stderr[-2000:])
    run("scripts/build_team_ratings.py")
    import os
    zip_dir = Path(os.environ.get("CRICSHEET_ZIP_DIR", ROOT.parent / ".scratch" / "predbuild"))
    if zip_dir.exists():
        run("scripts/build_player_master.py")
        run("scripts/build_player_priors.py")
    else:
        print("cricsheet zip dir not found -- player priors left as-is")
    run("scripts/predict_fixtures.py")
    run("scripts/score_predictions.py")
    status = write_predictions_status()
    print(f"[predictions_status] ratings as of {status['data_as_of']} "
          f"({status['n_matches_ingested']} matches ingested)")
    matches = pd.read_parquet(ROOT / "data/normalized/matches_normalized.parquet")
    played = int((matches["season"] == "S3").sum())
    print(f"S3 matches played so far: {played}")
    if played in (10, 20):
        print(f"CHECKPOINT: {played} S3 matches played -- a coefficient "
              "refit may be proposed and promoted only under the "
              "checkpoint rule in docs/PREDICTION_SYSTEM.md.")
