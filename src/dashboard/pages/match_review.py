"""
Post-Match Tactical Review — Match Intelligence
Maps to the Match Intelligence HTML mockup.
"""
import streamlit as st
import plotly.graph_objects as go
import sys
import os

# Ensure project root is on path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

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


def render_match_review():
    """Render the full Match Review page."""

    # ── Page Header ──────────────────────────────────────
    summary = get_match_summary()

    st.markdown(f"""
    <div style="margin-bottom: 48px;">
        <h2 class="page-title">Post-Match Tactical Review</h2>
        <p class="page-subtitle">{summary['match_title']}</p>
    </div>
    """, unsafe_allow_html=True)

    # ── Top Row: Summary + Takeaways ─────────────────────
    col_summary, col_takeaways = st.columns([2, 1], gap="medium")

    with col_summary:
        render_match_summary(summary)

    with col_takeaways:
        render_tactical_takeaways(get_tactical_takeaways())

    st.markdown("<div style='height: 32px;'></div>", unsafe_allow_html=True)

    # ── Charts Row: Manhattan + Worm ─────────────────────
    col_manhattan, col_worm = st.columns(2, gap="medium")

    with col_manhattan:
        st.markdown("""
        <div class="card">
            <div class="card-header">
                <h3 style="color: var(--primary);">Runs Per Over</h3>
            </div>
        </div>
        """, unsafe_allow_html=True)
        fig_manhattan = _build_manhattan_chart()
        st.plotly_chart(fig_manhattan, use_container_width=True, config={"displayModeBar": False})

    with col_worm:
        st.markdown("""
        <div class="card">
            <div class="card-header">
                <h3 style="color: var(--primary);">Cumulative Run Flow</h3>
            </div>
        </div>
        """, unsafe_allow_html=True)
        fig_worm = _build_worm_chart()
        st.plotly_chart(fig_worm, use_container_width=True, config={"displayModeBar": False})

    st.markdown("<div style='height: 32px;'></div>", unsafe_allow_html=True)

    # ── Tables Row: Phase Execution + Partnerships ───────
    col_phase, col_partner = st.columns(2, gap="medium")

    with col_phase:
        render_phase_table(get_phase_execution())

    with col_partner:
        render_partnerships_table(get_partnerships())

    # ── Footer ───────────────────────────────────────────
    st.markdown("""
    <div class="dashboard-footer">
        <span>© 2024 Janakpur Bolts. All Rights Reserved.</span>
        <div style="display: flex; gap: 24px;">
            <span>v2.4.1-stable</span>
            <span>System Status</span>
            <span>Privacy Policy</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
