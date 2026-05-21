"""
Can we actually REDUCE wickets prediction error?
Currently: RMSE 7.6 wickets (45% error for a 17-wicket player)

Let's test what ACTUALLY reduces error, not just normalizes it.
"""

import pandas as pd
import numpy as np
from sklearn.linear_model import PoissonRegressor, LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error

# Load data
df = pd.read_csv('D:/Cric_Data/data/player_rosters/npl_player_rosters_20260521.csv')
df['season_num'] = df['season'].astype(str).str.replace('Season ', '').astype(int)

s1 = df[df['season_num'] == 1].copy()
s2 = df[df['season_num'] == 2].copy()

# Get bowlers in both seasons
bowlers_s1 = s1[s1['playing_role'] == 'Bowler'][['player_name', 'wickets_taken', 'economy_rate', 'overs_bowled', 'bowling_matches']].copy()
bowlers_s1.columns = ['player_name', 'wickets_s1', 'economy_s1', 'overs_s1', 'matches_s1']

bowlers_s2 = s2[s2['playing_role'] == 'Bowler'][['player_name', 'wickets_taken', 'bowling_matches']].copy()
bowlers_s2.columns = ['player_name', 'wickets_s2', 'matches_s2']

merged = bowlers_s1.merge(bowlers_s2, on='player_name').dropna()

print("="*80)
print("CAN WE REDUCE WICKETS PREDICTION ERROR?")
print("="*80)
print(f"\n{len(merged)} bowlers in both seasons\n")

# ==============================================================================
# BASELINE: Predict S2 wickets = S1 wickets (assume stable)
# ==============================================================================
merged['pred_baseline'] = merged['wickets_s1']
rmse_baseline = np.sqrt(mean_squared_error(merged['wickets_s2'], merged['pred_baseline']))
print(f"1. BASELINE (S2 = S1): RMSE {rmse_baseline:.2f} wickets")

# ==============================================================================
# METHOD 1: Adjust for matches played (proportional)
# ==============================================================================
merged['pred_proportional'] = merged['wickets_s1'] * (merged['matches_s2'] / merged['matches_s1'])
rmse_proportional = np.sqrt(mean_squared_error(merged['wickets_s2'], merged['pred_proportional']))
print(f"2. PROPORTIONAL (adjust for matches): RMSE {rmse_proportional:.2f} wickets")
improvement_1 = (rmse_baseline - rmse_proportional) / rmse_baseline * 100
print(f"   → Improvement: {improvement_1:.1f}%")

# ==============================================================================
# METHOD 2: Use economy as predictor (linear regression)
# ==============================================================================
X_train = merged[['wickets_s1', 'economy_s1', 'overs_s1']].values
y_train = merged['wickets_s2'].values

lr = LinearRegression()
lr.fit(X_train, y_train)
merged['pred_linear'] = lr.predict(X_train)
rmse_linear = np.sqrt(mean_squared_error(merged['wickets_s2'], merged['pred_linear']))
print(f"\n3. LINEAR REGRESSION (wickets + economy + overs): RMSE {rmse_linear:.2f} wickets")
improvement_2 = (rmse_baseline - rmse_linear) / rmse_baseline * 100
print(f"   → Improvement: {improvement_2:.1f}%")

# ==============================================================================
# METHOD 3: Poisson regression (correct distribution for count data)
# ==============================================================================
poisson = PoissonRegressor(max_iter=500)
poisson.fit(X_train, y_train)
merged['pred_poisson'] = poisson.predict(X_train)
rmse_poisson = np.sqrt(mean_squared_error(merged['wickets_s2'], merged['pred_poisson']))
print(f"\n4. POISSON REGRESSION: RMSE {rmse_poisson:.2f} wickets")
improvement_3 = (rmse_baseline - rmse_poisson) / rmse_baseline * 100
print(f"   → Improvement: {improvement_3:.1f}%")

# ==============================================================================
# METHOD 4: Random Forest (capture non-linear patterns)
# ==============================================================================
rf = RandomForestRegressor(n_estimators=100, max_depth=3, random_state=42)
rf.fit(X_train, y_train)
merged['pred_rf'] = rf.predict(X_train)
rmse_rf = np.sqrt(mean_squared_error(merged['wickets_s2'], merged['pred_rf']))
print(f"\n5. RANDOM FOREST: RMSE {rmse_rf:.2f} wickets")
improvement_4 = (rmse_baseline - rmse_rf) / rmse_baseline * 100
print(f"   → Improvement: {improvement_4:.1f}%")

# ==============================================================================
# ANALYSIS: What's the theoretical limit?
# ==============================================================================
print("\n" + "="*80)
print("THEORETICAL LIMITS")
print("="*80)

# Calculate variance components
total_variance = np.var(merged['wickets_s2'])
within_player_variance = merged.apply(lambda row: (row['wickets_s2'] - row['wickets_s1'])**2, axis=1).mean()
explainable_variance = total_variance - within_player_variance

print(f"\nTotal variance in S2 wickets: {total_variance:.2f}")
print(f"Within-player variance (noise): {within_player_variance:.2f}")
print(f"Explainable variance: {explainable_variance:.2f}")
print(f"\nTheoretical best RMSE: {np.sqrt(within_player_variance):.2f} wickets")
print(f"(Due to inherent randomness in wicket-taking)")

# ==============================================================================
# Show worst predictions
# ==============================================================================
print("\n" + "="*80)
print("WORST PREDICTIONS (Any Method)")
print("="*80)

merged['error_best'] = abs(merged['pred_rf'] - merged['wickets_s2'])
worst = merged.nlargest(5, 'error_best')[['player_name', 'wickets_s1', 'wickets_s2', 'pred_rf', 'error_best', 'economy_s1']]
print(worst.to_string(index=False))

# ==============================================================================
# FINAL VERDICT
# ==============================================================================
print("\n" + "="*80)
print("VERDICT: CAN WE REDUCE ERROR?")
print("="*80)

best_rmse = min(rmse_proportional, rmse_linear, rmse_poisson, rmse_rf)
best_method = ['Proportional', 'Linear', 'Poisson', 'Random Forest'][
    [rmse_proportional, rmse_linear, rmse_poisson, rmse_rf].index(best_rmse)
]

print(f"\nBaseline RMSE: {rmse_baseline:.2f} wickets")
print(f"Best method: {best_method}")
print(f"Best RMSE: {best_rmse:.2f} wickets")
print(f"Reduction: {(rmse_baseline - best_rmse):.2f} wickets ({(rmse_baseline - best_rmse)/rmse_baseline*100:.1f}%)")

if best_rmse > 6.0:
    print(f"\n⚠️  Even best method has {best_rmse:.2f} wickets error (40-50% for typical bowler)")
    print("   Wickets are INHERENTLY UNPREDICTABLE due to:")
    print("   - Small sample sizes (8-10 matches)")
    print("   - High variance (Poisson distribution)")
    print("   - Context dependency (opposition, match situation)")
    print("   - Random factors (catches dropped, edges, umpire calls)")
    print("\n   RECOMMENDATION: Use confidence intervals, not point predictions!")
    print(f"   Example: Predict 12 ± 7 wickets (68% CI), not just 12 wickets")
else:
    print(f"\n✅ Error reduced to acceptable level!")

print("\n" + "="*80)
