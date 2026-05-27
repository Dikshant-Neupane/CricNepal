import os
import streamlit as st
import pandas as pd
import plotly.express as px
from src.dashboard.demo_data import get_bowling_phases, get_bowling_vs_batter_hand, get_bowling_tactical_directives

TEAM = "Janakpur Bolts"
BBB_PARQUET = "data/normalized/ball_by_ball_normalized.parquet"


def _render_live_heatmap() -> None:
    """Render bowler runs-conceded heatmap."""
    try:
        bbb = pd.read_parquet(BBB_PARQUET)
        # bbb has no season col — join with matches to get it
        try:
            matches = pd.read_parquet("data/normalized/matches_normalized.parquet")[
                ["match_id", "season"]
            ]
            bbb = bbb.merge(matches, on="match_id", how="left")
        except Exception:
            pass  # proceed without season filter

        jab_bowl = bbb[bbb["bowling_team"] == TEAM].copy()
        # Filter to S2 if available, else all
        if "season" in jab_bowl.columns:
            s2_data = jab_bowl[jab_bowl["season"] == "S2"]
            season_label = "S2"
            if s2_data.empty:
                s2_data = jab_bowl
                season_label = "All Seasons"
        else:
            s2_data = jab_bowl
            season_label = "All Seasons"

        s2_data = s2_data.copy()
        s2_data["over_n"] = pd.to_numeric(s2_data["over"], errors="coerce").astype("Int64")
        pivot = (
            s2_data.groupby(["bowler_name", "over_n"])["runs_total"]
            .sum()
            .reset_index()
        )
        pivot_wide = pivot.pivot_table(
            index="bowler_name", columns="over_n", values="runs_total", aggfunc="sum"
        ).fillna(0)
        # Filter to bowlers with ≥12 balls
        bowl_balls = s2_data.groupby("bowler_name").size()
        top_bowlers = bowl_balls[bowl_balls >= 12].index
        pivot_wide = pivot_wide.loc[pivot_wide.index.isin(top_bowlers)].sort_index()
        pivot_wide.columns = [str(int(c)) if pd.notna(c) else str(c) for c in pivot_wide.columns]
        pivot_wide = pivot_wide.reset_index().rename(columns={"bowler_name": "Bowler"})
        pivot_wide = pivot_wide.set_index("Bowler")

        fig = px.imshow(
            pivot_wide,
            labels=dict(x="Over", y="Bowler", color="Runs Conceded"),
            title=f"Runs Conceded by Over — Janakpur Bowling ({season_label})",
            color_continuous_scale="RdYlGn_r",
            aspect="auto",
            text_auto=True,
        )
        fig.update_layout(
            height=350,
            margin=dict(l=10, r=10, t=40, b=10),
            paper_bgcolor="rgba(0,0,0,0)",
        )
        fig.update_coloraxes(colorbar_title="Runs")
        st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})
        st.caption(f"Data: {season_label}. Bowlers with <12 balls excluded.")
    except Exception as exc:
        st.caption(f"Live heatmap unavailable: {exc}")

def render_bowling_intelligence():
    st.markdown(
        """
        <div class="jb-page-head">
            <h2 class="page-title">Bowling Intelligence</h2>
            <p class="page-subtitle">Phase control, resource allocation, and pressure-over plans.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Bowling Phase Breakdown
    st.markdown("""
    <div class="card" style="margin-bottom: 32px;">
        <div class="card-header">
            <h3>Bowling Phase Breakdown</h3>
        </div>
        <div class="card-body" style="padding: 24px;">
    """, unsafe_allow_html=True)
    
    phases = get_bowling_phases()
    
    cols = st.columns(3)
    for i, col in enumerate(cols):
        with col:
            p = phases[i]
            econ_c = p.get('econ_c', 'var(--on-surface)')
            st.markdown(f"""
            <div style="background: var(--surface-container-low); padding: 16px; border-radius: 8px;">
                <div style="font-size: 12px; font-weight: 600; color: var(--on-surface-variant); margin-bottom: 16px; letter-spacing: 0.02em;">{p['name']}</div>
                <div style="display: flex; justify-content: space-between; margin-bottom: 12px;">
                    <span style="font-size: 14px; color: var(--on-surface-variant);">Economy</span>
                    <span style="font-size: 14px; font-weight: 500; color: {econ_c};">{p['econ']}</span>
                </div>
                <div style="display: flex; justify-content: space-between; margin-bottom: 12px;">
                    <span style="font-size: 14px; color: var(--on-surface-variant);">Wickets</span>
                    <span style="font-size: 14px; font-weight: 500; color: var(--on-surface);">{p['wkts']}</span>
                </div>
                <div style="display: flex; justify-content: space-between; margin-bottom: 12px;">
                    <span style="font-size: 14px; color: var(--on-surface-variant);">Dot %</span>
                    <span style="font-size: 14px; font-weight: 500; color: var(--on-surface);">{p['dot']}</span>
                </div>
                <div style="display: flex; justify-content: space-between; padding-top: 12px; border-top: 1px solid var(--outline-variant);">
                    <span style="font-size: 14px; color: var(--on-surface-variant);">Pressure Index</span>
                    <span style="font-size: 14px; font-weight: 600; color: {p['pressure_c']};">{p['pressure']}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
    st.markdown("</div></div>", unsafe_allow_html=True)

    # Resource Allocation and vs Batter Hand
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("""
        <div class="card" style="height: 100%;">
            <div class="card-header">
                <h3>Resource Allocation by Over (S2)</h3>
            </div>
            <div class="card-body" style="padding: 12px 24px 24px 24px;">
        """, unsafe_allow_html=True)
        _render_live_heatmap()
        st.markdown("</div></div>", unsafe_allow_html=True)
        
    with col2:
        st.markdown("""
            <div class="card" style="height: 100%;">
            <div class="card-header">
                <h3>Split: vs Batter Hand</h3>
            </div>
            <div class="card-body" style="padding: 24px;">
        """, unsafe_allow_html=True)
        
        hands = get_bowling_vs_batter_hand()
        for h in hands:
            st.markdown(f"""
            <div style="background: var(--surface-container-low); padding: 16px; border-radius: 8px; margin-bottom: 16px;">
                <div style="font-size: 12px; font-weight: 600; color: var(--on-surface-variant); margin-bottom: 12px;">vs {h['hand']}</div>
                <div style="display: flex; justify-content: space-between;">
                    <div>
                        <div style="font-size: 12px; color: var(--on-surface-variant);">Economy</div>
                        <div style="font-size: 14px; font-weight: 500; margin-top: 4px;">{h['economy']}</div>
                    </div>
                    <div style="text-align: right;">
                        <div style="font-size: 12px; color: var(--on-surface-variant);">Strike Rate</div>
                        <div style="font-size: 14px; font-weight: 500; margin-top: 4px;">{h['strike_rate']}</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        st.markdown("</div></div>", unsafe_allow_html=True)

    st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)

    # Tactical Directives
    dirs = get_bowling_tactical_directives()
    st.markdown("""
    <div style="background: linear-gradient(135deg, var(--primary), var(--primary-2)); padding: 20px; border-radius: 12px;">
        <h3 style="color: #ffffff; margin: 0 0 18px 0; font-size: 18px; display: flex; align-items: center; gap: 8px;">
            <span style="font-size: 12px; letter-spacing: 0.06em; text-transform: uppercase; opacity: 0.85;">Plan</span> Tactical Directives
        </h3>
    """, unsafe_allow_html=True)
    
    for d in dirs:
        st.markdown(
            f"""
            <div style="background: rgba(255, 255, 255, 0.12); border: 1px solid rgba(255,255,255,0.25); padding: 14px; border-radius: 10px; margin-bottom: 10px; display: flex; align-items: flex-start; gap: 12px;">
                <span style="color: #f6e5c8; font-size: 11px; font-weight: 700; letter-spacing: 0.06em;">ITEM</span>
                <span style="color: #ffffff; font-size: 14px;">{d}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
    st.markdown(
        """
        <div class="card">
            <div class="card-header"><h3>Decision Summary</h3></div>
            <div class="card-body">
                <div class="insight-box"><strong>Insight:</strong> Middle-over control remains your most stable wicket-taking phase.</div>
                <div style="height:8px;"></div>
                <div class="insight-box"><strong>Risk:</strong> Death overs leak value when slower-ball patterns are shown too early.</div>
                <div style="height:8px;"></div>
                <div class="insight-box"><strong>Recommended Action:</strong> Delay variation reveal and keep one specialist fresh for over 19.</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
