"""
Generate Key Visualizations for Season 2 Analysis
=================================================

Creates 3 critical charts for stakeholder presentations:
1. Death overs bowling collapse (by player)
2. Chase batting decline (S1 vs S2)
3. Squad retention breakdown

Output: PNG files in docs/visualizations/
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# Set style
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (12, 7)
plt.rcParams['font.size'] = 11
plt.rcParams['axes.titlesize'] = 14
plt.rcParams['axes.labelsize'] = 12

# Paths
DATA_DIR = Path("D:/CricNepal/data/exports")
OUTPUT_DIR = Path("D:/CricNepal/docs/visualizations")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def create_death_bowlers_chart():
    """
    Chart 1: Death Overs Bowling Collapse
    Shows economy rate change for retained bowlers (highlights LN Rajbanshi)
    """
    print("\n[1/3] Creating death bowlers decline chart...")
    
    # Load data
    df = pd.read_csv(DATA_DIR / "player_death_bowlers_deltas.csv")
    
    # Sort by delta (worst first)
    df = df.sort_values('economy_rate_delta', ascending=False)
    
    # Create figure
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Color bars (red for worse, green for better)
    colors = ['#e74c3c' if x > 0 else '#2ecc71' for x in df['economy_rate_delta']]
    
    # Horizontal bar chart
    bars = ax.barh(df['bowler_name'], df['economy_rate_delta'], color=colors, alpha=0.8)
    
    # Add value labels
    for i, (bar, val) in enumerate(zip(bars, df['economy_rate_delta'])):
        ax.text(val + 0.3 if val > 0 else val - 0.3, 
                bar.get_y() + bar.get_height()/2,
                f'{val:+.2f}',
                va='center', 
                ha='left' if val > 0 else 'right',
                fontsize=10,
                fontweight='bold')
    
    # Reference line at 0
    ax.axvline(0, color='black', linestyle='--', linewidth=1.5, alpha=0.7)
    
    # Labels and title
    ax.set_xlabel('Economy Rate Change (S2 - S1)', fontsize=12, fontweight='bold')
    ax.set_ylabel('Bowler', fontsize=12, fontweight='bold')
    ax.set_title('Death Overs Bowling Collapse: Retained Bowlers Performance Change\n(Red = Worse in S2, Green = Better in S2)',
                 fontsize=14, fontweight='bold', pad=20)
    
    # Highlight LN Rajbanshi
    ln_raj_idx = df[df['bowler_name'] == 'LN Rajbanshi'].index
    if len(ln_raj_idx) > 0:
        idx = ln_raj_idx[0]
        ax.text(df.iloc[idx]['economy_rate_delta'] + 1, idx,
                '← CATASTROPHIC',
                va='center', ha='left',
                fontsize=11, fontweight='bold', color='#e74c3c',
                bbox=dict(boxstyle='round,pad=0.5', facecolor='yellow', alpha=0.7))
    
    # Grid
    ax.grid(axis='x', alpha=0.3)
    ax.set_axisbelow(True)
    
    plt.tight_layout()
    
    # Save
    output_file = OUTPUT_DIR / "death_bowlers_decline.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"  ✅ Saved: {output_file}")
    
    plt.close()


def create_chase_batting_chart():
    """
    Chart 2: Chase Batting Collapse
    Shows runs scored in chases S1 vs S2 (side-by-side bars)
    """
    print("\n[2/3] Creating chase batting decline chart...")
    
    # Load data
    df = pd.read_csv(DATA_DIR / "player_chase_batters_deltas.csv")
    
    # Sort by S1 runs (top contributors first)
    df = df.sort_values('runs_scored_s1', ascending=False)
    
    # Take top 7 for readability
    df = df.head(7)
    
    # Create figure
    fig, ax = plt.subplots(figsize=(12, 7))
    
    # Bar positions
    x = range(len(df))
    width = 0.35
    
    # S1 bars (green)
    bars1 = ax.bar([i - width/2 for i in x], df['runs_scored_s1'], 
                    width, label='Season 1', color='#27ae60', alpha=0.9)
    
    # S2 bars (red)
    bars2 = ax.bar([i + width/2 for i in x], df['runs_scored_s2'], 
                    width, label='Season 2', color='#e74c3c', alpha=0.9)
    
    # Add value labels on bars
    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                    f'{int(height)}',
                    ha='center', va='bottom', fontsize=9, fontweight='bold')
    
    # Labels and title
    ax.set_xlabel('Batter', fontsize=12, fontweight='bold')
    ax.set_ylabel('Runs Scored in Chases', fontsize=12, fontweight='bold')
    ax.set_title('Chase Batting Collapse: Top 7 Batters S1 vs S2\n(Green = S1 Success, Red = S2 Decline)',
                 fontsize=14, fontweight='bold', pad=20)
    ax.set_xticks(x)
    ax.set_xticklabels(df['batter_name'], rotation=45, ha='right')
    ax.legend(loc='upper right', fontsize=11)
    
    # Highlight BKEL Milantha
    bkel_idx = df[df['batter_name'] == 'BKEL Milantha'].index
    if len(bkel_idx) > 0:
        idx = list(df.index).index(bkel_idx[0])
        ax.annotate('Star Player\nCollapse\n(257 → 23)',
                   xy=(idx, df.iloc[bkel_idx[0]]['runs_scored_s1']),
                   xytext=(idx + 1.5, df.iloc[bkel_idx[0]]['runs_scored_s1'] + 30),
                   fontsize=10, fontweight='bold', color='#e74c3c',
                   bbox=dict(boxstyle='round,pad=0.5', facecolor='yellow', alpha=0.7),
                   arrowprops=dict(arrowstyle='->', color='#e74c3c', lw=2))
    
    # Grid
    ax.grid(axis='y', alpha=0.3)
    ax.set_axisbelow(True)
    
    plt.tight_layout()
    
    # Save
    output_file = OUTPUT_DIR / "chase_batting_decline.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"  ✅ Saved: {output_file}")
    
    plt.close()


def create_squad_retention_chart():
    """
    Chart 3: Squad Retention Breakdown
    Pie chart showing Retained/Departed/Recruited
    """
    print("\n[3/3] Creating squad retention chart...")
    
    # Data (from analysis results)
    sizes = [52, 45, 40]  # Retained, Departed, Recruited
    labels = [
        f'Retained\n52 players\n(53.6%)',
        f'Departed\n45 players\n(46.4%)',
        f'New Recruits\n40 players'
    ]
    colors = ['#2ecc71', '#e74c3c', '#3498db']
    explode = (0, 0.1, 0)  # Explode departed slice to highlight
    
    # Create figure
    fig, ax = plt.subplots(figsize=(10, 8))
    
    # Pie chart
    wedges, texts, autotexts = ax.pie(sizes, 
                                        explode=explode,
                                        labels=labels, 
                                        colors=colors,
                                        autopct='%1.1f%%',
                                        startangle=90,
                                        textprops={'fontsize': 12, 'fontweight': 'bold'},
                                        pctdistance=0.85)
    
    # Make percentage text larger
    for autotext in autotexts:
        autotext.set_color('white')
        autotext.set_fontsize(13)
        autotext.set_fontweight('bold')
    
    # Title
    ax.set_title('Squad Turnover: Season 1 → Season 2\n(46% Departed = High Instability)',
                 fontsize=14, fontweight='bold', pad=20)
    
    # Add annotation
    ax.text(0, -1.4, 
            'Industry Benchmark: 70-80% retention for successful teams\nJanakpur S2: Only 53.6% retained = too low',
            ha='center', fontsize=10, style='italic',
            bbox=dict(boxstyle='round,pad=0.8', facecolor='#ecf0f1', alpha=0.8))
    
    plt.tight_layout()
    
    # Save
    output_file = OUTPUT_DIR / "squad_retention.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"  ✅ Saved: {output_file}")
    
    plt.close()


def create_summary_report():
    """Create a text summary of visualizations."""
    print("\n" + "="*70)
    print("VISUALIZATION SUMMARY")
    print("="*70)
    
    print("\n📊 3 Charts Created:")
    print("\n1. death_bowlers_decline.png")
    print("   - Shows LN Rajbanshi +11.17 economy (catastrophic)")
    print("   - Highlights which bowlers got worse in S2")
    
    print("\n2. chase_batting_decline.png")
    print("   - Shows BKEL Milantha 257 → 23 runs (star collapse)")
    print("   - Compares S1 vs S2 for top 7 chase batters")
    
    print("\n3. squad_retention.png")
    print("   - Shows 46% departed (too high for stability)")
    print("   - Compares vs industry benchmark (70-80%)")
    
    print("\n" + "="*70)
    print(f"Charts saved to: {OUTPUT_DIR}")
    print("="*70)
    
    print("\n💡 Usage:")
    print("  - Embed in PowerPoint presentations")
    print("  - Include in stakeholder emails")
    print("  - Print for board meetings")
    
    print("\n✅ VISUALIZATION GENERATION COMPLETE")


def main():
    """Generate all 3 key charts."""
    print("="*70)
    print("GENERATING KEY VISUALIZATIONS FOR SEASON 2 ANALYSIS")
    print("="*70)
    
    # Create charts
    create_death_bowlers_chart()
    create_chase_batting_chart()
    create_squad_retention_chart()
    
    # Summary
    create_summary_report()


if __name__ == "__main__":
    main()
