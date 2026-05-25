"""
Janakpur Bolts: Season 1 vs Season 2 analysis

Why did they win S1 but struggle in S2?

Looks at:
- Phase performance (Powerplay/Middle/Death)
- Batting vs bowling contributions
- Player retention and form changes
- Win rate breakdown

Run: python src/analytics/s1_vs_s2_diagnosis.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from loguru import logger
from sqlalchemy import text
import pandas as pd

from src.db.connection import get_engine


def get_phase_comparison(season1: str = "S1", season2: str = "S2") -> pd.DataFrame:
    """Get phase-wise batting performance for both seasons."""
    engine = get_engine()
    
    query = text("""
        SELECT 
            ps.phase,
            m.season,
            COUNT(DISTINCT ps.match_id) as matches,
            AVG(ps.run_rate) as avg_run_rate,
            AVG(ps.total_wickets) as avg_wickets,
            AVG(ps.dot_ball_percentage) as avg_dot_percentage,
            AVG(ps.boundary_percentage) as avg_boundary_percentage
        FROM phase_summary ps
        JOIN matches m ON ps.match_id = m.match_id
        WHERE m.batting_team = 'Janakpur Bolts'
          AND m.season IN (:season1, :season2)
        GROUP BY ps.phase, m.season
        ORDER BY 
            CASE ps.phase 
                WHEN 'Powerplay' THEN 1
                WHEN 'Middle' THEN 2
                WHEN 'Death' THEN 3
            END,
            m.season;
    """)
    
    with engine.connect() as conn:
        df = pd.read_sql(query, conn, params={"season1": season1, "season2": season2})
    
    logger.info(f"Got phase comparison: {len(df)} rows")
    return df


def get_bowling_comparison(season1: str = "S1", season2: str = "S2") -> pd.DataFrame:
    """Get bowling stats when Janakpur bowled."""
    engine = get_engine()
    
    query = text("""
        SELECT 
            ps.phase,
            m.season,
            COUNT(DISTINCT ps.match_id) as matches,
            AVG(ps.run_rate) as avg_economy,
            AVG(ps.total_wickets) as avg_wickets_taken,
            AVG(ps.dot_ball_percentage) as avg_dot_percentage
        FROM phase_summary ps
        JOIN matches m ON ps.match_id = m.match_id
        WHERE m.bowling_team = 'Janakpur Bolts'
          AND m.season IN (:season1, :season2)
        GROUP BY ps.phase, m.season
        ORDER BY 
            CASE ps.phase 
                WHEN 'Powerplay' THEN 1
                WHEN 'Middle' THEN 2
                WHEN 'Death' THEN 3
            END,
            m.season;
    """)
    
    with engine.connect() as conn:
        df = pd.read_sql(query, conn, params={"season1": season1, "season2": season2})
    
    logger.info(f"Got bowling comparison: {len(df)} rows")
    return df


def get_win_rate_by_season() -> pd.DataFrame:
    """Win rate and match outcomes by season."""
    engine = get_engine()
    
    query = text("""
        SELECT 
            season,
            COUNT(*) as total_matches,
            SUM(CASE WHEN winner = 'Janakpur Bolts' THEN 1 ELSE 0 END) as wins,
            ROUND(
                100.0 * SUM(CASE WHEN winner = 'Janakpur Bolts' THEN 1 ELSE 0 END) / COUNT(*), 
                1
            ) as win_percentage,
            AVG(CASE 
                WHEN winner = 'Janakpur Bolts' THEN result_margin 
                ELSE NULL 
            END) as avg_win_margin,
            SUM(CASE WHEN toss_winner = 'Janakpur Bolts' THEN 1 ELSE 0 END) as tosses_won,
            SUM(CASE 
                WHEN toss_winner = 'Janakpur Bolts' 
                AND winner = 'Janakpur Bolts' 
                THEN 1 ELSE 0 
            END) as wins_after_winning_toss
        FROM matches
        WHERE batting_team = 'Janakpur Bolts' 
           OR bowling_team = 'Janakpur Bolts'
        GROUP BY season
        ORDER BY season;
    """)
    
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)
    
    logger.info(f"Got win rate data: {len(df)} rows")
    return df


def get_top_players_comparison(season1: str = "S1", season2: str = "S2", min_innings: int = 5) -> pd.DataFrame:
    """Compare key players' performance across seasons."""
    engine = get_engine()
    
    query = text("""
        SELECT 
            pi.player_name,
            m.season,
            COUNT(*) as innings,
            SUM(pi.runs_scored) as total_runs,
            SUM(pi.balls_faced) as total_balls,
            ROUND(AVG(pi.runs_scored), 1) as avg_runs,
            ROUND(AVG(pi.strike_rate), 1) as avg_strike_rate,
            MAX(pi.runs_scored) as highest_score,
            SUM(CASE WHEN pi.runs_scored >= 50 THEN 1 ELSE 0 END) as fifties
        FROM player_innings pi
        JOIN matches m ON pi.match_id = m.match_id
        WHERE pi.team = 'Janakpur Bolts'
          AND m.season IN (:season1, :season2)
          AND pi.balls_faced > 0  -- Exclude DNBs
        GROUP BY pi.player_name, m.season
        HAVING COUNT(*) >= :min_innings
        ORDER BY m.season, total_runs DESC;
    """)
    
    with engine.connect() as conn:
        df = pd.read_sql(query, conn, params={
            "season1": season1, 
            "season2": season2,
            "min_innings": min_innings
        })
    
    logger.info(f"Got player comparison: {len(df)} rows")
    return df


def generate_diagnosis_report():
    """Run the full analysis and export results."""
    logger.info("Starting S1 vs S2 diagnosis...")
    
    # Win rate comparison
    logger.info("Getting win rates...")
    win_rate_df = get_win_rate_by_season()
    print("\n" + "="*60)
    print("Win Rate Comparison")
    print("="*60)
    print(win_rate_df.to_string(index=False))
    
    # Phase-wise batting
    logger.info("Getting batting phases...")
    phase_batting_df = get_phase_comparison()
    print("\n" + "="*60)
    print("Batting by Phase")
    print("="*60)
    print(phase_batting_df.to_string(index=False))
    
    # Phase-wise bowling
    logger.info("Getting bowling phases...")
    phase_bowling_df = get_bowling_comparison()
    print("\n" + "="*60)
    print("Bowling by Phase")
    print("="*60)
    print(phase_bowling_df.to_string(index=False))
    
    # Top players
    logger.info("Getting player stats...")
    players_df = get_top_players_comparison()
    print("\n" + "="*60)
    print("Top Players (min 5 innings)")
    print("="*60)
    print(players_df.to_string(index=False))
    
    # Export CSVs
    export_path = Path(__file__).parent.parent.parent / "data" / "exports"
    export_path.mkdir(parents=True, exist_ok=True)
    
    win_rate_df.to_csv(export_path / "s1_vs_s2_win_rate.csv", index=False)
    phase_batting_df.to_csv(export_path / "s1_vs_s2_batting_phases.csv", index=False)
    phase_bowling_df.to_csv(export_path / "s1_vs_s2_bowling_phases.csv", index=False)
    players_df.to_csv(export_path / "s1_vs_s2_players.csv", index=False)
    
    logger.success(f"Exported to {export_path}")
    
    print("\n" + "="*60)
    print("Analysis complete!")
    print("="*60)
    print(f"Exports saved to: {export_path}")
    print("\nNext steps:")
    print("- Review CSV files in data/exports/")
    print("- Look for biggest S1 vs S2 gaps")
    print("- Check player retention impact")
    

if __name__ == "__main__":
    generate_diagnosis_report()
