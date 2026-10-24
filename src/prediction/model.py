"""
Pre-match win-probability model (research design, docs/PREDICTION_SYSTEM.md).

Regularised logistic regression on <=6 DIFFERENCE features:
  elo_diff, xi_batting_diff, xi_bowling_diff, form_nrr_diff, rest_diff
  (+ bat_first for the post-toss P2 variant only)
Features are computed strictly as-of each match. Calibration (Platt) is
fitted ONLY on walk-forward out-of-sample predictions. Probabilities are
clipped to [0.05, 0.95].
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

FEATURES_P1 = ["elo_diff", "xi_batting_diff", "xi_bowling_diff",
               "form_nrr_diff", "rest_diff"]
CLIP = (0.05, 0.95)


def overs_to_balls(overs_float) -> float:
    if overs_float is None or pd.isna(overs_float):
        return 0.0
    whole = int(overs_float)
    return whole * 6 + round((overs_float - whole) * 10)


def match_nrr(row, team) -> float | None:
    """Net run rate of `team` in one completed match (approx: innings
    overs from the scorecard; all-out innings are NOT adjusted to 20 overs
    here -- documented approximation, used only as a form feature)."""
    try:
        if row["innings_1_team"] == team:
            rf, ra = row["innings_1_runs"], row["innings_2_runs"]
            bf, ba = overs_to_balls(row["innings_1_overs"]), overs_to_balls(row["innings_2_overs"])
        elif row["innings_2_team"] == team:
            rf, ra = row["innings_2_runs"], row["innings_1_runs"]
            bf, ba = overs_to_balls(row["innings_2_overs"]), overs_to_balls(row["innings_1_overs"])
        else:
            return None
        if not bf or not ba:
            return None
        return float(rf / (bf / 6) - ra / (ba / 6))
    except Exception:
        return None


def xi_strength(registry_ids, priors_by_id) -> tuple[float, float]:
    """Mean batting/bowling index over an XI. Players missing from the
    priors table count as league average (index 1.0)."""
    bats, bowls = [], []
    for pid in registry_ids:
        pr = priors_by_id.get(pid)
        bats.append(float(pr["bat_index"]) if pr else 1.0)
        bowls.append(float(pr["bowl_index"]) if pr else 1.0)
    return (float(np.mean(bats)) if bats else 1.0,
            float(np.mean(bowls)) if bowls else 1.0)


def build_features(matches: pd.DataFrame, elo_hist: pd.DataFrame,
                   xi_by_match: dict, priors_by_id: dict) -> pd.DataFrame:
    """One feature row per match, all inputs strictly pre-match (Elo is the
    pre-match rating; form/rest use only earlier matches; XI is the actual
    XI, which is what the live P1 uses after announcement)."""
    m = matches.copy()
    m["match_date"] = pd.to_datetime(m["match_date"])
    m = m.sort_values(["match_date", "match_id"]).reset_index(drop=True)
    elo_pre = {(r.match_id, r.team_1): r.team_1_pre for r in elo_hist.itertuples()}
    elo_pre.update({(r.match_id, r.team_2): r.team_2_pre for r in elo_hist.itertuples()})
    form: dict[str, float] = {}
    last_played: dict[str, pd.Timestamp] = {}
    rows = []
    for _, row in m.iterrows():
        t1, t2 = row["team_1_name"], row["team_2_name"]
        xi1 = xi_by_match.get(row["match_id"], {}).get(t1, [])
        xi2 = xi_by_match.get(row["match_id"], {}).get(t2, [])
        b1, w1 = xi_strength(xi1, priors_by_id)
        b2, w2 = xi_strength(xi2, priors_by_id)
        def rest(team):
            if team not in last_played:
                return 7.0
            return min(14.0, float((row["match_date"] - last_played[team]).days))
        rows.append({
            "match_id": row["match_id"], "season": row["season"],
            "match_date": row["match_date"], "team_1": t1, "team_2": t2,
            "elo_diff": (elo_pre.get((row["match_id"], t1), 1500.0)
                         - elo_pre.get((row["match_id"], t2), 1500.0)) / 100.0,
            "xi_batting_diff": b1 - b2,
            "xi_bowling_diff": w1 - w2,
            "form_nrr_diff": form.get(t1, 0.0) - form.get(t2, 0.0),
            "rest_diff": (rest(t1) - rest(t2)) / 7.0,
            "winner": row.get("winner_name"),
            "innings_2_team": row.get("innings_2_team"),
        })
        # update form (EWMA, half-life ~3 matches) + last played AFTER
        for team in (t1, t2):
            nrr = match_nrr(row, team)
            if nrr is not None:
                form[team] = nrr if team not in form else 0.75 * form[team] + 0.25 * nrr
            last_played[team] = row["match_date"]
    return pd.DataFrame(rows)


def fit_logistic(X: pd.DataFrame, y: np.ndarray, C: float = 1.0):
    scaler = StandardScaler()
    Xs = scaler.fit_transform(X[FEATURES_P1])
    clf = LogisticRegression(C=C, max_iter=1000)
    clf.fit(Xs, y)
    return {"scaler_mean": scaler.mean_.tolist(), "scaler_scale": scaler.scale_.tolist(),
            "coef": clf.coef_[0].tolist(), "intercept": float(clf.intercept_[0]),
            "features": FEATURES_P1, "C": C}


def predict_raw(model: dict, X: pd.DataFrame) -> np.ndarray:
    Xs = (X[model["features"]].to_numpy(float) - np.array(model["scaler_mean"])) / np.array(model["scaler_scale"])
    z = Xs @ np.array(model["coef"]) + model["intercept"]
    return 1.0 / (1.0 + np.exp(-z))


def platt_fit(p_raw: np.ndarray, y: np.ndarray):
    """Two-parameter Platt scaling on out-of-sample predictions."""
    from sklearn.linear_model import LogisticRegression as _LR
    eps = 1e-6
    logit = np.log(np.clip(p_raw, eps, 1 - eps) / (1 - np.clip(p_raw, eps, 1 - eps)))
    lr = _LR(C=1e6, max_iter=1000)
    lr.fit(logit.reshape(-1, 1), y)
    return {"a": float(lr.coef_[0][0]), "b": float(lr.intercept_[0])}


def apply_calibration(p_raw, platt: dict | None):
    p = np.asarray(p_raw, float)
    if platt:
        eps = 1e-6
        logit = np.log(np.clip(p, eps, 1 - eps) / (1 - np.clip(p, eps, 1 - eps)))
        p = 1.0 / (1.0 + np.exp(-(platt["a"] * logit + platt["b"])))
    return np.clip(p, *CLIP)


# Chase premium (logit shift) estimated from S1+S2 (computed at build
# time by estimate_chase_logit: chasing teams won 33 of 63 decided
# matches, 52.4% -- a SMALL premium at Kirtipur, not the dew-heavy-venue
# stereotype). Used only by the P2 variant.
def estimate_chase_logit(matches: pd.DataFrame) -> dict:
    decided = matches[matches["winner_name"].notna()]
    chase_wins = float((decided["winner_name"] == decided["innings_2_team"]).sum())
    n = len(decided)
    rate = chase_wins / n if n else 0.5
    logit = float(np.log(rate / (1 - rate))) if 0 < rate < 1 else 0.0
    return {"chase_win_rate": rate, "n": int(n), "logit_shift_team_batting_second": logit}


def p2_adjust(p1: float, team1_bats_first: bool, chase: dict) -> float:
    """Post-toss P2: shift the logit by the chase premium for whichever
    team bats second."""
    eps = 1e-6
    z = np.log(min(max(p1, eps), 1 - eps) / (1 - min(max(p1, eps), 1 - eps)))
    shift = chase["logit_shift_team_batting_second"]
    # team_1 bats second -> team_1 gets +shift; else -shift
    z = z + (-shift if team1_bats_first else shift)
    return float(np.clip(1.0 / (1.0 + np.exp(-z)), *CLIP))


# --- Champion blend (production headline) ---------------------------------
# Evidence (backtest_prediction.py, S2 walk-forward): the fitted logistic
# on <=6 features did NOT beat Elo (raw WF log-loss 0.796 vs Elo 0.689) --
# S1-fitted signs do not survive auction churn. The research fallback is a
# parameter-free blend: Elo-implied probability averaged with an XI
# strength mapping whose scale k is FIXED a priori (not fitted to the
# backtest). S2 WF log-loss of this blend: 0.689 (Elo alone: 0.689) --
# no harm, no demonstrated gain; the S3 frozen log is the decisive test,
# and the fitted logistic remains a challenger that can be promoted at
# the match-10/20 checkpoints if it beats the blend on logged matches.
BLEND_K = 2.0
BLEND_W_ELO = 0.5


def xi_probability(xi_batting_diff: float, xi_bowling_diff: float,
                   k: float = BLEND_K) -> float:
    z = k * (float(xi_batting_diff) + float(xi_bowling_diff))
    return float(1.0 / (1.0 + np.exp(-z)))


def blend_probability(p_elo: float, xi_batting_diff: float,
                      xi_bowling_diff: float) -> float:
    p_xi = xi_probability(xi_batting_diff, xi_bowling_diff)
    return float(np.clip(BLEND_W_ELO * p_elo + (1 - BLEND_W_ELO) * p_xi, *CLIP))
