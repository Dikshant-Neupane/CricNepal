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
from datetime import datetime, timezone
from pathlib import Path

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

    now = datetime.now(timezone.utc).isoformat()
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
        "ingestion_timestamp": now,
        "parser_version": f"cricsheet_json_v{meta.get('data_version', '?')}",
        "git_commit_hash": None,
        "last_modified": now,
    }
    return match_row, deliveries


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
    for name, new_df, key in [
        ("matches", matches_df, "matches.parquet"),
        ("ball_by_ball", deliveries_df, "ball_by_ball.parquet"),
    ]:
        target = PARQUET_DIR / key
        existing = pd.read_parquet(target)
        fresh = new_df[~new_df["match_id"].isin(existing["match_id"])]
        skipped = len(new_df) - len(fresh)
        if len(fresh):
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


if __name__ == "__main__":
    main()
