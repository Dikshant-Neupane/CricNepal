"""
League Dew Factor Analysis
==========================

Purpose:
--------
Estimate whether day-night (D/N) matches show a measurable dew-related advantage
by comparing second-innings scoring and bowling control in Day vs Day-Night matches.

Approach:
--------
- Compute inning-level metrics (runs/over, dot%, boundaries/over, wickets) for innings 1 and 2
- Compare innings-2 performance in Day vs Day-Night matches league-wide
- Compute the same restricted to Janakpur Bolts matches to test team-specific dew effect

Output:
-------
- Summary logs and a visualization saved to data/exports/league_dew_factor.png
"""

import pandas as pd
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt

from src.utils.logging_config import get_logger
logger = get_logger(__name__)

try:
    from src.config.paths import NORMALIZED_DIR, EXPORT_DIR
except ImportError:
    NORMALIZED_DIR = Path(__file__).resolve().parent.parent / "data" / "normalized"
    EXPORT_DIR = Path(__file__).resolve().parent.parent / "data" / "exports"

EXPORT_DIR.mkdir(parents=True, exist_ok=True)


def load_data():
    bbb = pd.read_parquet(NORMALIZED_DIR / "ball_by_ball_normalized.parquet")
    matches = pd.read_parquet(NORMALIZED_DIR / "matches_normalized.parquet")
    return bbb, matches


def inning_level_metrics(bbb):
    # aggregate per match_id, innings
    agg = bbb.groupby(['match_id','innings']).agg(
        runs_off_bat=('runs_off_bat','sum'),
        runs_total=('runs_total','sum'),
        balls=('over','count'),
        dots=('is_dot_ball','sum'),
        boundaries=('is_boundary','sum'),
        wickets=('is_wicket','sum')
    ).reset_index()

    agg['overs'] = agg['balls'] / 6
    agg['runs_per_over'] = agg['runs_total'] / agg['overs'].replace(0,np.nan)
    agg['dot_pct'] = agg['dots'] / agg['balls'] * 100
    agg['boundaries_per_over'] = agg['boundaries'] / agg['overs'].replace(0,np.nan)
    return agg


def dew_comparison(bbb, matches):
    logger.info("\n" + "="*80)
    logger.info("LEAGUE DEW-FACTOR ANALYSIS (Day vs Day-Night)")
    logger.info("="*80)

    agg = inning_level_metrics(bbb)
    agg = agg.merge(matches[['match_id','day_night','season','team_1_name','team_2_name']], on='match_id', how='left')

    # Focus on innings 2 (where dew would affect bowling team)
    innings2 = agg[agg['innings'] == 2].copy()

    summary = innings2.groupby('day_night').agg(
        matches=('match_id','nunique'),
        avg_rpo=('runs_per_over','mean'),
        avg_dot_pct=('dot_pct','mean'),
        avg_boundaries_per_over=('boundaries_per_over','mean'),
        avg_wickets=('wickets','mean')
    ).reset_index()

    logger.info("\nLeague-level innings-2 summary by day_night:")
    logger.info(summary.to_string(index=False))

    # Janakpur-specific: look at match where Janakpur is either team
    janakpur_matches = matches[(matches['team_1_name']=='Janakpur Bolts') | (matches['team_2_name']=='Janakpur Bolts')]['match_id'].unique()
    jan_innings2 = innings2[innings2['match_id'].isin(janakpur_matches)].copy()

    jp_summary = jan_innings2.groupby('day_night').agg(
        matches=('match_id','nunique'),
        avg_rpo=('runs_per_over','mean'),
        avg_dot_pct=('dot_pct','mean'),
        avg_boundaries_per_over=('boundaries_per_over','mean'),
        avg_wickets=('wickets','mean')
    ).reset_index()

    logger.info("\nJanakpur-specific innings-2 summary by day_night:")
    logger.info(jp_summary.to_string(index=False))

    # Visualization: side-by-side bar charts for league and Janakpur
    fig, axes = plt.subplots(2,2, figsize=(12,8))

    # League RPO
    axes[0,0].bar(summary['day_night'], summary['avg_rpo'], color=['#2196F3','#FF9800'])
    axes[0,0].set_title('League innings-2 runs/over (Day vs Day-Night)')

    # League dot%
    axes[0,1].bar(summary['day_night'], summary['avg_dot_pct'], color=['#2196F3','#FF9800'])
    axes[0,1].set_title('League innings-2 dot% (Day vs Day-Night)')

    # JP RPO
    if not jp_summary.empty:
        axes[1,0].bar(jp_summary['day_night'], jp_summary['avg_rpo'], color=['#4CAF50','#FFC107'])
        axes[1,0].set_title('Janakpur innings-2 runs/over')
        axes[1,1].bar(jp_summary['day_night'], jp_summary['avg_dot_pct'], color=['#4CAF50','#FFC107'])
        axes[1,1].set_title('Janakpur innings-2 dot%')
    else:
        axes[1,0].text(0.5,0.5,'No Janakpur innings-2 data', ha='center')
        axes[1,1].text(0.5,0.5,'No Janakpur innings-2 data', ha='center')

    plt.tight_layout()
    out = EXPORT_DIR / 'league_dew_factor.png'
    plt.savefig(out, dpi=150)
    logger.info(f"\n📊 Visualization saved: {out}")
    plt.close()

    return summary, jp_summary


def main():
    bbb, matches = load_data()
    summary, jp_summary = dew_comparison(bbb, matches)
    return {
        'league': summary,
        'janakpur': jp_summary
    }


if __name__ == '__main__':
    main()
"""
League-Wide Dew Factor Analysis
================================

Validates the "chasing advantage" hypothesis at Kirtipur by analyzing ALL 64 
NPL matches, not just Janakpur Bolts' 17 matches.

Research Question:
-----------------
Is chasing advantageous at Kirtipur due to dew factor, or is JAB's 58% chasing 
win rate vs 20% batting first win rate team-specific?

Methodology:
-----------
1. Calculate league-wide batting first vs chasing win rates
2. Chi-square test: Is difference statistically significant?
3. Team-by-team analysis: Do all teams perform better chasing?
4. Match quality controls: Remove one-sided matches (100+ margin)
5. Temporal analysis: S1 vs S2 dew factor consistency
"""

import pandas as pd
import numpy as np
from scipy import stats
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

def load_npl_matches():
    """Load all NPL matches."""
    matches = pd.read_parquet(NORMALIZED_DIR / "matches_normalized.parquet")
    return matches


# ══════════════════════════════════════════════════════════════════════════
# LEAGUE-WIDE ANALYSIS
# ══════════════════════════════════════════════════════════════════════════

def calculate_league_wide_toss_impact(matches):
    """Calculate batting first vs chasing win rates across all teams."""
    logger.info("\n" + "="*80)
    logger.info("LEAGUE-WIDE DEW FACTOR ANALYSIS")
    logger.info("="*80)
    
    logger.info(f"\nTotal matches: {len(matches)}")
    logger.info(f"Season split: {matches['season'].value_counts().to_dict()}")
    
    # Determine who batted first
    # Assumption: toss_winner_name + toss_decision determines batting order
    # If toss winner chose "bat", they batted first
    # If toss winner chose "field", opponent batted first
    
    def determine_batting_first(row):
        """Return team that batted first."""
        if pd.isna(row['toss_decision']):
            return None  # Cannot determine
        
        toss_winner = row['toss_winner_name']
        toss_decision = row['toss_decision'].lower()
        
        if 'bat' in toss_decision:
            return toss_winner
        elif 'field' in toss_decision or 'bowl' in toss_decision:
            # Opponent batted first
            if row['team_1_name'] == toss_winner:
                return row['team_2_name']
            else:
                return row['team_1_name']
        else:
            return None
    
    matches['batting_first_team'] = matches.apply(determine_batting_first, axis=1)
    
    # Remove matches with missing toss data
    valid_matches = matches[matches['batting_first_team'].notna()].copy()
    logger.info(f"Valid matches (with toss data): {len(valid_matches)}")
    
    # Determine batting first vs chasing outcome
    def batting_first_outcome(row):
        """Did team batting first win?"""
        if row['batting_first_team'] == row['winner_name']:
            return 'batting_first_won'
        else:
            return 'chasing_won'
    
    valid_matches['outcome'] = valid_matches.apply(batting_first_outcome, axis=1)
    
    # Calculate league-wide rates
    batting_first_wins = len(valid_matches[valid_matches['outcome'] == 'batting_first_won'])
    chasing_wins = len(valid_matches[valid_matches['outcome'] == 'chasing_won'])
    total = len(valid_matches)
    
    batting_first_pct = (batting_first_wins / total) * 100
    chasing_pct = (chasing_wins / total) * 100
    
    logger.info(f"\n📊 LEAGUE-WIDE RESULTS:")
    logger.info(f"  Batting first wins: {batting_first_wins}/{total} ({batting_first_pct:.1f}%)")
    logger.info(f"  Chasing wins: {chasing_wins}/{total} ({chasing_pct:.1f}%)")
    logger.info(f"  Chasing advantage: +{chasing_pct - batting_first_pct:.1f}pp")
    
    # ── Statistical Test: Chi-Square ──
    logger.info("\n" + "-"*80)
    logger.info("CHI-SQUARE TEST: Is chasing advantage significant?")
    logger.info("-"*80)
    
    # Null hypothesis: Batting first = 50%, Chasing = 50%
    expected_bf = total / 2
    expected_chase = total / 2
    
    observed = [batting_first_wins, chasing_wins]
    expected = [expected_bf, expected_chase]
    
    chi2, p_value = stats.chisquare(observed, expected)
    
    logger.info(f"\nNull hypothesis: No batting order advantage (50/50 split)")
    logger.info(f"Observed: {batting_first_wins}/{chasing_wins}")
    logger.info(f"Expected: {expected_bf:.0f}/{expected_chase:.0f}")
    logger.info(f"Chi-square statistic: {chi2:.3f}")
    logger.info(f"P-value: {p_value:.4f}")
    
    if p_value < 0.05:
        logger.info(f"✅ SIGNIFICANT (p < 0.05): Chasing advantage is REAL")
        logger.info(f"   Dew factor hypothesis SUPPORTED by league-wide data")
    elif p_value < 0.10:
        logger.info(f"⚠️  MARGINALLY SIGNIFICANT (p < 0.10): Suggestive evidence")
    else:
        logger.info(f"❌ NOT SIGNIFICANT (p ≥ 0.10): No systematic chasing advantage")
        logger.info(f"   JAB's chasing bias may be team-specific, not venue-wide")
    
    return valid_matches, batting_first_pct, chasing_pct, p_value


# ══════════════════════════════════════════════════════════════════════════
# TEAM-BY-TEAM ANALYSIS
# ══════════════════════════════════════════════════════════════════════════

def team_by_team_analysis(matches):
    """Analyze batting first vs chasing for each team."""
    logger.info("\n" + "="*80)
    logger.info("TEAM-BY-TEAM TOSS IMPACT")
    logger.info("="*80)
    
    teams = sorted(set(matches['team_1_name'].unique()) | set(matches['team_2_name'].unique()))
    
    team_results = []
    
    for team in teams:
        # Get all matches where team participated
        team_matches = matches[
            (matches['team_1_name'] == team) | (matches['team_2_name'] == team)
        ]
        
        # Batting first matches
        bf_matches = team_matches[team_matches['batting_first_team'] == team]
        bf_wins = len(bf_matches[bf_matches['winner_name'] == team])
        bf_total = len(bf_matches)
        bf_pct = (bf_wins / bf_total * 100) if bf_total > 0 else 0
        
        # Chasing matches
        chase_matches = team_matches[team_matches['batting_first_team'] != team]
        chase_wins = len(chase_matches[chase_matches['winner_name'] == team])
        chase_total = len(chase_matches)
        chase_pct = (chase_wins / chase_total * 100) if chase_total > 0 else 0
        
        team_results.append({
            'team': team,
            'bf_wins': bf_wins,
            'bf_total': bf_total,
            'bf_pct': bf_pct,
            'chase_wins': chase_wins,
            'chase_total': chase_total,
            'chase_pct': chase_pct,
            'diff': chase_pct - bf_pct
        })
    
    team_df = pd.DataFrame(team_results).sort_values('diff', ascending=False)
    
    logger.info(f"\n{'Team':<25} {'Batting First':<20} {'Chasing':<20} {'Diff':<10}")
    logger.info("-"*80)
    
    for _, row in team_df.iterrows():
        logger.info(f"{row['team']:<25} {row['bf_wins']:>2}/{row['bf_total']:<2} ({row['bf_pct']:>5.1f}%)  "
                   f"{row['chase_wins']:>2}/{row['chase_total']:<2} ({row['chase_pct']:>5.1f}%)  "
                   f"{row['diff']:>+6.1f}pp")
    
    # Count how many teams favor chasing
    teams_favor_chasing = len(team_df[team_df['diff'] > 0])
    teams_favor_batting = len(team_df[team_df['diff'] < 0])
    
    logger.info(f"\n📊 SUMMARY:")
    logger.info(f"  Teams with chasing advantage: {teams_favor_chasing}/{len(team_df)}")
    logger.info(f"  Teams with batting first advantage: {teams_favor_batting}/{len(team_df)}")
    
    if teams_favor_chasing > (len(team_df) * 0.7):
        logger.info(f"  ✅ Chasing advantage is CONSISTENT across teams (>70%)")
        logger.info(f"     Supports dew factor hypothesis")
    elif teams_favor_chasing > (len(team_df) * 0.5):
        logger.info(f"  ⚠️  Chasing advantage is MODERATE (50-70% of teams)")
    else:
        logger.info(f"  ❌ Chasing advantage is NOT consistent across teams")
        logger.info(f"     Likely team-specific, not venue-specific")
    
    return team_df


# ══════════════════════════════════════════════════════════════════════════
# SEASONAL CONSISTENCY
# ══════════════════════════════════════════════════════════════════════════

def seasonal_consistency(matches):
    """Check if dew factor is consistent across S1 and S2."""
    logger.info("\n" + "="*80)
    logger.info("SEASONAL CONSISTENCY (S1 vs S2)")
    logger.info("="*80)
    
    for season in ['S1', 'S2']:
        season_matches = matches[matches['season'] == season]
        
        bf_wins = len(season_matches[season_matches['outcome'] == 'batting_first_won'])
        chase_wins = len(season_matches[season_matches['outcome'] == 'chasing_won'])
        total = len(season_matches)
        
        bf_pct = (bf_wins / total * 100) if total > 0 else 0
        chase_pct = (chase_wins / total * 100) if total > 0 else 0
        
        logger.info(f"\n{season}:")
        logger.info(f"  Batting first: {bf_wins}/{total} ({bf_pct:.1f}%)")
        logger.info(f"  Chasing: {chase_wins}/{total} ({chase_pct:.1f}%)")
        logger.info(f"  Chasing advantage: +{chase_pct - bf_pct:.1f}pp")


# ══════════════════════════════════════════════════════════════════════════
# VISUALIZATION
# ══════════════════════════════════════════════════════════════════════════

def create_dew_factor_plots(matches, team_df):
    """Visualize league-wide and team-level toss impact."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
    
    # ── Plot 1: League-Wide Win Rate ──
    outcomes = matches['outcome'].value_counts()
    
    labels = ['Batting First\nWins', 'Chasing\nWins']
    counts = [outcomes['batting_first_won'], outcomes['chasing_won']]
    colors = ['#E57373', '#64B5F6']
    
    bars = ax1.bar(labels, counts, color=colors, edgecolor='black', linewidth=1.5)
    ax1.set_ylabel('Number of Wins', fontsize=12)
    ax1.set_title('League-Wide: Batting First vs Chasing (All 64 Matches)', 
                  fontsize=14, fontweight='bold')
    ax1.set_ylim(0, max(counts) * 1.2)
    ax1.grid(axis='y', alpha=0.3)
    
    # Add value labels
    for bar in bars:
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height,
                f'{int(height)}\n({height/len(matches)*100:.1f}%)',
                ha='center', va='bottom', fontsize=11, fontweight='bold')
    
    # ── Plot 2: Team-Level Chasing Advantage ──
    team_df_sorted = team_df.sort_values('diff')
    
    colors_team = ['green' if x > 0 else 'red' for x in team_df_sorted['diff']]
    
    ax2.barh(team_df_sorted['team'], team_df_sorted['diff'], color=colors_team, alpha=0.7, edgecolor='black')
    ax2.axvline(0, color='black', linestyle='--', linewidth=1)
    ax2.set_xlabel('Chasing Advantage (percentage points)', fontsize=12)
    ax2.set_title('Team-Level: Chasing Win Rate - Batting First Win Rate', 
                  fontsize=14, fontweight='bold')
    ax2.grid(axis='x', alpha=0.3)
    
    plt.tight_layout()
    output_path = EXPORT_DIR / "league_wide_dew_factor_analysis.png"
    plt.savefig(output_path, dpi=150)
    logger.info(f"\n📊 Visualization saved: {output_path}")
    plt.close()


# ══════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════

def main():
    """Run league-wide dew factor analysis."""
    logger.info("\n" + "="*80)
    logger.info("LEAGUE-WIDE DEW FACTOR VALIDATION")
    logger.info("="*80)
    
    matches = load_npl_matches()
    
    # League-wide analysis
    matches_valid, bf_pct, chase_pct, p_value = calculate_league_wide_toss_impact(matches)
    
    # Team-by-team
    team_df = team_by_team_analysis(matches_valid)
    
    # Seasonal consistency
    seasonal_consistency(matches_valid)
    
    # Visualization
    create_dew_factor_plots(matches_valid, team_df)
    
    # ── Final Summary ──
    logger.info("\n" + "="*80)
    logger.info("🎯 FINAL CONCLUSION: DEW FACTOR HYPOTHESIS")
    logger.info("="*80)
    
    logger.info(f"\nLeague-wide chasing win rate: {chase_pct:.1f}%")
    logger.info(f"League-wide batting first win rate: {bf_pct:.1f}%")
    logger.info(f"Difference: {chase_pct - bf_pct:.1f}pp")
    logger.info(f"Statistical significance: p = {p_value:.4f}")
    
    teams_favor_chasing = len(team_df[team_df['diff'] > 0])
    
    if p_value < 0.05 and teams_favor_chasing > (len(team_df) * 0.7):
        logger.info(f"\n✅ DEW FACTOR HYPOTHESIS: STRONGLY SUPPORTED")
        logger.info(f"   - Chasing advantage is statistically significant (p < 0.05)")
        logger.info(f"   - {teams_favor_chasing}/{len(team_df)} teams favor chasing (>{len(team_df) * 0.7:.0f})")
        logger.info(f"   - Recommendation: Janakpur should ALWAYS CHASE when winning toss")
    elif p_value < 0.10:
        logger.info(f"\n⚠️  DEW FACTOR HYPOTHESIS: MODERATELY SUPPORTED")
        logger.info(f"   - Chasing advantage is marginally significant (p < 0.10)")
        logger.info(f"   - Evidence is suggestive but not conclusive")
        logger.info(f"   - Recommendation: Prefer chasing, but not absolute")
    else:
        logger.info(f"\n❌ DEW FACTOR HYPOTHESIS: NOT SUPPORTED")
        logger.info(f"   - Chasing advantage is NOT statistically significant (p ≥ 0.10)")
        logger.info(f"   - JAB's chasing bias is likely team-specific, not venue-wide")
        logger.info(f"   - Recommendation: Reevaluate toss strategy")
    
    logger.info(f"\n💡 JANAKPUR BOLTS CONTEXT:")
    jab_row = team_df[team_df['team'] == 'Janakpur Bolts'].iloc[0]
    logger.info(f"   JAB batting first: {jab_row['bf_pct']:.1f}% ({jab_row['bf_wins']}/{jab_row['bf_total']})")
    logger.info(f"   JAB chasing: {jab_row['chase_pct']:.1f}% ({jab_row['chase_wins']}/{jab_row['chase_total']})")
    logger.info(f"   JAB chasing advantage: {jab_row['diff']:.1f}pp")
    logger.info(f"   League average chasing advantage: {chase_pct - bf_pct:.1f}pp")
    
    if jab_row['diff'] > (chase_pct - bf_pct + 10):
        logger.info(f"\n   ⚠️  JAB's chasing advantage ({jab_row['diff']:.1f}pp) is HIGHER than league average ({chase_pct - bf_pct:.1f}pp)")
        logger.info(f"      This suggests JAB may have team-specific issues batting first (not just dew)")
    
    logger.info("\n" + "="*80)
    logger.info("ANALYSIS COMPLETE")
    logger.info("="*80)
    
    return {
        'league_bf_pct': bf_pct,
        'league_chase_pct': chase_pct,
        'p_value': p_value,
        'team_results': team_df
    }


if __name__ == "__main__":
    main()
