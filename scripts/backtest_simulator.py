#!/usr/bin/env python
"""Shadow backtest: Monte Carlo simulator vs champion blend on Season 2.

Distributions are fitted on Season 1 ball-by-ball ONLY. XIs are the actual
S2 XIs (the live P1 is likewise post-XI). Bowling rotations = XI players
with an S1 bowling distribution, ordered by S1 balls bowled. 2,000 sims
per match (production default is 10,000). Output:
data/predictions/backtest_simulator.json. Shadow mode: these numbers
decide nothing until the simulator beats the blend on the S3 frozen log.
"""
import json
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from src.prediction import simulator as S  # noqa: E402
from src.prediction.metrics import score_all  # noqa: E402
import backtest_prediction as BT  # noqa: E402

if __name__ == "__main__":
    matches = pd.read_parquet(ROOT / "data/normalized/matches_normalized.parquet")
    bb = pd.read_parquet(ROOT / "data/normalized/ball_by_ball_normalized.parquet")
    lineups = pd.read_parquet(ROOT / "data/final/parquet/match_lineups.parquet")
    reg = json.loads((ROOT / "data/predictions/registry_map.json").read_text())["names"]
    s1_ids = set(matches[matches.season == "S1"].match_id)
    dists = S.build_distributions(bb[bb.match_id.isin(s1_ids)], reg)
    priors_s2 = BT._priors_asof(date(2025, 11, 17), lineups)
    # bowling rotation order per player from S1 balls bowled
    s1bb = bb[bb.match_id.isin(s1_ids)]
    bowl_balls = (s1bb.assign(pid=s1bb.bowler_name.map(reg))
                  .groupby("pid").size().to_dict())
    core = pd.read_csv(ROOT / "data/predictions/backtest_s2.csv")
    core = core.set_index("match_id")
    rows = []
    s2 = matches[matches.season == "S2"].sort_values("match_date")
    for _, m in s2.iterrows():
        ln = lineups[lineups.match_id == m.match_id]
        xi = {t: list(g.sort_values("xi_position").cricsheet_registry_id)
              for t, g in ln.groupby("team_name")}
        t1, t2 = m.team_1_name, m.team_2_name
        def rotation(team):
            ids = [p for p in xi[team] if p in
                   {k for ph in S.PHASES for k in dists[ph]["bowl"]}]
            return sorted(ids, key=lambda p: -bowl_balls.get(p, 0)) or xi[team][:5]
        res = S.simulate_match(xi[t1], xi[t2], rotation(t1), rotation(t2),
                               dists, priors_s2, n_sims=2000, seed=7)
        y = 1 if m.winner_name == t1 else 0
        rows.append({"match_id": m.match_id, "team_1": t1, "team_2": t2,
                     "p_sim_team_1": res["p_team_1_win"], "y": y,
                     "mean_score_1": res["mean_score_1"], "mean_score_2": res["mean_score_2"]})
        print(m.match_id, t1, "vs", t2, "sim p1=", round(res["p_team_1_win"], 3), "y=", y)
    df = pd.DataFrame(rows)
    df.to_csv(ROOT / "data/predictions/backtest_simulator.csv", index=False)
    merged = df.set_index("match_id").join(core[["p_blend"]], how="inner")
    out = {"simulator": score_all(df.p_sim_team_1, df.y),
           "champion_blend_same_matches": score_all(merged.p_blend, merged.y),
           "n": int(len(df)), "n_sims_per_match": 2000,
           "notes": "Simulator distributions from S1 only; XI actual; "
                    "production sims use all available history + 10k sims."}
    (ROOT / "data/predictions/backtest_simulator.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))
