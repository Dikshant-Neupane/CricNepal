import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from ..services.data_loaders import load_ball_by_ball_normalized, load_matchup_stats

def render_matchups():
    st.markdown(
        """
        <div class="jb-page-head">
            <h2 class="page-title">Matchup Engine</h2>
            <p class="page-subtitle">Head-to-head probabilities and tactical plans by phase.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    bbb = load_ball_by_ball_normalized()
    if bbb is None or bbb.empty:
        st.error("Ball-by-ball data is unavailable.")
        return

    # Get unique sorted names for selectboxes
    batters = sorted([name for name in bbb['batter_name'].dropna().unique() if str(name).strip()])
    bowlers = sorted([name for name in bbb['bowler_name'].dropna().unique() if str(name).strip()])

    # Default to specific players if they exist, else just the first in the list
    default_batter = "Lokesh Bam" if "Lokesh Bam" in batters else batters[0] if batters else None
    default_bowler = "LN Rajbanshi" if "LN Rajbanshi" in bowlers else bowlers[0] if bowlers else None

    col1, col2 = st.columns([1, 3])
    
    with col1:
        st.markdown("""
        <h3 class="section-header" style="margin-bottom: 16px;">Configuration</h3>
        """, unsafe_allow_html=True)
        
        selected_batter = st.selectbox("Batter", batters, index=batters.index(default_batter) if default_batter else 0)
        selected_bowler = st.selectbox("Bowler", bowlers, index=bowlers.index(default_bowler) if default_bowler else 0)
        
        st.markdown("<div style='margin-bottom: 16px;'></div>", unsafe_allow_html=True)
        st.markdown("<div style='font-size: 14px; font-weight: 600; margin-bottom: 8px;'>Season Filter</div>", unsafe_allow_html=True)
        
        season_filter = st.radio("Season Filter", ["All", "2024", "2023"], horizontal=True, label_visibility="collapsed")
        
        min_threshold = st.slider("Sample Min Threshold Balls", 0, 100, 30, label_visibility="visible")
        
        st.markdown("<div style='margin-top: 18px;'></div>", unsafe_allow_html=True)
        st.button("Run Engine", type="primary", width="stretch")
        
    with col2:
        # Fetch real stats
        stats = load_matchup_stats(selected_batter, selected_bowler, season_filter, min_threshold)
        if not stats:
            st.warning("Could not calculate stats for this matchup.")
            return

        score = stats["score"]
        if score >= 70:
            favor = "Favorable to Batter"
            color = "#b7802f"
            bg = "rgba(183, 128, 47, 0.1)"
        elif score <= 40:
            favor = "Favorable to Bowler"
            color = "#103b2f"
            bg = "rgba(16, 59, 47, 0.1)"
        else:
            favor = "Balanced Matchup"
            color = "#4a5a54"
            bg = "rgba(74, 90, 84, 0.1)"

        # Matchup Score Card
        st.markdown(f"""
        <div class="card" style="margin-bottom: 24px;">
            <div class="card-body" style="display: flex; justify-content: space-between; align-items: center; padding: 32px;">
                <div>
                    <div style="font-size: 12px; font-weight: 600; color: #4a5a54; text-transform: uppercase; letter-spacing: 0.02em; margin-bottom: 8px;">Matchup Score</div>
                    <div style="display: flex; align-items: baseline; gap: 8px;">
                        <span style="font-size: 64px; font-weight: 700; color: #103b2f; line-height: 1;">{score}</span>
                        <span style="font-size: 24px; color: #4a5a54;">/ 100</span>
                    </div>
                </div>
                <div style="text-align: right;">
                    <div style="display: inline-flex; align-items: center; gap: 8px; background: {bg}; color: {color}; padding: 8px 16px; border-radius: 999px; font-size: 14px; font-weight: 600; border: 1px solid rgba(0,0,0,0.05); margin-bottom: 8px;">
                        <span style="width: 8px; height: 8px; background: {color}; border-radius: 50%; display: inline-block;"></span> {favor}
                    </div>
                    <div style="font-size: 12px; color: #4a5a54;">Data Confidence:<br><span style="font-weight: 600; color: #17231f;">{stats['confidence']}</span></div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Stats Cards
        c1, c2, c3, c4 = st.columns(4)
        
        with c1:
            st.markdown(f"""
            <div class="card" style="height: 100%;">
                <div class="card-body">
                    <div style="font-size: 14px; font-weight: 600; margin-bottom: 16px;">Dismissal Prob.</div>
                    <div style="font-size: 32px; font-weight: 700; color: #103b2f; margin-bottom: 8px;">{stats['dismissal_prob']:.1f}%</div>
                    <div style="font-size: 12px; color: #4a5a54;">Per 10 balls faced</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        with c2:
            st.markdown(f"""
            <div class="card" style="height: 100%;">
                <div class="card-body">
                    <div style="font-size: 14px; font-weight: 600; margin-bottom: 16px;">Expected SR</div>
                    <div style="font-size: 32px; font-weight: 700; color: #103b2f; margin-bottom: 8px;">{stats['expected_sr']:.1f}</div>
                    <div style="font-size: 12px; color: #4a5a54;">Runs per 100 balls</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        with c3:
            st.markdown(f"""
            <div class="card" style="height: 100%;">
                <div class="card-body">
                    <div style="font-size: 14px; font-weight: 600; margin-bottom: 16px;">Dot Pressure</div>
                    <div style="font-size: 32px; font-weight: 700; color: #103b2f; margin-bottom: 2px;">{stats['dot_pressure']:.1f}%</div>
                    <div style="font-size: 11px; color: #7d8f88; margin-bottom: 8px;">95% CI: [{stats['ci_lower']:.1f}%, {stats['ci_upper']:.1f}%]</div>
                    <div style="font-size: 12px; color: #4a5a54;">Balls resulting in 0 runs</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        with c4:
            st.markdown(f"""
            <div class="card" style="height: 100%;">
                <div class="card-body">
                    <div style="font-size: 14px; font-weight: 600; margin-bottom: 16px;">Sample Size</div>
                    <div style="font-size: 32px; font-weight: 700; color: #103b2f; margin-bottom: 8px;">{stats['balls_faced']}</div>
                    <div style="font-size: 12px; color: #4a5a54;">Total balls bowled</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        # Recommended Plan
        st.markdown("<div style='margin-bottom: 14px;'></div>", unsafe_allow_html=True)
        
        # Generate dynamic plan based on stats
        plan = []
        if stats['balls_faced'] == 0:
            plan.append("No historical data available for this specific matchup.")
        else:
            if stats['dot_pressure'] > 40:
                plan.append("Batter struggles to rotate strike against this bowler. Set tight field in the ring.")
            else:
                plan.append("Batter rotates strike easily. Protect the boundaries to prevent easy runs.")
                
            if stats['dismissal_prob'] > 10:
                plan.append("High probability of wicket. Bowler should be brought on aggressively when this batter is at crease.")
            elif stats['expected_sr'] > 150:
                plan.append("Batter is extremely aggressive and successful. Use this bowler purely defensively if forced to bowl.")
            
            if stats['expected_sr'] < 100 and stats['dismissal_prob'] < 5:
                plan.append("Batter is safe but slow. Allow the single to bring more aggressive batters on strike.")
        
        st.markdown("""
        <div class="card">
            <div class="card-header" style="background: #103b2f; border-bottom: none; border-radius: 8px 8px 0 0;">
                <h3 style="color: white; display: flex; justify-content: space-between; width: 100%;">
                    <span>Recommended Plan (Data-Driven)</span>
                    <span style="opacity: 0.8;">Detail</span>
                </h3>
            </div>
            <div class="card-body" style="padding: 32px;">
                <p style="font-size: 16px; line-height: 24px; margin-bottom: 24px; color: #17231f;">
                    These insights are generated dynamically from historical ball-by-ball analysis.
                </p>
                <ul style="padding-left: 20px; font-size: 14px; color: #4a5a54; line-height: 24px;">
        """ + "".join([f"<li style='margin-bottom: 12px;'>{p}</li>" for p in plan]) + """
                </ul>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Add Phase Breakdown Chart
        phases = stats.get('phases', [])
        if phases:
            st.markdown("<div style='margin-bottom: 16px;'></div>", unsafe_allow_html=True)
            st.markdown("### Phase-by-Phase Breakdown")
            
            phase_df = pd.DataFrame(phases)
            # Create a combined chart: Bar for runs, Line for SR
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=phase_df['phase'],
                y=phase_df['runs'],
                name='Runs Scored',
                marker_color='#103b2f',
                yaxis='y1'
            ))
            fig.add_trace(go.Scatter(
                x=phase_df['phase'],
                y=phase_df['sr'],
                name='Strike Rate',
                mode='lines+markers+text',
                text=phase_df['sr'].round(0).astype(int).astype(str),
                textposition='top center',
                line=dict(color='#b42318', width=3),
                marker=dict(size=10),
                yaxis='y2'
            ))
            
            fig.update_layout(
                yaxis=dict(title='Runs Scored', side='left', showgrid=False),
                yaxis2=dict(title='Strike Rate', side='right', overlaying='y', showgrid=False, range=[0, max(200, phase_df['sr'].max() * 1.2) if not phase_df.empty else 200]),
                plot_bgcolor='white',
                paper_bgcolor='white',
                margin=dict(l=40, r=40, t=20, b=20),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})


    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
    
    # Decision Summary Logic
    insight = "No historical matchup data." if stats['balls_faced'] == 0 else f"Expected SR is {stats['expected_sr']:.1f} with a dismissal rate of {stats['dismissal_prob']:.1f}% per 10 balls."
    risk = "Unknown risk profile." if stats['balls_faced'] == 0 else f"Dot ball pressure is currently at {stats['dot_pressure']:.1f}%."
    action = "Collect more data." if stats['balls_faced'] == 0 else ("Bowl aggressively" if stats['score'] <= 40 else "Defensive field settings" if stats['score'] >= 70 else "Standard plans apply")
    
    st.markdown(
        f"""
        <div class="card">
            <div class="card-header"><h3>Decision Summary</h3></div>
            <div class="card-body">
                <div class="insight-box"><strong>Insight:</strong> {insight}</div>
                <div style="height:8px;"></div>
                <div class="insight-box"><strong>Risk:</strong> {risk}</div>
                <div style="height:8px;"></div>
                <div class="insight-box"><strong>Recommended Action:</strong> {action}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
