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
from src.dashboard.demo_data import (
    get_match_summary,
    get_tactical_takeaways,
    get_runs_per_over,
    get_cumulative_flow,
    get_phase_execution,
    get_partnerships,
)
from src.dashboard.components.match_summary import (
    render_match_summary,
    render_tactical_takeaways,
    render_phase_table,
    render_partnerships_table,
)
from src.dashboard.components.ui_patterns import (
    render_page_header,
    render_spacer,
    render_card_start,
    render_card_end,
    render_insight_card
)
from src.dashboard.theme import COLORS


def _build_manhattan_chart() -> go.Figure:
    """Build the Runs Per Over Manhattan bar chart using Plotly."""
    df = get_runs_per_over()

    fig = go.Figure()

    # Bolts bars
    fig.add_trace(go.Bar(
        x=df["Over"],
        y=df["Bolts"],
        name="Bolts",
        marker_color=COLORS["primary"],
        marker_cornerradius=4,
    ))

    # Kings bars
    fig.add_trace(go.Bar(
        x=df["Over"],
        y=df["Kings"],
        name="Kings",
        marker_color=COLORS["outline_variant"],
        marker_cornerradius=4,
    ))

    # Wicket markers for Bolts
    wicket_overs_b = df[df["Bolts_Wickets"] > 0]
    if not wicket_overs_b.empty:
        fig.add_trace(go.Scatter(
            x=wicket_overs_b["Over"],
            y=wicket_overs_b["Bolts"] + 1.2,
            mode="markers",
            marker=dict(color=COLORS["error"], size=8, symbol="circle"),
            name="Wicket (B)",
            showlegend=False,
        ))

    # Wicket markers for Kings
    wicket_overs_k = df[df["Kings_Wickets"] > 0]
    if not wicket_overs_k.empty:
        fig.add_trace(go.Scatter(
            x=wicket_overs_k["Over"],
            y=wicket_overs_k["Kings"] + 1.2,
            mode="markers",
            marker=dict(color=COLORS["error"], size=8, symbol="circle"),
            name="Wicket (K)",
            showlegend=False,
        ))

    fig.update_layout(
        barmode="group",
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(family="Inter, sans-serif", color=COLORS["on_surface"]),
        margin=dict(l=40, r=20, t=10, b=40),
        height=340,
        legend=dict(
            orientation="h",
            yanchor="top",
            y=1.12,
            xanchor="right",
            x=1,
            font=dict(size=12),
        ),
        xaxis=dict(
            title="Over",
            tickmode="linear",
            tick0=1,
            dtick=2,
            gridcolor="rgba(193,200,194,0.2)",
            linecolor=COLORS["outline_variant"],
        ),
        yaxis=dict(
            title="Runs",
            gridcolor="rgba(193,200,194,0.15)",
            linecolor=COLORS["outline_variant"],
        ),
        bargap=0.2,
        bargroupgap=0.05,
    )

    return fig


def _build_worm_chart() -> go.Figure:
    """Build the Cumulative Run Flow worm chart using Plotly."""
    df = get_cumulative_flow()

    fig = go.Figure()

    # Bolts line (solid)
    fig.add_trace(go.Scatter(
        x=df["Over"],
        y=df["Bolts"],
        name="Bolts",
        mode="lines",
        line=dict(color=COLORS["primary"], width=3),
        fill="tonexty" if False else None,
    ))

    # Kings line (dashed)
    fig.add_trace(go.Scatter(
        x=df["Over"],
        y=df["Kings"],
        name="Kings",
        mode="lines",
        line=dict(color=COLORS["outline"], width=2.5, dash="dash"),
    ))

    fig.update_layout(
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(family="Inter, sans-serif", color=COLORS["on_surface"]),
        margin=dict(l=40, r=20, t=10, b=40),
        height=340,
        legend=dict(
            orientation="h",
            yanchor="top",
            y=1.12,
            xanchor="right",
            x=1,
            font=dict(size=12),
        ),
        xaxis=dict(
            title="Over",
            tickmode="linear",
            tick0=1,
            dtick=2,
            gridcolor="rgba(193,200,194,0.15)",
            linecolor=COLORS["outline_variant"],
        ),
        yaxis=dict(
            title="Cumulative Runs",
            gridcolor="rgba(193,200,194,0.15)",
            linecolor=COLORS["outline_variant"],
        ),
    )

    return fig


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
    using_demo = real_matches is None

    if using_demo:
        st.info("ℹ Demo data — real match parquet not available. Showing illustrative match.")
        summary = get_match_summary()
        page_subtitle = summary["match_title"]
    else:
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
        render_tactical_takeaways(get_tactical_takeaways())

    render_spacer(32)

    col_manhattan, col_worm = st.columns(2, gap="medium")

    with col_manhattan:
        render_card_start("Runs Per Over (Illustrative)")
        st.caption("Example — per-over delivery data not available in parquet.")
        fig_manhattan = _build_manhattan_chart()
        st.plotly_chart(fig_manhattan, width="stretch", config={"displayModeBar": False})
        render_card_end()

    with col_worm:
        render_card_start("Cumulative Run Flow (Illustrative)")
        st.caption("Example — per-over delivery data not available in parquet.")
        fig_worm = _build_worm_chart()
        st.plotly_chart(fig_worm, width="stretch", config={"displayModeBar": False})
        render_card_end()

    render_spacer(32)

    col_phase, col_partner = st.columns(2, gap="medium")

    with col_phase:
        render_phase_table(get_phase_execution())

    with col_partner:
        render_partnerships_table(get_partnerships())

    render_spacer(12)

    render_insight_card(
        title="Next-Match Action Pack",
        insights=[
            {
                "label": "Insight",
                "text": "Overs 11-15 acceleration was highest leverage in this win profile.",
                "type": "neutral",
            },
            {
                "label": "Risk",
                "text": "Early dot-ball pressure remains elevated against left-arm pace angles.",
                "type": "warning",
            },
            {
                "label": "Recommended Action",
                "text": "Promote one high-intent right-hander in PP if two dots in first over.",
                "type": "neutral",
            },
        ],
    )
