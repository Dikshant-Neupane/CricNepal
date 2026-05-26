import pandas as pd
import numpy as np
from pathlib import Path


def compute_elo(matches_path, out_csv):
    df = pd.read_parquet(matches_path)
    # attempt to find team and result columns using known names from normalized parquet
    team_a_col = None
    team_b_col = None
    winner_col = None
    date_col = None
    if 'team_1_name' in df.columns and 'team_2_name' in df.columns:
        team_a_col = 'team_1_name'
        team_b_col = 'team_2_name'
    if 'winner_name' in df.columns:
        winner_col = 'winner_name'
    if 'match_date' in df.columns:
        date_col = 'match_date'

    if not team_a_col or not team_b_col or not winner_col:
        raise RuntimeError('Could not find required columns for teams/winner in matches dataframe. Columns: ' + ','.join(df.columns))

    df = df[[team_a_col, team_b_col, winner_col] + ([date_col] if date_col else [])].copy()
    df = df.dropna(subset=[team_a_col, team_b_col])
    if date_col:
        df[date_col] = pd.to_datetime(df[date_col])
        df = df.sort_values(date_col)

    teams = pd.unique(df[[team_a_col, team_b_col]].values.ravel('K'))
    elo = {t: 1500.0 for t in teams}
    k = 40
    records = []
    for _, r in df.iterrows():
        a = r[team_a_col]
        b = r[team_b_col]
        winner = r[winner_col]
        ea = elo.get(a, 1500.0)
        eb = elo.get(b, 1500.0)
        # expected
        exp_a = 1 / (1 + 10 ** ((eb - ea) / 400.0))
        exp_b = 1 - exp_a
        # actual
        if pd.isna(winner):
            sa = 0.5
        else:
            sa = 1.0 if winner == a else (0.0 if winner == b else 0.5)
        sb = 1.0 - sa
        # updates
        new_ea = ea + k * (sa - exp_a)
        new_eb = eb + k * (sb - exp_b)
        # record pre-match elos
        records.append({'team_a': a, 'team_b': b, 'pre_elo_a': ea, 'pre_elo_b': eb})
        elo[a] = new_ea
        elo[b] = new_eb

    # ── Save final season Elo (unchanged original output) ──
    out = pd.DataFrame([{'team': t, 'elo': v} for t, v in elo.items()])
    out.to_csv(out_csv, index=False)
    print('Wrote team Elo to', out_csv)

    # ── Priority 6 fix: save per-match PRE-match rolling Elo ──
    # This eliminates look-ahead bias when using Elo as a feature or SOS proxy.
    # Columns: match_id, match_date, season, team_a, team_b, pre_elo_a, pre_elo_b,
    #          opp_elo_for_a (= pre_elo_b), opp_elo_for_b (= pre_elo_a)
    rolling_records = []
    elo_rolling = {t: 1500.0 for t in teams}
    for _, r in df.iterrows():
        a      = r[team_a_col]
        b      = r[team_b_col]
        winner = r[winner_col]
        ea     = elo_rolling.get(a, 1500.0)
        eb     = elo_rolling.get(b, 1500.0)
        mid    = r.get('match_id', None)
        mdate  = r[date_col] if date_col else None
        season = r.get('season', None)

        rolling_records.append({
            'match_id':    mid,
            'match_date':  mdate,
            'season':      season,
            'team_a':      a,
            'team_b':      b,
            'pre_elo_a':   ea,
            'pre_elo_b':   eb,
        })

        exp_a   = 1 / (1 + 10 ** ((eb - ea) / 400.0))
        exp_b   = 1 - exp_a
        sa      = 1.0 if (not pd.isna(winner) and winner == a) else \
                  (0.0 if (not pd.isna(winner) and winner == b) else 0.5)
        sb      = 1.0 - sa
        elo_rolling[a] = ea + k * (sa - exp_a)
        elo_rolling[b] = eb + k * (sb - exp_b)

    rolling_df = pd.DataFrame(rolling_records)
    rolling_path = out_csv.replace('team_elo.csv', 'rolling_team_elo.csv')
    rolling_df.to_csv(rolling_path, index=False)
    print('Wrote rolling pre-match Elo to', rolling_path)


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
    import sys
    matches_path = 'data/normalized/matches_normalized.parquet'
    out_csv = 'data/team_elo.csv'
    compute_elo(matches_path, out_csv)
