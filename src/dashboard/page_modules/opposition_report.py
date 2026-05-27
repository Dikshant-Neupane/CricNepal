import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from src.dashboard.demo_data import get_opposition_bowling_plans

def load_npl_teams_data():
    """Load roster data for all NPL teams"""
    try:
        import os
        roster_path = "D:/Cric_Data/data/player_rosters/npl_player_rosters_20260521.csv"
        if os.path.exists(roster_path):
            df = pd.read_csv(roster_path)
            # Normalize team names
            df['team'] = df['team'].replace({'Kathmandu Gurkhas': 'Kathmandu Gorkhas'})
            # Calculate wickets_per_match on the fly
            df['wickets_per_match'] = df['wickets_taken'] / df['bowling_matches'].replace(0, 1)
            return df
    except Exception as e:
        print(f"Error loading roster: {e}")
    return None

def analyze_all_teams(df):
    """Analyze all NPL teams for comparison"""
    if df is None:
        return None
    
    teams = sorted(df['team'].unique())
    results = []
    
    for team in teams:
        team_data = df[df['team'] == team]
        s1_data = team_data[team_data['season'] == 'Season 1']
        s2_data = team_data[team_data['season'] == 'Season 2']
        
        s1_avg = s1_data['wickets_per_match'].mean() if len(s1_data) > 0 else 0
        s2_avg = s2_data['wickets_per_match'].mean() if len(s2_data) > 0 else 0
        change_pct = ((s2_avg - s1_avg) / s1_avg * 100) if s1_avg > 0 else 0
        
        results.append({
            'team': team,
            's1_wickets': s1_avg,
            's2_wickets': s2_avg,
            'change_pct': change_pct,
            's1_players': len(s1_data),
            's2_players': len(s2_data)
        })
    
    return pd.DataFrame(results).sort_values('change_pct', ascending=False)

def render_opposition_report():
    st.markdown(
        """
        <div class="jb-page-head">
            <h2 class="page-title">Opposition Intelligence & NPL Comparison</h2>
            <p class="page-subtitle">Tactical analysis, multi-team comparison, and league-wide performance metrics</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    # Create tabs for different analysis types
    tab1, tab2, tab3 = st.tabs([
        "League Comparison",
        "Team Analysis", 
        "Tactical Report"
    ])
    
    with tab1:
        render_league_comparison_tab()
    
    with tab2:
        render_team_analysis_tab()
    
    with tab3:
        render_tactical_report_tab()

def render_league_comparison_tab():
    """NPL league-wide team comparison"""
    st.markdown("### 🏆 NPL Season 2 - All Teams Performance")
    
    df = load_npl_teams_data()
    
    if df is None:
        st.warning("League data not available")
        return
    
    team_analysis = analyze_all_teams(df)
    
    # Display comparison metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Teams", len(team_analysis))
    with col2:
        best_team = team_analysis.iloc[0]['team']
        st.metric("Best Improvement", best_team, f"+{team_analysis.iloc[0]['change_pct']:.1f}%")
    with col3:
        worst_team = team_analysis.iloc[-1]['team']
        st.metric("Largest Decline", worst_team, f"{team_analysis.iloc[-1]['change_pct']:.1f}%")
    
    st.markdown("---")
    
    # Bar chart comparing all teams
    st.markdown("### Team Performance Change (S1 → S2)")
    
    fig = go.Figure()
    
    colors = ['#10b981' if x > 0 else '#ef4444' for x in team_analysis['change_pct']]
    
    fig.add_trace(go.Bar(
        x=team_analysis['team'],
        y=team_analysis['change_pct'],
        marker_color=colors,
        text=[f"{x:+.1f}%" for x in team_analysis['change_pct']],
        textposition='outside'
    ))
    
    # Highlight Janakpur Bolts
    janakpur_idx = team_analysis[team_analysis['team'] == 'Janakpur Bolts'].index
    if len(janakpur_idx) > 0:
        idx = janakpur_idx[0]
        fig.add_trace(go.Scatter(
            x=[team_analysis.iloc[idx]['team']],
            y=[team_analysis.iloc[idx]['change_pct']],
            mode='markers',
            marker=dict(size=15, color='#fbbf24', symbol='star', line=dict(width=2, color='#fff')),
            name='Janakpur Bolts',
            showlegend=True
        ))
    
    fig.update_layout(
        height=400,
        xaxis_title="Team",
        yaxis_title="Performance Change (%)",
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        showlegend=True,
        hovermode='x unified'
    )
    
    st.plotly_chart(fig, width='stretch')
    
    st.markdown("---")
    
    # Detailed table
    st.markdown("### Detailed Team Stats")
    
    display_df = team_analysis[['team', 's1_wickets', 's2_wickets', 'change_pct', 's1_players', 's2_players']].copy()
    display_df.columns = ['Team', 'S1 Avg Wickets', 'S2 Avg Wickets', 'Change %', 'S1 Squad', 'S2 Squad']
    
    # Highlight Janakpur Bolts row
    def highlight_janakpur(row):
        if row['Team'] == 'Janakpur Bolts':
            return ['background-color: rgba(251, 191, 36, 0.2)'] * len(row)
        return [''] * len(row)
    
    st.dataframe(
        display_df.style.apply(highlight_janakpur, axis=1).format({
            'S1 Avg Wickets': '{:.2f}',
            'S2 Avg Wickets': '{:.2f}',
            'Change %': '{:+.1f}%'
        }),
        width='stretch',
        hide_index=True,
        height=350
    )
    
    st.info("⭐ **Janakpur Bolts** is highlighted in gold. Use the Team Analysis tab for deep-dive into specific opponents.")

def render_team_analysis_tab():
    """Detailed analysis of a selected opposition team"""
    st.markdown("### Opposition Team Deep Dive")
    
    df = load_npl_teams_data()
    
    if df is None:
        st.warning("Team data not available")
        return
    
    teams = sorted([t for t in df['team'].unique() if t != 'Janakpur Bolts'])
    
    col1, col2 = st.columns([1, 3])
    with col1:
        selected_team = st.selectbox("Select Opposition Team", teams)
    with col2:
        st.info(f"Analyzing **{selected_team}** roster and performance trends")
    
    # Analyze selected team
    team_data = df[df['team'] == selected_team]
    s1 = team_data[team_data['season'] == 'Season 1']
    s2 = team_data[team_data['season'] == 'Season 2']
    
    # Metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("S1 Squad Size", len(s1))
    with col2:
        st.metric("S2 Squad Size", len(s2))
    with col3:
        retained = len(set(s1['player_name']) & set(s2['player_name']))
        st.metric("Retained Players", retained)
    with col4:
        new_players = len(set(s2['player_name']) - set(s1['player_name']))
        st.metric("New Additions", new_players)
    
    st.markdown("---")
    
    # Top performers
    st.markdown(f"### {selected_team} - Top Performers (Season 2)")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Top Batters")
        top_batters = s2[s2['batting_matches'] > 0].nlargest(5, 'runs_scored')
        if len(top_batters) > 0:
            batter_df = top_batters[['player_name', 'runs_scored', 'strike_rate']].copy()
            batter_df.columns = ['Player', 'Runs', 'Strike Rate']
            st.dataframe(batter_df, width='stretch', hide_index=True)
        else:
            st.info("No batting data")
    
    with col2:
        st.markdown("#### Top Bowlers")
        top_bowlers = s2[s2['bowling_matches'] > 0].nlargest(5, 'wickets_taken')
        if len(top_bowlers) > 0:
            bowler_df = top_bowlers[['player_name', 'wickets_taken', 'economy_rate']].copy()
            bowler_df.columns = ['Player', 'Wickets', 'Economy']
            st.dataframe(bowler_df, width='stretch', hide_index=True)
        else:
            st.info("No bowling data")
    
    st.markdown("---")
    
    # Key changes
    st.markdown("### 📋 Key Roster Changes")
    
    lost_players = set(s1['player_name']) - set(s2['player_name'])
    gained_players = set(s2['player_name']) - set(s1['player_name'])
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### ❌ Players Lost")
        if lost_players:
            for player in sorted(list(lost_players))[:10]:
                st.markdown(f"- {player}")
        else:
            st.info("No players lost")
    
    with col2:
        st.markdown("#### New Additions")
        if gained_players:
            for player in sorted(list(gained_players))[:10]:
                st.markdown(f"- {player}")
        else:
            st.info("No new additions")

def render_tactical_report_tab():
    """Legacy tactical report interface"""
    st.markdown(
        """
        <div class="jb-page-head">
            <h2 class="page-title">Opposition Tactical Blueprint</h2>
            <p class="page-subtitle">Generate opponent-specific plans with tactical risk and matchup context.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    top_a, top_b = st.columns([1, 1])
    with top_a:
        st.button("Analyst Notes", width='stretch')
    with top_b:
        st.button("Export PDF", type="primary", width='stretch')

    # Top Configuration Row
    st.markdown("""
    <div class="card" style="margin-bottom: 32px;">
        <div class="card-body" style="padding: 18px;">
    """, unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
    with col1:
        st.selectbox("Opponent", ["Kathmandu Gorkhas", "Lalitpur Patriots", "Pokhara Rhinos"])
    with col2:
        st.selectbox("Venue", ["TU Cricket Ground", "Mulpani Cricket Ground"])
    with col3:
        st.selectbox("Data Range", ["Last 10 Matches", "All Time", "2024 Season"])
    with col4:
        st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
        st.button("Generate Report", type="primary", width='stretch')

    st.markdown("</div></div>", unsafe_allow_html=True)

    col_left, col_right = st.columns([2, 1])
    
    with col_left:
        # Key Threats
        st.markdown("""
            <div class="card" style="height: 100%;">
            <div class="card-header">
                <h3 style="display: flex; align-items: center; gap: 8px;">
                    <span style="color: var(--error);">Risk</span> Key Threats
                </h3>
            </div>
            <div class="card-body" style="display: flex; gap: 24px; padding: 24px;">
        """, unsafe_allow_html=True)
        
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("""
            <div style="background: var(--surface-container-low); padding: 16px; border-radius: 8px; border: 1px solid var(--border-subtle); height: 100%;">
                <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px;">
                    <div>
                        <div style="font-weight: 600; font-size: 14px;">Kushal Malla</div>
                        <div style="font-size: 12px; color: var(--on-surface-variant);">LHB • Middle Order</div>
                    </div>
                    <div style="background: rgba(186, 26, 26, 0.1); color: var(--error); padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: 600;">SR: 185.4</div>
                </div>
                <p style="font-size: 13px; color: var(--on-surface); line-height: 20px; margin-bottom: 16px;">Highly destructive in overs 15-20. Prefers pace on the ball targeting cow corner.</p>
                <div style="background: var(--surface-container); display: inline-block; padding: 4px 8px; border-radius: 4px; font-size: 11px; color: var(--on-surface-variant);">Spin Weakness: Left-Arm Orthodox</div>
            </div>
            """, unsafe_allow_html=True)
            
        with c2:
            st.markdown("""
            <div style="background: var(--surface-container-low); padding: 16px; border-radius: 8px; border: 1px solid var(--border-subtle); height: 100%;">
                <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px;">
                    <div>
                        <div style="font-weight: 600; font-size: 14px;">Sompal Kami</div>
                        <div style="font-size: 12px; color: var(--on-surface-variant);">RFM • Powerplay Bowler</div>
                    </div>
                    <div style="background: var(--primary); color: white; padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: 600;">Econ: 6.2</div>
                </div>
                <p style="font-size: 13px; color: var(--on-surface); line-height: 20px; margin-bottom: 16px;">Consistently hits hard lengths early. Swings it away from the right-hander.</p>
                <div style="background: var(--surface-container); display: inline-block; padding: 4px 8px; border-radius: 4px; font-size: 11px; color: var(--on-surface-variant);">Target Zone: Late Cut / Third Man</div>
            </div>
            """, unsafe_allow_html=True)
            
        st.markdown("</div></div>", unsafe_allow_html=True)

    with col_right:
        # Top Order Vulnerability
        st.markdown("""
            <div class="card" style="height: 100%;">
            <div class="card-header">
                <h3>Top Order Vulnerability</h3>
            </div>
            <div class="card-body" style="padding: 24px;">
                <div style="background: var(--surface-container-low); border-radius: 8px; border: 1px solid var(--outline-variant); height: 200px; display: flex; justify-content: center; align-items: center; position: relative;">
                    <div style="position: absolute; top: 16px; left: 0; right: 0; text-align: center; font-size: 12px; color: var(--on-surface-variant);">Pitch Map (Mockup)</div>
                    <div style="width: 80px; height: 140px; border: 1px solid var(--outline-variant); position: relative;">
                        <div style="position: absolute; bottom: 30px; left: 20px; width: 12px; height: 12px; background: var(--error); border-radius: 50%;"></div>
                        <div style="position: absolute; bottom: 25px; left: 25px; width: 12px; height: 12px; background: var(--error); border-radius: 50%;"></div>
                        <div style="position: absolute; bottom: 20px; left: 22px; width: 12px; height: 12px; background: var(--error); border-radius: 50%;"></div>
                        <div style="position: absolute; top: 40px; right: 20px; width: 6px; height: 6px; background: var(--secondary); border-radius: 50%;"></div>
                        <div style="position: absolute; top: 50px; right: 30px; width: 6px; height: 6px; background: var(--secondary); border-radius: 50%;"></div>
                        <div style="position: absolute; bottom: 0; left: 0; right: 0; height: 20px; border-top: 1px solid var(--outline-variant);"></div>
                    </div>
                    <div style="position: absolute; bottom: 8px; right: 16px; font-size: 10px; color: var(--on-surface-variant); display: flex; align-items: center; gap: 4px;">
                        <span style="width: 6px; height: 6px; background: var(--error); border-radius: 50%; display: inline-block;"></span> Dismissals
                    </div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
    st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)

    # Suggested Bowling Plans
    st.markdown("""
    <div class="card">
        <div class="card-header">
            <h3>Suggested Bowling Plans</h3>
            <a href="#" style="font-size: 14px; color: var(--secondary); font-weight: 600; text-decoration: none;">View Detailed Matchups</a>
        </div>
        <div class="card-body" style="padding: 0;">
    """, unsafe_allow_html=True)
    
    df = get_opposition_bowling_plans()
    
    table_html = """
    <table class="bolts-table">
        <thead>
            <tr>
                <th>Phase</th>
                <th>Primary Tactic</th>
                <th>Key Bowler(s)</th>
                <th>Field Setting Focus</th>
            </tr>
        </thead>
        <tbody>
    """
    
    for _, row in df.iterrows():
        # process key bowlers into tags
        bowlers = row['Key Bowler(s)'].split(", ")
        bowler_tags = "".join([f"<span style='background: var(--surface-container); padding: 4px 8px; border-radius: 4px; font-size: 11px; margin-right: 4px;'>{b}</span>" for b in bowlers])
        
        table_html += f"""
            <tr>
                <td style="white-space: nowrap;">{row['Phase']}</td>
                <td>{row['Primary Tactic']}</td>
                <td><div style="display: flex; gap: 4px; flex-wrap: wrap;">{bowler_tags}</div></td>
                <td>{row['Field Setting Focus']}</td>
            </tr>
        """
        
    table_html += "</tbody></table>"
    st.markdown(table_html, unsafe_allow_html=True)
    st.markdown("</div></div>", unsafe_allow_html=True)

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
    st.markdown(
        """
        <div class="card">
            <div class="card-header"><h3>Decision Summary</h3></div>
            <div class="card-body">
                <div class="insight-box"><strong>Insight:</strong> Middle-order threat profile is strongest in overs 14-18 under pace-on lengths.</div>
                <div style="height:8px;"></div>
                <div class="insight-box"><strong>Risk:</strong> Early width concessions allow low-risk boundary access and collapse your field plan.</div>
                <div style="height:8px;"></div>
                <div class="insight-box"><strong>Recommended Action:</strong> Start with hard-length squeeze and reserve death specialist for overs 17-20.</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
