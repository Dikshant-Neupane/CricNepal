#!/usr/bin/env python3
"""Build TU Ground (Kirtipur) par tables from the project's own
ball-by-ball data — the venue file the prediction and matchday work
reads from, instead of aggregator numbers that disagree with each
other.

Splits that matter at a single venue:
  * innings (1st vs 2nd)
  * phase (powerplay / middle / death) — from the BBB `phase` column
  * slot: Day vs Day-Night. The normalized data's `day_night` column is
    a useless default (all 64 matches say "Day-Night") and start times
    were not recorded, so the slot is DERIVED, with the rule stated
    here and in every output:
      - S1 (2024): all matches were day matches — floodlights were
        installed only for S2. Slot = "Day" for every S1 match.
      - S2 (2025): two starts per double-header day, 11:45 and 16:00.
        First match of a date = "Day", second = "Day-Night".
        A single-match S2 date cannot be assigned honestly ->
        "S2 single (slot unverified)" and it is excluded from the
        Day/Day-Night splits (kept in season totals).
      - S3 (2026): real start times exist in s3_fixtures.csv
        (12:30 -> "Day", 17:00 -> "Day-Night"), joined by match_id
        when S3 matches reach the normalized data.
    Strip identity is not recorded historically; the matchday capture
    log builds it from S3 onward.

Outputs (data/venue/):
  tu_par_summary.csv   per-split 1st-innings distribution + chase record
  tu_phase_par.csv     per split x innings x phase scoring rates
  tu_chase_bands.csv   chase success by 1st-innings total band
  tu_wickets_by_type.csv  wickets by bowling type (Pace/Spin), with
                       bowler-type coverage so the number is never
                       read without its denominator

Super Overs (innings 3-4 in the BBB) are excluded everywhere.
Re-run after every ingested match: python scripts/build_tu_par_tables.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "venue"
BANDS = [(0, 129), (130, 139), (140, 149), (150, 159),
         (160, 169), (170, 179), (180, 999)]


def derive_slot(matches: pd.DataFrame, fixtures: pd.DataFrame | None) -> pd.Series:
    """Day / Day-Night per the derivation in the module docstring."""
    m = matches.sort_values(["match_date", "match_number"])
    pos = m.groupby(["season", "match_date"]).cumcount()
    counts = m.groupby(["season", "match_date"])["match_id"].transform("size")
    slot = pd.Series("Day", index=m.index, dtype=object)
    s2 = m.season == "S2"
    slot[s2 & (counts == 1)] = "S2 single (slot unverified)"
    slot[s2 & (counts > 1) & (pos == 1)] = "Day-Night"
    slot[s2 & (counts > 1) & (pos == 0)] = "Day"
    if fixtures is not None and "S3" in set(m.season):
        times = fixtures.set_index("match_id")["start_time_local"].to_dict()
        for idx, row in m[m.season == "S3"].iterrows():
            t = str(times.get(row.match_id, ""))
            slot[idx] = "Day-Night" if t.startswith("17") else "Day"
    return slot.reindex(matches.index)


def load() -> tuple[pd.DataFrame, pd.DataFrame]:
    matches = pd.read_parquet(ROOT / "data/normalized/matches_normalized.parquet")
    bbb = pd.read_parquet(ROOT / "data/normalized/ball_by_ball_normalized.parquet")
    fx_path = ROOT / "data/fixtures/s3_fixtures.csv"
    fixtures = pd.read_csv(fx_path) if fx_path.exists() else None
    matches["slot"] = derive_slot(matches, fixtures)
    bbb = bbb[bbb.innings.isin([1, 2])].merge(
        matches[["match_id", "season", "slot"]], on="match_id", how="left")
    return matches, bbb


def split_frames(matches: pd.DataFrame) -> dict[str, pd.DataFrame]:
    return {
        "All matches": matches,
        "S1 (day era)": matches[matches.season == "S1"],
        "S2 (floodlight era)": matches[matches.season == "S2"],
        "Day slot": matches[matches.slot == "Day"],
        "Day-Night slot": matches[matches.slot == "Day-Night"],
    }


def par_summary(matches: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for name, d in split_frames(matches).items():
        decided = d[d.winner_name.notna()]
        rows.append({
            "split": name, "matches": len(d),
            "inn1_mean": round(d.innings_1_runs.mean(), 1),
            "inn1_median": float(d.innings_1_runs.median()),
            "inn1_q1": float(d.innings_1_runs.quantile(0.25)),
            "inn1_q3": float(d.innings_1_runs.quantile(0.75)),
            "inn1_min": int(d.innings_1_runs.min()),
            "inn1_max": int(d.innings_1_runs.max()),
            "inn2_mean": round(d.innings_2_runs.mean(), 1),
            "bat_first_wins": int((decided.winner_name == decided.innings_1_team).sum()),
            "chase_wins": int((decided.winner_name == decided.innings_2_team).sum()),
            "chase_win_pct": round(
                (decided.winner_name == decided.innings_2_team).mean() * 100, 1)
            if len(decided) else np.nan,
        })
    return pd.DataFrame(rows)


def phase_par(bbb: pd.DataFrame) -> pd.DataFrame:
    frames = {"All matches": bbb, "Day slot": bbb[bbb.slot == "Day"],
              "Day-Night slot": bbb[bbb.slot == "Day-Night"]}
    rows = []
    for name, d in frames.items():
        g = d.groupby(["innings", "phase"]).agg(
            runs=("runs_total", "sum"), balls=("runs_total", "size"),
            wickets=("is_wicket", "sum"),
            dots=("is_dot_ball", "sum"), boundaries=("is_boundary", "sum"))
        for (inn, phase), r in g.iterrows():
            rows.append({
                "split": name, "innings": int(inn), "phase": phase,
                "runs": int(r.runs), "balls": int(r.balls),
                "run_rate": round(r.runs / (r.balls / 6), 2),
                "wickets": int(r.wickets),
                "dot_pct": round(r.dots / r.balls * 100, 1),
                "boundary_pct": round(r.boundaries / r.balls * 100, 1),
            })
    return pd.DataFrame(rows)


def chase_bands(matches: pd.DataFrame) -> pd.DataFrame:
    decided = matches[matches.winner_name.notna()]
    rows = []
    for lo, hi in BANDS:
        d = decided[(decided.innings_1_runs >= lo) & (decided.innings_1_runs <= hi)]
        rows.append({
            "inn1_band": f"{lo}-{hi if hi < 900 else '+'}",
            "matches": len(d),
            "chase_wins": int((d.winner_name == d.innings_2_team).sum()),
            "chase_win_pct": round(
                (d.winner_name == d.innings_2_team).mean() * 100, 1) if len(d) else np.nan,
        })
    return pd.DataFrame(rows)


def wickets_by_type(bbb: pd.DataFrame, root: Path = ROOT) -> pd.DataFrame:
    """Wickets by bowling type via the enriched profiles' bowling_type.
    Coverage is reported per season: the share of wicket-taking bowlers
    whose type is known. 'bowler run out' style team wickets excluded —
    only deliveries with a credited bowler."""
    prof = pd.read_csv(root / "data/player_profiles/enriched_players_20260521.csv")
    ptype = (prof.dropna(subset=["bowling_type"])
             .drop_duplicates("player_name")
             .set_index("player_name")["bowling_type"].to_dict())

    def group(t: str) -> str:
        t = str(t).lower()
        if "spin" in t or "orthodox" in t or "wrist" in t or "leg" in t or "off" in t:
            return "Spin"
        if "pace" in t or "medium" in t or "fast" in t or "seam" in t:
            return "Pace"
        return "Other/unknown"

    wk = bbb[(bbb.is_wicket) & (bbb.dismissal_type != "run out")].copy()
    wk["btype"] = wk.bowler_name.map(lambda n: group(ptype.get(n, "")))
    rows = []
    for season, d in wk.groupby("season"):
        known = d[d.btype.isin(["Pace", "Spin"])]
        rows.append({
            "season": season, "bowler_wickets": len(d),
            "pace_wkts": int((d.btype == "Pace").sum()),
            "spin_wkts": int((d.btype == "Spin").sum()),
            "type_coverage_pct": round(len(known) / len(d) * 100, 1) if len(d) else np.nan,
            "spin_share_of_known_pct": round(
                (known.btype == "Spin").mean() * 100, 1) if len(known) else np.nan,
        })
    return pd.DataFrame(rows)


def main() -> None:
    matches, bbb = load()
    OUT.mkdir(parents=True, exist_ok=True)
    par_summary(matches).to_csv(OUT / "tu_par_summary.csv", index=False)
    phase_par(bbb).to_csv(OUT / "tu_phase_par.csv", index=False)
    chase_bands(matches).to_csv(OUT / "tu_chase_bands.csv", index=False)
    wickets_by_type(bbb).to_csv(OUT / "tu_wickets_by_type.csv", index=False)
    unver = int((matches.slot == "S2 single (slot unverified)").sum())
    print(f"TU par tables written to {OUT} from {len(matches)} matches "
          f"({(matches.season == 'S1').sum()} S1, {(matches.season == 'S2').sum()} S2); "
          f"slot derivation left {unver} S2 single-match day(s) unverified.")


if __name__ == "__main__":
    sys.exit(main())
