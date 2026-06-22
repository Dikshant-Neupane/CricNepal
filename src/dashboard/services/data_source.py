"""Data source helpers for dashboard metrics and validation."""

from __future__ import annotations

import pandas as pd
import os
from typing import Tuple, Optional

from src.dashboard.demo_data import get_season_match_records
from src.utils.logging_config import get_logger

# Initialize logger
logger = get_logger(__name__)

# Path to real parquet data
PARQUET_DATA_PATH = "D:/Cric_Data/data/final/parquet"


def _empty_result(columns: list[str]) -> pd.DataFrame:
    """Return empty DataFrame with specified columns."""
    return pd.DataFrame(columns=columns)


def _load_from_database() -> pd.DataFrame:
    """Load match-level records from the project database when available."""
    query = """
    WITH jb AS (
        SELECT team_id
        FROM teams
        WHERE LOWER(name) LIKE '%janakpur%'
        ORDER BY team_id
        LIMIT 1
    ),
    match_totals AS (
        SELECT
            m.match_id,
            m.season_id,
            m.match_number,
            m.match_winner_id,
            m.win_type,
            MAX(CASE WHEN i.batting_team_id = jb.team_id THEN i.total_runs END) AS runs_for,
            MAX(CASE WHEN i.batting_team_id <> jb.team_id THEN i.total_runs END) AS runs_against,
            MAX(CASE WHEN i.batting_team_id = jb.team_id THEN i.total_overs END) AS overs_faced,
            MAX(CASE WHEN i.batting_team_id <> jb.team_id THEN i.total_overs END) AS overs_bowled
        FROM matches m
        JOIN innings i ON i.match_id = m.match_id
        CROSS JOIN jb
        WHERE m.team1_id = jb.team_id OR m.team2_id = jb.team_id
        GROUP BY m.match_id, m.season_id, m.match_number, m.match_winner_id, m.win_type
    )
    SELECT
        CASE
            WHEN s.name ILIKE '%season 1%' THEN 'S1'
            WHEN s.name ILIKE '%season 2%' THEN 'S2'
            ELSE COALESCE(s.name, CAST(s.year AS TEXT))
        END AS season,
        c.name AS competition_name,
        CASE
            WHEN c.name ILIKE '%npl%' THEN 'A'
            WHEN c.name ILIKE '%kp oli%' THEN 'B'
            ELSE 'C'
        END AS competition_tier,
        'balanced'::TEXT AS opposition_strength_bucket,
        CASE
            WHEN mt.match_number IS NOT NULL AND mt.match_number >= 30 THEN 'high-pressure'
            ELSE 'league'
        END AS match_context,
        CASE
            WHEN mt.win_type IN ('no result', 'tie') THEN 'NR'
            WHEN mt.match_winner_id = jb.team_id THEN 'W'
            ELSE 'L'
        END AS result,
        COALESCE(mt.runs_for, 0)::FLOAT AS runs_for,
        COALESCE(mt.runs_against, 0)::FLOAT AS runs_against,
        COALESCE(mt.overs_faced, 0)::FLOAT AS overs_faced,
        COALESCE(mt.overs_bowled, 0)::FLOAT AS overs_bowled
    FROM match_totals mt
    JOIN seasons s ON s.season_id = mt.season_id
    JOIN competitions c ON c.competition_id = s.competition_id
    CROSS JOIN jb
    ORDER BY s.year, season;
    """

    from sqlalchemy import text

    # Lazy import avoids hard failure when DB env vars are missing.
    from src.db.connection import get_db

    with get_db() as db:
        rows = db.execute(text(query)).mappings().all()

    if not rows:
        return _empty_result(
            [
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
            ]
        )

    return pd.DataFrame(rows)


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
            logger.info(f"✓ Loaded {len(db_df)} matches from database")
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
            logger.info(f"✓ Loaded {len(parquet_df)} matches from parquet files (real data)")
            return parquet_df, "parquet"
        else:
            logger.warning("Parquet load returned empty result")
    except FileNotFoundError as e:
        logger.warning(f"Parquet files not found: {e}")
    except Exception as e:
        logger.error(f"Parquet load failed with error: {e}", exc_info=True)

    # Fall back to demo data as last resort
    logger.warning("⚠ Falling back to demo data (real data sources unavailable)")
    demo_df = get_season_match_records()
    logger.info(f"Loaded {len(demo_df)} demo records")
    return demo_df, "demo"
