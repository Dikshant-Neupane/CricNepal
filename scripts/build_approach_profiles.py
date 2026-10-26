"""Build team approach profiles from the ball-by-ball dataset.

One row per team describing how that team actually plays — chase vs
bat-first strength, powerplay batting/bowling, death batting, collapse
frequency, toss habits — plus a head-to-head table for every pair.
These are the numbers behind the dashboard's "How <opponent> play"
panel on the Bolts Game Plan page (option C of the 2026-10-26 brief
integration analysis: computed profiles + written per-match briefs).

Reads data/final/parquet/{matches,ball_by_ball}.parquet and writes
data/approach/team_approach_profiles.csv and data/approach/head_to_head.csv.
Runs inside scripts/inseason_update.py after the refresh step, so the
profiles absorb each Season 3 match as Cricsheet lands. Team names are
canonicalised to the Season 3 fixture spellings (the historical files
use both "Sudur Paschim Royals" and "Sudurpaschim Royals", and both
"Kathmandu Gurkhas" and "Kathmandu Gorkhas").
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent

CANONICAL = {
    "Sudur Paschim Royals": "Sudurpaschim Royals",
    "Kathmandu Gurkhas": "Kathmandu Gorkhas",
}


def canon(name):
    if pd.isna(name):
        return name
    return CANONICAL.get(str(name), str(name))


def compute_profiles(matches: pd.DataFrame, balls: pd.DataFrame) -> pd.DataFrame:
    m = matches.copy()
    b = balls.copy()
    for col in ("team_1_name", "team_2_name", "winner_name", "toss_winner_name"):
        m[col] = m[col].map(canon)
    b["batting_team"] = b["batting_team"].map(canon)
    b["bowling_team"] = b["bowling_team"].map(canon)

    inn = (b.groupby(["match_id", "innings", "batting_team"])
             .agg(runs=("runs_total", "sum"), wkts=("is_wicket", "sum"))
             .reset_index()
             .merge(m[["match_id", "winner_name"]], on="match_id", how="left"))
    pp_bat = (b[b.over < 6].groupby(["match_id", "batting_team"])
                .agg(r=("runs_total", "sum"), w=("is_wicket", "sum")).reset_index())
    pp_bowl = (b[b.over < 6].groupby(["match_id", "bowling_team"])
                 .agg(r=("runs_total", "sum"), w=("is_wicket", "sum")).reset_index())
    death = (b[b.over >= 16].groupby(["match_id", "batting_team"])
               .agg(r=("runs_total", "sum")).reset_index())

    rows = []
    for team in sorted(set(m.team_1_name) | set(m.team_2_name)):
        played = m[(m.team_1_name == team) | (m.team_2_name == team)]
        decided = played[played.winner_name.notna() & (played.winner_name != "")]
        wins = int((decided.winner_name == team).sum())
        bat1 = inn[(inn.batting_team == team) & (inn.innings == 1)]
        chase = inn[(inn.batting_team == team) & (inn.innings == 2)]
        pb = pp_bat[pp_bat.batting_team == team]
        pw = pp_bowl[pp_bowl.bowling_team == team]
        dth = death[death.batting_team == team]
        toss = played[played.toss_winner_name == team]
        rows.append({
            "team": team,
            "matches": int(len(played)),
            "wins": wins,
            "win_pct": round(100 * wins / len(decided), 1) if len(decided) else 0.0,
            "bat_first_n": int(len(bat1)),
            "bat_first_avg": round(float(bat1.runs.mean()), 1) if len(bat1) else 0.0,
            "bat_first_win_pct": round(100 * float((bat1.winner_name == team).mean()), 1) if len(bat1) else 0.0,
            "chase_n": int(len(chase)),
            "chase_avg": round(float(chase.runs.mean()), 1) if len(chase) else 0.0,
            "chase_win_pct": round(100 * float((chase.winner_name == team).mean()), 1) if len(chase) else 0.0,
            "pp_bat_runs_per_match": round(float(pb.r.mean()), 1) if len(pb) else 0.0,
            "pp_bat_wkts_per_match": round(float(pb.w.mean()), 2) if len(pb) else 0.0,
            "pp_bat_3plus_losses": int((pb.w >= 3).sum()),
            "pp_bowl_runs_conceded_per_match": round(float(pw.r.mean()), 1) if len(pw) else 0.0,
            "pp_bowl_wkts_per_match": round(float(pw.w.mean()), 2) if len(pw) else 0.0,
            "pp_bowl_3plus_taken": int((pw.w >= 3).sum()),
            "death_bat_runs_per_match": round(float(dth.r.mean()), 1) if len(dth) else 0.0,
            "totals_under_120": int((inn[inn.batting_team == team].runs < 120).sum()),
            "times_all_out": int((inn[inn.batting_team == team].wkts == 10).sum()),
            "toss_won": int(len(toss)),
            "toss_field_pct": round(100 * float((toss.toss_decision == "field").mean()), 1) if len(toss) else 0.0,
        })
    return pd.DataFrame(rows)


def compute_head_to_head(matches: pd.DataFrame) -> pd.DataFrame:
    m = matches.copy()
    for col in ("team_1_name", "team_2_name", "winner_name"):
        m[col] = m[col].map(canon)
    teams = sorted(set(m.team_1_name) | set(m.team_2_name))
    rows = []
    for i, a in enumerate(teams):
        for bteam in teams[i + 1:]:
            pair = m[((m.team_1_name == a) & (m.team_2_name == bteam))
                     | ((m.team_1_name == bteam) & (m.team_2_name == a))]
            rows.append({
                "team_a": a,
                "team_b": bteam,
                "matches": int(len(pair)),
                "a_wins": int((pair.winner_name == a).sum()),
                "b_wins": int((pair.winner_name == bteam).sum()),
            })
    return pd.DataFrame(rows)


def main() -> None:
    matches = pd.read_parquet(ROOT / "data" / "final" / "parquet" / "matches.parquet")
    balls = pd.read_parquet(ROOT / "data" / "final" / "parquet" / "ball_by_ball.parquet")
    out = ROOT / "data" / "approach"
    out.mkdir(parents=True, exist_ok=True)
    profiles = compute_profiles(matches, balls)
    h2h = compute_head_to_head(matches)
    profiles.to_csv(out / "team_approach_profiles.csv", index=False)
    h2h.to_csv(out / "head_to_head.csv", index=False)
    print(f"approach profiles: {len(profiles)} teams -> {out / 'team_approach_profiles.csv'}")
    print(f"head-to-head: {len(h2h)} pairs -> {out / 'head_to_head.csv'}")


if __name__ == "__main__":
    main()
