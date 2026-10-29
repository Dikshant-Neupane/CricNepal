#!/usr/bin/env python3
"""Paired bootstrap CI for the in-play WP model vs the simple baseline
(plan task 5.5, criterion V4).

Batch 1 (task 5.3) reported the innings-2 comparison as two aggregate
log-losses (WP model 0.4108 on 3,503 deliveries; 3-feature baseline
0.4137 on 3,471 undecided states) with no uncertainty on the
difference, and on slightly different state sets. This script puts
both systems on the SAME undecided innings-2 states (paired by match
and state), then bootstraps the per-match log-loss difference with
match-level resampling (deliveries within a match are correlated;
resampling deliveries would understate the interval).

Protocol mirrors scripts/evaluate_inplay_wp.py: WP model trained on
Season 1 only, scored on Season 2. Evaluation only.

Output: data/predictions/inplay_wp_vs_baseline_ci.json
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.analytics import win_probability_model as wp  # noqa: E402
from src.prediction.metrics import (  # noqa: E402
    paired_bootstrap,
    per_match_log_loss,
)


def main() -> int:
    matches = pd.read_parquet(ROOT / "data/normalized/matches_normalized.parquet")
    bb = pd.read_parquet(ROOT / "data/normalized/ball_by_ball_normalized.parquet")
    season_by_match = matches.set_index("match_id")["season"].to_dict()
    bb = bb.assign(season=bb["match_id"].map(season_by_match))
    m_s1, m_s2 = matches[matches["season"] == "S1"], matches[matches["season"] == "S2"]
    bb_s1, bb_s2 = bb[bb["season"] == "S1"], bb[bb["season"] == "S2"]

    model = wp.WinProbabilityModel()
    with tempfile.TemporaryDirectory() as td:
        wp.MODEL_DIR = Path(td)
        model.train(bb_s1, m_s1)
        states = model.build_match_states(bb_s2, m_s2)
        states = states[states["match_winner"].notna()].copy()
        states["p_win"] = model.predict_delivery_probs(states)

    inn2 = states[states["innings"] == 2].copy()
    inn2["wickets_in_hand"] = 10 - inn2["wickets_cumulative"]
    # The baseline's state set: undecided states only.
    inn2 = inn2[(inn2["runs_required"] > 0) & (inn2["balls_remaining"] > 0)
                & (inn2["wickets_in_hand"] > 0)]

    baseline = pd.read_csv(
        ROOT / "data/predictions/inplay_baseline_s2_predictions.csv")
    paired = inn2.merge(
        baseline,
        left_on=["match_id", "runs_required", "balls_remaining",
                 "wickets_in_hand"],
        right_on=["match_id", "runs_needed", "balls_left",
                  "wickets_in_hand"],
        suffixes=("_wp", "_base"))
    if len(paired) < 1000:
        raise SystemExit(f"pairing collapsed: only {len(paired)} states paired")
    # The two state constructions must agree on the outcome per state.
    assert (paired["is_batting_team_winner"].astype(float)
            == paired["y"]).all()

    paired["ll_wp"] = per_match_log_loss(paired["p_win"],
                                         paired["is_batting_team_winner"])
    paired["ll_base"] = per_match_log_loss(paired["p"],
                                           paired["is_batting_team_winner"])
    per_match = paired.groupby("match_id").agg(
        ll_wp=("ll_wp", "mean"), ll_base=("ll_base", "mean"),
        n=("ll_wp", "size"))
    boot = paired_bootstrap((per_match["ll_wp"] - per_match["ll_base"]).values)

    out = {
        "system": "inplay_wp_vs_simple_baseline",
        "comparison": "WP model minus 3-feature logistic baseline, "
                      "innings-2 log loss, paired on identical states",
        "train_season": "S1", "test_season": "S2",
        "unit_of_scoring": "delivery, bootstrapped by match",
        "n_deliveries_paired": int(len(paired)),
        "n_matches": int(len(per_match)),
        "wp_log_loss_paired": float(paired["ll_wp"].mean()),
        "baseline_log_loss_paired": float(paired["ll_base"].mean()),
        "difference_bootstrap": boot,
        "verdict": ("difference not established (CI includes zero)"
                    if boot["ci_includes_zero"] else
                    "difference established on the paired states"),
        "notes": "Aggregate figures quoted earlier (0.4108 vs 0.4137) "
                 "were computed on slightly different state sets; the "
                 "paired figures here are the like-for-like comparison.",
    }
    dest = ROOT / "data/predictions/inplay_wp_vs_baseline_ci.json"
    dest.write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
