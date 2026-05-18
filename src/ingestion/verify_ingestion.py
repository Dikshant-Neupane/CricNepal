"""
Post-Ingestion Verification Script
===================================
Quick health check to verify NPL data ingestion was successful.

Tests:
  1. Database connection
  2. All tables exist
  3. Expected row counts
  4. Janakpur Bolts data present
  5. Data quality checks

Usage:
  python src/ingestion/verify_ingestion.py
"""

import sys
from pathlib import Path
from loguru import logger
from sqlalchemy import text

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.db.connection import get_db, test_connection

# Configure logging
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:HH:mm:ss}</green> | <level>{level:8}</level> | {message}",
    level="INFO"
)


def check_database_connection():
    """Test 1: Database connection"""
    logger.info("Test 1: Database connection...")
    if test_connection():
        logger.success("  ✓ Connection OK")
        return True
    else:
        logger.error("  ✗ Connection failed")
        return False


def check_tables_exist():
    """Test 2: All required tables exist"""
    logger.info("Test 2: Table existence...")
    
    required_tables = [
        'competitions', 'seasons', 'venues', 'teams', 'players',
        'matches', 'innings', 'deliveries',
        'scorecards_batting', 'scorecards_bowling'
    ]
    
    with get_db() as db:
        missing = []
        for table in required_tables:
            try:
                db.execute(text(f"SELECT 1 FROM {table} LIMIT 1"))
            except Exception:
                missing.append(table)
        
        if missing:
            logger.error(f"  ✗ Missing tables: {', '.join(missing)}")
            return False
        else:
            logger.success(f"  ✓ All {len(required_tables)} tables exist")
            return True


def check_row_counts():
    """Test 3: Row counts match expected ranges"""
    logger.info("Test 3: Row counts...")
    
    expected = {
        'competitions': (1, 5),
        'seasons': (2, 10),
        'venues': (1, 10),
        'teams': (8, 20),
        'players': (50, 300),
        'matches': (64, 200),
        'innings': (120, 400),
        'deliveries': (10000, 50000),
        'scorecards_batting': (500, 5000),
        'scorecards_bowling': (500, 5000)
    }
    
    with get_db() as db:
        all_ok = True
        for table, (min_rows, max_rows) in expected.items():
            count = db.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
            
            if min_rows <= count <= max_rows:
                logger.info(f"    {table:25} {count:>8,} rows ✓")
            else:
                logger.warning(f"    {table:25} {count:>8,} rows (expected {min_rows}-{max_rows})")
                all_ok = False
        
        if all_ok:
            logger.success("  ✓ All row counts in expected range")
        else:
            logger.warning("  ⚠ Some row counts outside expected range (may be OK)")
        
        return all_ok


def check_janakpur_bolts_data():
    """Test 4: Janakpur Bolts data present"""
    logger.info("Test 4: Janakpur Bolts data...")
    
    with get_db() as db:
        # Check team exists
        team = db.execute(text("""
            SELECT team_id, name FROM teams WHERE name = 'Janakpur Bolts'
        """)).fetchone()
        
        if not team:
            logger.error("  ✗ Janakpur Bolts team not found")
            return False
        
        team_id, team_name = team
        logger.info(f"    Team found: {team_name} (ID={team_id})")
        
        # Check for Kathmandu team (verify normalization worked)
        kathmandu_teams = db.execute(text("""
            SELECT name FROM teams WHERE name LIKE 'Kathmandu%'
        """)).fetchall()
        
        if len(kathmandu_teams) == 1:
            logger.success(f"    Team normalization OK: {kathmandu_teams[0][0]} (1 team, not 2)")
        else:
            logger.warning(f"    Found {len(kathmandu_teams)} Kathmandu teams: {[t[0] for t in kathmandu_teams]}")
        
        # Check matches
        matches_count = db.execute(text("""
            SELECT COUNT(*) FROM matches m
            WHERE m.team1_id = :team_id OR m.team2_id = :team_id
        """), {'team_id': team_id}).scalar()
        
        logger.info(f"    Matches: {matches_count}")
        
        # Check wins
        wins_count = db.execute(text("""
            SELECT COUNT(*) FROM matches m
            WHERE m.match_winner_id = :team_id
        """), {'team_id': team_id}).scalar()
        
        win_pct = (wins_count / matches_count * 100) if matches_count > 0 else 0
        logger.info(f"    Wins: {wins_count} ({win_pct:.1f}%)")
        
        if matches_count >= 10 and wins_count > 0:
            logger.success("  ✓ Janakpur Bolts data present")
            return True
        else:
            logger.error("  ✗ Insufficient Janakpur Bolts data")
            return False


def check_data_quality():
    """Test 5: Basic data quality checks"""
    logger.info("Test 5: Data quality...")
    
    with get_db() as db:
        issues = []
        
        # Check for NULL match winners in completed matches
        null_winners = db.execute(text("""
            SELECT COUNT(*) FROM matches
            WHERE match_winner_id IS NULL 
            AND win_type NOT IN ('no result', 'tie')
        """)).scalar()
        
        if null_winners > 5:
            issues.append(f"{null_winners} matches missing winner")
        
        # Check for deliveries with NULL players
        null_players = db.execute(text("""
            SELECT COUNT(*) FROM deliveries
            WHERE striker_id IS NULL OR non_striker_id IS NULL OR bowler_id IS NULL
        """)).scalar()
        
        if null_players > 0:
            issues.append(f"{null_players} deliveries with NULL players")
        
        # Check for negative runs
        negative_runs = db.execute(text("""
            SELECT COUNT(*) FROM deliveries WHERE runs_total < 0
        """)).scalar()
        
        if negative_runs > 0:
            issues.append(f"{negative_runs} deliveries with negative runs")
        
        # Check for invalid phases
        invalid_phases = db.execute(text("""
            SELECT COUNT(*) FROM deliveries
            WHERE phase IS NOT NULL AND phase NOT IN ('powerplay', 'middle', 'death')
        """)).scalar()
        
        if invalid_phases > 0:
            issues.append(f"{invalid_phases} deliveries with invalid phase")
        
        if issues:
            logger.warning("  ⚠ Data quality issues:")
            for issue in issues:
                logger.warning(f"      {issue}")
            return False
        else:
            logger.success("  ✓ No data quality issues")
            return True


def display_summary():
    """Display ingestion summary statistics"""
    logger.info("")
    logger.info("=" * 80)
    logger.info("INGESTION SUMMARY")
    logger.info("=" * 80)
    logger.info("")
    
    with get_db() as db:
        # Competition & season info
        competitions = db.execute(text("""
            SELECT c.name, s.name AS season, s.year, COUNT(DISTINCT m.match_id) AS matches
            FROM competitions c
            JOIN seasons s ON c.competition_id = s.competition_id
            LEFT JOIN matches m ON s.season_id = m.season_id
            GROUP BY c.name, s.name, s.year
            ORDER BY s.year
        """)).fetchall()
        
        logger.info("Competitions & Seasons:")
        for comp, season, year, matches in competitions:
            logger.info(f"  {comp} - {season} ({year}): {matches} matches")
        
        logger.info("")
        
        # Top teams by matches
        teams = db.execute(text("""
            SELECT t.name, COUNT(DISTINCT m.match_id) AS matches,
                   SUM(CASE WHEN m.match_winner_id = t.team_id THEN 1 ELSE 0 END) AS wins
            FROM teams t
            LEFT JOIN matches m ON t.team_id = m.team1_id OR t.team_id = m.team2_id
            GROUP BY t.name
            ORDER BY matches DESC
            LIMIT 5
        """)).fetchall()
        
        logger.info("Top Teams:")
        for team, matches, wins in teams:
            win_pct = (wins / matches * 100) if matches > 0 else 0
            logger.info(f"  {team:25} {matches:>3} matches, {wins:>2} wins ({win_pct:.1f}%)")
        
        logger.info("")
        
        # Top batters (by runs)
        batters = db.execute(text("""
            SELECT p.canonical_name, 
                   SUM(sb.runs_scored) AS total_runs,
                   SUM(sb.balls_faced) AS total_balls,
                   ROUND(SUM(sb.runs_scored) * 100.0 / NULLIF(SUM(sb.balls_faced), 0), 2) AS strike_rate
            FROM players p
            JOIN scorecards_batting sb ON p.player_id = sb.player_id
            GROUP BY p.canonical_name
            HAVING SUM(sb.balls_faced) > 50
            ORDER BY total_runs DESC
            LIMIT 5
        """)).fetchall()
        
        logger.info("Top Batters (≥50 balls):")
        for player, runs, balls, sr in batters:
            logger.info(f"  {player:25} {runs:>4} runs @ SR {sr}")
        
        logger.info("")
        
        # Top bowlers (by wickets)
        bowlers = db.execute(text("""
            SELECT p.canonical_name,
                   SUM(sbow.wickets_taken) AS total_wickets,
                   ROUND(SUM(sbow.overs_bowled), 1) AS total_overs,
                   ROUND(SUM(sbow.runs_conceded) / NULLIF(SUM(sbow.overs_bowled), 0), 2) AS economy
            FROM players p
            JOIN scorecards_bowling sbow ON p.player_id = sbow.player_id
            GROUP BY p.canonical_name
            HAVING SUM(sbow.overs_bowled) > 10
            ORDER BY total_wickets DESC
            LIMIT 5
        """)).fetchall()
        
        logger.info("Top Bowlers (≥10 overs):")
        for player, wickets, overs, economy in bowlers:
            logger.info(f"  {player:25} {wickets:>2} wickets in {overs} overs @ econ {economy}")


def main():
    """Run all verification tests"""
    logger.info("=" * 80)
    logger.info("NPL DATA INGESTION — VERIFICATION")
    logger.info("=" * 80)
    logger.info("")
    
    tests = [
        check_database_connection,
        check_tables_exist,
        check_row_counts,
        check_janakpur_bolts_data,
        check_data_quality
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            logger.error(f"  ✗ Test failed with exception: {e}")
            results.append(False)
        logger.info("")
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    logger.info("=" * 80)
    if all(results):
        logger.success(f"✓ ALL TESTS PASSED ({passed}/{total})")
        logger.info("")
        display_summary()
        logger.info("")
        logger.info("=" * 80)
        logger.success("✓ INGESTION VERIFIED — READY FOR DASHBOARD")
        logger.info("=" * 80)
        logger.info("")
        logger.info("Next step:")
        logger.info("  streamlit run src/dashboard/app.py")
        logger.info("")
        return 0
    else:
        logger.warning(f"⚠ PARTIAL PASS ({passed}/{total})")
        logger.info("")
        logger.info("Some tests failed. Check logs above for details.")
        logger.info("You may still be able to use the dashboard, but verify data quality.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
