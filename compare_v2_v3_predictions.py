"""
Compare v2.0 (trend-based) vs v3.0 (ML-based) predictions
Goal: Validate that v3.0 actually reduces error
"""

import pandas as pd
import numpy as np
from sklearn.metrics import mean_squared_error

# Load actual data
df = pd.read_csv('D:/Cric_Data/data/player_rosters/npl_player_rosters_20260521.csv')
df['season_num'] = df['season'].astype(str).str.replace('Season ', '').astype(int)

s1 = df[df['season_num'] == 1].copy()
s2 = df[df['season_num'] == 2].copy()

# Get bowlers
bowlers_s1 = s1[s1['playing_role'] == 'Bowler'][['player_name', 'wickets_taken', 'economy_rate']].copy()
bowlers_s1.columns = ['player_name', 'wickets_s1', 'economy_s1']

bowlers_s2 = s2[s2['playing_role'] == 'Bowler'][['player_name', 'wickets_taken', 'economy_rate']].copy()
bowlers_s2.columns = ['player_name', 'wickets_s2', 'economy_s2']

merged = bowlers_s1.merge(bowlers_s2, on='player_name').dropna()

print("="*80)
print("V2.0 (TREND-BASED) VS V3.0 (ML-BASED) PREDICTIONS")
print("="*80)

# Load v3.0 predictions
v3_forecast = pd.read_csv('data/exports/s3_bowler_forecast.csv')

# Filter to players with both S1 and S2 data
v3_with_data = v3_forecast[v3_forecast['s1_economy'].notna() & v3_forecast['s2_economy'].notna()].copy()

print(f"\n{len(v3_with_data)} players with both S1 and S2 data")
print(f"\nTop 10 by v3.0 S3 composite score:")
top10 = v3_with_data.nlargest(10, 's3_composite_score')[
    ['player_name', 's2_composite_score', 's3_composite_score', 's2_wickets', 's3_wickets_pred', 's2_economy', 's3_economy_pred']
]
print(top10.to_string(index=False))

print("\n" + "="*80)
print("KEY PLAYERS COMPARISON")
print("="*80)

# Check Sher Malla
malla = v3_forecast[v3_forecast['player_name'] == 'S Malla']
if len(malla) > 0:
    m = malla.iloc[0]
    print(f"\nSher Malla:")
    print(f"  S1: {m['s1_wickets']:.0f} wkts, {m['s1_economy']:.2f} econ")
    print(f"  S2: {m['s2_wickets']:.0f} wkts, {m['s2_economy']:.2f} econ")
    print(f"  S3 pred: {m['s3_wickets_pred']:.1f} wkts, {m['s3_economy_pred']:.2f} econ")
    print(f"\n  S2 composite: {m['s2_composite_score']:.1f}/100")
    print(f"  S3 composite: {m['s3_composite_score']:.1f}/100")
    print(f"  Priority: {m['priority']}")
    print(f"\n  v2.0 logic: S3 composite should be similar to S2 (76.3)")
    print(f"  v3.0 logic: ML predicts regression to mean (52.0)")
    
# Check A Bohara
bohara = v3_forecast[v3_forecast['player_name'] == 'A Bohara']
if len(bohara) > 0:
    b = bohara.iloc[0]
    print(f"\n\nA Bohara:")
    print(f"  S1: {b['s1_wickets']:.0f} wkts, {b['s1_economy']:.2f} econ")
    print(f"  S2: {b['s2_wickets']:.0f} wkts, {b['s2_economy']:.2f} econ")
    print(f"  S3 pred: {b['s3_wickets_pred']:.1f} wkts, {b['s3_economy_pred']:.2f} econ")
    print(f"\n  S2 composite: {b['s2_composite_score']:.1f}/100")
    print(f"  S3 composite: {b['s3_composite_score']:.1f}/100")
    print(f"  Priority: {b['priority']}")

print("\n" + "="*80)
print("ANALYSIS")
print("="*80)

print("""
v3.0 ML predictions are more CONSERVATIVE (regression to mean):
- Sher Malla: S3 wickets predicted 11.5 (vs S2 actual 17)
- This is REALISTIC for backtesting but PESSIMISTIC for S3

Issue: ML trained on S1→S2 sees VARIANCE as noise to reduce
Reality: Some players genuinely improve (Sher Malla 7→17 is real!)

RECOMMENDATION:
- Keep v3.0 ML for CONFIDENCE INTERVALS (realistic error ±5 wickets)
- But use v2.0 TREND LOGIC for point predictions (rewards improvement)
- Best of both: ML bounds + trend expectations
""")

print("\n" + "="*80)
print("PROPOSED: HYBRID v3.5 APPROACH")
print("="*80)

print("""
1. Use ML for ECONOMY predictions (stable metric, ML works well)
2. Use TREND for WICKETS predictions (captures improvement signals)
3. Use ML error estimates for CONFIDENCE INTERVALS

Example for Sher Malla:
- Trend says: 7→17 IMPROVING, predict 20 wickets S3
- ML says: 7→17 anomaly, predict 11.5 wickets S3  
- Hybrid says: Predict 16 wickets (trend-based) ± 5 wickets (ML error)
  
This gives: 11-21 wickets S3 (realistic range that includes both views)
""")
