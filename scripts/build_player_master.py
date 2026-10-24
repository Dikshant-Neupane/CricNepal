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
