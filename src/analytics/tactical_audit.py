"""
Layer 4: Tactical/Captaincy Audit
Coach's Requirements:
- Win % under different captains (Anil Sah vs Wayne Parnell in S2)
- Toss decisions: bat-first vs bowl-first record
- Bowling change patterns
- DLS / NRR impact decisions

Focus: Quantify the impact of mid-season captaincy change
"""
import pandas as pd
from pathlib import Path
import json

# ══════════════════════════════════════════════════════════════════════════
# Configuration
# ══════════════════════════════════════════════════════════════════════════

try:
    from src.config.paths import NORMALIZED_DIR, EXPORT_DIR
    DATA_DIR = NORMALIZED_DIR
except ImportError:
    DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "normalized"
    EXPORT_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "exports"

TEAM = "Janakpur Bolts"

# Toss data extracted from Wikipedia (ESPNcricinfo source)
TOSS_DATA_S1 = {
    # Format: (toss_winner, toss_decision)
    # Janakpur Bolts matches in S1 (10 matches total: 7W, 3L)
    # League matches + Playoffs
    "S1_JAB_TOSSES": [
        {"match_num": 1, "toss_winner": "Janakpur Bolts", "decision": "field"},
        {"match_num": 7, "toss_winner": "Janakpur Bolts", "decision": "field"},
        {"match_num": 17, "toss_winner": "Janakpur Bolts", "decision": "field"},
        # Playoff Qualifier 1
        {"match_num": 30, "toss_winner": "Janakpur Bolts", "decision": "bat", "playoff": "Qualifier 1"},
        # Playoff Qualifier 2
        {"match_num": 31, "toss_winner": "Janakpur Bolts", "decision": "field", "playoff": "Qualifier 2"},
    ]
}

TOSS_DATA_S2 = {
    # Janakpur Bolts matches in S2 (7 matches total: 1W, 6L)
    "S2_JAB_TOSSES": [
        {"match_num": 9, "toss_winner": "Janakpur Bolts", "decision": "field"},
        {"match_num": 18, "toss_winner": "Janakpur Bolts", "decision": "bat"},
        {"match_num": 25, "toss_winner": "Janakpur Bolts", "decision": "bat"},
        {"match_num": 28, "toss_winner": "Janakpur Bolts", "decision": "field"},
    ]
}

# KEY INSIGHT FROM COACH'S BRIEFING:
# S2 Captaincy change: Anil Sah removed mid-season, Wayne Parnell appointed
# Need to identify which matches were under which captain
# Currently unknown - requires external research or player data

# ══════════════════════════════════════════════════════════════════════════
# Analysis Functions
# ══════════════════════════════════════════════════════════════════════════

def analyze_toss_impact():
    """
    Analyze toss win rate, toss decision patterns, and impact on match outcomes.
    
    Critical insights:
    - Did Janakpur win more when winning the toss?
    - Did batting first vs chasing affect win rate?
    - How did S1 vs S2 compare?
    """
    print("="*70)
    print("TACTICAL AUDIT: TOSS IMPACT ANALYSIS")
    print("="*70)
    
    # Load match data
    matches = pd.read_parquet(DATA_DIR / "matches_normalized.parquet")
    jab_matches = matches[
        (matches['team_1_name'] == TEAM) | (matches['team_2_name'] == TEAM)
    ].copy()
    
    print(f"\n[INFO] Loaded {len(jab_matches)} Janakpur Bolts matches")
    print(f"  S1: {len(jab_matches[jab_matches['season'] == 'S1'])} matches")
    print(f"  S2: {len(jab_matches[jab_matches['season'] == 'S2'])} matches")
    
    # Merge toss data
    toss_records = []
    
    # Process S1 tosses
    for toss in TOSS_DATA_S1["S1_JAB_TOSSES"]:
        toss_records.append({
            'season': 'S1',
            'match_num': toss['match_num'],
            'toss_won': toss['toss_winner'] == TEAM,
            'toss_decision': toss['decision'],
            'playoff': toss.get('playoff', None)
        })
    
    # Process S2 tosses
    for toss in TOSS_DATA_S2["S2_JAB_TOSSES"]:
        toss_records.append({
            'season': 'S2',
            'match_num': toss['match_num'],
            'toss_won': toss['toss_winner'] == TEAM,
            'toss_decision': toss['decision'],
            'playoff': None
        })
    
    toss_df = pd.DataFrame(toss_records)
    
    print("\n" + "="*70)
    print("TOSS WIN RATE ANALYSIS")
    print("="*70)
    
    # S1 toss analysis
    s1_tosses = toss_df[toss_df['season'] == 'S1']
    s1_toss_wins = s1_tosses['toss_won'].sum()
    s1_total = len(jab_matches[jab_matches['season'] == 'S1'])
    s1_toss_pct = (s1_toss_wins / s1_total * 100) if s1_total > 0 else 0
    
    print(f"\nSEASON 1:")
    print(f"  Toss wins: {s1_toss_wins}/{s1_total} ({s1_toss_pct:.1f}%)")
    print(f"  Toss decisions when won:")
    if len(s1_tosses[s1_tosses['toss_won']]) > 0:
        for _, row in s1_tosses[s1_tosses['toss_won']].iterrows():
            playoff_tag = f" [{row['playoff']}]" if row['playoff'] else ""
            print(f"    Match {row['match_num']}: {row['toss_decision'].upper()}{playoff_tag}")
    
    # S2 toss analysis
    s2_tosses = toss_df[toss_df['season'] == 'S2']
    s2_toss_wins = s2_tosses['toss_won'].sum()
    s2_total = len(jab_matches[jab_matches['season'] == 'S2'])
    s2_toss_pct = (s2_toss_wins / s2_total * 100) if s2_total > 0 else 0
    
    print(f"\nSEASON 2:")
    print(f"  Toss wins: {s2_toss_wins}/{s2_total} ({s2_toss_pct:.1f}%)")
    print(f"  Toss decisions when won:")
    if len(s2_tosses[s2_tosses['toss_won']]) > 0:
        for _, row in s2_tosses[s2_tosses['toss_won']].iterrows():
            print(f"    Match {row['match_num']}: {row['toss_decision'].upper()}")
    
    # Toss conversion analysis
    print("\n" + "="*70)
    print("TOSS CONVERSION ANALYSIS (Win match after winning toss)")
    print("="*70)
    
    # Calculate from existing match data
    s1_matches = jab_matches[jab_matches['season'] == 'S1']
    s1_wins = len(s1_matches[s1_matches['winner_name'] == TEAM])
    
    s2_matches = jab_matches[jab_matches['season'] == 'S2']
    s2_wins = len(s2_matches[s2_matches['winner_name'] == TEAM])
    
    print(f"\nSEASON 1:")
    print(f"  Total wins: {s1_wins}/{len(s1_matches)} ({s1_wins/len(s1_matches)*100:.1f}%)")
    print(f"  Toss wins: {s1_toss_wins}/{s1_total}")
    print(f"  ⚠️  NOTE: Toss conversion rate requires match-by-match alignment")
    print(f"      (need to map which toss wins led to match wins)")
    
    print(f"\nSEASON 2:")
    print(f"  Total wins: {s2_wins}/{len(s2_matches)} ({s2_wins/len(s2_matches)*100:.1f}%)")
    print(f"  Toss wins: {s2_toss_wins}/{s2_total}")
    
    # Batting first vs chasing analysis
    print("\n" + "="*70)
    print("BATTING FIRST VS CHASING (Toss Decision Impact)")
    print("="*70)
    
    # Load ball-by-ball to identify batting first vs chasing
    deliveries = pd.read_parquet(DATA_DIR / "ball_by_ball_normalized.parquet")
    jab_deliveries = deliveries[
        (deliveries['batting_team'] == TEAM) | (deliveries['bowling_team'] == TEAM)
    ]
    
    # Group by match to identify batting order
    batting_first_matches = []
    chasing_matches = []
    
    for match_id in jab_matches['match_id'].unique():
        match_deliveries = jab_deliveries[jab_deliveries['match_id'] == match_id]
        
        # Check innings 1 vs innings 2
        innings_1 = match_deliveries[match_deliveries['innings'] == 1]
        innings_2 = match_deliveries[match_deliveries['innings'] == 2]
        
        if len(innings_1) > 0 and len(innings_2) > 0:
            # Janakpur batted first if they were batting team in innings 1
            if innings_1.iloc[0]['batting_team'] == TEAM:
                batting_first_matches.append(match_id)
            else:
                chasing_matches.append(match_id)
    
    # Split by season
    s1_bat_first = [m for m in batting_first_matches if m in s1_matches['match_id'].values]
    s1_chase = [m for m in chasing_matches if m in s1_matches['match_id'].values]
    s2_bat_first = [m for m in batting_first_matches if m in s2_matches['match_id'].values]
    s2_chase = [m for m in chasing_matches if m in s2_matches['match_id'].values]
    
    # Calculate win rates
    s1_bat_first_wins = len([m for m in s1_bat_first if m in s1_matches[s1_matches['winner_name'] == TEAM]['match_id'].values])
    s1_chase_wins = len([m for m in s1_chase if m in s1_matches[s1_matches['winner_name'] == TEAM]['match_id'].values])
    
    s2_bat_first_wins = len([m for m in s2_bat_first if m in s2_matches[s2_matches['winner_name'] == TEAM]['match_id'].values])
    s2_chase_wins = len([m for m in s2_chase if m in s2_matches[s2_matches['winner_name'] == TEAM]['match_id'].values])
    
    print(f"\nSEASON 1:")
    print(f"  Batting first: {s1_bat_first_wins}/{len(s1_bat_first)} wins ({s1_bat_first_wins/len(s1_bat_first)*100 if len(s1_bat_first) > 0 else 0:.1f}%)")
    print(f"  Chasing: {s1_chase_wins}/{len(s1_chase)} wins ({s1_chase_wins/len(s1_chase)*100 if len(s1_chase) > 0 else 0:.1f}%)")
    
    print(f"\nSEASON 2:")
    print(f"  Batting first: {s2_bat_first_wins}/{len(s2_bat_first)} wins ({s2_bat_first_wins/len(s2_bat_first)*100 if len(s2_bat_first) > 0 else 0:.1f}%)")
    print(f"  Chasing: {s2_chase_wins}/{len(s2_chase)} wins ({s2_chase_wins/len(s2_chase)*100 if len(s2_chase) > 0 else 0:.1f}%)")
    
    # KEY INSIGHT
    print("\n" + "="*70)
    print("🔑 KEY TACTICAL INSIGHTS")
    print("="*70)
    
    print("\n1. TOSS WIN RATE:")
    print(f"   S1: {s1_toss_pct:.1f}% → S2: {s2_toss_pct:.1f}%")
    print(f"   Delta: {s2_toss_pct - s1_toss_pct:+.1f}pp")
    
    print("\n2. TOSS DECISION PREFERENCE:")
    s1_field_first = len(s1_tosses[(s1_tosses['toss_won']) & (s1_tosses['toss_decision'] == 'field')])
    s1_bat_first_toss = len(s1_tosses[(s1_tosses['toss_won']) & (s1_tosses['toss_decision'] == 'bat')])
    s2_field_first = len(s2_tosses[(s2_tosses['toss_won']) & (s2_tosses['toss_decision'] == 'field')])
    s2_bat_first_toss = len(s2_tosses[(s2_tosses['toss_won']) & (s2_tosses['toss_decision'] == 'bat')])
    
    print(f"   S1: Field {s1_field_first}/{s1_toss_wins}, Bat {s1_bat_first_toss}/{s1_toss_wins}")
    print(f"   S2: Field {s2_field_first}/{s2_toss_wins}, Bat {s2_bat_first_toss}/{s2_toss_wins}")
    
    print("\n3. BATTING FIRST VS CHASING:")
    s1_chase_pct = (s1_chase_wins/len(s1_chase)*100) if len(s1_chase) > 0 else 0
    s2_chase_pct = (s2_chase_wins/len(s2_chase)*100) if len(s2_chase) > 0 else 0
    print(f"   S1 chase win rate: {s1_chase_pct:.1f}%")
    print(f"   S2 chase win rate: {s2_chase_pct:.1f}%")
    print(f"   Delta: {s2_chase_pct - s1_chase_pct:+.1f}pp")
    
    print("\n4. CRITICAL PLAYOFF PATTERN (S1):")
    print("   - Qualifier 1: Won toss → BAT FIRST → LOST to SPR by 8 wickets")
    print("   - Qualifier 2: Won toss → FIELD → WON vs KAY by 2 wickets")
    print("   - Final: SPR won toss (bat) → JAB chased and WON by 5 wickets")
    print("   ➡️  LESSON: Janakpur wins when CHASING. Always chase if you win toss.")
    
    print("\n5. COACH'S PRIORITY - CAPTAINCY CHANGE:")
    print("   ⚠️  Anil Sah (S1 captain, removed mid-S2) vs Wayne Parnell (S2 captain)")
    print("   ⚠️  REQUIRES: Match-by-match captain assignment for S2")
    print("   ⚠️  ACTION: External research needed to split S2 matches by captain")
    
    # Export summary
    summary = {
        "season_1": {
            "toss_wins": int(s1_toss_wins),
            "toss_win_pct": round(s1_toss_pct, 1),
            "total_wins": int(s1_wins),
            "total_matches": int(len(s1_matches)),
            "batting_first_wins": int(s1_bat_first_wins),
            "batting_first_matches": int(len(s1_bat_first)),
            "chasing_wins": int(s1_chase_wins),
            "chasing_matches": int(len(s1_chase)),
            "chase_win_pct": round(s1_chase_pct, 1),
        },
        "season_2": {
            "toss_wins": int(s2_toss_wins),
            "toss_win_pct": round(s2_toss_pct, 1),
            "total_wins": int(s2_wins),
            "total_matches": int(len(s2_matches)),
            "batting_first_wins": int(s2_bat_first_wins),
            "batting_first_matches": int(len(s2_bat_first)),
            "chasing_wins": int(s2_chase_wins),
            "chasing_matches": int(len(s2_chase)),
            "chase_win_pct": round(s2_chase_pct, 1),
        },
        "deltas": {
            "toss_win_pct": round(s2_toss_pct - s1_toss_pct, 1),
            "chase_win_pct": round(s2_chase_pct - s1_chase_pct, 1),
        },
        "key_insights": [
            f"S1 chase win rate: {s1_chase_pct:.1f}%",
            f"S2 chase win rate: {s2_chase_pct:.1f}%",
            f"Delta: {s2_chase_pct - s1_chase_pct:+.1f}pp",
            "S1 Playoff Final: Janakpur won by CHASING (5 wickets)",
            "S2 Performance: 1W-6L (14.3% win rate)",
            "CRITICAL: Mid-season captaincy change from Anil Sah to Wayne Parnell"
        ]
    }
    
    return summary


def analyze_captaincy_change():
    """
    PLACEHOLDER: Analyze win rate under Anil Sah vs Wayne Parnell.
    
    Requirements:
    - Match-by-match captain assignment for S2
    - Identify which matches were under Anil Sah (before removal)
    - Identify which matches were under Wayne Parnell (after appointment)
    
    Current Status: BLOCKED - requires external research
    """
    print("\n" + "="*70)
    print("CAPTAINCY CHANGE ANALYSIS")
    print("="*70)
    
    print("\n⚠️  CRITICAL GAP IDENTIFIED:")
    print("   The coach explicitly mentioned:")
    print("   'Anil Sah was removed from captain of Janakpur Bolts mid-season")
    print("    & Wayne Parnell was appointed as captain.'")
    print("\n   To complete this analysis, we need:")
    print("   1. Which S2 matches were captained by Anil Sah?")
    print("   2. Which S2 matches were captained by Wayne Parnell?")
    print("   3. Win/loss record under each captain")
    print("   4. Death overs economy under each captain")
    print("   5. Toss decision patterns under each captain")
    
    print("\n   RECOMMENDATION:")
    print("   - Search ESPNcricinfo match scorecards for captain names")
    print("   - Look for press releases announcing captaincy change")
    print("   - Check NPL official website for squad/captain announcements")
    
    print("\n" + "="*70)


# ══════════════════════════════════════════════════════════════════════════
# Main Execution
# ══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("\n" + "="*70)
    print("LAYER 4: TACTICAL / CAPTAINCY AUDIT")
    print("Janakpur Bolts - NPL Season 1 vs Season 2")
    print("="*70)
    
    # Run toss impact analysis
    summary = analyze_toss_impact()
    
    # Run captaincy change analysis (currently placeholder)
    analyze_captaincy_change()
    
    # Export summary
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    summary_file = EXPORT_DIR / "tactical_audit_summary.json"
    
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"\n✓ Exported: {summary_file}")
    
    print("\n" + "="*70)
    print("TACTICAL AUDIT COMPLETE")
    print("="*70)
    print("\nNext steps:")
    print("1. ✅ Toss impact analysis complete")
    print("2. ⚠️  Captaincy change analysis BLOCKED (needs captain assignments)")
    print("3. ⚠️  Bowling change patterns (requires over-by-over bowler rotation data)")
    print("4. ⚠️  DLS/NRR impact (requires match-specific calculations)")
    print("\n" + "="*70)
