import pandas as pd
import numpy as np


def load_elo(path='data/team_elo.csv'):
    return pd.read_csv(path).set_index('team')['elo'].to_dict()


def phase_filter(df, phase='pp'):
    if phase == 'pp':
        return df[df['phase'].str.lower() == 'powerplay']
    elif phase == 'death':
        return df[df['phase'].str.lower() == 'death']
    else:
        raise ValueError('unknown phase')


def per_bowler_phase_stats(balls_df, phase):
    p = phase_filter(balls_df, phase)
    # require bowler_name, opponent
    grouped = p.groupby(['bowler_name', 'bowling_team']).agg(
        balls=('ball', 'count'),
        runs=('runs_total', 'sum'),
        dots=('is_dot_ball', 'sum'),
        wickets=('is_wicket', 'sum')
    ).reset_index()
    grouped['econ'] = grouped['runs'] / (grouped['balls'] / 6)
    grouped['dot_pct'] = grouped['dots'] / grouped['balls'] * 100
    grouped = grouped.rename(columns={'bowler_name': 'bowler'})
    return grouped


def adjust_econ_by_opponent(grouped, elo_map):
    mean_elo = np.mean(list(elo_map.values()))
    def adj(row):
        opp = row['bowling_team']
        opp_elo = elo_map.get(opp, mean_elo)
        return row['econ'] * (mean_elo / opp_elo)
    grouped['econ_sos'] = grouped.apply(adj, axis=1)
    return grouped


def recompute(input_balls='data/normalized/ball_by_ball_normalized.parquet', elo_csv='data/team_elo.csv'):
    print('Loading balls...')
    df = pd.read_parquet(input_balls)
    elo = load_elo(elo_csv)
    print('Computing phase stats...')
    pp = per_bowler_phase_stats(df, 'pp')
    death = per_bowler_phase_stats(df, 'death')
    pp = adjust_econ_by_opponent(pp, elo)
    death = adjust_econ_by_opponent(death, elo)

    # aggregate per bowler
    def agg_phase(ph_df, phase_name):
        return ph_df.groupby('bowler').apply(lambda g: pd.Series({
            f'{phase_name}_balls': g['balls'].sum(),
            f'{phase_name}_econ': (g['runs'].sum() / (g['balls'].sum()/6)) if g['balls'].sum()>0 else np.nan,
            f'{phase_name}_econ_sos': (g['econ_sos'] * g['balls']).sum() / g['balls'].sum() if g['balls'].sum()>0 else np.nan,
            f'{phase_name}_dot_pct': (g['dots'].sum()/g['balls'].sum()*100) if g['balls'].sum()>0 else np.nan,
        })).reset_index()

    pp_agg = agg_phase(pp, 'pp')
    death_agg = agg_phase(death, 'death')
    merged = pd.merge(pp_agg, death_agg, on='bowler', how='outer').fillna(0)

    # composite: average of sos-adjusted econ (lower better)
    merged['pp_econ_eff'] = merged['pp_econ_sos']
    merged['death_econ_eff'] = merged['death_econ_sos']
    # if missing, set high econ
    merged['pp_econ_eff'] = merged['pp_econ_eff'].fillna(999)
    merged['death_econ_eff'] = merged['death_econ_eff'].fillna(999)
    merged['composite_sos'] = 0.5 * merged['pp_econ_eff'] + 0.5 * merged['death_econ_eff']

    out_csv = 'deliverables/s3_bowler_shortlist_sos.csv'
    merged.to_csv(out_csv, index=False)
    print('Wrote SOS-adjusted shortlist to', out_csv)


if __name__ == '__main__':
    recompute()
