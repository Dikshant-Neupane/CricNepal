#!/usr/bin/env python3
"""Audit: best VERIFIED predictor for CricNepal (2026-11-12).

Two independent evaluations, both leakage-clean by construction:

Part A — Pre-match win probability (FROZEN system).
  Scores the S3 frozen log as it stands (cricsheet-scored matches only)
  per stage: champion blend vs Elo vs logistic challenger vs simulator
  vs coin. Paired bootstrap 95% CIs (10,000 resamples, seed 42).
  This script SCORES ONLY. It changes no constant, promotes nothing,
  and rewrites no locked row. Promotion follows docs/PREREGISTRATION_S3.md
  (checkpoint + frozen-log gate); a challenger that does not beat the
  champion here stays a challenger.

Part B — Bowler economy, S1 -> S2 (validation) then S2 -> S3 (holdout).
  Target: a bowler's overall economy in the target season (ALL phases,
  legal balls only). Definitions (stated once, used everywhere):
    legal ball  = extras_type NOT IN ('wides', 'noballs')
    bowler runs = runs_off_bat + runs_extras, except byes/legbyes
                  deliveries where bowler runs = runs_off_bat only
    economy     = bowler_runs / legal_balls * 6
  Minimum 12 legal balls in each season of a pair. Candidates use the
  PRIOR season only. Ridge alpha is selected by nested LOO-CV on the
  S1->S2 pairs ONLY; the S2->S3 holdout is evaluated exactly once,
  after selection is frozen. The S3 holdout is partial (12 ingested
  matches), so its N and ball counts are reported, not hidden.

Part C — Phase-prior recomputation.
  Recomputes the forecaster's phase priors from the shipped S1+S2
  ball-by-ball data under the implementation's own definition
  (wides/no-ball rows dropped entirely, runs_total / rows * 6) and
  reports them next to the constants in
  src/analytics/s3_performance_forecaster.py. No constant is changed
  by this script.

Outputs: data/predictions/model_comparison_audit.json (tracked).
  Every figure carries N and its cohort label.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from sklearn.linear_model import Ridge, RidgeCV  # noqa: E402
from sklearn.model_selection import LeaveOneOut  # noqa: E402
from sklearn.pipeline import Pipeline  # noqa: E402
from sklearn.preprocessing import StandardScaler  # noqa: E402

from src.prediction.metrics import (  # noqa: E402
    coin_baseline_metrics, paired_bootstrap, per_match_log_loss, score_all,
)

OUT = ROOT / "data" / "predictions" / "model_comparison_audit.json"
SEED = 42


# ---------------------------------------------------------------- Part A
def part_a() -> dict:
    fl = pd.read_csv(ROOT / "data/predictions/frozen_log.csv")
    sc = pd.read_csv(ROOT / "data/predictions/scorecard.csv")
    sc = sc[sc["outcome_classification"] == "scored"].copy()
    y = sc["actual_team_1_win"].to_numpy(float)
    out: dict = {}
    for stage, grp in sc.groupby("stage"):
        gy = grp["actual_team_1_win"].to_numpy(float)
        label = ("simulator" if stage == "SIM_shadow_preseason"
                 else "champion")
        res = {
            "n": int(len(grp)),
            "coin": coin_baseline_metrics(len(grp)),
            "elo": score_all(grp["p_elo"].to_numpy(float), gy),
            label: score_all(grp["p_team_1_win"].to_numpy(float), gy),
        }
        # logistic challenger: from the frozen log, same (match, stage).
        # Only for the champion stages; the SIM rows would duplicate
        # the P1 challenger result on the same 12 matches.
        chal_p = None
        if stage != "SIM_shadow_preseason":
            fl_s = fl[fl["stage"] == stage].set_index("match_id")
            chal = grp["match_id"].map(fl_s["p_logistic_challenger"])
            if chal.notna().all():
                chal_p = chal.to_numpy(float)
                res["logistic_challenger"] = score_all(chal_p, gy)
        # paired bootstrap: this stage's p_team_1_win minus Elo,
        # per-match log-loss
        d = (per_match_log_loss(grp["p_team_1_win"].to_numpy(float), gy)
             - per_match_log_loss(grp["p_elo"].to_numpy(float), gy))
        res[f"{label}_minus_elo_logloss"] = paired_bootstrap(d)
        # challenger minus champion, per-match log-loss (the gate
        # the preregistration requires for any promotion)
        if chal_p is not None:
            d2 = (per_match_log_loss(chal_p, gy)
                  - per_match_log_loss(
                      grp["p_team_1_win"].to_numpy(float), gy))
            res["challenger_minus_champion_logloss"] = paired_bootstrap(d2)
        out[stage] = res
    return out


# ---------------------------------------------------------------- Part B
def bowler_season_table() -> pd.DataFrame:
    """Per (bowler, season) overall + phase economy from the shipped
    final parquet. Seasons come from the matches join."""
    bbb = pd.read_parquet(ROOT / "data/final/parquet/ball_by_ball.parquet")
    matches = pd.read_parquet(ROOT / "data/final/parquet/matches.parquet")[
        ["match_id", "season"]]
    b = bbb.merge(matches, on="match_id", how="left")
    b = b[b["season"].isin(["S1", "S2", "S3"])].copy()
    b["is_legal"] = ~b["extras_type"].isin(["wides", "noballs"])
    b["bowl_runs"] = b["runs_off_bat"] + b["runs_extras"]
    byes = b["extras_type"].isin(["byes", "legbyes"])
    b.loc[byes, "bowl_runs"] = b.loc[byes, "runs_off_bat"]
    rows = []
    for (bowler, season), g in b.groupby(["bowler_name", "season"]):
        legal = g[g["is_legal"]]
        if len(legal) < 12:
            continue
        row = {"bowler": bowler, "season": season,
               "balls": int(len(legal)),
               "economy": float(g["bowl_runs"].sum() / len(legal) * 6),
               "wickets": int(g["is_wicket"].sum()),
               "dot_pct": float(legal["is_dot_ball"].mean() * 100)}
        for ph in ("Powerplay", "Middle", "Death"):
            gp = g[g["phase"] == ph]
            lp = gp[gp["is_legal"]]
            row[f"{ph.lower()}_econ"] = (
                float(gp["bowl_runs"].sum() / len(lp) * 6) if len(lp) >= 6
                else np.nan)
            row[f"{ph.lower()}_balls"] = int(len(lp))
            row[f"{ph.lower()}_dot_pct"] = (
                float(lp["is_dot_ball"].mean() * 100) if len(lp) else np.nan)
        rows.append(row)
    return pd.DataFrame(rows)


def paired_table(tab: pd.DataFrame, s_from: str, s_to: str) -> pd.DataFrame:
    a = tab[tab["season"] == s_from].set_index("bowler")
    b = tab[tab["season"] == s_to].set_index("bowler")
    common = sorted(set(a.index) & set(b.index))
    rows = []
    for bowler in common:
        ra, rb = a.loc[bowler], b.loc[bowler]
        if ra["balls"] < 12 or rb["balls"] < 12:
            continue
        rows.append({"bowler": bowler,
                     "s_from_balls": int(ra["balls"]),
                     "s_to_balls": int(rb["balls"]),
                     "s_from_econ": float(ra["economy"]),
                     "s_to_econ": float(rb["economy"]),
                     "s_from_pp": float(ra["powerplay_econ"]),
                     "s_from_mid": float(ra["middle_econ"]),
                     "s_from_death": float(ra["death_econ"]),
                     "s_from_dot": float(ra["dot_pct"]),
                     "s_from_wkts": int(ra["wickets"]),
                     "s_from_pp_balls": int(ra["powerplay_balls"]),
                     "s_from_mid_balls": int(ra["middle_balls"]),
                     "s_from_death_balls": int(ra["death_balls"])})
    return pd.DataFrame(rows)


def shrink(econ: float, league_mean: float, balls: float, k: float) -> float:
    w = balls / (balls + k)
    return float(w * econ + (1 - w) * league_mean)


def loo_predictions(paired: pd.DataFrame, alphas=(0.1, 1.0, 10.0, 100.0, 500.0)):
    """LOO-CV predictions for every candidate on the paired set.
    Baselines use a leave-one-out league mean (the pair's own S1
    economy never enters its own baseline). Ridge alpha is selected
    by nested LOO-CV inside each outer training fold."""
    y = paired["s_to_econ"].to_numpy(float)
    n = len(paired)
    feats = ["s_from_econ", "s_from_pp", "s_from_mid", "s_from_death",
             "s_from_dot", "s_from_wkts", "s_from_balls"]
    X = paired[feats].fillna(paired[feats].median(numeric_only=True)).to_numpy(float)
    preds = {k: np.zeros(n) for k in
             ("league_mean", "naive", "rtm", "shrink_k30", "shrink_k60",
              "shrink_k150", "ridge")}
    loo = LeaveOneOut()
    for i, (tr, te) in enumerate(loo.split(X)):
        lm = float(np.mean(paired["s_from_econ"].to_numpy(float)[tr]))
        econ = float(paired["s_from_econ"].iloc[i])
        balls = float(paired["s_from_balls"].iloc[i])
        preds["league_mean"][i] = lm
        preds["naive"][i] = econ
        preds["rtm"][i] = 0.5 * econ + 0.5 * lm
        preds["shrink_k30"][i] = shrink(econ, lm, balls, 30.0)
        preds["shrink_k60"][i] = shrink(econ, lm, balls, 60.0)
        preds["shrink_k150"][i] = shrink(econ, lm, balls, 150.0)
        pipe = Pipeline([("scaler", StandardScaler()),
                         ("ridge", RidgeCV(alphas=list(alphas), cv=LeaveOneOut()))])
        pipe.fit(X[tr], y[tr])
        preds["ridge"][i] = float(pipe.predict(X[te])[0])
    return preds, y


def mse(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.mean((np.asarray(a, float) - np.asarray(b, float)) ** 2))


def part_b() -> dict:
    tab = bowler_season_table()
    paired12 = paired_table(tab, "S1", "S2")
    paired23 = paired_table(tab, "S2", "S3")
    preds, y = loo_predictions(paired12)
    loo_res = {}
    for name, p in preds.items():
        se = (p - y) ** 2
        loo_res[name] = {"n": int(len(y)), "mse": mse(p, y),
                         "rmse": float(np.sqrt(mse(p, y))),
                         "mae": float(np.mean(np.abs(p - y)))}
    # paired bootstrap: each candidate minus shrinkage-k60, squared error
    base_se = (preds["shrink_k60"] - y) ** 2
    for name, p in preds.items():
        if name == "shrink_k60":
            continue
        loo_res[name]["vs_shrink_k60_sqerr_bootstrap"] = paired_bootstrap(
            (p - y) ** 2 - base_se)
    # Ridge alpha selected on S1->S2 LOO only, frozen before holdout.
    feats = ["s_from_econ", "s_from_pp", "s_from_mid", "s_from_death",
             "s_from_dot", "s_from_wkts", "s_from_balls"]
    X12 = paired12[feats].fillna(paired12[feats].median(numeric_only=True)).to_numpy(float)
    pipe = Pipeline([("scaler", StandardScaler()),
                     ("ridge", RidgeCV(alphas=[0.1, 1.0, 10.0, 100.0, 500.0],
                                       cv=LeaveOneOut()))])
    pipe.fit(X12, y)
    best_alpha = float(pipe.named_steps["ridge"].alpha_)
    # Holdout S2->S3, evaluated exactly once.
    y3 = paired23["s_to_econ"].to_numpy(float)
    lm23 = float(paired23["s_from_econ"].mean())
    hold = {}
    hold_preds = {
        "league_mean": np.full(len(y3), lm23),
        "naive": paired23["s_from_econ"].to_numpy(float),
        "rtm": 0.5 * paired23["s_from_econ"].to_numpy(float) + 0.5 * lm23,
        "shrink_k30": np.array([shrink(e, lm23, b, 30.0) for e, b in
                                zip(paired23["s_from_econ"], paired23["s_from_balls"])]),
        "shrink_k60": np.array([shrink(e, lm23, b, 60.0) for e, b in
                                zip(paired23["s_from_econ"], paired23["s_from_balls"])]),
        "shrink_k150": np.array([shrink(e, lm23, b, 150.0) for e, b in
                                 zip(paired23["s_from_econ"], paired23["s_from_balls"])]),
    }
    X23 = paired23[feats].fillna(paired23[feats].median(numeric_only=True)).to_numpy(float)
    hold_preds["ridge"] = pipe.predict(X23)
    for name, p in hold_preds.items():
        hold[name] = {"n": int(len(y3)), "mse": mse(p, y3),
                      "rmse": float(np.sqrt(mse(p, y3))),
                      "mae": float(np.mean(np.abs(p - y3)))}
    base_se3 = (hold_preds["shrink_k60"] - y3) ** 2
    for name, p in hold_preds.items():
        if name == "shrink_k60":
            continue
        hold[name]["vs_shrink_k60_sqerr_bootstrap"] = paired_bootstrap(
            (p - y3) ** 2 - base_se3)
    return {
        "target": "bowler overall economy (all phases, legal balls >= 12 per season)",
        "validation_S1_to_S2": {"n_pairs": int(len(paired12)),
                                "target_mean": float(y.mean()),
                                "target_sd": float(y.std()),
                                "loo_cv": loo_res},
        "ridge_alpha_selected_on_S1_S2_loo": best_alpha,
        "holdout_S2_to_S3": {"n_pairs": int(len(paired23)),
                             "note": "S3 is partial: 12 ingested matches only; "
                                     "holdout evaluated exactly once, after "
                                     "selection was frozen on S1->S2.",
                             "target_mean": float(y3.mean()),
                             "target_sd": float(y3.std()),
                             "s_to_balls_median": float(paired23["s_to_balls"].median()),
                             "results": hold},
    }


# ---------------------------------------------------------------- Part C
def part_c() -> dict:
    bbb = pd.read_parquet(ROOT / "data/final/parquet/ball_by_ball.parquet")
    matches = pd.read_parquet(ROOT / "data/final/parquet/matches.parquet")[
        ["match_id", "season"]]
    b = bbb.merge(matches, on="match_id", how="left")
    s12 = b[b["season"].isin(["S1", "S2"])]
    f = s12[~s12["extras_type"].isin(["wides", "noballs"])]
    out = {}
    for ph, g in f.groupby("phase"):
        out[ph] = {"n_rows": int(len(g)),
                   "economy_filtered_definition": round(
                       float(g["runs_total"].sum() / len(g) * 6), 3)}
    return out


def main():
    results = {"part_a_frozen_log_S3_to_date": part_a(),
               "part_b_bowler_economy": part_b(),
               "part_c_phase_priors_recomputed_S1_S2": part_c()}
    OUT.write_text(json.dumps(results, indent=1))
    print(json.dumps(results, indent=1))


if __name__ == "__main__":
    main()
