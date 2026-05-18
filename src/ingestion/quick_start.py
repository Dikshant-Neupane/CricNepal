"""
Quick Start — Full NPL Data Ingestion Pipeline
===============================================
Runs complete ingestion workflow:
  1. Apply database migrations (schema creation)
  2. Ingest NPL data from Parquet files
  3. Verify data integrity
  4. Display summary

Usage:
  python src/ingestion/quick_start.py [--dry-run]
"""

import sys
import argparse
from pathlib import Path
from loguru import logger

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.db.connection import test_connection
from sqlalchemy import text

# Configure logging
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:HH:mm:ss}</green> | <level>{level:8}</level> | {message}",
    level="INFO"
)


def run_step(step_num: int, step_name: str, module_name: str, dry_run: bool = False):
    """Run a pipeline step (import and execute main function)"""
    logger.info("")
    logger.info("=" * 80)
    logger.info(f"STEP {step_num}: {step_name}")
    logger.info("=" * 80)
    logger.info("")
    
    try:
        # Dynamic import
        if module_name == "run_migrations":
            from src.ingestion import run_migrations
            result = run_migrations.main()
        elif module_name == "ingest_npl_parquet":
            from src.ingestion import ingest_npl_parquet
            result = ingest_npl_parquet.main(dry_run=dry_run)
        else:
            logger.error(f"Unknown module: {module_name}")
            return 1
        
        if result != 0:
            logger.error(f"✗ Step {step_num} failed with exit code {result}")
            return result
        
        logger.success(f"✓ Step {step_num} completed successfully")
        return 0
        
    except Exception as e:
        logger.error(f"✗ Step {step_num} failed with exception: {e}")
        logger.exception(e)
        return 1


def display_summary():
    """Display final database summary"""
    logger.info("")
    logger.info("=" * 80)
    logger.info("DATABASE SUMMARY")
    logger.info("=" * 80)
    logger.info("")
    
    from src.db.connection import get_db
    
    with get_db() as db:
        # Table counts
        tables = [
            'competitions', 'seasons', 'venues', 'teams', 'players',
            'matches', 'innings', 'deliveries',
            'scorecards_batting', 'scorecards_bowling'
        ]
        
        logger.info("Row counts:")
        for table in tables:
            try:
                count = db.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                logger.info(f"  {table:25} {count:>8,} rows")
            except Exception:
                logger.warning(f"  {table:25} <not found>")
        
        logger.info("")
        
        # Janakpur Bolts stats
        try:
            bolts_matches = db.execute(text("""
                SELECT COUNT(*) FROM matches m
                JOIN teams t1 ON m.team1_id = t1.team_id
                JOIN teams t2 ON m.team2_id = t2.team_id
                WHERE t1.name = 'Janakpur Bolts' OR t2.name = 'Janakpur Bolts'
            """)).scalar()
            
            bolts_wins = db.execute(text("""
                SELECT COUNT(*) FROM matches m
                JOIN teams tw ON m.match_winner_id = tw.team_id
                WHERE tw.name = 'Janakpur Bolts'
            """)).scalar()
            
            win_pct = (bolts_wins / bolts_matches * 100) if bolts_matches > 0 else 0
            
            logger.info("Janakpur Bolts subset:")
            logger.info(f"  Matches:     {bolts_matches}")
            logger.info(f"  Wins:        {bolts_wins}")
            logger.info(f"  Win %:       {win_pct:.1f}%")
            
        except Exception as e:
            logger.warning(f"Could not compute Janakpur Bolts stats: {e}")


def main(dry_run: bool = False):
    """Run complete ingestion pipeline"""
    logger.info("")
    logger.info("╔" + "═" * 78 + "╗")
    logger.info("║" + " " * 20 + "NPL DATA INGESTION — QUICK START" + " " * 26 + "║")
    logger.info("╚" + "═" * 78 + "╝")
    logger.info("")
    
    if dry_run:
        logger.warning("⚠ DRY RUN MODE — No data will be written to database")
        logger.info("")
    
    # Pre-flight: Test database connection
    logger.info("Pre-flight: Testing database connection...")
    if not test_connection():
        logger.error("Database connection failed. Check .env configuration.")
        logger.error("Required variables: POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_HOST, POSTGRES_PORT")
        return 1
    logger.success("✓ Database connection OK")
    
    # Step 1: Run migrations
    if not dry_run:
        result = run_step(1, "Apply Database Migrations", "run_migrations", dry_run)
        if result != 0:
            return result
    else:
        logger.info("")
        logger.info("[DRY RUN] Skipping migrations (read-only mode)")
    
    # Step 2: Ingest data
    result = run_step(2, "Ingest NPL Data from Parquet", "ingest_npl_parquet", dry_run)
    if result != 0:
        return result
    
    # Step 3: Display summary
    if not dry_run:
        display_summary()
    
    # Final message
    logger.info("")
    logger.info("╔" + "═" * 78 + "╗")
    logger.info("║" + " " * 25 + "✓ INGESTION COMPLETE" + " " * 33 + "║")
    logger.info("╚" + "═" * 78 + "╝")
    logger.info("")
    logger.info("Next steps:")
    logger.info("  1. Start dashboard:  streamlit run src/dashboard/app.py")
    logger.info("  2. Verify data:      Check 'Executive Overview' page")
    logger.info("  3. Look for badge:   'Data source: Live DB' (not 'Demo')")
    logger.info("")
    
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Quick start: Run full NPL data ingestion pipeline"
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Test pipeline without writing to database'
    )
    args = parser.parse_args()
    
    sys.exit(main(dry_run=args.dry_run))
