"""
Janakpur Bolts Analytics Dashboard
Main Streamlit Application — Entry Point
"""
import streamlit as st
import sys
import os

# Ensure project root is on path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.dashboard.theme import get_theme_css
from src.dashboard.components.sidebar import render_sidebar
from src.dashboard.pages.executive_overview import render_executive_overview
from src.dashboard.pages.match_review import render_match_review
from src.dashboard.pages.batting_intelligence import render_batting_intelligence
from src.dashboard.pages.bowling_intelligence import render_bowling_intelligence
from src.dashboard.pages.matchups import render_matchups
from src.dashboard.pages.opposition_report import render_opposition_report


# ─── Page Configuration ──────────────────────────────────
st.set_page_config(
    page_title="Janakpur Bolts Analytics",
    page_icon="🏏",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Inject Theme CSS ────────────────────────────────────
st.markdown(get_theme_css(), unsafe_allow_html=True)

# ─── Top Header ──────────────────────────────────────────
st.markdown("""
<div class="top-header">Bolts Elite Performance</div>
""", unsafe_allow_html=True)

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

elif active_page == "review":
    render_match_review()

# ─── Coming Soon Stubs ───────────────────────────────────
else:
    LABELS = {
        "player_profiles": ("🔍 Player Profiles", "Individual player profiles with career stats, form curves, and shot maps."),
        "settings": ("⚙️ Settings", "Application configuration, database status, and environment info."),
        "support": ("❓ Support", "Documentation, FAQ, and contact information."),
    }

    label, desc = LABELS.get(active_page, ("📋 Page", "This page is under construction."))

    st.markdown(f"""
    <div style="margin-bottom: 48px;">
        <h2 class="page-title">{label}</h2>
        <p class="page-subtitle">{desc}</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="card" style="max-width: 600px;">
        <div style="padding: 48px; text-align: center;">
            <div style="font-size: 64px; margin-bottom: 16px;">🚧</div>
            <h3 style="font-size: 24px; font-weight: 600; color: var(--primary); margin-bottom: 8px;">
                Coming Soon
            </h3>
            <p style="font-size: 16px; color: var(--on-surface-variant); line-height: 24px;">
                This module is being built. Data scraping and ingestion pipelines
                need to be completed before this page goes live.
            </p>
            <div style="margin-top: 24px; padding: 12px 24px; background: rgba(44, 105, 78, 0.05);
                        border-radius: 8px; display: inline-block;">
                <span style="font-size: 14px; font-weight: 600; color: var(--secondary);">
                    Check back after data collection phase
                </span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Footer
    st.markdown("""
    <div class="dashboard-footer">
        <span>© 2024 Janakpur Bolts. All Rights Reserved.</span>
        <span>v2.4.1-stable</span>
    </div>
    """, unsafe_allow_html=True)
