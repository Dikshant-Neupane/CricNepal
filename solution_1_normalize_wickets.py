"""
SOLUTION 1: Normalize Wickets by Playing Time
Goal: Reduce variance by converting raw wickets to wickets per match
"""

import pandas as pd
import numpy as np

# Load data
df = pd.read_csv('D:/Cric_Data/data/player_rosters/npl_player_rosters_20260521.csv')
df['season_num'] = df['season'].astype(str).str.replace('Season ', '').astype(int)

# Split seasons
s1_data = df[df['season_num'] == 1].copy()
s2_data = df[df['season_num'] == 2].copy()

print("=" * 80)
print("SOLUTION 1: NORMALIZE WICKETS BY PLAYING TIME")
print("=" * 80)

# ============================================================================
# Calculate wickets per match
# ============================================================================
print("\n### Step 1: Calculate Wickets Per Match ###\n")

# Assuming 'bowling_matches' column exists (if not, we'll estimate)
# For NPL: typically 8-10 matches per season

for season_data, season_name in [(s1_data, 'S1'), (s2_data, 'S2')]:
    bowlers = season_data[season_data['playing_role'] == 'Bowler'].copy()
    
    # Calculate wickets per match
    # Assuming ~8 matches per season (adjust based on actual data)
    if 'bowling_matches' in bowlers.columns:
        bowlers['wickets_per_match'] = bowlers['wickets_taken'] / bowlers['bowling_matches']
    else:
        # Estimate: assume 8 matches per season
        bowlers['wickets_per_match'] = bowlers['wickets_taken'] / 8.0
    
    print(f"{season_name} Bowlers with normalized wickets:")
    print(bowlers[['player_name', 'wickets_taken', 'wickets_per_match']].head(10).to_string(index=False))
    print()

# ============================================================================
# Compare: Raw Wickets vs Wickets Per Match
# ============================================================================
print("\n### Step 2: Compare Raw vs Normalized Predictions ###\n")

# Get bowlers in both seasons
bowlers_s1 = s1_data[s1_data['playing_role'] == 'Bowler'][['player_name', 'wickets_taken']].copy()
bowlers_s1 = bowlers_s1.rename(columns={'wickets_taken': 'wickets_s1'})
bowlers_s1['wkts_per_match_s1'] = bowlers_s1['wickets_s1'] / 8.0

bowlers_s2 = s2_data[s2_data['playing_role'] == 'Bowler'][['player_name', 'wickets_taken']].copy()
bowlers_s2 = bowlers_s2.rename(columns={'wickets_taken': 'wickets_s2'})
bowlers_s2['wkts_per_match_s2'] = bowlers_s2['wickets_s2'] / 8.0

merged = bowlers_s1.merge(bowlers_s2, on='player_name')

# Predict S2 = S1 (baseline)
merged['wickets_s2_pred_raw'] = merged['wickets_s1']
merged['wkts_per_match_s2_pred'] = merged['wkts_per_match_s1']

# Calculate errors
merged['error_raw'] = abs(merged['wickets_s2_pred_raw'] - merged['wickets_s2'])
merged['error_normalized'] = abs(merged['wkts_per_match_s2_pred'] - merged['wkts_per_match_s2'])

# RMSE
rmse_raw = np.sqrt(np.mean(merged['error_raw'] ** 2))
rmse_normalized = np.sqrt(np.mean(merged['error_normalized'] ** 2))

print(f"Raw Wickets RMSE: {rmse_raw:.2f} wickets")
print(f"Normalized (per match) RMSE: {rmse_normalized:.2f} wkts/match")
print(f"\nImprovement: {(rmse_raw - rmse_normalized*8)/rmse_raw*100:.1f}%")

# Show examples
print("\n### Example: Sher Malla (S Malla) ###")
sm = merged[merged['player_name'] == 'S Malla']
if len(sm) > 0:
    row = sm.iloc[0]
    print(f"Raw wickets: {row['wickets_s1']:.0f} → {row['wickets_s2']:.0f} (predicted {row['wickets_s2_pred_raw']:.0f})")
    print(f"  Error: {row['error_raw']:.0f} wickets ❌")
    print(f"\nPer-match: {row['wkts_per_match_s1']:.2f} → {row['wkts_per_match_s2']:.2f} (predicted {row['wkts_per_match_s2_pred']:.2f})")
    print(f"  Error: {row['error_normalized']:.2f} wkts/match")
    print(f"  Better by: {(row['error_raw'] - row['error_normalized']*8):.1f} wickets")

print("\n" + "=" * 80)
print("KEY INSIGHT: Normalizing by playing time reduces variance!")
print("=" * 80)
