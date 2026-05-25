"""Quick script to get dataset statistics."""
import pandas as pd
from src.config.paths import NORMALIZED_DIR

matches = pd.read_parquet(NORMALIZED_DIR / 'matches_normalized.parquet')
deliveries = pd.read_parquet(NORMALIZED_DIR / 'ball_by_ball_normalized.parquet')

print("="*60)
print("CRICNEPAL DATASET STATISTICS")
print("="*60)
print(f"\nTotal Matches: {len(matches)}")
print(f"S1 Matches: {len(matches[matches['season']=='S1'])}")
print(f"S2 Matches: {len(matches[matches['season']=='S2'])}")
print(f"\nTotal Deliveries (balls): {len(deliveries):,}")
print(f"Total Teams: {matches['team_1_name'].nunique()}")

# Player stats
batters = set(deliveries['batter_name'].dropna())
bowlers = set(deliveries['bowler_name'].dropna())
all_players = batters.union(bowlers)

print(f"\nUnique Players: {len(all_players)}")
print(f"Unique Batters: {len(batters)}")
print(f"Unique Bowlers: {len(bowlers)}")

# Janakpur Bolts specific
jab_matches = matches[(matches['team_1_name']=='Janakpur Bolts') | (matches['team_2_name']=='Janakpur Bolts')]
jab_s1 = jab_matches[jab_matches['season']=='S1']
jab_s2 = jab_matches[jab_matches['season']=='S2']

print(f"\n--- JANAKPUR BOLTS ---")
print(f"Total Matches: {len(jab_matches)}")
print(f"S1 Matches: {len(jab_s1)}")
print(f"S2 Matches: {len(jab_s2)}")
print(f"S1 Wins: {(jab_s1['winner_name']=='Janakpur Bolts').sum()}")
print(f"S2 Wins: {(jab_s2['winner_name']=='Janakpur Bolts').sum()}")

# Date range
print(f"\nDate Range: {matches['date'].min()} to {matches['date'].max()}")
print("="*60)
