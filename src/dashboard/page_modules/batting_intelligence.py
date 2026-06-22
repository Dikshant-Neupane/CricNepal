import streamlit as st
import pandas as pd
from ..services.data_loaders import load_export_csv

def _load_phase_data():
    """Load and process S1 vs S2 batting phase data."""
    try:
        df = load_export_csv("s1_vs_s2_batting_by_phase.csv")
        if df is None or df.empty:
            return None
        return df
    except Exception as e:
        st.error(f"Failed to load phase data: {e}")
        return None

def _load_player_stats():
    """Load player batting statistics."""
    try:
        df = load_export_csv("player_batting_stats.csv")
        if df is None or df.empty:
            return None
        return df
    except Exception as e:
        st.error(f"Failed to load player stats: {e}")
        return None

def _load_s3_forecast():
    """Load S3 batter forecast data."""
    try:
        df = load_export_csv("s3_batter_forecast.csv")
        if df is None or df.empty:
            return None
        return df
    except Exception as e:
        st.error(f"Failed to load S3 forecast: {e}")
        return None

def _calculate_phase_metrics(phase_df):
    """Calculate phase-wise tactical insights from real data."""
    if phase_df is None:
        return []
    
    phases = []
    
    for phase_name in ['powerplay', 'middle', 'death']:
        s1 = phase_df[(phase_df['season'] == 'S1') & (phase_df['phase'] == phase_name)]
        s2 = phase_df[(phase_df['season'] == 'S2') & (phase_df['phase'] == phase_name)]
        
        if s1.empty or s2.empty:
            continue
        
        s1_sr = s1['strike_rate'].values[0]
        s2_sr = s2['strike_rate'].values[0]
        s1_dot = s1['dot_ball_pct'].values[0]
        s2_dot = s2['dot_ball_pct'].values[0]
        s1_bnd = s1['boundary_pct'].values[0]
        s2_bnd = s2['boundary_pct'].values[0]
        
        sr_delta = s2_sr - s1_sr
        dot_delta = s2_dot - s1_dot
        bnd_delta = s2_bnd - s1_bnd
        
        # Generate tactical insight
        if phase_name == 'powerplay':
            icon = ''
            if sr_delta < -10:
                text = f"SR declined {abs(sr_delta):.1f} pts. Dot balls up {dot_delta:.1f}%. Aggressive intent lost."
            else:
                text = f"SR change: {sr_delta:+.1f} pts. Boundary rate at {s2_bnd:.1f}%."
        elif phase_name == 'middle':
            icon = ''
            if sr_delta < -5:
                text = f"Consolidation phase weak. SR down {abs(sr_delta):.1f} pts, boundaries down {abs(bnd_delta):.1f}%."
            else:
                text = f"Middle phase stable. SR: {s2_sr:.1f}, rotation effective."
        else:  # death
            icon = ''
            if sr_delta > 5:
                text = f"Death hitting improved! SR up {sr_delta:+.1f} pts. Boundary rate: {s2_bnd:.1f}%."
            else:
                text = f"Death overs SR: {s2_sr:.1f}. Boundary rate: {s2_bnd:.1f}%."
        
        phases.append({
            'icon': icon,
            'phase': phase_name.capitalize(),
            'text': text,
            'sr': f"{s2_sr:.1f}",
            'sr_delta': f"{sr_delta:+.1f} pts",
            'sr_c': '#157347' if sr_delta > 0 else '#b42318',
            'dot': f"{s2_dot:.1f}%",
            'dot_delta': f"{dot_delta:+.1f}%",
            'dot_c': '#b42318' if dot_delta > 0 else '#157347',
            'bnd': f"{s2_bnd:.1f}%",
            'bnd_delta': f"{bnd_delta:+.1f}%",
            'bnd_c': '#157347' if bnd_delta > 0 else '#b42318',
            'dis': 'N/A',
            'dis_delta': '',
            'dis_c': '#666'
        })
    
    return phases

def _generate_insights(phase_df):
    """Generate data-driven tactical insights."""
    if phase_df is None:
        return {
            'insight': 'Insufficient data for analysis.',
            'risk': 'Data quality issues detected.',
            'action': 'Review data pipeline.'
        }
    
    s1_pp = phase_df[(phase_df['season'] == 'S1') & (phase_df['phase'] == 'powerplay')]
    s2_pp = phase_df[(phase_df['season'] == 'S2') & (phase_df['phase'] == 'powerplay')]
    s1_death = phase_df[(phase_df['season'] == 'S1') & (phase_df['phase'] == 'death')]
    s2_death = phase_df[(phase_df['season'] == 'S2') & (phase_df['phase'] == 'death')]
    
    insights = {}
    
    # Identify strongest phase
    if not s2_death.empty and s2_death['strike_rate'].values[0] > s2_pp['strike_rate'].values[0]:
        insights['insight'] = f"Death overs remain strongest phase (SR: {s2_death['strike_rate'].values[0]:.1f}) with {s2_death['boundary_pct'].values[0]:.1f}% boundary rate."
    else:
        insights['insight'] = f"Batting depth concerns. Death overs strike rate: {s2_death['strike_rate'].values[0]:.1f}."
    
    # Identify risk
    if not s2_pp.empty and not s1_pp.empty:
        pp_decline = s2_pp['strike_rate'].values[0] - s1_pp['strike_rate'].values[0]
        if pp_decline < -10:
            insights['risk'] = f"Powerplay SR declined {abs(pp_decline):.1f} pts (S1: {s1_pp['strike_rate'].values[0]:.1f} → S2: {s2_pp['strike_rate'].values[0]:.1f}). Dot ball % increased to {s2_pp['dot_ball_pct'].values[0]:.1f}%."
        else:
            insights['risk'] = f"Powerplay dot ball rate at {s2_pp['dot_ball_pct'].values[0]:.1f}% - rotation issues persist."
    
    # Recommend action
    s1_mid = phase_df[(phase_df['season'] == 'S1') & (phase_df['phase'] == 'middle')]
    s2_mid = phase_df[(phase_df['season'] == 'S2') & (phase_df['phase'] == 'middle')]
    if not s2_mid.empty and not s1_mid.empty:
        mid_decline = s2_mid['strike_rate'].values[0] - s1_mid['strike_rate'].values[0]
        if mid_decline < -5:
            insights['action'] = f"Strengthen middle-order batting. SR declined {abs(mid_decline):.1f} pts in overs 7-15. Target aggressive accumulators."
        else:
            insights['action'] = "Maintain death-over specialists. Consider promoting finishers to middle overs for momentum."
    
    return insights

def render_batting_intelligence():
    st.markdown(
        """
        <div class="jb-page-head">
            <h2 class="page-title">Batting Intelligence</h2>
            <p class="page-subtitle">Phase behavior, performance trends, and data-driven batting insights.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    # Load real data
    phase_df = _load_phase_data()
    player_stats = _load_player_stats()
    s3_forecast = _load_s3_forecast()
    
    if phase_df is None:
        st.error("Unable to load batting phase data. Check data exports.")
        return
    
    # Calculate metrics from real data
    tactical_data = _calculate_phase_metrics(phase_df)
    insights = _generate_insights(phase_df)
    
    # Phase Tactical Summary
    st.markdown("<div class='card'><div class='card-header'><h3>Phase Tactical Summary</h3></div><div class='card-body'>", unsafe_allow_html=True)
    cols = st.columns(3)
    for i, col in enumerate(cols):
        if i < len(tactical_data):
            with col:
                item = tactical_data[i]
                st.markdown(
                    f"""
                    <div class='insight-box' style='height: 100%;'>
                        <div style='font-size:24px; margin-bottom: 8px;'>{item['icon']}</div>
                        <div style='font-weight:700; margin-bottom: 6px; font-size:14px;'>{item['phase']}</div>
                        <div style='font-size:13px; line-height:1.5;'>{item['text']}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    st.markdown("</div></div>", unsafe_allow_html=True)

    st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)
    st.markdown("<h3 class='page-subtitle' style='font-size:18px; color: #17231f; font-weight:700;'>Phase Metrics (S2 Current)</h3>", unsafe_allow_html=True)

    # Phase Metrics Cards
    phase_cols = st.columns(3)

    for i, col in enumerate(phase_cols):
        if i < len(tactical_data):
            p = tactical_data[i]
            phase_name = p['phase']
            
            with col:
                st.markdown(
                    f"""
                    <div class="card" style="padding: 18px;">
                        <h3 style="margin:0 0 14px 0;">{phase_name} <span style="font-size:13px; color:#4a5a54;">Overs {1 if phase_name == 'Powerplay' else 7 if phase_name == 'Middle' else 16}-{6 if phase_name == 'Powerplay' else 15 if phase_name == 'Middle' else 20}</span></h3>
                        <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px;">
                            <div><div style="font-size:11px; color:#4a5a54;">Strike Rate</div><div style="font-size:26px; font-weight:800; color:#103b2f;">{p['sr']}</div><div style="font-size:11px; color:{p['sr_c']};">{p['sr_delta']}</div></div>
                            <div><div style="font-size:11px; color:#4a5a54;">Dot Ball %</div><div style="font-size:26px; font-weight:800; color:#103b2f;">{p['dot']}</div><div style="font-size:11px; color:{p['dot_c']};">{p['dot_delta']}</div></div>
                            <div><div style="font-size:11px; color:#4a5a54;">Boundary %</div><div style="font-size:26px; font-weight:800; color:#103b2f;">{p['bnd']}</div><div style="font-size:11px; color:{p['bnd_c']};">{p['bnd_delta']}</div></div>
                            <div><div style="font-size:11px; color:#4a5a54;">vs S1</div><div style="font-size:16px; font-weight:700; color:{p['sr_c']};">{p['sr_delta']}</div><div style="font-size:11px; color:#4a5a54;">SR Change</div></div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)

    # Player Stats and S3 Forecast
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Retained Batters Performance")
        st.caption("S1 → S2 Comparison")
        
        if player_stats is not None and not player_stats.empty:
            retained = player_stats[player_stats['status'] == 'retained'].copy()
            retained = retained.nlargest(5, 'S2_strike_rate')
            retained['SR Change'] = (retained['S2_strike_rate'] - retained['S1_strike_rate']).round(1)
            
            display_df = retained[['player_name', 'S1_strike_rate', 'S2_strike_rate', 'SR Change', 'S2_matches']].copy()
            display_df.columns = ['Player', 'S1 SR', 'S2 SR', 'Change', 'Matches']
            display_df['S1 SR'] = display_df['S1 SR'].round(1)
            display_df['S2 SR'] = display_df['S2 SR'].round(1)
            display_df['Matches'] = display_df['Matches'].astype(int)
            
            st.dataframe(
                display_df,
                hide_index=True,
                use_container_width=True,
                column_config={
                    "Change": st.column_config.NumberColumn(
                        "Change",
                        format="%.1f",
                    )
                }
            )
        else:
            st.info("Player statistics unavailable")

    with col2:
        st.markdown("### S3 Top Target Batters")
        st.caption("Forecast")
        
        if s3_forecast is not None and not s3_forecast.empty:
            targets = s3_forecast[s3_forecast['recommendation'] == 'TARGET'].copy()
            targets = targets.nlargest(5, 's3_runs_pred')
            
            display_df = targets[['player_name', 's2_runs', 's3_runs_pred', 'sr_trend']].copy()
            display_df.columns = ['Player', 'S2 Runs', 'S3 Pred', 'SR Trend']
            display_df['S2 Runs'] = display_df['S2 Runs'].astype(int)
            display_df['S3 Pred'] = display_df['S3 Pred'].astype(int)
            
            # Add trend icons
            display_df['SR Trend'] = display_df['SR Trend'].apply(
                lambda x: f"{x}" if x == 'IMPROVING' else f"{x}" if x == 'STABLE' else f"{x}"
            )
            
            st.dataframe(
                display_df,
                hide_index=True,
                use_container_width=True
            )
        else:
            st.info("S3 forecast data unavailable")

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
    
    # Data-driven insights
    st.markdown(
        f"""
        <div class="card">
            <div class="card-header"><h3>Data-Driven Insights</h3></div>
            <div class="card-body">
                <div class="insight-box"><strong> Key Finding:</strong> {insights.get('insight', 'Analysis in progress.')}</div>
                <div style="height:8px;"></div>
                <div class="insight-box"><strong> Risk Factor:</strong> {insights.get('risk', 'Monitoring required.')}</div>
                <div style="height:8px;"></div>
                <div class="insight-box"><strong> Recommended Action:</strong> {insights.get('action', 'Continue current strategy.')}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

