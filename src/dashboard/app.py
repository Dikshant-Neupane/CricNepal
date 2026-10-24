"""
Janakpur Bolts Analytics Dashboard
Main Streamlit Application — Entry Point
"""
import streamlit as st
import sys
import os

# Ensure project root is on path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

# Startup stays lean: page modules are imported lazily inside the router
# (only the page being viewed pays its import cost), and the Plotly theme
# is applied on first use by a chart page — the Season 3 Hub landing page
# renders with neither.
_PLOTLY_THEME_DONE = False


def _ensure_plotly_theme() -> None:
    """Global Plotly default template — white bg + dark text for all
    charts, applied once per process."""
    global _PLOTLY_THEME_DONE
    if _PLOTLY_THEME_DONE:
        return
    _PLOTLY_THEME_DONE = True
    try:
        import plotly.io as pio

        _jb_tpl = pio.templates["plotly_white"].to_plotly_json()
        _jb_tpl["layout"]["font"] = {"color": "#17231f", "family": "IBM Plex Sans, sans-serif"}
        _jb_tpl["layout"]["paper_bgcolor"] = "white"
        _jb_tpl["layout"]["plot_bgcolor"] = "white"
        pio.templates["jb_default"] = _jb_tpl
        pio.templates.default = "jb_default"
    except Exception:
        pass  # non-critical; charts will still render


from src.dashboard.theme import get_theme_css
from src.dashboard.components.sidebar import render_sidebar


#  Page Configuration 
st.set_page_config(
    page_title="Janakpur Bolts Analytics",
    page_icon="J",
    layout="wide",
    initial_sidebar_state="expanded",
)

#  Inject Theme CSS 
st.markdown(get_theme_css(), unsafe_allow_html=True)

#  Top Header 
st.markdown(
    """
    <div class="jb-topbar">
        <div>
            <div class="jb-brand-kicker">Janakpur Bolts Performance Lab</div>
            <div class="jb-brand-title">Season Intelligence Dashboard</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

#  Sidebar Navigation 
active_page = render_sidebar()

#  Page Router — every branch imports only its own page module.
if active_page in ["dashboard", "team_overview", "executive_overview"]:
    _ensure_plotly_theme()
    from src.dashboard.page_modules.executive_overview import render_executive_overview
    render_executive_overview()

elif active_page == "season3_hub":
    from src.dashboard.page_modules.season3_hub import render_season3_hub
    render_season3_hub()

elif active_page == "batting_analysis":
    _ensure_plotly_theme()
    from src.dashboard.page_modules.batting_intelligence import render_batting_intelligence
    render_batting_intelligence()

elif active_page == "bowling_analysis":
    _ensure_plotly_theme()
    from src.dashboard.page_modules.bowling_intelligence import render_bowling_intelligence
    render_bowling_intelligence()

elif active_page == "matchup_engine":
    _ensure_plotly_theme()
    from src.dashboard.page_modules.matchups import render_matchups
    render_matchups()

elif active_page == "opposition_reports":
    _ensure_plotly_theme()
    from src.dashboard.page_modules.opposition_report import render_opposition_report
    render_opposition_report()

elif active_page == "team_decline_analysis":
    _ensure_plotly_theme()
    from src.dashboard.page_modules.team_decline_analysis import render_team_decline_analysis
    render_team_decline_analysis()

elif active_page == "review":
    _ensure_plotly_theme()
    from src.dashboard.page_modules.match_review import render_match_review
    render_match_review()

elif active_page == "s3_recruiting":
    _ensure_plotly_theme()
    from src.dashboard.page_modules.s3_recruiting import render_s3_recruiting
    render_s3_recruiting()

elif active_page == "s3_strategic_analysis":
    _ensure_plotly_theme()
    from src.dashboard.page_modules.s3_strategic_analysis import render_s3_strategic_analysis
    render_s3_strategic_analysis()

elif active_page == "match_predictions":
    _ensure_plotly_theme()
    from src.dashboard.page_modules.match_predictions import render_match_predictions
    render_match_predictions()

elif active_page == "game_plan":
    from src.dashboard.page_modules.game_plan import render_game_plan
    render_game_plan()

elif active_page == "win_probability":
    _ensure_plotly_theme()
    from src.dashboard.page_modules.win_probability import render_win_probability
    render_win_probability()

elif active_page == "phase_analysis":
    _ensure_plotly_theme()
    from src.dashboard.page_modules.phase_analysis import render_phase_analysis
    render_phase_analysis()

elif active_page == "player_archetypes":
    _ensure_plotly_theme()
    from src.dashboard.page_modules.player_archetypes import render_player_archetypes
    render_player_archetypes()

elif active_page == "player_profiles":
    _ensure_plotly_theme()
    from src.dashboard.page_modules.player_profiles import render_player_profiles
    render_player_profiles()

elif active_page == "settings":
    from src.dashboard.page_modules.settings_page import render_settings
    render_settings()

elif active_page == "support":
    from src.dashboard.page_modules.support_page import render_support
    render_support()

#  Coming Soon Stubs 
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
