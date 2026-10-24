#!/usr/bin/env python
"""Production Monte Carlo simulator run over the S3 league fixtures.

SHADOW MODE: the simulator's probabilities are never the headline. With
--lock they are appended to the frozen log at stage
'SIM_shadow_preseason' (model_version 'sim_v1') so they can be scored
prospectively, separately from every P1/P2 stage -- promotion requires
beating the champion on that frozen log (docs/PREDICTION_SYSTEM.md).

Basis (identical to the locked P1s): expected XIs from
engine.select_expected_xi over the current player priors; distributions
fitted on ALL available ball-by-ball history (S1+S2); 10,000 sims per
match; deterministic per-match seed 20261026 + match_number. Players in
an expected XI without a cricsheet registry ID enter under a synthetic
id ("key:<player_key>") so their prior bat/bowl index still reshapes the
phase collective distribution; they cannot join a bowling rotation
(no fitted distribution), mirroring the backtest's rotation rule.
"""
import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.prediction import engine  # noqa: E402
from src.prediction import simulator as S  # noqa: E402

N_SIMS = 10000
SEED_BASE = 20261026
SIM_MODEL_VERSION = "sim_v1"
STAGE = "SIM_shadow_preseason"


def build_sim_context(root: Path):
    ctx = engine.load_context(root)
    bb = pd.read_parquet(root / "data/normalized/ball_by_ball_normalized.parquet")
    reg = json.loads((root / "data/predictions/registry_map.json").read_text())["names"]
    dists = S.build_distributions(bb, reg)
    bowl_balls = (bb.assign(pid=bb.bowler_name.map(reg))
                  .groupby("pid").size().to_dict())
    priors_by_id = {}
    for k, v in ctx["priors_by_key"].items():
        row = {"bat_index": float(v["bat_index"]), "bowl_index": float(v["bowl_index"])}
        rid = v.get("cricsheet_registry_id")
        priors_by_id[rid if isinstance(rid, str) else f"key:{k}"] = row
    return ctx, dists, bowl_balls, priors_by_id


def xi_ids(ctx, priors_by_key, team):
    out = []
    for k in ctx["xi_by_team"][team]:
        rid = priors_by_key[k].get("cricsheet_registry_id")
        out.append(rid if isinstance(rid, str) else f"key:{k}")
    return out


def rotation(xi, dists, bowl_balls):
    known = {p for ph in S.PHASES for p in dists[ph]["bowl"]}
    ids = [p for p in xi if p in known]
    return sorted(ids, key=lambda p: -bowl_balls.get(p, 0)) or xi[:5]


def simulate_fixtures(root: Path, n_sims: int = N_SIMS) -> pd.DataFrame:
    ctx, dists, bowl_balls, priors_by_id = build_sim_context(root)
    rows = []
    for _, fx in ctx["fixtures"].iterrows():
        t1, t2 = fx["team_1_name"], fx["team_2_name"]
        if not isinstance(t1, str) or not t1:
            continue  # playoff fixtures: teams TBA
        xi1 = xi_ids(ctx, ctx["priors_by_key"], t1)
        xi2 = xi_ids(ctx, ctx["priors_by_key"], t2)
        res = S.simulate_match(xi1, xi2, rotation(xi1, dists, bowl_balls),
                               rotation(xi2, dists, bowl_balls), dists,
                               priors_by_id, n_sims=n_sims,
                               seed=SEED_BASE + int(fx["match_number"]))
        pred = engine.predict_fixture(t1, t2, fx["match_date"], ctx["ratings"],
                                      ctx["priors_by_key"], ctx["xi_by_team"],
                                      ctx["form"], ctx["last_played"], ctx["model"])
        feats = dict(pred["features"])
        feats.update({"sim_mean_score_1": round(res["mean_score_1"], 1),
                      "sim_mean_score_2": round(res["mean_score_2"], 1),
                      "sim_tie_rate": round(res["tie_rate"], 4),
                      "n_sims": n_sims, "xi_1_ids": xi1, "xi_2_ids": xi2})
        rows.append({"match_id": fx["match_id"], "match_number": fx["match_number"],
                     "match_date": fx["match_date"], "team_1_name": t1,
                     "team_2_name": t2, "p_team_1_win": round(res["p_team_1_win"], 4),
                     "p_elo": pred["p_elo"], "p_logistic_challenger": None,
                     "features_json": json.dumps(feats)})
        print(fx["match_id"], t1, "vs", t2,
              "sim p1=", rows[-1]["p_team_1_win"])
    return pd.DataFrame(rows)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--lock", action="store_true",
                    help="append to frozen log at stage SIM_shadow_preseason")
    ap.add_argument("--n-sims", type=int, default=N_SIMS)
    args = ap.parse_args()
    df = simulate_fixtures(ROOT, n_sims=args.n_sims)
    out = ROOT / "data/predictions/simulator_preseason.csv"
    df.to_csv(out, index=False)
    print(f"{len(df)} simulator predictions -> {out}")
    if args.lock:
        n = engine.lock_predictions(ROOT, df, STAGE,
                                    model_version=SIM_MODEL_VERSION)
        print(f"locked {n} new predictions at stage {STAGE} "
              f"(model_version {SIM_MODEL_VERSION})")
