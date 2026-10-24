#!/usr/bin/env python
"""Score locked predictions in the frozen log against landed results.

THREE-SYSTEM RULE (review fix R2b): pre-match (P1 variants), toss-adjusted
(P2) and in-play are different prediction tasks. Metrics are therefore
computed and reported SEPARATELY for every frozen-log stage — this script
never pools stages into a single pre-match number, and the in-play system
is not scored here at all (see scripts/evaluate_inplay_wp.py).

Matches S3 results (normalized parquet) to fixtures by date + team pair.
Writes data/predictions/scorecard.csv (per-prediction rows) and
data/predictions/scorecard_metrics.json (metrics keyed by stage, each
with its own baselines). Baselines per stage: the Elo probability stored
in the log and a chase-heuristic baseline (expanding S1+S2 chase win
rate = 52.4%). Coarse calibration bins only (32 matches cannot support
finer)."""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.prediction.metrics import score_all  # noqa: E402

BINS = [(0.0, 0.4), (0.4, 0.5), (0.5, 0.6), (0.6, 0.8), (0.8, 1.01)]
BASELINE_COLS = (("model", "p_team_1_win"), ("elo_baseline", "p_elo"),
                 ("chase_baseline", "p_chase_baseline"))


def build_scored(log: pd.DataFrame, matches: pd.DataFrame,
                 fixtures: pd.DataFrame) -> pd.DataFrame:
    """Join frozen-log rows to landed S3 results. Pure function of its
    inputs (unit-testable); stages are carried through untouched."""
    s3 = matches[matches["season"] == "S3"].copy()
    fx_by_key = {}
    for _, f in fixtures.iterrows():
        if isinstance(f["team_1_name"], str) and f["team_1_name"]:
            fx_by_key[(f["match_date"], tuple(sorted([f["team_1_name"],
                                                      f["team_2_name"]])))] = f["match_id"]
    res_by_id = {}
    for _, m in s3.iterrows():
        key = (str(m["match_date"]), tuple(sorted([m["team_1_name"], m["team_2_name"]])))
        if key in fx_by_key:
            res_by_id[fx_by_key[key]] = m
    scored = []
    for _, r in log.iterrows():
        m = res_by_id.get(r["match_id"])
        if m is None or not isinstance(m["winner_name"], str):
            continue
        y = 1 if m["winner_name"] == r["team_1_name"] else 0
        chase_p = 0.524 if m["innings_2_team"] == r["team_1_name"] else 1 - 0.524
        scored.append({**{c: r[c] for c in ("match_id", "stage", "team_1_name",
                                            "team_2_name")},
                       "p_team_1_win": r["p_team_1_win"], "p_elo": r["p_elo"],
                       "p_chase_baseline": chase_p, "actual_team_1_win": y,
                       "winner": m["winner_name"]})
    return pd.DataFrame(scored)


def metrics_by_stage(sdf: pd.DataFrame) -> dict:
    """Metrics per stage — the ONLY aggregation this module produces.
    There is deliberately no pooled/all-stages entry: stages are
    different prediction tasks and must not be averaged together."""
    out = {}
    for stage, g in sdf.groupby("stage"):
        y = g["actual_team_1_win"].to_numpy()
        entry = {"n": int(len(g))}
        for name, col in BASELINE_COLS:
            entry[name] = score_all(g[col], y)
        bins = []
        for lo, hi in BINS:
            b = g[(g.p_team_1_win >= lo) & (g.p_team_1_win < hi)]
            if len(b):
                bins.append({"bin": [lo, hi], "n": int(len(b)),
                             "pred_mean": float(b.p_team_1_win.mean()),
                             "actual_rate": float(b.actual_team_1_win.mean())})
        entry["calibration_bins"] = bins
        out[str(stage)] = entry
    return out


def main():
    log_path = ROOT / "data/predictions/frozen_log.csv"
    if not log_path.exists():
        print("No frozen log yet -- nothing to score.")
        return
    log = pd.read_csv(log_path)
    matches = pd.read_parquet(ROOT / "data/normalized/matches_normalized.parquet")
    fixtures = pd.read_csv(ROOT / "data/fixtures/s3_fixtures.csv")
    sdf = build_scored(log, matches, fixtures)
    out = ROOT / "data/predictions/scorecard.csv"
    cols = ["match_id", "stage", "team_1_name", "team_2_name", "p_team_1_win",
            "p_elo", "p_chase_baseline", "actual_team_1_win", "winner"]
    if not len(sdf):
        pd.DataFrame(columns=cols).to_csv(out, index=False)
        (ROOT / "data/predictions/scorecard_metrics.json").write_text("{}")
        print("Frozen log has no scored predictions yet (no S3 results landed).")
        return
    sdf.to_csv(out, index=False)
    by_stage = metrics_by_stage(sdf)
    (ROOT / "data/predictions/scorecard_metrics.json").write_text(
        json.dumps(by_stage, indent=1))
    for stage, entry in by_stage.items():
        print(f"[{stage}] n={entry['n']}")
        for name, _col in BASELINE_COLS:
            s = entry[name]
            print(f"  {name:16s} acc={s['accuracy']:.3f} logloss={s['log_loss']:.4f} brier={s['brier']:.4f}")
        print("  calibration bins (predicted mean vs actual rate):")
        for b in entry["calibration_bins"]:
            print(f"    [{b['bin'][0]:.1f},{b['bin'][1]:.1f}) n={b['n']} "
                  f"pred={b['pred_mean']:.3f} actual={b['actual_rate']:.3f}")


if __name__ == "__main__":
    main()
