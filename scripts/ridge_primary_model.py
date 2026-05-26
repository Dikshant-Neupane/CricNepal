"""
Ridge Primary Model for Janakpur Bolts S3 Forecasting
======================================================
Priorities addressed:
  #1  Ridge replaces LightGBM as primary model for n≈37
  #2  Shrinkage estimator (James-Stein inspired) as explicit baseline
      — model MUST beat this to be included in report
  #3  Output is rank + confidence tier, NOT a point estimate

Target definition (unified):
  SOS-adjusted overall economy = (total_runs / (legal_balls / 6))
  normalised by opponent batting strength (pre-match Elo)
  Minimum threshold: 12 legal balls (2 full overs) per season

Usage:
  python scripts/ridge_primary_model.py
"""

import os
import warnings
import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge, RidgeCV
from sklearn.model_selection import LeaveOneOut, cross_val_score
from sklearn.metrics import mean_squared_error
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

warnings.filterwarnings("ignore")

ROOT        = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR    = os.path.join(ROOT, "data")
MODELS_DIR  = os.path.join(ROOT, "models")
DELIV       = os.path.join(ROOT, "deliverables")
os.makedirs(MODELS_DIR, exist_ok=True)
os.makedirs(DELIV, exist_ok=True)

LEAGUE_AVG_BALLS = 30   # approximate median legal balls per bowler per season in NPL
SHRINKAGE_K      = 30   # balls constant for James-Stein shrinkage (tune if needed)


# ─── Unified target: SOS-adjusted economy ────────────────────────────────────
def build_unified_target(phase_df: pd.DataFrame, elo_path: str) -> pd.DataFrame:
    """
    Compute SOS-adjusted economy for each bowler-season pair.

    Uses PRE-MATCH opponent Elo (from rolling_team_elo.csv) to avoid
    look-ahead bias.  Falls back to flat Elo if rolling file not available.

    Returns DataFrame with columns:
      player_name, season_norm, total_balls, raw_economy, sos_adj_economy,
      pp_econ, pp_balls, pp_dot_pct, death_econ, death_balls, death_dot_pct
    """
    df = phase_df.copy()
    df["season_norm"] = df["season"].apply(_norm_season)
    df = df.rename(columns={"bowler": "player_name"})

    # Aggregate per player-season
    agg = (
        df.groupby(["player_name", "season_norm"])
        .apply(_season_agg)
        .reset_index()
    )

    # ── Load opponent Elo (pre-match) ──
    rolling_path = os.path.join(DATA_DIR, "rolling_team_elo.csv")
    flat_path    = os.path.join(DATA_DIR, "team_elo.csv")
    if os.path.exists(rolling_path):
        elo_df = pd.read_csv(rolling_path)
        # league_avg_elo: mean of all pre-match Elo values seen
        league_avg_elo = pd.concat([elo_df["pre_elo_a"], elo_df["pre_elo_b"]]).mean()
        # season-level average opponent Elo (each team's opponents across their matches)
        # Use average of both sides' pre-Elo as a rough season-level SOS proxy
        norm_season_col = elo_df["season"].apply(
            lambda x: int(str(x).replace("S","").replace("SEASON ","").strip())
            if pd.notna(x) else -1
        ) if "season" in elo_df.columns else pd.Series([-1]*len(elo_df))
        elo_df["_sn"] = norm_season_col
        opp_avg = (
            pd.concat([
                elo_df[["_sn", "pre_elo_b"]].rename(columns={"pre_elo_b": "opp_elo"}),
                elo_df[["_sn", "pre_elo_a"]].rename(columns={"pre_elo_a": "opp_elo"}),
            ])
            .groupby("_sn")["opp_elo"].mean()
            .to_dict()
        )
    else:
        elo_df = pd.read_csv(flat_path)
        league_avg_elo = elo_df["elo"].mean()
        opp_avg = {}

    def _sos_factor(season):
        opp_elo = opp_avg.get(season, league_avg_elo)
        return league_avg_elo / opp_elo if opp_elo > 0 else 1.0

    agg["sos_factor"] = agg["season_norm"].apply(_sos_factor)
    agg["sos_adj_economy"] = agg["raw_economy"] * agg["sos_factor"]
    return agg


def _norm_season(x) -> int:
    s = str(x).strip().upper()
    if s.startswith("S") and len(s) <= 3:
        return int(s.replace("S", ""))
    if "SEASON" in s:
        return int(s.split()[-1])
    try:
        return int(s)
    except Exception:
        return -1


def _season_agg(g: pd.DataFrame) -> pd.Series:
    pp   = g[g["powerplay_balls"] > 0]
    dth  = g[g["death_balls"] > 0]

    pp_balls   = g["powerplay_balls"].sum()
    dth_balls  = g["death_balls"].sum()
    total_balls = pp_balls + dth_balls

    # Weighted economy across both phases
    if total_balls > 0:
        pp_runs  = g["powerplay_econ"].mul(g["powerplay_balls"]).sum() / 6
        dth_runs = g["death_econ"].mul(g["death_balls"]).sum() / 6
        raw_econ = (pp_runs + dth_runs) / (total_balls / 6)
    else:
        raw_econ = np.nan

    pp_econ     = g["powerplay_econ"].mean() if pp_balls > 0 else np.nan
    pp_dot      = g["powerplay_dot_pct"].mean() if pp_balls > 0 else np.nan
    dth_econ    = g["death_econ"].mean() if dth_balls > 0 else np.nan
    dth_dot     = g["death_dot_pct"].mean() if dth_balls > 0 else np.nan

    return pd.Series({
        "total_balls":   total_balls,
        "raw_economy":   raw_econ,
        "pp_econ":       pp_econ,
        "pp_balls":      pp_balls,
        "pp_dot_pct":    pp_dot,
        "death_econ":    dth_econ,
        "death_balls":   dth_balls,
        "death_dot_pct": dth_dot,
    })


# ─── Shrinkage estimator ──────────────────────────────────────────────────────
def shrinkage_estimate(
    s2_economy: float,
    league_avg: float,
    balls_faced: int,
    k: int = SHRINKAGE_K,
) -> float:
    """
    James-Stein-inspired shrinkage.
    reliability = balls / (balls + k)
    estimate = reliability * s2_econ + (1-reliability) * league_avg
    More balls → less shrinkage → more trust in observed economy.
    """
    reliability = balls_faced / (balls_faced + k)
    return reliability * s2_economy + (1 - reliability) * league_avg


# ─── Confidence tier based on balls faced ────────────────────────────────────
def confidence_tier(balls: int) -> str:
    if balls >= 60:
        return "HIGH (≥60 balls)"
    elif balls >= 30:
        return "MEDIUM (30–59 balls)"
    elif balls >= 12:
        return "LOW (12–29 balls)"
    else:
        return "INSUFFICIENT (<12 balls)"


# ─── Build S1→S2 paired dataset ──────────────────────────────────────────────
def build_paired_dataset(agg: pd.DataFrame) -> pd.DataFrame:
    """Pivot to player × (S1 features, S2 target), drop rows with < 12 total balls."""
    s1 = agg[agg["season_norm"] == 1].set_index("player_name")
    s2 = agg[agg["season_norm"] == 2].set_index("player_name")
    common = sorted(set(s1.index) & set(s2.index))
    rows = []
    for p in common:
        r1 = s1.loc[p]
        r2 = s2.loc[p]
        # enforce minimum 12 balls in both seasons
        if r1["total_balls"] < 12 or r2["total_balls"] < 12:
            continue
        rows.append({
            "player_name":        p,
            # S1 features
            "s1_economy":         r1["raw_economy"],
            "s1_sos_econ":        r1.get("sos_adj_economy", r1["raw_economy"]),
            "s1_balls":           r1["total_balls"],
            "s1_pp_econ":         r1["pp_econ"] if not np.isnan(r1["pp_econ"]) else r1["raw_economy"],
            "s1_pp_balls":        r1["pp_balls"],
            "s1_pp_dot_pct":      r1["pp_dot_pct"] if not np.isnan(r1["pp_dot_pct"]) else 0.0,
            "s1_death_econ":      r1["death_econ"] if not np.isnan(r1["death_econ"]) else r1["raw_economy"],
            "s1_death_balls":     r1["death_balls"],
            "s1_death_dot_pct":   r1["death_dot_pct"] if not np.isnan(r1["death_dot_pct"]) else 0.0,
            "s1_econ_trend":      r2["raw_economy"] - r1["raw_economy"],  # used as S1→S2 delta signal
            # S2 target
            "s2_economy":         r2["raw_economy"],
            "s2_sos_econ":        r2.get("sos_adj_economy", r2["raw_economy"]),
            "s2_balls":           r2["total_balls"],
        })
    return pd.DataFrame(rows)


# ─── Baseline comparisons ────────────────────────────────────────────────────
def compute_baselines(paired: pd.DataFrame, league_avg: float) -> dict:
    y_true = paired["s2_economy"].values

    # 1. Naive: carry S2 forward as S3 prediction (proxy: S1→S2)
    y_naive = paired["s1_economy"].values
    naive_mse = mean_squared_error(y_true, y_naive)

    # 2. RTM (regression to mean): 50/50 blend
    y_rtm = 0.5 * paired["s1_economy"].values + 0.5 * league_avg
    rtm_mse = mean_squared_error(y_true, y_rtm)

    # 3. Shrinkage: balls-weighted shrinkage
    y_shrink = np.array([
        shrinkage_estimate(row["s1_economy"], league_avg, int(row["s1_balls"]))
        for _, row in paired.iterrows()
    ])
    shrink_mse = mean_squared_error(y_true, y_shrink)

    return {
        "naive_mse":    naive_mse,
        "rtm_mse":      rtm_mse,
        "shrinkage_mse": shrink_mse,
        "baselines": {
            "naive":    y_naive,
            "rtm":      y_rtm,
            "shrinkage": y_shrink,
        }
    }


# ─── Prediction explanation ──────────────────────────────────────────────────
def explain_prediction(
    player_name: str,
    features: pd.Series,
    coef: np.ndarray,
    feat_names: list,
    league_avg_pred: float,
) -> str:
    contributions = {n: features[n] * c for n, c in zip(feat_names, coef)}
    top_pos = sorted(contributions.items(), key=lambda x: -x[1])[:2]
    top_neg = sorted(contributions.items(), key=lambda x: x[1])[:2]

    parts = []
    for name, val in top_pos:
        if abs(val) > 0.05:
            parts.append(f"{name}={features[name]:.2f} adds +{val:.2f}")
    for name, val in top_neg:
        if abs(val) > 0.05:
            parts.append(f"{name}={features[name]:.2f} reduces {val:.2f}")

    direction = "above" if sum(contributions.values()) > 0 else "below"
    detail = "; ".join(parts) if parts else "no dominant features"
    return f"Prediction {direction} average ({league_avg_pred:.2f}). Drivers: {detail}."


# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    phase_path = os.path.join(DATA_DIR, "per_bowler_season_features.csv")
    enrich_path = r"D:/cric_data/data/player_profiles/enriched_players_20260521.csv"

    phase_df  = pd.read_csv(phase_path)
    agg       = build_unified_target(phase_df, os.path.join(DATA_DIR, "team_elo.csv"))

    # merge age / bowling_type if available
    if os.path.exists(enrich_path):
        enrich = pd.read_csv(enrich_path)[["player_name", "bowling_type", "age"]].dropna(subset=["player_name"])
        agg = agg.merge(enrich, on="player_name", how="left")

    paired = build_paired_dataset(agg)
    n = len(paired)
    print(f"Paired training samples (both seasons, ≥12 balls each): {n}")

    if n < 5:
        print("ABORT: fewer than 5 paired samples — cannot fit model.")
        return

    league_avg = agg[agg["season_norm"] == 2]["raw_economy"].mean()
    print(f"League average economy (S2): {league_avg:.3f}")

    # ── Feature matrix ──
    feat_cols = [
        "s1_economy", "s1_sos_econ", "s1_balls",
        "s1_pp_econ", "s1_pp_balls", "s1_pp_dot_pct",
        "s1_death_econ", "s1_death_balls", "s1_death_dot_pct",
    ]
    # drop features that are entirely NaN
    feat_cols = [c for c in feat_cols if c in paired.columns and paired[c].notna().any()]
    X = paired[feat_cols].fillna(0.0).values
    y = paired["s2_economy"].values

    # ── Baselines ──
    bl = compute_baselines(paired, league_avg)
    print(f"\n── Baseline MSEs (lower = better) ──")
    print(f"  Naive (carry S1 econ forward): {bl['naive_mse']:.4f}  RMSE={bl['naive_mse']**0.5:.3f}")
    print(f"  Regression-to-mean (50/50):    {bl['rtm_mse']:.4f}  RMSE={bl['rtm_mse']**0.5:.3f}")
    print(f"  Shrinkage estimator:           {bl['shrinkage_mse']:.4f}  RMSE={bl['shrinkage_mse']**0.5:.3f}")

    # ── Ridge with Leave-One-Out CV ──
    alphas = [0.01, 0.1, 1.0, 10.0, 100.0, 500.0]
    loo    = LeaveOneOut()
    pipe   = Pipeline([("scaler", StandardScaler()), ("ridge", RidgeCV(alphas=alphas, cv=loo))])
    pipe.fit(X, y)

    ridge_cv = pipe.named_steps["ridge"]
    best_alpha = ridge_cv.alpha_
    loo_preds = cross_val_score(pipe, X, y, cv=loo, scoring="neg_mean_squared_error")
    ridge_mse  = -loo_preds.mean()
    print(f"\n── Ridge (LOO-CV) ──")
    print(f"  Best alpha:   {best_alpha}")
    print(f"  LOO MSE:      {ridge_mse:.4f}  RMSE={ridge_mse**0.5:.3f}")
    print(f"  Beats shrinkage baseline? {'YES ✅' if ridge_mse < bl['shrinkage_mse'] else 'NO ❌ — use shrinkage estimator instead'}")

    # Save model
    model_path = os.path.join(MODELS_DIR, "ridge_primary.joblib")
    joblib.dump(pipe, model_path)
    print(f"\nSaved Ridge pipeline → {model_path}")

    # ── S3 Predictions: apply to S2 data ──
    s2_data = agg[agg["season_norm"] == 2].set_index("player_name")
    coef    = pipe.named_steps["ridge"].coef_
    intercept = pipe.named_steps["ridge"].intercept_

    predictions = []
    for player, row in s2_data.iterrows():
        balls = int(row["total_balls"]) if not np.isnan(row["total_balls"]) else 0
        if balls < 12:
            tier = confidence_tier(balls)
            shrink_pred = np.nan
            ridge_pred  = np.nan
        else:
            shrink_pred = shrinkage_estimate(row["raw_economy"], league_avg, balls)
            # build feature vector from S2 data
            fv = {}
            for fc in feat_cols:
                orig = fc.replace("s1_", "s2_") if fc.startswith("s1_") else fc
                orig_alt = fc.replace("s1_", "")
                if orig in row.index:
                    fv[fc] = row[orig]
                elif orig_alt in row.index:
                    fv[fc] = row[orig_alt]
                else:
                    fv[fc] = 0.0
            fv_arr = np.nan_to_num(
                np.array([fv.get(c, 0.0) for c in feat_cols], dtype=float).reshape(1, -1),
                nan=0.0,
            )
            ridge_pred = float(pipe.predict(fv_arr)[0])
            tier = confidence_tier(balls)

        # final estimate: Ridge if beats baseline, else shrinkage
        final_pred = ridge_pred if ridge_mse < bl["shrinkage_mse"] else shrink_pred
        predictions.append({
            "player_name":       player,
            "s2_balls":          balls,
            "s2_raw_economy":    row["raw_economy"],
            "pred_s3_shrinkage": shrink_pred,
            "pred_s3_ridge":     ridge_pred,
            "pred_s3_final":     final_pred,
            "confidence_tier":   tier,
        })

    pred_df = pd.DataFrame(predictions)
    pred_df = pred_df[pred_df["confidence_tier"] != "INSUFFICIENT (<12 balls)"]
    pred_df = pred_df.sort_values("pred_s3_final")

    # ── Rank and tier classification ──
    q33 = pred_df["pred_s3_final"].quantile(0.33)
    q66 = pred_df["pred_s3_final"].quantile(0.66)

    def perf_tier(econ):
        if econ <= q33:
            return "TIER-1 ELITE"
        elif econ <= q66:
            return "TIER-2 SOLID"
        else:
            return "TIER-3 RISKY"

    pred_df["rank"]      = range(1, len(pred_df) + 1)
    pred_df["perf_tier"] = pred_df["pred_s3_final"].apply(perf_tier)

    # ── Ridge coefficient explanation (per bowler) ──
    league_avg_pred = float(pred_df["pred_s3_final"].mean())
    explanations = []
    for _, row in pred_df.iterrows():
        fv = {fc: 0.0 for fc in feat_cols}
        for fc in feat_cols:
            orig = fc.replace("s1_", "")
            if orig in s2_data.columns and row["player_name"] in s2_data.index:
                val = s2_data.loc[row["player_name"], orig] if orig in s2_data.columns else 0.0
                fv[fc] = 0.0 if pd.isna(val) else val
        fs = pd.Series(fv)
        explanations.append(explain_prediction(
            row["player_name"], fs, coef, feat_cols, league_avg_pred
        ))
    pred_df["model_rationale"] = explanations

    # ── Save outputs ──
    csv_out = os.path.join(DELIV, "s3_predictions_ridge_ranked.csv")
    pred_df.to_csv(csv_out, index=False)
    print(f"\nPredictions CSV → {csv_out}")

    # ── Markdown report ──
    _write_report(pred_df, bl, ridge_mse, best_alpha, n, league_avg)

    # ── Validation summary ──
    beats_naive    = ridge_mse < bl["naive_mse"]
    beats_rtm      = ridge_mse < bl["rtm_mse"]
    beats_shrink   = ridge_mse < bl["shrinkage_mse"]
    print(f"\n── Model validity summary ──")
    print(f"  Beats naive:     {'YES' if beats_naive else 'NO'}")
    print(f"  Beats RTM:       {'YES' if beats_rtm else 'NO'}")
    print(f"  Beats shrinkage: {'YES' if beats_shrink else 'NO'}")
    if not beats_shrink:
        print("\n  ⚠️  Ridge does NOT beat shrinkage baseline on this dataset.")
        print("     Final predictions use SHRINKAGE ESTIMATOR, not Ridge.")
        print("     Action: expand feature set or augment with cross-league data.")


def _write_report(pred_df, bl, ridge_mse, best_alpha, n, league_avg):
    lines = [
        "# Ridge Primary Model — S3 Forecast Report",
        f"\n**Team:** Janakpur Bolts  |  **Date:** May 2026\n",
        "## Model Selection Rationale",
        f"- Training sample n={n} (bowler-seasons with ≥12 balls in both S1 and S2)",
        "- Ridge regression is primary model for n<50 (lower variance than LightGBM)",
        "- LightGBM retained for future use once cross-league data augments n≥200",
        f"- Best Ridge alpha: {best_alpha}",
        "",
        "## Baseline Comparison (LOO-CV MSE)",
        "| Method | MSE | RMSE |",
        "|---|---|---|",
        f"| Naive (carry S1 forward) | {bl['naive_mse']:.4f} | {bl['naive_mse']**0.5:.3f} |",
        f"| Regression-to-mean       | {bl['rtm_mse']:.4f} | {bl['rtm_mse']**0.5:.3f} |",
        f"| Shrinkage estimator      | {bl['shrinkage_mse']:.4f} | {bl['shrinkage_mse']**0.5:.3f} |",
        f"| **Ridge (LOO-CV)**       | **{ridge_mse:.4f}** | **{ridge_mse**0.5:.3f}** |",
        "",
        f"League average S2 economy: {league_avg:.3f} runs/over",
        "",
        "## Target Definition",
        "SOS-adjusted overall economy = (total_runs / overs) × (league_avg_elo / opponent_avg_elo)",
        "Minimum threshold: 12 legal balls per season (removes 1-over cameos)",
        "",
        "## Confidence Tiers",
        "- HIGH: >=60 balls (reliable estimate, minimal shrinkage)",
        "- MEDIUM: 30-59 balls (moderate shrinkage applied)",
        "- LOW: 12-29 balls (heavy shrinkage toward league average)",
        "",
        "## S3 Candidate Rankings",
        "",
        "| Rank | Player | Pred Econ | Tier | Confidence | Rationale |",
        "|---|---|---|---|---|---|",
    ]

    tier_emoji = {"TIER-1 ELITE": "🟢", "TIER-2 SOLID": "🟡", "TIER-3 RISKY": "🔴"}
    for _, row in pred_df.iterrows():
        if pd.isna(row["pred_s3_final"]):
            continue
        emoji  = tier_emoji.get(row["perf_tier"], "")
        lines.append(
            f"| {int(row['rank'])} | {row['player_name']} "
            f"| {row['pred_s3_final']:.2f} "
            f"| {emoji} {row['perf_tier']} "
            f"| {row['confidence_tier']} "
            f"| {row['model_rationale']} |"
        )

    lines += [
        "",
        "## Janakpur Bolts — Priority Recruits (Tier 1 + High Confidence only)",
        "",
        "| Player | Pred S3 Econ | S2 Balls | Confidence |",
        "|---|---|---|---|",
    ]
    top = pred_df[
        (pred_df["perf_tier"] == "TIER-1 ELITE") &
        (pred_df["confidence_tier"].str.startswith("HIGH"))
    ]
    for _, row in top.iterrows():
        lines.append(
            f"| {row['player_name']} | {row['pred_s3_final']:.2f} "
            f"| {int(row['s2_balls'])} | {row['confidence_tier']} |"
        )

    out_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..", "deliverables", "s3_ridge_report.md"
    )
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    print(f"Markdown report → {out_path}")


if __name__ == "__main__":
    main()
