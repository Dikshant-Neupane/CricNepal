#!/usr/bin/env python
"""Walk-forward backtest of the pre-match model on Season 2 + final model.

Honesty protocol (docs/PREDICTION_SYSTEM.md):
- Player priors for the backtest are computed AS OF the start of Season 2
  (history window ends 2025-11-17), so no S2-or-later ball is in a prior.
- Each S2 match is predicted by a logistic model trained only on matches
  played before it (expanding window, starting from all of S1).
- Calibration (Platt) is fitted on those out-of-sample predictions only.
- The production model is then trained on S1+S2 features (XI features from
  pre-season priors of the respective season) and saved as JSON.
Outputs: data/predictions/backtest_s2.csv, backtest_metrics.json,
model_v1.json.
"""
import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.prediction import elo as E, model as M, priors as P  # noqa: E402
from src.prediction.metrics import coin_baseline_metrics, score_all  # noqa: E402

ZIP_DIR = Path(os.environ.get("CRICSHEET_ZIP_DIR", ROOT.parent / ".scratch" / "predbuild"))


def _zips():
    out = {}
    for fname, (label, _t) in P.COMPETITIONS.items():
        zp = ZIP_DIR / fname
        if zp.exists():
            out[zp] = label
    return out


def _priors_asof(ref: date, lineups: pd.DataFrame):
    agg = P.aggregate_cricsheet(_zips(), ref_date=ref, cutoff=ref - timedelta(days=3 * 365))
    players = (lineups[["cricsheet_registry_id", "player_name", "team_name"]]
               .drop_duplicates("cricsheet_registry_id")
               .rename(columns={"player_name": "canonical_name",
                                "team_name": "team"}))
    players["player_key"] = "reg_" + players["cricsheet_registry_id"]
    players["role"] = "unknown"
    pr = P.compute_priors(agg, players)
    return {r.cricsheet_registry_id: {"bat_index": r.bat_index, "bowl_index": r.bowl_index}
            for r in pr.itertuples()}


def main():
    matches = pd.read_parquet(ROOT / "data/normalized/matches_normalized.parquet")
    lineups = pd.read_parquet(ROOT / "data/final/parquet/match_lineups.parquet")
    xi_by_match = {}
    for (mid, team), g in lineups.groupby(["match_id", "team_name"]):
        xi_by_match.setdefault(mid, {})[team] = list(g["cricsheet_registry_id"])

    out = ROOT / "data" / "predictions"
    # --- as-of priors: pre-S1 for S1 features, pre-S2 for S2 features ---
    priors_s1 = _priors_asof(date(2024, 11, 30), lineups)
    priors_s2 = _priors_asof(date(2025, 11, 17), lineups)
    hist = E.compute_history(matches)
    feats = {}
    for season, priors in (("S1", priors_s1), ("S2", priors_s2)):
        sub = matches[matches["season"] == season]
        f = M.build_features(sub, hist, xi_by_match, priors)
        # form/rest must carry across seasons: recompute on the full frame
        feats[season] = f
    full = M.build_features(matches, hist, xi_by_match, priors_s2)
    # S1 rows: replace XI diffs with pre-S1-prior versions
    f1 = feats["S1"].set_index("match_id")
    for col in ("xi_batting_diff", "xi_bowling_diff"):
        full.loc[full["season"] == "S1", col] = full.loc[full["season"] == "S1", "match_id"].map(f1[col])
    full = full[full["winner"].notna()].reset_index(drop=True)
    full["y"] = (full["winner"] == full["team_1"]).astype(int)
    train0 = full[full["season"] == "S1"]
    test = full[full["season"] == "S2"].reset_index(drop=True)

    # --- walk-forward over S2 ---
    preds, elo_p, chase_p, chase_rates = [], [], [], []
    for i, row in test.iterrows():
        tr = pd.concat([train0, test.iloc[:i]])
        model = M.fit_logistic(tr[M.FEATURES_P1], tr["y"].to_numpy())
        preds.append(float(M.predict_raw(model, row.to_frame().T[M.FEATURES_P1])[0]))
        elo_p.append(float(E.expected(
            1500 + row["elo_diff"] * 100 / 2 + 0, 1500 - row["elo_diff"] * 100 / 2)) if False else np.nan)
        # elo baseline from canonical history pre ratings
        h = hist[hist["match_id"] == row["match_id"]].iloc[0]
        elo_p[-1] = float(E.expected(h["team_1_pre"], h["team_2_pre"]))
        decided_tr = tr[tr["innings_2_team"].notna()]
        rate = float((decided_tr["winner"] == decided_tr["innings_2_team"]).mean()) if len(decided_tr) else 0.5
        chase_rates.append(rate)
        chase_p.append(rate if row["innings_2_team"] == row["team_1"] else 1 - rate)
    test["p_raw"] = preds
    test["p_elo"] = elo_p
    test["p_chase"] = chase_p
    test["p_blend"] = [M.blend_probability(pe, xb, xw) for pe, xb, xw
                       in zip(test["p_elo"], test["xi_batting_diff"],
                              test["xi_bowling_diff"])]
    platt = M.platt_fit(test["p_raw"].to_numpy(), test["y"].to_numpy())
    y = test["y"].to_numpy()
    metrics = {
        "champion_blend": score_all(test["p_blend"], y),
        "challenger_logistic_raw": score_all(test["p_raw"], y),
        # Coin baseline is definitional (LL=ln2, Brier=0.25, accuracy
        # null) -- F2 audit: score_all on p=0.5 used to emit a spurious
        # "accuracy" of 0.34375, which was just the S2 team_1 win share
        # under the p>=0.5 tie rule. Never compute it again.
        "baseline_coin": coin_baseline_metrics(len(y)),
        "baseline_higher_elo": score_all(test["p_elo"], y),
        "baseline_chase_heuristic": score_all(test["p_chase"], y),
        "platt_on_logistic_oos": platt, "n_test": int(len(y)),
        "notes": "S2 walk-forward; priors as of 2025-11-17; XI = actual XI "
                 "(the live P1 is also post-XI-announcement). The fitted "
                 "logistic LOSES to Elo on this backtest and its Platt slope "
                 "is negative -- it ships as challenger only. The champion "
                 "blend ties Elo (no demonstrated gain). S3 frozen log is "
                 "the decisive evaluation.",
    }
    test.to_csv(out / "backtest_s2.csv", index=False)
    (out / "backtest_metrics.json").write_text(json.dumps(metrics, indent=1))

    # --- production model: train on S1+S2, calibration from WF OOS ---
    final = M.fit_logistic(full[M.FEATURES_P1], full["y"].to_numpy())
    final.update({"version": "v1", "role": "challenger",
                  "trained_on": "S1+S2 (64 matches, tie excluded)",
                  "champion": {"type": "elo_xi_blend", "k": M.BLEND_K,
                               "w_elo": M.BLEND_W_ELO},
                  "chase": M.estimate_chase_logit(matches),
                  "clip": list(M.CLIP)})
    (out / "model_v1.json").write_text(json.dumps(final, indent=1))
    for k, v in metrics.items():
        if isinstance(v, dict) and "accuracy" in v:
            acc = "  n/a" if v["accuracy"] is None else f"{v['accuracy']:.3f}"
            print(f"{k:28s} acc={acc} logloss={v['log_loss']:.4f} brier={v['brier']:.4f} n={v['n']}")
    print("platt (diagnostic only):", platt)


if __name__ == "__main__":
    main()
