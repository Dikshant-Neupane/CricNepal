import pandas as pd

# Load matches data
matches = pd.read_parquet('D:/Cric_Data/data/final/parquet/matches.parquet')

# Get Season 2 matches
s2_matches = matches[matches['season'] == 'S2'].sort_values('match_date')

print('Season 2 Final Matches:')
print(s2_matches[['match_date', 'team_1_name', 'team_2_name', 'winner_name', 'match_type']].tail(5).to_string(index=False))

print('\n\nFinal Match Details:')
final = s2_matches.iloc[-1]
print(f'Date: {final["match_date"]}')
print(f'Teams: {final["team_1_name"]} vs {final["team_2_name"]}')
print(f'Winner: {final["winner_name"]}')
print(f'Margin: {final["win_margin"]} {final["win_by"]}')
print(f'Venue: {final["venue_name"]}')
print(f'Match Type: {final["match_type"]}')

# Check if this was Lumbini Lions vs Sudurpaschim Royals
if 'Lumbini Lions' in [final['team_1_name'], final['team_2_name']] and \
   'Sudurpaschim Royals' in [final['team_1_name'], final['team_2_name']]:
    print('\n✅ CONFIRMED: Lumbini Lions won NPL Season 2!')
    print(f'   Defeated Sudurpaschim Royals by {final["win_margin"]} {final["win_by"]}')
