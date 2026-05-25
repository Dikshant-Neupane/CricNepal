import pandas as pd

# Check the structure of real data
matches = pd.read_parquet('D:/Cric_Data/data/final/parquet/matches.parquet')
print("Matches columns:")
print(matches.columns.tolist())
print("\nSample data:")
print(matches[['season', 'team_1_name', 'team_2_name', 'winner_name', 'match_type', 
               'innings_1_team', 'innings_1_runs', 'innings_2_runs']].head())
print("\nMatch types:")
print(matches['match_type'].value_counts())

# Filter for Janakpur Bolts only
janakpur = matches[(matches['team_1_name'] == 'Janakpur Bolts') | 
                   (matches['team_2_name'] == 'Janakpur Bolts')]
print(f"\n\nJanakpur Bolts matches: {len(janakpur)}")
print(janakpur[['season', 'team_1_name', 'team_2_name', 'winner_name']].head(10))
