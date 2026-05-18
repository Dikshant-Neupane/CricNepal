from sqlalchemy import text
from src.db.connection import get_db

with get_db() as db:
    # Overall counts
    matches = db.execute(text('SELECT COUNT(*) FROM matches')).scalar()
    deliveries = db.execute(text('SELECT COUNT(*) FROM deliveries')).scalar()
    innings = db.execute(text('SELECT COUNT(*) FROM innings')).scalar()
    players = db.execute(text('SELECT COUNT(*) FROM players')).scalar()
    
    # Janakpur Bolts specific
    janakpur = db.execute(text("""
        SELECT COUNT(*) FROM matches m
        JOIN teams t1 ON m.team1_id = t1.team_id OR m.team2_id = t1.team_id
        WHERE t1.name = 'Janakpur Bolts'
    """)).scalar()
    
    bolts_deliveries = db.execute(text("""
        SELECT COUNT(*) FROM deliveries d
        JOIN innings i ON d.innings_id = i.innings_id
        JOIN teams t ON i.batting_team_id = t.team_id OR i.bowling_team_id = t.team_id
        WHERE t.name = 'Janakpur Bolts'
    """)).scalar()
    
    print(f"\n{'='*60}")
    print(f"CRICNEPAL DATABASE — LOADED SUCCESSFULLY")
    print(f"{'='*60}")
    print(f"Matches:              {matches:>8,}")
    print(f"Innings:              {innings:>8,}")
    print(f"Deliveries:           {deliveries:>8,}")
    print(f"Players:              {players:>8,}")
    print(f"\nJanakpur Bolts:")
    print(f"  Matches:            {janakpur:>8,}")
    print(f"  Deliveries:         {bolts_deliveries:>8,}")
    print(f"{'='*60}\n")
