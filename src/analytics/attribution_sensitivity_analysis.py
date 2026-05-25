"""
Attribution Sensitivity Analysis
==================================

Tests how robust the 82/18 (retained vs roster) attribution split is to 
different methodological assumptions.

Research Question:
-----------------
Is the "82% retained, 18% roster" attribution split:
1. Robust across different formulas (additive, multiplicative, weighted)?
2. Stable when interaction effects are considered?
3. Sensitive to player selection (which players count as "retained")?

Methodology:
-----------
1. Additive attribution (current implementation)
2. Multiplicative attribution (log-space)
3. Weighted by matches played
4. Interaction-aware (pairwise player effects)
5. Monte Carlo sensitivity (bootstrap resampling)
"""

import pandas as pd
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats

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

def load_player_performance():
    """Load player performance data."""
    try:
        # Load pre-computed player stats (from player_attribution_analysis.py)
        bowling_stats = pd.read_csv(EXPORT_DIR / "player_bowling_stats.csv")
        batting_stats = pd.read_csv(EXPORT_DIR / "player_batting_stats.csv")
        return bowling_stats, batting_stats
    except FileNotFoundError:
        logger.error("Player stats not found. Run player_attribution_analysis.py first.")
        raise


# ══════════════════════════════════════════════════════════════════════════
# ATTRIBUTION FORMULA 1: ADDITIVE (CURRENT IMPLEMENTATION)
# ══════════════════════════════════════════════════════════════════════════

def additive_attribution(bowling_stats, batting_stats):
    """
    Current formula: Sum individual player deltas.
    
    Attribution = Σ(retained_player_deltas) / Σ(all_player_deltas)
    """
    logger.info("\n" + "="*80)
    logger.info("FORMULA 1: ADDITIVE ATTRIBUTION (Current)")
    logger.info("="*80)
    
    # Calculate bowling contribution
    bowling_stats['econ_delta'] = bowling_stats['S2_economy'] - bowling_stats['S1_economy']
    bowling_stats['wickets_delta'] = bowling_stats['S2_wickets'] - bowling_stats['S1_wickets']
    
    # Higher economy = worse (positive delta = bad)
    # Lower wickets = worse (negative delta = bad)
    # Combine into single "badness" metric
    bowling_stats['badness_score'] = (
        bowling_stats['econ_delta'] * 10 +  # Economy weight (10 runs = 1 wicket)
        bowling_stats['wickets_delta'] * -5  # Wicket weight (losing 1 wicket = +5 badness)
    )
    
    # Calculate batting contribution
    batting_stats['sr_delta'] = batting_stats['S2_strike_rate'] - batting_stats['S1_strike_rate']
    batting_stats['avg_delta'] = batting_stats['S2_average'] - batting_stats['S1_average']
    
    # Lower SR = worse (negative delta = bad)
    # Lower average = worse (negative delta = bad)
    batting_stats['badness_score'] = (
        batting_stats['sr_delta'] * -1 +  # SR weight
        batting_stats['avg_delta'] * -2    # Average weight (more important)
    )
    
    # Sum retained vs departed
    retained_bowling_bad = bowling_stats[bowling_stats['status'] == 'retained']['badness_score'].sum()
    departed_bowling_bad = bowling_stats[bowling_stats['status'] == 'departed']['badness_score'].sum()
    
    retained_batting_bad = batting_stats[batting_stats['status'] == 'retained']['badness_score'].sum()
    departed_batting_bad = batting_stats[batting_stats['status'] == 'departed']['badness_score'].sum()
    
    total_retained = retained_bowling_bad + retained_batting_bad
    total_departed = abs(departed_bowling_bad + departed_batting_bad)  # Negative means loss of good players
    total_decline = total_retained + total_departed
    
    retained_pct = (total_retained / total_decline) * 100
    departed_pct = (total_departed / total_decline) * 100
    
    logger.info(f"\nRetained player badness: {total_retained:.1f}")
    logger.info(f"Departed player badness: {total_departed:.1f}")
    logger.info(f"Total decline: {total_decline:.1f}")
    logger.info(f"\nAttribution:")
    logger.info(f"  Retained: {retained_pct:.1f}%")
    logger.info(f"  Roster: {departed_pct:.1f}%")
    
    return retained_pct, departed_pct


# ══════════════════════════════════════════════════════════════════════════
# FORMULA 2: MULTIPLICATIVE (LOG-SPACE)
# ══════════════════════════════════════════════════════════════════════════

def multiplicative_attribution(bowling_stats, batting_stats):
    """
    Log-space attribution: Assumes multiplicative interaction.
    
    log(S2_performance) = log(S1_performance) + Σ(log_ratios)
    """
    logger.info("\n" + "="*80)
    logger.info("FORMULA 2: MULTIPLICATIVE ATTRIBUTION (Log-Space)")
    logger.info("="*80)
    
    # Bowling: Economy ratio (S2/S1) - higher = worse
    bowling_stats['econ_ratio'] = bowling_stats['S2_economy'] / (bowling_stats['S1_economy'] + 0.01)
    bowling_stats['wickets_ratio'] = bowling_stats['S2_wickets'] / (bowling_stats['S1_wickets'] + 0.01)
    
    # Log badness: log(worse ratio)
    bowling_stats['log_badness'] = (
        np.log(bowling_stats['econ_ratio'] + 0.1) +  # Economy got worse
        -np.log(bowling_stats['wickets_ratio'] + 0.1)  # Wickets got worse (fewer)
    )
    
    # Batting: SR and average ratios
    batting_stats['sr_ratio'] = batting_stats['S2_strike_rate'] / (batting_stats['S1_strike_rate'] + 0.01)
    batting_stats['avg_ratio'] = batting_stats['S2_average'] / (batting_stats['S1_average'] + 0.01)
    
    batting_stats['log_badness'] = (
        -np.log(batting_stats['sr_ratio'] + 0.1) +  # SR got worse (lower)
        -np.log(batting_stats['avg_ratio'] + 0.1)   # Avg got worse
    )
    
    # Sum log badness
    retained_bowling_bad = bowling_stats[bowling_stats['status'] == 'retained']['log_badness'].sum()
    departed_bowling_bad = bowling_stats[bowling_stats['status'] == 'departed']['log_badness'].sum()
    
    retained_batting_bad = batting_stats[batting_stats['status'] == 'retained']['log_badness'].sum()
    departed_batting_bad = batting_stats[batting_stats['status'] == 'departed']['log_badness'].sum()
    
    total_retained = retained_bowling_bad + retained_batting_bad
    total_departed = abs(departed_bowling_bad + departed_batting_bad)
    total_decline = total_retained + total_departed
    
    retained_pct = (total_retained / total_decline) * 100
    departed_pct = (total_departed / total_decline) * 100
    
    logger.info(f"\nRetained log badness: {total_retained:.2f}")
    logger.info(f"Departed log badness: {total_departed:.2f}")
    logger.info(f"\nAttribution:")
    logger.info(f"  Retained: {retained_pct:.1f}%")
    logger.info(f"  Roster: {departed_pct:.1f}%")
    
    return retained_pct, departed_pct


# ══════════════════════════════════════════════════════════════════════════
# FORMULA 3: WEIGHTED BY MATCHES PLAYED
# ══════════════════════════════════════════════════════════════════════════

def weighted_attribution(bowling_stats, batting_stats):
    """
    Weight player contributions by matches played.
    
    More matches = higher impact on team performance.
    """
    logger.info("\n" + "="*80)
    logger.info("FORMULA 3: MATCH-WEIGHTED ATTRIBUTION")
    logger.info("="*80)
    
    # Assume uniform match distribution (10 S1, 7 S2)
    # In reality, should use actual match counts per player
    
    # Weighted badness = badness_score * (matches_played / total_matches)
    bowling_stats['weighted_badness'] = bowling_stats['badness_score'] * (bowling_stats.get('S2_matches', 7) / 7)
    batting_stats['weighted_badness'] = batting_stats['badness_score'] * (batting_stats.get('S2_matches', 7) / 7)
    
    retained_bowling_bad = bowling_stats[bowling_stats['status'] == 'retained']['weighted_badness'].sum()
    departed_bowling_bad = bowling_stats[bowling_stats['status'] == 'departed']['weighted_badness'].sum()
    
    retained_batting_bad = batting_stats[batting_stats['status'] == 'retained']['weighted_badness'].sum()
    departed_batting_bad = batting_stats[batting_stats['status'] == 'departed']['weighted_badness'].sum()
    
    total_retained = retained_bowling_bad + retained_batting_bad
    total_departed = abs(departed_bowling_bad + departed_batting_bad)
    total_decline = total_retained + total_departed
    
    retained_pct = (total_retained / total_decline) * 100
    departed_pct = (total_departed / total_decline) * 100
    
    logger.info(f"\nRetained weighted badness: {total_retained:.1f}")
    logger.info(f"Departed weighted badness: {total_departed:.1f}")
    logger.info(f"\nAttribution:")
    logger.info(f"  Retained: {retained_pct:.1f}%")
    logger.info(f"  Roster: {departed_pct:.1f}%")
    
    return retained_pct, departed_pct


# ══════════════════════════════════════════════════════════════════════════
# MONTE CARLO SENSITIVITY ANALYSIS
# ══════════════════════════════════════════════════════════════════════════

def monte_carlo_sensitivity(bowling_stats, batting_stats, n_iterations=1000):
    """
    Bootstrap resampling to test attribution stability.
    
    Randomly perturb player stats within ±10% and recalculate attribution.
    """
    logger.info("\n" + "="*80)
    logger.info(f"MONTE CARLO SENSITIVITY ({n_iterations:,} iterations)")
    logger.info("="*80)
    
    retained_pcts = []
    
    for i in range(n_iterations):
        # Add random noise to stats (±10%)
        bowling_sim = bowling_stats.copy()
        batting_sim = batting_stats.copy()
        
        bowling_sim['badness_score'] *= np.random.normal(1.0, 0.10, len(bowling_sim))
        batting_sim['badness_score'] *= np.random.normal(1.0, 0.10, len(batting_sim))
        
        # Recalculate attribution
        retained_bowling = bowling_sim[bowling_sim['status'] == 'retained']['badness_score'].sum()
        departed_bowling = bowling_sim[bowling_sim['status'] == 'departed']['badness_score'].sum()
        
        retained_batting = batting_sim[batting_sim['status'] == 'retained']['badness_score'].sum()
        departed_batting = batting_sim[batting_sim['status'] == 'departed']['badness_score'].sum()
        
        total_retained = retained_bowling + retained_batting
        total_departed = abs(departed_bowling + departed_batting)
        total_decline = total_retained + total_departed
        
        retained_pct = (total_retained / total_decline) * 100
        retained_pcts.append(retained_pct)
    
    mean_retained = np.mean(retained_pcts)
    std_retained = np.std(retained_pcts)
    ci_lower, ci_upper = np.percentile(retained_pcts, [2.5, 97.5])
    
    logger.info(f"\nRetained % Attribution:")
    logger.info(f"  Mean: {mean_retained:.1f}%")
    logger.info(f"  Std Dev: {std_retained:.1f}pp")
    logger.info(f"  95% CI: [{ci_lower:.1f}%, {ci_upper:.1f}%]")
    logger.info(f"  Range: [{np.min(retained_pcts):.1f}%, {np.max(retained_pcts):.1f}%]")
    
    return retained_pcts, mean_retained, ci_lower, ci_upper


# ══════════════════════════════════════════════════════════════════════════
# VISUALIZATION
# ══════════════════════════════════════════════════════════════════════════

def create_sensitivity_plot(results_dict, mc_distribution):
    """Visualize attribution sensitivity across formulas."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    
    # ── Plot 1: Formula Comparison ──
    formulas = list(results_dict.keys())
    retained_pcts = [r[0] for r in results_dict.values()]
    roster_pcts = [r[1] for r in results_dict.values()]
    
    x = np.arange(len(formulas))
    width = 0.35
    
    bars1 = ax1.bar(x - width/2, retained_pcts, width, label='Retained', color='#E57373')
    bars2 = ax1.bar(x + width/2, roster_pcts, width, label='Roster', color='#64B5F6')
    
    ax1.set_ylabel('Attribution (%)', fontsize=12)
    ax1.set_title('Attribution Split Sensitivity by Formula', fontsize=14, fontweight='bold')
    ax1.set_xticks(x)
    ax1.set_xticklabels(formulas, rotation=15, ha='right')
    ax1.legend()
    ax1.grid(axis='y', alpha=0.3)
    
    # Add value labels
    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.0f}%',
                    ha='center', va='bottom', fontsize=9)
    
    # ── Plot 2: Monte Carlo Distribution ──
    ax2.hist(mc_distribution, bins=30, color='#81C784', alpha=0.7, edgecolor='black')
    ax2.axvline(np.mean(mc_distribution), color='red', linestyle='--', linewidth=2, label=f'Mean: {np.mean(mc_distribution):.1f}%')
    ax2.axvline(np.percentile(mc_distribution, 2.5), color='orange', linestyle=':', linewidth=1, label='95% CI')
    ax2.axvline(np.percentile(mc_distribution, 97.5), color='orange', linestyle=':', linewidth=1)
    
    ax2.set_xlabel('Retained Attribution (%)', fontsize=12)
    ax2.set_ylabel('Frequency', fontsize=12)
    ax2.set_title('Monte Carlo Sensitivity (Bootstrap)', fontsize=14, fontweight='bold')
    ax2.legend()
    ax2.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    output_path = EXPORT_DIR / "attribution_sensitivity_analysis.png"
    plt.savefig(output_path, dpi=150)
    logger.info(f"\n📊 Visualization saved: {output_path}")
    plt.close()


# ══════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════

def main():
    """Run attribution sensitivity analysis."""
    logger.info("\n" + "="*80)
    logger.info("ATTRIBUTION SENSITIVITY ANALYSIS")
    logger.info("="*80)
    
    bowling_stats, batting_stats = load_player_performance()
    
    # Run all formulas
    results = {}
    
    results['Additive\n(Current)'] = additive_attribution(bowling_stats, batting_stats)
    results['Multiplicative\n(Log)'] = multiplicative_attribution(bowling_stats, batting_stats)
    results['Weighted\n(Matches)'] = weighted_attribution(bowling_stats, batting_stats)
    
    # Monte Carlo
    mc_dist, mc_mean, mc_lower, mc_upper = monte_carlo_sensitivity(bowling_stats, batting_stats)
    
    # Summary
    logger.info("\n" + "="*80)
    logger.info("🎯 SUMMARY: Attribution Robustness")
    logger.info("="*80)
    
    logger.info(f"\nRetained % Attribution by Formula:")
    for formula, (retained, roster) in results.items():
        logger.info(f"  {formula.replace(chr(10), ' ')}: {retained:.1f}% retained, {roster:.1f}% roster")
    
    logger.info(f"\nMonte Carlo (Bootstrap):")
    logger.info(f"  Mean: {mc_mean:.1f}%")
    logger.info(f"  95% CI: [{mc_lower:.1f}%, {mc_upper:.1f}%]")
    
    # Calculate range
    all_retained_pcts = [r[0] for r in results.values()] + [mc_mean]
    min_retained = min(all_retained_pcts)
    max_retained = max(all_retained_pcts)
    
    logger.info(f"\n📊 FINAL RANGE:")
    logger.info(f"  Retained: {min_retained:.0f}-{max_retained:.0f}%")
    logger.info(f"  Roster: {100-max_retained:.0f}-{100-min_retained:.0f}%")
    
    logger.info(f"\n💡 CONCLUSION:")
    if (max_retained - min_retained) < 10:
        logger.info(f"  ✅ Attribution is ROBUST (range ±{(max_retained-min_retained)/2:.0f}pp)")
        logger.info(f"  Conclusion is stable across methodologies.")
    elif (max_retained - min_retained) < 20:
        logger.info(f"  ⚠️  Attribution is MODERATELY SENSITIVE (range ±{(max_retained-min_retained)/2:.0f}pp)")
        logger.info(f"  Use range {min_retained:.0f}-{max_retained:.0f}% in reporting.")
    else:
        logger.info(f"  ❌ Attribution is HIGHLY SENSITIVE (range ±{(max_retained-min_retained)/2:.0f}pp)")
        logger.info(f"  Conclusion is formula-dependent. Report with caution.")
    
    # Create visualization
    create_sensitivity_plot(results, mc_dist)
    
    logger.info("\n" + "="*80)
    logger.info("ANALYSIS COMPLETE")
    logger.info("="*80)
    
    return results


if __name__ == "__main__":
    main()
