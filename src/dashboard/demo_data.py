"""
Janakpur Bolts Dashboard — Demo Data Module
Dynamically checks data/exports/ for computed analysis outputs, falling back to mock demo data if they are missing.
All functions return data ready for display — no DB dependency.
"""
import pandas as pd
import json
from pathlib import Path

def get_exports_filepath(filename: str) -> Path:
    """Helper to locate a file in the data/exports directory under different run contexts."""
    try:
        from src.config.paths import EXPORTS_DIR
        path = EXPORTS_DIR / filename
        if path.exists():
            return path
    except ImportError:
        pass
    
    # Absolute and relative fallbacks
    for path_candidate in [
        Path("data/exports") / filename,
        Path(__file__).resolve().parent.parent.parent / "data" / "exports" / filename,
        Path("D:/CricNepal/data/exports") / filename,
        Path("../data/exports") / filename
    ]:
        if path_candidate.exists():
            return path_candidate
    return None


# ═══════════════════════════════════════════════════════════
# TEAM INTELLIGENCE (Executive Overview) DATA
# ═══════════════════════════════════════════════════════════

def get_strategic_metrics() -> list[dict]:
    """Three top-level KPI cards from the Team Intelligence mockup."""
    # Attempt to load real data
    tactical_path = get_exports_filepath("tactical_audit_summary.json")
    bowling_path = get_exports_filepath("s1_vs_s2_bowling_by_phase.csv")
    
    # Defaults
    toss_val, toss_delta, toss_type = "68%", "+12% vs Lg", "positive"
    chase_val, chase_delta, chase_type = "72%", "Target < 170", "neutral"
    death_val, death_delta, death_type = "9.8", "-0.4 vs Lg", "negative"
    
    if tactical_path:
        try:
            with open(tactical_path, 'r') as f:
                data = json.load(f)
            s2 = data.get("season_2", {})
            deltas = data.get("deltas", {})
            
            toss_val = f"{int(s2.get('toss_win_pct', 57.1))}%"
            toss_delta = f"{deltas.get('toss_win_pct', +7.1):+.1f}% vs S1"
            toss_type = "positive" if deltas.get('toss_win_pct', 0) >= 0 else "negative"
            
            chase_val = f"{int(s2.get('chase_win_pct', 25.0))}%"
            chase_delta = f"{deltas.get('chase_win_pct', -50.0):+.1f}% vs S1"
            chase_type = "positive" if deltas.get('chase_win_pct', 0) >= 0 else "negative"
        except Exception:
            pass
            
    if bowling_path:
        try:
            df = pd.read_csv(bowling_path)
            s1_death = df[(df['season'] == 'S1') & (df['phase'] == 'death')]['economy'].values[0]
            s2_death = df[(df['season'] == 'S2') & (df['phase'] == 'death')]['economy'].values[0]
            death_val = f"{s2_death:.2f}"
            econ_delta = s2_death - s1_death
            death_delta = f"{econ_delta:+.2f} vs S1"
            death_type = "negative" if econ_delta > 0 else "positive"
        except Exception:
            pass
            
    return [
        {
            "title": "Toss Win Rate (S2)",
            "value": toss_val,
            "delta": toss_delta,
            "delta_type": toss_type,
            "description": "Toss winning rate in Season 2 matches.",
            "icon": "",
        },
        {
            "title": "Chase Win Rate (S2)",
            "value": chase_val,
            "delta": chase_delta,
            "delta_type": chase_type,
            "description": "Win rate when chasing in S2.",
            "icon": "",
        },
        {
            "title": "Death Economy (S2)",
            "value": death_val,
            "delta": death_delta,
            "delta_type": death_type,
            "description": "Runs per over conceded in death overs (16-20).",
            "icon": "",
        },
    ]


def get_batting_phases() -> list[dict]:
    """Batting phase analysis — Powerplay / Middle / Death."""
    path = get_exports_filepath("s1_vs_s2_batting_by_phase.csv")
    
    if path:
        try:
            df = pd.read_csv(path)
            pp_s2 = df[(df['season'] == 'S2') & (df['phase'] == 'powerplay')].iloc[0]
            pp_s1 = df[(df['season'] == 'S1') & (df['phase'] == 'powerplay')].iloc[0]
            
            mid_s2 = df[(df['season'] == 'S2') & (df['phase'] == 'middle')].iloc[0]
            mid_s1 = df[(df['season'] == 'S1') & (df['phase'] == 'middle')].iloc[0]
            
            death_s2 = df[(df['season'] == 'S2') & (df['phase'] == 'death')].iloc[0]
            death_s1 = df[(df['season'] == 'S1') & (df['phase'] == 'death')].iloc[0]
            
            return [
                {
                    "name": "Powerplay (1-6)",
                    "highlight": None,
                    "stats": [
                        {"label": "SR", "value": f"{pp_s2['strike_rate']:.1f}", "style": "primary"},
                        {"label": "Dot %", "value": f"{pp_s2['dot_ball_pct']:.1f}%", "style": "normal"},
                        {"label": "Bnd %", "value": f"{pp_s2['boundary_pct']:.1f}%", "style": "accent"},
                        {"label": "Wkts Lost", "value": f"{int(pp_s2['wickets_lost'])}", "style": "normal"},
                    ],
                    "sr": f"{pp_s2['strike_rate']:.1f}",
                    "dot": f"{pp_s2['dot_ball_pct']:.1f}%",
                    "bnd": f"{pp_s2['boundary_pct']:.1f}%",
                    "dis": f"{pp_s2['wickets_lost']/7:.1f}",
                    "sr_delta": f"{(pp_s2['strike_rate'] - pp_s1['strike_rate']):+.1f} vs S1",
                    "dot_delta": f"{(pp_s2['dot_ball_pct'] - pp_s1['dot_ball_pct']):+.1f}% vs S1",
                    "bnd_delta": f"{(pp_s2['boundary_pct'] - pp_s1['boundary_pct']):+.1f}% vs S1",
                    "dis_delta": "Avg wkts lost/match",
                    "sr_c": "var(--secondary)" if pp_s2['strike_rate'] > pp_s1['strike_rate'] else "var(--error)",
                    "dot_c": "var(--error)" if pp_s2['dot_ball_pct'] > pp_s1['dot_ball_pct'] else "var(--secondary)",
                    "bnd_c": "var(--secondary)" if pp_s2['boundary_pct'] > pp_s1['boundary_pct'] else "var(--error)",
                    "dis_c": "var(--error)" if (pp_s2['wickets_lost']/7) > (pp_s1['wickets_lost']/10) else "var(--secondary)",
                },
                {
                    "name": "Middle (7-15)",
                    "highlight": None,
                    "stats": [
                        {"label": "SR", "value": f"{mid_s2['strike_rate']:.1f}", "style": "primary"},
                        {"label": "Dot %", "value": f"{mid_s2['dot_ball_pct']:.1f}%", "style": "normal"},
                        {"label": "Bnd %", "value": f"{mid_s2['boundary_pct']:.1f}%", "style": "normal"},
                        {"label": "Wkts Lost", "value": f"{int(mid_s2['wickets_lost'])}", "style": "normal"},
                    ],
                    "sr": f"{mid_s2['strike_rate']:.1f}",
                    "dot": f"{mid_s2['dot_ball_pct']:.1f}%",
                    "bnd": f"{mid_s2['boundary_pct']:.1f}%",
                    "dis": f"{mid_s2['wickets_lost']/7:.1f}",
                    "sr_delta": f"{(mid_s2['strike_rate'] - mid_s1['strike_rate']):+.1f} vs S1",
                    "dot_delta": f"{(mid_s2['dot_ball_pct'] - mid_s1['dot_ball_pct']):+.1f}% vs S1",
                    "bnd_delta": f"{(mid_s2['boundary_pct'] - mid_s1['boundary_pct']):+.1f}% vs S1",
                    "dis_delta": "Avg wkts lost/match",
                    "sr_c": "var(--secondary)" if mid_s2['strike_rate'] > mid_s1['strike_rate'] else "var(--error)",
                    "dot_c": "var(--error)" if mid_s2['dot_ball_pct'] > mid_s1['dot_ball_pct'] else "var(--secondary)",
                    "bnd_c": "var(--secondary)" if mid_s2['boundary_pct'] > mid_s1['boundary_pct'] else "var(--error)",
                    "dis_c": "var(--error)" if (mid_s2['wickets_lost']/7) > (mid_s1['wickets_lost']/10) else "var(--secondary)",
                },
                {
                    "name": "Death (16-20)",
                    "highlight": "secondary",
                    "stats": [
                        {"label": "SR", "value": f"{death_s2['strike_rate']:.1f}", "style": "primary"},
                        {"label": "Dot %", "value": f"{death_s2['dot_ball_pct']:.1f}%", "style": "normal"},
                        {"label": "Bnd %", "value": f"{death_s2['boundary_pct']:.1f}%", "style": "accent"},
                        {"label": "Wkts Lost", "value": f"{int(death_s2['wickets_lost'])}", "style": "normal"},
                    ],
                    "sr": f"{death_s2['strike_rate']:.1f}",
                    "dot": f"{death_s2['dot_ball_pct']:.1f}%",
                    "bnd": f"{death_s2['boundary_pct']:.1f}%",
                    "dis": f"{death_s2['wickets_lost']/7:.1f}",
                    "sr_delta": f"{(death_s2['strike_rate'] - death_s1['strike_rate']):+.1f} vs S1",
                    "dot_delta": f"{(death_s2['dot_ball_pct'] - death_s1['dot_ball_pct']):+.1f}% vs S1",
                    "bnd_delta": f"{(death_s2['boundary_pct'] - death_s1['boundary_pct']):+.1f}% vs S1",
                    "dis_delta": "Avg wkts lost/match",
                    "sr_c": "var(--secondary)" if death_s2['strike_rate'] > death_s1['strike_rate'] else "var(--error)",
                    "dot_c": "var(--error)" if death_s2['dot_ball_pct'] > death_s1['dot_ball_pct'] else "var(--secondary)",
                    "bnd_c": "var(--secondary)" if death_s2['boundary_pct'] > death_s1['boundary_pct'] else "var(--error)",
                    "dis_c": "var(--error)" if (death_s2['wickets_lost']/7) > (death_s1['wickets_lost']/10) else "var(--secondary)",
                },
            ]
        except Exception:
            pass

    return [
        {
            "name": "Powerplay (1-6)",
            "highlight": None,
            "stats": [
                {"label": "SR", "value": "134.5", "style": "primary"},
                {"label": "Avg", "value": "32.1", "style": "primary"},
                {"label": "Dot %", "value": "42%", "style": "normal"},
                {"label": "Bnd %", "value": "21%", "style": "accent"},
            ],
            "sr": "134.5", "dot": "42%", "bnd": "21%", "dis": "32.1",
            "sr_delta": "↓ 2.4", "dot_delta": "↑ 1.2%", "bnd_delta": "↓ 0.5%", "dis_delta": "Avg runs/wkt",
            "sr_c": "var(--error)", "dot_c": "var(--error)", "bnd_c": "var(--error)", "dis_c": "var(--error)",
        },
        {
            "name": "Middle (7-15)",
            "highlight": None,
            "stats": [
                {"label": "SR", "value": "121.0", "style": "primary"},
                {"label": "Avg", "value": "28.4", "style": "primary"},
                {"label": "Dot %", "value": "28%", "style": "normal"},
                {"label": "Bnd %", "value": "12%", "style": "normal"},
            ],
            "sr": "121.0", "dot": "28%", "bnd": "12%", "dis": "28.4",
            "sr_delta": "↓ 5.2", "dot_delta": "↓ 2.1%", "bnd_delta": "↓ 1.4%", "dis_delta": "Avg runs/wkt",
            "sr_c": "var(--error)", "dot_c": "var(--secondary)", "bnd_c": "var(--error)", "dis_c": "var(--error)",
        },
        {
            "name": "Death (16-20)",
            "highlight": "secondary",
            "stats": [
                {"label": "SR", "value": "185.2", "style": "primary"},
                {"label": "Avg", "value": "18.5", "style": "primary"},
                {"label": "Dot %", "value": "22%", "style": "normal"},
                {"label": "Bnd %", "value": "28%", "style": "accent"},
            ],
            "sr": "185.2", "dot": "22%", "bnd": "28%", "dis": "18.5",
            "sr_delta": "↑ 12.4", "dot_delta": "↓ 4.5%", "bnd_delta": "↑ 3.2%", "dis_delta": "Avg runs/wkt",
            "sr_c": "var(--secondary)", "dot_c": "var(--secondary)", "bnd_c": "var(--secondary)", "dis_c": "var(--secondary)",
        },
    ]


def get_bowling_phases() -> list[dict]:
    """Bowling phase analysis — Powerplay / Middle / Death."""
    path = get_exports_filepath("s1_vs_s2_bowling_by_phase.csv")
    
    if path:
        try:
            df = pd.read_csv(path)
            pp_s2 = df[(df['season'] == 'S2') & (df['phase'] == 'powerplay')].iloc[0]
            pp_s1 = df[(df['season'] == 'S1') & (df['phase'] == 'powerplay')].iloc[0]
            
            mid_s2 = df[(df['season'] == 'S2') & (df['phase'] == 'middle')].iloc[0]
            mid_s1 = df[(df['season'] == 'S1') & (df['phase'] == 'middle')].iloc[0]
            
            death_s2 = df[(df['season'] == 'S2') & (df['phase'] == 'death')].iloc[0]
            death_s1 = df[(df['season'] == 'S1') & (df['phase'] == 'death')].iloc[0]
            
            return [
                {
                    "name": "POWERPLAY (1-6)",
                    "highlight": None,
                    "stats": [
                        {"label": "Econ", "value": f"{pp_s2['economy']:.2f}", "style": "primary"},
                        {"label": "Wkts", "value": f"{int(pp_s2['wickets_taken'])}", "style": "primary"},
                        {"label": "Dot %", "value": f"{pp_s2['dot_ball_pct']:.1f}%", "style": "accent"},
                        {"label": "vs S1", "value": f"{(pp_s2['economy'] - pp_s1['economy']):+.2f}", "style": "accent" if (pp_s2['economy'] - pp_s1['economy']) <= 0 else "error"},
                    ],
                    "econ": f"{pp_s2['economy']:.2f}",
                    "wkts": f"{int(pp_s2['wickets_taken'])}",
                    "dot": f"{pp_s2['dot_ball_pct']:.1f}%",
                    "pressure": "Optimal" if pp_s2['economy'] < 7.0 else "High",
                    "pressure_c": "var(--primary)" if pp_s2['economy'] < 7.0 else "var(--secondary)",
                },
                {
                    "name": "MIDDLE (7-15)",
                    "highlight": None,
                    "stats": [
                        {"label": "Econ", "value": f"{mid_s2['economy']:.2f}", "style": "primary"},
                        {"label": "Wkts", "value": f"{int(mid_s2['wickets_taken'])}", "style": "primary"},
                        {"label": "Dot %", "value": f"{mid_s2['dot_ball_pct']:.1f}%", "style": "normal"},
                        {"label": "vs S1", "value": f"{(mid_s2['economy'] - mid_s1['economy']):+.2f}", "style": "normal"},
                    ],
                    "econ": f"{mid_s2['economy']:.2f}",
                    "wkts": f"{int(mid_s2['wickets_taken'])}",
                    "dot": f"{mid_s2['dot_ball_pct']:.1f}%",
                    "pressure": "Optimal" if mid_s2['economy'] < 7.5 else "High",
                    "pressure_c": "var(--primary)" if mid_s2['economy'] < 7.5 else "var(--secondary)",
                },
                {
                    "name": "DEATH (16-20)",
                    "highlight": "error",
                    "stats": [
                        {"label": "Econ", "value": f"{death_s2['economy']:.2f}", "style": "error"},
                        {"label": "Wkts", "value": f"{int(death_s2['wickets_taken'])}", "style": "primary"},
                        {"label": "Dot %", "value": f"{death_s2['dot_ball_pct']:.1f}%", "style": "normal"},
                        {"label": "vs S1", "value": f"{(death_s2['economy'] - death_s1['economy']):+.2f}", "style": "error"},
                    ],
                    "econ": f"{death_s2['economy']:.2f}",
                    "econ_c": "var(--error)" if death_s2['economy'] > 9.0 else "var(--on-surface)",
                    "wkts": f"{int(death_s2['wickets_taken'])}",
                    "dot": f"{death_s2['dot_ball_pct']:.1f}%",
                    "pressure": "Critical" if death_s2['economy'] > 9.0 else "Optimal",
                    "pressure_c": "var(--error)" if death_s2['economy'] > 9.0 else "var(--primary)",
                },
            ]
        except Exception:
            pass

    return [
        {
            "name": "POWERPLAY (1-6)",
            "highlight": None,
            "stats": [
                {"label": "Econ", "value": "7.2", "style": "primary"},
                {"label": "Wkt/Ov", "value": "0.25", "style": "primary"},
                {"label": "Dot %", "value": "48%", "style": "accent"},
                {"label": "vs Lg", "value": "-0.5", "style": "accent"},
            ],
            "econ": "7.2", "wkts": "12", "dot": "48%",
            "pressure": "High", "pressure_c": "var(--secondary)",
        },
        {
            "name": "MIDDLE (7-15)",
            "highlight": None,
            "stats": [
                {"label": "Econ", "value": "7.8", "style": "primary"},
                {"label": "Wkt/Ov", "value": "0.31", "style": "primary"},
                {"label": "Dot %", "value": "32%", "style": "normal"},
                {"label": "vs Lg", "value": "+0.1", "style": "normal"},
            ],
            "econ": "7.8", "wkts": "24", "dot": "32%",
            "pressure": "Optimal", "pressure_c": "var(--primary)",
        },
        {
            "name": "DEATH (16-20)",
            "highlight": "error",
            "stats": [
                {"label": "Econ", "value": "9.8", "style": "error"},
                {"label": "Wkt/Ov", "value": "0.45", "style": "primary"},
                {"label": "Dot %", "value": "25%", "style": "normal"},
                {"label": "vs Lg", "value": "+0.4", "style": "error"},
            ],
            "econ": "9.8", "econ_c": "var(--error)", "wkts": "8", "dot": "25%",
            "pressure": "Critical", "pressure_c": "var(--error)",
        },
    ]


def get_order_contribution() -> list[dict]:
    """Batting order contribution percentages."""
    return [
        {"label": "Top (1-3)", "value": 45, "color": "primary"},
        {"label": "Mid (4-5)", "value": 35, "color": "secondary"},
        {"label": "Low (6-7)", "value": 15, "color": "tertiary"},
        {"label": "Tail (8+)", "value": 5, "color": "muted"},
    ]


def get_resource_heatmap() -> list[dict]:
    """
    Bowling resource heatmap — bowler × over allocation.
    Each bowler has 20 values (overs 1-20), representing allocation intensity 0.0-1.0.
    """
    return [
        {
            "name": "B1 (Pace)",
            "color_base": "primary",
            "overs": [0.8, 0.2, 0, 0, 0, 0, 0, 0, 0, 0,
                       0, 0, 0, 0, 0, 0.4, 0, 0.9, 0, 1.0],
        },
        {
            "name": "B2 (Spin)",
            "color_base": "secondary",
            "overs": [0, 0, 0, 0, 0, 0.8, 0, 0.9, 0, 0.7,
                       0, 0.6, 0, 0, 0, 0, 0, 0, 0, 0],
        },
        {
            "name": "B3 (Pace)",
            "color_base": "primary",
            "overs": [0, 0.9, 0, 0.8, 0, 0, 0, 0, 0, 0,
                       0, 0, 0, 0, 0.6, 0, 0.9, 0, 0.8, 0],
        },
        {
            "name": "B4 (Spin)",
            "color_base": "secondary",
            "overs": [0, 0, 0, 0, 0, 0, 0.7, 0, 0.8, 0,
                       0.9, 0, 0.7, 0.6, 0, 0, 0, 0, 0, 0],
        },
        {
            "name": "B5 (Pace)",
            "color_base": "primary",
            "overs": [0.6, 0, 0.9, 0, 0.7, 0, 0, 0, 0, 0,
                       0, 0, 0, 0, 0, 0.8, 0, 0, 0.7, 0],
        },
    ]


# ═══════════════════════════════════════════════════════════
# MATCH INTELLIGENCE (Post-Match Review) DATA
# ═══════════════════════════════════════════════════════════

def get_match_summary() -> dict:
    """Match 14 summary data."""
    return {
        "match_title": "Match 14: Janakpur Bolts vs. Kathmandu Kings",
        "result": "Bolts Win by 14 Runs",
        "team1": {
            "name": "Janakpur Bolts",
            "short": "JKB",
            "score": "184/5",
            "overs": "20.0 Overs",
            "rr": "9.20 RR",
            "is_winner": True,
        },
        "team2": {
            "name": "Kathmandu Kings",
            "short": "KTM",
            "score": "170/8",
            "overs": "20.0 Overs",
            "rr": "8.50 RR",
            "is_winner": False,
        },
        "potm": "A. Khan (68 off 41, 2-24)",
    }


def get_tactical_takeaways() -> list[dict]:
    """Post-match tactical insights."""
    path = get_exports_filepath("tactical_audit_summary.json")
    if path:
        try:
            with open(path, 'r') as f:
                data = json.load(f)
            insights = data.get("key_insights", [])
            if insights:
                results = []
                for insight in insights[:3]:
                    itype = "warning" if "CRITICAL" in insight or "Delta" in insight or "Decline" in insight else "success"
                    title = "Tactical Insight"
                    if "Captaincy" in insight or "Wayne Parnell" in insight:
                        title = "Captaincy Change"
                    elif "chase" in insight or "CHASING" in insight:
                        title = "Chasing Dynamics"
                    elif "Performance" in insight:
                        title = "Season 2 Performance"
                    results.append({
                        "type": itype,
                        "title": title,
                        "desc": insight
                    })
                return results
        except Exception:
            pass
            
    return [
        {
            "type": "success",
            "title": "Middle Overs Acceleration",
            "desc": "Batting RR jumped to 9.8 in overs 11-15, capitalizing on opposition spin.",
        },
        {
            "type": "success",
            "title": "Death Bowling Execution",
            "desc": "Conceded only 28 runs in final 4 overs, utilizing wide yorkers effectively.",
        },
        {
            "type": "warning",
            "title": "Powerplay Dot Balls",
            "desc": "18 dot balls faced in PP; top order struggled against left-arm pace angle.",
        },
    ]


def get_runs_per_over() -> pd.DataFrame:
    """Manhattan chart data — runs scored per over for both teams."""
    return pd.DataFrame({
        "Over": list(range(1, 21)),
        "Bolts": [6, 8, 4, 12, 11, 5, 16, 8, 19, 14,
                   10, 7, 12, 9, 8, 6, 11, 5, 9, 9],
        "Kings": [9, 5, 7, 12, 5, 8, 5, 10, 14, 8,
                  6, 11, 9, 7, 10, 8, 12, 6, 10, 6],
        "Bolts_Wickets": [0, 0, 0, 1, 0, 0, 1, 0, 1, 0,
                           0, 0, 0, 0, 0, 0, 1, 0, 0, 1],
        "Kings_Wickets": [1, 0, 0, 1, 0, 1, 0, 0, 1, 0,
                           0, 1, 0, 0, 1, 0, 0, 1, 0, 1],
    })


def get_cumulative_flow() -> pd.DataFrame:
    """Worm chart data — cumulative runs over by over."""
    rpo = get_runs_per_over()
    return pd.DataFrame({
        "Over": rpo["Over"],
        "Bolts": rpo["Bolts"].cumsum(),
        "Kings": rpo["Kings"].cumsum(),
    })


def get_phase_execution() -> pd.DataFrame:
    """Phase-level batting execution comparison: Match vs Season Average."""
    return pd.DataFrame({
        "Phase": ["Powerplay (1-6)", "Middle (7-15)", "Death (16-20)"],
        "Match RR": [7.33, 9.44, 11.00],
        "Season Avg": [8.10, 8.25, 10.50],
        "Delta": [-0.77, +1.19, +0.50],
    })


def get_partnerships() -> pd.DataFrame:
    """Key partnerships from the match."""
    return pd.DataFrame({
        "Batters": ["A. Khan & R. Singh", "D. Sharma & A. Khan", "K. Malla & S. Jha"],
        "Runs": ["84", "42", "35*"],
        "Balls": [48, 30, 16],
        "SR": [175.0, 140.0, 218.7],
    })


# ═══════════════════════════════════════════════════════════
# BATTING INTELLIGENCE DATA
# ═══════════════════════════════════════════════════════════

def get_batting_tactical_summary() -> list[dict]:
    return [
        {"phase": "Powerplay", "icon": "PP", "text": "Intent is optimal (SR 145+), but early dismissal rate (2.1 avg) is compromising middle-over stability."},
        {"phase": "Middle Overs", "icon": "MO", "text": "Dot ball % is 6% above league average against Left-Arm Orthodox. Strike rotation requires immediate addressal."},
        {"phase": "Death Overs", "icon": "DO", "text": "Elite execution. Boundary % is top-tier, primarily driven by deep crease positioning against yorker attempts."},
    ]

def get_batting_core_intelligence() -> pd.DataFrame:
    path = get_exports_filepath("s3_batter_forecast.csv")
    if path:
        try:
            df = pd.read_csv(path)
            valid_df = df[df['s2_runs'].notna() & (df['s2_runs'] > 0)].copy()
            if not valid_df.empty:
                # Sort by s2_runs descending, take top 4
                top_batters = valid_df.sort_values(by='s2_runs', ascending=False).head(4)
                
                records = []
                for _, row in top_batters.iterrows():
                    inns = 8  # fallback
                    priority = row.get('priority', 5)
                    fit = "OPTIMAL" if priority >= 8 else "FAVORABLE" if priority >= 6 else "NEUTRAL"
                    
                    records.append({
                        "Player": row['player_name'],
                        "Inns": inns,
                        "Runs": int(row['s2_runs']),
                        "SR": round(row.get('s2_strike_rate', 130.0), 1),
                        "Bndry %": f"{row.get('boundary_pct', 18.0):.1f}%" if 'boundary_pct' in row else "18.5%",
                        "Matchup Fit": fit
                    })
                return pd.DataFrame(records)
        except Exception:
            pass
            
    return pd.DataFrame({
        "Player": ["A. Sharma", "R. Singh", "S. Jha", "K. Malla"],
        "Inns": [8, 9, 8, 7],
        "Runs": [284, 312, 185, 245],
        "SR": [155.2, 142.5, 128.4, 185.4],
        "Bndry %": ["22.4%", "18.5%", "14.2%", "28.5%"],
        "Matchup Fit": ["OPTIMAL", "FAVORABLE", "NEUTRAL", "OPTIMAL"],
    })

# ═══════════════════════════════════════════════════════════
# BOWLING INTELLIGENCE DATA
# ═══════════════════════════════════════════════════════════

def get_bowling_vs_batter_hand() -> list[dict]:
    return [
        {"hand": "LHB", "economy": "8.1", "strike_rate": "18.4"},
        {"hand": "RHB", "economy": "7.2", "strike_rate": "15.2"},
    ]

def get_bowling_tactical_directives() -> list[str]:
    return [
        "Use Lalit Rajbanshi in overs 7–10 against left-heavy middle order to exploit negative match-ups.",
        "Hold back pace variations for the death overs (16-20); avoid exposing slower balls in the powerplay."
    ]

# ═══════════════════════════════════════════════════════════
# MATCHUP ENGINE DATA
# ═══════════════════════════════════════════════════════════

def get_matchup_plan() -> list[str]:
    return [
        "Watch for the wrong'un on the 4th stump line.",
        "High probability of scoring through mid-wicket.",
        "Avoid forcing shots square on the off-side due to protected field."
    ]

# ═══════════════════════════════════════════════════════════
# OPPOSITION REPORT DATA
# ═══════════════════════════════════════════════════════════

def get_opposition_bowling_plans() -> pd.DataFrame:
    return pd.DataFrame({
        "Phase": ["Powerplay (1-6)", "Middle (7-15)", "Death (16-20)"],
        "Primary Tactic": [
            "Deny width, force hitting square off the front foot. Use variations early.",
            "Spin choke. Attack stumps, employ wrong'uns against LHB.",
            "Wide yorkers wide of off-stump, slower bouncers into the pitch."
        ],
        "Key Bowler(s)": ["Pace 1, Spin 1", "Leg Spin", "Death Specialist"],
        "Field Setting Focus": [
            "Deep square leg back early, ring tight on the off-side.",
            "Sweepers on both sides, tight inner ring to stop singles.",
            "Protect straight boundaries, pack the off-side boundary."
        ]
    })


def get_season_match_records() -> pd.DataFrame:
    """Match-level dataset used for KPI and data-quality services in the dashboard."""
    return pd.DataFrame(
        [
            {
                "season": "S1",
                "competition_name": "NPL Season 1",
                "competition_tier": "A",
                "opposition_strength_bucket": "strong",
                "match_context": "league",
                "result": "W",
                "runs_for": 176,
                "runs_against": 162,
                "overs_faced": 20.0,
                "overs_bowled": 20.0,
            },
            {
                "season": "S1",
                "competition_name": "NPL Season 1",
                "competition_tier": "A",
                "opposition_strength_bucket": "balanced",
                "match_context": "league",
                "result": "W",
                "runs_for": 182,
                "runs_against": 170,
                "overs_faced": 20.0,
                "overs_bowled": 20.0,
            },
            {
                "season": "S1",
                "competition_name": "NPL Season 1",
                "competition_tier": "A",
                "opposition_strength_bucket": "strong",
                "match_context": "knockout",
                "result": "W",
                "runs_for": 168,
                "runs_against": 149,
                "overs_faced": 20.0,
                "overs_bowled": 20.0,
            },
            {
                "season": "S2",
                "competition_name": "NPL Season 2",
                "competition_tier": "A",
                "opposition_strength_bucket": "strong",
                "match_context": "league",
                "result": "L",
                "runs_for": 154,
                "runs_against": 171,
                "overs_faced": 20.0,
                "overs_bowled": 20.0,
            },
            {
                "season": "S2",
                "competition_name": "NPL Season 2",
                "competition_tier": "A",
                "opposition_strength_bucket": "balanced",
                "match_context": "league",
                "result": "L",
                "runs_for": 149,
                "runs_against": 165,
                "overs_faced": 20.0,
                "overs_bowled": 20.0,
            },
            {
                "season": "S2",
                "competition_name": "NPL Season 2",
                "competition_tier": "A",
                "opposition_strength_bucket": "strong",
                "match_context": "knockout",
                "result": "W",
                "runs_for": 171,
                "runs_against": 167,
                "overs_faced": 20.0,
                "overs_bowled": 20.0,
            },
            {
                "season": "S3 Prep",
                "competition_name": "KP Oli Cup",
                "competition_tier": "B",
                "opposition_strength_bucket": "balanced",
                "match_context": "high-pressure",
                "result": "W",
                "runs_for": 188,
                "runs_against": 172,
                "overs_faced": 20.0,
                "overs_bowled": 20.0,
            },
            {
                "season": "S3 Prep",
                "competition_name": "KP Oli Cup",
                "competition_tier": "B",
                "opposition_strength_bucket": "strong",
                "match_context": "knockout",
                "result": "L",
                "runs_for": 161,
                "runs_against": 168,
                "overs_faced": 20.0,
                "overs_bowled": 20.0,
            },
            {
                "season": "S3 Prep",
                "competition_name": "President Cup",
                "competition_tier": "C",
                "opposition_strength_bucket": "weak",
                "match_context": "league",
                "result": "W",
                "runs_for": 174,
                "runs_against": 152,
                "overs_faced": 20.0,
                "overs_bowled": 20.0,
            },
        ]
    )


# ═══════════════════════════════════════════════════════════
# NAVIGATION DATA
# ═══════════════════════════════════════════════════════════

NAV_ITEMS = [
    {"icon": "📊", "label": "Dashboard", "key": "dashboard"},
    {"icon": "⚡", "label": "Season Analysis", "key": "team_decline_analysis"},
    {"icon": "👤", "label": "Player Profiles", "key": "player_profiles"},
    {"icon": "🏏", "label": "Batting Analysis", "key": "batting_analysis"},
    {"icon": "🎯", "label": "Bowling Analysis", "key": "bowling_analysis"},
    {"icon": "⚔️", "label": "Matchup Engine", "key": "matchup_engine"},
    {"icon": "🔍", "label": "Opposition Reports", "key": "opposition_reports"},
]

NAV_BOTTOM = [
    {"icon": "", "label": "Settings", "key": "settings"},
    {"icon": "", "label": "Support", "key": "support"},
]
