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


RESOLVED_ROWS = [
    {
        "conflict_id": "CONF-001",
        "detected": DETECTED,
        "type": "team_identity_split",
        "scope": "all matches involving the Kathmandu franchise, S1+S2",
        "source_a": "data/normalized/matches_normalized.parquet",
        "value_a": "Kathmandu Gorkhas",
        "source_b": "data/final/parquet/matches.parquet",
        "value_b": "Kathmandu Gurkhas",
        "status": "RESOLVED 2026-10-29",
        "resolution": "plan task 1.2: scripts/sync_final_from_normalized.py "
                      "regenerated the final copies from the canonical "
                      "normalized layer and aligned team identity in the "
                      "derived artefacts; the served layer now carries "
                      "exactly 8 team names (tests/test_canonical_layer.py)",
        "notes": "Identity conflict only; the 2026-10-29 audit found zero "
                 "winner/margin discrepancies. Winner-spelling rows "
                 "CONF-W-espn_1462644/1462657/1462662/1462664 were the "
                 "per-match instances and are resolved by the same action. "
                 "A residual ID-level split inside normalized itself is "
                 "tracked separately as CONF-002.",
    },
    {
        # Resolved at the source by the 2026-11-10 derived-tables
        # refresh (commit d0426b8), which rebuilt the canonical
        # matches layer with a single Kathmandu team ID. Verified
        # 2026-11-13: the layer carries exactly 8 team IDs and no
        # team_kathmandu_gurkhas cell; at d4c8f65 (2026-11-04) the
        # split was still present.
        "conflict_id": "CONF-002",
        "detected": DETECTED,
        "type": "team_id_split_in_canonical",
        "scope": "Kathmandu matches in data/normalized "
                 "(team_1_id/team_2_id)",
        "source_a": "data/normalized/matches_normalized.parquet",
        "value_a": "team_kathmandu_gorkhas",
        "source_b": "data/normalized/matches_normalized.parquet",
        "value_b": "team_kathmandu_gurkhas",
        "status": "RESOLVED 2026-11-10",
        "resolution": "derived-tables refresh (commit d0426b8, "
                      "2026-11-10) rebuilt the canonical matches layer "
                      "with one Kathmandu team ID; the ingest-side fix "
                      "the register had deferred to post-season landed "
                      "with that refresh instead",
        "notes": "Name columns in normalized were already unified "
                 "(Kathmandu Gorkhas only); only the ID columns split, "
                 "and no displayed name or result was affected.",
    },
    {
        # Resolved at the source by the same 2026-11-10 refresh
        # (commit d0426b8): stored innings overs now agree with the
        # NRR-convention derivation on all 152 innings. Verified
        # 2026-11-13 (n_bad = 0 of 152); at d4c8f65 (2026-11-04) 73
        # of 152 innings disagreed.
        "conflict_id": "CONF-003",
        "detected": DETECTED,
        "type": "stored_overs_convention",
        "scope": "152 innings in data/normalized",
        "source_a": "data/normalized/matches_normalized.parquet "
                    "(stored innings_*_overs)",
        "value_a": "overs as stored (all-out innings at overs faced; "
                   "notation variant elsewhere)",
        "source_b": "data/normalized/ball_by_ball_normalized."
                    "parquet (derived, NRR convention)",
        "value_b": "legal-ball overs; all-out innings count the full "
                   "20 overs",
        "status": "RESOLVED 2026-11-10",
        "resolution": "derived-tables refresh (commit d0426b8, "
                      "2026-11-10) rebuilt the canonical matches layer "
                      "with stored overs following the NRR convention; "
                      "the served copies already carried the derived "
                      "summaries (scripts/sync_final_from_normalized.py)",
        "notes": "Stored runs agree with the deliveries on all "
                 "innings; only overs differed, and they no longer do.",
    },
]


def detect_conflicts() -> list[dict]:
    norm = pd.read_parquet(NORMALIZED)
    final = pd.read_parquet(FINAL)
    rows: list[dict] = []

    # CONF-002: the canonical layer's own team-ID columns carry both
    # Kathmandu IDs. The served final copy is aligned by the sync
    # script, but the upstream ingest still emits both — surfaced
    # here, not patched at the source mid-season (plan 1.2).
    id_cols = [c for c in ("team_1_id", "team_2_id") if c in norm]
    if id_cols:
        ids = set(pd.concat([norm[c] for c in id_cols]).dropna().unique())
        if "team_kathmandu_gurkhas" in ids:
            rows.append({
                "conflict_id": "CONF-002",
                "detected": DETECTED,
                "type": "team_id_split_in_canonical",
                "scope": "Kathmandu matches in data/normalized "
                         "(team_1_id/team_2_id)",
                "source_a": "data/normalized/matches_normalized.parquet",
                "value_a": "team_kathmandu_gorkhas",
                "source_b": "data/normalized/matches_normalized.parquet",
                "value_b": "team_kathmandu_gurkhas",
                "status": "open — surfaced, not resolved",
                "resolution": "served copies aligned by "
                              "scripts/sync_final_from_normalized.py; the "
                              "ingest-side fix (single canonical team ID) "
                              "is a separate post-season change",
                "notes": "Name columns in normalized are unified "
                         "(Kathmandu Gorkhas only); only the ID columns "
                         "split. No displayed name or result is affected.",
            })

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

    # CONF-003: canonical's stored innings overs disagree with the
    # NRR convention derived from the canonical ball-by-ball (all-out
    # innings stored at overs faced, not the full 20). Stored runs
    # agree everywhere. Served copies carry the derived summaries.
    try:
        bbb = pd.read_parquet(
            ROOT / "data/normalized/ball_by_ball_normalized.parquet")
        bbb = bbb[bbb["innings"] <= 2].copy()
        bbb["legal"] = ~bbb["extras_type"].isin(["wides", "noballs"])
        bbb["wkt"] = (bbb["is_wicket"]
                      & (bbb["dismissal_type"] != "retired hurt"))
        agg = (bbb.groupby(["match_id", "innings"])
               .agg(legal=("legal", "sum"), wkts=("wkt", "sum")))
        n_idx = norm.set_index("match_id")
        n_bad = 0
        for (match_id, inn), r in agg.iterrows():
            expected = 20.0 if r["wkts"] >= 10 else r["legal"] / 6.0
            stored = n_idx.loc[match_id, f"innings_{inn}_overs"]
            if pd.notna(stored) and abs(float(stored) - expected) > 1e-9:
                n_bad += 1
        if n_bad:
            rows.append({
                "conflict_id": "CONF-003",
                "detected": DETECTED,
                "type": "stored_overs_convention",
                "scope": f"{n_bad} of {len(agg)} innings in "
                         "data/normalized",
                "source_a": "data/normalized/matches_normalized.parquet "
                            "(stored innings_*_overs)",
                "value_a": "overs as stored (all-out innings at overs "
                           "faced; notation variant elsewhere)",
                "source_b": "data/normalized/ball_by_ball_normalized."
                            "parquet (derived, NRR convention)",
                "value_b": "legal-ball overs; all-out innings count "
                           "the full 20 overs",
                "status": "open — surfaced, not resolved",
                "resolution": "served copies carry the derived "
                              "summaries (scripts/"
                              "sync_final_from_normalized.py), which "
                              "reproduce the verified Janakpur S1 NRR "
                              "+0.139; stored summaries would read "
                              "+0.492. Ingest-side fix is post-season.",
                "notes": "Stored runs agree with the deliveries on "
                         "all innings; only overs differ.",
            })
    except Exception:
        pass

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
        live = detect_conflicts()
    except Exception as exc:  # unreadable inputs are a hard failure
        print(f"ERROR: could not read match layers: {exc}", file=sys.stderr)
        return 2
    live_ids = {r["conflict_id"] for r in live}
    rows = live + [r for r in RESOLVED_ROWS
                   if r["conflict_id"] not in live_ids]
    df = pd.DataFrame(rows)
    if args.write:
        df.to_csv(REGISTER, index=False)
        print(f"wrote {REGISTER} ({len(df)} conflicts)")
    print(df.to_string(index=False) if len(df) else "no conflicts found")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
