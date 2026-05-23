"""
Root Cause Analysis — S1 vs S2 Structural Performance Breakdown
================================================================
Investigates: "What structural performance dimensions collapsed between S1 and S2?"

ANALYSIS FRAMEWORK:
1. Batting Collapse?
   - Run rate by phase (PP/Middle/Death)
   - Wickets lost in powerplay
   - Death overs strike rate
   - Dot ball percentage

2. Bowling Regression?
   - Economy by phase
   - Boundary concession rate
   - Wicket-taking frequency
   - Death overs containment

3. Squad Turnover?
   - Retained core players
   - Overseas replacements
   - Role continuity

4. Match Context Effects?
   - Toss dependency
   - Chase failures
   - Close-match conversion

NOT asking: "Why did they lose?"
ASKING: "Which performance dimensions changed most significantly?"
"""

import pandas as pd
from pathlib import Path
import numpy as np

# Import logging
from src.utils.logging_config import get_logger

# Initialize logger for this module
logger = get_logger(__name__)
from typing import Dict, Tuple
import warnings
warnings.filterwarnings('ignore')

try:
    from src.config.paths import NORMALIZED_DIR, EXPORT_DIR
except ImportError:
    # Fallback for direct script execution
    NORMALIZED_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "normalized"
    EXPORT_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "exports"

EXPORT_DIR.mkdir(parents=True, exist_ok=True)

DATA_DIR = NORMALIZED_DIR

TEAM = "Janakpur Bolts"

# Phase definitions (standard T20)
POWERPLAY_OVERS = 6
DEATH_OVERS_START = 16

# ══════════════════════════════════════════════════════════════════════════
# Helper Functions
# ══════════════════════════════════════════════════════════════════════════

def classify_phase(over_num: int) -> str:
    """Classify delivery into match phase."""
    if over_num < POWERPLAY_OVERS:
        return 'powerplay'
    elif over_num < DEATH_OVERS_START:
        return 'middle'
    else:
        return 'death'


def load_janakpur_matches() -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Load normalized data filtered for Janakpur Bolts matches."""
    matches = pd.read_parquet(DATA_DIR / "matches_normalized.parquet")
    ball_by_ball = pd.read_parquet(DATA_DIR / "ball_by_ball_normalized.parquet")
    
    # Filter for Janakpur matches
    janakpur_matches = matches[
        (matches['team_1_name'] == TEAM) | (matches['team_2_name'] == TEAM)
    ].copy()
    
    janakpur_match_ids = set(janakpur_matches['match_id'])
    janakpur_deliveries = ball_by_ball[ball_by_ball['match_id'].isin(janakpur_match_ids)].copy()
    
    # Phase already exists in data, but normalize to lowercase
    if 'phase' in janakpur_deliveries.columns:
        janakpur_deliveries['phase'] = janakpur_deliveries['phase'].str.lower()
    else:
        janakpur_deliveries['phase'] = janakpur_deliveries['over'].apply(classify_phase)
    
    return janakpur_matches, janakpur_deliveries


# ══════════════════════════════════════════════════════════════════════════
# 1. BATTING ANALYSIS
# ══════════════════════════════════════════════════════════════════════════

def analyze_batting_by_phase(matches_df: pd.DataFrame, deliveries_df: pd.DataFrame) -> pd.DataFrame:
    """
    Analyze Janakpur's batting performance by phase and season.
    
    Metrics:
    - Run rate (runs per over)
    - Strike rate (runs per 100 balls)
    - Dot ball percentage
    - Boundary percentage
    - Wickets lost
    """
    # Determine which innings Janakpur was batting
    batting_deliveries = []
    
    for match_id in matches_df['match_id'].unique():
        match = matches_df[matches_df['match_id'] == match_id].iloc[0]
        match_deliveries = deliveries_df[deliveries_df['match_id'] == match_id]
        
        # Find Janakpur's batting innings using batting_team column
        janakpur_batting = match_deliveries[match_deliveries['batting_team'] == TEAM]
        
        if len(janakpur_batting) > 0:
            janakpur_batting = janakpur_batting.copy()
            janakpur_batting['season'] = match['season']
            batting_deliveries.append(janakpur_batting)
    
    if not batting_deliveries:
        return pd.DataFrame()
    
    batting_df = pd.concat(batting_deliveries, ignore_index=True)
    
    # Aggregate by season and phase
    metrics = []
    
    for season in ['S1', 'S2']:
        season_data = batting_df[batting_df['season'] == season]
        
        for phase in ['powerplay', 'middle', 'death']:
            phase_data = season_data[season_data['phase'] == phase]
            
            if len(phase_data) == 0:
                continue
            
            total_runs = phase_data['runs_off_bat'].sum() + phase_data['runs_extras'].sum()
            total_balls = len(phase_data)
            dots = len(phase_data[phase_data['is_dot_ball'] == True])
            boundaries = len(phase_data[phase_data['runs_off_bat'].isin([4, 6])])
            fours = len(phase_data[phase_data['runs_off_bat'] == 4])
            sixes = len(phase_data[phase_data['runs_off_bat'] == 6])
            wickets = phase_data['is_wicket'].sum()
            
            run_rate = (total_runs / total_balls) * 6 if total_balls > 0 else 0
            strike_rate = (total_runs / total_balls) * 100 if total_balls > 0 else 0
            dot_pct = (dots / total_balls) * 100 if total_balls > 0 else 0
            boundary_pct = (boundaries / total_balls) * 100 if total_balls > 0 else 0
            
            metrics.append({
                'season': season,
                'phase': phase,
                'total_runs': int(total_runs),
                'total_balls': int(total_balls),
                'run_rate': round(run_rate, 2),
                'strike_rate': round(strike_rate, 1),
                'dot_ball_pct': round(dot_pct, 1),
                'boundary_pct': round(boundary_pct, 1),
                'fours': int(fours),
                'sixes': int(sixes),
                'wickets_lost': int(wickets),
            })
    
    return pd.DataFrame(metrics)


# ══════════════════════════════════════════════════════════════════════════
# 2. BOWLING ANALYSIS
# ══════════════════════════════════════════════════════════════════════════

def analyze_bowling_by_phase(matches_df: pd.DataFrame, deliveries_df: pd.DataFrame) -> pd.DataFrame:
    """
    Analyze Janakpur's bowling performance by phase and season.
    
    Metrics:
    - Economy rate
    - Dot ball percentage
    - Boundary concession rate
    - Wickets taken
    """
    bowling_deliveries = []
    
    for match_id in matches_df['match_id'].unique():
        match = matches_df[matches_df['match_id'] == match_id].iloc[0]
        match_deliveries = deliveries_df[deliveries_df['match_id'] == match_id]
        
        # Find Janakpur's bowling innings (when they are bowling_team)
        janakpur_bowling = match_deliveries[match_deliveries['bowling_team'] == TEAM]
        
        if len(janakpur_bowling) > 0:
            janakpur_bowling = janakpur_bowling.copy()
            janakpur_bowling['season'] = match['season']
            bowling_deliveries.append(janakpur_bowling)
    
    if not bowling_deliveries:
        return pd.DataFrame()
    
    bowling_df = pd.concat(bowling_deliveries, ignore_index=True)
    
    # Aggregate by season and phase
    metrics = []
    
    for season in ['S1', 'S2']:
        season_data = bowling_df[bowling_df['season'] == season]
        
        for phase in ['powerplay', 'middle', 'death']:
            phase_data = season_data[season_data['phase'] == phase]
            
            if len(phase_data) == 0:
                continue
            
            total_runs = phase_data['runs_off_bat'].sum() + phase_data['runs_extras'].sum()
            total_balls = len(phase_data)
            dots = len(phase_data[phase_data['is_dot_ball'] == True])
            boundaries = len(phase_data[phase_data['runs_off_bat'].isin([4, 6])])
            wickets = phase_data['is_wicket'].sum()
            
            economy = (total_runs / total_balls) * 6 if total_balls > 0 else 0
            dot_pct = (dots / total_balls) * 100 if total_balls > 0 else 0
            boundary_pct = (boundaries / total_balls) * 100 if total_balls > 0 else 0
            wicket_rate = (wickets / total_balls) * 100 if total_balls > 0 else 0
            
            metrics.append({
                'season': season,
                'phase': phase,
                'runs_conceded': int(total_runs),
                'total_balls': int(total_balls),
                'economy': round(economy, 2),
                'dot_ball_pct': round(dot_pct, 1),
                'boundary_conceded_pct': round(boundary_pct, 1),
                'wickets_taken': int(wickets),
                'wicket_rate': round(wicket_rate, 2),
            })
    
    return pd.DataFrame(metrics)


# ══════════════════════════════════════════════════════════════════════════
# 3. MATCH CONTEXT ANALYSIS
# ══════════════════════════════════════════════════════════════════════════

def analyze_match_context(matches_df: pd.DataFrame, deliveries_df: pd.DataFrame) -> pd.DataFrame:
    """
    Analyze match context effects.
    
    Metrics:
    - Toss win rate and decision impact
    - Batting first vs chasing performance
    - Close match conversion (<10 run margin or <2 wickets)
    """
    metrics = []
    
    # First, determine which innings Janakpur batted in for each match
    match_innings_map = {}
    for match_id in matches_df['match_id'].unique():
        match_deliveries = deliveries_df[deliveries_df['match_id'] == match_id]
        
        # Check which innings Janakpur was batting
        inn1_batting = match_deliveries[
            (match_deliveries['innings'] == 1) & 
            (match_deliveries['batting_team'] == TEAM)
        ]
        inn2_batting = match_deliveries[
            (match_deliveries['innings'] == 2) & 
            (match_deliveries['batting_team'] == TEAM)
        ]
        
        if len(inn1_batting) > 0:
            match_innings_map[match_id] = 1  # Batted first
        elif len(inn2_batting) > 0:
            match_innings_map[match_id] = 2  # Chased
    
    for season in ['S1', 'S2']:
        season_matches = matches_df[matches_df['season'] == season].copy()
        
        # Add batting_order column
        season_matches['janakpur_batting_order'] = season_matches['match_id'].map(match_innings_map)
        
        total_matches = len(season_matches)
        wins = len(season_matches[season_matches['winner_name'] == TEAM])
        
        # Toss analysis
        toss_wins = len(season_matches[season_matches['toss_winner_name'] == TEAM])
        toss_wins_converted = len(season_matches[
            (season_matches['toss_winner_name'] == TEAM) & 
            (season_matches['winner_name'] == TEAM)
        ])
        
        # Batting first vs chasing
        batting_first = season_matches[season_matches['janakpur_batting_order'] == 1]
        chasing = season_matches[season_matches['janakpur_batting_order'] == 2]
        
        batting_first_wins = len(batting_first[batting_first['winner_name'] == TEAM])
        chasing_wins = len(chasing[chasing['winner_name'] == TEAM])
        
        # Close matches (margin <10 runs or <2 wickets)
        close_matches = season_matches[
            ((season_matches['win_by'] == 'runs') & (season_matches['win_margin'] <= 10)) |
            ((season_matches['win_by'] == 'wickets') & (season_matches['win_margin'] <= 2))
        ]
        close_wins = len(close_matches[close_matches['winner_name'] == TEAM])
        
        metrics.append({
            'season': season,
            'total_matches': int(total_matches),
            'wins': int(wins),
            'win_rate': round((wins/total_matches)*100, 1) if total_matches > 0 else 0,
            'toss_wins': int(toss_wins),
            'toss_win_rate': round((toss_wins/total_matches)*100, 1) if total_matches > 0 else 0,
            'toss_converted': int(toss_wins_converted),
            'toss_conversion_rate': round((toss_wins_converted/toss_wins)*100, 1) if toss_wins > 0 else 0,
            'batting_first_matches': int(len(batting_first)),
            'batting_first_wins': int(batting_first_wins),
            'batting_first_win_rate': round((batting_first_wins/len(batting_first))*100, 1) if len(batting_first) > 0 else 0,
            'chasing_matches': int(len(chasing)),
            'chasing_wins': int(chasing_wins),
            'chasing_win_rate': round((chasing_wins/len(chasing))*100, 1) if len(chasing) > 0 else 0,
            'close_matches': int(len(close_matches)),
            'close_wins': int(close_wins),
            'close_match_win_rate': round((close_wins/len(close_matches))*100, 1) if len(close_matches) > 0 else 0,
        })
    
    return pd.DataFrame(metrics)


# ══════════════════════════════════════════════════════════════════════════
# 4. DELTA CALCULATION
# ══════════════════════════════════════════════════════════════════════════

def calculate_deltas(df: pd.DataFrame, metrics: list, by_phase: bool = False) -> pd.DataFrame:
    """Calculate S2 - S1 deltas for specified metrics."""
    if by_phase:
        # Phase-based comparison
        deltas = []
        for phase in df['phase'].unique():
            s1_data = df[(df['season'] == 'S1') & (df['phase'] == phase)]
            s2_data = df[(df['season'] == 'S2') & (df['phase'] == phase)]
            
            if len(s1_data) == 0 or len(s2_data) == 0:
                continue
            
            delta_row = {'phase': phase}
            for metric in metrics:
                s1_val = s1_data.iloc[0][metric] if metric in s1_data.columns else 0
                s2_val = s2_data.iloc[0][metric] if metric in s2_data.columns else 0
                delta_row[f'{metric}_s1'] = s1_val
                delta_row[f'{metric}_s2'] = s2_val
                delta_row[f'{metric}_delta'] = s2_val - s1_val
            
            deltas.append(delta_row)
        
        return pd.DataFrame(deltas)
    else:
        # Season-level comparison
        s1_data = df[df['season'] == 'S1']
        s2_data = df[df['season'] == 'S2']
        
        if len(s1_data) == 0 or len(s2_data) == 0:
            return pd.DataFrame()
        
        delta_row = {}
        for metric in metrics:
            s1_val = s1_data.iloc[0][metric] if metric in s1_data.columns else 0
            s2_val = s2_data.iloc[0][metric] if metric in s2_data.columns else 0
            delta_row[f'{metric}_s1'] = s1_val
            delta_row[f'{metric}_s2'] = s2_val
            delta_row[f'{metric}_delta'] = s2_val - s1_val
        
        return pd.DataFrame([delta_row])


# ══════════════════════════════════════════════════════════════════════════
# Main Execution
# ══════════════════════════════════════════════════════════════════════════

def main():
    logger.info("="*70)
    logger.info("ROOT CAUSE ANALYSIS: JANAKPUR BOLTS S1 VS S2")
    logger.info("="*70)
    logger.info(f"\nFraming: What structural performance dimensions collapsed?")
    logger.info(f"Team: {TEAM}")
    logger.info(f"Data source: {DATA_DIR}")
    
    # Load data
    logger.info("\n[1/4] Loading normalized data...")
    matches, deliveries = load_janakpur_matches()
    logger.info(f"  Loaded: {len(matches)} Janakpur matches, {len(deliveries)} deliveries")
    logger.info(f"  S1 matches: {len(matches[matches['season'] == 'S1'])}")
    logger.info(f"  S2 matches: {len(matches[matches['season'] == 'S2'])}")
    
    # 1. Batting analysis
    logger.info("\n[2/4] Analyzing batting performance by phase...")
    batting_metrics = analyze_batting_by_phase(matches, deliveries)
    logger.info(batting_metrics.to_string(index=False))
    
    # Calculate batting deltas
    batting_delta_metrics = ['run_rate', 'strike_rate', 'dot_ball_pct', 'boundary_pct', 'wickets_lost']
    batting_deltas = calculate_deltas(batting_metrics, batting_delta_metrics, by_phase=True)
    
    # 2. Bowling analysis
    logger.info("\n[3/4] Analyzing bowling performance by phase...")
    bowling_metrics = analyze_bowling_by_phase(matches, deliveries)
    logger.info(bowling_metrics.to_string(index=False))
    
    # Calculate bowling deltas
    bowling_delta_metrics = ['economy', 'dot_ball_pct', 'boundary_conceded_pct', 'wickets_taken']
    bowling_deltas = calculate_deltas(bowling_metrics, bowling_delta_metrics, by_phase=True)
    
    # 3. Match context analysis
    logger.info("\n[4/4] Analyzing match context effects...")
    context_metrics = analyze_match_context(matches, deliveries)
    logger.info(context_metrics.to_string(index=False))
    
    # Calculate context deltas
    context_delta_metrics = ['win_rate', 'toss_conversion_rate', 'batting_first_win_rate', 
                             'chasing_win_rate', 'close_match_win_rate']
    context_deltas = calculate_deltas(context_metrics, context_delta_metrics, by_phase=False)
    
    # Export results
    logger.info("\n" + "="*70)
    logger.info("EXPORTING ANALYSIS RESULTS")
    logger.info("="*70)
    
    exports = {
        's1_vs_s2_batting_by_phase.csv': batting_metrics,
        's1_vs_s2_batting_deltas.csv': batting_deltas,
        's1_vs_s2_bowling_by_phase.csv': bowling_metrics,
        's1_vs_s2_bowling_deltas.csv': bowling_deltas,
        's1_vs_s2_match_context.csv': context_metrics,
        's1_vs_s2_context_deltas.csv': context_deltas,
    }
    
    for filename, df in exports.items():
        if len(df) > 0:
            output_path = EXPORT_DIR / filename
            df.to_csv(output_path, index=False)
            logger.info(f"  [OK] Exported: {output_path}")
    
    # Summary of key findings
    logger.info("\n" + "="*70)
    logger.info("KEY FINDINGS SUMMARY")
    logger.info("="*70)
    
    # Identify largest deltas
    if len(batting_deltas) > 0:
        logger.info("\n[BATTING] DELTAS (S2 - S1):")
        for _, row in batting_deltas.iterrows():
            phase = row['phase']
            rr_delta = row.get('run_rate_delta', 0)
            dot_delta = row.get('dot_ball_pct_delta', 0)
            logger.info(f"  {phase.upper()}: Run rate {rr_delta:+.2f}, Dot% {dot_delta:+.1f}%")
    
    if len(bowling_deltas) > 0:
        logger.info("\n[BOWLING] DELTAS (S2 - S1):")
        for _, row in bowling_deltas.iterrows():
            phase = row['phase']
            eco_delta = row.get('economy_delta', 0)
            dot_delta = row.get('dot_ball_pct_delta', 0)
            logger.info(f"  {phase.upper()}: Economy {eco_delta:+.2f}, Dot% {dot_delta:+.1f}%")
    
    if len(context_deltas) > 0:
        logger.info("\n[MATCH CONTEXT] DELTAS (S2 - S1):")
        row = context_deltas.iloc[0]
        for metric in context_delta_metrics:
            delta_col = f'{metric}_delta'
            if delta_col in row:
                logger.info(f"  {metric}: {row[delta_col]:+.1f}%")
    
    logger.info("\n" + "="*70)
    logger.info("ROOT CAUSE ANALYSIS COMPLETE")
    logger.info("="*70)
    logger.info(f"\nNext step: Create management brief from findings")
    logger.info(f"Export location: {EXPORT_DIR}")


if __name__ == "__main__":
    main()
