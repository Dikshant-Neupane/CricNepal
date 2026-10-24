#!/usr/bin/env python
"""Build data/predictions/player_history.csv + player_priors.csv (Task 3).

Downloads are NOT stored in the repo; cricsheet zips are read from
CRICSHEET_ZIP_DIR (default ~/workspace/.scratch/predbuild).
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.prediction.players import build_registry_map  # noqa: E402
from src.prediction import priors as P  # noqa: E402
import pandas as pd  # noqa: E402

if __name__ == "__main__":
    zip_dir = Path(os.environ.get("CRICSHEET_ZIP_DIR",
                                  ROOT.parent / ".scratch" / "predbuild"))
    zips = {}
    for fname, (label, _t) in P.COMPETITIONS.items():
        zp = zip_dir / fname
        if zp.exists():
            zips[zp] = label
    print("Competitions:", {Path(z).name: c for z, c in zips.items()})
    agg = P.aggregate_cricsheet(zips)
    out = ROOT / "data" / "predictions"
    agg.to_csv(out / "player_history.csv", index=False)
    master = pd.read_csv(out / "player_master.csv")
    pr = P.compute_priors(agg, master)
    pr.to_csv(out / "player_priors.csv", index=False)
    print(f"history rows: {len(agg)}; priors: {len(pr)}")
    print(pr.prior_group.value_counts().to_dict())
    print(pr.sort_values('bat_balls_eff', ascending=False).head(8)[
        ['canonical_name', 'team', 'prior_group', 'bat_balls_eff', 'prior_bat_rpb', 'prior_bowl_econ']].to_string())
