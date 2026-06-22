"""
Post-Match Tactical Review — Match Intelligence
Maps to the Match Intelligence HTML mockup.
"""
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import sys
import os

# Ensure project root is on path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from src.dashboard.services.data_loaders import load_matches_normalized
from src.dashboard.components.match_summary import (
    render_match_summary,
)
from src.dashboard.components.ui_patterns import (
    render_page_header,
    render_spacer,
    render_card_start,
    render_card_end,
    render_insight_card
)
from src.dashboard.theme import COLORS

_REVIEW_TEAM = "Janakpur Bolts"

def _load_real_matches() -> pd.DataFrame | None:
    """
    Load Janakpur Bolts match data from the normalised parquet.
    Returns a filtered, selector-labelled DataFrame or None if unavailable.
    """
    df = load_matches_normalized()
    if df is None:
        return None

    team_df = df[
        (df["team_1_name"] == _REVIEW_TEAM) | (df["team_2_name"] == _REVIEW_TEAM)
    ].copy()

    if team_df.empty:
        return None

    team_df["match_date"] = pd.to_datetime(team_df["match_date"], errors="coerce")
    team_df = team_df.sort_values("match_date", ascending=False).reset_index(drop=True)

    team_df["opposition"] = team_df.apply(
        lambda r: r["team_2_name"] if r["team_1_name"] == _REVIEW_TEAM else r["team_1_name"],
        axis=1,
    )
    team_df["result"] = team_df.apply(
        lambda r: "Won" if r.get("winner_name") == _REVIEW_TEAM else "Lost",
        axis=1,
    )
    team_df["selector_label"] = team_df.apply(
        lambda r: (
            f"{r['match_date'].strftime('%d %b %Y')} vs {r['opposition']} — {r['result']}"
            if pd.notna(r["match_date"])
            else f"Unknown date vs {r['opposition']} — {r['result']}"
        ),
        axis=1,
    )
    return team_df


def render_match_review():
    """Render the full Match Review page."""

    real_matches = _load_real_matches()
    
    if real_matches is None:
        st.warning("Match data is not available. Please ensure parquet files are loaded.")
        st.stop()

    labels = real_matches["selector_label"].tolist()
    selected_label = st.selectbox("Select match to review", labels, key="match_selector")
    idx = labels.index(selected_label)
    row = real_matches.iloc[idx]
    summary = {
        "match_title": selected_label,
        "team1": {
            "name": _REVIEW_TEAM,
            "short": "JKB",
            "score": str(row.get("team_1_total_runs", "—")),
            "overs": "20.0 Overs",
            "rr": "—",
            "is_winner": row["result"] == "Won",
        },
        "team2": {
            "name": row["opposition"],
            "short": row["opposition"][:3].upper(),
            "score": str(row.get("team_2_total_runs", "—")),
            "overs": "20.0 Overs",
            "rr": "—",
            "is_winner": row["result"] == "Lost",
        },
        "potm": "—",
    }
    page_subtitle = selected_label

    render_page_header(
        title="Post-Match Tactical Review",
        subtitle=page_subtitle,
        insight_label="Decision Lens",
        insight_text="Confirm repeatable win behaviors and isolate non-repeatable spikes before next match.",
        alert_icon="Key",
    )

    col_summary, col_takeaways = st.columns([2, 1], gap="medium")

    with col_summary:
        render_match_summary(summary)

    with col_takeaways:
        render_card_start("Tactical Takeaways")
        st.info("Tactical takeaways require live match event streaming.")
        render_card_end()

    render_spacer(32)

    col_manhattan, col_worm = st.columns(2, gap="medium")

    with col_manhattan:
        render_card_start("Runs Per Over")
        st.info("Per-over delivery data not available in current dataset.")
        render_card_end()

    with col_worm:
        render_card_start("Cumulative Run Flow")
        st.info("Per-over delivery data not available in current dataset.")
        render_card_end()

    render_spacer(32)

    col_phase, col_partner = st.columns(2, gap="medium")

    with col_phase:
        render_card_start("Phase Execution")
        st.info("Phase execution data requires live match event streaming.")
        render_card_end()

    with col_partner:
        render_card_start("Top Partnerships")
        st.info("Partnership data requires live match event streaming.")
        render_card_end()

    render_spacer(12)

    render_insight_card(
        title="Next-Match Action Pack",
        insights=[
            {
                "label": "Notice",
                "text": "Action pack requires live tactical scouting feed integration.",
                "type": "neutral",
            }
        ],
    )
