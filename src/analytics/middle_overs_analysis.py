"""
Middle Overs Analysis
====================

Research Question:
-----------------
If death batting IMPROVED and death bowling needs re-validation, where is the real problem?

Hypothesis: Middle overs (7-15) are the weak link, not death overs (16-20).

Methodology:
-----------
Compare S1 vs S2 performance in overs 7-15 for:
1. **JAB Batting** (run rate, wickets lost, boundaries)
2. **JAB Bowling** (economy, wickets taken, dot %)

If middle overs declined in both batting AND bowling, this explains:
- Why JAB couldn't close out games early in S2
- Why both teams ended up batting full 20 overs more often in S2
- Why death phase metrics looked bad in naive analysis (survivorship bias)

Expected Finding:
----------------
S1: Dominated middle overs → closed games early (rarely needed death overs)
S2: Lost middle overs control → forced into death phase (where they actually performed OK)
"""

import pandas as pd
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns

# Initialize
from src.utils.logging_config import get_logger
logger = get_logger(__name__)

try:
    from src.config.paths import NORMALIZED_DIR, EXPORT_DIR
except ImportError:
    NORMALIZED_DIR = Path(__file__).resolve().parent.parent / "data" / "normalized"
    EXPORT_DIR = Path(__file__).resolve().parent.parent / "data" / "exports"

EXPORT_DIR.mkdir(parents=True, exist_ok=True)

# ══════════════════════════════════════════════════════════════════════════
# LOAD DATA
# ══════════════════════════════════════════════════════════════════════════

def load_ball_by_ball():
    """Load normalized ball-by-ball data."""
    bbb = pd.read_parquet(NORMALIZED_DIR / "ball_by_ball_normalized.parquet")
    return bbb


# ══════════════════════════════════════════════════════════════════════════
# MIDDLE OVERS BATTING ANALYSIS
# ══════════════════════════════════════════════════════════════════════════

def analyze_middle_overs_batting(bbb, team="Janakpur Bolts", middle_start=7, middle_end=15):
    """
    Analyze JAB's batting performance in middle overs (7-15).
    """
    logger.info("\n" + "="*80)
    logger.info(f"MIDDLE OVERS BATTING ANALYSIS (Overs {middle_start}-{middle_end})")
    logger.info("="*80)
    
    # Load match data for season mapping
    matches = pd.read_parquet(NORMALIZED_DIR / "matches_normalized.parquet")
    
    # Merge season info
    bbb_with_season = bbb.merge(
        matches[['match_id', 'season']],
        on='match_id',
        how='left'
    )
    
    # Filter: JAB batting in middle overs
    jab_middle_batting = bbb_with_season[
        (bbb_with_season['batting_team'] == team) &
        (bbb_with_season['over'] >= middle_start) &
        (bbb_with_season['over'] <= middle_end)
    ]
    
    logger.info(f"\n{team} - Middle Overs Batting Performance:")
    logger.info("-"*80)
    
    season_stats = []
    
    for season in ['S1', 'S2']:
        season_data = jab_middle_batting[jab_middle_batting['season'] == season]
        
        if len(season_data) == 0:
            logger.info(f"\n{season}: No middle overs batting data")
            continue
        
        total_runs = season_data['runs_off_bat'].sum()
        total_balls = len(season_data)
        total_overs = total_balls / 6
        
        run_rate = total_runs / total_overs if total_overs > 0 else 0
        strike_rate = (total_runs / total_balls * 100) if total_balls > 0 else 0
        
        boundaries = season_data['is_boundary'].sum()
        boundary_rate = (boundaries / total_balls * 100) if total_balls > 0 else 0
        
        dots = season_data['is_dot_ball'].sum()
        dot_pct = (dots / total_balls * 100) if total_balls > 0 else 0
        
        wickets_lost = season_data['is_wicket'].sum()
        
        # Count unique innings
        innings_count = season_data.groupby(['match_id', 'innings']).ngroups
        
        logger.info(f"\n{season}:")
        logger.info(f"  Innings: {innings_count}")
        logger.info(f"  Total runs: {total_runs} in {total_overs:.1f} overs ({total_balls} balls)")
        logger.info(f"  Run rate: {run_rate:.2f} runs/over")
        logger.info(f"  Strike rate: {strike_rate:.1f}")
        logger.info(f"  Boundaries: {boundaries} ({boundary_rate:.1f}% of balls)")
        logger.info(f"  Dot ball %: {dot_pct:.1f}%")
        logger.info(f"  Wickets lost: {wickets_lost} ({wickets_lost/innings_count:.2f} per innings)")
        
        season_stats.append({
            'season': season,
            'innings': innings_count,
            'total_runs': total_runs,
            'total_overs': total_overs,
            'run_rate': run_rate,
            'strike_rate': strike_rate,
            'boundaries': boundaries,
            'boundary_rate': boundary_rate,
            'dot_pct': dot_pct,
            'wickets_lost': wickets_lost,
            'wickets_per_innings': wickets_lost / innings_count if innings_count > 0 else 0
        })
    
    stats_df = pd.DataFrame(season_stats)
    
    # Delta analysis
    if len(stats_df) == 2:
        s1 = stats_df[stats_df['season'] == 'S1'].iloc[0]
        s2 = stats_df[stats_df['season'] == 'S2'].iloc[0]
        
        logger.info(f"\n{'='*80}")
        logger.info("MIDDLE OVERS BATTING DELTA (S1 → S2):")
        logger.info("-"*80)
        logger.info(f"  Run rate: {s1['run_rate']:.2f} → {s2['run_rate']:.2f} "
                   f"({s2['run_rate'] - s1['run_rate']:+.2f} runs/over)")
        logger.info(f"  Strike rate: {s1['strike_rate']:.1f} → {s2['strike_rate']:.1f} "
                   f"({s2['strike_rate'] - s1['strike_rate']:+.1f})")
        logger.info(f"  Boundaries/over: {s1['boundaries']/s1['total_overs']:.2f} → "
                   f"{s2['boundaries']/s2['total_overs']:.2f} "
                   f"({s2['boundaries']/s2['total_overs'] - s1['boundaries']/s1['total_overs']:+.2f})")
        logger.info(f"  Dot ball %: {s1['dot_pct']:.1f}% → {s2['dot_pct']:.1f}% "
                   f"({s2['dot_pct'] - s1['dot_pct']:+.1f}pp)")
        logger.info(f"  Wickets/innings: {s1['wickets_per_innings']:.2f} → {s2['wickets_per_innings']:.2f} "
                   f"({s2['wickets_per_innings'] - s1['wickets_per_innings']:+.2f})")
        
        # Diagnosis
        logger.info(f"\n💡 BATTING DIAGNOSIS:")
        
        run_rate_delta = s2['run_rate'] - s1['run_rate']
        wickets_delta = s2['wickets_per_innings'] - s1['wickets_per_innings']
        
        if run_rate_delta < -0.75:
            logger.info(f"  🔴 MIDDLE-OVERS BATTING DECLINE: {abs(run_rate_delta):.2f} runs/over drop")
            if wickets_delta > 0.5:
                logger.info(f"     + {wickets_delta:.2f} more wickets/innings → COLLAPSE pattern")
            else:
                logger.info(f"     Wickets stable → Scoring rate is the issue")
        elif run_rate_delta < -0.3:
            logger.info(f"  🟡 MODERATE BATTING DECLINE: {abs(run_rate_delta):.2f} runs/over drop")
        else:
            logger.info(f"  ✅ BATTING STABLE OR IMPROVED in middle overs")
    
    return stats_df


# ══════════════════════════════════════════════════════════════════════════
# MIDDLE OVERS BOWLING ANALYSIS
# ══════════════════════════════════════════════════════════════════════════

def analyze_middle_overs_bowling(bbb, team="Janakpur Bolts", middle_start=7, middle_end=15):
    """
    Analyze JAB's bowling performance in middle overs (7-15).
    """
    logger.info("\n" + "="*80)
    logger.info(f"MIDDLE OVERS BOWLING ANALYSIS (Overs {middle_start}-{middle_end})")
    logger.info("="*80)
    
    # Load match data for season mapping
    matches = pd.read_parquet(NORMALIZED_DIR / "matches_normalized.parquet")
    
    # Merge season info
    bbb_with_season = bbb.merge(
        matches[['match_id', 'season']],
        on='match_id',
        how='left'
    )
    
    # Filter: JAB bowling in middle overs
    jab_middle_bowling = bbb_with_season[
        (bbb_with_season['bowling_team'] == team) &
        (bbb_with_season['over'] >= middle_start) &
        (bbb_with_season['over'] <= middle_end)
    ]
    
    logger.info(f"\n{team} - Middle Overs Bowling Performance:")
    logger.info("-"*80)
    
    season_stats = []
    
    for season in ['S1', 'S2']:
        season_data = jab_middle_bowling[jab_middle_bowling['season'] == season]
        
        if len(season_data) == 0:
            logger.info(f"\n{season}: No middle overs bowling data")
            continue
        
        total_runs = season_data['runs_off_bat'].sum()
        extras = season_data[season_data['runs_off_bat'] == 0]['runs_total'].sum()
        total_runs_conceded = total_runs + extras
        
        total_balls = len(season_data)
        total_overs = total_balls / 6
        
        economy = total_runs_conceded / total_overs if total_overs > 0 else 0
        
        boundaries = season_data['is_boundary'].sum()
        boundary_rate = (boundaries / total_balls * 100) if total_balls > 0 else 0
        
        dots = season_data['is_dot_ball'].sum()
        dot_pct = (dots / total_balls * 100) if total_balls > 0 else 0
        
        wickets_taken = season_data['is_wicket'].sum()
        
        # Count unique opponent innings
        innings_count = season_data.groupby(['match_id', 'innings']).ngroups
        
        logger.info(f"\n{season}:")
        logger.info(f"  Opponent innings: {innings_count}")
        logger.info(f"  Runs conceded: {total_runs_conceded} in {total_overs:.1f} overs ({total_balls} balls)")
        logger.info(f"  Economy rate: {economy:.2f} runs/over")
        logger.info(f"  Boundaries conceded: {boundaries} ({boundary_rate:.1f}% of balls)")
        logger.info(f"  Dot ball %: {dot_pct:.1f}%")
        logger.info(f"  Wickets taken: {wickets_taken} ({wickets_taken/innings_count:.2f} per innings)")
        logger.info(f"  Strike rate: {total_balls/wickets_taken:.1f} balls/wicket" if wickets_taken > 0 else "  Strike rate: N/A (no wickets)")
        
        season_stats.append({
            'season': season,
            'innings': innings_count,
            'total_runs_conceded': total_runs_conceded,
            'total_overs': total_overs,
            'economy': economy,
            'boundaries_conceded': boundaries,
            'boundary_rate': boundary_rate,
            'dot_pct': dot_pct,
            'wickets_taken': wickets_taken,
            'wickets_per_innings': wickets_taken / innings_count if innings_count > 0 else 0,
            'bowling_strike_rate': total_balls / wickets_taken if wickets_taken > 0 else None
        })
    
    stats_df = pd.DataFrame(season_stats)
    
    # Delta analysis
    if len(stats_df) == 2:
        s1 = stats_df[stats_df['season'] == 'S1'].iloc[0]
        s2 = stats_df[stats_df['season'] == 'S2'].iloc[0]
        
        logger.info(f"\n{'='*80}")
        logger.info("MIDDLE OVERS BOWLING DELTA (S1 → S2):")
        logger.info("-"*80)
        logger.info(f"  Economy rate: {s1['economy']:.2f} → {s2['economy']:.2f} "
                   f"({s2['economy'] - s1['economy']:+.2f} runs/over)")
        logger.info(f"  Boundaries/over: {s1['boundaries_conceded']/s1['total_overs']:.2f} → "
                   f"{s2['boundaries_conceded']/s2['total_overs']:.2f} "
                   f"({s2['boundaries_conceded']/s2['total_overs'] - s1['boundaries_conceded']/s1['total_overs']:+.2f})")
        logger.info(f"  Dot ball %: {s1['dot_pct']:.1f}% → {s2['dot_pct']:.1f}% "
                   f"({s2['dot_pct'] - s1['dot_pct']:+.1f}pp)")
        logger.info(f"  Wickets/innings: {s1['wickets_per_innings']:.2f} → {s2['wickets_per_innings']:.2f} "
                   f"({s2['wickets_per_innings'] - s1['wickets_per_innings']:+.2f})")
        
        if s1['bowling_strike_rate'] and s2['bowling_strike_rate']:
            logger.info(f"  Bowling strike rate: {s1['bowling_strike_rate']:.1f} → {s2['bowling_strike_rate']:.1f} "
                       f"({s2['bowling_strike_rate'] - s1['bowling_strike_rate']:+.1f} balls/wicket)")
        
        # Diagnosis
        logger.info(f"\n💡 BOWLING DIAGNOSIS:")
        
        economy_delta = s2['economy'] - s1['economy']
        wickets_delta = s2['wickets_per_innings'] - s1['wickets_per_innings']
        
        if economy_delta > 0.75 or wickets_delta < -0.5:
            logger.info(f"  🔴 MIDDLE-OVERS BOWLING COLLAPSE")
            if economy_delta > 0.75:
                logger.info(f"     Economy worsened by {economy_delta:.2f} runs/over")
            if wickets_delta < -0.5:
                logger.info(f"     Wicket-taking dropped by {abs(wickets_delta):.2f} wickets/innings")
            logger.info(f"     → JAB couldn't control middle overs in S2")
        elif economy_delta > 0.3:
            logger.info(f"  🟡 MODERATE BOWLING DECLINE: {economy_delta:.2f} runs/over worse")
        else:
            logger.info(f"  ✅ BOWLING STABLE OR IMPROVED in middle overs")
    
    return stats_df


# ══════════════════════════════════════════════════════════════════════════
# INTEGRATED MIDDLE OVERS DIAGNOSIS
# ══════════════════════════════════════════════════════════════════════════

def integrated_middle_overs_diagnosis(batting_stats, bowling_stats):
    """
    Combine batting and bowling middle overs analysis.
    """
    logger.info("\n" + "="*80)
    logger.info("🎯 INTEGRATED DIAGNOSIS: Middle Overs Control")
    logger.info("="*80)
    
    if len(batting_stats) < 2 or len(bowling_stats) < 2:
        logger.info("\n⚠️ Insufficient data for integrated diagnosis")
        return
    
    s1_bat = batting_stats[batting_stats['season'] == 'S1'].iloc[0]
    s2_bat = batting_stats[batting_stats['season'] == 'S2'].iloc[0]
    
    s1_bowl = bowling_stats[bowling_stats['season'] == 'S1'].iloc[0]
    s2_bowl = bowling_stats[bowling_stats['season'] == 'S2'].iloc[0]
    
    bat_rate_delta = s2_bat['run_rate'] - s1_bat['run_rate']
    bowl_econ_delta = s2_bowl['economy'] - s1_bowl['economy']
    
    logger.info(f"\nMiddle Overs (7-15) Performance:")
    logger.info(f"  Batting run rate: {s1_bat['run_rate']:.2f} → {s2_bat['run_rate']:.2f} "
               f"(Δ = {bat_rate_delta:+.2f} runs/over)")
    logger.info(f"  Bowling economy: {s1_bowl['economy']:.2f} → {s2_bowl['economy']:.2f} "
               f"(Δ = {bowl_econ_delta:+.2f} runs/over)")
    
    # Net run rate in middle overs
    s1_net_rr = s1_bat['run_rate'] - s1_bowl['economy']
    s2_net_rr = s2_bat['run_rate'] - s2_bowl['economy']
    net_rr_delta = s2_net_rr - s1_net_rr
    
    logger.info(f"\n  Net run rate (batting - bowling):")
    logger.info(f"    S1: {s1_net_rr:+.2f} runs/over")
    logger.info(f"    S2: {s2_net_rr:+.2f} runs/over")
    logger.info(f"    Delta: {net_rr_delta:+.2f} runs/over")
    
    # Classification
    logger.info(f"\n{'='*80}")
    logger.info("ROOT CAUSE VERDICT:")
    logger.info("-"*80)
    
    if bat_rate_delta < -0.5 and bowl_econ_delta > 0.5:
        logger.info("  📊 COMPLETE MIDDLE-OVERS COLLAPSE (Batting + Bowling)")
        logger.info("     JAB lost control of overs 7-15 in BOTH batting and bowling")
        logger.info(f"     Net swing: {net_rr_delta:.2f} runs/over")
        logger.info("\n  💡 PRIMARY ROOT CAUSE: Middle overs (7-15), NOT death phase (16-20)")
        logger.info("     → S1 won by dominating middle overs, closing games early")
        logger.info("     → S2 lost middle-overs dominance, forced into full 20-over games")
        
    elif bat_rate_delta < -0.5:
        logger.info("  📊 MIDDLE-OVERS BATTING COLLAPSE")
        logger.info("     Batting declined, bowling stayed stable")
        logger.info("\n  💡 S3 Priority: Strengthen middle-order batters (positions 4-6)")
        
    elif bowl_econ_delta > 0.5:
        logger.info("  📊 MIDDLE-OVERS BOWLING COLLAPSE")
        logger.info("     Bowling declined, batting stayed stable")
        logger.info("\n  💡 S3 Priority: Strengthen middle-overs bowlers (overs 7-15)")
        
    else:
        logger.info("  📊 MIDDLE OVERS STABLE")
        logger.info("     No severe decline in overs 7-15")
        logger.info("\n  💡 Root cause may be elsewhere (captaincy, powerplay, death phase)")
    
    # Connection to two-tier findings
    logger.info(f"\n{'='*80}")
    logger.info("🔗 CONNECTION TO TWO-TIER FINDINGS:")
    logger.info("-"*80)
    logger.info("  Death batting two-tier showed: IMPROVED in S2 (when reaching death)")
    logger.info("  Death bowling two-tier: [PENDING VALIDATION]")
    logger.info("")
    logger.info("  If middle overs collapsed + death phase improved:")
    logger.info("    → S1 strategy: WIN IN MIDDLE OVERS (don't need death phase)")
    logger.info("    → S2 strategy: SURVIVE TO DEATH (but damage already done)")
    logger.info("")
    logger.info("  This explains survivorship bias in original phase analysis:")
    logger.info("    - S1 rarely reached death → small denominator → metrics look worse")
    logger.info("    - S2 always reached death → large denominator → metrics look better")
    logger.info("    - But conditional analysis reverses the narrative!")


# ══════════════════════════════════════════════════════════════════════════
# VISUALIZATION
# ══════════════════════════════════════════════════════════════════════════

def create_middle_overs_visualization(batting_stats, bowling_stats):
    """Visualize middle overs analysis."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    
    seasons = batting_stats['season'].values
    
    # Plot 1: Batting run rate
    bat_rates = batting_stats['run_rate'].values
    bars1 = ax1.bar(seasons, bat_rates, color=['#4CAF50', '#F44336'], alpha=0.7, edgecolor='black')
    ax1.set_ylabel('Run Rate (runs/over)', fontsize=12)
    ax1.set_title('Middle Overs Batting (7-15)', fontsize=14, fontweight='bold')
    ax1.set_ylim(0, max(bat_rates) * 1.3)
    ax1.grid(axis='y', alpha=0.3)
    
    for bar in bars1:
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.2f}',
                ha='center', va='bottom', fontsize=12, fontweight='bold')
    
    # Plot 2: Bowling economy
    bowl_econs = bowling_stats['economy'].values
    bars2 = ax2.bar(seasons, bowl_econs, color=['#4CAF50', '#F44336'], alpha=0.7, edgecolor='black')
    ax2.set_ylabel('Economy Rate (runs/over)', fontsize=12)
    ax2.set_title('Middle Overs Bowling (7-15)', fontsize=14, fontweight='bold')
    ax2.set_ylim(0, max(bowl_econs) * 1.3)
    ax2.grid(axis='y', alpha=0.3)
    
    for bar in bars2:
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.2f}',
                ha='center', va='bottom', fontsize=12, fontweight='bold')
    
    plt.tight_layout()
    output_path = EXPORT_DIR / "middle_overs_analysis.png"
    plt.savefig(output_path, dpi=150)
    logger.info(f"\n📊 Visualization saved: {output_path}")
    plt.close()


# ══════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════

def main():
    """Run middle overs analysis."""
    logger.info("\n" + "="*80)
    logger.info("MIDDLE OVERS ANALYSIS (Overs 7-15)")
    logger.info("="*80)
    logger.info("\nHypothesis: Real problem is middle overs, not death overs")
    
    bbb = load_ball_by_ball()
    
    # Batting in middle overs
    batting_stats = analyze_middle_overs_batting(bbb)
    
    # Bowling in middle overs
    bowling_stats = analyze_middle_overs_bowling(bbb)
    
    # Integrated diagnosis
    integrated_middle_overs_diagnosis(batting_stats, bowling_stats)
    
    # Visualization
    if len(batting_stats) >= 2 and len(bowling_stats) >= 2:
        create_middle_overs_visualization(batting_stats, bowling_stats)
    
    logger.info("\n" + "="*80)
    logger.info("ANALYSIS COMPLETE")
    logger.info("="*80)
    
    return {
        'batting': batting_stats,
        'bowling': bowling_stats
    }


if __name__ == "__main__":
    main()
