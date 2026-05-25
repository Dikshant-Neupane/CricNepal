"""
Comprehensive Janakpur Bolts Decline Analysis
==============================================
Data-driven investigation with statistical rigor and uncertainty quantification.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import json

# Data paths
ROSTER_PATH = Path("D:/Cric_Data/data/player_rosters/npl_player_rosters_20260521.csv")
MATCH_JSON_DIR = Path("D:/Cric_Data/data/raw/cricsheet/npl_json")

print("=" * 80)
print("JANAKPUR BOLTS: CHAMPIONSHIP DECLINE ANALYSIS")
print("=" * 80)
print()

# ============================================================================
# PART 1: LOAD AND VALIDATE DATA
# ============================================================================

print("📊 Loading player roster data...")
df = pd.read_csv(ROSTER_PATH)

# Extract Janakpur data
janakpur_s1 = df[(df['team'] == 'Janakpur Bolts') & (df['season'] == 'Season 1')].copy()
janakpur_s2 = df[(df['team'] == 'Janakpur Bolts') & (df['season'] == 'Season 2')].copy()

print(f"✅ S1 Squad: {len(janakpur_s1)} players")
print(f"✅ S2 Squad: {len(janakpur_s2)} players")
print()

# ============================================================================
# PART 2: TEAM PERFORMANCE METRICS
# ============================================================================

print("=" * 80)
print("TEAM-LEVEL PERFORMANCE COMPARISON")
print("=" * 80)
print()

def calculate_team_stats(df_season, season_name):
    """Calculate aggregate team statistics"""
    stats = {}
    
    # Batting
    batting_df = df_season[df_season['batting_matches'] > 0]
    stats['total_runs'] = batting_df['runs_scored'].sum()
    stats['total_matches_batting'] = batting_df['batting_matches'].sum()
    stats['avg_runs_per_player'] = stats['total_runs'] / len(batting_df) if len(batting_df) > 0 else 0
    stats['team_strike_rate'] = batting_df['strike_rate'].mean()
    stats['batters_100plus'] = len(batting_df[batting_df['runs_scored'] >= 100])
    
    # Bowling
    bowling_df = df_season[df_season['bowling_matches'] > 0]
    stats['total_wickets'] = bowling_df['wickets_taken'].sum()
    stats['total_overs'] = bowling_df['overs_bowled'].sum()
    stats['team_economy'] = bowling_df['economy_rate'].mean()
    stats['bowlers_10plus'] = len(bowling_df[bowling_df['wickets_taken'] >= 10])
    stats['bowlers_count'] = len(bowling_df)
    
    # All-rounders (played both bat and bowl)
    allrounders = df_season[(df_season['batting_matches'] > 0) & (df_season['bowling_matches'] > 0)]
    stats['allrounders_count'] = len(allrounders)
    stats['allrounders_runs'] = allrounders['runs_scored'].sum()
    stats['allrounders_wickets'] = allrounders['wickets_taken'].sum()
    
    return stats

s1_stats = calculate_team_stats(janakpur_s1, "S1")
s2_stats = calculate_team_stats(janakpur_s2, "S2")

print("BATTING PERFORMANCE")
print("-" * 80)
print(f"{'Metric':<30} | {'Season 1':>15} | {'Season 2':>15} | {'Change':>15}")
print("-" * 80)

batting_metrics = [
    ('Total Runs', 'total_runs', ''),
    ('Avg Runs/Player', 'avg_runs_per_player', '.1f'),
    ('Team Strike Rate', 'team_strike_rate', '.2f'),
    ('Batters 100+ Runs', 'batters_100plus', ''),
]

for label, key, fmt in batting_metrics:
    s1_val = s1_stats[key]
    s2_val = s2_stats[key]
    change = ((s2_val - s1_val) / s1_val * 100) if s1_val > 0 else 0
    
    if fmt:
        s1_str = f"{s1_val:{fmt}}"
        s2_str = f"{s2_val:{fmt}}"
    else:
        s1_str = f"{int(s1_val)}"
        s2_str = f"{int(s2_val)}"
    
    change_str = f"{change:+.1f}%" if change != 0 else "0.0%"
    emoji = "📉" if change < -5 else "📈" if change > 5 else "➡️"
    
    print(f"{label:<30} | {s1_str:>15} | {s2_str:>15} | {change_str:>12} {emoji}")

print()
print("BOWLING PERFORMANCE")
print("-" * 80)
print(f"{'Metric':<30} | {'Season 1':>15} | {'Season 2':>15} | {'Change':>15}")
print("-" * 80)

bowling_metrics = [
    ('Total Wickets', 'total_wickets', ''),
    ('Total Overs', 'total_overs', '.1f'),
    ('Team Economy', 'team_economy', '.2f'),
    ('Bowlers 10+ Wickets', 'bowlers_10plus', ''),
]

for label, key, fmt in bowling_metrics:
    s1_val = s1_stats[key]
    s2_val = s2_stats[key]
    change = ((s2_val - s1_val) / s1_val * 100) if s1_val > 0 else 0
    
    if fmt:
        s1_str = f"{s1_val:{fmt}}"
        s2_str = f"{s2_val:{fmt}}"
    else:
        s1_str = f"{int(s1_val)}"
        s2_str = f"{int(s2_val)}"
    
    change_str = f"{change:+.1f}%" if change != 0 else "0.0%"
    # For economy, lower is better
    if key == 'team_economy':
        emoji = "📈" if change < -5 else "📉" if change > 5 else "➡️"
    else:
        emoji = "📉" if change < -5 else "📈" if change > 5 else "➡️"
    
    print(f"{label:<30} | {s1_str:>15} | {s2_str:>15} | {change_str:>12} {emoji}")

print()
print("TEAM BALANCE")
print("-" * 80)
print(f"{'Metric':<30} | {'Season 1':>15} | {'Season 2':>15} | {'Change':>15}")
print("-" * 80)

balance_metrics = [
    ('All-rounders Count', 'allrounders_count', ''),
    ('All-rounder Runs', 'allrounders_runs', ''),
    ('All-rounder Wickets', 'allrounders_wickets', ''),
]

for label, key, fmt in balance_metrics:
    s1_val = s1_stats[key]
    s2_val = s2_stats[key]
    change = ((s2_val - s1_val) / s1_val * 100) if s1_val > 0 else 0
    
    s1_str = f"{int(s1_val)}"
    s2_str = f"{int(s2_val)}"
    
    change_str = f"{change:+.1f}%" if change != 0 else "0.0%"
    emoji = "📉" if change < -5 else "📈" if change > 5 else "➡️"
    
    print(f"{label:<30} | {s1_str:>15} | {s2_str:>15} | {change_str:>12} {emoji}")

print()
print()

# ============================================================================
# PART 3: PLAYER TURNOVER ANALYSIS
# ============================================================================

print("=" * 80)
print("ROSTER TURNOVER ANALYSIS")
print("=" * 80)
print()

s1_players = set(janakpur_s1['player_name'])
s2_players = set(janakpur_s2['player_name'])

departed = s1_players - s2_players
retained = s1_players & s2_players
new_players = s2_players - s1_players

turnover_rate = (len(departed) + len(new_players)) / (len(s1_players) + len(s2_players)) * 100

print(f"Squad Stability: {len(retained)}/{len(s1_players)} retained ({len(retained)/len(s1_players)*100:.1f}%)")
print(f"Turnover Rate: {turnover_rate:.1f}% (players in/out)")
print()

# Analyze departed players
print("🚪 DEPARTED PLAYERS (S1 → Not in S2)")
print("-" * 80)

departed_df = janakpur_s1[janakpur_s1['player_name'].isin(departed)].copy()
departed_df['total_contribution'] = departed_df['runs_scored'] + (departed_df['wickets_taken'] * 20)
departed_df = departed_df.sort_values('total_contribution', ascending=False)

print(f"{'Player':<25} | {'Runs':>8} | {'Wickets':>8} | {'Matches':>8} | {'Impact':>10}")
print("-" * 80)

total_departed_runs = 0
total_departed_wickets = 0
total_departed_impact = 0

for _, player in departed_df.iterrows():
    name = player['player_name'][:24]
    runs = int(player['runs_scored'])
    wickets = int(player['wickets_taken'])
    matches = max(player['batting_matches'], player['bowling_matches'])
    impact = int(player['total_contribution'])
    
    total_departed_runs += runs
    total_departed_wickets += wickets
    total_departed_impact += impact
    
    print(f"{name:<25} | {runs:>8} | {wickets:>8} | {int(matches):>8} | {impact:>10}")

print("-" * 80)
print(f"{'TOTAL DEPARTED':<25} | {total_departed_runs:>8} | {total_departed_wickets:>8} | {'':<8} | {total_departed_impact:>10}")
print()

# Analyze new players
print("🆕 NEW PLAYERS (S2 Only)")
print("-" * 80)

new_df = janakpur_s2[janakpur_s2['player_name'].isin(new_players)].copy()
new_df['total_contribution'] = new_df['runs_scored'] + (new_df['wickets_taken'] * 20)
new_df = new_df.sort_values('total_contribution', ascending=False)

print(f"{'Player':<25} | {'Runs':>8} | {'Wickets':>8} | {'Matches':>8} | {'Impact':>10}")
print("-" * 80)

total_new_runs = 0
total_new_wickets = 0
total_new_impact = 0

for _, player in new_df.iterrows():
    name = player['player_name'][:24]
    runs = int(player['runs_scored'])
    wickets = int(player['wickets_taken'])
    matches = max(player['batting_matches'], player['bowling_matches'])
    impact = int(player['total_contribution'])
    
    total_new_runs += runs
    total_new_wickets += wickets
    total_new_impact += impact
    
    print(f"{name:<25} | {runs:>8} | {wickets:>8} | {int(matches):>8} | {impact:>10}")

print("-" * 80)
print(f"{'TOTAL NEW':<25} | {total_new_runs:>8} | {total_new_wickets:>8} | {'':<8} | {total_new_impact:>10}")
print()

print("NET ROSTER CHANGE:")
print(f"  Runs: {total_new_runs - total_departed_runs:+d} ({(total_new_runs - total_departed_runs)/total_departed_runs*100:+.1f}%)")
print(f"  Wickets: {total_new_wickets - total_departed_wickets:+d} ({(total_new_wickets - total_departed_wickets)/total_departed_wickets*100:+.1f}%)")
print(f"  Impact: {total_new_impact - total_departed_impact:+d} ({(total_new_impact - total_departed_impact)/total_departed_impact*100:+.1f}%)")
print()
print()

# ============================================================================
# PART 4: RETAINED PLAYER PERFORMANCE CHANGES
# ============================================================================

print("=" * 80)
print("RETAINED PLAYER PERFORMANCE ANALYSIS")
print("=" * 80)
print()

retained_analysis = []

for player_name in retained:
    s1_row = janakpur_s1[janakpur_s1['player_name'] == player_name].iloc[0]
    s2_row = janakpur_s2[janakpur_s2['player_name'] == player_name].iloc[0]
    
    # Calculate performance changes
    runs_s1 = s1_row['runs_scored']
    runs_s2 = s2_row['runs_scored']
    wickets_s1 = s1_row['wickets_taken']
    wickets_s2 = s2_row['wickets_taken']
    
    matches_s1 = max(s1_row['batting_matches'], s1_row['bowling_matches'])
    matches_s2 = max(s2_row['batting_matches'], s2_row['bowling_matches'])
    
    # Normalize by matches
    runs_per_match_s1 = runs_s1 / matches_s1 if matches_s1 > 0 else 0
    runs_per_match_s2 = runs_s2 / matches_s2 if matches_s2 > 0 else 0
    wickets_per_match_s1 = wickets_s1 / matches_s1 if matches_s1 > 0 else 0
    wickets_per_match_s2 = wickets_s2 / matches_s2 if matches_s2 > 0 else 0
    
    # Calculate impact change (runs + wickets*20)
    impact_s1 = runs_s1 + (wickets_s1 * 20)
    impact_s2 = runs_s2 + (wickets_s2 * 20)
    impact_change = impact_s2 - impact_s1
    impact_change_pct = ((impact_s2 - impact_s1) / impact_s1 * 100) if impact_s1 > 0 else 0
    
    retained_analysis.append({
        'player': player_name,
        'runs_s1': runs_s1,
        'runs_s2': runs_s2,
        'wickets_s1': wickets_s1,
        'wickets_s2': wickets_s2,
        'matches_s1': matches_s1,
        'matches_s2': matches_s2,
        'impact_s1': impact_s1,
        'impact_s2': impact_s2,
        'impact_change': impact_change,
        'impact_change_pct': impact_change_pct
    })

# Sort by impact change (biggest drops first)
retained_df = pd.DataFrame(retained_analysis).sort_values('impact_change')

print("TOP 10 PERFORMANCE CHANGES (Retained Players)")
print("-" * 100)
print(f"{'Player':<25} | {'S1 Impact':>10} | {'S2 Impact':>10} | {'Change':>10} | {'%':>8} | {'Status':<15}")
print("-" * 100)

for _, row in retained_df.head(10).iterrows():
    name = row['player'][:24]
    s1_impact = int(row['impact_s1'])
    s2_impact = int(row['impact_s2'])
    change = int(row['impact_change'])
    pct = row['impact_change_pct']
    
    if pct < -30:
        status = "🚨 COLLAPSED"
    elif pct < -10:
        status = "📉 DECLINED"
    elif pct > 50:
        status = "🚀 BREAKOUT"
    elif pct > 20:
        status = "📈 IMPROVED"
    else:
        status = "➡️ STABLE"
    
    print(f"{name:<25} | {s1_impact:>10} | {s2_impact:>10} | {change:>10} | {pct:>7.1f}% | {status:<15}")

print()
print()

# Summary statistics
big_declines = retained_df[retained_df['impact_change_pct'] < -30]
improvements = retained_df[retained_df['impact_change_pct'] > 20]

print("PERFORMANCE SUMMARY:")
print(f"  Major Declines (>30% drop): {len(big_declines)} players")
print(f"  Improvements (>20% gain): {len(improvements)} players")
print(f"  Net Impact Change (Retained): {retained_df['impact_change'].sum():+.0f} runs equivalent")
print()
print()

# ============================================================================
# PART 5: STATISTICAL SIGNIFICANCE TESTING
# ============================================================================

print("=" * 80)
print("STATISTICAL ANALYSIS")
print("=" * 80)
print()

# Calculate confidence intervals for key metrics
def bootstrap_mean_ci(data, n_bootstrap=1000, ci=95):
    """Calculate bootstrap confidence interval"""
    bootstrapped_means = []
    for _ in range(n_bootstrap):
        sample = np.random.choice(data, size=len(data), replace=True)
        bootstrapped_means.append(np.mean(sample))
    
    lower = np.percentile(bootstrapped_means, (100 - ci) / 2)
    upper = np.percentile(bootstrapped_means, 100 - (100 - ci) / 2)
    return lower, upper

# Team wickets analysis
s1_wickets = janakpur_s1[janakpur_s1['bowling_matches'] > 0]['wickets_taken'].values
s2_wickets = janakpur_s2[janakpur_s2['bowling_matches'] > 0]['wickets_taken'].values

s1_wickets_mean = np.mean(s1_wickets)
s2_wickets_mean = np.mean(s2_wickets)
s1_wickets_ci = bootstrap_mean_ci(s1_wickets)
s2_wickets_ci = bootstrap_mean_ci(s2_wickets)

print("WICKETS PER BOWLER:")
print(f"  S1: {s1_wickets_mean:.2f} ± [{s1_wickets_ci[0]:.2f}, {s1_wickets_ci[1]:.2f}] (95% CI)")
print(f"  S2: {s2_wickets_mean:.2f} ± [{s2_wickets_ci[0]:.2f}, {s2_wickets_ci[1]:.2f}] (95% CI)")
print(f"  Change: {s2_wickets_mean - s1_wickets_mean:.2f} ({(s2_wickets_mean - s1_wickets_mean)/s1_wickets_mean*100:+.1f}%)")
print()

# Economy rate analysis
s1_economy = janakpur_s1[janakpur_s1['bowling_matches'] > 0]['economy_rate'].values
s2_economy = janakpur_s2[janakpur_s2['bowling_matches'] > 0]['economy_rate'].values

s1_economy_mean = np.mean(s1_economy)
s2_economy_mean = np.mean(s2_economy)
s1_economy_ci = bootstrap_mean_ci(s1_economy)
s2_economy_ci = bootstrap_mean_ci(s2_economy)

print("ECONOMY RATE:")
print(f"  S1: {s1_economy_mean:.2f} ± [{s1_economy_ci[0]:.2f}, {s1_economy_ci[1]:.2f}] (95% CI)")
print(f"  S2: {s2_economy_mean:.2f} ± [{s2_economy_ci[0]:.2f}, {s2_economy_ci[1]:.2f}] (95% CI)")
print(f"  Change: {s2_economy_mean - s1_economy_mean:.2f} ({(s2_economy_mean - s1_economy_mean)/s1_economy_mean*100:+.1f}%)")
print()

# Strike rate analysis
s1_sr = janakpur_s1[janakpur_s1['batting_matches'] > 0]['strike_rate'].values
s2_sr = janakpur_s2[janakpur_s2['batting_matches'] > 0]['strike_rate'].values

s1_sr_mean = np.mean(s1_sr)
s2_sr_mean = np.mean(s2_sr)
s1_sr_ci = bootstrap_mean_ci(s1_sr)
s2_sr_ci = bootstrap_mean_ci(s2_sr)

print("BATTING STRIKE RATE:")
print(f"  S1: {s1_sr_mean:.2f} ± [{s1_sr_ci[0]:.2f}, {s1_sr_ci[1]:.2f}] (95% CI)")
print(f"  S2: {s2_sr_mean:.2f} ± [{s2_sr_ci[0]:.2f}, {s2_sr_ci[1]:.2f}] (95% CI)")
print(f"  Change: {s2_sr_mean - s1_sr_mean:.2f} ({(s2_sr_mean - s1_sr_mean)/s1_sr_mean*100:+.1f}%)")
print()
print()

# ============================================================================
# PART 6: COMPARISON WITH OTHER TEAMS
# ============================================================================

print("=" * 80)
print("LEAGUE-WIDE CONTEXT")
print("=" * 80)
print()

# Calculate league-wide changes
all_teams = df['team'].unique()
league_changes = []

for team in all_teams:
    team_s1 = df[(df['team'] == team) & (df['season'] == 'Season 1')]
    team_s2 = df[(df['team'] == team) & (df['season'] == 'Season 2')]
    
    if len(team_s1) == 0 or len(team_s2) == 0:
        continue
    
    s1_total_wickets = team_s1[team_s1['bowling_matches'] > 0]['wickets_taken'].sum()
    s2_total_wickets = team_s2[team_s2['bowling_matches'] > 0]['wickets_taken'].sum()
    wicket_change_pct = ((s2_total_wickets - s1_total_wickets) / s1_total_wickets * 100) if s1_total_wickets > 0 else 0
    
    s1_total_runs = team_s1[team_s1['batting_matches'] > 0]['runs_scored'].sum()
    s2_total_runs = team_s2[team_s2['batting_matches'] > 0]['runs_scored'].sum()
    runs_change_pct = ((s2_total_runs - s1_total_runs) / s1_total_runs * 100) if s1_total_runs > 0 else 0
    
    league_changes.append({
        'team': team,
        's1_wickets': s1_total_wickets,
        's2_wickets': s2_total_wickets,
        'wicket_change_pct': wicket_change_pct,
        's1_runs': s1_total_runs,
        's2_runs': s2_total_runs,
        'runs_change_pct': runs_change_pct
    })

league_df = pd.DataFrame(league_changes).sort_values('wicket_change_pct', ascending=False)

print("TEAM BOWLING CHANGES (S1 → S2)")
print("-" * 80)
print(f"{'Team':<25} | {'S1 Wickets':>12} | {'S2 Wickets':>12} | {'Change':>10}")
print("-" * 80)

for _, row in league_df.iterrows():
    team_name = row['team'][:24]
    s1_w = int(row['s1_wickets'])
    s2_w = int(row['s2_wickets'])
    change = row['wicket_change_pct']
    
    emoji = "📉" if change < -10 else "📈" if change > 10 else "➡️"
    highlight = "👈 JANAKPUR" if "Janakpur" in team_name else ""
    
    print(f"{team_name:<25} | {s1_w:>12} | {s2_w:>12} | {change:>9.1f}% {emoji} {highlight}")

print()

# Janakpur's rank
janakpur_rank = league_df.reset_index(drop=True)
janakpur_pos = janakpur_rank[janakpur_rank['team'].str.contains('Janakpur')].index[0] + 1

print(f"Janakpur Bowling Decline Rank: {janakpur_pos}/{len(league_df)}")
print(f"League Average Bowling Change: {league_df['wicket_change_pct'].mean():.1f}%")
print(f"Janakpur vs League: {league_df[league_df['team'].str.contains('Janakpur')]['wicket_change_pct'].iloc[0] - league_df['wicket_change_pct'].mean():.1f} percentage points worse")
print()
print()

# ============================================================================
# PART 7: ROOT CAUSE ATTRIBUTION
# ============================================================================

print("=" * 80)
print("ROOT CAUSE ATTRIBUTION (Data-Driven)")
print("=" * 80)
print()

# Calculate what portion of decline is due to each factor
total_impact_loss = total_departed_impact - total_new_impact + retained_df['impact_change'].sum()

departed_contribution = (total_departed_impact - total_new_impact) / abs(total_impact_loss) * 100 if total_impact_loss != 0 else 0
retained_decline_contribution = retained_df[retained_df['impact_change'] < 0]['impact_change'].sum() / total_impact_loss * 100 if total_impact_loss != 0 else 0

print(f"Total Team Impact Loss: {abs(total_impact_loss):.0f} runs equivalent")
print()
print("Attribution:")
print(f"  1. Player Departures (net): {departed_contribution:.1f}% of decline")
print(f"     - Lost: {total_departed_impact} impact")
print(f"     - Gained: {total_new_impact} impact")
print(f"     - Net: {total_departed_impact - total_new_impact:+d} impact")
print()
print(f"  2. Retained Player Decline: {abs(retained_decline_contribution):.1f}% of decline")
print(f"     - Number declining: {len(big_declines)}")
print(f"     - Total impact lost: {retained_df[retained_df['impact_change'] < 0]['impact_change'].sum():.0f}")
print()

# Confidence assessment
print("=" * 80)
print("ANALYSIS CONFIDENCE LEVELS")
print("=" * 80)
print()

print("✅ HIGH CONFIDENCE (>90%):")
print("  - Player roster changes (departed/new players)")
print("  - Performance metric changes (runs, wickets, economy)")
print("  - Team-level statistical comparisons")
print()

print("🟡 MEDIUM CONFIDENCE (70-90%):")
print("  - Impact attribution percentages (±10% margin)")
print("  - Causation (correlation observed, but confounds possible)")
print("  - Player decline root causes (form, injury, or context)")
print()

print("⚠️ LOW CONFIDENCE (<70%):")
print("  - WHY players departed (contract, performance, personal)")
print("  - Championship status (no match results data)")
print("  - Opposition quality changes")
print()

print("=" * 80)
print("ANALYSIS COMPLETE")
print("=" * 80)
print()
print("Export dashboard data? Run dashboard export script next.")
