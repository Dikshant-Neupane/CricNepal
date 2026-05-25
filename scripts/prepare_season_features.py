import pandas as pd
import argparse

def prepare(ball_parquet='data/normalized/ball_by_ball_normalized.parquet', matches_parquet='data/normalized/matches_normalized.parquet', out_csv='data/per_bowler_season_features.csv'):
    balls = pd.read_parquet(ball_parquet)
    matches = pd.read_parquet(matches_parquet)
    # keep match_id -> season mapping
    match_season = matches[['match_id', 'season']]
    balls = balls.merge(match_season, on='match_id', how='left')

    def agg_phase(df, phase_name):
        p = df[df['phase'].str.lower() == phase_name]
        g = p.groupby(['bowler_name', 'season']).agg(
            balls=('ball', 'count'),
            runs=('runs_total', 'sum'),
            dots=('is_dot_ball', 'sum'),
            wickets=('is_wicket', 'sum')
        ).reset_index()
        g[f'{phase_name}_econ'] = g['runs'] / (g['balls'] / 6)
        g[f'{phase_name}_dot_pct'] = g['dots'] / g['balls'] * 100
        return g[['bowler_name','season',f'{phase_name}_econ',f'{phase_name}_dot_pct', 'balls']].rename(columns={'balls':f'{phase_name}_balls'})

    pp = agg_phase(balls, 'powerplay')
    death = agg_phase(balls, 'death')

    merged = pp.merge(death, on=['bowler_name','season'], how='outer').fillna(0)
    merged = merged.rename(columns={'bowler_name':'bowler'})
    merged.to_csv(out_csv, index=False)
    print('Wrote season features to', out_csv)


if __name__ == '__main__':
    prepare()
