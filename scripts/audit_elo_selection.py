#!/usr/bin/env python
"""F1 audit: Elo parameter-selection provenance (evaluation integrity).

Finding: the canonical Elo constants (K=20, season_regression=0.40) were
chosen from a grid evaluated on the Season 2 walk-forward -- the same
S2 set that is then reported as the backtest evaluation. That is
selection-on-test: the reported S2 log-loss for Elo-family models is
mildly optimistic. This script quantifies the effect and performs the
clean reselection:

- Provenance: the restricted grid actually used at build time
  (scripts/build_team_ratings.py: K in {20,24,28,32} x regression in
  {0.25,0.33,0.40}) is saved in data/predictions/elo_tuning.csv; the
  wider default grid of elo.tune_walk_forward (K 16..40 x regression
  {0,0.25,0.33,0.40,0.50}) is recomputed here for the full surface.
- Clean reselection: K is selected by walk-forward WITHIN Season 1
  only (the between-season regression cannot be selected within one
  season; its S2 sensitivity is reported separately and the shipped
  0.40 rests on the research prior of 25-40%, not on clean selection).
- Pre-committed decision (Pre-registration Amendment #3): keep
  (20, 0.40) for Season 3 either way -- if the S1-only K is worse on S2
  by >0.002 log-loss, switching would chase test-set noise; if it is
  within 0.002 or better, switching constants mid-protocol for a
  within-noise difference is worse than the bounded bias. The S3 frozen
  log is unaffected: its parameters were fixed before Match 1. The
  contamination is in the historical evaluation claim, not the
  prospective test.

Output: data/predictions/elo_selection_audit.json
"""
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.prediction import elo as E  # noqa: E402
from src.prediction.metrics import log_loss  # noqa: E402

CHOSEN = {"k": 20.0, "season_regression": 0.40}
FULL_KS = [float(k) for k in range(16, 41, 4)]
FULL_REGS = [0.0, 0.25, 0.33, 0.40, 0.50]


def _s2_ll(matches, k, reg):
    hist = E.compute_history(matches, k=float(k), season_regression=float(reg))
    ev = hist[(hist["season"] == "S2") & hist["score_team_1"].notna()]
    return float(log_loss(ev["expected_team_1"], ev["score_team_1"])), int(len(ev))


def _s1_walk_forward_ll(matches, k):
    """Walk-forward log-loss within Season 1 only (single-season frame,
    so no between-season regression is involved in the scoring)."""
    s1 = matches[matches["season"] == "S1"]
    hist = E.compute_history(s1, k=float(k), season_regression=0.0)
    ev = hist[hist["score_team_1"].notna()]
    return float(log_loss(ev["expected_team_1"], ev["score_team_1"])), int(len(ev))


def main():
    matches = pd.read_parquet(ROOT / "data/normalized/matches_normalized.parquet")
    out = {"finding": "elo_parameter_selection_on_s2_test_set",
           "chosen_constants": CHOSEN}

    # ---- provenance: the restricted grid saved at build time ----
    saved = pd.read_csv(ROOT / "data/predictions/elo_tuning.csv")
    restricted = []
    for _, r in saved.iterrows():
        ll, n = _s2_ll(matches, r["k"], r["season_regression"])
        restricted.append({"k": float(r["k"]),
                             "season_regression": float(r["season_regression"]),
                             "n": n, "walk_forward_log_loss": ll,
                             "saved_log_loss": float(r["walk_forward_log_loss"]),
                             "reproduces_saved": abs(ll - float(r["walk_forward_log_loss"])) < 1e-12})
    out["provenance"] = {
        "grid_code": "src/prediction/elo.py: tune_walk_forward(); restricted "
                     "grid invoked by scripts/build_team_ratings.py "
                     "(ks=range(20,33,4), regressions=(0.25,0.33,0.40))",
        "grid_scored_on": "Season 2 walk-forward log-loss (pre-match ratings "
                          "only), n=32 -- the same S2 set reported as the "
                          "backtest evaluation in backtest_metrics.json",
        "saved_surface_file": "data/predictions/elo_tuning.csv",
        "restricted_grid_recomputed": restricted,
        "restricted_grid_argmin": min(restricted, key=lambda d: d["walk_forward_log_loss"]),
        "restricted_grid_range": (max(d["walk_forward_log_loss"] for d in restricted)
                                  - min(d["walk_forward_log_loss"] for d in restricted)),
    }

    # ---- full surface on S2 (elo.tune_walk_forward default grid) ----
    surface = []
    for k in FULL_KS:
        for reg in FULL_REGS:
            ll, n = _s2_ll(matches, k, reg)
            surface.append({"k": k, "season_regression": reg, "n": n,
                            "walk_forward_log_loss": ll})
    ll_chosen = next(d["walk_forward_log_loss"] for d in surface
                     if d["k"] == CHOSEN["k"]
                     and d["season_regression"] == CHOSEN["season_regression"])
    argmin = min(surface, key=lambda d: d["walk_forward_log_loss"])
    ll_max = max(d["walk_forward_log_loss"] for d in surface)
    out["s2_full_grid"] = {
        "ks": FULL_KS, "regressions": FULL_REGS, "surface": surface,
        "ll_at_chosen_20_0.40": ll_chosen,
        "argmin": argmin,
        "ll_range_max_minus_min": ll_max - argmin["walk_forward_log_loss"],
        "chosen_minus_argmin": ll_chosen - argmin["walk_forward_log_loss"],
        "selection_bound": out["provenance"]["restricted_grid_range"],
        "selection_bound_outer_full_grid_range": ll_max - argmin["walk_forward_log_loss"],
        "bound_definition": "Maximum plausible optimism from selection: "
                            "the range (max - min log-loss) of the grid "
                            "that was actually searched at build time (the "
                            "restricted grid saved in elo_tuning.csv). The "
                            "chosen cell is that grid's argmin, so no "
                            "selection within the searched grid could have "
                            "flattered the reported S2 number by more than "
                            "this range. The wider default grid's range is "
                            "kept as a conservative outer envelope.",
    }

    # ---- clean reselection: K within Season 1 only ----
    s1_rows = []
    for k in FULL_KS:
        ll, n = _s1_walk_forward_ll(matches, k)
        s1_rows.append({"k": k, "n": n, "s1_walk_forward_log_loss": ll})
    s1_best = min(s1_rows, key=lambda d: d["s1_walk_forward_log_loss"])
    k_s1 = s1_best["k"]
    ll_s1k_on_s2, _ = _s2_ll(matches, k_s1, CHOSEN["season_regression"])
    diff = ll_s1k_on_s2 - ll_chosen
    out["s1_only_selection"] = {
        "method": "Walk-forward within Season 1 only: ratings evolve "
                  "through S1 with each candidate K; every S1 match is "
                  "scored with its pre-match ratings. Regression is not "
                  "involved (single-season frame).",
        "table": s1_rows,
        "chosen_k": k_s1,
        "s2_log_loss_at_s1_k_reg_0.40": ll_s1k_on_s2,
        "s2_log_loss_at_20_0.40": ll_chosen,
        "difference_s1k_minus_chosen_on_s2": diff,
        "branch": ("worse_by_more_than_0.002" if diff > 0.002
                   else "within_0.002_or_better"),
    }

    # ---- regression sensitivity on S2 (cannot be selected within S1) ----
    reg_slice = []
    for reg in [0.0, 0.1, 0.2, 0.25, 0.33, 0.40, 0.5]:
        ll, _ = _s2_ll(matches, CHOSEN["k"], reg)
        reg_slice.append({"season_regression": reg, "k": CHOSEN["k"],
                          "s2_walk_forward_log_loss": ll})
    out["regression_sensitivity_s2_at_k20"] = {
        "slice": reg_slice,
        "range": (max(d["s2_walk_forward_log_loss"] for d in reg_slice)
                  - min(d["s2_walk_forward_log_loss"] for d in reg_slice)),
        "note": "The between-season regression cannot be validated within "
                "one season, so 0.40 is NOT a clean selection: it rests on "
                "the research prior (regress 25-40% toward the mean between "
                "seasons) and is merely consistent with this S2 slice. Any "
                "future selection must be nested (select on earlier seasons "
                "only).",
    }

    out["decision"] = {
        "action": "keep (K=20, season_regression=0.40) for Season 3",
        "rule": "Pre-committed in Pre-registration Amendment #3: keep the "
                "shipped constants under either branch -- if the S1-only K "
                "is worse on S2 by >0.002, the shipped pair stands on the "
                "bounded-bias argument; if within 0.002 or better, "
                "switching mid-protocol for a within-noise difference is "
                "worse than the bounded bias.",
        "branch_taken": out["s1_only_selection"]["branch"],
        "standing_rule": "Future parameter selection must be nested: "
                         "select on earlier seasons only, never on the "
                         "season being reported as the evaluation.",
        "effect_on_s3_frozen_log": "None. S3 parameters were fixed before "
                                   "Match 1; the contamination is in the "
                                   "historical S2 evaluation claim, not in "
                                   "the prospective S3 test.",
        "interpretation": "S2 backtest log-loss figures for Elo-family "
                          "models are mildly optimistic by at most the "
                          "measured selection bound (the range of the "
                          "grid actually searched, "
                          f"{out['s2_full_grid']['selection_bound']:.4f}; "
                          "outer envelope over the wider default grid: "
                          f"{out['s2_full_grid']['selection_bound_outer_full_grid_range']:.4f}). "
                          "Treat 0.6888 as 'no better than about "
                          f"{ll_chosen + out['s2_full_grid']['selection_bound']:.4f} "
                          "once selection is accounted for' -- i.e. even "
                          "Elo's apparent edge over the coin flip (0.6931) "
                          "is within the selection bound. Still "
                          "indistinguishable from the champion blend.",
    }

    path = ROOT / "data/predictions/elo_selection_audit.json"
    path.write_text(json.dumps(out, indent=1))
    print(f"restricted grid reproduces saved: "
          f"{all(d['reproduces_saved'] for d in restricted)}")
    print(f"S2 full grid: LL(20,0.40)={ll_chosen:.6f} argmin="
          f"K{argmin['k']}/reg{argmin['season_regression']} LL={argmin['walk_forward_log_loss']:.6f} "
          f"range={out['s2_full_grid']['ll_range_max_minus_min']:.6f}")
    print(f"S1-only K: {k_s1} (S1 LL {s1_best['s1_walk_forward_log_loss']:.6f}); "
          f"its S2 LL={ll_s1k_on_s2:.6f}, diff vs chosen={diff:+.6f} "
          f"-> branch {out['s1_only_selection']['branch']}")
    print(f"-> {path}")


if __name__ == "__main__":
    main()
