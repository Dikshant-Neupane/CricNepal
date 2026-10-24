import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.prediction import elo as canonical_elo  # noqa: E402


def compute_elo(matches_path, out_csv):
    """Write team_elo.csv + rolling_team_elo.csv from the CANONICAL Elo
    engine (src/prediction/elo.py: K=20, 40% between-season regression,
    MOV capped at 1.5x).

    Previously this script carried its own K=40/no-regression engine and
    its rolling output had match_id/season null in every row (it subset
    the dataframe to team/winner/date columns before reading them).
    Rolling rows now come straight from the canonical per-match history,
    so match_id and season are populated.
    """
    df = pd.read_parquet(matches_path)
    hist = canonical_elo.compute_history(df)
    finals = canonical_elo.final_ratings(hist)
    out = pd.DataFrame([{"team": t, "elo": v} for t, v in finals.items()])
    out.to_csv(out_csv, index=False)
    print("Wrote team Elo to", out_csv)

    rolling = pd.DataFrame({
        "match_id": hist["match_id"], "match_date": hist["match_date"],
        "season": hist["season"], "team_a": hist["team_1"],
        "team_b": hist["team_2"], "pre_elo_a": hist["team_1_pre"],
        "pre_elo_b": hist["team_2_pre"],
    })
    rolling_path = out_csv.replace("team_elo.csv", "rolling_team_elo.csv")
    rolling.to_csv(rolling_path, index=False)
    print("Wrote rolling pre-match Elo to", rolling_path)


def compute_bowler_sos(bbb_df, rolling_elo_path: str, league_avg_elo: float = 1500.0) -> pd.DataFrame:
    """
    Priority 7 fix: compute pre-match SOS for each bowler-match.
    Uses OPPONENT'S PRE-MATCH Elo (from rolling_team_elo.csv), not within-match
    batting quality — removing within-match look-ahead leakage.

    Returns DataFrame with columns:
      player_name, match_id, season, bowling_team, opp_pre_elo, sos_factor
    where sos_factor = league_avg_elo / opp_pre_elo
    (factor > 1 = tougher opponent, economy should be normalised down)
    """
    rolling = pd.read_csv(rolling_elo_path)
    # For each match, map each team to the opponent's pre-match Elo
    # team_a's opponent = team_b (pre_elo_b), team_b's opponent = team_a (pre_elo_a)
    team_a_opp = rolling[["match_id", "season", "team_a", "pre_elo_b"]].rename(
        columns={"team_a": "bowling_team", "pre_elo_b": "opp_pre_elo"}
    )
    team_b_opp = rolling[["match_id", "season", "team_b", "pre_elo_a"]].rename(
        columns={"team_b": "bowling_team", "pre_elo_a": "opp_pre_elo"}
    )
    opp_elo = pd.concat([team_a_opp, team_b_opp], ignore_index=True)
    opp_elo["sos_factor"] = league_avg_elo / opp_elo["opp_pre_elo"].clip(lower=100)

    # Join to ball-by-ball to get bowler-level SOS
    bbb = bbb_df[["match_id", "bowler_name", "bowling_team"]].drop_duplicates(
        subset=["match_id", "bowler_name"]
    )
    bbb = bbb.rename(columns={"bowler_name": "player_name"})
    result = bbb.merge(opp_elo[["match_id", "bowling_team", "opp_pre_elo", "sos_factor"]],
                       on=["match_id", "bowling_team"], how="left")
    return result


if __name__ == '__main__':
    matches_path = 'data/normalized/matches_normalized.parquet'
    out_csv = 'data/team_elo.csv'
    compute_elo(matches_path, out_csv)
