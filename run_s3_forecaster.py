"""
Run S3 Performance Forecaster with real NPL player data.
"""

import pandas as pd
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
        # strike_rate and player_name already correct
    }
    
    for col, new_col in column_mapping.items():
        if col in s1_data.columns:
            s1_data.rename(columns={col: new_col}, inplace=True)
            s2_data.rename(columns={col: new_col}, inplace=True)
    
    # Add 'average' column (calculate from runs and balls)
    for data in [s1_data, s2_data]:
        # Batting average = runs / dismissals (assume dismissals = matches for simplicity)
        data['average'] = data['runs'] / data['batting_matches'].replace(0, 1)
        data['average'] = data['average'].fillna(0)
    
    print(f"\n✓ Standardized column names")
    print(f"  Required columns present: player_name, role, wickets, economy, runs, strike_rate, average")
    
    return s1_data, s2_data


def main():
    """Run S3 Performance Forecaster."""
    
    # Load data
    s1_data, s2_data = load_and_prepare_data()
    
    # Initialize forecaster
    forecaster = S3PerformanceForecaster(s1_data, s2_data)
    
    # Generate forecasts
    export_path = Path("data/exports")
    export_path.mkdir(parents=True, exist_ok=True)
    
    results = forecaster.generate_full_forecast(export_path=str(export_path))
    
    print("\n" + "="*80)
    print("S3 FORECAST COMPLETE!")
    print("="*80)
    print(f"\n✓ Bowler forecast: {len(results['bowlers'])} players")
    print(f"✓ Batter forecast: {len(results['batters'])} players")
    print(f"\n📁 Exports saved to: {export_path.absolute()}/")
    print(f"   - s3_bowler_forecast.csv")
    print(f"   - s3_batter_forecast.csv")
    
    # Print top recommendations
    print("\n" + "="*80)
    print("TOP 10 AUCTION TARGETS (All Roles)")
    print("="*80)
    
    # Combine and sort by priority
    all_forecasts = pd.concat([
        results['bowlers'][['player_name', 'role', 'recommendation', 'priority', 'max_bid', 'reason']],
        results['batters'][['player_name', 'role', 'recommendation', 'priority', 'max_bid', 'reason']]
    ]).sort_values('priority', ascending=False).head(10)
    
    print(all_forecasts.to_string(index=False))
    
    print("\n" + "="*80)
    print("NEXT STEPS")
    print("="*80)
    print("1. Open data/exports/s3_bowler_forecast.csv in Excel")
    print("2. Open data/exports/s3_batter_forecast.csv in Excel")
    print("3. Review 'recommendation' column for auction decisions")
    print("4. Update docs/S3_Auction_Target_List.md with new insights")
    print("5. Focus on Priority 8-10 players (highest value targets)")
    print("="*80 + "\n")


if __name__ == '__main__':
    main()
