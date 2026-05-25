"""
Database connection and session management
"""
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool
from contextlib import contextmanager
from loguru import logger
from src.config.settings import get_settings


settings = get_settings()

# Create engine with connection pooling
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=settings.environment == "development"
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@contextmanager
def get_db() -> Session:
    """
    Context manager for database sessions
    
    Usage:
        with get_db() as db:
            result = db.execute(text("SELECT * FROM teams"))
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Database error: {e}")
        raise
    finally:
        db.close()


def test_connection() -> bool:
    """Test database connection"""
    try:
        with get_db() as db:
            result = db.execute(text("SELECT 1"))
            logger.info("Database connection successful")
            return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False


def get_team_count() -> int:
    """Get count of teams in database (for testing)"""
    try:
        with get_db() as db:
            result = db.execute(text("SELECT COUNT(*) FROM teams")).scalar()
            return result
    except Exception as e:
        logger.error(f"Error fetching team count: {e}")
        return 0
