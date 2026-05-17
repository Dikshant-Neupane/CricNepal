"""Executive overview module with stronger hierarchy and clearer strategic narrative."""

import streamlit as st
import pandas as pd
import plotly.express as px

from src.dashboard.services.data_source import load_match_records
from src.dashboard.services.metrics import build_executive_cards
from src.dashboard.services.data_quality import validate_match_records


def _momentum_chart() -> None:
    data = pd.DataFrame(
        {
            "match": ["M1", "M2", "M3", "M4", "M5", "M6"],
            "team_form": [58, 63, 61, 69, 72, 78],
            "middle_over_index": [52, 55, 60, 67, 70, 74],
        }
    )
    fig = px.line(
        data,
        x="match",
        y=["team_form", "middle_over_index"],
        markers=True,
        color_discrete_sequence=["#103b2f", "#b7802f"],
    )
    fig.update_layout(
        height=280,
        margin=dict(l=20, r=10, t=20, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend_title_text="",
        yaxis_title="Index",
        xaxis_title="Recent Matches",
    )
    fig.update_traces(line_width=3)
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})


def render_executive_overview():
    match_df, data_source = load_match_records()
    quality_report = validate_match_records(match_df)

    st.markdown(
        """
        <div class="jb-page-head">
            <h2 class="page-title">Executive Overview</h2>
            <p class="page-subtitle">Fast read on win drivers, risk factors, and immediate tactical priorities.</p>
            <div class="insight-alert">
                <span class="insight-alert-icon">Note</span>
                <p class="insight-alert-text"><span class="insight-label">Focus:</span> Death bowling control remains the highest-impact risk for Season 3.</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4, c5 = st.columns(5)
    cards = build_executive_cards(match_df)
    reliability_delta = (
        f"{quality_report['error_count']} errors, {quality_report['warning_count']} warnings"
        if quality_report["status"] != "healthy"
        else "Contract checks passing"
    )
    cards.append(
        (
            "Data Reliability",
            str(quality_report["reliability_score"]),
            reliability_delta,
            "",
            "metric-card-delta-positive" if quality_report["status"] == "healthy" else "metric-card-delta-negative",
        )
    )

    normalized_cards = []
    for card in cards:
        if len(card) == 4:
            label, value, delta, icon = card
            normalized_cards.append((label, value, delta, icon, "metric-card-delta-positive"))
        else:
            normalized_cards.append(card)

    for col, (label, value, delta, icon, delta_class) in zip([c1, c2, c3, c4, c5], normalized_cards):
        with col:
            delta_text = f"{icon} {delta}".strip()
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-card-label">{label}</div>
                    <div class="metric-card-value">{value}</div>
                    <div class="metric-card-delta {delta_class}">{delta_text}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    source_label = "Live DB" if data_source == "database" else "Demo"
    st.caption(f"Data source: {source_label}")

    st.markdown("<div style='height:18px;'></div>", unsafe_allow_html=True)

    left, right = st.columns([2.2, 1])

    with left:
        st.markdown(
            """
            <div class="card">
                <div class="card-header"><h3>Performance Momentum</h3></div>
                <div class="card-body"></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        _momentum_chart()
        st.markdown(
            """
            <div class="insight-box">
                <strong>Insight:</strong> Middle-over stability and wicket preservation explain most recent win momentum.
            </div>
            """,
            unsafe_allow_html=True,
        )

        a, b = st.columns(2)
        with a:
            st.markdown(
                """
                <div class="card">
                    <div class="card-header"><h3>Top Batting Contributors</h3></div>
                    <div class="card-body">
                        <table class="data-table">
                            <thead><tr><th>Player</th><th class="text-right">Runs</th><th class="text-right">SR</th></tr></thead>
                            <tbody>
                                <tr><td>A. Sharma</td><td class="text-right">342</td><td class="text-right">145.2</td></tr>
                                <tr><td>K. Malla</td><td class="text-right">289</td><td class="text-right">132.8</td></tr>
                                <tr><td>D. Singh</td><td class="text-right">156</td><td class="text-right">168.5</td></tr>
                            </tbody>
                        </table>
                        <div class="insight-box"><strong>Watch:</strong> top-order vs left-arm pace in first 3 overs.</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with b:
            st.markdown(
                """
                <div class="card">
                    <div class="card-header"><h3>Top Bowling Contributors</h3></div>
                    <div class="card-body">
                        <table class="data-table">
                            <thead><tr><th>Player</th><th class="text-right">Wkts</th><th class="text-right">Econ</th></tr></thead>
                            <tbody>
                                <tr><td>S. Kami</td><td class="text-right">14</td><td class="text-right">7.2</td></tr>
                                <tr><td>L. Rajbanshi</td><td class="text-right">11</td><td class="text-right">6.8</td></tr>
                                <tr><td>G. Jha</td><td class="text-right">9</td><td class="text-right text-error">9.5</td></tr>
                            </tbody>
                        </table>
                        <div style="display:flex; gap:8px; margin-top: 8px;">
                            <div class="phase-box" style="flex:1;"><div class="phase-box-label">PP Wkts</div><div class="phase-box-value">18</div></div>
                            <div class="phase-box" style="flex:1;"><div class="phase-box-label">Middle</div><div class="phase-box-value">24</div></div>
                            <div class="phase-box phase-box-error" style="flex:1;"><div class="phase-box-label phase-box-label-error">Death</div><div class="phase-box-value phase-box-value-error">8</div></div>
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    with right:
        st.markdown(
            """
            <div class="section-card">
                <div class="section-card-header section-card-header-primary">
                    <h3 class="section-card-title section-card-title-white">Tactical Command</h3>
                </div>
                <div class="section-card-body">
                    <div class="tactical-box tactical-box-error">
                        <div class="tactical-box-title tactical-box-title-error">Active Warning</div>
                        <div class="tactical-box-body">Opposition left-arm spin threat in overs 7-12.</div>
                    </div>
                    <div class="tactical-box tactical-box-success">
                        <div class="tactical-box-title tactical-box-title-success">Advantage</div>
                        <div class="tactical-box-body">Bolts pace battery in powerplay remains favorable.</div>
                    </div>
                    <div class="insight-box"><strong>Plan:</strong> attack PP with intent, hold two death specialists for 17-20.</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        findings = quality_report.get("findings", [])
        if findings:
            findings_markup = "".join(
                [
                    f"<li><strong>{item['message']}:</strong> {item['details']}</li>"
                    for item in findings[:3]
                ]
            )
            st.markdown(
                f"""
                <div style="height:12px;"></div>
                <div class="card">
                    <div class="card-header"><h3>Data Contract Findings</h3></div>
                    <div class="card-body">
                        <ul style="padding-left: 18px; margin: 0; line-height: 1.5;">
                            {findings_markup}
                        </ul>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                """
                <div style="height:12px;"></div>
                <div class="card">
                    <div class="card-header"><h3>Data Contract Findings</h3></div>
                    <div class="card-body">
                        <div class="insight-box"><strong>Status:</strong> Required fields, tiers, contexts, and result values are valid.</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown(
            """
            <div style="height:12px;"></div>
            <div class="card">
                <div class="card-header"><h3>Next Match Snapshot</h3></div>
                <div class="card-body">
                    <div style="font-size:20px; font-weight:800; color: var(--primary);">Kathmandu Kings</div>
                    <div style="font-size:13px; color: var(--on-surface-variant); margin-bottom: 12px;">May 18, 2026 • TU Cricket Ground</div>
                    <div class="insight-box"><strong>Threat:</strong> middle-over spin choke and late acceleration.</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
