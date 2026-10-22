#!/usr/bin/env python
"""
Cricsheet JSON -> CricNepal parquet ingestion
=============================================
Converts cricsheet.org ball-by-ball JSON files (v1 format) into the project's
matches / ball_by_ball parquet schema, so new-season matches flow through the
existing pipeline (normalize -> features -> analytics -> dashboard).

Season mapping is by match date year: 2024 -> S1, 2025 -> S2, 2026 -> S3.

Usage:
    python scripts/ingest_cricsheet.py /path/to/npl_json [--append]

    --append   Merge into data/final/parquet/{matches,ball_by_ball}.parquet,
               skipping match_ids that already exist. Without --append the
               script writes preview files to data/final/parquet/_preview_*
               and prints a summary (safe default: touches nothing).

Source: https://cricsheet.org/downloads/  (npl_json.zip for NPL matches)
Conventions match the existing S1/S2 rows exactly:
    match_id = "espn_<cricsheet_id>", source_system = "Cricsheet",
    over 0-indexed, ball 1-indexed within over, ball_sequence cumulative
    per innings, phase Powerplay(0-5)/Middle(6-14)/Death(15-19),
    is_dot_ball = (runs_total == 0), boundary_type Four/Six.
"""

import argparse
import json
import sys
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

PARQUET_DIR = PROJECT_ROOT / "data" / "final" / "parquet"

SEASON_BY_YEAR = {2024: "S1", 2025: "S2", 2026: "S3"}

# Team-name variants seen in cricsheet data -> the canonical names used
# throughout this project's existing S1/S2 rows.
TEAM_NAME_FIXES = {
    "Sudur Paschim Royals": "Sudurpaschim Royals",
}


def canon_team(name: str) -> str:
    return TEAM_NAME_FIXES.get(name, name)


def slug(name: str) -> str:
    return "player_" + name.strip().lower().replace(" ", "_")


def phase_for(over_0idx: int) -> str:
    if over_0idx <= 5:
        return "Powerplay"
    if over_0idx <= 14:
        return "Middle"
    return "Death"


def parse_match(path: Path, run_id: str):
    """Parse one cricsheet JSON file -> (match_row dict, [delivery_row dicts])."""
    stem = path.stem
    data = json.loads(path.read_text(encoding="utf-8"))
    info = data["info"]
    meta = data.get("meta", {})

    match_id = f"espn_{stem}"
    match_date = info["dates"][0]
    year = int(match_date[:4])
    # Production parquet stores match_date as datetime.date objects.
    match_date = date.fromisoformat(match_date)
    season = SEASON_BY_YEAR.get(year, f"S{year - 2023}")

    teams = [canon_team(t) for t in info["teams"]]
    toss = info.get("toss", {})
    outcome = info.get("outcome", {})
    event = info.get("event", {})

    # --- outcome ---
    winner = canon_team(outcome["winner"]) if outcome.get("winner") else None
    win_by, win_margin = None, None
    result_status = "normal"
    if "by" in outcome:
        by = outcome["by"]
        if "runs" in by:
            win_by, win_margin = "Runs", by["runs"]
        elif "wickets" in by:
            win_by, win_margin = "Wickets", by["wickets"]
        elif "innings" in by:
            win_by, win_margin = "Innings", by["innings"]
    elif outcome.get("result"):
        result_status = outcome["result"]  # e.g. "no result", "tie"
    elif "method" in outcome:
        result_status = f"DLS ({outcome['method']})"

    # team_1 / team_2 are alphabetical in the existing data
    team_a, team_b = sorted(teams)
    venue = (info.get("venue") or "").replace(", Kirtipur", "").strip() or None

    pom = info.get("player_of_match") or []
    pom = pom[0] if pom else None

    # --- innings summaries ---
    innings_summaries = []
    deliveries = []
    seq = 0  # ball_sequence is cumulative across the whole match (not per innings)
    raw_teams = info["teams"]
    for inn_idx, inn in enumerate(data["innings"], start=1):
        # Delivery rows in the existing data keep raw cricsheet team names
        # (team normalization was only ever applied to the matches table).
        batting_team = inn["team"]
        bowling_team = raw_teams[1] if raw_teams[0] == batting_team else raw_teams[0]
        canon_batting = canon_team(batting_team)
        total_runs = 0
        total_wkts = 0
        total_extras = 0
        balls = 0
        for over_obj in inn["overs"]:
            over_0idx = int(over_obj["over"])
            for b_idx, dlv in enumerate(over_obj["deliveries"], start=1):
                seq += 1
                balls += 1
                runs = dlv["runs"]
                extras = dlv.get("extras", {})
                extras_type = next(iter(extras.keys()), None)
                wickets = dlv.get("wickets", [])
                is_wicket = bool(wickets)
                wk = wickets[0] if wickets else {}
                fielders = wk.get("fielders", [])
                fielder = fielders[0].get("name") if fielders else None
                batter_runs = runs["batter"]
                deliveries.append({
                    "match_id": match_id,
                    "innings": inn_idx,
                    "over": over_0idx,
                    "ball": b_idx,
                    "ball_sequence": seq,
                    "batter_id": slug(dlv["batter"]),
                    "batter_name": dlv["batter"],
                    "non_striker_id": slug(dlv["non_striker"]) if dlv.get("non_striker") else None,
                    "non_striker_name": dlv.get("non_striker"),
                    "bowler_id": slug(dlv["bowler"]),
                    "bowler_name": dlv["bowler"],
                    "runs_off_bat": batter_runs,
                    "runs_extras": runs["extras"],
                    "runs_total": runs["total"],
                    "extras_type": extras_type,
                    "is_boundary": batter_runs in (4, 6),
                    "boundary_type": "Four" if batter_runs == 4 else ("Six" if batter_runs == 6 else None),
                    "is_wicket": is_wicket,
                    "dismissal_type": wk.get("kind"),
                    "dismissed_batter_id": slug(wk["player_out"]) if wk.get("player_out") else None,
                    "dismissed_batter_name": wk.get("player_out"),
                    "fielder_id": slug(fielder) if fielder else None,
                    "fielder_name": fielder,
                    "batting_team": batting_team,
                    "bowling_team": bowling_team,
                    "phase": phase_for(over_0idx),
                    "is_dot_ball": runs["total"] == 0,
                    "ingestion_run_id": run_id,
                })
                total_runs += runs["total"]
                total_extras += runs["extras"]
                if is_wicket:
                    total_wkts += 1
        overs = balls // 6 + (balls % 6) / 10
        innings_summaries.append({
            "team": canon_batting, "runs": total_runs, "wickets": total_wkts,
            "overs": round(overs, 1), "extras": total_extras,
        })

    now = datetime.now(timezone.utc)
    officials = info.get("officials", {})
    match_row = {
        "match_id": match_id,
        "season": season,
        "tournament_id": None,
        "tournament_name": event.get("name", "Nepal Premier League"),
        "match_number": event.get("match_number"),
        "match_date": match_date,
        "match_start_time": None,
        "match_format": "T20",
        "gender": info.get("gender"),
        "match_type": info.get("match_type"),
        "day_night": None,
        "team_1_id": None,
        "team_1_name": team_a,
        "team_2_id": None,
        "team_2_name": team_b,
        "venue_id": None,
        "venue_name": venue,
        "city": info.get("city"),
        "country": "Nepal",
        "toss_winner_id": None,
        "toss_winner_name": canon_team(toss["winner"]) if toss.get("winner") else None,
        "toss_decision": toss.get("decision"),
        "result_status": result_status,
        "winner_name": winner,
        "win_margin": win_margin,
        "win_by": win_by,
        "player_of_match": pom,
        "player_of_match_id": slug(pom) if pom else None,
        "home_away_neutral": "neutral",
        "match_importance": None,
        "opposition_strength": None,
        "opposition_style": None,
        "pts_table_position": None,
        "qualification_status": None,
        "innings_1_team": innings_summaries[0]["team"] if len(innings_summaries) > 0 else None,
        "innings_1_runs": innings_summaries[0]["runs"] if len(innings_summaries) > 0 else None,
        "innings_1_wickets": innings_summaries[0]["wickets"] if len(innings_summaries) > 0 else None,
        "innings_1_overs": innings_summaries[0]["overs"] if len(innings_summaries) > 0 else None,
        "innings_1_extras": innings_summaries[0]["extras"] if len(innings_summaries) > 0 else None,
        "innings_2_team": innings_summaries[1]["team"] if len(innings_summaries) > 1 else None,
        "innings_2_runs": innings_summaries[1]["runs"] if len(innings_summaries) > 1 else None,
        "innings_2_wickets": innings_summaries[1]["wickets"] if len(innings_summaries) > 1 else None,
        "innings_2_overs": innings_summaries[1]["overs"] if len(innings_summaries) > 1 else None,
        "innings_2_extras": innings_summaries[1]["extras"] if len(innings_summaries) > 1 else None,
        "dls_applied": "method" in outcome,
        "dls_target": None,
        "dls_par_score": None,
        "source_system": "Cricsheet",
        "source_url": f"https://cricsheet.org/matches/{stem}",
        "ingestion_run_id": run_id,
        # Production parquet: ingestion_timestamp naive UTC, last_modified aware UTC.
        "ingestion_timestamp": now.replace(tzinfo=None),
        "parser_version": f"cricsheet_json_v{meta.get('data_version', '?')}",
        "git_commit_hash": None,
        "last_modified": now,
    }
    return match_row, deliveries


def align_to_existing(existing: pd.DataFrame, fresh: pd.DataFrame):
    """Coerce `fresh` to the production parquet's per-column types.

    The existing parquets were written by the original pipeline and carry
    its type choices; freshly parsed rows must match them or the append
    write fails (e.g. match_date date-objects vs ISO strings). Rules:
    - a production column that is entirely null carries no type
      information: promote it to the fresh column's dtype instead of
      forcing fresh values into a degenerate type (e.g. float64).
    - datetime columns: parse fresh values, matching tz-awareness.
    - float/integer columns: numeric-coerce fresh values.
    Returns (existing, fresh) ready for concat.
    """
    existing = existing.copy()
    fresh = fresh.copy()
    for col in existing.columns:
        if col not in fresh.columns:
            continue
        et, ft = existing[col].dtype, fresh[col].dtype
        if et == ft:
            continue
        if existing[col].isna().all() and fresh[col].notna().any():
            try:
                existing[col] = existing[col].astype(ft)
                continue
            except (ValueError, TypeError):
                pass
        if pd.api.types.is_datetime64_any_dtype(et):
            parsed = pd.to_datetime(fresh[col], utc=True)
            if getattr(et, "tz", None) is None:
                parsed = parsed.dt.tz_localize(None)
            fresh[col] = parsed
        elif pd.api.types.is_float_dtype(et):
            fresh[col] = pd.to_numeric(fresh[col], errors="coerce").astype("float64")
        elif pd.api.types.is_integer_dtype(et):
            fresh[col] = pd.to_numeric(fresh[col], errors="coerce").astype(et)
    return existing, fresh


# --- Derived tables -------------------------------------------------------
# player_innings / phase_summary live in data/final/parquet and are read by
# the dashboard, but the original pipeline that built them is not in this
# repo. Their derivation from ball_by_ball was reverse-engineered and
# verified to reproduce all 64 S1/S2 matches exactly (1,917 + 378 rows,
# zero value differences). Production conventions replicated faithfully:
# balls_faced excludes wides AND no-balls; bowling runs_conceded is the
# full runs_total; a dismissal is recorded only when the dismissed player
# is the striker; economy_rate is 0.0 below 6 balls bowled; dismissal_type
# and maidens are unpopulated (null) in production; percentage columns in
# phase_summary round half-up to 1dp.
BOWLER_WICKETS = {"bowled", "caught", "caught and bowled", "lbw", "stumped",
                  "hit wicket", "retired out"}


def _pct_half_up(part: float, whole: float) -> float:
    if not whole:
        return 0.0
    return float(Decimal(str(part / whole * 100)).quantize(
        Decimal("0.1"), rounding=ROUND_HALF_UP))


def derive_player_innings(bb: pd.DataFrame, run_id: str) -> pd.DataFrame:
    """One row per (match, innings, player) for the given deliveries."""
    frames = []
    for (match_id, innings), grp in bb.groupby(["match_id", "innings"], sort=False):
        batting_team = grp["batting_team"].iloc[0]
        bat = grp.copy()
        bat["faced"] = (~bat["extras_type"].isin(["wides", "noballs"])).astype(int)
        batting = bat.groupby(["batter_id", "batter_name"], sort=False).agg(
            runs_scored=("runs_off_bat", "sum"), balls_faced=("faced", "sum"),
            fours=("runs_off_bat", lambda s: (s == 4).sum()),
            sixes=("runs_off_bat", lambda s: (s == 6).sum())).reset_index().rename(
            columns={"batter_id": "player_id", "batter_name": "player_name"})
        dis = grp[(grp["dismissed_batter_name"].notna())
                  & (grp["dismissed_batter_name"] == grp["batter_name"])][
            ["dismissed_batter_id", "phase"]].drop_duplicates("dismissed_batter_id")
        batting = batting.merge(dis, left_on="player_id",
                                right_on="dismissed_batter_id", how="left").drop(
            columns=["dismissed_batter_id"]).rename(columns={"phase": "dismissal_phase"})
        batting["dismissed"] = batting["dismissal_phase"].notna()

        bowl = grp.copy()
        bowl["legal"] = (~bowl["extras_type"].isin(["wides", "noballs"])).astype(int)
        bowl["bwicket"] = bowl.apply(
            lambda r: 1 if r["is_wicket"] and r["dismissal_type"] in BOWLER_WICKETS else 0,
            axis=1)
        bowling = bowl.groupby(["bowler_id", "bowler_name"], sort=False).agg(
            balls_bowled=("legal", "sum"), runs_conceded=("runs_total", "sum"),
            wickets_taken=("bwicket", "sum"),
            dot_balls=("is_dot_ball", "sum")).reset_index().rename(
            columns={"bowler_id": "player_id", "bowler_name": "player_name"})

        rows = batting.merge(bowling, on=["player_id", "player_name"], how="outer")
        rows.insert(0, "match_id", match_id)
        rows.insert(1, "innings", innings)
        rows["team_name"] = batting_team  # production keeps raw delivery names
        batted = rows["balls_faced"].notna()
        rows["player_role"] = np.where(batted, "batter", "bowler")
        for c in ["runs_scored", "balls_faced", "fours", "sixes", "balls_bowled",
                  "runs_conceded", "wickets_taken", "dot_balls"]:
            rows[c] = rows[c].fillna(0).astype(int)
        rs, bf = rows["runs_scored"].to_numpy(float), rows["balls_faced"].to_numpy(float)
        rows["strike_rate"] = np.where(
            bf > 0, np.round(rs / np.where(bf == 0, 1, bf) * 100, 2), 0.0)
        rc, bl = rows["runs_conceded"].to_numpy(float), rows["balls_bowled"].to_numpy(float)
        rows["economy_rate"] = np.where(
            bl >= 6, np.round(rc / (np.where(bl == 0, 1, bl) / 6), 2), 0.0)
        rows["dismissed"] = rows["dismissed"].fillna(False)
        rows["dismissal_type"] = None
        rows["maidens"] = np.nan
        rows["ingestion_run_id"] = run_id
        frames.append(rows)
    cols = ["match_id", "innings", "player_id", "player_name", "team_name",
            "player_role", "runs_scored", "balls_faced", "fours", "sixes",
            "strike_rate", "dismissed", "dismissal_type", "dismissal_phase",
            "balls_bowled", "runs_conceded", "wickets_taken", "dot_balls",
            "economy_rate", "maidens", "ingestion_run_id"]
    return pd.concat(frames, ignore_index=True)[cols] if frames else pd.DataFrame(columns=cols)


def derive_phase_summary(bb: pd.DataFrame) -> pd.DataFrame:
    """One row per (match, innings, phase) for the given deliveries."""
    phase_order = {"Powerplay": 0, "Middle": 1, "Death": 2}
    rows = []
    for (match_id, innings, phase), grp in bb.groupby(
            ["match_id", "innings", "phase"], sort=False):
        balls = len(grp)
        runs = float(grp["runs_total"].sum())
        boundaries = float(grp["runs_off_bat"].isin([4, 6]).sum())
        dots = float(grp["is_dot_ball"].sum())
        rows.append({
            "match_id": match_id, "innings": innings, "phase": phase,
            "balls_bowled": balls, "runs_scored": runs,
            "wickets": float(grp["is_wicket"].sum()),
            "boundaries": boundaries,
            "sixes": float((grp["runs_off_bat"] == 6).sum()),
            "dots": dots,
            "run_rate": round(runs / (balls / 6), 2) if balls else 0.0,
            "dot_ball_pct": _pct_half_up(dots, balls),
            "boundary_pct": _pct_half_up(boundaries, balls),
        })
    out = pd.DataFrame(rows)
    if len(out):
        out["_po"] = out["phase"].map(phase_order).fillna(9)
        out = out.sort_values(["match_id", "innings", "_po"]).drop(columns=["_po"])
    return out.reset_index(drop=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("json_dir", help="Directory of cricsheet JSON files")
    ap.add_argument("--append", action="store_true",
                    help="Merge into data/final/parquet (skips existing match_ids)")
    args = ap.parse_args()

    json_dir = Path(args.json_dir)
    files = sorted(json_dir.glob("*.json"))
    if not files:
        print(f"No JSON files in {json_dir}")
        sys.exit(1)

    run_id = f"cricsheet_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    match_rows, all_deliveries = [], []
    for f in files:
        try:
            mr, dlvs = parse_match(f, run_id)
            match_rows.append(mr)
            all_deliveries.extend(dlvs)
        except Exception as e:  # noqa: BLE001 - report file, keep going
            print(f"SKIP {f.name}: {e}")

    matches_df = pd.DataFrame(match_rows)
    deliveries_df = pd.DataFrame(all_deliveries)
    print(f"Parsed {len(matches_df)} matches, {len(deliveries_df)} deliveries "
          f"(seasons: {dict(matches_df['season'].value_counts())})")

    if not args.append:
        out_m = PARQUET_DIR / "_preview_matches.parquet"
        out_d = PARQUET_DIR / "_preview_ball_by_ball.parquet"
        matches_df.to_parquet(out_m, index=False)
        deliveries_df.to_parquet(out_d, index=False)
        print(f"Preview written (nothing merged): {out_m}, {out_d}")
        return

    # --- append mode: merge, skipping existing match_ids ---
    fresh_ids = []
    for name, new_df, key in [
        ("matches", matches_df, "matches.parquet"),
        ("ball_by_ball", deliveries_df, "ball_by_ball.parquet"),
    ]:
        target = PARQUET_DIR / key
        existing = pd.read_parquet(target)
        fresh = new_df[~new_df["match_id"].isin(existing["match_id"])]
        skipped = len(new_df) - len(fresh)
        if name == "matches":
            fresh_ids = fresh["match_id"].tolist()
        if len(fresh):
            existing, fresh = align_to_existing(existing, fresh)
            if name == "ball_by_ball":
                # ball_sequence is a global counter in the existing data:
                # continue it so new rows don't collide with old ones.
                offset = int(existing["ball_sequence"].max())
                fresh = fresh.copy()
                fresh["ball_sequence"] = fresh["ball_sequence"] + offset
            merged = pd.concat([existing, fresh], ignore_index=True)
            merged.to_parquet(target, index=False)
        print(f"{name}: +{len(fresh)} new rows, {skipped} already present "
              f"(total {len(existing) + len(fresh)})")

    # --- derived tables: keep player_innings / phase_summary in step ---
    if fresh_ids:
        merged_bb = pd.read_parquet(PARQUET_DIR / "ball_by_ball.parquet")
        new_bb = merged_bb[merged_bb["match_id"].isin(fresh_ids)]
        for builder, key in [
            (lambda d: derive_player_innings(d, run_id), "player_innings.parquet"),
            (derive_phase_summary, "phase_summary.parquet"),
        ]:
            target = PARQUET_DIR / key
            derived = builder(new_bb)
            if target.exists():
                existing = pd.read_parquet(target)
                derived = derived[~derived["match_id"].isin(existing["match_id"])]
                if len(derived):
                    existing, derived = align_to_existing(existing, derived)
                    merged = pd.concat([existing, derived], ignore_index=True)
                    merged.to_parquet(target, index=False)
                print(f"{key}: +{len(derived)} derived rows "
                      f"(total {len(existing) + len(derived)})")
            else:
                derived.to_parquet(target, index=False)
                print(f"{key}: created with {len(derived)} derived rows")


if __name__ == "__main__":
    main()
