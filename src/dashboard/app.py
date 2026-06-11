"""
Janakpur Bolts Analytics Dashboard
Main Streamlit Application — Entry Point
"""
import streamlit as st
import sys
import os
from datetime import datetime

# Ensure project root is on path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.dashboard.theme import get_theme_css
from src.dashboard.components.sidebar import render_sidebar
from src.dashboard.page_modules.executive_overview import render_executive_overview
from src.dashboard.page_modules.match_review import render_match_review
from src.dashboard.page_modules.batting_intelligence import render_batting_intelligence
from src.dashboard.page_modules.bowling_intelligence import render_bowling_intelligence
from src.dashboard.page_modules.matchups import render_matchups
from src.dashboard.page_modules.opposition_report import render_opposition_report
from src.dashboard.page_modules.team_decline_analysis import render_team_decline_analysis
from src.dashboard.page_modules.s3_recruiting import render_s3_recruiting
from src.dashboard.page_modules.s3_strategic_analysis import render_s3_strategic_analysis


# ─── Page Configuration ──────────────────────────────────
st.set_page_config(
    page_title="Janakpur Bolts Analytics",
    page_icon="J",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Inject Theme CSS ────────────────────────────────────
st.markdown(get_theme_css(), unsafe_allow_html=True)

# ─── Top Header ──────────────────────────────────────────
today = datetime.now().strftime("%d %b %Y")
st.markdown(
    f"""
    <div class="jb-topbar">
        <div>
            <div class="jb-brand-kicker">Janakpur Bolts Performance Lab</div>
            <div class="jb-brand-title">Season Intelligence Dashboard</div>
        </div>
        <div class="jb-date-pill">{today}</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ─── Sidebar Navigation ─────────────────────────────────
active_page = render_sidebar()

# ─── Page Router ─────────────────────────────────────────
if active_page in ["dashboard", "team_overview", "executive_overview"]:
    render_executive_overview()

elif active_page == "batting_analysis":
    render_batting_intelligence()

elif active_page == "bowling_analysis":
    render_bowling_intelligence()

elif active_page == "matchup_engine":
    render_matchups()

elif active_page == "opposition_reports":
    render_opposition_report()

elif active_page == "team_decline_analysis":
    render_team_decline_analysis()

elif active_page == "review":
    render_match_review()

elif active_page == "s3_recruiting":
    render_s3_recruiting()

elif active_page == "s3_strategic_analysis":
    render_s3_strategic_analysis()

# ─── Coming Soon Stubs ───────────────────────────────────
else:
    LABELS = {
        "player_profiles": ("Player Profiles", "Individual player profiles with career stats, form curves, and shot maps."),
        "settings": ("Settings", "Application configuration, database status, and environment info."),
        "support": ("Support", "Documentation, FAQ, and contact information."),
    }

    label, desc = LABELS.get(active_page, ("Page", "This page is under construction."))

    st.markdown(
        f"""
        <div class="jb-page-head">
            <h2 class="page-title">{label}</h2>
            <p class="page-subtitle">{desc}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="jb-empty">
            <div class="jb-empty-icon">In Progress</div>
            <h3>Module In Progress</h3>
            <p>
                This view will be activated once ingestion, validation, and season intelligence
                pipelines are synced with production data.
            </p>
            <div class="jb-empty-tip">Next: complete tiered tournament ingestion and KPI delta generation.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown(
    """
    <div class="dashboard-footer">
        <span>Janakpur Bolts Analytics</span>
        <span>Build: season-intel-v3</span>
    </div>
    """,
    unsafe_allow_html=True,
)
