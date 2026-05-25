"""
Statistical Validation: Regression to Mean Analysis
====================================================

Tests whether Janakpur Bolts' S1→S2 decline can be explained by regression 
to the mean vs structural performance decline.

Research Question:
-----------------
Is the 70%→14% win rate decline due to:
1. Bad luck (regression from over-performance in S1)?
2. Structural decline (genuine performance deterioration)?

Methodology:
-----------
1. Binomial test: P(win rate ≤ 14% | true skill = X%)
2. Compare S2 observed (14%) vs expected (regression to league mean)
3. Calculate effect size and statistical significance
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
    """Load NPL match data."""
    matches = pd.read_parquet(NORMALIZED_DIR / "matches_normalized.parquet")
    return matches

# ══════════════════════════════════════════════════════════════════════════
# REGRESSION TO MEAN ANALYSIS
# ══════════════════════════════════════════════════════════════════════════

def calculate_league_average_win_rate(matches):
    """Calculate league-wide average win rate (should be ~50%)."""
    # Each match has 1 winner, so total wins = total matches
    # Each team plays ~7-10 matches per season
    
    team_records = []
    for season in ['S1', 'S2']:
        season_matches = matches[matches['season'] == season]
        teams = set(season_matches['team_1_name'].unique()) | set(season_matches['team_2_name'].unique())
        
        for team in teams:
            team_matches = season_matches[
                (season_matches['team_1_name'] == team) | (season_matches['team_2_name'] == team)
            ]
            wins = len(team_matches[team_matches['winner_name'] == team])
            total = len(team_matches)
            
            if total > 0:
                team_records.append({
                    'season': season,
                    'team': team,
                    'wins': wins,
                    'total': total,
                    'win_pct': (wins / total) * 100
                })
    
    records_df = pd.DataFrame(team_records)
    league_avg = records_df['win_pct'].mean()
    
    logger.info(f"\nLeague-wide Win Rate Distribution:")
    logger.info(f"  Mean: {league_avg:.1f}%")
    logger.info(f"  Median: {records_df['win_pct'].median():.1f}%")
    logger.info(f"  Std Dev: {records_df['win_pct'].std():.1f}pp")
    logger.info(f"  Min: {records_df['win_pct'].min():.1f}%")
    logger.info(f"  Max: {records_df['win_pct'].max():.1f}%")
    
    return league_avg, records_df


def binomial_test_win_rate(n_matches, n_wins, true_skill):
    """
    Test: P(observed wins or fewer | true skill)
    
    If p < 0.05, observed win rate is significantly LOWER than true skill.
    """
    # Cumulative probability of n_wins or fewer
    p_value = stats.binom.cdf(n_wins, n_matches, true_skill)
    
    return p_value


def regression_to_mean_analysis(matches):
    """Main regression-to-mean analysis."""
    logger.info("="*80)
    logger.info("REGRESSION TO MEAN ANALYSIS")
    logger.info("="*80)
    
    # Get Janakpur Bolts data
    TEAM = "Janakpur Bolts"
    jab_matches = matches[
        (matches['team_1_name'] == TEAM) | (matches['team_2_name'] == TEAM)
    ]
    
    s1_matches = jab_matches[jab_matches['season'] == 'S1']
    s2_matches = jab_matches[jab_matches['season'] == 'S2']
    
    s1_wins = len(s1_matches[s1_matches['winner_name'] == TEAM])
    s2_wins = len(s2_matches[s2_matches['winner_name'] == TEAM])
    
    s1_total = len(s1_matches)
    s2_total = len(s2_matches)
    
    s1_pct = (s1_wins / s1_total) * 100
    s2_pct = (s2_wins / s2_total) * 100
    
    logger.info(f"\n{TEAM} Win Rates:")
    logger.info(f"  S1: {s1_wins}/{s1_total} ({s1_pct:.1f}%)")
    logger.info(f"  S2: {s2_wins}/{s2_total} ({s2_pct:.1f}%)")
    logger.info(f"  Delta: {s2_pct - s1_pct:.1f}pp")
    
    # Get league average
    league_avg, records_df = calculate_league_average_win_rate(matches)
    
    # ── Test 1: Is S2 significantly worse than league average (50%)? ──
    logger.info("\n" + "="*80)
    logger.info("TEST 1: S2 vs League Average (50%)")
    logger.info("="*80)
    
    p_value_50 = binomial_test_win_rate(s2_total, s2_wins, 0.50)
    
    logger.info(f"\nHypothesis: True skill = 50% (league average)")
    logger.info(f"Observed S2: {s2_pct:.1f}% ({s2_wins}/{s2_total})")
    logger.info(f"P(win rate ≤ {s2_pct:.1f}% | true skill = 50%) = {p_value_50:.4f}")
    
    if p_value_50 < 0.05:
        logger.info(f"✅ SIGNIFICANT (p < 0.05): S2 performance is WORSE than random chance")
        logger.info(f"   Evidence of structural decline beyond regression to mean.")
    elif p_value_50 < 0.10:
        logger.info(f"⚠️  MARGINALLY SIGNIFICANT (p < 0.10): Suggestive evidence")
        logger.info(f"   S2 is worse than expected, but not conclusive (small sample).")
    else:
        logger.info(f"❌ NOT SIGNIFICANT (p ≥ 0.10): S2 could be bad luck")
        logger.info(f"   Insufficient evidence of structural decline.")
    
    # ── Test 2: Is S1 significantly better than league average? ──
    logger.info("\n" + "="*80)
    logger.info("TEST 2: S1 vs League Average (50%)")
    logger.info("="*80)
    
    # For upper tail, use 1 - CDF for P(wins ≥ observed)
    p_value_s1_upper = 1 - stats.binom.cdf(s1_wins - 1, s1_total, 0.50)
    
    logger.info(f"\nHypothesis: True skill = 50%")
    logger.info(f"Observed S1: {s1_pct:.1f}% ({s1_wins}/{s1_total})")
    logger.info(f"P(win rate ≥ {s1_pct:.1f}% | true skill = 50%) = {p_value_s1_upper:.4f}")
    
    if p_value_s1_upper < 0.05:
        logger.info(f"✅ SIGNIFICANT (p < 0.05): S1 was LUCKY (over-performed)")
        logger.info(f"   Expected regression to 50% in S2.")
    else:
        logger.info(f"❌ NOT SIGNIFICANT: S1 within normal variance of 50% true skill")
    
    # ── Test 3: Expected S2 with regression to mean ──
    logger.info("\n" + "="*80)
    logger.info("TEST 3: Expected S2 Win Rate (Regression to Mean)")
    logger.info("="*80)
    
    # ═══════════════════════════════════════════════════════════════════════
    # REGRESSION TO MEAN FORMULA (TRANSPARENT DOCUMENTATION)
    # ═══════════════════════════════════════════════════════════════════════
    #
    # Formula: E(S2) = league_mean + α * (S1 - league_mean)
    #
    # Where:
    #   E(S2) = Expected S2 win rate (after regression to mean)
    #   league_mean = League-wide average win rate (~50% in balanced league)
    #   S1 = Observed S1 win rate
    #   α = Regression coefficient (reliability, signal-to-noise ratio)
    #
    # Regression Coefficient (α) Interpretation:
    #   α = 0.0 → Pure luck (S1 = random, expect full regression to 50%)
    #   α = 0.3 → Strong regression (assume 70% luck, 30% skill)
    #   α = 0.5 → Medium regression (assume 50% luck, 50% skill) ← DEFAULT
    #   α = 0.7 → Weak regression (assume 30% luck, 70% skill)
    #   α = 1.0 → No regression (S1 = true skill, no luck component)
    #
    # Why α = 0.5 as default?
    #   - Small sample size (n=10 S1 matches) → High variance
    #   - T20 cricket research (IPL/BBL) suggests reliability 0.4-0.6 for 7-10 match samples
    #   - Medium assumption is conservative middle ground
    #
    # Decomposition:
    #   Total decline = S1 - S2 = (S1 - E(S2)) + (E(S2) - S2)
    #                           = [Luck component] + [Structural component]
    #
    # Example with JAB data:
    #   S1 = 70%, league_mean = 50%, α = 0.5
    #   E(S2) = 50 + 0.5 * (70 - 50) = 50 + 10 = 60%
    #   
    #   If observed S2 = 14%:
    #     Luck component = 70 - 60 = 10pp (S1 over-performance)
    #     Structural component = 14 - 60 = -46pp (genuine decline)
    #     Total = 14 - 70 = -56pp
    #
    # Sensitivity Analysis:
    #   We test α = 0.3, 0.5, 0.7 to show robustness
    # ═══════════════════════════════════════════════════════════════════════
    
    # With small sample (n=10, n=7), expect strong regression (α = 0.3-0.5)
    alpha_strong = 0.3  # Strong regression (high luck assumption)
    alpha_medium = 0.5  # Medium regression (50/50 luck/skill) ← PRIMARY
    alpha_weak = 0.7    # Weak regression (high skill assumption)
    
    expected_s2_strong = league_avg + alpha_strong * (s1_pct - league_avg)
    expected_s2_medium = league_avg + alpha_medium * (s1_pct - league_avg)
    expected_s2_weak = league_avg + alpha_weak * (s1_pct - league_avg)
    
    logger.info(f"\nS1 observed: {s1_pct:.1f}%")
    logger.info(f"League mean: {league_avg:.1f}%")
    logger.info(f"\nExpected S2 (regression to mean):")
    logger.info(f"  Strong regression (α=0.3): {expected_s2_strong:.1f}%")
    logger.info(f"  Medium regression (α=0.5): {expected_s2_medium:.1f}%")
    logger.info(f"  Weak regression (α=0.7): {expected_s2_weak:.1f}%")
    logger.info(f"\nObserved S2: {s2_pct:.1f}%")
    logger.info(f"Difference from expected (medium regression): {s2_pct - expected_s2_medium:.1f}pp")
    
    # Test if S2 is significantly lower than expected (medium regression)
    expected_wins_medium = int(round(expected_s2_medium / 100 * s2_total))
    p_value_regression = binomial_test_win_rate(s2_total, s2_wins, expected_s2_medium / 100)
    
    logger.info(f"\nBinomial test: P(S2 ≤ {s2_pct:.1f}% | expected = {expected_s2_medium:.1f}%) = {p_value_regression:.4f}")
    
    if p_value_regression < 0.05:
        logger.info(f"✅ SIGNIFICANT: S2 is WORSE than regression-to-mean prediction")
        logger.info(f"   Evidence of structural decline beyond luck.")
    elif p_value_regression < 0.10:
        logger.info(f"⚠️  MARGINALLY SIGNIFICANT: Suggestive evidence")
    else:
        logger.info(f"❌ NOT SIGNIFICANT: S2 within normal regression variance")
    
    # ── Summary ──
    logger.info("\n" + "="*80)
    logger.info("🎯 SUMMARY: Regression to Mean vs Structural Decline")
    logger.info("="*80)
    
    logger.info(f"\n1. S1 Win Rate ({s1_pct:.1f}%):")
    if p_value_s1_upper < 0.05:
        logger.info(f"   ✅ Significantly above league average (p={p_value_s1_upper:.3f})")
        logger.info(f"   S1 included ~{s1_pct - league_avg:.0f}pp of luck")
    else:
        logger.info(f"   ⚠️  Within normal variance of league average")
    
    logger.info(f"\n2. S2 Win Rate ({s2_pct:.1f}%):")
    logger.info(f"   Expected (regression to mean): {expected_s2_medium:.1f}%")
    logger.info(f"   Observed: {s2_pct:.1f}%")
    logger.info(f"   Gap: {s2_pct - expected_s2_medium:.1f}pp")
    
    if p_value_regression < 0.10:
        logger.info(f"   ✅ Evidence of structural decline (p={p_value_regression:.3f})")
        logger.info(f"   Recommendation: Investigate root causes (phase performance, roster)")
    else:
        logger.info(f"   ⚠️  Could be bad luck + regression (p={p_value_regression:.3f})")
        logger.info(f"   Recommendation: Monitor S3 before major changes")
    
    logger.info(f"\n3. Estimated Luck vs Structural Components:")
    luck_component = s1_pct - expected_s2_medium
    structural_component = expected_s2_medium - s2_pct
    total_decline = s1_pct - s2_pct
    
    logger.info(f"\n   📐 DECOMPOSITION FORMULA (Using α = {alpha_medium}):")
    logger.info(f"      Total decline = S1 - S2 = {s1_pct:.1f} - {s2_pct:.1f} = {total_decline:.1f}pp")
    logger.info(f"      ")
    logger.info(f"      Breakdown:")
    logger.info(f"        Luck component = S1 - E(S2)")
    logger.info(f"                      = {s1_pct:.1f} - {expected_s2_medium:.1f}")
    logger.info(f"                      = {luck_component:.1f}pp ({luck_component/total_decline*100:.0f}% of total)")
    logger.info(f"      ")
    logger.info(f"        Structural component = E(S2) - S2")
    logger.info(f"                            = {expected_s2_medium:.1f} - {s2_pct:.1f}")
    logger.info(f"                            = {structural_component:.1f}pp ({structural_component/total_decline*100:.0f}% of total)")
    logger.info(f"      ")
    logger.info(f"      Verification: {luck_component:.1f} + {structural_component:.1f} = {total_decline:.1f}pp ✓")
    
    # Sensitivity to alpha
    logger.info(f"\n   📊 SENSITIVITY TO REGRESSION COEFFICIENT (α):")
    
    for alpha_val, alpha_name in [(alpha_strong, 'Strong'), (alpha_medium, 'Medium'), (alpha_weak, 'Weak')]:
        exp_s2 = league_avg + alpha_val * (s1_pct - league_avg)
        luck_comp = s1_pct - exp_s2
        struct_comp = exp_s2 - s2_pct
        
        logger.info(f"      α = {alpha_val} ({alpha_name}): Luck = {luck_comp:.0f}pp, Structural = {struct_comp:.0f}pp")
    
    logger.info(f"\n   💡 INTERPRETATION:")
    logger.info(f"      S1's {s1_pct:.0f}% win rate included ~{luck_component:.0f}pp of luck (over-performance)")
    logger.info(f"      Expected S2 with regression: ~{expected_s2_medium:.0f}%")
    logger.info(f"      Observed S2: {s2_pct:.0f}%")
    logger.info(f"      → Structural decline of ~{structural_component:.0f}pp beyond luck reversal")
    
    # Create visualization
    create_regression_plot(s1_pct, s2_pct, expected_s2_medium, league_avg)
    
    return {
        's1_pct': s1_pct,
        's2_pct': s2_pct,
        'league_avg': league_avg,
        'expected_s2': expected_s2_medium,
        'p_value_s2_vs_50': p_value_50,
        'p_value_s2_vs_expected': p_value_regression,
        'luck_component_pp': luck_component,
        'structural_component_pp': structural_component
    }


def create_regression_plot(s1_pct, s2_pct, expected_s2, league_avg):
    """Visualize regression to mean."""
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Plot points
    ax.scatter([1], [s1_pct], s=200, color='green', label=f'S1 Observed ({s1_pct:.1f}%)', zorder=3)
    ax.scatter([2], [s2_pct], s=200, color='red', label=f'S2 Observed ({s2_pct:.1f}%)', zorder=3)
    ax.scatter([2], [expected_s2], s=200, color='orange', marker='s', 
               label=f'S2 Expected (Regression: {expected_s2:.1f}%)', zorder=3)
    
    # Plot regression line
    ax.plot([1, 2], [s1_pct, expected_s2], 'o--', color='orange', linewidth=2, 
            label='Expected Regression Path', zorder=2)
    
    # Plot actual line
    ax.plot([1, 2], [s1_pct, s2_pct], 'o-', color='darkred', linewidth=2, 
            label='Actual Performance', zorder=2)
    
    # League average line
    ax.axhline(league_avg, color='gray', linestyle='--', linewidth=1, label=f'League Average ({league_avg:.1f}%)')
    
    # Annotations
    ax.text(1, s1_pct + 3, 'S1: Lucky?', ha='center', fontsize=10, color='green')
    ax.text(2, expected_s2 + 3, 'Expected\n(Regression)', ha='center', fontsize=9, color='orange')
    ax.text(2, s2_pct - 3, 'S2: Structural\nDecline?', ha='center', fontsize=9, color='red')
    
    ax.set_xlim(0.5, 2.5)
    ax.set_ylim(0, 100)
    ax.set_xticks([1, 2])
    ax.set_xticklabels(['Season 1', 'Season 2'])
    ax.set_ylabel('Win Rate (%)', fontsize=12)
    ax.set_title('Janakpur Bolts: Regression to Mean Analysis', fontsize=14, fontweight='bold')
    ax.legend(loc='upper right', fontsize=10)
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    output_path = EXPORT_DIR / "regression_to_mean_analysis.png"
    plt.savefig(output_path, dpi=150)
    logger.info(f"\n📊 Visualization saved: {output_path}")
    plt.close()


# ══════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════

def main():
    """Run regression to mean analysis."""
    logger.info("\n" + "="*80)
    logger.info("STATISTICAL VALIDATION: REGRESSION TO MEAN")
    logger.info("="*80)
    
    matches = load_npl_matches()
    results = regression_to_mean_analysis(matches)
    
    logger.info("\n" + "="*80)
    logger.info("ANALYSIS COMPLETE")
    logger.info("="*80)
    logger.info(f"Results exported to: {EXPORT_DIR}")
    
    return results


if __name__ == "__main__":
    main()
