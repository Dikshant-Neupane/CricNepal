#!/usr/bin/env python
"""Estimate cross-league translation factors from overlap players (A5).

For each source league L and each kind (batting / bowling):
- overlap players = registry IDs with >= MIN_BALLS (60) decay-weighted
  balls in BOTH L (ALL phase) and the NPL (ALL phase) in
  data/predictions/player_history.csv;
- per player, deviation of their runs/ball from their league's mean
  (bowling deviation is sign-flipped: positive = better than mean,
  matching priors._combine);
- t_hat = weighted regression through the origin of dev_NPL on dev_L,
  weights = paired effective balls (n_L * n_NPL) / (n_L + n_NPL);
  95% CI from the weighted residual variance.
A combined estimate stacks batting and bowling player-deviations.

Update rule: a league's assumed factor is replaced by the estimate
shrunk toward the assumed value, t_new = (n * t_hat + N0 * t_assumed)
/ (n + N0) with N0 = 8, ONLY where ALL of these hold:
  (a) combined overlap n >= 8;
  (b) the 95% CI of t_hat excludes the assumed value (the data actually
      argue for a move);
  (c) the 95% CI of t_hat excludes 0 (the estimate establishes a
      positive translation at all -- a near-zero or negative t_hat
      whose CI spans zero is the signature of a confounded pool, e.g.
      home internationals who are below-mean against a world-class
      T20I pool but above-mean at home; applying it would import the
      confound into every prior).
Otherwise the assumed factor is retained and the estimate + n are
reported. Output: data/predictions/translation_factors.json.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.prediction import priors as P  # noqa: E402

MIN_BALLS = 60.0
N0 = 8.0


def _wls_origin(x, y, w):
    x, y, w = map(lambda a: np.asarray(a, float), (x, y, w))
    denom = float((w * x * x).sum())
    if denom <= 0 or len(x) < 3:
        return None
    t = float((w * x * y).sum() / denom)
    resid = y - t * x
    dof = max(len(x) - 1, 1)
    s2 = float((w * resid * resid).sum() / dof)
    se = float(np.sqrt(s2 / denom)) if denom > 0 else float("nan")
    return {"t_hat": round(t, 4), "ci_low": round(t - 1.96 * se, 4),
            "ci_high": round(t + 1.96 * se, 4), "n": int(len(x))}


def estimate(agg: pd.DataFrame) -> dict:
    means = P.league_means(agg)
    m_all = means[means["phase"] == "ALL"].set_index("competition")
    a = agg[agg["phase"] == "ALL"]
    npl = a[a["competition"] == "NPL"].set_index("registry_id")
    assumed = {label: t for label, t in P.COMPETITIONS.values()}
    out = {}
    for comp in sorted(set(a["competition"]) - {"NPL"}):
        sub = a[a["competition"] == comp].set_index("registry_id")
        res = {"assumed_t": assumed.get(comp)}
        stacked_x, stacked_y, stacked_w = [], [], []
        for kind, balls_col, runs_col, mean_col, flip in (
                ("bat", "bat_balls", "bat_runs", "bat_rpb", 1.0),
                ("bowl", "bowl_balls", "bowl_runs", "bowl_rpb", -1.0)):
            xs, ys, ws = [], [], []
            for pid in sub.index.intersection(npl.index):
                n_l = float(sub.loc[pid, balls_col])
                n_n = float(npl.loc[pid, balls_col])
                if n_l < MIN_BALLS or n_n < MIN_BALLS:
                    continue
                dev_l = flip * (float(sub.loc[pid, runs_col]) / n_l
                                - float(m_all.loc[comp, mean_col]))
                dev_n = flip * (float(npl.loc[pid, runs_col]) / n_n
                                - float(m_all.loc["NPL", mean_col]))
                w = (n_l * n_n) / (n_l + n_n)
                xs.append(dev_l); ys.append(dev_n); ws.append(w)
            est = _wls_origin(xs, ys, ws)
            res[kind] = est
            if est:
                stacked_x += xs; stacked_y += ys; stacked_w += ws
        comb = _wls_origin(stacked_x, stacked_y, stacked_w)
        res["combined"] = comb
        res["combined_n_players"] = int(len(
            set(sub.index.intersection(npl.index))))
        # decision per the pre-stated rule
        t_assumed = assumed.get(comp)
        applied, t_new = False, t_assumed
        if comb and comb["n"] >= 8 and t_assumed is not None:
            excludes_assumed = (comb["ci_high"] < t_assumed
                                or comb["ci_low"] > t_assumed)
            excludes_zero = comb["ci_low"] > 0
            if excludes_assumed and excludes_zero:
                t_new = round((comb["n"] * comb["t_hat"] + N0 * t_assumed)
                              / (comb["n"] + N0), 4)
                applied = True
        res["decision"] = {"applied": applied, "t_after": t_new,
                           "rule": "combined n>=8 AND 95% CI of t_hat "
                                   "excludes the assumed value AND "
                                   "excludes 0; t shrunk toward assumed "
                                   f"with N0={N0:g}"}
        out[comp] = res
    return out


if __name__ == "__main__":
    agg = pd.read_csv(ROOT / "data/predictions/player_history.csv")
    out = estimate(agg)
    path = ROOT / "data/predictions/translation_factors.json"
    path.write_text(json.dumps(out, indent=1))
    for comp, r in out.items():
        c = r["combined"]
        print(f"{comp:6s} assumed={r['assumed_t']}  combined="
              f"{c if not c else (c['t_hat'], c['ci_low'], c['ci_high'], 'n=' + str(c['n']))}"
              f"  decision: {'APPLY t=' + str(r['decision']['t_after']) if r['decision']['applied'] else 'retain assumed'}")
    print(f"-> {path}")
