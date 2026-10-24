#!/usr/bin/env python
"""Canonical Elo outputs (Task 5): per-match history, S3-start current
ratings, and the walk-forward tuning table. Engine: src/prediction/elo.py."""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.prediction import elo  # noqa: E402

if __name__ == "__main__":
    matches = pd.read_parquet(ROOT / "data/normalized/matches_normalized.parquet")
    out = ROOT / "data" / "predictions"
    out.mkdir(parents=True, exist_ok=True)
    hist = elo.compute_history(matches)
    hist.to_csv(out / "elo_history.csv", index=False)
    cur = elo.current_ratings(matches)
    pd.DataFrame([{"team": t, "rating_s3_start": round(r, 1)}
                  for t, r in sorted(cur.items(), key=lambda x: -x[1])]
                 ).to_csv(out / "team_ratings_current.csv", index=False)
    best, table = elo.tune_walk_forward(matches, ks=range(20, 33, 4),
                                        regressions=(0.25, 0.33, 0.40))
    table.to_csv(out / "elo_tuning.csv", index=False)
    print("tuned best (within research ranges):", best)
    print(pd.DataFrame([{"team": t, "rating_s3_start": round(r, 1)}
                        for t, r in sorted(cur.items(), key=lambda x: -x[1])]).to_string(index=False))
