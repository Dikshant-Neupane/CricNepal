"""
Canonical Elo engine for CricNepal (single source of truth).

Replaces the two disagreeing implementations:
- scripts/compute_team_elo.py (K=40, no season regression) — now a thin
  wrapper over this module; its rolling output also carries match_id/season.
- src/analytics/opposition_strength_analysis.py keeps its own history
  builder for SOS/WAE dashboard outputs (unchanged behaviour), but new
  prediction code must use THIS module.

Design (docs/PREDICTION_SYSTEM.md; research report 2026-10-24):
- expected score E = 1 / (1 + 10**(-(Ra-Rb)/400))
- update R += K * MOV * (actual - expected), MOV capped at MOV_CAP
- between seasons every rating regresses toward 1500 by `season_regression`
  (fraction of the deviation from 1500 that is removed).
- K and season_regression were selected by walk-forward log-loss:
  ratings run through Season 1, regress at the boundary, then every
  Season 2 match is predicted with its pre-match ratings before being
  updated. NOTE (F1 audit, 2026-10-24): that selection reused the S2
  set that is also reported as the backtest -- selection-on-test. The
  bias is bounded (<=0.0050 log-loss over the grid actually searched)
  and recorded in Pre-registration Amendment #3 and
  data/predictions/elo_selection_audit.json.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .metrics import log_loss

INITIAL_ELO = 1500.0
# Selected 2026-10-24 by tune_walk_forward() on S1->S2 within the
# research ranges (K 20-32, regression 0.25-0.40); these values are the
# restricted grid's argmin (grid saved in data/predictions/elo_tuning.csv).
# PROVENANCE (F1 audit): the grid was scored on Season 2, the same set
# reported as the backtest -- selection-on-test. The restricted-grid
# surface is FLAT (log-loss range 0.0050; coin flip = 0.6931), so the
# reported Elo log-loss is mildly optimistic by at most that bound.
# Clean reselection within S1 alone picks K=28 (S2 log-loss within
# 0.0003 of these constants); (20, 0.40) is kept for Season 3 per
# Pre-registration Amendment #3. Regression 0.40 rests on the research
# prior (25-40%), not on clean selection. Full audit:
# data/predictions/elo_selection_audit.json (scripts/audit_elo_selection.py).
DEFAULT_K = 20.0
DEFAULT_SEASON_REGRESSION = 0.40
MOV_CAP = 1.5


def expected(rating_a: float, rating_b: float) -> float:
    return 1.0 / (1.0 + 10.0 ** ((rating_b - rating_a) / 400.0))


def _mov_multiplier(row) -> float:
    """Margin-of-victory multiplier from innings run differential, capped.

    Uses innings totals when available: |run diff| of 60+ saturates the
    multiplier at MOV_CAP so one blowout cannot dominate a rating.
    """
    r1, r2 = row.get("innings_1_runs"), row.get("innings_2_runs")
    if r1 is None or r2 is None or pd.isna(r1) or pd.isna(r2):
        return 1.0
    return 1.0 + (MOV_CAP - 1.0) * min(1.0, abs(float(r1) - float(r2)) / 60.0)


def _score(row, team) -> float | None:
    if row.get("result_status") == "tie":
        return 0.5
    winner = row.get("winner_name")
    if winner is None or pd.isna(winner):
        return None
    return 1.0 if winner == team else 0.0


def regress(ratings: dict, fraction: float) -> dict:
    """Regress every rating toward INITIAL_ELO by `fraction` of deviation."""
    return {t: INITIAL_ELO + (1.0 - fraction) * (r - INITIAL_ELO)
            for t, r in ratings.items()}


def compute_history(matches: pd.DataFrame, k: float = DEFAULT_K,
                    season_regression: float = DEFAULT_SEASON_REGRESSION,
                    use_mov: bool = True) -> pd.DataFrame:
    """One row per match: pre/post Elo for both teams, chronological."""
    m = matches.copy()
    m["match_date"] = pd.to_datetime(m["match_date"])
    m = m.sort_values(["match_date", "match_id"]).reset_index(drop=True)
    ratings: dict[str, float] = {}
    last_season = None
    rows = []
    for _, row in m.iterrows():
        season = row["season"]
        if last_season is not None and season != last_season:
            ratings = regress(ratings, season_regression)
        last_season = season
        t1, t2 = row["team_1_name"], row["team_2_name"]
        r1 = ratings.get(t1, INITIAL_ELO)
        r2 = ratings.get(t2, INITIAL_ELO)
        s1 = _score(row, t1)
        mov = _mov_multiplier(row) if use_mov else 1.0
        if s1 is None:
            post1, post2 = r1, r2
        else:
            e1 = expected(r1, r2)
            post1 = r1 + k * mov * (s1 - e1)
            post2 = r2 + k * mov * ((1 - s1) - (1 - e1))
        ratings[t1], ratings[t2] = post1, post2
        rows.append({
            "match_id": row["match_id"], "season": season,
            "match_date": row["match_date"], "team_1": t1, "team_2": t2,
            "team_1_pre": r1, "team_2_pre": r2,
            "team_1_post": post1, "team_2_post": post2,
            "expected_team_1": expected(r1, r2),
            "score_team_1": s1 if s1 is not None else np.nan,
            "winner": row.get("winner_name"),
        })
    return pd.DataFrame(rows)


def final_ratings(history: pd.DataFrame) -> dict:
    ratings = {}
    for _, r in history.iterrows():
        ratings[r["team_1"]] = r["team_1_post"]
        ratings[r["team_2"]] = r["team_2_post"]
    return ratings


def current_ratings(matches: pd.DataFrame, k: float = DEFAULT_K,
                    season_regression: float = DEFAULT_SEASON_REGRESSION,
                    next_season_regression: bool = True) -> dict:
    """Ratings as of now: history run + regression into the next season."""
    hist = compute_history(matches, k=k, season_regression=season_regression)
    ratings = final_ratings(hist)
    if next_season_regression and len(matches):
        ratings = regress(ratings, season_regression)
    return ratings


def tune_walk_forward(matches: pd.DataFrame, ks=range(16, 41, 4),
                      regressions=(0.0, 0.25, 0.33, 0.40, 0.50),
                      eval_season: str = "S2"):
    """Grid-search (K, season_regression) on walk-forward log-loss.

    Every eval-season match is scored with pre-match ratings only.
    Returns (best_params, results_df).
    """
    results = []
    for k in ks:
        for reg in regressions:
            hist = compute_history(matches, k=float(k), season_regression=float(reg))
            ev = hist[(hist["season"] == eval_season) & hist["score_team_1"].notna()]
            if len(ev) == 0:
                continue
            ll = log_loss(ev["expected_team_1"], ev["score_team_1"])
            results.append({"k": float(k), "season_regression": float(reg),
                            "n": len(ev), "walk_forward_log_loss": ll})
    df = pd.DataFrame(results).sort_values("walk_forward_log_loss")
    best = df.iloc[0]
    return ({"k": float(best["k"]),
             "season_regression": float(best["season_regression"])},
            df.reset_index(drop=True))
