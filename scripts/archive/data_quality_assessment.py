"""
Data Quality Assessment & Model Critique
Critical evaluation of S3 Performance Forecaster outputs
"""

import pandas as pd
import numpy as np

# Load forecasts
bowlers = pd.read_csv('data/exports/s3_bowler_forecast.csv')
batters = pd.read_csv('data/exports/s3_batter_forecast.csv')

print('=' * 80)
print('DATA SCIENTIST SELF-CRITIQUE: S3 PERFORMANCE FORECASTER')
print('=' * 80)

# ============================================================================
# 1. DATA QUALITY ASSESSMENT
# ============================================================================
print('\n### 1. DATA QUALITY ISSUES ###\n')

print(f'Bowlers: {len(bowlers)} total')
insufficient_bowlers = len(bowlers[bowlers['economy_trend'] == 'INSUFFICIENT_DATA'])
print(f'  - INSUFFICIENT_DATA: {insufficient_bowlers} ({insufficient_bowlers/len(bowlers)*100:.1f}%)')
print(f'  - Priority 8 (TARGET): {len(bowlers[bowlers["priority"] == 8])}')
print(f'  - Priority 5 (RETAIN): {len(bowlers[bowlers["priority"] == 5])}')
print(f'  - Priority 2 (CAUTION): {len(bowlers[bowlers["priority"] == 2])}')

print(f'\nBatters: {len(batters)} total')
insufficient_batters = len(batters[batters['runs_trend'] == 'INSUFFICIENT_DATA'])
print(f'  - INSUFFICIENT_DATA: {insufficient_batters} ({insufficient_batters/len(batters)*100:.1f}%)')
print(f'  - Priority 8 (TARGET): {len(batters[batters["priority"] == 8])}')
print(f'  - Priority 5 (RETAIN): {len(batters[batters["priority"] == 5])}')
print(f'  - Priority 2 (CAUTION): {len(batters[batters["priority"] == 2])}')

# ============================================================================
# 2. CRITICAL FLAW: COMPOSITE SCORING MISSING
# ============================================================================
print('\n### 2. CRITICAL FLAW: NO COMPOSITE SCORING ###\n')

print('Bowlers with IMPROVING wickets + STABLE economy (UNDERVALUED):')
improving_wkts = bowlers[
    (bowlers['wickets_trend'] == 'IMPROVING') & 
    (bowlers['economy_trend'] == 'STABLE')
]
if len(improving_wkts) > 0:
    print(improving_wkts[['player_name', 's1_wickets', 's2_wickets', 's3_wickets_pred', 
                           's1_economy', 's2_economy', 'priority', 'max_bid']].to_string(index=False))
    print(f'\n⚠️ ISSUE: {len(improving_wkts)} bowlers with improving wickets get Priority 5, not 8!')
    print('   These are BETTER than stable performers but model treats them equally.')
else:
    print('None found')

# ============================================================================
# 3. SAMPLE SIZE ISSUES
# ============================================================================
print('\n### 3. SAMPLE SIZE ISSUES ###\n')

# Batters with very low runs (unreliable trends)
small_sample = batters[
    ((batters['s1_runs'] < 50) | (batters['s2_runs'] < 50)) & 
    (batters['runs_trend'] == 'IMPROVING')
].dropna(subset=['s1_runs', 's2_runs'])

print(f'Batters with <50 runs in S1 or S2 marked as "IMPROVING" (HIGH RISK):')
print(f'Found: {len(small_sample)} players\n')
if len(small_sample) > 0:
    print(small_sample[['player_name', 's1_runs', 's2_runs', 's3_runs_pred', 
                        'priority', 'max_bid']].to_string(index=False))
    print('\n⚠️ ISSUE: Small sample sizes create unreliable trend predictions.')
    print('   Example: 14 runs → 47 runs looks "IMPROVING" but too few balls to be confident.')

# Batters who never batted
zero_runs = batters[(batters['s1_runs'] == 0) | (batters['s2_runs'] == 0)].dropna(subset=['s1_runs', 's2_runs'])
print(f'\nBatters with 0 runs in any season: {len(zero_runs)}')
if len(zero_runs) > 0:
    print(zero_runs[['player_name', 's1_runs', 's2_runs', 'recommendation']].head(5).to_string(index=False))

# ============================================================================
# 4. SHER MALLA CASE STUDY: WHY MODEL UNDERVALUES
# ============================================================================
print('\n### 4. CASE STUDY: SHER MALLA (S MALLA) UNDERVALUATION ###\n')

sher_malla = bowlers[bowlers['player_name'] == 'S Malla']
if len(sher_malla) > 0:
    sm = sher_malla.iloc[0]
    print(f"S Malla (Sher Malla):")
    print(f"  Economy: S1 {sm['s1_economy']:.2f} → S2 {sm['s2_economy']:.2f} → S3 {sm['s3_economy_pred']:.2f}")
    print(f"  Economy Trend: {sm['economy_trend']}")
    print(f"  Wickets: S1 {sm['s1_wickets']:.0f} → S2 {sm['s2_wickets']:.0f} → S3 {sm['s3_wickets_pred']:.1f}")
    print(f"  Wickets Trend: {sm['wickets_trend']}")
    print(f"  Model Priority: {sm['priority']} - {sm['recommendation']}")
    print(f"  Model Bid: {sm['max_bid']}")
    print(f"\n⚠️ ISSUE: Wickets DOUBLED (7→17) but model gives Priority 5!")
    print("   WHY: Model treats economy and wickets separately.")
    print("   FIX: Need composite 'bowler_value_score' = f(economy_trend, wickets_trend)")
    print("   CORRECT VALUE: Priority 8-10, ₨20-22 lakh (joint #1 wicket-taker)")

# ============================================================================
# 5. STRIKE RATE ANOMALIES
# ============================================================================
print('\n### 5. STRIKE RATE ANOMALIES ###\n')

# Extreme SR changes
batters['sr_change'] = batters['s2_strike_rate'] - batters['s1_strike_rate']
extreme_sr = batters[
    (abs(batters['sr_change']) > 50) & 
    (batters['runs_trend'] != 'INSUFFICIENT_DATA')
].sort_values('sr_change', ascending=False)

print('Batters with >50 strike rate change (potential small sample issues):')
if len(extreme_sr) > 0:
    print(extreme_sr[['player_name', 's1_runs', 's1_strike_rate', 's2_runs', 
                      's2_strike_rate', 'sr_change', 'priority']].head(10).to_string(index=False))
    print('\n⚠️ ISSUE: Extreme SR changes often indicate small sample size, not true skill.')

# ============================================================================
# 6. INSUFFICIENT_DATA PROBLEM
# ============================================================================
print('\n### 6. INSUFFICIENT_DATA HANDLING FLAW ###\n')

print(f'Total players with INSUFFICIENT_DATA: {insufficient_bowlers + insufficient_batters}')
print(f'All get: Priority 5, RETAIN/SIGN, ₨10-15 lakh')
print('\n⚠️ ISSUE: One-season players get same recommendation as proven stable performers!')
print('   FIX: Should have:')
print('   - Lower priority (3-4)')
print('   - Lower confidence intervals (±40-50%)')
print('   - "UNPROVEN" recommendation tier')
print('   - Max bid: ₨5-8 lakh (not ₨10-15 lakh)')

# ============================================================================
# 7. MODEL STRENGTHS (WHAT WORKS WELL)
# ============================================================================
print('\n### 7. MODEL STRENGTHS (WHAT WORKS WELL) ###\n')

print('✅ Correctly identified declining players:')
declining = bowlers[bowlers['economy_trend'] == 'DECLINING']
print(declining[['player_name', 's1_economy', 's2_economy', 's3_economy_pred', 'recommendation']].to_string(index=False))

print('\n✅ Correctly identified improving batters:')
improving_batters = batters[batters['runs_trend'] == 'IMPROVING'].head(5)
print(improving_batters[['player_name', 's1_runs', 's2_runs', 's3_runs_pred', 'runs_delta']].to_string(index=False))

# ============================================================================
# 8. STATISTICAL RIGOR MISSING
# ============================================================================
print('\n### 8. MISSING STATISTICAL RIGOR ###\n')

print('❌ No validation metrics:')
print('  - No R² or RMSE for predictions')
print('  - No backtesting (S2 predictions from S1 vs actual S2)')
print('  - No confidence interval validation')
print('  - No significance testing (is trend statistically significant?)')
print('\n❌ No feature correlations:')
print('  - Does economy correlate with wickets?')
print('  - Does strike rate correlate with runs?')
print('  - Are trends consistent across roles?')
print('\n❌ No uncertainty quantification:')
print('  - Sample size not factored into confidence')
print('  - No Bayesian priors for regression to mean')

# ============================================================================
# 9. RECOMMENDED IMPROVEMENTS
# ============================================================================
print('\n### 9. RECOMMENDED IMPROVEMENTS (PRIORITY ORDER) ###\n')

print('1. **ADD COMPOSITE SCORING** (HIGHEST PRIORITY)')
print('   Create bowler_value = weighted_sum(economy_trend, wickets_trend, SR_trend)')
print('   Weight wickets 60%, economy 40% for T20')
print('   Re-prioritize Sher Malla, A Bohara, Shahab Alam')
print('')
print('2. **FIX INSUFFICIENT_DATA HANDLING**')
print('   - Separate tier: "UNPROVEN" (not RETAIN/SIGN)')
print('   - Lower max bids: ₨5-8 lakh (not ₨10-15 lakh)')
print('   - Wider confidence intervals: ±50%')
print('')
print('3. **ADD SAMPLE SIZE FILTERS**')
print('   - Minimum threshold: 50 balls faced (batters), 10 overs bowled (bowlers)')
print('   - Flag "SMALL_SAMPLE" if below threshold')
print('   - Reduce priority by 2 levels for small samples')
print('')
print('4. **BACKTEST THE MODEL**')
print('   - Predict S2 from S1, compare to actual S2')
print('   - Calculate RMSE for economy, runs, SR predictions')
print('   - Validate confidence intervals (do 80% fall within range?)')
print('')
print('5. **ADD ROLE-BASED ADJUSTMENTS**')
print('   - Death bowler with 6.5 economy = excellent (Priority +2)')
print('   - Powerplay bowler with 6.5 economy = average (Priority +0)')
print('   - Finisher with 150 SR = excellent (Priority +2)')
print('   - Anchor with 150 SR = good (Priority +1)')

# ============================================================================
# 10. OVERALL MODEL GRADE
# ============================================================================
print('\n### 10. OVERALL MODEL GRADE ###\n')

print('STRENGTHS (Score: 6/10):')
print('  ✅ Simple, interpretable logic')
print('  ✅ Correctly identifies clear trends (improving/declining)')
print('  ✅ Confidence intervals for uncertainty')
print('  ✅ Exported in usable CSV format')
print('')
print('WEAKNESSES (Score: 4/10):')
print('  ❌ No composite scoring (treats metrics independently)')
print('  ❌ Poor handling of INSUFFICIENT_DATA (38% of players!)')
print('  ❌ No sample size adjustments')
print('  ❌ No statistical validation (backtesting, RMSE)')
print('  ❌ Undervalues wicket-taking ability vs economy')
print('  ❌ No role-based adjustments')
print('  ❌ No phase-specific metrics')
print('')
print('OVERALL GRADE: C+ (Functional but needs major improvements)')
print('')
print('PRODUCTION READINESS: 50% - OK for initial screening, NOT for final decisions')
print('')
print('RECOMMENDED ACTION:')
print('  1. Use current forecasts for initial player screening ✅')
print('  2. Apply analyst overrides for key targets (Sher Malla, BKEL Milantha)')
print('  3. Build v2.0 with composite scoring + validation BEFORE auction')
print('  4. Add minimum sample size filters')
print('  5. Backtest on S1→S2 predictions to validate approach')

print('\n' + '=' * 80)
print('END OF SELF-CRITIQUE')
print('=' * 80)
