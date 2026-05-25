"""
Run S3 Performance Forecaster with real NPL player data.
v2.0: Composite scoring + wickets normalization
"""

import pandas as pd
import numpy as np
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from analytics.s3_performance_forecaster import S3PerformanceForecaster


def load_and_prepare_data():
    """Load NPL player roster data and split into S1 and S2."""
    
    print("="*80)
    print("LOADING NPL PLAYER ROSTER DATA")
    print("="*80)
    
    # Load data
    data_path = Path("D:/Cric_Data/data/player_rosters/npl_player_rosters_20260521.csv")
    df = pd.read_csv(data_path)
    
    print(f"✓ Loaded {len(df)} player-season records")
    print(f"✓ Columns: {', '.join(df.columns)}")
    print(f"\nSeason values: {df['season'].unique()}")
    print("\n" + "="*80)
    
    # Convert season to numeric - handle both "Season 1" and 1
    df['season_num'] = df['season'].astype(str).str.replace('Season ', '').astype(int)
    
    # Split by season
    s1_data = df[df['season_num'] == 1].copy()
    s2_data = df[df['season_num'] == 2].copy()
    
    print(f"\n✓ Season 1: {len(s1_data)} player records")
    print(f"✓ Season 2: {len(s2_data)} player records")
    
    # Standardize column names for forecaster
    # Expected: player_name, role, wickets, economy, runs, average, strike_rate
    
    # Rename columns to match forecaster expectations
    column_mapping = {
        'playing_role': 'role',
        'runs_scored': 'runs',
        'wickets_taken': 'wickets',
        'economy_rate': 'economy'
        # strike_rate, player_name, bowling_matches, balls_bowled already correct
    }
    
    for col, new_col in column_mapping.items():
        if col in s1_data.columns:
            s1_data.rename(columns={col: new_col}, inplace=True)
            s2_data.rename(columns={col: new_col}, inplace=True)
    
    # Add 'average' column (calculate from runs and dismissals)
    for data in [s1_data, s2_data]:
        # Batting average = runs / dismissals (assume dismissals = matches for simplicity)
        data['average'] = data['runs'] / data['batting_matches'].replace(0, 1)
        data['average'] = data['average'].fillna(0)
        
        # Ensure bowling_matches exists (use default if missing)
        if 'bowling_matches' not in data.columns:
            print("⚠️  Warning: bowling_matches column not found, estimating from data...")
            # Estimate: if player has wickets or economy, assume they bowled in matches
            data['bowling_matches'] = data.apply(
                lambda row: 8 if (not pd.isna(row.get('wickets', np.nan)) and row.get('wickets', 0) > 0) else 0,
                axis=1
            )
        
        # Ensure balls_bowled exists (estimate if missing)
        if 'balls_bowled' not in data.columns and 'overs_bowled' in data.columns:
            print("⚠️  Warning: balls_bowled column not found, calculating from overs_bowled...")
            data['balls_bowled'] = data['overs_bowled'] * 6
        elif 'balls_bowled' not in data.columns:
            # Last resort: estimate from economy and runs
            print("⚠️  Warning: balls_bowled not found, estimating from economy...")
            data['balls_bowled'] = data.apply(
                lambda row: (row.get('runs_conceded', 0) / row.get('economy', 8.0)) * 6 
                if not pd.isna(row.get('economy', np.nan)) else np.nan,
                axis=1
            )
    
    print(f"\n✓ Standardized column names")
    print(f"  Required columns present: player_name, role, wickets, economy, runs, strike_rate, average")
    print(f"  Added/verified: bowling_matches, balls_bowled (for composite scoring)")
    
    return s1_data, s2_data


def main():
    """Run S3 Performance Forecaster v2.0."""
    
    # Load data
    s1_data, s2_data = load_and_prepare_data()
    
    # Initialize forecaster
    forecaster = S3PerformanceForecaster(s1_data, s2_data)
    
    # Generate forecasts
    export_path = Path("data/exports")
    export_path.mkdir(parents=True, exist_ok=True)
    
    results = forecaster.generate_full_forecast(export_path=str(export_path))
    
    print("\n" + "="*80)
    print("S3 FORECAST COMPLETE (v2.0 with Composite Scoring)")
    print("="*80)
    print(f"\n✓ Bowler forecast: {len(results['bowlers'])} players")
    print(f"✓ Batter forecast: {len(results['batters'])} players")
    print(f"\n📁 Exports saved to: {export_path.absolute()}/")
    print(f"   - s3_bowler_forecast.csv")
    print(f"   - s3_batter_forecast.csv")
    
    # Export NPL grade-specific CSVs
    bowlers = results['bowlers']
    
    # Grade A targets
    grade_a = bowlers[bowlers['npl_grade'].str.contains('Grade A', na=False)].sort_values('priority', ascending=False)
    if len(grade_a) > 0:
        grade_a_file = export_path / 'NPL_Grade_A_Targets.csv'
        grade_a.to_csv(grade_a_file, index=False)
        print(f"   - NPL_Grade_A_Targets.csv ({len(grade_a)} players)")
    
    # Grade B targets
    grade_b = bowlers[bowlers['npl_grade'].str.contains('Grade B', na=False)].sort_values('priority', ascending=False)
    if len(grade_b) > 0:
        grade_b_file = export_path / 'NPL_Grade_B_Targets.csv'
        grade_b.to_csv(grade_b_file, index=False)
        print(f"   - NPL_Grade_B_Targets.csv ({len(grade_b)} players)")
    
    # Grade C targets
    grade_c = bowlers[bowlers['npl_grade'].str.contains('Grade C', na=False)].sort_values('priority', ascending=False)
    if len(grade_c) > 0:
        grade_c_file = export_path / 'NPL_Grade_C_Targets.csv'
        grade_c.to_csv(grade_c_file, index=False)
        print(f"   - NPL_Grade_C_Targets.csv ({len(grade_c)} players)")
    
    # Print top recommendations
    print("\n" + "="*80)
    print("TOP 10 BOWLER TARGETS (v2.0 Composite Scoring)")
    print("="*80)
    print("\nKey Metrics:")
    print("- Composite Score: 60% wickets/match + 30% economy + 10% SR")
    print("- Priority 9-10: Grade A (₨13-15L)")
    print("- Priority 7-8: Grade B (₨6-10L)")
    print("- Priority 3-5: Grade C (₨2-7L)")
    print("\n" + "-"*80)
    
    top_bowlers = bowlers[['player_name', 's2_composite_score', 's3_composite_score', 
                           'priority', 'npl_grade', 'bid_range', 'recommendation']].head(10)
    print(top_bowlers.to_string(index=False))
    
    print("\n" + "="*80)
    print("KEY IMPROVEMENTS IN v2.0")
    print("="*80)
    print("✅ Wickets normalized by playing time (wickets per match)")
    print("✅ Composite scoring: 60% wickets + 30% economy + 10% SR")
    print("✅ Mapped to NPL auction grades (A/B/C)")
    print("✅ Corrected priority for elite wicket-takers")
    print("\nExpected fixes:")
    print("- Sher Malla: Priority 5 → 9 (Grade A, ₨13-15L)")
    print("- A Bohara: Priority 5 → 8 (Grade A/B, ₨8-10L)")
    print("- Shahab Alam: Priority 5 → 7 (Grade B, ₨6-8L)")
    
    # Check if Sher Malla is in the data
    sher_malla = bowlers[bowlers['player_name'] == 'S Malla']
    if len(sher_malla) > 0:
        print("\n" + "="*80)
        print("VALIDATION: Sher Malla (Joint #1 Wicket-Taker S2)")
        print("="*80)
        sm = sher_malla.iloc[0]
        print(f"S2 Performance:")
        print(f"  Wickets: {sm['s2_wickets']:.0f} wickets")
        print(f"  Wickets/match: {sm['s2_wkts_per_match']:.2f} wkts/match")
        print(f"  Economy: {sm['s2_economy']:.2f}")
        print(f"  Composite Score: {sm['s2_composite_score']:.1f}/100")
        print(f"\nv2.0 Recommendation:")
        print(f"  Priority: {sm['priority']} {sm['recommendation']}")
        print(f"  NPL Grade: {sm['npl_grade']}")
        print(f"  Bid Range: {sm['bid_range']}")
        print(f"  Reason: {sm['reason']}")
        
        if sm['priority'] >= 8:
            print(f"\n✅ CORRECT! Elite wicket-taker properly valued")
        else:
            print(f"\n⚠️  Warning: May still be undervalued (expected Priority 8-9)")
    
    print("\n" + "="*80)
    print("NEXT STEPS")
    print("="*80)
    print("1. Open data/exports/NPL_Grade_A_Targets.csv")
    print("2. Review composite scores and priorities")
    print("3. Prepare Grade A budget: ₨36L for 3 players")
    print("4. Bid aggressively on Priority 9-10 players")
    print("5. Update docs/S3_Auction_Target_List.md")
    print("="*80 + "\n")


if __name__ == '__main__':
    main()
