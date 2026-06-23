"""Data source helpers for dashboard metrics and validation."""

from __future__ import annotations

import pandas as pd
import os
from typing import Tuple, Optional

from src.utils.logging_config import get_logger

# Initialize logger
logger = get_logger(__name__)

from src.config.paths import PARQUET_DIR

# Path to real parquet data
PARQUET_DATA_PATH = str(PARQUET_DIR)


def _empty_result(columns: list[str]) -> pd.DataFrame:
    """Return empty DataFrame with specified columns."""
    return pd.DataFrame(columns=columns)


def _load_from_parquet(team_name: str = "Janakpur Bolts") -> pd.DataFrame:
    """
    Load match records from parquet files for a specific team.
    
    Args:
        team_name: Team name to filter for (default: Janakpur Bolts)
        
    Returns:
        DataFrame with match records in dashboard format
        
    Raises:
        FileNotFoundError: If parquet file doesn't exist
        ValueError: If required columns are missing
    """
    matches_path = os.path.join(PARQUET_DATA_PATH, "matches.parquet")
    
    if not os.path.exists(matches_path):
        logger.warning(f"Parquet file not found at {matches_path}")
        raise FileNotFoundError(f"Matches parquet not found: {matches_path}")
    
    logger.info(f"Loading matches from {matches_path}")
    
    try:
        # Load matches
        matches = pd.read_parquet(matches_path)
        logger.info(f"Loaded {len(matches)} matches from parquet")
        
        # Filter for the specified team
        team_matches = matches[
            (matches['team_1_name'] == team_name) | 
            (matches['team_2_name'] == team_name)
        ].copy()
        
        logger.info(f"Filtered to {len(team_matches)} matches for {team_name}")
        
        if team_matches.empty:
            logger.warning(f"No matches found for team: {team_name}")
            return _empty_result([
                "season",
                "competition_name",
                "competition_tier",
                "opposition_strength_bucket",
                "match_context",
                "result",
                "runs_for",
                "runs_against",
                "overs_faced",
                "overs_bowled",
            ])
        
        # Transform to expected format
        records = []
        for _, row in team_matches.iterrows():
            # Determine if team was batting first or second
            team_batted_first = row['innings_1_team'] == team_name
            
            if team_batted_first:
                runs_for = row['innings_1_runs'] if pd.notna(row['innings_1_runs']) else 0
                runs_against = row['innings_2_runs'] if pd.notna(row['innings_2_runs']) else 0
                overs_faced = row['innings_1_overs'] if pd.notna(row['innings_1_overs']) else 20.0
                overs_bowled = row['innings_2_overs'] if pd.notna(row['innings_2_overs']) else 20.0
            else:
                runs_for = row['innings_2_runs'] if pd.notna(row['innings_2_runs']) else 0
                runs_against = row['innings_1_runs'] if pd.notna(row['innings_1_runs']) else 0
                overs_faced = row['innings_2_overs'] if pd.notna(row['innings_2_overs']) else 20.0
                overs_bowled = row['innings_1_overs'] if pd.notna(row['innings_1_overs']) else 20.0
            
            # Determine result
            if pd.isna(row['winner_name']):
                result = 'NR'  # No result
            elif row['winner_name'] == team_name:
                result = 'W'
            else:
                result = 'L'
            
            # Determine match context based on match_type
            match_type = str(row['match_type']) if pd.notna(row['match_type']) else ''
            if any(keyword in match_type for keyword in ['Final', 'Qualifier', 'Eliminator', 'Playoff']):
                match_context = 'knockout'
            elif 'Match' in match_type:
                # Extract match number if available
                try:
                    match_num = int(match_type.split()[-1])
                    if match_num >= 25:  # Late-season matches
                        match_context = 'high-pressure'
                    else:
                        match_context = 'league'
                except:
                    match_context = 'league'
            else:
                match_context = 'league'
            
            # Use opposition_strength if available, else default to 'balanced'
            # Ensure lowercase and valid value
            opposition_strength_bucket = row.get('opposition_strength', 'balanced')
            if pd.isna(opposition_strength_bucket):
                opposition_strength_bucket = 'balanced'
            else:
                # Convert to lowercase and validate
                opposition_strength_bucket = str(opposition_strength_bucket).lower()
                if opposition_strength_bucket not in ['strong', 'balanced', 'weak']:
                    opposition_strength_bucket = 'balanced'  # Default to balanced if invalid
            
            records.append({
                'season': row['season'],
                'competition_name': row['tournament_name'] if pd.notna(row['tournament_name']) else 'NPL',
                'competition_tier': 'A',  # NPL is tier A
                'opposition_strength_bucket': opposition_strength_bucket,
                'match_context': match_context,
                'result': result,
                'runs_for': float(runs_for),
                'runs_against': float(runs_against),
                'overs_faced': float(overs_faced),
                'overs_bowled': float(overs_bowled),
            })
        
        df = pd.DataFrame(records)
        logger.info(f"Successfully transformed {len(df)} match records")
        return df
        
    except Exception as e:
        logger.error(f"Error loading parquet data: {e}", exc_info=True)
        raise


def load_match_records() -> Tuple[pd.DataFrame, str]:
    """
    Return match records and source tag (database, parquet, or demo).
    
    Priority order:
    1. Database (if configured)
    2. Parquet files (production data)
    3. Demo data (fallback for testing)
    
    Returns:
        Tuple of (DataFrame with match records, source identifier string)
    """
    logger.info("Loading match records - checking data sources")
    
    # Try database first
    try:
        logger.debug("Attempting to load from database")
        db_df = _load_from_database()
        if not db_df.empty:
            logger.info(f" Loaded {len(db_df)} matches from database")
            return db_df, "database"
        else:
            logger.debug("Database returned empty result")
    except ImportError as e:
        logger.debug(f"Database module not available: {e}")
    except Exception as e:
        logger.warning(f"Database load failed: {e}")
    
    # Try parquet files
    try:
        logger.debug(f"Attempting to load from parquet at {PARQUET_DATA_PATH}")
        parquet_df = _load_from_parquet()
        if not parquet_df.empty:
            logger.info(f" Loaded {len(parquet_df)} matches from parquet files (real data)")
            return parquet_df, "parquet"
        else:
            logger.warning("Parquet load returned empty result")
    except FileNotFoundError as e:
        logger.warning(f"Parquet files not found: {e}")
    except Exception as e:
        logger.error(f"Parquet load failed with error: {e}", exc_info=True)

    # Fall back to empty result if everything fails
    logger.warning(" Falling back to empty result (real data sources unavailable)")
    # Return empty format instead of demo data
    demo_df = _empty_result([
        "season", "competition_name", "competition_tier", 
        "opposition_strength_bucket", "match_context", "result", 
        "runs_for", "runs_against", "overs_faced", "overs_bowled"
    ])
    return demo_df, "demo"
