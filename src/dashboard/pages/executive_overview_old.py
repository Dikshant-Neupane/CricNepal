"""
Executive Overview — Team Performance Intelligence
Maps to the Team Intelligence HTML mockup.
"""
import streamlit as st
import sys
import os

# Ensure project root is on path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from src.dashboard.demo_data import (
    get_strategic_metrics,
    get_batting_phases,
    get_bowling_phases,
    get_order_contribution,
    get_resource_heatmap,
)
from src.dashboard.components.metric_card import render_metric_row
from src.dashboard.components.phase_card import render_phase_section
from src.dashboard.components.bar_chart import render_order_contribution, render_resource_heatmap


def render_executive_overview():
    """Render the full Executive Overview page."""

    # ── Page Header ──────────────────────────────────────
    st.markdown("""
    <div style="margin-bottom: 48px;">
        <h2 class="page-title">Team Performance Intelligence</h2>
        <p class="page-subtitle">Diagnostic overview of core tactical phases and resource deployment.</p>
    </div>
    """, unsafe_allow_html=True)

    # ── Strategic Metrics Row (3 cards) ──────────────────
    metrics = get_strategic_metrics()
    render_metric_row(metrics)

    st.markdown("<div style='height: 32px;'></div>", unsafe_allow_html=True)

    # ── Phase Analysis Row ───────────────────────────────
    col_bat, col_bowl = st.columns(2)

    with col_bat:
        render_phase_section(
            title="Batting Phase Analysis",
            icon="🏏",
            phases=get_batting_phases(),
        )

    with col_bowl:
        render_phase_section(
            title="Bowling Phase Analysis",
            icon="⚾",
            phases=get_bowling_phases(),
        )

    st.markdown("<div style='height: 32px;'></div>", unsafe_allow_html=True)

    # ── Deep Dives Row ───────────────────────────────────
    col_order, col_heat = st.columns(2)

    with col_order:
        render_order_contribution(get_order_contribution())

    with col_heat:
        render_resource_heatmap(get_resource_heatmap())

    # ── Footer ───────────────────────────────────────────
    st.markdown("""
    <div class="dashboard-footer">
        <span>© 2024 Janakpur Bolts. All Rights Reserved.</span>
        <span>v2.4.1-stable</span>
    </div>
    """, unsafe_allow_html=True)
