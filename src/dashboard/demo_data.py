"""
Janakpur Bolts Dashboard — Demo Data Module
Hardcoded data from the HTML mockups for the demo dashboard.
All functions return data ready for display — no DB dependency.
"""
import pandas as pd


# ═══════════════════════════════════════════════════════════
# TEAM INTELLIGENCE (Executive Overview) DATA
# ═══════════════════════════════════════════════════════════

def get_strategic_metrics() -> list[dict]:
    """Three top-level KPI cards from the Team Intelligence mockup."""
    return [
        {
            "title": "Toss Impact",
            "value": "68%",
            "delta": "+12% vs Lg",
            "delta_type": "positive",
            "description": "Win probability when batting first after winning toss.",
            "icon": "🪙",
        },
        {
            "title": "Chasing Efficiency",
            "value": "72%",
            "delta": "Target < 170",
            "delta_type": "neutral",
            "description": "Win rate when chasing. Drops to 41% > 170.",
            "icon": "📈",
        },
        {
            "title": "Death Economy",
            "value": "9.8",
            "delta": "-0.4 vs Lg",
            "delta_type": "negative",
            "description": "Runs per over conceded in overs 16-20.",
            "icon": "⚠️",
        },
    ]


def get_batting_phases() -> list[dict]:
    """Batting phase analysis — Powerplay / Middle / Death."""
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
        },
    ]


def get_bowling_phases() -> list[dict]:
    """Bowling phase analysis — Powerplay / Middle / Death."""
    return [
        {
            "name": "Powerplay (1-6)",
            "highlight": None,
            "stats": [
                {"label": "Econ", "value": "7.2", "style": "primary"},
                {"label": "Wkt/Ov", "value": "0.25", "style": "primary"},
                {"label": "Dot %", "value": "48%", "style": "accent"},
                {"label": "vs Lg", "value": "-0.5", "style": "accent"},
            ],
        },
        {
            "name": "Middle (7-15)",
            "highlight": None,
            "stats": [
                {"label": "Econ", "value": "7.8", "style": "primary"},
                {"label": "Wkt/Ov", "value": "0.31", "style": "primary"},
                {"label": "Dot %", "value": "32%", "style": "normal"},
                {"label": "vs Lg", "value": "+0.1", "style": "normal"},
            ],
        },
        {
            "name": "Death (16-20)",
            "highlight": "error",
            "stats": [
                {"label": "Econ", "value": "9.8", "style": "error"},
                {"label": "Wkt/Ov", "value": "0.45", "style": "primary"},
                {"label": "Dot %", "value": "25%", "style": "normal"},
                {"label": "vs Lg", "value": "+0.4", "style": "error"},
            ],
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
        {"phase": "Powerplay", "icon": "⚡", "text": "Intent is optimal (SR 145+), but early dismissal rate (2.1 avg) is compromising middle-over stability."},
        {"phase": "Middle Overs", "icon": "🔄", "text": "Dot ball % is 6% above league average against Left-Arm Orthodox. Strike rotation requires immediate addressal."},
        {"phase": "Death Overs", "icon": "🚀", "text": "Elite execution. Boundary % is top-tier, primarily driven by deep crease positioning against yorker attempts."},
    ]

def get_batting_core_intelligence() -> pd.DataFrame:
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


# ═══════════════════════════════════════════════════════════
# NAVIGATION DATA
# ═══════════════════════════════════════════════════════════

NAV_ITEMS = [
    {"icon": "🎛️", "label": "Dashboard", "key": "dashboard"},
    {"icon": "👥", "label": "Team Overview", "key": "team_overview"},
    {"icon": "🔍", "label": "Player Profiles", "key": "player_profiles"},
    {"icon": "🏏", "label": "Batting Analysis", "key": "batting_analysis"},
    {"icon": "⚾", "label": "Bowling Analysis", "key": "bowling_analysis"},
    {"icon": "⚔️", "label": "Matchup Engine", "key": "matchup_engine"},
    {"icon": "📋", "label": "Opposition Reports", "key": "opposition_reports"},
]

NAV_BOTTOM = [
    {"icon": "⚙️", "label": "Settings", "key": "settings"},
    {"icon": "❓", "label": "Support", "key": "support"},
]
