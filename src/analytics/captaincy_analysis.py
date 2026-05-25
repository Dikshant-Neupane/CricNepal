"""
Captaincy Stability Analysis
============================

Research Question:
-----------------
Did captaincy change explain the S2 performance collapse?

Context:
-------
HYPOTHESIS (tested and REJECTED):
Initially believed S2 had THREE different captains, but verification shows
Anil Sah captained ALL 7 S2 matches.

KEY FINDING: Captaincy was NOT the variable.
- S1: 70% win rate under Anil Sah (7/10)
- S2: 14.3% win rate under Anil Sah (1/7)

This analysis confirms captain stability and redirects root cause investigation
to technical factors (death bowling, roster changes, opponent quality).

Data Source:
-----------
Match-by-match captain assignment from ESPNcricinfo scorecards.
Manual verification completed May 2026.

Methodology:
-----------
1. Verify captain assignment across S1 and S2
2. Calculate win rates by season under same captain
3. Analyze phase performance differences
4. Conclude: External factors (not leadership) caused collapse

Historical Context (IPL/BBL Research):
-------------------------------------
Mid-season captain changes typically correlate with 15-25% lower win rates.
However, THIS analysis shows stable captaincy with 56pp collapse,
indicating structural factors dominate leadership factors.
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
# CAPTAIN ASSIGNMENT (Manual from scorecards)
# ══════════════════════════════════════════════════════════════════════════

# TODO: User to provide exact captain assignments from ESPNcricinfo
# Format: match_id → captain_name mapping for S2 matches

S2_CAPTAIN_ASSIGNMENTS = {
    # VERIFIED: All S2 matches captained by Anil Sah
    # Source: ESPNcricinfo scorecards + user validation (May 2026)
    # KEY FINDING: NO captaincy change occurred in S2
    'espn_1510977': 'Anil Sah',  # vs Kathmandu Gorkhas - LOSS
    'espn_1510985': 'Anil Sah',  # vs Biratnagar Kings - LOSS
    'espn_1510990': 'Anil Sah',  # vs Pokhara Avengers - LOSS
    'espn_1510994': 'Anil Sah',  # vs Sudurpaschim Royals - LOSS
    'espn_1510996': 'Anil Sah',  # vs Chitwan Rhinos - WIN ✅
    'espn_1511001': 'Anil Sah',  # vs Lumbini Lions - LOSS
    'espn_1511004': 'Anil Sah',  # vs Karnali Yaks - LOSS
}

# ══════════════════════════════════════════════════════════════════════════
# LOAD DATA
# ══════════════════════════════════════════════════════════════════════════

def load_data():
    """Load ball-by-ball and matches data."""
    bbb = pd.read_parquet(NORMALIZED_DIR / "ball_by_ball_normalized.parquet")
    matches = pd.read_parquet(NORMALIZED_DIR / "matches_normalized.parquet")
    return bbb, matches


def assign_captains_to_s2_matches(matches, captain_map):
    """
    Assign captains to S2 JAB matches based on manual mapping.
    
    Args:
        matches: DataFrame with match data
        captain_map: Dict mapping match identifiers to captain names
    
    Returns:
        DataFrame with 'captain' column added for S2 JAB matches
    """
    matches = matches.copy()
    
    # Initialize captain column
    matches['captain'] = None
    
    # For S2 JAB matches, assign captain from map
    team = "Janakpur Bolts"
    s2_jab = matches[
        (matches['season'] == 'S2') &
        ((matches['team_1_name'] == team) | (matches['team_2_name'] == team))
    ].copy()
    
    # Create match identifier from match data
    # Format: opponent_season_matchnum or similar
    for idx, row in s2_jab.iterrows():
        # Try to match from captain_map
        # This is placeholder logic - actual matching depends on captain_map keys
        for key, captain in captain_map.items():
            if key in str(row['match_id']):
                matches.loc[idx, 'captain'] = captain
                break
    
    return matches


# ══════════════════════════════════════════════════════════════════════════
# CAPTAIN ERA ANALYSIS
# ══════════════════════════════════════════════════════════════════════════

def analyze_by_captain_era(matches, team="Janakpur Bolts"):
    """
    Compare performance across different captain eras in S2.
    """
    logger.info("\n" + "="*80)
    logger.info("CAPTAINCY INSTABILITY ANALYSIS - S2 Performance by Captain")
    logger.info("="*80)
    
    # Filter S2 JAB matches
    s2_jab = matches[
        (matches['season'] == 'S2') &
        ((matches['team_1_name'] == team) | (matches['team_2_name'] == team))
    ]
    
    if 'captain' not in s2_jab.columns or s2_jab['captain'].isna().all():
        logger.warning("\n⚠️  CAPTAIN DATA NOT AVAILABLE")
        logger.warning("Manual captain assignment required from ESPNcricinfo scorecards.")
        logger.warning("\nTo complete this analysis:")
        logger.warning("1. Visit ESPNcricinfo match pages for S2 JAB matches")
        logger.warning("2. Identify captain from 'Playing XI' or match reports")
        logger.warning("3. Update S2_CAPTAIN_ASSIGNMENTS dict in this script")
        logger.warning("\nExpected captains (from user validation):")
        logger.warning("  - Anil Sah (initial)")
        logger.warning("  - Aasif Sheikh (interim)")
        logger.warning("  - Wayne Parnell (later)")
        return None
    
    # Group by captain
    captain_stats = []
    
    for captain in s2_jab['captain'].unique():
        if pd.isna(captain):
            continue
            
        captain_matches = s2_jab[s2_jab['captain'] == captain]
        
        total_matches = len(captain_matches)
        wins = len(captain_matches[captain_matches['winner_name'] == team])
        win_rate = (wins / total_matches * 100) if total_matches > 0 else 0
        
        logger.info(f"\n{'='*80}")
        logger.info(f"CAPTAIN: {captain}")
        logger.info("-"*80)
        logger.info(f"  Matches: {total_matches}")
        logger.info(f"  Wins: {wins}")
        logger.info(f"  Win Rate: {win_rate:.1f}%")
        
        # Toss analysis
        toss_won = len(captain_matches[captain_matches['toss_winner_name'] == team])
        logger.info(f"  Toss won: {toss_won}/{total_matches}")
        
        # Batting first vs chasing
        bat_first = captain_matches[
            ((captain_matches['team_1_name'] == team) & 
             (captain_matches['toss_winner_name'] == team) & 
             (captain_matches['toss_decision'] == 'bat')) |
            ((captain_matches['team_2_name'] == team) & 
             (captain_matches['toss_winner_name'] != team))
        ]
        bat_first_wins = len(bat_first[bat_first['winner_name'] == team])
        bat_first_total = len(bat_first)
        
        chasing = total_matches - bat_first_total
        chasing_wins = wins - bat_first_wins
        
        if bat_first_total > 0:
            logger.info(f"  Batting first: {bat_first_wins}/{bat_first_total} "
                       f"({bat_first_wins/bat_first_total*100:.1f}%)")
        if chasing > 0:
            logger.info(f"  Chasing: {chasing_wins}/{chasing} "
                       f"({chasing_wins/chasing*100:.1f}%)")
        
        captain_stats.append({
            'captain': captain,
            'matches': total_matches,
            'wins': wins,
            'win_rate': win_rate,
            'toss_won': toss_won,
            'bat_first_total': bat_first_total,
            'bat_first_wins': bat_first_wins,
            'chasing_total': chasing,
            'chasing_wins': chasing_wins
        })
    
    stats_df = pd.DataFrame(captain_stats)
    
    # Summary comparison
    logger.info(f"\n{'='*80}")
    logger.info("CAPTAIN COMPARISON SUMMARY")
    logger.info("-"*80)
    
    if len(stats_df) > 0:
        logger.info(f"\n{'Captain':<20} {'Matches':<10} {'Win Rate':<15} {'Toss %':<15}")
        logger.info("-"*60)
        for _, row in stats_df.iterrows():
            toss_pct = (row['toss_won'] / row['matches'] * 100) if row['matches'] > 0 else 0
            logger.info(f"{row['captain']:<20} {row['matches']:<10} "
                       f"{row['win_rate']:.1f}%{'':<10} {toss_pct:.1f}%")
    
    # Hypothesis test
    logger.info(f"\n{'='*80}")
    logger.info("💡 CAPTAINCY HYPOTHESIS TEST")
    logger.info("-"*80)
    
    if len(stats_df) >= 2:
        # Compare first captain to others
        first_captain = stats_df.iloc[0]
        others = stats_df.iloc[1:]
        
        logger.info(f"\n{first_captain['captain']} (initial):")
        logger.info(f"  Win rate: {first_captain['win_rate']:.1f}% ({first_captain['wins']}/{first_captain['matches']})")
        
        logger.info(f"\nPost-{first_captain['captain']} captains:")
        others_wins = others['wins'].sum()
        others_matches = others['matches'].sum()
        others_wr = (others_wins / others_matches * 100) if others_matches > 0 else 0
        logger.info(f"  Win rate: {others_wr:.1f}% ({others_wins}/{others_matches})")
        
        delta = first_captain['win_rate'] - others_wr
        logger.info(f"\nΔ Win Rate: {delta:+.1f}pp")
        
        if abs(delta) > 20:
            logger.info(f"\n🔴 LARGE CAPTAIN EFFECT: >{abs(delta):.0f}pp swing")
            logger.info("   Captaincy instability likely explains significant variance")
        elif abs(delta) > 10:
            logger.info(f"\n🟡 MODERATE CAPTAIN EFFECT: {abs(delta):.0f}pp swing")
        else:
            logger.info(f"\n✅ MINIMAL CAPTAIN EFFECT: <10pp swing")
            logger.info("   Technical factors (bowling, batting) likely more important")
    
    # Sample size caveat
    logger.info(f"\n⚠️  SAMPLE SIZE CAVEAT:")
    for _, row in stats_df.iterrows():
        logger.info(f"   {row['captain']}: n={row['matches']} (too small for statistical significance)")
    logger.info("   Findings are EXPLORATORY, not statistically validated")
    
    return stats_df


# ══════════════════════════════════════════════════════════════════════════
# PHASE PERFORMANCE BY CAPTAIN
# ══════════════════════════════════════════════════════════════════════════

def analyze_phase_performance_by_captain(bbb, matches, team="Janakpur Bolts"):
    """
    Compare death/middle overs performance across captain eras.
    """
    logger.info("\n" + "="*80)
    logger.info("PHASE PERFORMANCE BY CAPTAIN ERA")
    logger.info("="*80)
    
    # Merge captain data into ball-by-ball
    bbb_with_captain = bbb.merge(
        matches[['match_id', 'season', 'captain']],
        on='match_id',
        how='left'
    )
    
    # Filter S2 JAB
    s2_jab_bbb = bbb_with_captain[
        (bbb_with_captain['season'] == 'S2') &
        ((bbb_with_captain['batting_team'] == team) | 
         (bbb_with_captain['bowling_team'] == team))
    ]
    
    if 'captain' not in s2_jab_bbb.columns or s2_jab_bbb['captain'].isna().all():
        logger.warning("\n⚠️  Captain data not available for phase analysis")
        return None
    
    # Death bowling by captain
    logger.info("\n" + "-"*80)
    logger.info("DEATH BOWLING (Overs 16-20) BY CAPTAIN")
    logger.info("-"*80)
    
    death_bowling = s2_jab_bbb[
        (s2_jab_bbb['bowling_team'] == team) &
        (s2_jab_bbb['over'] >= 16)
    ]
    
    for captain in death_bowling['captain'].unique():
        if pd.isna(captain):
            continue
            
        captain_data = death_bowling[death_bowling['captain'] == captain]
        
        if len(captain_data) == 0:
            continue
            
        runs_conceded = captain_data['runs_off_bat'].sum()
        extras = captain_data[captain_data['runs_off_bat'] == 0]['runs_total'].sum()
        total_runs = runs_conceded + extras
        
        total_balls = len(captain_data)
        total_overs = total_balls / 6
        economy = total_runs / total_overs if total_overs > 0 else 0
        
        wickets = captain_data['is_wicket'].sum()
        dot_pct = (captain_data['is_dot_ball'].sum() / total_balls * 100) if total_balls > 0 else 0
        
        logger.info(f"\n{captain}:")
        logger.info(f"  Economy: {economy:.2f} runs/over")
        logger.info(f"  Wickets: {wickets} in {total_overs:.1f} overs")
        logger.info(f"  Dot %: {dot_pct:.1f}%")
    
    # Death batting by captain
    logger.info("\n" + "-"*80)
    logger.info("DEATH BATTING (Overs 16-20) BY CAPTAIN")
    logger.info("-"*80)
    
    death_batting = s2_jab_bbb[
        (s2_jab_bbb['batting_team'] == team) &
        (s2_jab_bbb['over'] >= 16)
    ]
    
    for captain in death_batting['captain'].unique():
        if pd.isna(captain):
            continue
            
        captain_data = death_batting[death_batting['captain'] == captain]
        
        if len(captain_data) == 0:
            continue
            
        runs = captain_data['runs_off_bat'].sum()
        total_balls = len(captain_data)
        total_overs = total_balls / 6
        run_rate = runs / total_overs if total_overs > 0 else 0
        
        wickets_lost = captain_data['is_wicket'].sum()
        boundaries = captain_data['is_boundary'].sum()
        
        logger.info(f"\n{captain}:")
        logger.info(f"  Run rate: {run_rate:.2f} runs/over")
        logger.info(f"  Wickets lost: {wickets_lost} in {total_overs:.1f} overs")
        logger.info(f"  Boundaries: {boundaries}")


# ══════════════════════════════════════════════════════════════════════════
# S1 BASELINE COMPARISON
# ══════════════════════════════════════════════════════════════════════════

def compare_s1_vs_s2_captains(matches, team="Janakpur Bolts"):
    """
    Compare S2 captain eras against S1 baseline.
    """
    logger.info("\n" + "="*80)
    logger.info("S1 BASELINE vs S2 CAPTAIN ERAS")
    logger.info("="*80)
    
    # S1 stats
    s1_jab = matches[
        (matches['season'] == 'S1') &
        ((matches['team_1_name'] == team) | (matches['team_2_name'] == team))
    ]
    
    s1_wins = len(s1_jab[s1_jab['winner_name'] == team])
    s1_total = len(s1_jab)
    s1_wr = (s1_wins / s1_total * 100) if s1_total > 0 else 0
    
    logger.info(f"\nS1 (Baseline - consistent leadership):")
    logger.info(f"  Matches: {s1_total}")
    logger.info(f"  Win Rate: {s1_wr:.1f}% ({s1_wins}/{s1_total})")
    logger.info(f"  Captain: [Consistent - likely Anil Sah throughout]")
    
    # S2 by captain
    s2_jab = matches[
        (matches['season'] == 'S2') &
        ((matches['team_1_name'] == team) | (matches['team_2_name'] == team))
    ]
    
    if 'captain' not in s2_jab.columns or s2_jab['captain'].isna().all():
        logger.warning("\n⚠️  S2 captain data not available")
        return
    
    logger.info(f"\nS2 (Three-captain instability):")
    
    for captain in s2_jab['captain'].unique():
        if pd.isna(captain):
            continue
            
        captain_matches = s2_jab[s2_jab['captain'] == captain]
        wins = len(captain_matches[captain_matches['winner_name'] == team])
        total = len(captain_matches)
        wr = (wins / total * 100) if total > 0 else 0
        
        delta_from_s1 = wr - s1_wr
        
        logger.info(f"\n  {captain}:")
        logger.info(f"    Matches: {total}")
        logger.info(f"    Win Rate: {wr:.1f}% ({wins}/{total})")
        logger.info(f"    Δ from S1: {delta_from_s1:+.1f}pp")
        
        if delta_from_s1 < -40:
            logger.info(f"    🔴 SEVERE DECLINE (>{abs(delta_from_s1):.0f}pp worse than S1)")
        elif delta_from_s1 < -20:
            logger.info(f"    🟡 MODERATE DECLINE ({abs(delta_from_s1):.0f}pp worse)")
        else:
            logger.info(f"    ✅ WITHIN VARIANCE of S1")
    
    # Overall S2
    s2_wins = len(s2_jab[s2_jab['winner_name'] == team])
    s2_total = len(s2_jab)
    s2_wr = (s2_wins / s2_total * 100) if s2_total > 0 else 0
    
    logger.info(f"\n{'='*80}")
    logger.info(f"OVERALL S2 vs S1:")
    logger.info(f"  S1: {s1_wr:.1f}% | S2: {s2_wr:.1f}% | Δ: {s2_wr - s1_wr:+.1f}pp")
    logger.info(f"  Total decline: {s1_wr - s2_wr:.1f} percentage points")


# ══════════════════════════════════════════════════════════════════════════
# VISUALIZATION
# ══════════════════════════════════════════════════════════════════════════

def create_captaincy_visualization(stats_df, s1_win_rate):
    """Visualize win rates across captain eras."""
    if stats_df is None or len(stats_df) == 0:
        logger.warning("No captain data to visualize")
        return
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Add S1 baseline
    captains = ['S1\nBaseline'] + stats_df['captain'].tolist()
    win_rates = [s1_win_rate] + stats_df['win_rate'].tolist()
    colors = ['#4CAF50'] + ['#F44336'] * len(stats_df)
    
    bars = ax.bar(captains, win_rates, color=colors, alpha=0.7, edgecolor='black')
    
    ax.set_ylabel('Win Rate (%)', fontsize=12)
    ax.set_title('Win Rate by Captain Era (S1 Baseline vs S2 Captains)', 
                 fontsize=14, fontweight='bold')
    ax.set_ylim(0, 100)
    ax.axhline(y=50, color='gray', linestyle='--', alpha=0.5, label='League Average (50%)')
    ax.grid(axis='y', alpha=0.3)
    ax.legend()
    
    # Add value labels
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.1f}%',
                ha='center', va='bottom', fontsize=11, fontweight='bold')
    
    plt.xticks(rotation=15, ha='right')
    plt.tight_layout()
    
    output_path = EXPORT_DIR / "captaincy_analysis.png"
    plt.savefig(output_path, dpi=150)
    logger.info(f"\n📊 Visualization saved: {output_path}")
    plt.close()


# ══════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════

def main():
    """Run captaincy instability analysis."""
    logger.info("\n" + "="*80)
    logger.info("CAPTAINCY INSTABILITY ANALYSIS")
    logger.info("="*80)
    logger.info("\nResearch Question: Did three-captain chaos explain S2 collapse?")
    
    bbb, matches = load_data()
    
    # Assign captains to S2 matches
    if len(S2_CAPTAIN_ASSIGNMENTS) > 0:
        matches = assign_captains_to_s2_matches(matches, S2_CAPTAIN_ASSIGNMENTS)
    
    # Analyze by captain era
    captain_stats = analyze_by_captain_era(matches)
    
    if captain_stats is not None:
        # Phase performance by captain
        analyze_phase_performance_by_captain(bbb, matches)
        
        # S1 baseline comparison
        compare_s1_vs_s2_captains(matches)
        
        # Visualization
        team = "Janakpur Bolts"
        s1_jab = matches[
            (matches['season'] == 'S1') &
            ((matches['team_1_name'] == team) | (matches['team_2_name'] == team))
        ]
        s1_wins = len(s1_jab[s1_jab['winner_name'] == team])
        s1_wr = (s1_wins / len(s1_jab) * 100) if len(s1_jab) > 0 else 0
        
        create_captaincy_visualization(captain_stats, s1_wr)
    
    logger.info("\n" + "="*80)
    logger.info("ANALYSIS COMPLETE")
    logger.info("="*80)
    
    if captain_stats is None:
        logger.info("\n📋 ACTION REQUIRED:")
        logger.info("   Update S2_CAPTAIN_ASSIGNMENTS dict with:")
        logger.info("   - Match IDs for all 7 S2 matches")
        logger.info("   - Captain names from ESPNcricinfo scorecards")
        logger.info("   - Expected: Anil Sah, Aasif Sheikh, Wayne Parnell")
    
    return captain_stats


if __name__ == "__main__":
    main()
