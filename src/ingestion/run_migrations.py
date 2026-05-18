"""
Database Migration Runner
=========================
Applies SQL migrations from sql/migrations/ to the PostgreSQL database.

Usage:
  python src/ingestion/run_migrations.py
"""

import sys
from pathlib import Path
from loguru import logger

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.db.connection import get_db, test_connection
from sqlalchemy import text

# Configure logging
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:HH:mm:ss}</green> | <level>{level:8}</level> | {message}",
    level="INFO"
)

MIGRATIONS_DIR = Path("sql/migrations")


def get_applied_migrations():
    """Get list of applied migrations from database"""
    with get_db() as db:
        # Create migrations tracking table if it doesn't exist
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                migration_name VARCHAR(255) PRIMARY KEY,
                applied_at TIMESTAMPTZ DEFAULT NOW()
            )
        """))
        
        result = db.execute(text("SELECT migration_name FROM schema_migrations"))
        return {row[0] for row in result.fetchall()}


def apply_migration(migration_file: Path):
    """Apply a single migration file"""
    logger.info(f"Applying migration: {migration_file.name}")
    
    # Read migration SQL
    sql = migration_file.read_text(encoding='utf-8')
    
    with get_db() as db:
        # Execute migration
        db.execute(text(sql))
        
        # Record migration
        db.execute(
            text("INSERT INTO schema_migrations (migration_name) VALUES (:name)"),
            {'name': migration_file.name}
        )
    
    logger.success(f"  ✓ Applied: {migration_file.name}")


def main():
    """Run all pending migrations"""
    logger.info("=" * 80)
    logger.info("DATABASE MIGRATION RUNNER")
    logger.info("=" * 80)
    logger.info("")
    
    # Test connection
    logger.info("Testing database connection...")
    if not test_connection():
        logger.error("Database connection failed. Check .env configuration.")
        return 1
    logger.info("")
    
    # Get applied migrations
    applied = get_applied_migrations()
    logger.info(f"Found {len(applied)} already applied migrations")
    logger.info("")
    
    # Find migration files
    migration_files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    
    if not migration_files:
        logger.warning(f"No migration files found in {MIGRATIONS_DIR}")
        return 0
    
    logger.info(f"Found {len(migration_files)} total migration files")
    logger.info("")
    
    # Apply pending migrations
    pending = [f for f in migration_files if f.name not in applied]
    
    if not pending:
        logger.success("✓ All migrations already applied")
        return 0
    
    logger.info(f"Applying {len(pending)} pending migrations...")
    for migration_file in pending:
        try:
            apply_migration(migration_file)
        except Exception as e:
            logger.error(f"✗ Failed to apply {migration_file.name}: {e}")
            return 1
    
    logger.info("")
    logger.success("=" * 80)
    logger.success("✓ ALL MIGRATIONS APPLIED SUCCESSFULLY")
    logger.success("=" * 80)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
