#!/usr/bin/env python3
"""Simple-logistic in-play baseline (plan task 5.3, criterion V3).

The master prompt requires the in-play win-probability model to be
reported against a simple logistic baseline on three state features:

    runs needed, balls left, wickets in hand   (innings 2 only)

Protocol mirrors the existing in-play evaluation
(scripts/evaluate_inplay_wp.py): train on Season 1, score on Season 2,
one sample per delivery, state measured after each delivery (the same
convention as WinProbabilityModel.build_match_states). Evaluation
only — nothing here feeds any live prediction path.

Outputs:
    data/predictions/inplay_baseline_evaluation.json
    data/predictions/inplay_baseline_s2_predictions.csv
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.prediction import metrics as pm  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
BBB = ROOT / "data/normalized/ball_by_ball_normalized.parquet"
MATCHES = ROOT / "data/normalized/matches_normalized.parquet"


def innings2_states() -> pd.DataFrame:
    bb = pd.read_parquet(BBB)
    m = pd.read_parquet(MATCHES)[["match_id", "season", "winner_name"]]
    bb = bb.merge(m, on="match_id", how="left")
    bb = bb.sort_values(["match_id", "innings", "ball_sequence"])
    g = bb.groupby(["match_id", "innings"])
    bb["runs_cum"] = g["runs_total"].cumsum()
    bb["wkts_cum"] = g["is_wicket"].cumsum()
    bb["is_legal"] = ~bb["extras_type"].isin(["wides", "noballs"])
    bb["legal_cum"] = bb.groupby(["match_id", "innings"])[
        "is_legal"].cumsum()
    inn1 = (bb[bb.innings == 1].groupby("match_id")["runs_total"].sum()
            .rename("inn1_total"))
    bb = bb.merge(inn1, on="match_id", how="left")
    ch = bb[bb.innings == 2].copy()
    ch["runs_needed"] = ch["inn1_total"] + 1 - ch["runs_cum"]
    ch["balls_left"] = 120 - ch["legal_cum"]
    ch["wickets_in_hand"] = 10 - ch["wkts_cum"]
    ch["y"] = (ch["batting_team"] == ch["winner_name"]).astype(float)
    # decided states carry no information for a baseline comparison
    ch = ch[(ch.runs_needed > 0) & (ch.balls_left > 0)
            & (ch.wickets_in_hand > 0)]
    return ch[["match_id", "season", "runs_needed", "balls_left",
               "wickets_in_hand", "y"]]


def main() -> int:
    st = innings2_states()
    feats = ["runs_needed", "balls_left", "wickets_in_hand"]
    tr = st[st.season == "S1"]
    te = st[st.season == "S2"].copy()
    model = LogisticRegression(C=1.0, max_iter=1000)
    model.fit(tr[feats], tr["y"])
    te["p"] = model.predict_proba(te[feats])[:, 1]
    out = {
        "system": "inplay_simple_logistic_baseline",
        "features": feats,
        "train_season": "S1", "test_season": "S2",
        "unit_of_scoring": "delivery",
        "innings": 2,
        "comparable_to_prematch_metrics": False,
        "overall": pm.score_all(te["p"], te["y"]),
        "coefficients": {f: float(c) for f, c in
                         zip(feats, model.coef_[0])},
        "intercept": float(model.intercept_[0]),
        "notes": "Baseline required by the master prompt Section 5 "
                 "for the in-play WP model. Compare against "
                 "inplay_wp_evaluation.json innings-2 delivery-level "
                 "numbers only.",
    }
    (ROOT / "data/predictions/inplay_baseline_evaluation.json"
     ).write_text(json.dumps(out, indent=2))
    te[["match_id", "runs_needed", "balls_left", "wickets_in_hand",
        "p", "y"]].to_csv(
        ROOT / "data/predictions/inplay_baseline_s2_predictions.csv",
        index=False)
    print(json.dumps(out["overall"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
