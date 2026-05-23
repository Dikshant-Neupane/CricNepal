"""
Player Attribution Analysis: Janakpur Bolts S1 vs S2
=====================================================

Objective: Identify which individual players contributed to performance collapse/success.

Key Questions:
1. Which death bowlers failed in S2?
2. Which middle overs bowlers lost control?
3. How many players were retained S1 -> S2?
4. Which batters failed in chases?

Output: Player-level CSV exports for recruitment/retention decisions.
"""

import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple

# Import logging
from src.utils.logging_config import get_logger

# Initialize logger for this module
logger = get_logger(__name__)

# ============================================================
# CONFIGURATION
# ============================================================
TEAM = "Janakpur Bolts"

try:
    from src.config.paths import NORMALIZED_DIR, EXPORT_DIR
    DATA_DIR = NORMALIZED_DIR
except ImportError:
    DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "normalized"
    EXPORT_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "exports"

MATCHES_FILE = DATA_DIR / "matches_normalized.parquet"
DELIVERIES_FILE = DATA_DIR / "ball_by_ball_normalized.parquet"

# Phase definitions
DEATH_OVERS = (16, 20)
MIDDLE_OVERS = (7, 16)
POWERPLAY_OVERS = (1, 7)


# ============================================================
# DATA LOADING
# ============================================================
def load_janakpur_data() -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Load matches and deliveries for Janakpur Bolts."""
    logger.info(f"\n[1/6] Loading normalized data...")
    
    matches = pd.read_parquet(MATCHES_FILE)
    deliveries = pd.read_parquet(DELIVERIES_FILE)
    
    # Filter Janakpur matches
    janakpur_matches = matches[
        (matches['team_1_name'] == TEAM) | (matches['team_2_name'] == TEAM)
    ].copy()
    
    # Filter Janakpur deliveries
    janakpur_deliveries = deliveries[
        deliveries['match_id'].isin(janakpur_matches['match_id'])
    ].copy()
    
    # Merge season info
    janakpur_deliveries = janakpur_deliveries.merge(
        janakpur_matches[['match_id', 'season', 'winner_name']],
        on='match_id',
        how='left'
    )
    
    logger.info(f"  Loaded: {len(janakpur_matches)} matches, {len(janakpur_deliveries)} deliveries")
    logger.info(f"  S1 matches: {len(janakpur_matches[janakpur_matches['season'] == 'S1'])}")
    logger.info(f"  S2 matches: {len(janakpur_matches[janakpur_matches['season'] == 'S2'])}")
    
    return janakpur_matches, janakpur_deliveries


# ============================================================
# DEATH OVERS BOWLING ANALYSIS
# ============================================================
def analyze_death_bowlers(matches_df: pd.DataFrame, deliveries_df: pd.DataFrame) -> pd.DataFrame:
    """
    Analyze individual bowler performance in death overs (16-20).
    
    Metrics per bowler per season:
    - Economy rate
    - Dot ball percentage
    - Boundary percentage
    - Wickets taken
    - Overs bowled
    """
    logger.info("\n[2/6] Analyzing death overs bowlers...")
    
    # Filter death overs bowling by Janakpur
    death_bowling = deliveries_df[
        (deliveries_df['bowling_team'] == TEAM) &
        (deliveries_df['over'] >= DEATH_OVERS[0]) &
        (deliveries_df['over'] < DEATH_OVERS[1])
    ].copy()
    
    logger.info(f"  Found {len(death_bowling)} death overs deliveries bowled")
    
    # Group by bowler and season
    bowler_stats = []
    
    for (season, bowler), group in death_bowling.groupby(['season', 'bowler_name']):
        total_balls = len(group)
        total_runs = group['runs_off_bat'].sum() + group['runs_extras'].sum()
        total_overs = total_balls / 6.0
        
        economy = (total_runs / total_overs) if total_overs > 0 else 0
        dot_balls = group['is_dot_ball'].sum()
        dot_pct = (dot_balls / total_balls * 100) if total_balls > 0 else 0
        
        boundaries = group['is_boundary'].sum()
        boundary_pct = (boundaries / total_balls * 100) if total_balls > 0 else 0
        
        wickets = group['is_wicket'].sum()
        
        bowler_stats.append({
            'season': season,
            'bowler_name': bowler,
            'overs_bowled': round(total_overs, 1),
            'balls_bowled': total_balls,
            'runs_conceded': total_runs,
            'economy_rate': round(economy, 2),
            'dot_ball_pct': round(dot_pct, 1),
            'boundary_pct': round(boundary_pct, 1),
            'wickets': wickets,
            'avg_balls_per_wicket': round(total_balls / wickets, 1) if wickets > 0 else None
        })
    
    df = pd.DataFrame(bowler_stats)
    
    # Sort by economy within each season
    df = df.sort_values(['season', 'economy_rate'])
    
    logger.info(f"  Analyzed {len(df)} bowler-season combinations")
    logger.info(f"  S1 death bowlers: {len(df[df['season'] == 'S1'])}")
    logger.info(f"  S2 death bowlers: {len(df[df['season'] == 'S2'])}")
    
    return df


# ============================================================
# MIDDLE OVERS BOWLING ANALYSIS
# ============================================================
def analyze_middle_bowlers(matches_df: pd.DataFrame, deliveries_df: pd.DataFrame) -> pd.DataFrame:
    """
    Analyze individual bowler performance in middle overs (7-15).
    
    Metrics per bowler per season:
    - Economy rate
    - Dot ball percentage
    - Wickets taken
    - Overs bowled
    """
    logger.info("\n[3/6] Analyzing middle overs bowlers...")
    
    # Filter middle overs bowling by Janakpur
    middle_bowling = deliveries_df[
        (deliveries_df['bowling_team'] == TEAM) &
        (deliveries_df['over'] >= MIDDLE_OVERS[0]) &
        (deliveries_df['over'] < MIDDLE_OVERS[1])
    ].copy()
    
    logger.info(f"  Found {len(middle_bowling)} middle overs deliveries bowled")
    
    # Group by bowler and season
    bowler_stats = []
    
    for (season, bowler), group in middle_bowling.groupby(['season', 'bowler_name']):
        total_balls = len(group)
        total_runs = group['runs_off_bat'].sum() + group['runs_extras'].sum()
        total_overs = total_balls / 6.0
        
        economy = (total_runs / total_overs) if total_overs > 0 else 0
        dot_balls = group['is_dot_ball'].sum()
        dot_pct = (dot_balls / total_balls * 100) if total_balls > 0 else 0
        
        wickets = group['is_wicket'].sum()
        
        bowler_stats.append({
            'season': season,
            'bowler_name': bowler,
            'overs_bowled': round(total_overs, 1),
            'balls_bowled': total_balls,
            'runs_conceded': total_runs,
            'economy_rate': round(economy, 2),
            'dot_ball_pct': round(dot_pct, 1),
            'wickets': wickets,
            'avg_balls_per_wicket': round(total_balls / wickets, 1) if wickets > 0 else None
        })
    
    df = pd.DataFrame(bowler_stats)
    df = df.sort_values(['season', 'economy_rate'])
    
    logger.info(f"  Analyzed {len(df)} bowler-season combinations")
    
    return df


# ============================================================
# SQUAD RETENTION ANALYSIS
# ============================================================
def analyze_squad_retention(deliveries_df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    """
    Analyze player retention from S1 to S2.
    
    Categories:
    - S1 only (departed players)
    - Both seasons (retained players)
    - S2 only (new recruits)
    """
    logger.info("\n[4/6] Analyzing squad retention...")
    
    # Get unique players per season
    s1_players = set(deliveries_df[deliveries_df['season'] == 'S1']['batter_name'].unique())
    s1_players.update(deliveries_df[deliveries_df['season'] == 'S1']['bowler_name'].unique())
    
    s2_players = set(deliveries_df[deliveries_df['season'] == 'S2']['batter_name'].unique())
    s2_players.update(deliveries_df[deliveries_df['season'] == 'S2']['bowler_name'].unique())
    
    # Categorize players
    retained = s1_players.intersection(s2_players)
    departed = s1_players - s2_players
    recruited = s2_players - s1_players
    
    logger.info(f"  S1 squad size: {len(s1_players)}")
    logger.info(f"  S2 squad size: {len(s2_players)}")
    logger.info(f"  Retained: {len(retained)} ({len(retained)/len(s1_players)*100:.1f}%)")
    logger.info(f"  Departed: {len(departed)} ({len(departed)/len(s1_players)*100:.1f}%)")
    logger.info(f"  Recruited: {len(recruited)}")
    
    # Create summary dataframes
    retained_df = pd.DataFrame({'player_name': sorted(retained), 'status': 'Retained'})
    departed_df = pd.DataFrame({'player_name': sorted(departed), 'status': 'Departed'})
    recruited_df = pd.DataFrame({'player_name': sorted(recruited), 'status': 'New Recruit'})
    
    # Calculate impact of departed players (S1 performance)
    departed_impact = []
    for player in departed:
        # Batting stats
        bat_balls = len(deliveries_df[
            (deliveries_df['season'] == 'S1') &
            (deliveries_df['batter_name'] == player) &
            (deliveries_df['batting_team'] == TEAM)
        ])
        bat_runs = deliveries_df[
            (deliveries_df['season'] == 'S1') &
            (deliveries_df['batter_name'] == player) &
            (deliveries_df['batting_team'] == TEAM)
        ]['runs_off_bat'].sum()
        
        # Bowling stats
        bowl_balls = len(deliveries_df[
            (deliveries_df['season'] == 'S1') &
            (deliveries_df['bowler_name'] == player) &
            (deliveries_df['bowling_team'] == TEAM)
        ])
        bowl_runs = (
            deliveries_df[
                (deliveries_df['season'] == 'S1') &
                (deliveries_df['bowler_name'] == player) &
                (deliveries_df['bowling_team'] == TEAM)
            ]['runs_off_bat'].sum() +
            deliveries_df[
                (deliveries_df['season'] == 'S1') &
                (deliveries_df['bowler_name'] == player) &
                (deliveries_df['bowling_team'] == TEAM)
            ]['runs_extras'].sum()
        )
        bowl_wickets = deliveries_df[
            (deliveries_df['season'] == 'S1') &
            (deliveries_df['bowler_name'] == player) &
            (deliveries_df['bowling_team'] == TEAM)
        ]['is_wicket'].sum()
        
        departed_impact.append({
            'player_name': player,
            'status': 'Departed',
            's1_batting_balls': bat_balls,
            's1_batting_runs': bat_runs,
            's1_batting_avg': round(bat_runs / bat_balls * 100, 1) if bat_balls > 0 else 0,
            's1_bowling_balls': bowl_balls,
            's1_bowling_runs': bowl_runs,
            's1_bowling_economy': round(bowl_runs / (bowl_balls/6), 2) if bowl_balls > 0 else 0,
            's1_bowling_wickets': bowl_wickets
        })
    
    departed_impact_df = pd.DataFrame(departed_impact)
    departed_impact_df = departed_impact_df.sort_values('s1_batting_runs', ascending=False)
    
    return {
        'retention_summary': pd.concat([retained_df, departed_df, recruited_df], ignore_index=True),
        'departed_impact': departed_impact_df,
        'stats': {
            'total_s1': len(s1_players),
            'total_s2': len(s2_players),
            'retained': len(retained),
            'departed': len(departed),
            'recruited': len(recruited),
            'retention_rate': round(len(retained) / len(s1_players) * 100, 1)
        }
    }


# ============================================================
# CHASE BATTING ANALYSIS
# ============================================================
def analyze_chase_batters(matches_df: pd.DataFrame, deliveries_df: pd.DataFrame) -> pd.DataFrame:
    """
    Analyze individual batter performance in chase scenarios.
    
    Metrics per batter per season:
    - Runs scored while chasing
    - Strike rate while chasing
    - Balls faced
    - Matches chased
    """
    logger.info("\n[5/6] Analyzing chase batting performance...")
    
    # Determine which matches Janakpur was chasing
    chasing_matches = []
    for match_id in matches_df['match_id'].unique():
        match = matches_df[matches_df['match_id'] == match_id].iloc[0]
        match_deliveries = deliveries_df[deliveries_df['match_id'] == match_id]
        
        # Check if Janakpur batted in innings 2 (chasing)
        inn2_batting = match_deliveries[
            (match_deliveries['innings'] == 2) &
            (match_deliveries['batting_team'] == TEAM)
        ]
        
        if len(inn2_batting) > 0:
            chasing_matches.append({
                'match_id': match_id,
                'season': match['season'],
                'won': match['winner_name'] == TEAM
            })
    
    chase_df = pd.DataFrame(chasing_matches)
    logger.info(f"  Found {len(chase_df)} chase matches")
    logger.info(f"  S1 chases: {len(chase_df[chase_df['season'] == 'S1'])}, wins: {chase_df[(chase_df['season'] == 'S1') & chase_df['won']]['won'].sum()}")
    logger.info(f"  S2 chases: {len(chase_df[chase_df['season'] == 'S2'])}, wins: {chase_df[(chase_df['season'] == 'S2') & chase_df['won']]['won'].sum()}")
    
    # Analyze batter performance in chases
    chase_match_ids = chase_df['match_id'].unique()
    chase_deliveries = deliveries_df[
        (deliveries_df['match_id'].isin(chase_match_ids)) &
        (deliveries_df['innings'] == 2) &
        (deliveries_df['batting_team'] == TEAM)
    ].copy()
    
    batter_stats = []
    
    for (season, batter), group in chase_deliveries.groupby(['season', 'batter_name']):
        total_balls = len(group)
        total_runs = group['runs_off_bat'].sum()
        
        strike_rate = (total_runs / total_balls * 100) if total_balls > 0 else 0
        
        # Count matches
        matches_played = group['match_id'].nunique()
        
        # Count wins
        match_ids = group['match_id'].unique()
        wins = sum(1 for mid in match_ids if chase_df[
            (chase_df['match_id'] == mid) & chase_df['won']
        ]['won'].any())
        
        # Dismissals
        dismissals = group['is_wicket'].sum()
        
        batter_stats.append({
            'season': season,
            'batter_name': batter,
            'matches_chased': matches_played,
            'wins': wins,
            'balls_faced': total_balls,
            'runs_scored': total_runs,
            'strike_rate': round(strike_rate, 1),
            'dismissals': dismissals,
            'batting_avg': round(total_runs / dismissals, 1) if dismissals > 0 else None
        })
    
    df = pd.DataFrame(batter_stats)
    df = df.sort_values(['season', 'runs_scored'], ascending=[True, False])
    
    logger.info(f"  Analyzed {len(df)} batter-season combinations in chases")
    
    return df


# ============================================================
# CALCULATE DELTAS
# ============================================================
def calculate_player_deltas(s1_df: pd.DataFrame, s2_df: pd.DataFrame, 
                            player_col: str, metric_cols: List[str]) -> pd.DataFrame:
    """Calculate S2 - S1 deltas for players who appeared in both seasons."""
    
    # Find common players
    s1_players = set(s1_df[player_col].unique())
    s2_players = set(s2_df[player_col].unique())
    common_players = s1_players.intersection(s2_players)
    
    if not common_players:
        return pd.DataFrame()
    
    deltas = []
    for player in common_players:
        s1_row = s1_df[s1_df[player_col] == player].iloc[0]
        s2_row = s2_df[s2_df[player_col] == player].iloc[0]
        
        delta_row = {player_col: player}
        for col in metric_cols:
            s1_val = s1_row[col]
            s2_val = s2_row[col]
            if pd.notna(s1_val) and pd.notna(s2_val):
                delta_row[f'{col}_s1'] = s1_val
                delta_row[f'{col}_s2'] = s2_val
                delta_row[f'{col}_delta'] = round(s2_val - s1_val, 2)
        
        deltas.append(delta_row)
    
    return pd.DataFrame(deltas)


# ============================================================
# EXPORT RESULTS
# ============================================================
def export_results(death_bowlers: pd.DataFrame, middle_bowlers: pd.DataFrame,
                  retention: Dict, chase_batters: pd.DataFrame):
    """Export all analysis results to CSV."""
    logger.info("\n" + "="*70)
    logger.info("EXPORTING PLAYER ANALYSIS RESULTS")
    logger.info("="*70)
    
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Death bowlers
    death_file = EXPORT_DIR / "player_death_bowlers_s1_vs_s2.csv"
    death_bowlers.to_csv(death_file, index=False)
    logger.info(f"  [OK] Exported: {death_file}")
    
    # Death bowler deltas
    death_s1 = death_bowlers[death_bowlers['season'] == 'S1']
    death_s2 = death_bowlers[death_bowlers['season'] == 'S2']
    death_deltas = calculate_player_deltas(
        death_s1, death_s2, 'bowler_name',
        ['economy_rate', 'dot_ball_pct', 'wickets']
    )
    if not death_deltas.empty:
        death_delta_file = EXPORT_DIR / "player_death_bowlers_deltas.csv"
        death_deltas.to_csv(death_delta_file, index=False)
        logger.info(f"  [OK] Exported: {death_delta_file}")
    
    # Middle bowlers
    middle_file = EXPORT_DIR / "player_middle_bowlers_s1_vs_s2.csv"
    middle_bowlers.to_csv(middle_file, index=False)
    logger.info(f"  [OK] Exported: {middle_file}")
    
    # Middle bowler deltas
    middle_s1 = middle_bowlers[middle_bowlers['season'] == 'S1']
    middle_s2 = middle_bowlers[middle_bowlers['season'] == 'S2']
    middle_deltas = calculate_player_deltas(
        middle_s1, middle_s2, 'bowler_name',
        ['economy_rate', 'dot_ball_pct', 'wickets']
    )
    if not middle_deltas.empty:
        middle_delta_file = EXPORT_DIR / "player_middle_bowlers_deltas.csv"
        middle_deltas.to_csv(middle_delta_file, index=False)
        logger.info(f"  [OK] Exported: {middle_delta_file}")
    
    # Squad retention
    retention_file = EXPORT_DIR / "player_squad_retention.csv"
    retention['retention_summary'].to_csv(retention_file, index=False)
    logger.info(f"  [OK] Exported: {retention_file}")
    
    # Departed impact
    departed_file = EXPORT_DIR / "player_departed_impact.csv"
    retention['departed_impact'].to_csv(departed_file, index=False)
    logger.info(f"  [OK] Exported: {departed_file}")
    
    # Chase batters
    chase_file = EXPORT_DIR / "player_chase_batters_s1_vs_s2.csv"
    chase_batters.to_csv(chase_file, index=False)
    logger.info(f"  [OK] Exported: {chase_file}")
    
    # Chase batter deltas
    chase_s1 = chase_batters[chase_batters['season'] == 'S1']
    chase_s2 = chase_batters[chase_batters['season'] == 'S2']
    chase_deltas = calculate_player_deltas(
        chase_s1, chase_s2, 'batter_name',
        ['runs_scored', 'strike_rate', 'batting_avg']
    )
    if not chase_deltas.empty:
        chase_delta_file = EXPORT_DIR / "player_chase_batters_deltas.csv"
        chase_deltas.to_csv(chase_delta_file, index=False)
        logger.info(f"  [OK] Exported: {chase_delta_file}")


# ============================================================
# SUMMARY REPORT
# ============================================================
def print_summary(death_bowlers: pd.DataFrame, middle_bowlers: pd.DataFrame,
                 retention: Dict, chase_batters: pd.DataFrame):
    """Print key findings summary."""
    logger.info("\n" + "="*70)
    logger.info("KEY FINDINGS SUMMARY - PLAYER ATTRIBUTION")
    logger.info("="*70)
    
    # Death bowlers
    logger.info("\n[DEATH BOWLERS] TOP 3 BY SEASON:")
    death_s1 = death_bowlers[death_bowlers['season'] == 'S1'].head(3)
    death_s2 = death_bowlers[death_bowlers['season'] == 'S2'].head(3)
    
    logger.info("\n  S1 (Best Economy):")
    for _, row in death_s1.iterrows():
        logger.info(f"    {row['bowler_name']}: {row['economy_rate']} economy, {row['dot_ball_pct']}% dots, {row['wickets']} wkts")
    
    logger.info("\n  S2 (Best Economy):")
    for _, row in death_s2.iterrows():
        logger.info(f"    {row['bowler_name']}: {row['economy_rate']} economy, {row['dot_ball_pct']}% dots, {row['wickets']} wkts")
    
    # Squad retention
    logger.info(f"\n[SQUAD RETENTION]:")
    stats = retention['stats']
    logger.info(f"  Retention rate: {stats['retention_rate']}%")
    logger.info(f"  Retained: {stats['retained']}/{stats['total_s1']} players")
    logger.info(f"  Departed: {stats['departed']} players")
    logger.info(f"  New recruits: {stats['recruited']} players")
    
    # Top departed players
    if not retention['departed_impact'].empty:
        logger.info("\n  TOP 3 DEPARTED PLAYERS (by S1 batting):")
        for _, row in retention['departed_impact'].head(3).iterrows():
            logger.info(f"    {row['player_name']}: {row['s1_batting_runs']} runs, {row['s1_bowling_wickets']} wkts")
    
    # Chase batters
    logger.info("\n[CHASE BATTING] TOP 3 RUN SCORERS BY SEASON:")
    chase_s1 = chase_batters[chase_batters['season'] == 'S1'].head(3)
    chase_s2 = chase_batters[chase_batters['season'] == 'S2'].head(3)
    
    logger.info("\n  S1:")
    for _, row in chase_s1.iterrows():
        logger.info(f"    {row['batter_name']}: {row['runs_scored']} runs @ {row['strike_rate']} SR")
    
    logger.info("\n  S2:")
    for _, row in chase_s2.iterrows():
        logger.info(f"    {row['batter_name']}: {row['runs_scored']} runs @ {row['strike_rate']} SR")
    
    logger.info("\n" + "="*70)
    logger.info("PLAYER ATTRIBUTION ANALYSIS COMPLETE")
    logger.info("="*70)
    logger.info(f"\nExport location: {EXPORT_DIR}")
    logger.info("\nNext step: Generate player attribution report")


# ============================================================
# MAIN EXECUTION
# ============================================================
def main():
    """Execute full player attribution analysis."""
    logger.info("="*70)
    logger.info("PLAYER ATTRIBUTION ANALYSIS: JANAKPUR BOLTS S1 VS S2")
    logger.info("="*70)
    logger.info(f"\nObjective: Identify individual player contributions to performance change")
    logger.info(f"Team: {TEAM}")
    logger.info(f"Data source: {DATA_DIR}")
    
    # Load data
    matches, deliveries = load_janakpur_data()
    
    # Analyze death bowlers
    death_bowlers = analyze_death_bowlers(matches, deliveries)
    
    # Analyze middle bowlers
    middle_bowlers = analyze_middle_bowlers(matches, deliveries)
    
    # Analyze squad retention
    retention = analyze_squad_retention(deliveries)
    
    # Analyze chase batters
    chase_batters = analyze_chase_batters(matches, deliveries)
    
    # Export results
    export_results(death_bowlers, middle_bowlers, retention, chase_batters)
    
    # Print summary
    print_summary(death_bowlers, middle_bowlers, retention, chase_batters)


if __name__ == "__main__":
    main()
