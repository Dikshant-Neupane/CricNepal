"""Data source helpers for dashboard metrics and validation."""

from __future__ import annotations

import pandas as pd
import os
from typing import Tuple

from src.utils.logging_config import get_logger

# Initialize logger
logger = get_logger(__name__)

from src.config.paths import PARQUET_DIR

# Path to real parquet data
PARQUET_DATA_PATH = str(PARQUET_DIR)


def _empty_result(columns: list[str]) -> pd.DataFrame:
    """Return empty DataFrame with specified columns."""
    return pd.DataFrame(columns=columns)


def _load_from_database() -> pd.DataFrame:
    """
    Load match records from the PostgreSQL database (if configured).

    Raises ImportError when sqlalchemy is not installed and propagates
    connection/query errors; load_match_records treats any failure here
    as 'fall through to parquet'.
    """
    from sqlalchemy import create_engine, text  # ImportError -> caller falls back
    from src.config.settings import get_settings

    engine = create_engine(
        get_settings().database_url,
        connect_args={"connect_timeout": 3},
    )
    query = text(
        "SELECT season, competition_name, competition_tier, "
        "opposition_strength_bucket, match_context, result, "
        "runs_for, runs_against, overs_faced, overs_bowled "
        "FROM match_records"
    )
    with engine.connect() as conn:
        return pd.read_sql(query, conn)


def _backfill_innings_summaries(matches: pd.DataFrame) -> pd.DataFrame:
    """Fill missing innings summary columns from ball-by-ball data.

    The cricsheet ingestion leaves innings_1/2 team, runs and overs as NaN in
    matches.parquet, which silently zeroed every downstream runs/overs KPI
    (season NRR displayed as +0.000). When those columns are missing, derive
    them from ball_by_ball.parquet: runs are the innings totals, overs are
    legal deliveries / 6 with the standard NRR all-out rule (an innings
    ending all out counts as the full 20 overs). Super-over innings (>2) are
    excluded, per NRR convention. Existing non-null values are never
    overwritten.
    """
    summary_cols = [
        "innings_1_team", "innings_1_runs", "innings_1_overs",
        "innings_2_team", "innings_2_runs", "innings_2_overs",
    ]
    if all(c in matches.columns and matches[c].notna().any() for c in summary_cols):
        return matches
    bbb_path = os.path.join(PARQUET_DATA_PATH, "ball_by_ball.parquet")
    if not os.path.exists(bbb_path):
        return matches
    try:
        bbb = pd.read_parquet(
            bbb_path,
            columns=["match_id", "innings", "batting_team", "runs_total",
                     "extras_type", "is_wicket", "dismissal_type"],
        )
    except Exception:
        logger.warning("Could not read ball-by-ball parquet for innings backfill", exc_info=True)
        return matches
    bbb = bbb[bbb["innings"] <= 2].copy()
    if bbb.empty:
        return matches
    bbb["legal"] = ~bbb["extras_type"].isin(["wides", "noballs"])
    bbb["wkt"] = bbb["is_wicket"] & (bbb["dismissal_type"] != "retired hurt")
    agg = (
        bbb.groupby(["match_id", "innings", "batting_team"], as_index=False)
        .agg(runs=("runs_total", "sum"), legal=("legal", "sum"), wkts=("wkt", "sum"))
    )
    agg["overs"] = agg.apply(lambda r: 20.0 if r["wkts"] >= 10 else r["legal"] / 6.0, axis=1)
    by_key = {(r.match_id, r.innings): r for r in agg.itertuples()}
    matches = matches.copy()
    for c in summary_cols:
        if c not in matches.columns:
            matches[c] = pd.NA
    # The all-NaN team columns arrive as float64; they must hold strings.
    for c in ("innings_1_team", "innings_2_team"):
        if matches[c].dtype != object:
            matches[c] = matches[c].astype(object)
    for idx, row in matches.iterrows():
        for inn in (1, 2):
            rec = by_key.get((row["match_id"], inn))
            if rec is None:
                continue
            for col, val in (
                (f"innings_{inn}_team", rec.batting_team),
                (f"innings_{inn}_runs", float(rec.runs)),
                (f"innings_{inn}_overs", float(rec.overs)),
            ):
                if pd.isna(row[col]):
                    matches.at[idx, col] = val
    return matches


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
        matches = _backfill_innings_summaries(matches)
        
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
