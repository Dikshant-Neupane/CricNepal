#!/usr/bin/env python3
"""Populate player_of_match in the canonical matches table from the
cricsheet NPL bundle (plan task 1.5 — populate branch).

The stored canonical layer carried player_of_match /
player_of_match_id as null on all 64 S1/S2 matches, although the
cricsheet bundle (npl_json.zip) carries info.player_of_match for
every one of them and scripts/ingest_cricsheet.py captures it (the
stored layer evidently predates that capture). This script applies
exactly the ingest's semantics to the stored table:

    pom = info["player_of_match"][0]           (raw surface name)
    player_of_match_id = "player_" + pom.lower().replace(" ", "_")

The write is limited to those two columns: the script verifies
before writing that every match_id in the table has a bundle JSON,
and after writing that no other column changed. Values are the
cricsheet surface forms (e.g. "AK Sah"), as the ingest stores them;
canonical-name resolution is the identity registry's job, not this
column's.

Usage:
    python scripts/populate_player_of_match.py /path/to/npl_json.zip
"""
from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
MATCHES = ROOT / "data" / "normalized" / "matches_normalized.parquet"


def _slug(name: str) -> str:
    # Identical to scripts/ingest_cricsheet.py::slug.
    return "player_" + name.strip().lower().replace(" ", "_")


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    bundle = Path(sys.argv[1])
    with zipfile.ZipFile(bundle) as z:
        pom_by_match: dict[str, str] = {}
        for name in z.namelist():
            if not name.endswith(".json"):
                continue
            info = json.loads(z.read(name)).get("info", {})
            pom = info.get("player_of_match") or []
            if pom:
                pom_by_match[f"espn_{Path(name).stem}"] = pom[0]
    print(f"bundle: {len(pom_by_match)} matches carry player_of_match")

    df = pd.read_parquet(MATCHES)
    before = df.copy()
    missing = [m for m in df["match_id"] if m not in pom_by_match]
    if missing:
        print(f"ERROR: {len(missing)} table matches have no bundle "
              f"value (e.g. {missing[:3]}); refusing to write",
              file=sys.stderr)
        return 1
    df["player_of_match"] = df["match_id"].map(pom_by_match)
    df["player_of_match_id"] = df["player_of_match"].map(_slug)

    untouched = [c for c in df.columns
                 if c not in ("player_of_match", "player_of_match_id")]
    pd.testing.assert_frame_equal(
        before[untouched].reset_index(drop=True),
        df[untouched].reset_index(drop=True))
    assert df["player_of_match"].notna().all()
    df.to_parquet(MATCHES, index=False)
    print(f"populated player_of_match (+_id) on {len(df)} matches in "
          f"{MATCHES.relative_to(ROOT)}; all other columns verified "
          "unchanged")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
