"""Settings & Status — real application and data status (read-only).

Replaces the "Module In Progress" stub, which promised configuration and
database status that were never shown. This page reports the actual
state: which data source served the dashboard, how much data is loaded,
and how fresh the prediction inputs are. The public deployment has no
user-editable settings, and this page says so instead of implying
otherwise.
"""
import json
import platform

import pandas as pd
import streamlit as st

from src.config.paths import DATA_DIR, PARQUET_DIR

PREDICTIONS_DIR = DATA_DIR / "predictions"


def render_settings():
    st.markdown(
        """
        <div class="jb-page-head">
            <h2 class="page-title">Settings</h2>
            <p class="page-subtitle">Application status, data freshness, and environment info. Read-only in the public deployment.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("### Data Status")
    try:
        matches = pd.read_parquet(
            PARQUET_DIR / "matches.parquet", columns=["match_id", "season"]
        )
        bbb_rows = len(pd.read_parquet(PARQUET_DIR / "ball_by_ball.parquet", columns=["match_id"]))
        seasons = ", ".join(sorted(matches["season"].dropna().unique()))
        st.write(f"- **Matches loaded:** {len(matches)} ({seasons})")
        st.write(f"- **Ball-by-ball deliveries:** {bbb_rows:,}")
    except Exception:
        st.write("- **Matches loaded:** unavailable (parquet data not readable)")

    status_path = PREDICTIONS_DIR / "predictions_status.json"
    if status_path.exists():
        status = json.loads(status_path.read_text())
        st.write(f"- **Ratings as of:** "
                 f"{status.get('data_as_of') or status.get('ratings_as_of', '—')} "
                 f"({status.get('n_matches_ingested', '—')} matches ingested)")
        prov = status.get("provisional", {})
        st.write(f"- **Provisional results recorded:** {prov.get('n_provisional_results', 0)} "
                 f"(superseded: {prov.get('n_superseded_by_official', 0)})")
        st.write("- **Data note:** Cricsheet publication lags real time "
                 "(Season 2 median lag was 8 days), so in-season ratings can "
                 "trail the latest played match.")

    st.markdown("### Environment")
    st.write(f"- **Python:** {platform.python_version()}")
    st.write(f"- **Streamlit:** {st.__version__}")
    st.write("- **Build:** season-intel-v3")
    st.write("- **Configuration:** the public app reads committed parquet "
             "snapshots; there are no user-editable settings.")
