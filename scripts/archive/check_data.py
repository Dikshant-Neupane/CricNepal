# Quick data count check
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from src.db.connection import get_engine

engine = get_engine()

with engine.connect() as conn:
    matches = conn.execute(text("SELECT COUNT(*) FROM matches")).scalar()
    deliveries = conn.execute(text("SELECT COUNT(*) FROM ball_by_ball")).scalar()
    players = conn.execute(text("SELECT COUNT(*) FROM players")).scalar()
    teams = conn.execute(text("SELECT COUNT(*) FROM teams")).scalar()
    
    print("\n" + "="*50)
    print("CricNepal Database Contents")
    print("="*50)
    print(f"Matches:     {matches:,}")
    print(f"Deliveries:  {deliveries:,}")
    print(f"Players:     {players:,}")
    print(f"Teams:       {teams:,}")
    print("="*50)
    print("\nData is in PostgreSQL (localhost:5432)")
    print("="*50 + "\n")
