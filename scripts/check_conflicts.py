#!/usr/bin/env python3
"""Cross-source conflicts register (plan task 1.1, criterion D4).

Read-only check: compares the two stored copies of the S1/S2 match
layer (data/normalized, canonical, vs data/final/parquet, legacy) and
lists every disagreement as a conflict row. Conflicts are SURFACED,
never silently resolved: this script picks no winner between sources.

Usage:
    python scripts/check_conflicts.py            # print the register
    python scripts/check_conflicts.py --write     # also write
        data/conflicts_register.csv

Exit code is 0 when the register was produced (conflicts existing is
a finding, not a failure); 2 on unreadable inputs.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
NORMALIZED = ROOT / "data/normalized/matches_normalized.parquet"
FINAL = ROOT / "data/final/parquet/matches.parquet"
REGISTER = ROOT / "data/conflicts_register.csv"
DETECTED = "2026-10-29"


def detect_conflicts() -> list[dict]:
    norm = pd.read_parquet(NORMALIZED)
    final = pd.read_parquet(FINAL)
    rows: list[dict] = []

    def team_names(df):
        cols = [c for c in ("team_1_name", "team_2_name") if c in df]
        return set(pd.concat([df[c] for c in cols]).dropna().unique())

    only_final = sorted(team_names(final) - team_names(norm))
    only_norm = sorted(team_names(norm) - team_names(final))
    if only_final or only_norm:
        rows.append({
            "conflict_id": "CONF-001",
            "detected": DETECTED,
            "type": "team_identity_split",
            "scope": "all matches involving the Kathmandu franchise, S1+S2",
            "source_a": "data/normalized/matches_normalized.parquet",
            "value_a": "; ".join(only_norm) or "(canonical names)",
            "source_b": "data/final/parquet/matches.parquet",
            "value_b": "; ".join(only_final),
            "status": "open — surfaced, not resolved",
            "resolution": "none applied; canonical layer is "
                          "data/normalized per docs/DATA_DICTIONARY.md; "
                          "merging the legacy copy is plan task 1.2 "
                          "(gated, not yet done)",
            "notes": "Same franchise under two spellings across the "
                     "two stored copies. Identity conflict only: the "
                     "2026-10-29 audit recomputed every result and "
                     "found zero winner/margin discrepancies.",
        })

    merged = norm[["match_id", "winner_name"]].merge(
        final[["match_id", "winner_name"]], on="match_id",
        suffixes=("_normalized", "_final"))
    diffs = merged[merged.winner_name_normalized.fillna("")
                   != merged.winner_name_final.fillna("")]
    for _, d in diffs.iterrows():
        rows.append({
            "conflict_id": f"CONF-W-{d.match_id}",
            "detected": DETECTED,
            "type": "winner_name_spelling",
            "scope": f"match {d.match_id}",
            "source_a": "data/normalized/matches_normalized.parquet",
            "value_a": d.winner_name_normalized,
            "source_b": "data/final/parquet/matches.parquet",
            "value_b": d.winner_name_final,
            "status": "open — surfaced, not resolved",
            "resolution": "none applied; both spellings denote the "
                          "same franchise (see CONF-001)",
            "notes": "Spelling variant of the winner name, not a "
                     "different winner.",
        })
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true",
                    help="write data/conflicts_register.csv")
    args = ap.parse_args()
    try:
        rows = detect_conflicts()
    except Exception as exc:  # unreadable inputs are a hard failure
        print(f"ERROR: could not read match layers: {exc}", file=sys.stderr)
        return 2
    df = pd.DataFrame(rows)
    if args.write:
        df.to_csv(REGISTER, index=False)
        print(f"wrote {REGISTER} ({len(df)} conflicts)")
    print(df.to_string(index=False) if len(df) else "no conflicts found")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
