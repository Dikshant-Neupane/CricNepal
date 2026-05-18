from sqlalchemy import text
from src.db.connection import get_db

with get_db() as db:
    matches = db.execute(text('SELECT COUNT(*) FROM matches')).scalar()
    deliveries = db.execute(text('SELECT COUNT(*) FROM deliveries')).scalar()
    players = db.execute(text('SELECT COUNT(*) FROM players')).scalar()
    
    print(f"\nCurrent Database State:")
    print(f"  Matches:     {matches}")
    print(f"  Deliveries:  {deliveries}")
    print(f"  Players:     {players}")
