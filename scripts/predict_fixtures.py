#!/usr/bin/env python
"""Generate upcoming-fixture probabilities; optionally lock them into the
frozen log and/or emit post-toss P2 from a toss CSV
(columns: match_id, toss_winner_name, toss_decision)."""
import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.prediction import engine  # noqa: E402
from src.prediction import model as M  # noqa: E402
import json  # noqa: E402

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--lock", metavar="STAGE", help="lock into frozen log under this stage")
    ap.add_argument("--toss-csv", help="toss results CSV for P2")
    args = ap.parse_args()
    preds = engine.generate_predictions(ROOT)
    out = ROOT / "data/predictions/upcoming_predictions.csv"
    preds.to_csv(out, index=False)
    print(f"{len(preds)} fixture predictions -> {out}")
    if args.lock:
        n = engine.lock_predictions(ROOT, preds, args.lock)
        print(f"locked {n} new predictions at stage {args.lock}")
    if args.toss_csv:
        chase = json.loads((ROOT / "data/predictions/model_v1.json").read_text())["chase"]
        toss = pd.read_csv(args.toss_csv)
        rows = []
        for _, t in toss.iterrows():
            p = preds[preds.match_id == t.match_id]
            if not len(p):
                continue
            p = p.iloc[0]
            # P2 goes through the engine's contract-checked path: it
            # refuses without a valid toss winner + decision (R2a).
            p2 = engine.p2_probability(float(p.p_team_1_win), p.team_1_name,
                                       p.team_2_name, t.toss_winner_name,
                                       t.toss_decision, chase)
            rows.append({"match_id": t.match_id, "team_1_name": p.team_1_name,
                         "team_2_name": p.team_2_name, "p_team_1_win": round(p2, 4),
                         "p_elo": p.p_elo, "p_logistic_challenger": p.p_logistic_challenger,
                         "features_json": p.features_json})
        if rows:
            n = engine.lock_predictions(ROOT, pd.DataFrame(rows), "P2")
            print(f"locked {n} P2 predictions")
