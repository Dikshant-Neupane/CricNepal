#!/usr/bin/env python
"""Out-of-sample evaluation of the IN-PLAY win-probability system.

This evaluates src/analytics/win_probability_model.py as its own system
(review fix R2c): the model is trained on Season 1 deliveries ONLY and
scored on Season 2 deliveries it never saw. The production training
behaviour in refresh_all (train on all data) is NOT changed -- this is
an evaluation harness only.

The resulting numbers are DELIVERY-LEVEL, IN-PLAY metrics: each delivery
is one sample, and late-innings states are near-determined, so accuracy
and log-loss here are structurally NOT comparable to the pre-match
(P1) or toss-adjusted (P2) metrics, which are one sample per match
before a ball is bowled. The output JSON carries that warning in its
header and the dashboard labels it the same way.

Output: data/predictions/inplay_wp_evaluation.json
"""
import json
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.analytics import win_probability_model as wp  # noqa: E402
from src.prediction.metrics import score_all  # noqa: E402

HEADER_NOTE = ("IN-PLAY, delivery-level metrics (one sample per delivery, "
               "model trained on Season 1, scored on Season 2). These "
               "numbers are NOT comparable to the pre-match (P1) or "
               "toss-adjusted (P2) metrics: in-play states include "
               "near-determined late-innings positions, so delivery-level "
               "accuracy/log-loss are structurally more flattering than "
               "one-prediction-per-match pre-match scores.")

if __name__ == "__main__":
    matches = pd.read_parquet(ROOT / "data/normalized/matches_normalized.parquet")
    bb = pd.read_parquet(ROOT / "data/normalized/ball_by_ball_normalized.parquet")
    season_by_match = matches.set_index("match_id")["season"].to_dict()
    bb = bb.assign(season=bb["match_id"].map(season_by_match))
    m_s1 = matches[matches["season"] == "S1"]
    m_s2 = matches[matches["season"] == "S2"]
    bb_s1 = bb[bb["season"] == "S1"]
    bb_s2 = bb[bb["season"] == "S2"]

    model = wp.WinProbabilityModel()
    # train() dumps joblib files into wp.MODEL_DIR; redirect that to a
    # temp dir so the evaluation never touches production artefacts.
    with tempfile.TemporaryDirectory() as td:
        wp.MODEL_DIR = Path(td)
        model.train(bb_s1, m_s1)
        states = model.build_match_states(bb_s2, m_s2)
        states = states[states["match_winner"].notna()].copy()
        states["p_win"] = model.predict_delivery_probs(states)

    def block(df):
        s = score_all(df["p_win"], df["is_batting_team_winner"])
        s["n_deliveries"] = int(len(df))
        s["n_matches"] = int(df["match_id"].nunique())
        return s

    out = {
        "system": "in_play_win_probability",
        "header_note": HEADER_NOTE,
        "comparable_to_prematch_metrics": False,
        "unit_of_scoring": "delivery",
        "train_season": "S1", "test_season": "S2",
        "model": "src/analytics/win_probability_model.py (LogisticRegression, "
                 "innings-1 and innings-2 models, state features only)",
        "overall": block(states),
        "by_innings": {str(inn): block(g) for inn, g in states.groupby("innings")},
        "notes": "Delivery-level accuracy counts every delivery as an "
                 "independent sample although deliveries within a match are "
                 "highly correlated; treat it as a state-quality diagnostic, "
                 "not as evidence about pre-match forecasting skill.",
    }
    dest = ROOT / "data/predictions/inplay_wp_evaluation.json"
    dest.write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))
