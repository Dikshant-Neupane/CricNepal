"""
Death Batting Two-Tier Analysis
================================

Separates "did we reach death overs?" from "how did we perform in death overs?"

Research Question:
-----------------
Is the death batting decline due to:
1. Early/middle-order collapse (fewer innings reaching overs 16-20)?
2. Death-phase execution failure (poor scoring when we DID reach overs 16-20)?

Methodology:
-----------
**Tier 1:** Innings Completion Rate
    - What % of innings reached over 16 (death phase start)?
    - S1 vs S2 comparison

**Tier 2:** Death Phase Run Rate (Conditional on Reaching)
    - For innings that DID reach over 16, what was the run rate in overs 16-20?
    - S1 vs S2 comparison
    - Only computed on innings that actually entered death phase

**Why Two Tiers Matter:**
- If Tier 1 drops (S1: 90% → S2: 60%), problem is MIDDLE-ORDER COLLAPSE
- If Tier 1 stable but Tier 2 drops, problem is DEATH BATTING EXECUTION
- If both drop, it's a COMPOUND FAILURE (collapse earlier + score slower when reaching)
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
# TIER 1: INNINGS COMPLETION ANALYSIS
# ══════════════════════════════════════════════════════════════════════════

def analyze_innings_completion(bbb, team="Janakpur Bolts", death_phase_start=16):
    """
    Tier 1: Did the team reach death overs?
    
    Returns:
        - % of innings reaching over 16
        - Average final over reached
        - All-out rate (innings ending before over 20)
    """
    logger.info("\n" + "="*80)
    logger.info("TIER 1: INNINGS COMPLETION ANALYSIS")
    logger.info("="*80)
    
    # Load match data for season mapping
    matches = pd.read_parquet(NORMALIZED_DIR / "matches_normalized.parquet")
    
    # Merge season info into bbb
    bbb_with_season = bbb.merge(
        matches[['match_id', 'season']],
        on='match_id',
        how='left'
    )
    
    # Filter team batting
    team_batting = bbb_with_season[bbb_with_season['batting_team'] == team]
    
    # Group by season, match_id, innings to get innings-level stats
    innings_stats = team_batting.groupby(['season', 'match_id', 'innings']).agg({
        'over': 'max',  # Last over faced
        'is_wicket': 'sum',  # Total wickets lost
        'runs_total': 'sum'  # Total runs scored
    }).reset_index()
    
    innings_stats.rename(columns={'over': 'final_over'}, inplace=True)
    
    # Flag: Did innings reach death phase?
    innings_stats['reached_death'] = innings_stats['final_over'] >= death_phase_start
    innings_stats['all_out'] = innings_stats['is_wicket'] >= 10  # All out (10 wickets)
    
    # Analysis by season
    logger.info(f"\n{team} - Innings Completion by Season:")
    logger.info("-"*80)
    
    season_summary = []
    
    for season in ['S1', 'S2']:
        season_innings = innings_stats[innings_stats['season'] == season]
        
        total_innings = len(season_innings)
        reached_death = season_innings['reached_death'].sum()
        reached_death_pct = (reached_death / total_innings * 100) if total_innings > 0 else 0
        
        avg_final_over = season_innings['final_over'].mean()
        
        all_out_count = season_innings['all_out'].sum()
        all_out_pct = (all_out_count / total_innings * 100) if total_innings > 0 else 0
        
        logger.info(f"\n{season}:")
        logger.info(f"  Total innings: {total_innings}")
        logger.info(f"  Reached death (over {death_phase_start}+): {reached_death}/{total_innings} ({reached_death_pct:.1f}%)")
        logger.info(f"  Average final over: {avg_final_over:.1f}")
        logger.info(f"  All out before over 20: {all_out_count}/{total_innings} ({all_out_pct:.1f}%)")
        
        season_summary.append({
            'season': season,
            'total_innings': total_innings,
            'reached_death': reached_death,
            'reached_death_pct': reached_death_pct,
            'avg_final_over': avg_final_over,
            'all_out_count': all_out_count,
            'all_out_pct': all_out_pct
        })
    
    summary_df = pd.DataFrame(season_summary)
    
    # Delta analysis
    if len(summary_df) == 2:
        s1 = summary_df[summary_df['season'] == 'S1'].iloc[0]
        s2 = summary_df[summary_df['season'] == 'S2'].iloc[0]
        
        logger.info(f"\n{'='*80}")
        logger.info("TIER 1 DELTA (S1 → S2):")
        logger.info("-"*80)
        logger.info(f"  Death phase reach rate: {s1['reached_death_pct']:.1f}% → {s2['reached_death_pct']:.1f}% "
                   f"({s2['reached_death_pct'] - s1['reached_death_pct']:+.1f}pp)")
        logger.info(f"  Average final over: {s1['avg_final_over']:.1f} → {s2['avg_final_over']:.1f} "
                   f"({s2['avg_final_over'] - s1['avg_final_over']:+.1f} overs)")
        logger.info(f"  All-out rate: {s1['all_out_pct']:.1f}% → {s2['all_out_pct']:.1f}% "
                   f"({s2['all_out_pct'] - s1['all_out_pct']:+.1f}pp)")
        
        # Diagnosis
        logger.info(f"\n💡 TIER 1 DIAGNOSIS:")
        
        if (s2['reached_death_pct'] - s1['reached_death_pct']) < -10:
            logger.info(f"  🔴 EARLY COLLAPSE PROBLEM: Death phase reach rate dropped by "
                       f"{s1['reached_death_pct'] - s2['reached_death_pct']:.0f}pp")
            logger.info(f"     → Middle-order failure is primary issue")
        elif (s2['reached_death_pct'] - s1['reached_death_pct']) < -5:
            logger.info(f"  🟡 MODERATE COLLAPSE: Slightly fewer innings reaching death")
        else:
            logger.info(f"  ✅ INNINGS COMPLETION STABLE: Most innings still reaching death phase")
            logger.info(f"     → Problem is death-phase EXECUTION, not early collapse")
    
    return summary_df, innings_stats


# ══════════════════════════════════════════════════════════════════════════
# TIER 2: DEATH PHASE PERFORMANCE (CONDITIONAL)
# ══════════════════════════════════════════════════════════════════════════

def analyze_death_phase_performance(bbb, team="Janakpur Bolts", death_phase_start=16):
    """
    Tier 2: For innings that REACHED death phase, how did they perform?
    
    Only analyzes deliveries in overs 16-20 for innings that actually got there.
    """
    logger.info("\n" + "="*80)
    logger.info("TIER 2: DEATH PHASE PERFORMANCE (Conditional on Reaching)")
    logger.info("="*80)
    
    # Load match data for season mapping
    matches = pd.read_parquet(NORMALIZED_DIR / "matches_normalized.parquet")
    
    # Merge season info
    bbb_with_season = bbb.merge(
        matches[['match_id', 'season']],
        on='match_id',
        how='left'
    )
    
    # Filter team batting
    team_batting = bbb_with_season[bbb_with_season['batting_team'] == team]
    
    # Identify innings that reached death phase
    innings_max_over = team_batting.groupby(['season', 'match_id', 'innings'])['over'].max().reset_index()
    innings_max_over.rename(columns={'over': 'final_over'}, inplace=True)
    
    death_innings = innings_max_over[innings_max_over['final_over'] >= death_phase_start][
        ['season', 'match_id', 'innings']
    ]
    
    # Merge to filter only death-reaching innings
    team_batting_death_qualified = team_batting.merge(
        death_innings,
        on=['season', 'match_id', 'innings'],
        how='inner'
    )
    
    # Filter to death phase overs only
    death_balls = team_batting_death_qualified[
        team_batting_death_qualified['over'] >= death_phase_start
    ]
    
    logger.info(f"\n{team} - Death Phase Performance (Overs {death_phase_start}-20):")
    logger.info("-"*80)
    logger.info("Note: Only includes innings that actually reached over 16")
    
    season_death_stats = []
    
    for season in ['S1', 'S2']:
        season_death = death_balls[death_balls['season'] == season]
        
        if len(season_death) == 0:
            logger.info(f"\n{season}: No death phase data (no innings reached over {death_phase_start})")
            continue
        
        total_runs = season_death['runs_off_bat'].sum()
        total_balls = len(season_death)
        total_overs = total_balls / 6
        
        run_rate = total_runs / total_overs if total_overs > 0 else 0
        
        boundaries = season_death['is_boundary'].sum()
        dots = season_death['is_dot_ball'].sum()
        dot_pct = (dots / total_balls * 100) if total_balls > 0 else 0
        
        wickets_lost = season_death['is_wicket'].sum()
        
        innings_count = death_innings[death_innings['season'] == season].shape[0]
        
        logger.info(f"\n{season}:")
        logger.info(f"  Innings reaching death: {innings_count}")
        logger.info(f"  Total runs: {total_runs} in {total_overs:.1f} overs ({total_balls} balls)")
        logger.info(f"  Run rate: {run_rate:.2f} runs/over")
        logger.info(f"  Boundaries: {boundaries} ({boundaries/innings_count:.1f} per innings)")
        logger.info(f"  Dot ball %: {dot_pct:.1f}%")
        logger.info(f"  Wickets lost: {wickets_lost} ({wickets_lost/innings_count:.1f} per innings)")
        
        season_death_stats.append({
            'season': season,
            'innings_reaching_death': innings_count,
            'total_runs': total_runs,
            'total_overs': total_overs,
            'run_rate': run_rate,
            'boundaries': boundaries,
            'dot_pct': dot_pct,
            'wickets_lost': wickets_lost
        })
    
    stats_df = pd.DataFrame(season_death_stats)
    
    # Delta analysis
    if len(stats_df) == 2:
        s1 = stats_df[stats_df['season'] == 'S1'].iloc[0]
        s2 = stats_df[stats_df['season'] == 'S2'].iloc[0]
        
        logger.info(f"\n{'='*80}")
        logger.info("TIER 2 DELTA (S1 → S2):")
        logger.info("-"*80)
        logger.info(f"  Run rate: {s1['run_rate']:.2f} → {s2['run_rate']:.2f} "
                   f"({s2['run_rate'] - s1['run_rate']:+.2f} runs/over)")
        logger.info(f"  Boundaries/innings: {s1['boundaries']/s1['innings_reaching_death']:.1f} → "
                   f"{s2['boundaries']/s2['innings_reaching_death']:.1f} "
                   f"({s2['boundaries']/s2['innings_reaching_death'] - s1['boundaries']/s1['innings_reaching_death']:+.1f})")
        logger.info(f"  Dot ball %: {s1['dot_pct']:.1f}% → {s2['dot_pct']:.1f}% "
                   f"({s2['dot_pct'] - s1['dot_pct']:+.1f}pp)")
        
        # Diagnosis
        logger.info(f"\n💡 TIER 2 DIAGNOSIS:")
        
        run_rate_delta = s2['run_rate'] - s1['run_rate']
        
        if run_rate_delta < -1.5:
            logger.info(f"  🔴 SEVERE DEATH BATTING DECLINE: {abs(run_rate_delta):.2f} runs/over drop")
            logger.info(f"     → Death phase execution is a MAJOR problem")
        elif run_rate_delta < -0.5:
            logger.info(f"  🟡 MODERATE DEATH BATTING DECLINE: {abs(run_rate_delta):.2f} runs/over drop")
        else:
            logger.info(f"  ✅ DEATH BATTING STABLE: Run rate maintained when reaching death")
    
    return stats_df


# ══════════════════════════════════════════════════════════════════════════
# INTEGRATED DIAGNOSIS
# ══════════════════════════════════════════════════════════════════════════

def integrated_diagnosis(tier1_summary, tier2_stats):
    """
    Combine Tier 1 and Tier 2 to give overall diagnosis.
    """
    logger.info("\n" + "="*80)
    logger.info("🎯 INTEGRATED DIAGNOSIS: Death Phase Failure Root Cause")
    logger.info("="*80)
    
    if len(tier1_summary) < 2 or len(tier2_stats) < 2:
        logger.info("\n⚠️ Insufficient data for integrated diagnosis")
        return
    
    s1_tier1 = tier1_summary[tier1_summary['season'] == 'S1'].iloc[0]
    s2_tier1 = tier1_summary[tier1_summary['season'] == 'S2'].iloc[0]
    
    s1_tier2 = tier2_stats[tier2_stats['season'] == 'S1'].iloc[0]
    s2_tier2 = tier2_stats[tier2_stats['season'] == 'S2'].iloc[0]
    
    reach_rate_drop = s1_tier1['reached_death_pct'] - s2_tier1['reached_death_pct']
    run_rate_drop = s1_tier2['run_rate'] - s2_tier2['run_rate']
    
    logger.info(f"\nKey Metrics:")
    logger.info(f"  Tier 1 (Reach Rate): {s1_tier1['reached_death_pct']:.0f}% → {s2_tier1['reached_death_pct']:.0f}% "
               f"(Δ = {-reach_rate_drop:+.0f}pp)")
    logger.info(f"  Tier 2 (Run Rate): {s1_tier2['run_rate']:.2f} → {s2_tier2['run_rate']:.2f} "
               f"(Δ = {-run_rate_drop:+.2f} runs/over)")
    
    # Classification matrix
    logger.info(f"\n{'='*80}")
    logger.info("ROOT CAUSE CLASSIFICATION:")
    logger.info("-"*80)
    
    if reach_rate_drop > 10 and run_rate_drop > 1.0:
        logger.info("  📊 COMPOUND FAILURE (Both tiers declined)")
        logger.info("     1. Early/middle-order collapse → Fewer innings reaching death")
        logger.info("     2. Poor death-phase execution → Lower scoring when reaching")
        logger.info("\n  💡 S3 Priority: FIX BOTH middle-order stability AND death batting")
        
    elif reach_rate_drop > 10:
        logger.info("  📊 PRIMARY CAUSE: EARLY/MIDDLE-ORDER COLLAPSE")
        logger.info("     Death phase performance was OK when reached, but too few innings got there")
        logger.info("\n  💡 S3 Priority: Strengthen TOP/MIDDLE order, not death specialists")
        
    elif run_rate_drop > 1.0:
        logger.info("  📊 PRIMARY CAUSE: DEATH BATTING EXECUTION")
        logger.info("     Reached death overs consistently, but scored poorly in overs 16-20")
        logger.info("\n  💡 S3 Priority: Recruit death-over specialists (finishers)")
        
    else:
        logger.info("  📊 MILD DECLINE ACROSS BOTH TIERS")
        logger.info("     Neither early collapse nor death execution showed severe deterioration")
        logger.info("\n  💡 May be regression to mean or other factors (captaincy, opposition)")
    
    # Sample size caveat
    logger.info(f"\n⚠️  SAMPLE SIZE CAVEAT:")
    logger.info(f"   S1 death innings: n={s1_tier2['innings_reaching_death']}")
    logger.info(f"   S2 death innings: n={s2_tier2['innings_reaching_death']}")
    logger.info(f"   Small samples (n<10) limit confidence in conclusions")


# ══════════════════════════════════════════════════════════════════════════
# VISUALIZATION
# ══════════════════════════════════════════════════════════════════════════

def create_two_tier_visualization(tier1_summary, tier2_stats):
    """Visualize two-tier analysis."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    
    # Plot 1: Tier 1 - Innings Completion
    seasons = tier1_summary['season'].values
    reach_rates = tier1_summary['reached_death_pct'].values
    
    bars1 = ax1.bar(seasons, reach_rates, color=['#4CAF50', '#F44336'], alpha=0.7, edgecolor='black')
    ax1.set_ylabel('% of Innings Reaching Death Phase', fontsize=12)
    ax1.set_title('Tier 1: Did We Reach Death Overs?', fontsize=14, fontweight='bold')
    ax1.set_ylim(0, 100)
    ax1.grid(axis='y', alpha=0.3)
    
    for bar in bars1:
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.0f}%',
                ha='center', va='bottom', fontsize=12, fontweight='bold')
    
    # Plot 2: Tier 2 - Death Phase Run Rate
    run_rates = tier2_stats['run_rate'].values
    
    bars2 = ax2.bar(seasons, run_rates, color=['#4CAF50', '#F44336'], alpha=0.7, edgecolor='black')
    ax2.set_ylabel('Run Rate (runs/over)', fontsize=12)
    ax2.set_title('Tier 2: Death Phase Scoring (When Reached)', fontsize=14, fontweight='bold')
    ax2.set_ylim(0, max(run_rates) * 1.3)
    ax2.grid(axis='y', alpha=0.3)
    
    for bar in bars2:
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.2f}',
                ha='center', va='bottom', fontsize=12, fontweight='bold')
    
    plt.tight_layout()
    output_path = EXPORT_DIR / "death_batting_two_tier_analysis.png"
    plt.savefig(output_path, dpi=150)
    logger.info(f"\n📊 Visualization saved: {output_path}")
    plt.close()


# ══════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════

def main():
    """Run two-tier death batting analysis."""
    logger.info("\n" + "="*80)
    logger.info("DEATH BATTING TWO-TIER ANALYSIS")
    logger.info("="*80)
    logger.info("\nSeparating 'reaching death overs' from 'death phase execution'")
    
    bbb = load_ball_by_ball()
    
    # Tier 1: Innings completion
    tier1_summary, innings_stats = analyze_innings_completion(bbb)
    
    # Tier 2: Death phase performance (conditional)
    tier2_stats = analyze_death_phase_performance(bbb)
    
    # Integrated diagnosis
    integrated_diagnosis(tier1_summary, tier2_stats)
    
    # Visualization
    if len(tier1_summary) >= 2 and len(tier2_stats) >= 2:
        create_two_tier_visualization(tier1_summary, tier2_stats)
    
    logger.info("\n" + "="*80)
    logger.info("ANALYSIS COMPLETE")
    logger.info("="*80)
    
    return {
        'tier1': tier1_summary,
        'tier2': tier2_stats,
        'innings_details': innings_stats
    }


if __name__ == "__main__":
    main()
