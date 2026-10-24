#!/usr/bin/env python
"""Score locked predictions in the frozen log against landed results.

THREE-SYSTEM RULE (review fix R2b): pre-match (P1 variants), toss-adjusted
(P2) and in-play are different prediction tasks. Metrics are therefore
computed and reported SEPARATELY for every frozen-log stage — this script
never pools stages into a single pre-match number, and the in-play system
is not scored here at all (see scripts/evaluate_inplay_wp.py).

CANONICAL STAGES (review S13 fix, G1): metrics are grouped by CANONICAL
horizon (src/prediction/stages.py) — the pre-season locks stored as
'P1_preseason_expected_xi' are horizon P0_PRESEASON, the matchday
confirmed-XI locks stored as 'P1_post_XI' are P1_CONFIRMED_XI, and
'P2_post_toss' is P2_POST_TOSS. Stored strings in the log are never
rewritten; canonical names are the reporting layer.

Matches S3 results (normalized parquet) to fixtures by date + team pair.
Writes data/predictions/scorecard.csv (per-prediction rows) and
data/predictions/scorecard_metrics.json (metrics keyed by stage, each
with its own baselines). Baselines per stage: the Elo probability stored
in the log and a chase-heuristic baseline (expanding S1+S2 chase win
rate = 52.4%). Coarse calibration bins only (32 matches cannot support
finer).

OUTCOME RULES (frozen before Season 3; docs/PREDICTION_SYSTEM.md):
the target is the official winner as ingested from cricsheet. A
super-over decider counts as a win for the super-over winner and a
DLS/par-score result as a win for the declared winner (both arrive as
a recorded winner -> scored). A match tied with no decider, abandoned,
or with no result is EXCLUDED -- never scored as 0.5, never silently
dropped: excluded rows are carried in the scorecard with their
classification and reason, and counts are surfaced in
scorecard_metrics.json under "outcome_classification". Classification
lives in src/prediction/metrics.py: classify_outcome."""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.prediction import stages as STAGES  # noqa: E402
from src.prediction.metrics import (OUTCOME_SCORED, classify_outcome,  # noqa: E402
                                    score_all)

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
        if m is None:
            continue  # fixture not landed yet -- not a classification
        classification, winner, reason = classify_outcome(m)
        row = {**{c: r[c] for c in ("match_id", "stage", "team_1_name",
                                   "team_2_name")},
               "p_team_1_win": r["p_team_1_win"], "p_elo": r["p_elo"],
               "outcome_classification": classification,
               "exclusion_reason": reason}
        if classification == OUTCOME_SCORED:
            y = 1 if winner == r["team_1_name"] else 0
            chase_p = 0.524 if m["innings_2_team"] == r["team_1_name"] else 1 - 0.524
            row.update({"p_chase_baseline": chase_p, "actual_team_1_win": y,
                        "winner": winner})
        else:
            row.update({"p_chase_baseline": np.nan,
                        "actual_team_1_win": np.nan, "winner": winner or ""})
        scored.append(row)
    return pd.DataFrame(scored)


def outcome_classification_summary(sdf: pd.DataFrame) -> dict:
    """Per-classification counts (distinct fixtures and log rows) plus
    the per-match exclusion record. Surfaced in scorecard_metrics.json
    so an excluded match is always visible, never silently dropped."""
    summary = {"counts": {}, "excluded_matches": []}
    if not len(sdf) or "outcome_classification" not in sdf.columns:
        return summary
    for classification, g in sdf.groupby("outcome_classification"):
        summary["counts"][str(classification)] = {
            "matches": int(g["match_id"].nunique()), "log_rows": int(len(g))}
    excluded = sdf[sdf["outcome_classification"] != OUTCOME_SCORED]
    for mid, g in excluded.groupby("match_id"):
        first = g.iloc[0]
        summary["excluded_matches"].append({
            "match_id": str(mid),
            "classification": str(first["outcome_classification"]),
            "reason": str(first["exclusion_reason"])})
    return summary


def metrics_by_stage(sdf: pd.DataFrame) -> dict:
    """Metrics per CANONICAL horizon — the ONLY aggregation this module
    produces. Stored stage strings are read through the canonical
    registry (src/prediction/stages.py): rows are grouped by canonical
    horizon (P0_PRESEASON / P1_CONFIRMED_XI / P2_POST_TOSS /
    SIM_SHADOW), so legacy aliases of one horizon can never split a
    score, and different horizons can never be pooled. There is
    deliberately no pooled/all-stages entry: horizons are different
    prediction tasks and must not be averaged together. Each entry
    records the stored stage string(s) it was read from. An
    unregistered stage string raises (registry rule).
    Only rows classified 'scored' enter the metrics; excluded matches
    (no result / tied with no decider) are reported separately via
    outcome_classification_summary, never scored as 0.5."""
    if "outcome_classification" in sdf.columns:
        sdf = sdf[sdf["outcome_classification"] == OUTCOME_SCORED]
    if not len(sdf):
        return {}
    sdf = sdf.assign(_canonical=sdf["stage"].map(STAGES.canonical_stage))
    out = {}
    for canonical, g in sdf.groupby("_canonical", sort=False):
        y = g["actual_team_1_win"].to_numpy()
        entry = {"n": int(len(g)),
                 "canonical_horizon": str(canonical),
                 "canonical_label": STAGES.canonical_label(str(canonical)),
                 "stage": (str(g["stage"].iloc[0]) if g["stage"].nunique() == 1
                           else sorted(str(s) for s in g["stage"].unique())),
                 "stored_stages": sorted(str(s) for s in g["stage"].unique())}
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
        out[str(canonical)] = entry
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
            "p_elo", "p_chase_baseline", "actual_team_1_win", "winner",
            "outcome_classification", "exclusion_reason"]
    classification = outcome_classification_summary(sdf)
    if not len(sdf):
        pd.DataFrame(columns=cols).to_csv(out, index=False)
        (ROOT / "data/predictions/scorecard_metrics.json").write_text(
            json.dumps({"outcome_classification": classification}, indent=1))
        print("Frozen log has no scored predictions yet (no S3 results landed).")
        return
    sdf.to_csv(out, index=False)
    by_stage = metrics_by_stage(sdf)
    (ROOT / "data/predictions/scorecard_metrics.json").write_text(
        json.dumps({**by_stage, "outcome_classification": classification},
                   indent=1))
    counts = classification["counts"]
    if counts:
        print("Outcome classification: " + ", ".join(
            f"{k}={v['matches']} match(es)" for k, v in sorted(counts.items())))
    for ex in classification["excluded_matches"]:
        print(f"  EXCLUDED {ex['match_id']}: {ex['classification']} — {ex['reason']}")
    for canonical, entry in by_stage.items():
        print(f"[{canonical} — stored as {entry['stage']}] n={entry['n']}")
        for name, _col in BASELINE_COLS:
            s = entry[name]
            print(f"  {name:16s} acc={s['accuracy']:.3f} logloss={s['log_loss']:.4f} brier={s['brier']:.4f}")
        print("  calibration bins (predicted mean vs actual rate):")
        for b in entry["calibration_bins"]:
            print(f"    [{b['bin'][0]:.1f},{b['bin'][1]:.1f}) n={b['n']} "
                  f"pred={b['pred_mean']:.3f} actual={b['actual_rate']:.3f}")


if __name__ == "__main__":
    main()
