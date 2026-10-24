#!/usr/bin/env python
"""Prediction refresh -- runs inside refresh_all.py AFTER Elo.

What it does (and does not do):
- Rebuilds canonical Elo outputs (ratings/history/tuning).
- If the cricsheet zip dir is available, rebuilds player history + priors
  (this is how player posteriors update after each S3 match lands: the
  in-season bundle ingest runs before refresh_all).
- Regenerates UNLOCKED upcoming-fixture probabilities.
- Re-scores the frozen log (read-only on the log).
- NEVER writes to, rewrites, or deletes frozen-log rows.
- Coefficients/champion are NOT refit here. Checkpoint rule: after S3
  matches 10 and 20, a refit may be PROPOSED (pooled Bayesian-style update)
  and is promoted only if it beats the frozen champion on since-checkpoint
  frozen-log log-loss. See docs/PREDICTION_SYSTEM.md.
"""
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

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
    matches = pd.read_parquet(ROOT / "data/normalized/matches_normalized.parquet")
    played = int((matches["season"] == "S3").sum())
    print(f"S3 matches played so far: {played}")
    if played in (10, 20):
        print(f"CHECKPOINT: {played} S3 matches played -- a coefficient "
              "refit may be proposed and promoted only under the "
              "checkpoint rule in docs/PREDICTION_SYSTEM.md.")
