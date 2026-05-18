"""
NPL Data Ingestion — Parquet to PostgreSQL
==========================================
Reads validated NPL data from scraping pipeline (Parquet files) and ingests into 
the CricNepal PostgreSQL database.

Source: D:\Cric_Data\data\final\parquet\
Target: PostgreSQL (bolts_analytics database)

Tables populated:
  - Reference: competitions, seasons, venues, teams, players
  - Matches: matches, innings
  - Ball-by-ball: deliveries
  - Scorecards: scorecards_batting, scorecards_bowling

Usage:
  python src/ingestion/ingest_npl_parquet.py [--dry-run]
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple

import pandas as pd
from loguru import logger
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.db.connection import get_db, test_connection
from src.config.settings import get_settings

# ══════════════════════════════════════════════════════════════════════════
# Configuration
# ══════════════════════════════════════════════════════════════════════════

settings = get_settings()

# Source Parquet directory (scraping output)
PARQUET_DIR = Path("D:/Cric_Data/data/final/parquet")

# Parquet files
MATCHES_FILE = PARQUET_DIR / "matches.parquet"
BALL_BY_BALL_FILE = PARQUET_DIR / "ball_by_ball.parquet"
PLAYER_INNINGS_FILE = PARQUET_DIR / "player_innings.parquet"
PHASE_SUMMARY_FILE = PARQUET_DIR / "phase_summary.parquet"

# Configure logging
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:HH:mm:ss}</green> | <level>{level:8}</level> | {message}",
    level="INFO"
)
logger.add(
    Path("logs/ingestion_{time:YYYY-MM-DD}.log"),
    rotation="1 day",
    retention="30 days",
    level="DEBUG"
)


# ══════════════════════════════════════════════════════════════════════════
# Helper Functions
# ══════════════════════════════════════════════════════════════════════════

# Team name normalization mapping (handle rebrands/aliases)
TEAM_NAME_MAPPING = {
    # Kathmandu franchise rebrand: Season 1 → Season 2
    "Kathmandu Gurkhas": "Kathmandu Gorkhas",  # S1 name → S2 name (canonical)
    # Sudurpaschim spelling variants
    "Sudur Paschim Royals": "Sudurpaschim Royals",  # Space variant → canonical
    # Add other historical rebrands here as needed
}

def normalize_team_name(team_name) -> str:
    """
    Normalize team names to handle rebrands and aliases.
    
    Example: "Kathmandu Gurkhas" (S1) → "Kathmandu Gorkhas" (S2, canonical)
    
    Returns the canonical team name, or empty string if input is None/NaN.
    """
    if team_name is None or (isinstance(team_name, float) and pd.isna(team_name)):
        return ""
    
    team_name_str = str(team_name)
    return TEAM_NAME_MAPPING.get(team_name_str, team_name_str)


def validate_files() -> bool:
    """Check that all required Parquet files exist"""
    logger.info("Validating Parquet files...")
    
    files = [MATCHES_FILE, BALL_BY_BALL_FILE, PLAYER_INNINGS_FILE, PHASE_SUMMARY_FILE]
    missing = [f for f in files if not f.exists()]
    
    if missing:
        logger.error(f"Missing Parquet files:")
        for f in missing:
            logger.error(f"  - {f}")
        return False
    
    logger.success(f"All 4 Parquet files found")
    return True


def load_parquet_files() -> Dict[str, pd.DataFrame]:
    """Load all Parquet files into DataFrames"""
    logger.info("Loading Parquet files...")
    
    dfs = {
        "matches": pd.read_parquet(MATCHES_FILE),
        "ball_by_ball": pd.read_parquet(BALL_BY_BALL_FILE),
        "player_innings": pd.read_parquet(PLAYER_INNINGS_FILE),
        "phase_summary": pd.read_parquet(PHASE_SUMMARY_FILE)
    }
    
    # Rename columns in ball_by_ball to match expected schema
    ball_by_ball = dfs['ball_by_ball']
    column_mapping = {
        'innings': 'innings_num',
        'over': 'over_num',
        'ball': 'ball_num',
        'batter_name': 'striker',
        'non_striker_name': 'non_striker',
        'bowler_name': 'bowler',
        'runs_off_bat': 'runs_off_bat',
        'dismissal_type': 'wicket_type'
    }
    ball_by_ball = ball_by_ball.rename(columns=column_mapping)
    
    # Parse extras_type into boolean flags
    ball_by_ball['is_wide'] = ball_by_ball['extras_type'] == 'wides'
    ball_by_ball['is_noball'] = ball_by_ball['extras_type'] == 'noballs'
    ball_by_ball['is_bye'] = ball_by_ball['extras_type'] == 'byes'
    ball_by_ball['is_legbye'] = ball_by_ball['extras_type'] == 'legbyes'
    
    # Parse boundary_type into boolean flags
    ball_by_ball['is_boundary_4'] = ball_by_ball['boundary_type'] == '4'
    ball_by_ball['is_boundary_6'] = ball_by_ball['boundary_type'] == '6'
    
    dfs['ball_by_ball'] = ball_by_ball
    
    # Rename columns in player_innings to match expected schema
    player_innings = dfs['player_innings']
    player_innings = player_innings.rename(columns={'innings': 'innings_num'})
    dfs['player_innings'] = player_innings
    
    for name, df in dfs.items():
        logger.info(f"  {name:20} {len(df):>8,} rows")
    
    return dfs


def extract_player_names(dfs: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Extract unique player names from ball-by-ball and player_innings"""
    logger.info("Extracting unique player names...")
    
    players = set()
    
    # From ball_by_ball (using renamed columns)
    if 'striker' in dfs['ball_by_ball'].columns:
        players.update(dfs['ball_by_ball']['striker'].dropna().unique())
    if 'non_striker' in dfs['ball_by_ball'].columns:
        players.update(dfs['ball_by_ball']['non_striker'].dropna().unique())
    if 'bowler' in dfs['ball_by_ball'].columns:
        players.update(dfs['ball_by_ball']['bowler'].dropna().unique())
    
    # From player_innings
    if 'player_name' in dfs['player_innings'].columns:
        players.update(dfs['player_innings']['player_name'].dropna().unique())
    
    player_df = pd.DataFrame({
        'canonical_name': sorted(players),
        'batting_hand': 'Unknown',
        'bowling_arm': 'Unknown',
        'primary_role': 'Batter',
        'country': 'Nepal'
    })
    
    logger.info(f"  Found {len(player_df)} unique players")
    return player_df


# ══════════════════════════════════════════════════════════════════════════
# Ingestion Functions
# ══════════════════════════════════════════════════════════════════════════

def ingest_competitions_and_seasons(matches_df: pd.DataFrame, dry_run: bool = False) -> Dict[str, int]:
    """Create competitions and seasons, return mapping to IDs"""
    logger.info("Ingesting competitions and seasons...")
    
    # NPL competition
    competition_name = "Nepal Premier League"
    competition_short = "NPL"
    
    if dry_run:
        logger.info(f"  [DRY RUN] Would create competition: {competition_name}")
        return {'competition_id': 1, 'season_s1_id': 1, 'season_s2_id': 2}
    
    with get_db() as db:
        # Insert competition (UPSERT)
        result = db.execute(text("""
            INSERT INTO competitions (name, short_name, country, format)
            VALUES (:name, :short_name, :country, :format)
            ON CONFLICT (name, country) DO UPDATE SET short_name = EXCLUDED.short_name
            RETURNING competition_id
        """), {
            'name': competition_name,
            'short_name': competition_short,
            'country': 'Nepal',
            'format': 'T20'
        })
        competition_id = result.scalar()
        logger.success(f"  Competition: {competition_name} (ID={competition_id})")
        
        # Insert seasons
        season_ids = {}
        for season_name, year in [('Season 1', 2023), ('Season 2', 2024)]:
            result = db.execute(text("""
                INSERT INTO seasons (competition_id, name, year)
                VALUES (:competition_id, :name, :year)
                ON CONFLICT (competition_id, year) DO UPDATE SET name = EXCLUDED.name
                RETURNING season_id
            """), {
                'competition_id': competition_id,
                'name': season_name,
                'year': year
            })
            season_id = result.scalar()
            season_ids[f"season_{season_name.lower().replace(' ', '_')}_id"] = season_id
            logger.success(f"  ✓ Season: {season_name} {year} (ID={season_id})")
        
        return {'competition_id': competition_id, **season_ids}


def ingest_venues(matches_df: pd.DataFrame, dry_run: bool = False) -> Dict[str, int]:
    """Create venues, return mapping venue_name -> venue_id"""
    logger.info("Ingesting venues...")
    
    # Extract unique venues from matches
    venues = matches_df[['venue_name', 'city', 'country']].drop_duplicates()
    
    if dry_run:
        logger.info(f"  [DRY RUN] Would create {len(venues)} venues")
        return {}
    
    venue_map = {}
    with get_db() as db:
        for _, row in venues.iterrows():
            result = db.execute(text("""
                INSERT INTO venues (name, city, country)
                VALUES (:name, :city, :country)
                ON CONFLICT (name, city) DO UPDATE SET country = EXCLUDED.country
                RETURNING venue_id
            """), {
                'name': row['venue_name'],
                'city': row.get('city', 'Kirtipur'),
                'country': row.get('country', 'Nepal')
            })
            venue_id = result.scalar()
            venue_map[row['venue_name']] = venue_id
        
        logger.success(f"  ✓ Created {len(venue_map)} venues")
    
    return venue_map


def ingest_teams(matches_df: pd.DataFrame, dry_run: bool = False) -> Dict[str, int]:
    """Create teams, return mapping team_name -> team_id"""
    logger.info("Ingesting teams...")
    
    # Extract unique teams and normalize names (handle rebrands)
    teams = set()
    teams.update(matches_df['team_1_name'].dropna().apply(normalize_team_name).unique())
    teams.update(matches_df['team_2_name'].dropna().apply(normalize_team_name).unique())
    
    if dry_run:
        logger.info(f"  [DRY RUN] Would create {len(teams)} teams")
        return {}
    
    team_map = {}
    with get_db() as db:
        for canonical_name in sorted(teams):
            # Generate short name (e.g., "Janakpur Bolts" -> "JB")
            short_name = ''.join([word[0] for word in canonical_name.split()[:2]])
            
            result = db.execute(text("""
                INSERT INTO teams (name, short_name)
                VALUES (:name, :short_name)
                ON CONFLICT (name) DO UPDATE SET short_name = EXCLUDED.short_name
                RETURNING team_id
            """), {
                'name': canonical_name,
                'short_name': short_name
            })
            team_id = result.scalar()
            
            # Map both canonical name and any aliases to the same team_id
            team_map[canonical_name] = team_id
            
            # Also map old names to new team_id (for lookup during ingestion)
            for old_name, new_name in TEAM_NAME_MAPPING.items():
                if new_name == canonical_name:
                    team_map[old_name] = team_id
        
        logger.success(f"  ✓ Created {len(teams)} teams (normalized {len(TEAM_NAME_MAPPING)} aliases)")
    
    return team_map


def ingest_players(player_df: pd.DataFrame, dry_run: bool = False) -> Dict[str, int]:
    """Create players, return mapping player_name -> player_id"""
    logger.info(f"Ingesting {len(player_df)} players...")
    
    if dry_run:
        logger.info(f"  [DRY RUN] Would create {len(player_df)} players")
        return {}
    
    player_map = {}
    with get_db() as db:
        for _, row in player_df.iterrows():
            result = db.execute(text("""
                INSERT INTO players (canonical_name, batting_hand, bowling_arm, primary_role, country)
                VALUES (:name, :batting_hand, :bowling_arm, :role, :country)
                ON CONFLICT (canonical_name, date_of_birth) 
                DO UPDATE SET country = EXCLUDED.country
                RETURNING player_id
            """), {
                'name': row['canonical_name'],
                'batting_hand': row.get('batting_hand', 'Unknown'),
                'bowling_arm': row.get('bowling_arm', 'Unknown'),
                'role': row.get('primary_role', 'Batter'),
                'country': row.get('country', 'Nepal')
            })
            player_id = result.scalar()
            player_map[row['canonical_name']] = player_id
        
        logger.success(f"  ✓ Created {len(player_map)} players")
    
    return player_map


def ingest_matches(
    matches_df: pd.DataFrame,
    season_map: Dict[str, int],
    venue_map: Dict[str, int],
    team_map: Dict[str, int],
    player_map: Dict[str, int],
    dry_run: bool = False
) -> Dict[str, int]:
    """Ingest matches, return mapping match_id (from Parquet) -> match_id (PostgreSQL)"""
    logger.info(f"Ingesting {len(matches_df)} matches...")
    
    if dry_run:
        logger.info(f"  [DRY RUN] Would create {len(matches_df)} matches")
        return {}
    
    match_map = {}
    with get_db() as db:
        for _, row in matches_df.iterrows():
            # Map season
            season_code = row.get('season', 'S1')
            season_id = season_map.get(f"season_season_1_id" if season_code == 'S1' else "season_season_2_id")
            
            # Map teams (normalize names to handle rebrands)
            team1_id = team_map.get(normalize_team_name(row['team_1_name']))
            team2_id = team_map.get(normalize_team_name(row['team_2_name']))
            
            # Map venue
            venue_id = venue_map.get(row['venue_name'])
            
            # Map toss winner (normalize name)
            toss_winner_name = normalize_team_name(row.get('toss_winner_name'))
            toss_winner_id = team_map.get(toss_winner_name) if toss_winner_name else None
            
            # Map match winner (normalize name)
            winner_name = normalize_team_name(row.get('winner_name')) if pd.notna(row.get('winner_name')) else None
            winner_id = team_map.get(winner_name) if winner_name else None
            
            # Map player of match
            pom_id = player_map.get(row.get('player_of_match')) if pd.notna(row.get('player_of_match')) else None
            
            result = db.execute(text("""
                INSERT INTO matches (
                    season_id, match_number, match_date, venue_id,
                    team1_id, team2_id, toss_winner_id, toss_decision,
                    match_winner_id, win_type, win_margin, player_of_match_id,
                    source, source_match_id
                )
                VALUES (
                    :season_id, :match_number, :match_date, :venue_id,
                    :team1_id, :team2_id, :toss_winner_id, :toss_decision,
                    :winner_id, :win_type, :win_margin, :pom_id,
                    :source, :source_match_id
                )
                ON CONFLICT (source, source_match_id) DO UPDATE 
                SET match_winner_id = EXCLUDED.match_winner_id
                RETURNING match_id
            """), {
                'season_id': season_id,
                'match_number': row.get('match_number'),
                'match_date': pd.to_datetime(row['match_date']).date() if pd.notna(row.get('match_date')) else None,
                'venue_id': venue_id,
                'team1_id': team1_id,
                'team2_id': team2_id,
                'toss_winner_id': toss_winner_id,
                'toss_decision': row.get('toss_decision'),
                'winner_id': winner_id,
                'win_type': row.get('win_by', '').lower() if pd.notna(row.get('win_by')) else None,
                'win_margin': int(row['win_margin']) if pd.notna(row.get('win_margin')) else None,
                'pom_id': pom_id,
                'source': 'cricsheet',
                'source_match_id': row['match_id']
            })
            pg_match_id = result.scalar()
            match_map[row['match_id']] = pg_match_id
        
        logger.success(f"  ✓ Created {len(match_map)} matches")
    
    return match_map


def ingest_innings_and_deliveries(
    ball_by_ball_df: pd.DataFrame,
    match_map: Dict[str, int],
    team_map: Dict[str, int],
    player_map: Dict[str, int],
    dry_run: bool = False
) -> Dict[Tuple[str, int], int]:
    """Ingest innings and deliveries, return mapping (match_id, innings_num) -> innings_id"""
    logger.info(f"Ingesting innings and {len(ball_by_ball_df)} deliveries...")
    
    if dry_run:
        logger.info(f"  [DRY RUN] Would create innings and deliveries")
        return {}
    
    innings_map = {}
    
    # Group by match and innings
    grouped = ball_by_ball_df.groupby(['match_id', 'innings_num'])
    
    with get_db() as db:
        for (match_id, innings_num), innings_df in grouped:
            pg_match_id = match_map.get(match_id)
            if not pg_match_id:
                logger.warning(f"  Skipping innings for unknown match: {match_id}")
                continue
            
            # Get innings totals
            total_runs = innings_df['runs_total'].sum()
            total_wickets = innings_df['is_wicket'].sum()
            total_overs = innings_df['over_num'].max() + (innings_df[innings_df['over_num'] == innings_df['over_num'].max()]['ball_num'].max() / 10)
            total_extras = innings_df['runs_extras'].sum()
            
            # Get teams (assuming batting_team and bowling_team columns exist)
            batting_team = innings_df['batting_team'].iloc[0] if 'batting_team' in innings_df.columns else None
            bowling_team = innings_df['bowling_team'].iloc[0] if 'bowling_team' in innings_df.columns else None
            
            # Normalize team names before lookup
            batting_team_id = team_map.get(normalize_team_name(batting_team)) if batting_team else None
            bowling_team_id = team_map.get(normalize_team_name(bowling_team)) if bowling_team else None
            
            # Create innings
            result = db.execute(text("""
                INSERT INTO innings (
                    match_id, innings_number, batting_team_id, bowling_team_id,
                    total_runs, total_wickets, total_overs, total_extras
                )
                VALUES (
                    :match_id, :innings_num, :batting_team_id, :bowling_team_id,
                    :total_runs, :total_wickets, :total_overs, :total_extras
                )
                ON CONFLICT (match_id, innings_number) DO UPDATE
                SET total_runs = EXCLUDED.total_runs
                RETURNING innings_id
            """), {
                'match_id': pg_match_id,
                'innings_num': innings_num,
                'batting_team_id': batting_team_id,
                'bowling_team_id': bowling_team_id,
                'total_runs': int(total_runs),
                'total_wickets': int(total_wickets),
                'total_overs': float(total_overs),
                'total_extras': int(total_extras)
            })
            innings_id = result.scalar()
            innings_map[(match_id, innings_num)] = innings_id
            
            # Insert deliveries for this innings (bulk insert)
            deliveries = []
            for _, delivery in innings_df.iterrows():
                striker_id = player_map.get(delivery.get('striker'))
                non_striker_id = player_map.get(delivery.get('non_striker'))
                bowler_id = player_map.get(delivery.get('bowler'))
                
                if not all([striker_id, non_striker_id, bowler_id]):
                    continue
                
                deliveries.append({
                    'innings_id': innings_id,
                    'over_number': int(delivery['over_num']),
                    'ball_number': int(delivery['ball_num']),
                    'striker_id': striker_id,
                    'non_striker_id': non_striker_id,
                    'bowler_id': bowler_id,
                    'runs_batter': int(delivery.get('runs_off_bat', 0)),
                    'runs_extras': int(delivery.get('runs_extras', 0)),
                    'runs_total': int(delivery.get('runs_total', 0)),
                    'is_wide': bool(delivery.get('is_wide', False)),
                    'is_noball': bool(delivery.get('is_noball', False)),
                    'is_bye': bool(delivery.get('is_bye', False)),
                    'is_legbye': bool(delivery.get('is_legbye', False)),
                    'is_boundary_four': bool(delivery.get('is_boundary_4', False)),
                    'is_boundary_six': bool(delivery.get('is_boundary_6', False)),
                    'is_wicket': bool(delivery.get('is_wicket', False)),
                    'dismissal_type': delivery.get('wicket_type'),
                    'phase': delivery.get('phase', 'powerplay').lower(),
                    'source': 'cricsheet'
                })
            
            # Bulk insert deliveries
            if deliveries:
                db.execute(text("""
                    INSERT INTO deliveries (
                        innings_id, over_number, ball_number, striker_id, non_striker_id, bowler_id,
                        runs_batter, runs_extras, runs_total, is_wide, is_noball, is_bye, is_legbye,
                        is_boundary_four, is_boundary_six, is_wicket, dismissal_type, phase, source
                    )
                    VALUES (
                        :innings_id, :over_number, :ball_number, :striker_id, :non_striker_id, :bowler_id,
                        :runs_batter, :runs_extras, :runs_total, :is_wide, :is_noball, :is_bye, :is_legbye,
                        :is_boundary_four, :is_boundary_six, :is_wicket, :dismissal_type, :phase, :source
                    )
                    ON CONFLICT (innings_id, over_number, ball_number) DO NOTHING
                """), deliveries)
        
        logger.success(f"  ✓ Created {len(innings_map)} innings and deliveries")
    
    return innings_map


def ingest_scorecards(
    player_innings_df: pd.DataFrame,
    innings_map: Dict[Tuple[str, int], int],
    player_map: Dict[str, int],
    dry_run: bool = False
):
    """Ingest batting and bowling scorecards"""
    logger.info(f"Ingesting {len(player_innings_df)} player scorecards...")
    
    if dry_run:
        logger.info(f"  [DRY RUN] Would create scorecards")
        return
    
    batting_records = []
    bowling_records = []
    
    for _, row in player_innings_df.iterrows():
        innings_id = innings_map.get((row['match_id'], row['innings_num']))
        player_id = player_map.get(row['player_name'])
        
        if not innings_id or not player_id:
            continue
        
        # Batting scorecard
        if row.get('role') == 'batter' or pd.notna(row.get('runs_scored')):
            batting_records.append({
                'innings_id': innings_id,
                'player_id': player_id,
                'batting_position': int(row.get('batting_position', 999)),
                'runs_scored': int(row.get('runs_scored', 0)),
                'balls_faced': int(row.get('balls_faced', 0)),
                'fours': int(row.get('fours', 0)),
                'sixes': int(row.get('sixes', 0)),
                'strike_rate': float(row['strike_rate']) if pd.notna(row.get('strike_rate')) else None,
                'dismissal_type': row.get('dismissal_type')
            })
        
        # Bowling scorecard
        if row.get('role') == 'bowler' or pd.notna(row.get('wickets')):
            bowling_records.append({
                'innings_id': innings_id,
                'player_id': player_id,
                'overs_bowled': float(row.get('overs_bowled', 0)),
                'runs_conceded': int(row.get('runs_conceded', 0)),
                'wickets_taken': int(row.get('wickets', 0)),
                'economy_rate': float(row['economy']) if pd.notna(row.get('economy')) else None,
                'wides': int(row.get('wides', 0)),
                'noballs': int(row.get('noballs', 0))
            })
    
    with get_db() as db:
        # Bulk insert batting
        if batting_records:
            db.execute(text("""
                INSERT INTO scorecards_batting (
                    innings_id, player_id, batting_position, runs_scored, balls_faced,
                    fours, sixes, strike_rate, dismissal_type
                )
                VALUES (
                    :innings_id, :player_id, :batting_position, :runs_scored, :balls_faced,
                    :fours, :sixes, :strike_rate, :dismissal_type
                )
                ON CONFLICT (innings_id, player_id) DO UPDATE
                SET runs_scored = EXCLUDED.runs_scored
            """), batting_records)
            logger.success(f"  ✓ Created {len(batting_records)} batting records")
        
        # Bulk insert bowling
        if bowling_records:
            db.execute(text("""
                INSERT INTO scorecards_bowling (
                    innings_id, player_id, overs_bowled, runs_conceded, wickets_taken,
                    economy_rate, wides, noballs
                )
                VALUES (
                    :innings_id, :player_id, :overs_bowled, :runs_conceded, :wickets_taken,
                    :economy_rate, :wides, :noballs
                )
                ON CONFLICT (innings_id, player_id) DO UPDATE
                SET wickets_taken = EXCLUDED.wickets_taken
            """), bowling_records)
            logger.success(f"  ✓ Created {len(bowling_records)} bowling records")


# ══════════════════════════════════════════════════════════════════════════
# Main Execution
# ══════════════════════════════════════════════════════════════════════════

def main(dry_run: bool = False):
    """Main ingestion pipeline"""
    logger.info("=" * 80)
    logger.info("NPL DATA INGESTION — Parquet to PostgreSQL")
    logger.info("=" * 80)
    logger.info(f"Source: {PARQUET_DIR}")
    logger.info(f"Target: {settings.postgres_db}@{settings.postgres_host}")
    if dry_run:
        logger.warning("DRY RUN MODE — No data will be written")
    logger.info("")
    
    # Step 0: Validate files
    if not validate_files():
        logger.error("Validation failed. Exiting.")
        return 1
    
    # Step 1: Test database connection
    logger.info("Testing database connection...")
    if not test_connection():
        logger.error("Database connection failed. Check .env configuration.")
        return 1
    logger.info("")
    
    # Step 2: Load Parquet files
    dfs = load_parquet_files()
    logger.info("")
    
    # Step 3: Extract reference data
    player_df = extract_player_names(dfs)
    logger.info("")
    
    # Step 4: Ingest reference tables
    season_map = ingest_competitions_and_seasons(dfs['matches'], dry_run)
    venue_map = ingest_venues(dfs['matches'], dry_run)
    team_map = ingest_teams(dfs['matches'], dry_run)
    player_map = ingest_players(player_df, dry_run)
    logger.info("")
    
    # Step 5: Ingest matches
    match_map = ingest_matches(
        dfs['matches'], season_map, venue_map, team_map, player_map, dry_run
    )
    logger.info("")
    
    # Step 6: Ingest innings and deliveries
    innings_map = ingest_innings_and_deliveries(
        dfs['ball_by_ball'], match_map, team_map, player_map, dry_run
    )
    logger.info("")
    
    # Step 7: Ingest scorecards
    ingest_scorecards(dfs['player_innings'], innings_map, player_map, dry_run)
    logger.info("")
    
    # Step 8: Verification
    if not dry_run:
        logger.info("Verifying ingestion...")
        with get_db() as db:
            counts = {
                'competitions': db.execute(text("SELECT COUNT(*) FROM competitions")).scalar(),
                'seasons': db.execute(text("SELECT COUNT(*) FROM seasons")).scalar(),
                'venues': db.execute(text("SELECT COUNT(*) FROM venues")).scalar(),
                'teams': db.execute(text("SELECT COUNT(*) FROM teams")).scalar(),
                'players': db.execute(text("SELECT COUNT(*) FROM players")).scalar(),
                'matches': db.execute(text("SELECT COUNT(*) FROM matches")).scalar(),
                'innings': db.execute(text("SELECT COUNT(*) FROM innings")).scalar(),
                'deliveries': db.execute(text("SELECT COUNT(*) FROM deliveries")).scalar(),
                'scorecards_batting': db.execute(text("SELECT COUNT(*) FROM scorecards_batting")).scalar(),
                'scorecards_bowling': db.execute(text("SELECT COUNT(*) FROM scorecards_bowling")).scalar(),
            }
            
            logger.info("Database row counts:")
            for table, count in counts.items():
                logger.info(f"  {table:25} {count:>8,} rows")
    
    logger.info("")
    logger.success("=" * 80)
    logger.success("NPL DATA INGESTION COMPLETE")
    logger.success("=" * 80)
    
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest NPL Parquet data into PostgreSQL")
    parser.add_argument('--dry-run', action='store_true', help='Validate without writing to database')
    args = parser.parse_args()
    
    sys.exit(main(dry_run=args.dry_run))
