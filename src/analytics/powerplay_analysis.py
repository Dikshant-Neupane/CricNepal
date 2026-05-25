"""
Powerplay Analysis (Overs 1-6)
==============================

Purpose:
--------
Analyze Janakpur Bolts performance in the powerplay (overs 1-6) for S1 vs S2.

Methodology:
-----------
- Compute batting metrics (run rate, boundaries, dot %) when JAB batting
- Compute bowling metrics (economy, wickets, dot %) when JAB bowling
- Compare S1 vs S2 and produce integrated diagnosis and visualization
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


def load_ball_by_ball():
    return pd.read_parquet(NORMALIZED_DIR / "ball_by_ball_normalized.parquet")


def analyze_powerplay_batting(bbb, team="Janakpur Bolts", start=1, end=6):
    logger.info("\n" + "="*80)
    logger.info(f"POWERPLAY BATTING ANALYSIS (Overs {start}-{end})")
    logger.info("="*80)

    matches = pd.read_parquet(NORMALIZED_DIR / "matches_normalized.parquet")
    bbb_with_season = bbb.merge(matches[['match_id', 'season']], on='match_id', how='left')

    jab_pp_batting = bbb_with_season[
        (bbb_with_season['batting_team'] == team) &
        (bbb_with_season['over'] >= start) &
        (bbb_with_season['over'] <= end)
    ]

    season_stats = []

    for season in ['S1', 'S2']:
        season_data = jab_pp_batting[jab_pp_batting['season'] == season]
        if len(season_data) == 0:
            logger.info(f"\n{season}: No powerplay batting data")
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

    if len(stats_df) == 2:
        s1 = stats_df[stats_df['season'] == 'S1'].iloc[0]
        s2 = stats_df[stats_df['season'] == 'S2'].iloc[0]

        logger.info(f"\n{'='*80}")
        logger.info("POWERPLAY BATTING DELTA (S1 → S2):")
        logger.info("-"*80)
        logger.info(f"  Run rate: {s1['run_rate']:.2f} → {s2['run_rate']:.2f} ({s2['run_rate'] - s1['run_rate']:+.2f} runs/over)")
        logger.info(f"  Dot ball %: {s1['dot_pct']:.1f}% → {s2['dot_pct']:.1f}% ({s2['dot_pct'] - s1['dot_pct']:+.1f}pp)")

    return stats_df


def analyze_powerplay_bowling(bbb, team='Janakpur Bolts', start=1, end=6):
    logger.info("\n" + "="*80)
    logger.info(f"POWERPLAY BOWLING ANALYSIS (Overs {start}-{end})")
    logger.info("="*80)

    matches = pd.read_parquet(NORMALIZED_DIR / "matches_normalized.parquet")
    bbb_with_season = bbb.merge(matches[['match_id', 'season']], on='match_id', how='left')

    jab_pp_bowling = bbb_with_season[
        (bbb_with_season['bowling_team'] == team) &
        (bbb_with_season['over'] >= start) &
        (bbb_with_season['over'] <= end)
    ]

    season_stats = []

    for season in ['S1', 'S2']:
        season_data = jab_pp_bowling[jab_pp_bowling['season'] == season]
        if len(season_data) == 0:
            logger.info(f"\n{season}: No powerplay bowling data")
            continue

        total_runs = season_data['runs_off_bat'].sum()
        extras = season_data[season_data['runs_off_bat'] == 0]['runs_total'].sum()
        total_runs_conceded = total_runs + extras

        total_balls = len(season_data)
        total_overs = total_balls / 6

        economy = total_runs_conceded / total_overs if total_overs > 0 else 0

        dots = season_data['is_dot_ball'].sum()
        dot_pct = (dots / total_balls * 100) if total_balls > 0 else 0

        wickets_taken = season_data['is_wicket'].sum()
        innings_count = season_data.groupby(['match_id', 'innings']).ngroups

        logger.info(f"\n{season}:")
        logger.info(f"  Opponent innings: {innings_count}")
        logger.info(f"  Runs conceded: {total_runs_conceded} in {total_overs:.1f} overs ({total_balls} balls)")
        logger.info(f"  Economy rate: {economy:.2f} runs/over")
        logger.info(f"  Dot ball %: {dot_pct:.1f}%")
        logger.info(f"  Wickets taken: {wickets_taken} ({wickets_taken/innings_count:.2f} per innings)")

        season_stats.append({
            'season': season,
            'innings': innings_count,
            'total_runs_conceded': total_runs_conceded,
            'total_overs': total_overs,
            'economy': economy,
            'dot_pct': dot_pct,
            'wickets_taken': wickets_taken,
            'wickets_per_innings': wickets_taken / innings_count if innings_count > 0 else 0
        })

    stats_df = pd.DataFrame(season_stats)

    if len(stats_df) == 2:
        s1 = stats_df[stats_df['season'] == 'S1'].iloc[0]
        s2 = stats_df[stats_df['season'] == 'S2'].iloc[0]

        logger.info(f"\n{'='*80}")
        logger.info("POWERPLAY BOWLING DELTA (S1 → S2):")
        logger.info("-"*80)
        logger.info(f"  Economy rate: {s1['economy']:.2f} → {s2['economy']:.2f} ({s2['economy'] - s1['economy']:+.2f} runs/over)")
        logger.info(f"  Dot ball %: {s1['dot_pct']:.1f}% → {s2['dot_pct']:.1f}% ({s2['dot_pct'] - s1['dot_pct']:+.1f}pp)")

    return stats_df


def integrated_powerplay_diagnosis(batting_stats, bowling_stats):
    logger.info("\n" + "="*80)
    logger.info("🎯 INTEGRATED DIAGNOSIS: Powerplay (Overs 1-6)")
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

    logger.info(f"\nPowerplay Performance:")
    logger.info(f"  Batting run rate: {s1_bat['run_rate']:.2f} → {s2_bat['run_rate']:.2f} (Δ = {bat_rate_delta:+.2f})")
    logger.info(f"  Bowling economy: {s1_bowl['economy']:.2f} → {s2_bowl['economy']:.2f} (Δ = {bowl_econ_delta:+.2f})")

    s1_net_rr = s1_bat['run_rate'] - s1_bowl['economy']
    s2_net_rr = s2_bat['run_rate'] - s2_bowl['economy']
    net_rr_delta = s2_net_rr - s1_net_rr

    logger.info(f"\n  Net run rate (batting - bowling): S1: {s1_net_rr:+.2f}, S2: {s2_net_rr:+.2f}, Δ: {net_rr_delta:+.2f}")

    logger.info(f"\n{'='*80}")
    logger.info("ROOT CAUSE VERDICT: Powerplay")
    logger.info("-"*80)

    if bat_rate_delta < -0.5 and bowl_econ_delta > 0.5:
        logger.info("  🔴 POWERPLAY COLLAPSE (Both batting and bowling)")
    elif bat_rate_delta < -0.5:
        logger.info("  📊 POWERPLAY BATTING DECLINE")
    elif bowl_econ_delta > 0.5:
        logger.info("  📊 POWERPLAY BOWLING DECLINE")
    else:
        logger.info("  ✅ POWERPLAY STABLE OR IMPROVED")


def create_powerplay_visualization(batting_stats, bowling_stats):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14,6))

    seasons = batting_stats['season'].values
    bat_rates = batting_stats['run_rate'].values
    bowl_econs = bowling_stats['economy'].values

    bars1 = ax1.bar(seasons, bat_rates, color=['#4CAF50', '#F44336'], alpha=0.8, edgecolor='black')
    ax1.set_ylabel('Run Rate (runs/over)')
    ax1.set_title('Powerplay Batting (1-6)')
    for bar in bars1:
        ax1.text(bar.get_x() + bar.get_width()/2., bar.get_height(), f'{bar.get_height():.2f}', ha='center', va='bottom')

    bars2 = ax2.bar(seasons, bowl_econs, color=['#4CAF50', '#F44336'], alpha=0.8, edgecolor='black')
    ax2.set_ylabel('Economy (runs/over)')
    ax2.set_title('Powerplay Bowling (1-6)')
    for bar in bars2:
        ax2.text(bar.get_x() + bar.get_width()/2., bar.get_height(), f'{bar.get_height():.2f}', ha='center', va='bottom')

    plt.tight_layout()
    output_path = EXPORT_DIR / 'powerplay_analysis.png'
    plt.savefig(output_path, dpi=150)
    logger.info(f"\n📊 Visualization saved: {output_path}")
    plt.close()


def main():
    logger.info("\n" + "="*80)
    logger.info("POWERPLAY ANALYSIS (Overs 1-6)")
    logger.info("="*80)

    bbb = load_ball_by_ball()

    batting_stats = analyze_powerplay_batting(bbb)
    bowling_stats = analyze_powerplay_bowling(bbb)

    integrated_powerplay_diagnosis(batting_stats, bowling_stats)

    if len(batting_stats) >= 2 and len(bowling_stats) >= 2:
        create_powerplay_visualization(batting_stats, bowling_stats)

    logger.info("\n" + "="*80)
    logger.info("POWERPLAY ANALYSIS COMPLETE")
    logger.info("="*80)

    return {
        'batting': batting_stats,
        'bowling': bowling_stats
    }


if __name__ == '__main__':
    main()
"""
Powerplay Analysis (Overs 1-6)
=============================

Research Question:
-----------------
Did Janakpur Bolts' powerplay (overs 1-6) performance change between S1 and S2?

Methodology:
-----------
Mirror of `middle_overs_analysis.py` but for overs 1-6:
1. Analyze batting (run rate, boundaries, dot %, wickets)
2. Analyze bowling (economy, dot %, boundaries conceded, wickets taken)
3. Integrated diagnosis and visualization
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


def load_ball_by_ball():
    return pd.read_parquet(NORMALIZED_DIR / "ball_by_ball_normalized.parquet")


def analyze_powerplay_batting(bbb, team="Janakpur Bolts", start=1, end=6):
    logger.info("\n" + "="*80)
    logger.info(f"POWERPLAY BATTING ANALYSIS (Overs {start}-{end})")
    logger.info("="*80)

    matches = pd.read_parquet(NORMALIZED_DIR / "matches_normalized.parquet")
    bbb_with_season = bbb.merge(matches[['match_id', 'season']], on='match_id', how='left')

    pp_batting = bbb_with_season[
        (bbb_with_season['batting_team'] == team) &
        (bbb_with_season['over'] >= start) &
        (bbb_with_season['over'] <= end)
    ]

    season_stats = []

    for season in ['S1', 'S2']:
        sd = pp_batting[pp_batting['season'] == season]
        if len(sd) == 0:
            logger.info(f"{season}: No powerplay batting data")
            continue

        total_runs = sd['runs_off_bat'].sum()
        total_balls = len(sd)
        total_overs = total_balls / 6
        run_rate = total_runs / total_overs if total_overs > 0 else 0

        boundaries = sd['is_boundary'].sum()
        boundary_rate = boundaries / total_balls * 100 if total_balls > 0 else 0

        dots = sd['is_dot_ball'].sum()
        dot_pct = dots / total_balls * 100 if total_balls > 0 else 0

        wickets = sd['is_wicket'].sum()
        innings_count = sd.groupby(['match_id', 'innings']).ngroups

        logger.info(f"\n{season}:")
        logger.info(f"  Innings: {innings_count}")
        logger.info(f"  Runs: {total_runs} in {total_overs:.1f} overs ({total_balls} balls)")
        logger.info(f"  Run rate: {run_rate:.2f}")
        logger.info(f"  Boundaries: {boundaries} ({boundary_rate:.1f}% of balls)")
        logger.info(f"  Dot %: {dot_pct:.1f}%")
        logger.info(f"  Wickets lost: {wickets} ({wickets/innings_count:.2f} per innings)")

        season_stats.append({
            'season': season,
            'innings': innings_count,
            'total_runs': total_runs,
            'total_overs': total_overs,
            'run_rate': run_rate,
            'boundaries': boundaries,
            'boundary_rate': boundary_rate,
            'dot_pct': dot_pct,
            'wickets_lost': wickets,
            'wickets_per_innings': wickets / innings_count if innings_count > 0 else 0
        })

    stats_df = pd.DataFrame(season_stats)

    if len(stats_df) == 2:
        s1 = stats_df[stats_df['season'] == 'S1'].iloc[0]
        s2 = stats_df[stats_df['season'] == 'S2'].iloc[0]
        logger.info("\n" + "="*80)
        logger.info("POWERPLAY BATTING DELTA (S1 → S2):")
        logger.info("-"*80)
        logger.info(f"  Run rate: {s1['run_rate']:.2f} → {s2['run_rate']:.2f} ({s2['run_rate']-s1['run_rate']:+.2f})")
        logger.info(f"  Dot %: {s1['dot_pct']:.1f}% → {s2['dot_pct']:.1f}% ({s2['dot_pct']-s1['dot_pct']:+.1f}pp)")
        logger.info(f"  Wickets/inn: {s1['wickets_per_innings']:.2f} → {s2['wickets_per_innings']:.2f} ({s2['wickets_per_innings']-s1['wickets_per_innings']:+.2f})")

        if s2['run_rate'] - s1['run_rate'] < -0.5:
            logger.info("  🔴 POWERPLAY BATTING DECLINE")
        elif s2['run_rate'] - s1['run_rate'] < -0.2:
            logger.info("  🟡 MODERATE POWERPLAY BATTING DECLINE")
        else:
            logger.info("  ✅ POWERPLAY BATTING STABLE/IMPROVED")

    return stats_df


def analyze_powerplay_bowling(bbb, team="Janakpur Bolts", start=1, end=6):
    logger.info("\n" + "="*80)
    logger.info(f"POWERPLAY BOWLING ANALYSIS (Overs {start}-{end})")
    logger.info("="*80)

    matches = pd.read_parquet(NORMALIZED_DIR / "matches_normalized.parquet")
    bbb_with_season = bbb.merge(matches[['match_id', 'season']], on='match_id', how='left')

    pp_bowling = bbb_with_season[
        (bbb_with_season['bowling_team'] == team) &
        (bbb_with_season['over'] >= start) &
        (bbb_with_season['over'] <= end)
    ]

    season_stats = []

    for season in ['S1', 'S2']:
        sd = pp_bowling[pp_bowling['season'] == season]
        if len(sd) == 0:
            logger.info(f"{season}: No powerplay bowling data")
            continue

        runs = sd['runs_off_bat'].sum()
        extras = sd[sd['runs_off_bat'] == 0]['runs_total'].sum()
        runs_conceded = runs + extras
        balls = len(sd)
        overs = balls / 6
        economy = runs_conceded / overs if overs > 0 else 0

        dots = sd['is_dot_ball'].sum()
        dot_pct = dots / balls * 100 if balls > 0 else 0
        boundaries = sd['is_boundary'].sum()
        wickets = sd['is_wicket'].sum()
        innings_count = sd.groupby(['match_id', 'innings']).ngroups

        logger.info(f"\n{season}:")
        logger.info(f"  Opp innings: {innings_count}")
        logger.info(f"  Runs conceded: {runs_conceded} in {overs:.1f} overs ({balls} balls)")
        logger.info(f"  Economy: {economy:.2f}")
        logger.info(f"  Dot %: {dot_pct:.1f}%")
        logger.info(f"  Boundaries conceded: {boundaries}")
        logger.info(f"  Wickets taken: {wickets} ({wickets/innings_count:.2f} per innings)")

        season_stats.append({
            'season': season,
            'innings': innings_count,
            'runs_conceded': runs_conceded,
            'overs': overs,
            'economy': economy,
            'dot_pct': dot_pct,
            'boundaries_conceded': boundaries,
            'wickets': wickets,
            'wickets_per_innings': wickets/innings_count if innings_count > 0 else 0
        })

    stats_df = pd.DataFrame(season_stats)

    if len(stats_df) == 2:
        s1 = stats_df[stats_df['season'] == 'S1'].iloc[0]
        s2 = stats_df[stats_df['season'] == 'S2'].iloc[0]
        logger.info("\n" + "="*80)
        logger.info("POWERPLAY BOWLING DELTA (S1 → S2):")
        logger.info("-"*80)
        logger.info(f"  Economy: {s1['economy']:.2f} → {s2['economy']:.2f} ({s2['economy']-s1['economy']:+.2f})")
        logger.info(f"  Dot %: {s1['dot_pct']:.1f}% → {s2['dot_pct']:.1f}% ({s2['dot_pct']-s1['dot_pct']:+.1f}pp)")
        logger.info(f"  Wickets/inn: {s1['wickets_per_innings']:.2f} → {s2['wickets_per_innings']:.2f} ({s2['wickets_per_innings']-s1['wickets_per_innings']:+.2f})")

        if s2['economy'] - s1['economy'] > 0.5:
            logger.info("  🔴 POWERPLAY BOWLING DECLINE")
        elif s2['economy'] - s1['economy'] > 0.2:
            logger.info("  🟡 MODERATE POWERPLAY BOWLING DECLINE")
        else:
            logger.info("  ✅ POWERPLAY BOWLING STABLE/IMPROVED")

    return stats_df


def integrated_powerplay_diagnosis(batting_stats, bowling_stats):
    logger.info("\n" + "="*80)
    logger.info("🎯 INTEGRATED DIAGNOSIS: Powerplay (1-6)")
    logger.info("="*80)

    if len(batting_stats) < 2 or len(bowling_stats) < 2:
        logger.info("\n⚠️ Insufficient data for integrated powerplay diagnosis")
        return

    s1_bat = batting_stats[batting_stats['season'] == 'S1'].iloc[0]
    s2_bat = batting_stats[batting_stats['season'] == 'S2'].iloc[0]
    s1_bowl = bowling_stats[bowling_stats['season'] == 'S1'].iloc[0]
    s2_bowl = bowling_stats[bowling_stats['season'] == 'S2'].iloc[0]

    bat_delta = s2_bat['run_rate'] - s1_bat['run_rate']
    bowl_delta = s2_bowl['economy'] - s1_bowl['economy']

    logger.info(f"Powerplay run rate: {s1_bat['run_rate']:.2f} → {s2_bat['run_rate']:.2f} (Δ={bat_delta:+.2f})")
    logger.info(f"Powerplay economy: {s1_bowl['economy']:.2f} → {s2_bowl['economy']:.2f} (Δ={bowl_delta:+.2f})")

    net1 = s1_bat['run_rate'] - s1_bowl['economy']
    net2 = s2_bat['run_rate'] - s2_bowl['economy']
    net_delta = net2 - net1

    logger.info(f"Net run rate (bat - bowl): S1={net1:+.2f}, S2={net2:+.2f}, Δ={net_delta:+.2f}")

    if bat_delta < -0.5 and bowl_delta > 0.5:
        logger.info("  🔴 COMPLETE POWERPLAY COLLAPSE")
    elif bat_delta < -0.5:
        logger.info("  📊 POWERPLAY BATTING COLLAPSE")
    elif bowl_delta > 0.5:
        logger.info("  📊 POWERPLAY BOWLING DECLINE")
    else:
        logger.info("  ✅ POWERPLAY STABLE")


def create_powerplay_visualization(batting_stats, bowling_stats):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    seasons = batting_stats['season'].values

    bat_rates = batting_stats['run_rate'].values
    bars1 = ax1.bar(seasons, bat_rates, color=['#4CAF50', '#F44336'], alpha=0.8, edgecolor='black')
    ax1.set_title('Powerplay Batting (1-6)')
    ax1.set_ylabel('Run Rate (r/o)')
    for bar in bars1:
        ax1.text(bar.get_x()+bar.get_width()/2., bar.get_height(), f'{bar.get_height():.2f}', ha='center', va='bottom')

    bowl_econs = bowling_stats['economy'].values
    bars2 = ax2.bar(seasons, bowl_econs, color=['#4CAF50', '#F44336'], alpha=0.8, edgecolor='black')
    ax2.set_title('Powerplay Bowling (1-6)')
    ax2.set_ylabel('Economy (r/o)')
    for bar in bars2:
        ax2.text(bar.get_x()+bar.get_width()/2., bar.get_height(), f'{bar.get_height():.2f}', ha='center', va='bottom')

    plt.tight_layout()
    out = EXPORT_DIR / 'powerplay_analysis.png'
    plt.savefig(out, dpi=150)
    logger.info(f"\n📊 Visualization saved: {out}")
    plt.close()


def main():
    logger.info("\n" + "="*80)
    logger.info("POWERPLAY ANALYSIS (Overs 1-6)")
    logger.info("="*80)

    bbb = load_ball_by_ball()
    bat_stats = analyze_powerplay_batting(bbb)
    bowl_stats = analyze_powerplay_bowling(bbb)
    integrated_powerplay_diagnosis(bat_stats, bowl_stats)
    if len(bat_stats) >= 2 and len(bowl_stats) >= 2:
        create_powerplay_visualization(bat_stats, bowl_stats)

    logger.info("\n" + "="*80)
    logger.info("ANALYSIS COMPLETE")
    logger.info("="*80)

    return {'batting': bat_stats, 'bowling': bowl_stats}


if __name__ == '__main__':
    main()
