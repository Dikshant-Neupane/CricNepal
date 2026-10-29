#!/usr/bin/env python3
"""Calibration reporting: reliability bins + ECE per system
(plan task 5.2, criterion V2). Additive output only:

    data/predictions/calibration_metrics.json

Systems covered are those with stored per-unit predictions:
pre-match champion blend / Elo / raw logistic / simulator (S2
backtest CSVs) and the in-play simple-logistic baseline (S2 delivery
predictions from scripts/inplay_baseline.py). The in-play WP model's
own calibration is NOT produced here: its evaluation harness emits
aggregate metrics only, no per-delivery predictions (see WORKLOG).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PRED = ROOT / "data/predictions"
BINS = np.linspace(0.0, 1.0, 11)


def reliability(p, y) -> dict:
    p = np.asarray(p, float)
    y = np.asarray(y, float)
    idx = np.clip(np.digitize(p, BINS[1:-1]), 0, 9)
    rows, ece = [], 0.0
    for b in range(10):
        m = idx == b
        n = int(m.sum())
        if n == 0:
            rows.append({"bin": b, "lo": float(BINS[b]),
                         "hi": float(BINS[b + 1]), "n": 0,
                         "mean_p": None, "freq": None})
            continue
        mp, fq = float(p[m].mean()), float(y[m].mean())
        ece += n * abs(mp - fq)
        rows.append({"bin": b, "lo": float(BINS[b]),
                     "hi": float(BINS[b + 1]), "n": n,
                     "mean_p": mp, "freq": fq})
    return {"n": int(len(y)), "ece": float(ece / len(y)), "bins": rows}


def main() -> int:
    systems = {}
    b = pd.read_csv(PRED / "backtest_s2.csv")
    for name, col in [("champion_blend", "p_blend"), ("elo", "p_elo"),
                      ("raw_logistic", "p_raw")]:
        systems[name] = {"unit": "match", "test": "S2 walk-forward",
                         **reliability(b[col], b["y"])}
    s = pd.read_csv(PRED / "backtest_simulator.csv")
    systems["simulator_shadow"] = {
        "unit": "match", "test": "S2 backtest",
        **reliability(s["p_sim_team_1"], s["y"])}
    base = PRED / "inplay_baseline_s2_predictions.csv"
    if base.exists():
        d = pd.read_csv(base)
        systems["inplay_simple_logistic_baseline"] = {
            "unit": "delivery", "test": "S2, trained on S1",
            **reliability(d["p"], d["y"])}
    out = {"generated": "2026-10-29", "bins": 10,
           "definition": "ECE = sum over bins of (n_bin/N) * "
                         "|mean predicted - observed frequency|",
           "systems": systems,
           "not_produced": {
               "inplay_wp_model": "its evaluation harness emits "
                   "aggregate metrics only; per-delivery OOS "
                   "predictions are not stored (plan 4.2 territory)"}}
    (PRED / "calibration_metrics.json").write_text(
        json.dumps(out, indent=2))
    for name, srec in systems.items():
        print(f"{name}: n={srec['n']} ECE={srec['ece']:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
