"""
Death Bowling Two-Tier Analysis
================================

Separates "did opponents reach death overs?" from "how much did they score in death overs?"

Research Question:
-----------------
Is the death bowling decline due to:
1. Opponents collapsing earlier in S1 (fewer innings reaching death)?
2. Genuine death bowling execution failure (worse economy when opponents DID reach death)?

Methodology:
-----------
**Tier 1:** Opposition Innings Completion Rate
    - What % of opponent innings reached over 16 (death phase start)?
    - S1 vs S2 comparison
    - If S1 had more early bowling collapses, fewer opponents reached death

**Tier 2:** Death Bowling Economy (Conditional on Opponents Reaching)
    - For opponent innings that DID reach over 16, what was JAB's economy in overs 16-20?
    - S1 vs S2 comparison
    - Only computed on innings that actually entered death phase

**Why Two Tiers Matter:**
- If Tier 1: S1 opponents 50% reach death → S2 opponents 90% reach death, 
  JAB BOWLING got weaker in middle overs (couldn't bowl teams out early)
- If Tier 1 stable but Tier 2 economy worsens, it's DEATH BOWLING execution
- If both worsen, it's a COMPOUND FAILURE

**Survivorship Bias Note:**
- Naive calculation (total runs in death / total death overs across all matches)
  conflates reach rate with economy
- Two-tier separates these effects
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
# TIER 1: OPPOSITION INNINGS COMPLETION ANALYSIS
# ══════════════════════════════════════════════════════════════════════════

def analyze_opposition_innings_completion(bbb, team="Janakpur Bolts", death_phase_start=16):
    """
    Tier 1: Did opponents reach death overs against JAB's bowling?
    
    Returns:
        - % of opponent innings reaching over 16
        - Average final over opponent reached
        - All-out rate (JAB bowled them out before over 20)
    """
    logger.info("\n" + "="*80)
    logger.info("TIER 1: OPPOSITION INNINGS COMPLETION ANALYSIS")
    logger.info("="*80)
    logger.info("(How often did opponents reach death overs against JAB's bowling?)")
    
    # Load match data for season mapping
    matches = pd.read_parquet(NORMALIZED_DIR / "matches_normalized.parquet")
    
    # Merge season info into bbb
    bbb_with_season = bbb.merge(
        matches[['match_id', 'season']],
        on='match_id',
        how='left'
    )
    
    # Filter: Opponents batting (JAB bowling)
    opp_batting = bbb_with_season[bbb_with_season['bowling_team'] == team]
    
    # Group by season, match_id, innings to get innings-level stats
    opp_innings_stats = opp_batting.groupby(['season', 'match_id', 'innings']).agg({
        'over': 'max',  # Last over opponent faced
        'is_wicket': 'sum',  # Total wickets lost by opponent
        'runs_total': 'sum'  # Total runs scored by opponent
    }).reset_index()
    
    opp_innings_stats.rename(columns={'over': 'final_over'}, inplace=True)
    
    # Flag: Did opponent innings reach death phase?
    opp_innings_stats['reached_death'] = opp_innings_stats['final_over'] >= death_phase_start
    opp_innings_stats['all_out'] = opp_innings_stats['is_wicket'] >= 10  # JAB bowled them all out
    
    # Analysis by season
    logger.info(f"\nOpponents vs {team} - Innings Completion by Season:")
    logger.info("-"*80)
    
    season_summary = []
    
    for season in ['S1', 'S2']:
        season_innings = opp_innings_stats[opp_innings_stats['season'] == season]
        
        total_innings = len(season_innings)
        reached_death = season_innings['reached_death'].sum()
        reached_death_pct = (reached_death / total_innings * 100) if total_innings > 0 else 0
        
        avg_final_over = season_innings['final_over'].mean()
        
        all_out_count = season_innings['all_out'].sum()
        all_out_pct = (all_out_count / total_innings * 100) if total_innings > 0 else 0
        
        logger.info(f"\n{season}:")
        logger.info(f"  Opponent innings: {total_innings}")
        logger.info(f"  Reached death (over {death_phase_start}+): {reached_death}/{total_innings} ({reached_death_pct:.1f}%)")
        logger.info(f"  Average final over: {avg_final_over:.1f}")
        logger.info(f"  JAB bowled them all out before over 20: {all_out_count}/{total_innings} ({all_out_pct:.1f}%)")
        
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
        logger.info(f"  Opponent death phase reach rate: {s1['reached_death_pct']:.1f}% → {s2['reached_death_pct']:.1f}% "
                   f"({s2['reached_death_pct'] - s1['reached_death_pct']:+.1f}pp)")
        logger.info(f"  Opponent average final over: {s1['avg_final_over']:.1f} → {s2['avg_final_over']:.1f} "
                   f"({s2['avg_final_over'] - s1['avg_final_over']:+.1f} overs)")
        logger.info(f"  JAB all-out rate: {s1['all_out_pct']:.1f}% → {s2['all_out_pct']:.1f}% "
                   f"({s2['all_out_pct'] - s1['all_out_pct']:+.1f}pp)")
        
        # Diagnosis
        logger.info(f"\n💡 TIER 1 DIAGNOSIS:")
        
        reach_delta = s2['reached_death_pct'] - s1['reached_death_pct']
        
        if reach_delta > 15:
            logger.info(f"  🔴 MIDDLE-OVERS BOWLING COLLAPSE: Opponent reach rate jumped {reach_delta:.0f}pp")
            logger.info(f"     → JAB couldn't bowl teams out early in S2")
            logger.info(f"     → Problem is MIDDLE OVERS (7-15), not death bowling")
        elif reach_delta > 5:
            logger.info(f"  🟡 MODERATE BOWLING DECLINE: More opponents reaching death")
            logger.info(f"     → Reduced ability to take early wickets")
        else:
            logger.info(f"  ✅ EARLY WICKET-TAKING STABLE: Similar % reaching death")
            logger.info(f"     → If death economy worsened, it's death bowling execution")
    
    return summary_df, opp_innings_stats


# ══════════════════════════════════════════════════════════════════════════
# TIER 2: DEATH BOWLING ECONOMY (CONDITIONAL)
# ══════════════════════════════════════════════════════════════════════════

def analyze_death_bowling_performance(bbb, team="Janakpur Bolts", death_phase_start=16):
    """
    Tier 2: For opponent innings that REACHED death phase, what was JAB's economy?
    
    Only analyzes deliveries in overs 16-20 for innings that actually got there.
    """
    logger.info("\n" + "="*80)
    logger.info("TIER 2: DEATH BOWLING ECONOMY (Conditional on Opponents Reaching)")
    logger.info("="*80)
    
    # Load match data for season mapping
    matches = pd.read_parquet(NORMALIZED_DIR / "matches_normalized.parquet")
    
    # Merge season info
    bbb_with_season = bbb.merge(
        matches[['match_id', 'season']],
        on='match_id',
        how='left'
    )
    
    # Filter: Opponents batting (JAB bowling)
    opp_batting = bbb_with_season[bbb_with_season['bowling_team'] == team]
    
    # Identify opponent innings that reached death phase
    opp_innings_max_over = opp_batting.groupby(['season', 'match_id', 'innings'])['over'].max().reset_index()
    opp_innings_max_over.rename(columns={'over': 'final_over'}, inplace=True)
    
    death_innings = opp_innings_max_over[opp_innings_max_over['final_over'] >= death_phase_start][
        ['season', 'match_id', 'innings']
    ]
    
    # Merge to filter only death-reaching innings
    opp_batting_death_qualified = opp_batting.merge(
        death_innings,
        on=['season', 'match_id', 'innings'],
        how='inner'
    )
    
    # Filter to death phase overs only
    death_bowling = opp_batting_death_qualified[
        opp_batting_death_qualified['over'] >= death_phase_start
    ]
    
    logger.info(f"\nOpponents vs {team} - Death Phase Performance (Overs {death_phase_start}-20):")
    logger.info("-"*80)
    logger.info("Note: Only includes opponent innings that actually reached over 16")
    
    season_death_stats = []
    
    for season in ['S1', 'S2']:
        season_death = death_bowling[death_bowling['season'] == season]
        
        if len(season_death) == 0:
            logger.info(f"\n{season}: No death phase data (no opponent innings reached over {death_phase_start})")
            continue
        
        total_runs = season_death['runs_off_bat'].sum()
        extras = season_death[season_death['runs_off_bat'] == 0]['runs_total'].sum()  # Extras
        total_runs_conceded = total_runs + extras
        
        total_balls = len(season_death)
        total_overs = total_balls / 6
        
        economy = total_runs_conceded / total_overs if total_overs > 0 else 0
        
        boundaries = season_death['is_boundary'].sum()
        dots = season_death['is_dot_ball'].sum()
        dot_pct = (dots / total_balls * 100) if total_balls > 0 else 0
        
        wickets_taken = season_death['is_wicket'].sum()
        
        innings_count = death_innings[death_innings['season'] == season].shape[0]
        
        logger.info(f"\n{season}:")
        logger.info(f"  Opponent innings reaching death: {innings_count}")
        logger.info(f"  Runs conceded: {total_runs_conceded} in {total_overs:.1f} overs ({total_balls} balls)")
        logger.info(f"  Economy rate: {economy:.2f} runs/over")
        logger.info(f"  Boundaries conceded: {boundaries} ({boundaries/innings_count:.1f} per innings)")
        logger.info(f"  Dot ball %: {dot_pct:.1f}%")
        logger.info(f"  Wickets taken: {wickets_taken} ({wickets_taken/innings_count:.1f} per innings)")
        
        season_death_stats.append({
            'season': season,
            'innings_reaching_death': innings_count,
            'total_runs_conceded': total_runs_conceded,
            'total_overs': total_overs,
            'economy': economy,
            'boundaries_conceded': boundaries,
            'dot_pct': dot_pct,
            'wickets_taken': wickets_taken
        })
    
    stats_df = pd.DataFrame(season_death_stats)
    
    # Delta analysis
    if len(stats_df) == 2:
        s1 = stats_df[stats_df['season'] == 'S1'].iloc[0]
        s2 = stats_df[stats_df['season'] == 'S2'].iloc[0]
        
        logger.info(f"\n{'='*80}")
        logger.info("TIER 2 DELTA (S1 → S2):")
        logger.info("-"*80)
        logger.info(f"  Economy rate: {s1['economy']:.2f} → {s2['economy']:.2f} "
                   f"({s2['economy'] - s1['economy']:+.2f} runs/over)")
        logger.info(f"  Boundaries/innings: {s1['boundaries_conceded']/s1['innings_reaching_death']:.1f} → "
                   f"{s2['boundaries_conceded']/s2['innings_reaching_death']:.1f} "
                   f"({s2['boundaries_conceded']/s2['innings_reaching_death'] - s1['boundaries_conceded']/s1['innings_reaching_death']:+.1f})")
        logger.info(f"  Dot ball %: {s1['dot_pct']:.1f}% → {s2['dot_pct']:.1f}% "
                   f"({s2['dot_pct'] - s1['dot_pct']:+.1f}pp)")
        logger.info(f"  Wickets/innings: {s1['wickets_taken']/s1['innings_reaching_death']:.1f} → "
                   f"{s2['wickets_taken']/s2['innings_reaching_death']:.1f} "
                   f"({s2['wickets_taken']/s2['innings_reaching_death'] - s1['wickets_taken']/s1['innings_reaching_death']:+.1f})")
        
        # Diagnosis
        logger.info(f"\n💡 TIER 2 DIAGNOSIS:")
        
        economy_delta = s2['economy'] - s1['economy']
        
        if economy_delta > 1.5:
            logger.info(f"  🔴 SEVERE DEATH BOWLING DECLINE: {economy_delta:.2f} runs/over worse")
            logger.info(f"     → Death bowling execution is a MAJOR problem")
        elif economy_delta > 0.5:
            logger.info(f"  🟡 MODERATE DEATH BOWLING DECLINE: {economy_delta:.2f} runs/over worse")
        else:
            logger.info(f"  ✅ DEATH BOWLING STABLE: Economy maintained when opponents reached death")
    
    return stats_df


# ══════════════════════════════════════════════════════════════════════════
# INTEGRATED DIAGNOSIS
# ══════════════════════════════════════════════════════════════════════════

def integrated_diagnosis(tier1_summary, tier2_stats):
    """
    Combine Tier 1 and Tier 2 to give overall diagnosis.
    """
    logger.info("\n" + "="*80)
    logger.info("🎯 INTEGRATED DIAGNOSIS: Death Bowling Failure Root Cause")
    logger.info("="*80)
    
    if len(tier1_summary) < 2 or len(tier2_stats) < 2:
        logger.info("\n⚠️ Insufficient data for integrated diagnosis")
        return
    
    s1_tier1 = tier1_summary[tier1_summary['season'] == 'S1'].iloc[0]
    s2_tier1 = tier1_summary[tier1_summary['season'] == 'S2'].iloc[0]
    
    s1_tier2 = tier2_stats[tier2_stats['season'] == 'S1'].iloc[0]
    s2_tier2 = tier2_stats[tier2_stats['season'] == 'S2'].iloc[0]
    
    reach_rate_increase = s2_tier1['reached_death_pct'] - s1_tier1['reached_death_pct']
    economy_increase = s2_tier2['economy'] - s1_tier2['economy']
    
    logger.info(f"\nKey Metrics:")
    logger.info(f"  Tier 1 (Opponent Reach Rate): {s1_tier1['reached_death_pct']:.0f}% → {s2_tier1['reached_death_pct']:.0f}% "
               f"(Δ = {reach_rate_increase:+.0f}pp)")
    logger.info(f"  Tier 2 (Death Economy): {s1_tier2['economy']:.2f} → {s2_tier2['economy']:.2f} "
               f"(Δ = {economy_increase:+.2f} runs/over)")
    
    # Classification matrix
    logger.info(f"\n{'='*80}")
    logger.info("ROOT CAUSE CLASSIFICATION:")
    logger.info("-"*80)
    
    if reach_rate_increase > 15 and economy_increase > 1.0:
        logger.info("  📊 COMPOUND FAILURE (Both tiers worsened)")
        logger.info("     1. Middle-overs bowling collapse → More opponents reaching death")
        logger.info("     2. Poor death-phase bowling → Higher economy when they reached")
        logger.info("\n  💡 S3 Priority: FIX BOTH middle-overs wicket-taking AND death bowling")
        
    elif reach_rate_increase > 15:
        logger.info("  📊 PRIMARY CAUSE: MIDDLE-OVERS BOWLING COLLAPSE")
        logger.info("     Death phase economy was OK, but too many opponents reached death")
        logger.info("     → JAB couldn't take wickets in overs 7-15 in S2")
        logger.info("\n  💡 S3 Priority: Strengthen MIDDLE-OVERS bowlers (7-15), not death specialists")
        
    elif economy_increase > 1.0:
        logger.info("  📊 PRIMARY CAUSE: DEATH BOWLING EXECUTION")
        logger.info("     Similar % of opponents reached death, but scored more in overs 16-20")
        logger.info("\n  💡 S3 Priority: Recruit death-over bowling specialists")
        
    else:
        logger.info("  📊 MILD DECLINE OR STABLE")
        logger.info("     Neither middle-overs collapse nor death execution showed severe deterioration")
        logger.info("\n  💡 May be regression to mean or other factors (captaincy, opposition)")
    
    # Sample size caveat
    logger.info(f"\n⚠️  SAMPLE SIZE CAVEAT:")
    logger.info(f"   S1 opponent innings reaching death: n={s1_tier2['innings_reaching_death']}")
    logger.info(f"   S2 opponent innings reaching death: n={s2_tier2['innings_reaching_death']}")
    logger.info(f"   Small samples (n<10) limit confidence in conclusions")


# ══════════════════════════════════════════════════════════════════════════
# VISUALIZATION
# ══════════════════════════════════════════════════════════════════════════

def create_two_tier_visualization(tier1_summary, tier2_stats):
    """Visualize two-tier analysis."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    
    # Plot 1: Tier 1 - Opponent Innings Completion
    seasons = tier1_summary['season'].values
    reach_rates = tier1_summary['reached_death_pct'].values
    
    bars1 = ax1.bar(seasons, reach_rates, color=['#4CAF50', '#F44336'], alpha=0.7, edgecolor='black')
    ax1.set_ylabel('% of Opponent Innings Reaching Death Phase', fontsize=12)
    ax1.set_title('Tier 1: Did Opponents Reach Death Overs?', fontsize=14, fontweight='bold')
    ax1.set_ylim(0, 100)
    ax1.grid(axis='y', alpha=0.3)
    
    for bar in bars1:
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.0f}%',
                ha='center', va='bottom', fontsize=12, fontweight='bold')
    
    # Plot 2: Tier 2 - Death Bowling Economy
    economies = tier2_stats['economy'].values
    
    bars2 = ax2.bar(seasons, economies, color=['#4CAF50', '#F44336'], alpha=0.7, edgecolor='black')
    ax2.set_ylabel('Economy Rate (runs/over)', fontsize=12)
    ax2.set_title('Tier 2: Death Bowling Economy (When Reached)', fontsize=14, fontweight='bold')
    ax2.set_ylim(0, max(economies) * 1.3)
    ax2.grid(axis='y', alpha=0.3)
    
    for bar in bars2:
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.2f}',
                ha='center', va='bottom', fontsize=12, fontweight='bold')
    
    plt.tight_layout()
    output_path = EXPORT_DIR / "death_bowling_two_tier_analysis.png"
    plt.savefig(output_path, dpi=150)
    logger.info(f"\n📊 Visualization saved: {output_path}")
    plt.close()


# ══════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════

def main():
    """Run two-tier death bowling analysis."""
    logger.info("\n" + "="*80)
    logger.info("DEATH BOWLING TWO-TIER ANALYSIS")
    logger.info("="*80)
    logger.info("\nSeparating 'opponents reaching death' from 'death bowling economy'")
    
    bbb = load_ball_by_ball()
    
    # Tier 1: Opposition innings completion
    tier1_summary, opp_innings_stats = analyze_opposition_innings_completion(bbb)
    
    # Tier 2: Death bowling performance (conditional)
    tier2_stats = analyze_death_bowling_performance(bbb)
    
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
        'opp_innings_details': opp_innings_stats
    }


if __name__ == "__main__":
    main()
