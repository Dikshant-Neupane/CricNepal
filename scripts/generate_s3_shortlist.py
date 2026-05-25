import pandas as pd
from pathlib import Path

def compute_phase_stats(df, phase_mask):
    # use runs_total when available
    runs_col = 'runs_total' if 'runs_total' in df.columns else 'runs_off_bat'
    dot_col = 'is_dot' if 'is_dot' in df.columns else 'is_dot_ball'
    wk_col = 'is_wicket' if 'is_wicket' in df.columns else 'is_wicket'

    g = df[phase_mask].groupby('bowler').agg(
        balls=('ball', 'count'),
        runs_conceded=(runs_col, 'sum'),
        dots=(dot_col, 'sum'),
        wickets=(wk_col, 'sum'),
    ).reset_index()
    g['econ'] = g['runs_conceded'] * 6 / g['balls']
    g['dot_pct'] = g['dots'] / g['balls'] * 100
    g['wickets_per_inn'] = g['wickets'] / (g['balls'] / 6)
    return g[['bowler','balls','runs_conceded','econ','dot_pct','wickets_per_inn']]

def main():
    root = Path('data/normalized')
    bb = pd.read_parquet(root / 'ball_by_ball_normalized.parquet')

    # normalize expected column names from normalized parquet
    if 'bowler' not in bb.columns and 'bowler_name' in bb.columns:
        bb = bb.rename(columns={'bowler_name':'bowler'})
    if 'runs_off_bat' not in bb.columns and 'runs_total' in bb.columns:
        # prefer runs_off_bat when available; otherwise use runs_total
        bb['runs_off_bat'] = bb.get('runs_off_bat', bb['runs_total'] - bb.get('runs_extras', 0))
    if 'is_dot' not in bb.columns and 'is_dot_ball' in bb.columns:
        bb = bb.rename(columns={'is_dot_ball':'is_dot'})
    if 'is_wicket' not in bb.columns:
        bb['is_wicket'] = bb.get('is_wicket', 0)
    # ensure over exists
    if 'over' not in bb.columns and 'ball_sequence' in bb.columns:
        bb['over'] = bb['ball_sequence'].astype(int)

    # Powerplay: overs 1-6 (assuming 'over' 1-indexed)
    pp_mask = bb['over'].between(1,6)
    death_mask = bb['over'] >= 16

    pp_stats = compute_phase_stats(bb, pp_mask).rename(columns=lambda c: f'pp_{c}' if c!='bowler' else c)
    death_stats = compute_phase_stats(bb, death_mask).rename(columns=lambda c: f'death_{c}' if c!='bowler' else c)

    stats = pp_stats.merge(death_stats, on='bowler', how='outer').fillna(0)

    # Minimal sample thresholds
    stats = stats[(stats['pp_balls'] >= 60) | (stats['death_balls'] >= 60)]

    # Composite score: lower is better
    stats['pp_weight'] = 0.5
    stats['death_weight'] = 0.5
    stats['composite_score'] = stats['pp_econ'].where(stats['pp_balls']>0, 10) * stats['pp_weight'] + stats['death_econ'].where(stats['death_balls']>0, 10) * stats['death_weight']

    # Rank candidates (lower score better)
    stats = stats.sort_values('composite_score')

    out_dir = Path('deliverables')
    out_dir.mkdir(parents=True, exist_ok=True)
    out_csv = out_dir / 's3_bowler_shortlist.csv'
    stats.to_csv(out_csv, index=False)

    print(f'Wrote shortlist to: {out_csv} (rows: {len(stats)})')
    # print top 20
    print(stats[['bowler','pp_balls','pp_econ','pp_dot_pct','death_balls','death_econ','death_dot_pct','composite_score']].head(20).to_string(index=False))

if __name__ == '__main__':
    main()
