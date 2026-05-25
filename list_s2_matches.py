import pandas as pd
from pathlib import Path

# Load matches
matches = pd.read_parquet(Path('data/normalized/matches_normalized.parquet'))

# Filter S2 JAB matches
team = "Janakpur Bolts"
s2_jab = matches[
    (matches['season'] == 'S2') &
    ((matches['team_1_name'] == team) | (matches['team_2_name'] == team))
].copy()

# Sort by date if available
if 'date' in s2_jab.columns:
    s2_jab = s2_jab.sort_values('date')

print("\n" + "="*80)
print("S2 JANAKPUR BOLTS MATCHES - Captain Assignment Required")
print("="*80)
print("\nPlease provide the captain for each match below:")
print("(Expected: Anil Sah, Aasif Sheikh, or Wayne Parnell)\n")

for i, (_, row) in enumerate(s2_jab.iterrows(), 1):
    print(f"{i}. Match ID: {row['match_id']}")
    print(f"   Teams: {row['team_1_name']} vs {row['team_2_name']}")
    print(f"   Winner: {row['winner_name']}")
    if 'date' in row and pd.notna(row['date']):
        print(f"   Date: {row['date']}")
    print(f"   Captain: ________________\n")

print("\n" + "="*80)
print("Once you provide captains, update S2_CAPTAIN_ASSIGNMENTS in:")
print("src/analytics/captaincy_analysis.py")
print("="*80)
