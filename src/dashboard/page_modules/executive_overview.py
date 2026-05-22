"""Executive overview module with stronger hierarchy and clearer strategic narrative."""

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

from src.dashboard.services.data_source import load_match_records
from src.dashboard.services.metrics import build_executive_cards
from src.dashboard.services.data_quality import validate_match_records
from src.dashboard.demo_data import get_exports_filepath


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

    # Update source label to recognize parquet data
    if data_source == "database":
        source_label = "Live DB"
    elif data_source == "parquet":
        source_label = "Parquet (Real Data)"
    else:
        source_label = "Demo"
    
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

        # Dynamic contributor tables from real data
        bat_rows = ""
        bat_path = get_exports_filepath("s3_batter_forecast.csv")
        if bat_path:
            try:
                bdf = pd.read_csv(bat_path)
                top_bat = bdf[bdf['s2_runs'].notna()].nlargest(3, 's2_runs')
                for _, r in top_bat.iterrows():
                    sr_val = f"{r['s2_strike_rate']:.1f}" if pd.notna(r.get('s2_strike_rate')) else "—"
                    bat_rows += f"<tr><td>{r['player_name']}</td><td class='text-right'>{int(r['s2_runs'])}</td><td class='text-right'>{sr_val}</td></tr>"
            except Exception:
                pass
        if not bat_rows:
            bat_rows = "<tr><td colspan='3' style='text-align:center; color:var(--on-surface-variant);'>No data</td></tr>"

        bowl_rows = ""
        pp_wkts, mid_wkts, death_wkts = "—", "—", "—"
        bowl_path = get_exports_filepath("s3_bowler_forecast.csv")
        phase_path = get_exports_filepath("s1_vs_s2_bowling_by_phase.csv")
        if bowl_path:
            try:
                bowldf = pd.read_csv(bowl_path)
                top_bowl = bowldf[bowldf['s2_wickets'].notna()].nlargest(3, 's2_wickets')
                for _, r in top_bowl.iterrows():
                    econ_val = f"{r['s2_economy']:.1f}" if pd.notna(r.get('s2_economy')) else "—"
                    econ_class = 'text-right text-error' if pd.notna(r.get('s2_economy')) and r['s2_economy'] > 8.5 else 'text-right'
                    bowl_rows += f"<tr><td>{r['player_name']}</td><td class='text-right'>{int(r['s2_wickets'])}</td><td class='{econ_class}'>{econ_val}</td></tr>"
            except Exception:
                pass
        if not bowl_rows:
            bowl_rows = "<tr><td colspan='3' style='text-align:center; color:var(--on-surface-variant);'>No data</td></tr>"
        if phase_path:
            try:
                pdf = pd.read_csv(phase_path)
                s2 = pdf[pdf['season'] == 'S2']
                pp_wkts = str(int(s2[s2['phase'] == 'powerplay']['wickets_taken'].values[0]))
                mid_wkts = str(int(s2[s2['phase'] == 'middle']['wickets_taken'].values[0]))
                death_wkts = str(int(s2[s2['phase'] == 'death']['wickets_taken'].values[0]))
            except Exception:
                pass

        a, b = st.columns(2)
        with a:
            st.markdown(
                f"""
                <div class="card">
                    <div class="card-header"><h3>Top Batting Contributors (S2)</h3></div>
                    <div class="card-body">
                        <table class="data-table">
                            <thead><tr><th>Player</th><th class="text-right">Runs</th><th class="text-right">SR</th></tr></thead>
                            <tbody>{bat_rows}</tbody>
                        </table>
                        <div class="insight-box"><strong>Watch:</strong> Powerplay dot-ball rate increased +4.3% in S2 — top-order intent needs review.</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with b:
            st.markdown(
                f"""
                <div class="card">
                    <div class="card-header"><h3>Top Bowling Contributors (S2)</h3></div>
                    <div class="card-body">
                        <table class="data-table">
                            <thead><tr><th>Player</th><th class="text-right">Wkts</th><th class="text-right">Econ</th></tr></thead>
                            <tbody>{bowl_rows}</tbody>
                        </table>
                        <div style="display:flex; gap:8px; margin-top: 8px;">
                            <div class="phase-box" style="flex:1;"><div class="phase-box-label">PP Wkts</div><div class="phase-box-value">{pp_wkts}</div></div>
                            <div class="phase-box" style="flex:1;"><div class="phase-box-label">Middle</div><div class="phase-box-value">{mid_wkts}</div></div>
                            <div class="phase-box phase-box-error" style="flex:1;"><div class="phase-box-label phase-box-label-error">Death</div><div class="phase-box-value phase-box-value-error">{death_wkts}</div></div>
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

        next_date = (datetime.now() + timedelta(days=3)).strftime("%b %d, %Y")
        st.markdown(
            f"""
            <div style="height:12px;"></div>
            <div class="card">
                <div class="card-header"><h3>Season 3 Preparation</h3></div>
                <div class="card-body">
                    <div style="font-size:20px; font-weight:800; color: var(--primary);">NPL Season 3</div>
                    <div style="font-size:13px; color: var(--on-surface-variant); margin-bottom: 12px;">Upcoming • Use Batting & Bowling Intelligence tabs for phase-level prep</div>
                    <div class="insight-box"><strong>Priority:</strong> Address death-over economy regression (+1.64 vs S1) and powerplay batting intent (SR dropped -12.4).</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
