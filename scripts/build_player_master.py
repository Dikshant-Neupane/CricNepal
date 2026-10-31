#!/usr/bin/env python
"""Build data/predictions/player_master.csv (Task 2) and the cricsheet
registry map cache (data/predictions/registry_map.json) from any cricsheet
zips found in the scratch download dir (override with CRICSHEET_ZIP_DIR)."""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.prediction.players import build_player_master, build_registry_map  # noqa: E402

if __name__ == "__main__":
    zip_dir = Path(os.environ.get("CRICSHEET_ZIP_DIR",
                                  ROOT.parent / ".scratch" / "predbuild"))
    zips = sorted(zip_dir.glob("*_json.zip")) if zip_dir.exists() else []
    reg_map = build_registry_map(zips) if zips else {}
    out_dir = ROOT / "data" / "predictions"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "registry_map.json").write_text(json.dumps(
        {"source_zips": [z.name for z in zips], "names": reg_map}, indent=1))
    master = build_player_master(ROOT, reg_map)
    master.to_csv(out_dir / "player_master.csv", index=False)
    print(f"player_master: {len(master)} rows; registry IDs resolved: "
          f"{master.cricsheet_registry_id.notna().sum()}; "
          f"registry map names: {len(reg_map)} from {[z.name for z in zips]}")
    # Squad-rule validation report (plan task 3.3): flags only, never
    # fails the build -- squads evolve in-season.
    from src.prediction.squad_validation import validate_squads
    report = validate_squads(master)
    report.to_csv(out_dir / "squad_validation_report.csv", index=False)
    flagged = report[~report["overseas_within_reported_range"]]
    print(f"squad validation: {len(report)} teams, "
          f"{len(flagged)} flagged outside the reported 6-8 overseas "
          f"range: {sorted(flagged['team'])}")
