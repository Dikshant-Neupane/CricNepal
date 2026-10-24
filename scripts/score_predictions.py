#!/usr/bin/env python
"""Score locked predictions in the frozen log against landed results.

Matches S3 results (normalized parquet) to fixtures by date + team pair.
Writes data/predictions/scorecard.csv and prints metrics per stage vs the
Elo baseline stored in the log and a chase-heuristic baseline (expanding
S1+S2 chase win rate = 52.4%). Coarse calibration bins only (32 matches
cannot support finer)."""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.prediction.metrics import score_all  # noqa: E402

BINS = [(0.0, 0.4), (0.4, 0.5), (0.5, 0.6), (0.6, 0.8), (0.8, 1.01)]

if __name__ == "__main__":
    log_path = ROOT / "data/predictions/frozen_log.csv"
    if not log_path.exists():
        print("No frozen log yet -- nothing to score.")
        sys.exit(0)
    log = pd.read_csv(log_path)
    matches = pd.read_parquet(ROOT / "data/normalized/matches_normalized.parquet")
    s3 = matches[matches["season"] == "S3"].copy()
    fixtures = pd.read_csv(ROOT / "data/fixtures/s3_fixtures.csv")
    fx_by_key = {}
    for _, f in fixtures.iterrows():
        if isinstance(f["team_1_name"], str) and f["team_1_name"]:
            fx_by_key[(f["match_date"], tuple(sorted([f["team_1_name"], f["team_2_name"]])))] = f["match_id"]
    res_by_id = {}
    for _, m in s3.iterrows():
        key = (str(m["match_date"]), tuple(sorted([m["team_1_name"], m["team_2_name"]])))
        if key in fx_by_key:
            res_by_id[fx_by_key[key]] = m
    scored = []
    for _, r in log.iterrows():
        m = res_by_id.get(r["match_id"])
        if m is None or not isinstance(m["winner_name"], str):
            continue
        y = 1 if m["winner_name"] == r["team_1_name"] else 0
        chase_p = 0.524 if m["innings_2_team"] == r["team_1_name"] else 1 - 0.524
        scored.append({**{c: r[c] for c in ("match_id", "stage", "team_1_name", "team_2_name")},
                       "p_team_1_win": r["p_team_1_win"], "p_elo": r["p_elo"],
                       "p_chase_baseline": chase_p, "actual_team_1_win": y,
                       "winner": m["winner_name"]})
    out = ROOT / "data/predictions/scorecard.csv"
    if not scored:
        pd.DataFrame(columns=["match_id", "stage", "team_1_name", "team_2_name",
                              "p_team_1_win", "p_elo", "p_chase_baseline",
                              "actual_team_1_win", "winner"]).to_csv(out, index=False)
        print("Frozen log has no scored predictions yet (no S3 results landed).")
        sys.exit(0)
    sdf = pd.DataFrame(scored)
    sdf.to_csv(out, index=False)
    for stage, g in sdf.groupby("stage"):
        y = g["actual_team_1_win"].to_numpy()
        print(f"[{stage}] n={len(g)}")
        for name, col in (("model", "p_team_1_win"), ("elo_baseline", "p_elo"),
                          ("chase_baseline", "p_chase_baseline"), ):
            s = score_all(g[col], y)
            print(f"  {name:16s} acc={s['accuracy']:.3f} logloss={s['log_loss']:.4f} brier={s['brier']:.4f}")
        print("  calibration bins (predicted mean vs actual rate):")
        for lo, hi in BINS:
            b = g[(g.p_team_1_win >= lo) & (g.p_team_1_win < hi)]
            if len(b):
                print(f"    [{lo:.1f},{hi:.1f}) n={len(b)} pred={b.p_team_1_win.mean():.3f} actual={b.actual_team_1_win.mean():.3f}")
