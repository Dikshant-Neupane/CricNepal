#!/usr/bin/env python
"""Fit the v1.1 temperature for the champion blend (Task A2).

Method: temperature scaling ON THE LOGIT (Guo et al. temperature
scaling) -- p_cal = sigmoid(logit(p_raw) / T). Chosen over a linear
shrink in probability space because it is the standard single-parameter
calibration for probabilistic classifiers, preserves ranking exactly,
and behaves smoothly near the clip bounds. T > 1 softens (the blend is
over-confident), T < 1 sharpens.

Fitted ONLY on the Season 2 walk-forward out-of-sample predictions in
data/predictions/backtest_s2.csv (column p_blend vs y) -- the same OOS
predictions the v1 backtest reported. The already-locked v1 P1 rows are
NOT touched: v1.1 applies to future locks (P1_post_XI and later).

Output: data/predictions/model_v1_1.json + the frozen constant
TEMPERATURE_V1_1 in src/prediction/model.py (update both together; the
pre-registration drift test asserts they agree).
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import minimize_scalar

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.prediction import model as M  # noqa: E402
from src.prediction.metrics import brier, log_loss  # noqa: E402


def fit_temperature(p, y):
    p = np.clip(np.asarray(p, float), 1e-6, 1 - 1e-6)
    z = np.log(p / (1 - p))
    y = np.asarray(y, float)

    def nll(T):
        q = 1.0 / (1.0 + np.exp(-z / T))
        return log_loss(np.clip(q, *M.CLIP), y)

    res = minimize_scalar(nll, bounds=(0.2, 5.0), method="bounded")
    return float(res.x)


if __name__ == "__main__":
    bt = pd.read_csv(ROOT / "data/predictions/backtest_s2.csv")
    p, y = bt["p_blend"].to_numpy(), bt["y"].to_numpy()
    T = fit_temperature(p, y)
    p_cal = M.apply_temperature(p, T)
    out = {
        "version": "v1.1",
        "base_model": "v1 champion blend (elo_xi_blend, k=2.0, w_elo=0.5)",
        "calibration": {
            "method": "temperature scaling on the logit: "
                      "p_cal = sigmoid(logit(p_raw) / T)",
            "temperature_T": round(T, 4),
            "fitted_on": "Season 2 walk-forward out-of-sample predictions "
                         "(data/predictions/backtest_s2.csv, p_blend vs y)",
            "n_oos": int(len(y)),
            "fitted_date": "2026-10-24",
        },
        "oos_metrics_same_predictions": {
            "before": {"log_loss": log_loss(np.clip(p, *M.CLIP), y),
                       "brier": brier(np.clip(p, *M.CLIP), y)},
            "after": {"log_loss": log_loss(p_cal, y), "brier": brier(p_cal, y)},
        },
        "applies_to": "future locks only (P1_post_XI and later stages); "
                      "locked v1 rows are never rewritten",
    }
    path = ROOT / "data/predictions/model_v1_1.json"
    path.write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))
    print(f"-> {path}")
    print(f"NOTE: model.py TEMPERATURE_V1_1 must equal {round(T, 4)} "
          f"(drift test asserts this).")
