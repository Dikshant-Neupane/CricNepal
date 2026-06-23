import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from src.dashboard.services.data_loaders import load_npl_rosters
from src.config.paths import EXPORT_DIR

# Real NPL teams in this dataset (anti-drift list — these come straight
# from `data/normalized/matches_normalized.parquet`).
NPL_TEAMS = [
    "Biratnagar Kings",
    "Chitwan Rhinos",
    "Janakpur Bolts",
    "Karnali Yaks",
    "Kathmandu Gorkhas",
    "Lumbini Lions",
    "Pokhara Avengers",
    "Sudurpaschim Royals",
]


def get_opposition_bowling_plans() -> pd.DataFrame:
    """
    Generate real bowling plans based on S2 Janakpur Bolts bowlers
    and their phase-specific performance data.
    """
    try:
        # Load phase bowler forecast (has specialist flags and economy by phase)
        phase_df = pd.read_csv(EXPORT_DIR / "s3_phase_bowler_forecast.csv")
        
        # Load roster to get S2 Janakpur Bolts bowlers
        roster_df = load_npl_rosters()
        if roster_df is not None:
            jb_s2 = roster_df[
                (roster_df['team'] == 'Janakpur Bolts') & 
                (roster_df['season'] == 'Season 2') &
                (roster_df['bowling_matches'] > 0)
            ].copy()
            jb_bowlers = set(jb_s2['player_name'].unique())
        else:
            jb_bowlers = set()
        
        # Filter phase data for JB bowlers
        jb_phase = phase_df[phase_df['bowler_name'].isin(jb_bowlers)].copy()
        
        # Build bowling plans for each phase
        plans = []
        
        # Powerplay (1-6)
        pp_bowlers = jb_phase[jb_phase['phase'] == 'Powerplay'].copy()
        if len(pp_bowlers) > 0:
            specialists = pp_bowlers[pp_bowlers['specialist_flag'] == 'SPECIALIST']
            if len(specialists) > 0:
                top_pp = specialists.sort_values('s3_economy_proj').head(2)['bowler_name'].tolist()
                pp_eco = specialists.sort_values('s3_economy_proj').head(2)['s3_economy_proj'].mean()
            else:
                pp_bowlers = pp_bowlers.sort_values('s3_economy_proj')
                top_pp = pp_bowlers.head(2)['bowler_name'].tolist()
                pp_eco = pp_bowlers.head(2)['s3_economy_proj'].mean()
            
            plans.append({
                "Phase": "Powerplay (1-6)",
                "Primary Tactic": f"Attack with pace, exploit new ball. Target economy < {pp_eco:.1f} RPO.",
                "Key Bowler(s)": ", ".join(top_pp) if top_pp else "Best pacers available",
                "Field Setting Focus": "Slip and gully early, deep square leg back for pull shots"
            })
        else:
            plans.append({
                "Phase": "Powerplay (1-6)",
                "Primary Tactic": "Attack with pace, exploit new ball swing",
                "Key Bowler(s)": "Opening bowlers",
                "Field Setting Focus": "Attacking field with slips"
            })
        
        # Middle overs (7-15)
        mid_bowlers = jb_phase[jb_phase['phase'] == 'Middle'].copy()
        if len(mid_bowlers) > 0:
            specialists = mid_bowlers[mid_bowlers['specialist_flag'] == 'SPECIALIST']
            if len(specialists) > 0:
                top_mid = specialists.sort_values('s3_economy_proj').head(2)['bowler_name'].tolist()
                mid_eco = specialists.sort_values('s3_economy_proj').head(2)['s3_economy_proj'].mean()
            else:
                mid_bowlers = mid_bowlers.sort_values('s3_economy_proj')
                top_mid = mid_bowlers.head(2)['bowler_name'].tolist()
                mid_eco = mid_bowlers.head(2)['s3_economy_proj'].mean()
            
            plans.append({
                "Phase": "Middle (7-15)",
                "Primary Tactic": f"Spin control, dry up runs. Target economy < {mid_eco:.1f} RPO.",
                "Key Bowler(s)": ", ".join(top_mid) if top_mid else "Spin options",
                "Field Setting Focus": "Sweepers on both sides, tight inner ring to stop singles"
            })
        else:
            plans.append({
                "Phase": "Middle (7-15)",
                "Primary Tactic": "Spin control, pressure through dot balls",
                "Key Bowler(s)": "Spin options",
                "Field Setting Focus": "Defensive ring with deep fielders"
            })
        
        # Death overs (16-20)
        death_bowlers = jb_phase[jb_phase['phase'] == 'Death'].copy()
        if len(death_bowlers) > 0:
            # Prioritize specialists
            specialists = death_bowlers[death_bowlers['specialist_flag'] == 'SPECIALIST']
            if len(specialists) > 0:
                top_death = specialists.sort_values('s3_economy_proj').head(2)['bowler_name'].tolist()
                death_eco = specialists.sort_values('s3_economy_proj').head(2)['s3_economy_proj'].mean()
            else:
                death_bowlers = death_bowlers.sort_values('s3_economy_proj')
                top_death = death_bowlers.head(2)['bowler_name'].tolist()
                death_eco = death_bowlers.head(2)['s3_economy_proj'].mean()
            
            plans.append({
                "Phase": "Death (16-20)",
                "Primary Tactic": f"Yorkers and slower balls. Target economy < {death_eco:.1f} RPO.",
                "Key Bowler(s)": ", ".join(top_death) if top_death else "Death specialists",
                "Field Setting Focus": "Protect straight boundaries, pack the off-side boundary"
            })
        else:
            plans.append({
                "Phase": "Death (16-20)",
                "Primary Tactic": "Yorkers and wide variations",
                "Key Bowler(s)": "Death specialists",
                "Field Setting Focus": "Straight boundary protection"
            })
        
        return pd.DataFrame(plans)
        
    except Exception as e:
        # Fallback to generic plan if data loading fails
        st.warning(f"Could not load bowling plans from data: {e}")
        return pd.DataFrame({
            "Phase": ["Powerplay (1-6)", "Middle (7-15)", "Death (16-20)"],
            "Primary Tactic": [
                "Attack with pace, exploit new ball swing",
                "Spin control, pressure through dot balls",
                "Yorkers and wide variations"
            ],
            "Key Bowler(s)": ["Opening bowlers", "Spin options", "Death specialists"],
            "Field Setting Focus": [
                "Attacking field with slips",
                "Defensive ring with deep fielders",
                "Straight boundary protection"
            ]
        })


def load_npl_teams_data():
    """Load roster data for all NPL teams (cached, paths centralized)."""
    return load_npl_rosters()

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
        "Team Analysis",
        "League Comparison",
        "Tactical Report",
    ])

    with tab1:
        render_team_analysis_tab()

    with tab2:
        render_league_comparison_tab()

    with tab3:
        render_tactical_report_tab()

def render_league_comparison_tab():
    """NPL league-wide team comparison"""
    st.markdown("###  NPL Season 2 - All Teams Performance")
    
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
            x=[team_analysis.loc[idx]['team']],
            y=[team_analysis.loc[idx]['change_pct']],
            mode='markers',
            marker=dict(size=15, color='#fbbf24', symbol='star', line=dict(width=2, color='#fff')),
            name='Janakpur Bolts',
            showlegend=True
        ))
    
    fig.update_layout(
        height=400,
        xaxis_title="Team",
        yaxis_title="Performance Change (%)",
        plot_bgcolor='white',
        paper_bgcolor='white',
        showlegend=True,
        hovermode='x unified',
        font=dict(color="#17231f"),
        xaxis=dict(tickangle=-30, tickfont=dict(color="#17231f")),
        yaxis=dict(tickfont=dict(color="#17231f"), gridcolor="rgba(0,0,0,0.06)"),
        margin=dict(l=20, r=20, t=40, b=100),
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
    
    st.info(" **Janakpur Bolts** is highlighted in gold. Use the Team Analysis tab for deep-dive into specific opponents.")

def render_team_analysis_tab():
    """Detailed analysis of a selected opposition team"""
    st.markdown("### Opposition Team Deep Dive")
    
    df = load_npl_teams_data()
    
    if df is None:
        st.warning("Team data not available")
        return
    
    teams = sorted([t for t in df['team'].unique() if t != 'Janakpur Bolts'])
    # Default to Pokhara Avengers (key S3 rival) if present, else first team
    default_idx = teams.index('Pokhara Avengers') if 'Pokhara Avengers' in teams else 0

    col1, col2 = st.columns([1, 3])
    with col1:
        selected_team = st.selectbox(
            "Select Opposition Team",
            teams,
            index=default_idx,
            key="opposition_team_selector",
        )
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
    st.markdown("###  Key Roster Changes")
    
    lost_players = set(s1['player_name']) - set(s2['player_name'])
    gained_players = set(s2['player_name']) - set(s1['player_name'])
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("####  Players Lost")
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
        # Use real NPL opponent names (excluding JAB itself)
        opponents = [t for t in NPL_TEAMS if t != "Janakpur Bolts"]
        selected_opp = st.selectbox("Opponent", opponents)
    with col2:
        st.selectbox("Venue", ["Tribhuvan University Cricket Ground"])
    with col3:
        st.selectbox("Data Range", ["S1 + S2", "S2 only", "S1 only"])
    with col4:
        st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
        st.button("Generate Report", type="primary", width='stretch')

    st.markdown("</div></div>", unsafe_allow_html=True)

    from src.dashboard.services.data_loaders import load_ball_by_ball_normalized
    bbb = load_ball_by_ball_normalized()
    
    if bbb is not None:
        # Map selected team to possible string variants in the raw dataset
        if selected_opp == "Kathmandu Gorkhas":
            opp_variants = ["Kathmandu Gorkhas", "Kathmandu Gurkhas"]
        elif selected_opp == "Sudurpaschim Royals":
            opp_variants = ["Sudurpaschim Royals", "Sudur Paschim Royals"]
        else:
            opp_variants = [selected_opp]
            
        opp_bat = bbb[bbb['batting_team'].isin(opp_variants)]
        opp_bowl = bbb[bbb['bowling_team'].isin(opp_variants)]
        

        # Compute league averages for radar charts
        league_bat_sr = 120.0
        league_bat_avg = 20.0
        league_bat_bound = 15.0
        
        league_bowl_econ = 7.5
        league_bowl_sr = 18.0
        league_bowl_dot = 35.0
        
        if bbb is not None and not bbb.empty:
            tot_runs = bbb['runs_off_bat'].sum()
            tot_balls = len(bbb)
            tot_wkts = bbb['is_wicket'].sum()
            tot_bounds = len(bbb[bbb['runs_off_bat'].isin([4, 6])])
            
            league_bat_sr = (tot_runs / tot_balls) * 100 if tot_balls else 120.0
            league_bat_avg = tot_runs / tot_wkts if tot_wkts else 20.0
            league_bat_bound = (tot_bounds / tot_balls) * 100 if tot_balls else 15.0
            
            tot_bowl_runs = bbb['runs_total'].sum()
            tot_dots = len(bbb[bbb['runs_total'] == 0])
            league_bowl_econ = (tot_bowl_runs / tot_balls) * 6 if tot_balls else 7.5
            league_bowl_sr = tot_balls / tot_wkts if tot_wkts else 18.0
            league_bowl_dot = (tot_dots / tot_balls) * 100 if tot_balls else 35.0

        # Threat 1: Top Batter
        top_batter_name = "Unknown"
        top_batter_sr = 0.0
        bat_fig = None
        if not opp_bat.empty:
            bat_stats = opp_bat.groupby('batter_name').agg(
                runs=('runs_off_bat', 'sum'), 
                balls=('match_id', 'count'),
                wkts=('is_wicket', 'sum'),
                bounds=('runs_off_bat', lambda x: (x.isin([4, 6])).sum())
            ).reset_index()
            bat_stats = bat_stats[bat_stats['balls'] > 30].sort_values('runs', ascending=False)
            if not bat_stats.empty:
                top_batter = bat_stats.iloc[0]
                top_batter_name = top_batter['batter_name']
                top_batter_sr = (top_batter['runs'] / top_batter['balls']) * 100
                avg = top_batter['runs'] / top_batter['wkts'] if top_batter['wkts'] > 0 else top_batter['runs']
                bound_pct = (top_batter['bounds'] / top_batter['balls']) * 100
                
                bat_fig = go.Figure()
                bat_fig.add_trace(go.Scatterpolar(
                    r=[league_bat_sr, league_bat_avg, league_bat_bound, league_bat_sr],
                    theta=['Strike Rate', 'Average', 'Boundary %', 'Strike Rate'],
                    fill='toself',
                    name='League Avg',
                    line_color='rgba(125, 143, 136, 0.5)',
                    fillcolor='rgba(125, 143, 136, 0.2)'
                ))
                bat_fig.add_trace(go.Scatterpolar(
                    r=[top_batter_sr, avg, bound_pct, top_batter_sr],
                    theta=['Strike Rate', 'Average', 'Boundary %', 'Strike Rate'],
                    fill='toself',
                    name=top_batter_name,
                    line_color='#b42318',
                    fillcolor='rgba(180, 35, 24, 0.4)'
                ))
                bat_fig.update_layout(
                    polar=dict(radialaxis=dict(visible=False, range=[0, max(200, top_batter_sr)])),
                    showlegend=False,
                    margin=dict(l=20, r=20, t=20, b=20),
                    height=180,
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)'
                )
                
        # Threat 2: Top Bowler
        top_bowler_name = "Unknown"
        top_bowler_econ = 0.0
        bowl_fig = None
        if not opp_bowl.empty:
            bowl_stats = opp_bowl.groupby('bowler_name').agg(
                runs=('runs_total', 'sum'), 
                balls=('match_id', 'count'),
                wkts=('is_wicket', 'sum'),
                dots=('runs_total', lambda x: (x == 0).sum())
            ).reset_index()
            bowl_stats = bowl_stats[bowl_stats['balls'] > 30].sort_values('balls', ascending=False)
            if not bowl_stats.empty:
                top_bowler = bowl_stats.iloc[0]
                top_bowler_name = top_bowler['bowler_name']
                top_bowler_econ = (top_bowler['runs'] / top_bowler['balls']) * 6
                sr = top_bowler['balls'] / top_bowler['wkts'] if top_bowler['wkts'] > 0 else top_bowler['balls']
                dot_pct = (top_bowler['dots'] / top_bowler['balls']) * 100
                
                # For bowlers, lower Econ and lower SR is better. We invert them for radar or just show raw.
                # Let's show raw but note that smaller is better for econ/sr.
                bowl_fig = go.Figure()
                bowl_fig.add_trace(go.Scatterpolar(
                    r=[league_bowl_econ, league_bowl_sr, league_bowl_dot, league_bowl_econ],
                    theta=['Economy', 'Strike Rate', 'Dot %', 'Economy'],
                    fill='toself',
                    name='League Avg',
                    line_color='rgba(125, 143, 136, 0.5)',
                    fillcolor='rgba(125, 143, 136, 0.2)'
                ))
                bowl_fig.add_trace(go.Scatterpolar(
                    r=[top_bowler_econ, sr, dot_pct, top_bowler_econ],
                    theta=['Economy', 'Strike Rate', 'Dot %', 'Economy'],
                    fill='toself',
                    name=top_bowler_name,
                    line_color='#103b2f',
                    fillcolor='rgba(16, 59, 47, 0.4)'
                ))
                bowl_fig.update_layout(
                    polar=dict(radialaxis=dict(visible=False, range=[0, max(60, dot_pct)])),
                    showlegend=False,
                    margin=dict(l=20, r=20, t=20, b=20),
                    height=180,
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)'
                )

                
        # Top Order vulnerability
        vuln_msg = "Top order struggles against pace in the powerplay."
        if not opp_bat.empty:
            pp_bat = opp_bat[opp_bat['over'] < 6]
            if not pp_bat.empty:
                pp_wkts = pp_bat['is_wicket'].sum()
                pp_matches = pp_bat['match_id'].nunique()
                vuln_msg = f"Average {pp_wkts/pp_matches:.1f} wickets lost in Powerplay." if pp_matches else vuln_msg
                
    else:
        top_batter_name = "No Data"
        top_batter_sr = 0.0
        top_bowler_name = "No Data"
        top_bowler_econ = 0.0
        vuln_msg = "Data unavailable."

    col_left, col_right = st.columns([2, 1])
    
    with col_left:
        # Key Threats
        st.markdown(f"""
            <div class="card" style="height: 100%;">
            <div class="card-header">
                <h3 style="display: flex; align-items: center; gap: 8px;">
                    <span style="color: #b42318;">Risk</span> Key Threats ({selected_opp})
                </h3>
            </div>
            <div class="card-body" style="display: flex; gap: 24px; padding: 24px;">
        """, unsafe_allow_html=True)
        
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"""
            <div style="background: #edf2ef; padding: 16px; border-radius: 8px; border: 1px solid #d9e2dd; height: 100%;">
                <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 4px;">
                    <div>
                        <div style="font-weight: 600; font-size: 14px;">{top_batter_name}</div>
                        <div style="font-size: 12px; color: #4a5a54;">Key Batter</div>
                    </div>
                    <div style="background: rgba(186, 26, 26, 0.1); color: #b42318; padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: 600;">SR: {top_batter_sr:.1f}</div>
                </div>
            """, unsafe_allow_html=True)
            if bat_fig:
                st.plotly_chart(bat_fig, use_container_width=True, config={'displayModeBar': False})
            st.markdown("""
                <div style="background: #e3ebe6; display: inline-block; padding: 4px 8px; border-radius: 4px; font-size: 11px; color: #4a5a54; margin-top: 8px;">Target with Matchup Engine</div>
            </div>
            """, unsafe_allow_html=True)
            
        with c2:
            st.markdown(f"""
            <div style="background: #edf2ef; padding: 16px; border-radius: 8px; border: 1px solid #d9e2dd; height: 100%;">
                <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 4px;">
                    <div>
                        <div style="font-weight: 600; font-size: 14px;">{top_bowler_name}</div>
                        <div style="font-size: 12px; color: #4a5a54;">Key Bowler</div>
                    </div>
                    <div style="background: #103b2f; color: white; padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: 600;">Econ: {top_bowler_econ:.1f}</div>
                </div>
            """, unsafe_allow_html=True)
            if bowl_fig:
                st.plotly_chart(bowl_fig, use_container_width=True, config={'displayModeBar': False})
            st.markdown("""
                <div style="background: #e3ebe6; display: inline-block; padding: 4px 8px; border-radius: 4px; font-size: 11px; color: #4a5a54; margin-top: 8px;">Respect in Middle Overs</div>
            </div>
            """, unsafe_allow_html=True)
            
        st.markdown("</div></div>", unsafe_allow_html=True)

    with col_right:
        # Top Order Vulnerability
        st.markdown(f"""
            <div class="card" style="height: 100%;">
            <div class="card-header">
                <h3>Vulnerability</h3>
            </div>
            <div class="card-body" style="padding: 24px;">
                <div style="background: #edf2ef; border-radius: 8px; border: 1px solid #cad4cf; height: 200px; display: flex; flex-direction: column; justify-content: center; align-items: center; padding: 16px; text-align: center;">
                    <div style="font-size: 48px; margin-bottom: 16px;"></div>
                    <div style="font-size: 14px; font-weight: 600; color: #17231f; margin-bottom: 8px;">{vuln_msg}</div>
                    <div style="font-size: 12px; color: #4a5a54;">Data-driven insight based on ball-by-ball history.</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
    st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)

    # Suggested Bowling Plans
    st.markdown("""
    <div class="card">
        <div class="card-header">
            <h3>Janakpur Bolts Bowling Plans</h3>
        </div>
        <div class="card-body" style="padding: 0;">
    """, unsafe_allow_html=True)
    
    df = get_opposition_bowling_plans()
    
    table_html = """<table class="bolts-table">
    <thead>
        <tr>
            <th>Phase</th>
            <th>Primary Tactic</th>
            <th>Key Bowler(s)</th>
            <th>Field Setting Focus</th>
        </tr>
    </thead>
    <tbody>"""
    
    for _, row in df.iterrows():
        bowlers = str(row['Key Bowler(s)']).split(", ")
        bowler_tags = "".join([f"<span style='background: #e3ebe6; padding: 4px 8px; border-radius: 4px; font-size: 11px; margin-right: 4px;'>{b}</span>" for b in bowlers])
        
        table_html += f"""<tr>
            <td style="white-space: nowrap;">{row['Phase']}</td>
            <td>{row['Primary Tactic']}</td>
            <td><div style="display: flex; gap: 4px; flex-wrap: wrap;">{bowler_tags}</div></td>
            <td>{row['Field Setting Focus']}</td>
        </tr>"""
        
    table_html += "</tbody></table>"
    st.markdown(table_html, unsafe_allow_html=True)
    st.markdown("</div></div>", unsafe_allow_html=True)

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="card">
            <div class="card-header"><h3>Decision Summary</h3></div>
            <div class="card-body">
                <div class="insight-box"><strong>Insight:</strong> {selected_opp}'s key threat is {top_batter_name} (SR: {top_batter_sr:.1f}).</div>
                <div style="height:8px;"></div>
                <div class="insight-box"><strong>Risk:</strong> {top_bowler_name} has historically restricted scoring to {top_bowler_econ:.1f} RPO.</div>
                <div style="height:8px;"></div>
                <div class="insight-box"><strong>Recommended Action:</strong> Deploy Matchup Engine against {top_batter_name} to find favorable matchups.</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

