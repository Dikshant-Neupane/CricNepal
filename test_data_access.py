"""
Quick check to verify the database has data loaded.
Run this to make sure the ingestion worked.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import text
from src.db.connection import get_engine

print("\n" + "="*60)
print("Checking database connection and data...")
print("="*60)

try:
    engine = get_engine()
    with engine.connect() as conn:
        
        # Check how many tables we have
        print("\nDatabase tables:")
        print("-" * 60)
        tables = conn.execute(text("""
            SELECT COUNT(*) as table_count
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)).scalar()
        print(f"   {tables} tables found")
        
        # Get row counts from main tables
        print("\nRow counts:")
        print("-" * 60)
        
        matches = conn.execute(text("SELECT COUNT(*) FROM matches")).scalar()
        print(f"   Matches:     {matches:,}")
        
        deliveries = conn.execute(text("SELECT COUNT(*) FROM ball_by_ball")).scalar()
        print(f"   Deliveries:  {deliveries:,}")
        
        players = conn.execute(text("SELECT COUNT(*) FROM players")).scalar()
        print(f"   Players:     {players:,}")
        
        teams = conn.execute(text("SELECT COUNT(*) FROM teams")).scalar()
        print(f"   Teams:       {teams}")
        
        # Get Janakpur Bolts specific data
        print("\nJanakpur Bolts coverage:")
        print("-" * 60)
        
        janakpur_matches = conn.execute(text("""
            SELECT COUNT(*) 
            FROM matches 
            WHERE batting_team = 'Janakpur Bolts' 
               OR bowling_team = 'Janakpur Bolts'
        """)).scalar()
        print(f"   Matches:     {janakpur_matches}")
        
        janakpur_deliveries = conn.execute(text("""
            SELECT COUNT(*) 
            FROM ball_by_ball bb
            JOIN matches m ON bb.match_id = m.match_id
            WHERE m.batting_team = 'Janakpur Bolts' 
               OR m.bowling_team = 'Janakpur Bolts'
        """)).scalar()
        print(f"   Deliveries:  {janakpur_deliveries:,}")
        
        # Grab a recent match for sanity check
        print("\nMost recent Janakpur match:")
        print("-" * 60)
        
        sample = conn.execute(text("""
            SELECT 
                season,
                match_date,
                batting_team,
                bowling_team,
                winner,
                result_margin,
                result_type
            FROM matches
            WHERE batting_team = 'Janakpur Bolts' 
               OR bowling_team = 'Janakpur Bolts'
            ORDER BY match_date DESC
            LIMIT 1
        """)).fetchone()
        
        if sample:
            print(f"   Season:      {sample[0]}")
            print(f"   Date:        {sample[1]}")
            print(f"   Batting:     {sample[2]}")
            print(f"   Bowling:     {sample[3]}")
            print(f"   Winner:      {sample[4]}")
            print(f"   Margin:      {sample[5]} {sample[6]}")
        
        # Top run scorers across all NPL
        print("\nTop 5 run scorers (all NPL):")
        print("-" * 60)
        
        top_batters = conn.execute(text("""
            SELECT 
                player_name,
                SUM(runs_scored) as total_runs,
                COUNT(*) as innings,
                ROUND(AVG(strike_rate), 1) as avg_sr
            FROM player_innings
            WHERE balls_faced > 0
            GROUP BY player_name
            ORDER BY total_runs DESC
            LIMIT 5
        """)).fetchall()
        
        for i, batter in enumerate(top_batters, 1):
            print(f"   {i}. {batter[0]:<20} {batter[1]:>4} runs ({batter[2]} inns, SR {batter[3]})")
        
        # Quick look at Janakpur's powerplay performance
        print("\nJanakpur powerplay batting:")
        print("-" * 60)
        
        powerplay = conn.execute(text("""
            SELECT 
                m.season,
                COUNT(DISTINCT ps.match_id) as matches,
                ROUND(AVG(ps.run_rate), 2) as avg_rpo,
                ROUND(AVG(ps.dot_ball_percentage), 1) as dot_pct
            FROM phase_summary ps
            JOIN matches m ON ps.match_id = m.match_id
            WHERE m.batting_team = 'Janakpur Bolts'
              AND ps.phase = 'Powerplay'
            GROUP BY m.season
            ORDER BY m.season
        """)).fetchall()
        
        for phase in powerplay:
            print(f"   {phase[0]}: {phase[1]} matches, {phase[2]} RPO, {phase[3]}% dots")
        
        print("\n" + "="*60)
        print("Data access confirmed!")
        print("="*60)
        print("\nLooks good. You can now:")
        print("  - Launch dashboard: streamlit run src/dashboard/app.py")
        print("  - Run analysis: python src/analytics/s1_vs_s2_diagnosis.py")
        print("="*60 + "\n")
        
except Exception as e:
    print(f"\nError: {e}")
    print("\nTroubleshooting:")
    print("  - Check Docker is running: docker ps")
    print("  - Check .env has DB_HOST=localhost")
    print("  - Try re-running: python src/ingestion/quick_start.py")
    sys.exit(1)
