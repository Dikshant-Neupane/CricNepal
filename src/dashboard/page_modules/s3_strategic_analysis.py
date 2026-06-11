"""Season 3 Strategic Analysis — S1 Success vs S2 Decline → S3 Recommendations

Comprehensive analysis comparing Season 1 (champions) vs Season 2 (underperformance)
with data-driven recommendations for Season 3.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from pathlib import Path

from src.dashboard.services.data_loaders import export_path, load_export_csv


def _load_s1_s2_comparison():
    """Load S1 vs S2 phase-wise comparison data."""
    batting = load_export_csv("s1_vs_s2_batting_by_phase.csv")
    bowling = load_export_csv("s1_vs_s2_bowling_by_phase.csv")
    match_context = load_export_csv("s1_vs_s2_match_context.csv")
    return batting, bowling, match_context


def _load_s3_forecasts():
    """Load S3 performance forecasts."""
    bowler_forecast = load_export_csv("s3_phase_bowler_forecast.csv")
    batter_forecast = load_export_csv("s3_batter_forecast.csv")
    return bowler_forecast, batter_forecast


def _phase_delta_card(phase_name: str, s1_val: float, s2_val: float, metric_name: str, 
                      better_lower: bool = False, unit: str = ""):
    """Render a phase comparison card showing S1→S2 change."""
    delta = s2_val - s1_val
    delta_pct = (delta / s1_val * 100) if s1_val != 0 else 0
    
    # Determine if improvement or decline
    if better_lower:
        is_improvement = delta < 0
        arrow = "▼" if delta < 0 else "▲"
        color = "#1a6b51" if is_improvement else "#c44b4f"
    else:
        is_improvement = delta > 0
        arrow = "▲" if delta > 0 else "▼"
        color = "#1a6b51" if is_improvement else "#c44b4f"
    
    status = "✅ Improved" if is_improvement else "🔻 Declined"
    
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-card-label">{phase_name} {metric_name}</div>
        <div style="display:flex; justify-content:space-between; align-items:flex-end; margin-top:8px;">
            <div>
                <div style="font-size:13px; color:var(--on-surface-variant);">S1: {s1_val:.2f}{unit}</div>
                <div style="font-size:13px; color:var(--on-surface-variant);">S2: {s2_val:.2f}{unit}</div>
            </div>
            <div style="text-align:right;">
                <div style="font-size:18px; font-weight:600; color:{color};">
                    {arrow} {abs(delta):.2f}{unit}
                </div>
                <div style="font-size:11px; color:{color};">
                    ({delta_pct:+.1f}%)
                </div>
            </div>
        </div>
        <div style="margin-top:8px; font-size:12px; color:{color};">{status}</div>
    </div>
    """, unsafe_allow_html=True)


def render_s3_strategic_analysis():
    """Main render function for S3 Strategic Analysis page."""
    
    st.markdown("""
    <div class="jb-page-head">
        <h2 class="page-title">🎯 Season 3 Strategic Analysis</h2>
        <p class="page-subtitle">Why we won S1, why we lost S2, and what to do for S3.
        Data-driven comparison and actionable recommendations.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Load data
    batting_df, bowling_df, match_context = _load_s1_s2_comparison()
    bowler_forecast, batter_forecast = _load_s3_forecasts()
    
    if batting_df is None or bowling_df is None or match_context is None:
        st.error("⚠️ S1 vs S2 comparison data not found. Run analysis scripts first.")
        return
    
    # Get match counts for normalization
    s1_matches = match_context[match_context["season"] == "S1"]["total_matches"].iloc[0]
    s2_matches = match_context[match_context["season"] == "S2"]["total_matches"].iloc[0]
    
    # ========================================================================
    # SECTION 1: EXECUTIVE SUMMARY
    # ========================================================================
    st.markdown("## 📊 Executive Summary")
    
    # Show match counts first
    st.markdown(f"""
    <div style="background:linear-gradient(135deg, rgba(16,59,47,0.1), rgba(16,59,47,0.05)); 
                padding:16px; border-radius:8px; margin-bottom:20px; text-align:center;">
        <strong>Season 1:</strong> {int(s1_matches)} matches (7 wins, 70% win rate) &nbsp;&nbsp;|&nbsp;&nbsp; 
        <strong>Season 2:</strong> {int(s2_matches)} matches (1 win, 14.3% win rate)
        <br><span style="font-size:12px; color:var(--on-surface-variant);">
        All metrics below are normalized per game for fair comparison
        </span>
    </div>
    """, unsafe_allow_html=True)
    
    # Calculate overall season performance (per game)
    s1_batting = batting_df[batting_df["season"] == "S1"]
    s2_batting = batting_df[batting_df["season"] == "S2"]
    s1_bowling = bowling_df[bowling_df["season"] == "S1"]
    s2_bowling = bowling_df[bowling_df["season"] == "S2"]
    
    s1_run_rate_avg = s1_batting["run_rate"].mean()
    s2_run_rate_avg = s2_batting["run_rate"].mean()
    s1_economy_avg = s1_bowling["economy"].mean()
    s2_economy_avg = s2_bowling["economy"].mean()
    
    # Per-game wickets
    s1_wickets_lost_total = s1_batting["wickets_lost"].sum()
    s2_wickets_lost_total = s2_batting["wickets_lost"].sum()
    s1_wickets_taken_total = s1_bowling["wickets_taken"].sum()
    s2_wickets_taken_total = s2_bowling["wickets_taken"].sum()
    
    s1_wickets_lost_pg = s1_wickets_lost_total / s1_matches
    s2_wickets_lost_pg = s2_wickets_lost_total / s2_matches
    s1_wickets_taken_pg = s1_wickets_taken_total / s1_matches
    s2_wickets_taken_pg = s2_wickets_taken_total / s2_matches
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        delta_rr = s2_run_rate_avg - s1_run_rate_avg
        color = "#c44b4f" if delta_rr < 0 else "#1a6b51"
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-card-label">Batting Run Rate</div>
            <div class="metric-card-value">S1: {s1_run_rate_avg:.2f}</div>
            <div class="metric-card-value">S2: {s2_run_rate_avg:.2f}</div>
            <div style="margin-top:8px; font-size:14px; color:{color}; font-weight:600;">
                {delta_rr:+.2f} RPO
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        delta_econ = s2_economy_avg - s1_economy_avg
        color = "#c44b4f" if delta_econ > 0 else "#1a6b51"
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-card-label">Bowling Economy</div>
            <div class="metric-card-value">S1: {s1_economy_avg:.2f}</div>
            <div class="metric-card-value">S2: {s2_economy_avg:.2f}</div>
            <div style="margin-top:8px; font-size:14px; color:{color}; font-weight:600;">
                {delta_econ:+.2f} RPO
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-card-label">Wickets Lost/Game</div>
            <div class="metric-card-value">S1: {s1_wickets_lost_pg:.1f}</div>
            <div class="metric-card-value">S2: {s2_wickets_lost_pg:.1f}</div>
            <div style="margin-top:8px; font-size:14px; color:{"#1a6b51" if s2_wickets_lost_pg < s1_wickets_lost_pg else "#c44b4f"}; font-weight:600;">
                {s2_wickets_lost_pg - s1_wickets_lost_pg:+.1f}
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-card-label">Wickets Taken/Game</div>
            <div class="metric-card-value">S1: {s1_wickets_taken_pg:.1f}</div>
            <div class="metric-card-value">S2: {s2_wickets_taken_pg:.1f}</div>
            <div style="margin-top:8px; font-size:14px; color:{"#1a6b51" if s2_wickets_taken_pg > s1_wickets_taken_pg else "#c44b4f"}; font-weight:600;">
                {s2_wickets_taken_pg - s1_wickets_taken_pg:+.1f}
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<div style='height:24px;'></div>", unsafe_allow_html=True)
    
    # Wickets per game visualization
    st.markdown("### 📉 Wickets Per Game - Phase Breakdown")
    
    # Calculate per-game wickets for each phase
    phases_data = []
    for phase in ["powerplay", "middle", "death"]:
        s1_phase_bowl = bowling_df[(bowling_df["season"] == "S1") & (bowling_df["phase"] == phase)].iloc[0]
        s2_phase_bowl = bowling_df[(bowling_df["season"] == "S2") & (bowling_df["phase"] == phase)].iloc[0]
        
        s1_wkts_pg = s1_phase_bowl["wickets_taken"] / s1_matches
        s2_wkts_pg = s2_phase_bowl["wickets_taken"] / s2_matches
        
        phases_data.append({
            "Phase": phase.capitalize(),
            "S1 Wickets/Game": s1_wkts_pg,
            "S2 Wickets/Game": s2_wkts_pg,
            "Change": s2_wkts_pg - s1_wkts_pg,
            "Change %": ((s2_wkts_pg - s1_wkts_pg) / s1_wkts_pg * 100) if s1_wkts_pg > 0 else 0
        })
    
    phases_df = pd.DataFrame(phases_data)
    
    # Create grouped bar chart
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        name='Season 1',
        x=phases_df["Phase"],
        y=phases_df["S1 Wickets/Game"],
        marker_color='#1a6b51',
        text=phases_df["S1 Wickets/Game"].round(1),
        textposition='outside'
    ))
    
    fig.add_trace(go.Bar(
        name='Season 2',
        x=phases_df["Phase"],
        y=phases_df["S2 Wickets/Game"],
        marker_color='#c44b4f',
        text=phases_df["S2 Wickets/Game"].round(1),
        textposition='outside'
    ))
    
    fig.update_layout(
        barmode='group',
        title="Wickets Taken Per Game by Phase",
        xaxis_title="Phase",
        yaxis_title="Wickets Per Game",
        height=350,
        showlegend=True,
        template="plotly_white",
        font=dict(family="IBM Plex Sans, sans-serif")
    )
    
    st.plotly_chart(fig, width='stretch')
    
    # Show the data table
    phases_display = phases_df.copy()
    phases_display["S1 Wickets/Game"] = phases_display["S1 Wickets/Game"].round(1)
    phases_display["S2 Wickets/Game"] = phases_display["S2 Wickets/Game"].round(1)
    phases_display["Change"] = phases_display["Change"].round(1)
    phases_display["Change %"] = phases_display["Change %"].round(0).astype(int)
    
    st.dataframe(phases_display, width='stretch', hide_index=True)
    
    st.markdown("<div style='height:24px;'></div>", unsafe_allow_html=True)
    
    # Key Findings
    st.markdown("### 🔍 Key Findings")
    
    findings_col1, findings_col2 = st.columns(2)
    
    with findings_col1:
        st.markdown(f"""
        <div style="background:linear-gradient(135deg, rgba(26,107,81,0.1), rgba(26,107,81,0.05)); 
                    padding:20px; border-radius:12px; border-left:4px solid #1a6b51;">
            <h4 style="margin:0 0 12px 0; color:#1a6b51;">✅ Season 1 Success Factors ({int(s1_matches)} matches)</h4>
            <ul style="margin:8px 0; padding-left:20px; line-height:1.8;">
                <li><strong>Powerplay Dominance:</strong> 7.03 RPO strike rate</li>
                <li><strong>Middle Overs Control:</strong> 6.62 economy rate</li>
                <li><strong>Death Bowling:</strong> 3.5 wickets/game in death overs</li>
                <li><strong>Wicket-Taking:</strong> 7.6 wickets/game overall</li>
                <li><strong>Win Rate:</strong> 70% (7/10 matches)</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with findings_col2:
        st.markdown(f"""
        <div style="background:linear-gradient(135deg, rgba(196,75,79,0.1), rgba(196,75,79,0.05)); 
                    padding:20px; border-radius:12px; border-left:4px solid #c44b4f;">
            <h4 style="margin:0 0 12px 0; color:#c44b4f;">🔻 Season 2 Failure Points ({int(s2_matches)} matches)</h4>
            <ul style="margin:8px 0; padding-left:20px; line-height:1.8;">
                <li><strong>Powerplay Collapse:</strong> Drop to 6.28 RPO (-10.7%)</li>
                <li><strong>Death Bowling Leak:</strong> 9.32 economy (+21.4%)</li>
                <li><strong>Wicket-Taking Collapse:</strong> 7.6 → 5.9 wickets/game (-22%)</li>
                <li><strong>Middle Overs Pressure:</strong> Dot ball % dropped 40.9→30.2</li>
                <li><strong>Win Rate Collapse:</strong> 14.3% (1/7 matches)</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<div style='height:32px;'></div>", unsafe_allow_html=True)
    
    # ========================================================================
    # SECTION 2: PHASE-WISE BREAKDOWN
    # ========================================================================
    st.markdown("## 📈 Phase-Wise Performance Analysis")
    
    tabs = st.tabs(["⚡ Powerplay (1-6)", "🎯 Middle Overs (7-15)", "💥 Death Overs (16-20)"])
    
    # Powerplay Tab
    with tabs[0]:
        st.markdown("### Powerplay Analysis (Overs 1-6)")
        
        s1_pp_bat = batting_df[(batting_df["season"] == "S1") & (batting_df["phase"] == "powerplay")].iloc[0]
        s2_pp_bat = batting_df[(batting_df["season"] == "S2") & (batting_df["phase"] == "powerplay")].iloc[0]
        s1_pp_bowl = bowling_df[(bowling_df["season"] == "S1") & (bowling_df["phase"] == "powerplay")].iloc[0]
        s2_pp_bowl = bowling_df[(bowling_df["season"] == "S2") & (bowling_df["phase"] == "powerplay")].iloc[0]
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            _phase_delta_card("Batting", s1_pp_bat["run_rate"], s2_pp_bat["run_rate"], 
                            "Run Rate", better_lower=False, unit=" RPO")
        
        with col2:
            _phase_delta_card("Batting", s1_pp_bat["boundary_pct"], s2_pp_bat["boundary_pct"], 
                            "Boundary %", better_lower=False, unit="%")
        
        with col3:
            _phase_delta_card("Bowling", s1_pp_bowl["economy"], s2_pp_bowl["economy"], 
                            "Economy", better_lower=True, unit=" RPO")
        
        st.markdown("#### 📊 Powerplay Batting Comparison")
        pp_bat_comparison = pd.DataFrame({
            "Metric": ["Run Rate", "Strike Rate", "Dot Ball %", "Boundary %", "Wickets Lost"],
            "Season 1": [
                s1_pp_bat["run_rate"],
                s1_pp_bat["strike_rate"],
                s1_pp_bat["dot_ball_pct"],
                s1_pp_bat["boundary_pct"],
                s1_pp_bat["wickets_lost"]
            ],
            "Season 2": [
                s2_pp_bat["run_rate"],
                s2_pp_bat["strike_rate"],
                s2_pp_bat["dot_ball_pct"],
                s2_pp_bat["boundary_pct"],
                s2_pp_bat["wickets_lost"]
            ]
        })
        pp_bat_comparison["Change"] = pp_bat_comparison["Season 2"] - pp_bat_comparison["Season 1"]
        pp_bat_comparison["Change %"] = (pp_bat_comparison["Change"] / pp_bat_comparison["Season 1"] * 100).round(1)
        
        st.dataframe(pp_bat_comparison, width='stretch', hide_index=True)
        
        st.markdown("#### 💡 Powerplay Recommendations for S3")
        s1_pp_wickets_pg = s1_pp_bat["wickets_lost"] / s1_matches
        s2_pp_wickets_pg = s2_pp_bat["wickets_lost"] / s2_matches
        
        st.markdown(f"""
        - **Restore Aggression:** Target 7+ RPO in powerplay (currently 6.28)
        - **Boundary Focus:** Need 15-16% boundary rate (down from S1's 16.1%)
        - **Top Order Stability:** S2 had {s2_pp_wickets_pg:.1f} wickets/game vs S1's {s1_pp_wickets_pg:.1f} - maintain stability
        - **Bowling Discipline:** S2 economy 6.61 slightly worse than S1 (6.33) - tighten lines
        """)
    
    # Middle Overs Tab
    with tabs[1]:
        st.markdown("### Middle Overs Analysis (Overs 7-15)")
        
        s1_mid_bat = batting_df[(batting_df["season"] == "S1") & (batting_df["phase"] == "middle")].iloc[0]
        s2_mid_bat = batting_df[(batting_df["season"] == "S2") & (batting_df["phase"] == "middle")].iloc[0]
        s1_mid_bowl = bowling_df[(bowling_df["season"] == "S1") & (bowling_df["phase"] == "middle")].iloc[0]
        s2_mid_bowl = bowling_df[(bowling_df["season"] == "S2") & (bowling_df["phase"] == "middle")].iloc[0]
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            _phase_delta_card("Batting", s1_mid_bat["run_rate"], s2_mid_bat["run_rate"], 
                            "Run Rate", better_lower=False, unit=" RPO")
        
        with col2:
            _phase_delta_card("Bowling", s1_mid_bowl["economy"], s2_mid_bowl["economy"], 
                            "Economy", better_lower=True, unit=" RPO")
        
        with col3:
            _phase_delta_card("Bowling", s1_mid_bowl["wicket_rate"], s2_mid_bowl["wicket_rate"], 
                            "Wicket Rate", better_lower=False, unit="")
        
        st.markdown("#### 🚨 Critical Issue: Middle Overs Bowling Collapse")
        s1_mid_wickets_pg = s1_mid_bowl["wickets_taken"] / s1_matches
        s2_mid_wickets_pg = s2_mid_bowl["wickets_taken"] / s2_matches
        wicket_decline_pct = ((s2_mid_wickets_pg - s1_mid_wickets_pg) / s1_mid_wickets_pg * 100)
        
        st.error(f"""
        **Dot Ball % Collapse:** 40.9% (S1) → 30.2% (S2) = **-26% decline**  
        **Wickets/Game Drop:** {s1_mid_wickets_pg:.1f} (S1) → {s2_mid_wickets_pg:.1f} (S2) = **{wicket_decline_pct:.0f}% decline**  
        
        Middle overs is WHERE WE LOST SEASON 2. Opponents scored freely without pressure.
        """)
        
        st.markdown("#### 💡 Middle Overs Recommendations for S3")
        st.markdown(f"""
        - **URGENT:** Restore middle overs wicket-taking (need 2.5-3.0 wickets/game, currently {s2_mid_wickets_pg:.1f})
        - **Dot Ball Pressure:** Target 38-40% dot ball rate (S2's 30.2% too low)
        - **Spinner Effectiveness:** Review spinner economy and wicket contribution
        - **Bowling Rotations:** Identify S1 bowlers who took wickets vs S2 bowlers who leaked
        """)
    
    # Death Overs Tab
    with tabs[2]:
        st.markdown("### Death Overs Analysis (Overs 16-20)")
        
        s1_death_bat = batting_df[(batting_df["season"] == "S1") & (batting_df["phase"] == "death")].iloc[0]
        s2_death_bat = batting_df[(batting_df["season"] == "S2") & (batting_df["phase"] == "death")].iloc[0]
        s1_death_bowl = bowling_df[(bowling_df["season"] == "S1") & (bowling_df["phase"] == "death")].iloc[0]
        s2_death_bowl = bowling_df[(bowling_df["season"] == "S2") & (bowling_df["phase"] == "death")].iloc[0]
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            _phase_delta_card("Batting", s1_death_bat["run_rate"], s2_death_bat["run_rate"], 
                            "Run Rate", better_lower=False, unit=" RPO")
        
        with col2:
            _phase_delta_card("Bowling", s1_death_bowl["economy"], s2_death_bowl["economy"], 
                            "Economy", better_lower=True, unit=" RPO")
        
        with col3:
            _phase_delta_card("Bowling", s1_death_bowl["wickets_taken"], s2_death_bowl["wickets_taken"], 
                            "Wickets", better_lower=False, unit="")
        
        st.markdown("#### 🚨 Critical Issue: Death Bowling Leakage")
        s1_death_wickets_pg = s1_death_bowl["wickets_taken"] / s1_matches
        s2_death_wickets_pg = s2_death_bowl["wickets_taken"] / s2_matches
        
        st.error(f"""
        **Economy Explosion:** 7.68 (S1) → 9.32 (S2) = **+21.4% worse**  
        **Dot Ball Collapse:** 37.7% (S1) → 25.5% (S2) = **-32% decline**  
        **Wickets/Game:** {s1_death_wickets_pg:.1f} (S1) → {s2_death_wickets_pg:.1f} (S2) = **-23% decline**
        
        Death bowling leaked runs in S2. Lost control in critical closing overs.
        """)
        
        st.markdown("#### 💡 Death Overs Recommendations for S3")
        st.markdown("""
        - **Death Specialists:** Identify bowlers with <8.0 economy in death (use S3 forecast data)
        - **Yorker Execution:** Focus on yorker % and wide yorker variations
        - **Plan B Options:** Have 3-4 reliable death bowlers, not just 1-2
        - **Boundary Prevention:** Target <14% boundary rate (S2 was 16.5%)
        """)
    
    st.markdown("<div style='height:32px;'></div>", unsafe_allow_html=True)
    
    # ========================================================================
    # SECTION 3: S3 BOWLING FORECAST & RECOMMENDATIONS
    # ========================================================================
    if bowler_forecast is not None and not bowler_forecast.empty:
        # Validate required columns exist
        required_cols = ["phase", "bowler_name", "s3_economy_proj", "s2_balls", "s2_economy_raw", "specialist_flag"]
        missing_cols = [col for col in required_cols if col not in bowler_forecast.columns]
        
        if missing_cols:
            st.warning(f"⚠️ Bowler forecast data missing columns: {', '.join(missing_cols)}. Skipping forecast section.")
        else:
            st.markdown("## 🎯 Season 3 Bowling Strategy")
            
            st.markdown("""
            Using **Bayesian shrinkage forecasting**, here are our projected best bowlers by phase for S3.
            Focus recruitment and role assignments on these specialists.
            """)
            
            # Death bowling specialists
            st.markdown("### 💥 Death Overs Specialists (Target: <7.5 Economy)")
            
            death_specialists = bowler_forecast[
                (bowler_forecast["phase"].str.lower() == "death") & 
                (bowler_forecast["s3_economy_proj"] < 7.5)
            ].sort_values("s3_economy_proj").head(10)
            
            if not death_specialists.empty:
                death_display = death_specialists[[
                    "bowler_name", "s2_balls", "s2_economy_raw", "s3_economy_proj", "specialist_flag"
                ]].copy()
                death_display.columns = ["Bowler", "S2 Balls", "S2 Economy", "S3 Forecast", "Rating"]
                st.dataframe(death_display, width='stretch', hide_index=True)
                
                top_death = death_specialists.iloc[0]
                st.success(f"""
                **Top Death Bowler:** {top_death['bowler_name']}  
                S2 Economy: {top_death['s2_economy_raw']:.2f} → S3 Forecast: {top_death['s3_economy_proj']:.2f}
                """)
            else:
                st.warning("No death specialists projected <7.5 economy. Need external recruitment.")
            
            # Middle overs workhorses
            st.markdown("### 🎯 Middle Overs Workhorses (Target: <7.0 Economy)")
            
            middle_specialists = bowler_forecast[
                (bowler_forecast["phase"].str.lower() == "middle") & 
                (bowler_forecast["s3_economy_proj"] < 7.0)
            ].sort_values("s3_economy_proj").head(10)
            
            if not middle_specialists.empty:
                middle_display = middle_specialists[[
                    "bowler_name", "s2_balls", "s2_economy_raw", "s3_economy_proj", "specialist_flag"
                ]].copy()
                middle_display.columns = ["Bowler", "S2 Balls", "S2 Economy", "S3 Forecast", "Rating"]
                st.dataframe(middle_display, width='stretch', hide_index=True)
            else:
                st.warning("Limited middle overs specialists. This is our S2 weakness area.")
            
            # Powerplay enforcers
            st.markdown("### ⚡ Powerplay Attack (Target: <6.5 Economy)")
            
            pp_specialists = bowler_forecast[
                (bowler_forecast["phase"].str.lower() == "powerplay") & 
                (bowler_forecast["s3_economy_proj"] < 6.5)
            ].sort_values("s3_economy_proj").head(10)
            
            if not pp_specialists.empty:
                pp_display = pp_specialists[[
                    "bowler_name", "s2_balls", "s2_economy_raw", "s3_economy_proj", "specialist_flag"
                ]].copy()
                pp_display.columns = ["Bowler", "S2 Balls", "S2 Economy", "S3 Forecast", "Rating"]
                st.dataframe(pp_display, width='stretch', hide_index=True)
            else:
                st.info("Powerplay bowling acceptable in S2. Maintain current bowlers.")
    
    st.markdown("<div style='height:32px;'></div>", unsafe_allow_html=True)
    
    # ========================================================================
    # SECTION 4: STRATEGIC ACTION PLAN
    # ========================================================================
    st.markdown("## 🎯 Season 3 Strategic Action Plan")
    
    st.markdown("""
    <div style="background:linear-gradient(135deg, rgba(16,59,47,0.1), rgba(16,59,47,0.05)); 
                padding:24px; border-radius:12px; border-left:4px solid #103b2f;">
    """, unsafe_allow_html=True)
    
    st.markdown("### 🔴 Priority 1: Fix Middle Overs Bowling (CRITICAL)")
    s1_mid_wkts_pg = s1_mid_bowl["wickets_taken"] / s1_matches
    s2_mid_wkts_pg = s2_mid_bowl["wickets_taken"] / s2_matches
    st.markdown(f"""
    **Problem:** Wicket-taking dropped from {s1_mid_wkts_pg:.1f} to {s2_mid_wkts_pg:.1f} wickets/game (-{abs((s2_mid_wkts_pg - s1_mid_wkts_pg) / s1_mid_wkts_pg * 100):.0f}%)  
    **Target:** 2.5-3.0 wickets per game in middle overs (S1 level)  
    **Action:**
    1. Recruit specialist spinners with proven middle overs wicket-taking record
    2. Review S1 bowlers who are NOT in S2 squad (departed impact analysis)
    3. Increase middle overs dot ball % from 30.2% back to 40%+
    4. Use S3 forecast to identify bowlers projected <7.0 economy in middle
    """)
    
    st.markdown("### 🟠 Priority 2: Restore Death Bowling Control")
    
    # Get top death bowler from forecast if available
    top_death_bowler_text = ""
    if bowler_forecast is not None and not bowler_forecast.empty:
        death_bowlers = bowler_forecast[
            (bowler_forecast["phase"].str.lower() == "death") & 
            (bowler_forecast["s3_economy_proj"] < 8.0)
        ].sort_values("s3_economy_proj")
        if not death_bowlers.empty:
            top = death_bowlers.iloc[0]
            top_death_bowler_text = f"3. Use {top['bowler_name']} ({top['s3_economy_proj']:.2f} projected economy) as primary death bowler\n    "
        else:
            top_death_bowler_text = "3. Identify and recruit death specialist (none projected <8.0 economy)\n    "
    else:
        top_death_bowler_text = "3. Assign primary death bowling specialist based on S2 performance\n    "
    
    st.markdown(f"""
    **Problem:** Death economy exploded from 7.68 to 9.32 (+21%)  
    **Target:** <8.0 death economy  
    **Action:**
    1. Assign clear death bowling roles (overs 16-20 specialists)
    2. Practice yorker execution and wide variations
    {top_death_bowler_text}4. Have 3 backup death options (not just 1-2)
    """)
    
    st.markdown("### 🟡 Priority 3: Restore Powerplay Batting Aggression")
    s1_pp_wkts_pg = s1_pp_bat["wickets_lost"] / s1_matches
    s2_pp_wkts_pg = s2_pp_bat["wickets_lost"] / s2_matches
    st.markdown(f"""
    **Problem:** Run rate dropped from 7.03 to 6.28 (-10.7%)  
    **Target:** 7+ RPO in powerplay  
    **Action:**
    1. Open with aggressive intent batters (boundary focus)
    2. Target 15-16% boundary rate in first 6 overs
    3. Accept {s1_pp_wkts_pg:.1f}-{s1_pp_wkts_pg + 0.5:.1f} wickets/game if run rate improves (S2 had {s2_pp_wkts_pg:.1f}, acceptable)
    4. Review S1 opening partnerships vs S2 opening pairs
    """)
    
    st.markdown("### 🟢 Priority 4: Squad Continuity & Chemistry")
    st.markdown("""
    **Problem:** Player departures and new squad integration in S2  
    **Target:** Retain core S1 winners, integrate new players carefully  
    **Action:**
    1. Review departed player impact analysis
    2. Prioritize retained S1 players in XI (if form holds)
    3. New players: phased integration with clear role definition
    4. Build middle order stability (reduce collapse risk)
    """)
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    st.markdown("<div style='height:32px;'></div>", unsafe_allow_html=True)
    
    # ========================================================================
    # FINAL SUMMARY
    # ========================================================================
    st.markdown("## 📝 Final Recommendations Summary")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"""
        <div style="padding:20px; background:rgba(26,107,81,0.1); border-radius:12px;">
            <h4 style="color:#1a6b51; margin-top:0;">✅ What to KEEP from S1 ({int(s1_matches)} games)</h4>
            <ul style="line-height:1.8;">
                <li>Powerplay bowling discipline (6.33 economy)</li>
                <li>Death bowling wicket-taking (3.5 wickets/game)</li>
                <li>Middle overs pressure (3.0 wickets/game)</li>
                <li>Overall team batting aggression (7.25 RPO)</li>
                <li>Wicket-taking mentality (7.6 wickets/game overall)</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div style="padding:20px; background:rgba(196,75,79,0.1); border-radius:12px;">
            <h4 style="color:#c44b4f; margin-top:0;">🔧 What to FIX from S2 ({int(s2_matches)} games)</h4>
            <ul style="line-height:1.8;">
                <li>Middle overs wicket-taking (3.0 → 2.3 wickets/game)</li>
                <li>Death bowling economy (7.68 → 9.32 RPO)</li>
                <li>Powerplay batting aggression (7.03 → 6.28 RPO)</li>
                <li>Overall wicket-taking (7.6 → 5.9 wickets/game)</li>
                <li>Dot ball pressure across all phases</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("""
    ---
    **Data Sources:** S1 vs S2 phase analysis, S3 Bayesian forecasts, player performance deltas  
    **Next Steps:** Review recruiting shortlist, finalize playing XI roles, practice phase-specific plans
    """)
