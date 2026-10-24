"""Support — what this app is, where the data comes from, and how to
report a problem. Replaces the "Module In Progress" stub, which promised
documentation and contact information that were never provided.
"""
import streamlit as st

REPO_URL = "https://github.com/Dikshant-Neupane/CricNepal"


def render_support():
    st.markdown(
        """
        <div class="jb-page-head">
            <h2 class="page-title">Support</h2>
            <p class="page-subtitle">About this dashboard, its data sources, and how to report a problem.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("### About")
    st.write(
        "The Janakpur Bolts Performance Lab is an analytics dashboard for "
        "Nepal Premier League cricket, built by Dikshant Neupane. It covers "
        "NPL Seasons 1-2 ball-by-ball history and a prospective, "
        "pre-registered forecasting evaluation for Season 3."
    )

    st.markdown("### Data Sources")
    st.write(
        "- **Ball-by-ball data:** Cricsheet (cricsheet.org), the public "
        "cricket data project. Publication typically lags match day; "
        "Season 2's median lag was 8 days.\n"
        "- **Season 3 fixtures:** Cricket Association of Nepal schedule, "
        "including the revised start times published on 20 October 2026.\n"
        "- **Squads:** official Season 3 team rosters as published before "
        "the season."
    )

    st.markdown("### Forecasts — Read This First")
    st.write(
        "Match predictions on this site are an **experimental, prospective "
        "evaluation**, not a validated high-accuracy predictor. Every "
        "forecast is locked in an append-only log before the match, under "
        "a pre-registered methodology, and scored only after official data "
        "is published. In backtesting, the model did **not** beat a simple "
        "higher-Elo baseline — the Season 3 log exists to find out whether "
        "it can. Full methodology: `docs/PREDICTION_SYSTEM.md` and "
        "`docs/PREREGISTRATION_S3.md` in the repository."
    )

    st.markdown("### Report a Problem")
    st.write(
        f"Found a wrong number or a broken page? Open an issue on GitHub: "
        f"{REPO_URL}/issues — please include the page name and what you "
        "expected to see."
    )
    st.write(f"Source code: {REPO_URL}")
