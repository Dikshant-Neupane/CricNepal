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

    out = pd.DataFrame([{'team': t, 'elo': v} for t, v in elo.items()])
    out.to_csv(out_csv, index=False)
    print('Wrote team Elo to', out_csv)


if __name__ == '__main__':
    import sys
    matches_path = 'data/normalized/matches_normalized.parquet'
    out_csv = 'data/team_elo.csv'
    compute_elo(matches_path, out_csv)
