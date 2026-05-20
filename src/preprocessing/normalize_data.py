"""
Data Stabilization Phase — Mandatory Preprocessing
==================================================
Normalizes team names, player identities, and validates data integrity
before root cause analysis.

BLOCKING ISSUES ADDRESSED:
1. Team name variants (Gurkhas/Gorkhas)
2. Player identity consistency
3. Match duplicate detection
4. Playoff match labeling

Must run BEFORE any comparative analysis.
"""

import pandas as pd
from pathlib import Path
import numpy as np
from typing import Dict, Tuple
import warnings
warnings.filterwarnings('ignore')

# ══════════════════════════════════════════════════════════════════════════
# Configuration
# ══════════════════════════════════════════════════════════════════════════

PARQUET_DIR = Path("D:/Cric_Data/data/final/parquet")
EXPORT_DIR = Path("D:/CricNepal/data/normalized")
EXPORT_DIR.mkdir(parents=True, exist_ok=True)

# Team name normalization mapping
TEAM_NAME_MAPPING = {
    "Kathmandu Gurkhas": "Kathmandu Gorkhas",  # Official S2 spelling
    "Sudur Paschim Royals": "Sudurpaschim Royals",  # Remove space
}

# ══════════════════════════════════════════════════════════════════════════
# 1. Team Name Normalization
# ══════════════════════════════════════════════════════════════════════════

def normalize_team_names(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply team name normalization to all team columns.
    
    Critical for:
    - Preventing fragmented standings
    - Accurate opposition history
    - Valid win distributions
    """
    team_cols = [col for col in df.columns if 'team' in col.lower() and 'name' in col.lower()]
    team_cols += [col for col in df.columns if col in ['winner_name', 'toss_winner_name']]
    # Also include batting_team and bowling_team from ball_by_ball data
    team_cols += [col for col in df.columns if col in ['batting_team', 'bowling_team']]
    
    df_normalized = df.copy()
    
    for col in team_cols:
        if col in df_normalized.columns:
            df_normalized[col] = df_normalized[col].replace(TEAM_NAME_MAPPING)
    
    return df_normalized


def validate_team_normalization(df: pd.DataFrame) -> Dict[str, any]:
    """Verify team normalization was successful."""
    team_cols = ['team_1_name', 'team_2_name', 'winner_name']
    all_teams = set()
    
    for col in team_cols:
        if col in df.columns:
            all_teams.update(df[col].dropna().unique())
    
    # Check for variants
    has_gurkhas = 'Kathmandu Gurkhas' in all_teams
    has_gorkhas = 'Kathmandu Gorkhas' in all_teams
    
    validation = {
        'total_unique_teams': len(all_teams),
        'expected_teams': 8,
        'has_gurkhas_variant': has_gurkhas,
        'has_gorkhas_variant': has_gorkhas,
        'normalization_successful': not has_gurkhas,  # Should only have Gorkhas
        'all_teams': sorted(all_teams)
    }
    
    return validation


# ══════════════════════════════════════════════════════════════════════════
# 2. Player Identity Consistency
# ══════════════════════════════════════════════════════════════════════════

def detect_player_variants(df: pd.DataFrame) -> pd.DataFrame:
    """
    Detect potential player name duplicates/variants.
    
    Examples:
    - "A. Sharma" vs "Anil Sharma"
    - "K Malla" vs "Kushal Malla"
    """
    player_cols = [col for col in df.columns if 'player' in col.lower() or 
                   col in ['striker', 'non_striker', 'bowler', 'fielder', 'batter_name', 'bowler_name']]
    
    all_players = set()
    for col in player_cols:
        if col in df.columns:
            all_players.update(df[col].dropna().unique())
    
    # Simple duplicate detection: look for similar names
    players_df = pd.DataFrame({'player_name': sorted(all_players)})
    
    # Extract last names for similarity check
    players_df['last_name'] = players_df['player_name'].str.split().str[-1]
    players_df['first_initial'] = players_df['player_name'].str[0]
    
    # Find potential duplicates
    duplicates = players_df.groupby(['last_name', 'first_initial']).filter(lambda x: len(x) > 1)
    
    return duplicates.sort_values('last_name')


# ══════════════════════════════════════════════════════════════════════════
# 3. Match Validation
# ══════════════════════════════════════════════════════════════════════════

def validate_matches(matches_df: pd.DataFrame) -> Dict[str, any]:
    """
    Validate match data integrity.
    
    Checks:
    - No duplicate match_ids
    - All matches have basic metadata
    - Playoff matches properly labeled
    """
    validation = {
        'total_matches': len(matches_df),
        'duplicate_match_ids': matches_df['match_id'].duplicated().sum(),
        'missing_winner': matches_df['winner_name'].isna().sum(),
        'missing_teams': matches_df[['team_1_name', 'team_2_name']].isna().sum().sum(),
        's1_matches': len(matches_df[matches_df['season'] == 'S1']),
        's2_matches': len(matches_df[matches_df['season'] == 'S2']),
    }
    
    # Infer playoff matches (more than 7 league matches per team)
    team_match_counts = {}
    for _, match in matches_df.iterrows():
        season = match['season']
        for team in [match['team_1_name'], match['team_2_name']]:
            key = (season, team)
            team_match_counts[key] = team_match_counts.get(key, 0) + 1
    
    # Teams with >7 matches likely made playoffs
    playoff_teams = {team: count for team, count in team_match_counts.items() if count > 7}
    
    validation['playoff_teams_inferred'] = playoff_teams
    
    return validation


# ══════════════════════════════════════════════════════════════════════════
# 4. Deliveries Data Validation
# ══════════════════════════════════════════════════════════════════════════

def validate_deliveries(deliveries_df: pd.DataFrame, matches_df: pd.DataFrame) -> Dict[str, any]:
    """
    Validate ball-by-ball data completeness.
    
    Expected: ~200-250 deliveries per T20 match
    """
    deliveries_per_match = deliveries_df.groupby('match_id').size()
    
    validation = {
        'total_deliveries': len(deliveries_df),
        'matches_with_deliveries': len(deliveries_per_match),
        'total_matches': len(matches_df),
        'avg_deliveries_per_match': deliveries_per_match.mean(),
        'min_deliveries': deliveries_per_match.min(),
        'max_deliveries': deliveries_per_match.max(),
        'matches_with_low_deliveries': len(deliveries_per_match[deliveries_per_match < 100]),
    }
    
    # Check for matches in matches.parquet but not in deliveries
    match_ids_matches = set(matches_df['match_id'])
    match_ids_deliveries = set(deliveries_df['match_id'].unique())
    
    validation['matches_missing_deliveries'] = len(match_ids_matches - match_ids_deliveries)
    validation['orphan_deliveries'] = len(match_ids_deliveries - match_ids_matches)
    
    return validation


# ══════════════════════════════════════════════════════════════════════════
# Main Execution
# ══════════════════════════════════════════════════════════════════════════

def main():
    print("="*70)
    print("DATA STABILIZATION PHASE")
    print("="*70)
    
    # Load raw data
    print("\n[1/5] Loading raw data...")
    matches = pd.read_parquet(PARQUET_DIR / "matches.parquet")
    ball_by_ball = pd.read_parquet(PARQUET_DIR / "ball_by_ball.parquet")
    
    print(f"  Loaded: {len(matches)} matches, {len(ball_by_ball)} deliveries")
    
    # Validate BEFORE normalization
    print("\n[2/5] Validating raw data...")
    pre_validation = validate_team_normalization(matches)
    print(f"  Teams found (raw): {pre_validation['total_unique_teams']}")
    print(f"  Expected: {pre_validation['expected_teams']}")
    
    if pre_validation['has_gurkhas_variant'] and pre_validation['has_gorkhas_variant']:
        print("  ⚠️  WARNING: Both Gurkhas/Gorkhas variants detected")
        print("      Normalization REQUIRED")
    
    # Normalize team names
    print("\n[3/5] Normalizing team names...")
    matches_normalized = normalize_team_names(matches)
    ball_by_ball_normalized = normalize_team_names(ball_by_ball)
    
    # Validate AFTER normalization
    post_validation = validate_team_normalization(matches_normalized)
    print(f"  Teams after normalization: {post_validation['total_unique_teams']}")
    
    if post_validation['normalization_successful']:
        print("  ✓ Normalization successful")
    else:
        print("  ✗ Normalization FAILED - Gurkhas variant still present")
    
    print("\n  Final team list:")
    for team in post_validation['all_teams']:
        print(f"    - {team}")
    
    # Match validation
    print("\n[4/5] Validating match data...")
    match_validation = validate_matches(matches_normalized)
    print(f"  Total matches: {match_validation['total_matches']}")
    print(f"  S1 matches: {match_validation['s1_matches']}")
    print(f"  S2 matches: {match_validation['s2_matches']}")
    print(f"  Duplicate match IDs: {match_validation['duplicate_match_ids']}")
    print(f"  Missing winner: {match_validation['missing_winner']}")
    
    if match_validation['playoff_teams_inferred']:
        print(f"\n  Playoff teams inferred (>7 matches):")
        for (season, team), count in sorted(match_validation['playoff_teams_inferred'].items()):
            print(f"    {season} - {team}: {count} matches")
    
    # Deliveries validation
    print("\n[5/5] Validating deliveries data...")
    deliveries_validation = validate_deliveries(ball_by_ball_normalized, matches_normalized)
    print(f"  Total deliveries: {deliveries_validation['total_deliveries']}")
    print(f"  Avg per match: {deliveries_validation['avg_deliveries_per_match']:.1f}")
    print(f"  Range: {deliveries_validation['min_deliveries']}-{deliveries_validation['max_deliveries']}")
    print(f"  Matches with <100 deliveries: {deliveries_validation['matches_with_low_deliveries']}")
    print(f"  Matches missing deliveries: {deliveries_validation['matches_missing_deliveries']}")
    
    # Player identity check
    print("\n[BONUS] Checking player name variants...")
    player_variants = detect_player_variants(ball_by_ball_normalized)
    
    if len(player_variants) > 0:
        print(f"  ⚠️  Found {len(player_variants)} potential player name variants:")
        print(player_variants[['player_name', 'last_name']].head(10).to_string(index=False))
        if len(player_variants) > 10:
            print(f"      ... and {len(player_variants) - 10} more")
    else:
        print("  ✓ No obvious player name variants detected")
    
    # Export normalized data
    print("\n" + "="*70)
    print("EXPORTING NORMALIZED DATA")
    print("="*70)
    
    export_files = {
        'matches_normalized.parquet': matches_normalized,
        'ball_by_ball_normalized.parquet': ball_by_ball_normalized,
    }
    
    for filename, df in export_files.items():
        output_path = EXPORT_DIR / filename
        df.to_parquet(output_path, index=False)
        print(f"  ✓ Exported: {output_path}")
    
    # Export validation report
    validation_report = {
        'pre_normalization': pre_validation,
        'post_normalization': post_validation,
        'match_validation': match_validation,
        'deliveries_validation': deliveries_validation,
    }
    
    # Save as JSON
    import json
    
    def convert_to_json_serializable(obj):
        """Convert numpy types to Python native types."""
        if isinstance(obj, dict):
            return {k: convert_to_json_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple, set)):
            return [convert_to_json_serializable(item) for item in obj]
        elif hasattr(obj, 'item'):  # numpy types
            return obj.item()
        elif isinstance(obj, tuple) and len(obj) == 2:
            # Handle (season, team) tuples from playoff_teams_inferred
            return f"{obj[0]}_{obj[1]}"
        else:
            return obj
    
    report_path = EXPORT_DIR / "validation_report.json"
    with open(report_path, 'w') as f:
        # Convert all teams to be JSON-safe
        report = convert_to_json_serializable(validation_report)
        # Special handling for playoff_teams_inferred which has tuple keys
        if 'match_validation' in report and 'playoff_teams_inferred' in report['match_validation']:
            playoff_dict = {}
            for key, val in validation_report['match_validation']['playoff_teams_inferred'].items():
                playoff_dict[f"{key[0]}_{key[1]}"] = int(val)
            report['match_validation']['playoff_teams_inferred'] = playoff_dict
        json.dump(report, f, indent=2)
    
    print(f"  ✓ Validation report: {report_path}")
    
    print("\n" + "="*70)
    print("DATA STABILIZATION COMPLETE")
    print("="*70)
    print("\nNext step: Proceed to root cause analysis (Phase 2)")
    print(f"Normalized data location: {EXPORT_DIR}")
    
    # Summary decision
    print("\n" + "="*70)
    print("READINESS ASSESSMENT")
    print("="*70)
    
    blockers = []
    
    if not post_validation['normalization_successful']:
        blockers.append("Team name normalization failed")
    
    if match_validation['duplicate_match_ids'] > 0:
        blockers.append("Duplicate match IDs detected")
    
    if deliveries_validation['matches_missing_deliveries'] > 0:
        blockers.append(f"{deliveries_validation['matches_missing_deliveries']} matches missing deliveries")
    
    if blockers:
        print("⚠️  BLOCKING ISSUES FOUND:")
        for blocker in blockers:
            print(f"  - {blocker}")
        print("\nRESOLVE THESE BEFORE ANALYSIS")
    else:
        print("✓ ALL CHECKS PASSED")
        print("✓ DATA IS STABLE")
        print("✓ READY FOR ROOT CAUSE ANALYSIS")


if __name__ == "__main__":
    main()
