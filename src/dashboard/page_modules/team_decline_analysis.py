"""
NPL Team Decline Analysis - Interactive Dashboard
Statistical analysis of team performance changes across seasons
Uses rich parquet data for detailed insights
"""
import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path
import plotly.graph_objects as go
import plotly.express as px

from src.dashboard.services.data_loaders import load_export_csv


@st.cache_data
def load_all_data():
    """Load all NPL data sources"""
    data_dir = Path("D:/Cric_Data/data")

    try:
        # Load parquet files
        matches = pd.read_parquet(data_dir / "final/parquet/matches.parquet")
        player_innings = pd.read_parquet(data_dir / "final/parquet/player_innings.parquet")
        phase_summary = pd.read_parquet(data_dir / "final/parquet/phase_summary.parquet")

        # Load roster for season comparison
        roster = pd.read_csv(data_dir / "player_rosters/npl_player_rosters_20260521.csv")

        # Load enriched player profiles
        enriched_path = data_dir / "player_profiles/enriched_players_20260521.csv"
        enriched = pd.read_csv(enriched_path) if enriched_path.exists() else pd.DataFrame()

        # Fix team name inconsistency
        for df in [matches, player_innings]:
            for col in ["team_1_name", "team_2_name", "team_name"]:
                if col in df.columns:
                    df[col] = df[col].str.replace("Kathmandu Gurkhas", "Kathmandu Gorkhas")

        return {
            "matches": matches,
            "player_innings": player_innings,
            "phase_summary": phase_summary,
            "roster": roster,
            "enriched": enriched,
        }
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None


#  Win Drivers Tab 

def _render_win_drivers_tab() -> None:
    """S1 success factors: phase-wise strengths, WPA leaders, and match context."""
    batting  = load_export_csv("s1_vs_s2_batting_by_phase.csv")
    bowling  = load_export_csv("s1_vs_s2_bowling_by_phase.csv")
    context  = load_export_csv("s1_vs_s2_match_context.csv")
    wpa      = load_export_csv("player_wpa_leaderboard.csv")

    st.markdown("## Win Drivers — Season 1 Success")
    st.caption("What made the championship season work. Use these as the S3 baseline.")

    # Match context KPIs from s1_vs_s2_match_context.csv
    if context is not None:
        s1 = context[context["season"] == "S1"]
        if not s1.empty:
            r = s1.iloc[0]
            st.markdown("### Season 1 Match Context")
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.metric("Win Rate", f"{r.get('win_rate', 0):.1f}%", "7/10 matches")
            with c2:
                st.metric("Chase Win Rate", f"{r.get('chasing_win_rate', 0):.1f}%", "Won chasing")
            with c3:
                st.metric("Bat-First Win %", f"{r.get('batting_first_win_rate', 0):.1f}%", "Set totals")
            with c4:
                st.metric("Toss Conversion", f"{r.get('toss_conversion_rate', 0):.1f}%", "Converted wins")
    else:
        st.warning("Missing: s1_vs_s2_match_context.csv")

    st.markdown("---")

    # Batting phase cards
    if batting is not None:
        s1_bat = batting[batting["season"] == "S1"]
        if not s1_bat.empty:
            st.markdown("### S1 Batting by Phase")
            cols = st.columns(3)
            phases = [("powerplay", "Powerplay (1-6)"), ("middle", "Middle (7-15)"), ("death", "Death (16-20)")]
            for col, (phase, label) in zip(cols, phases):
                row = s1_bat[s1_bat["phase"] == phase]
                if row.empty:
                    continue
                r = row.iloc[0]
                with col:
                    st.markdown(f"**{label}**")
                    st.metric("Run Rate", f"{r.get('run_rate', 0):.2f}")
                    st.metric("Strike Rate", f"{r.get('strike_rate', 0):.1f}")
                    st.metric("Dot Ball %", f"{r.get('dot_ball_pct', 0):.1f}%")
    else:
        st.warning("Missing: s1_vs_s2_batting_by_phase.csv")

    # Bowling phase cards
    if bowling is not None:
        s1_bowl = bowling[bowling["season"] == "S1"]
        if not s1_bowl.empty:
            st.markdown("### S1 Bowling by Phase")
            cols = st.columns(3)
            phases = [("powerplay", "Powerplay (1-6)"), ("middle", "Middle (7-15)"), ("death", "Death (16-20)")]
            for col, (phase, label) in zip(cols, phases):
                row = s1_bowl[s1_bowl["phase"] == phase]
                if row.empty:
                    continue
                r = row.iloc[0]
                with col:
                    st.markdown(f"**{label}**")
                    st.metric("Economy", f"{r.get('economy', 0):.2f}")
                    st.metric("Wickets", str(int(r.get('wickets_taken', 0))))
                    st.metric("Dot Ball %", f"{r.get('dot_ball_pct', 0):.1f}%")
    else:
        st.warning("Missing: s1_vs_s2_bowling_by_phase.csv")

    st.markdown("---")
        st.markdown("### Top WPA Performers (S1)")
        top5 = wpa.sort_values("combined_wpa", ascending=False).head(5).reset_index(drop=True)
        top5.index += 1
        display_wpa = top5[["player_name", "combined_wpa", "batting_wpa", "bowling_wpa"]].rename(columns={
            "player_name": "Player",
            "combined_wpa": "Combined WPA",
            "batting_wpa": "Batting WPA",
            "bowling_wpa": "Bowling WPA",
        })
        display_wpa.index.name = "Rank"
        st.dataframe(display_wpa, use_container_width=True)
    else:
        st.warning("Missing: player_wpa_leaderboard.csv — skipping WPA section.")

    #  What to Preserve 
    st.markdown("###  What to Preserve for Season 3")
    st.markdown("""
    <div style="background:linear-gradient(135deg,rgba(16,59,47,0.08),rgba(16,59,47,0.03));
                border-left:4px solid #103b2f;padding:16px 20px;border-radius:8px;">
        <ul style="margin:0;padding-left:18px;line-height:1.9;font-size:14px;">
            <li><strong>Powerplay bowling discipline</strong> — 6.33 economy, 11 wickets total (best phase S1)</li>
            <li><strong>Death bowling wicket-taking</strong> — 3.5 wickets/game, keeping economy ≤7.68</li>
            <li><strong>Middle-overs dot-ball pressure</strong> — 40.9% dot rate; creates collapse windows</li>
            <li><strong>Chase mentality</strong> — 75% chase win rate; build batting order around this strength</li>
            <li><strong>Overall wicket-taking</strong> — 7.6 wickets/game; team wins when wickets fall</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)


#  Loss Drivers Tab 

def _render_loss_drivers_tab() -> None:
    """S2 failure analysis: phase decline heatmap, leakage metrics, root causes."""
    batting = load_export_csv("s1_vs_s2_batting_by_phase.csv")
    bowling = load_export_csv("s1_vs_s2_bowling_by_phase.csv")
    context = load_export_csv("s1_vs_s2_match_context.csv")
    deltas  = load_export_csv("s1_vs_s2_bowling_deltas.csv")

    st.markdown("## Loss Drivers — Season 2 Failure Analysis")
    st.caption("Where and why the performance collapsed. Fix these for S3.")

    # Three headline regression signals
    c1, c2, c3 = st.columns(3)

    # Death bowling leakage
    death_delta = None
    if bowling is not None:
        s1_death = bowling[(bowling["season"] == "S1") & (bowling["phase"] == "death")]
        s2_death = bowling[(bowling["season"] == "S2") & (bowling["phase"] == "death")]
        if not s1_death.empty and not s2_death.empty:
            death_delta = float(s2_death.iloc[0]["economy"]) - float(s1_death.iloc[0]["economy"])

    with c1:
        delta_str = f"+{death_delta:.2f} rpo" if death_delta is not None else "N/A"
        st.metric("Death Bowling Leakage", delta_str, "S1: 7.68  →  S2: 9.32")

    # Chase failure rate
    chase_s1, chase_s2 = 75.0, 25.0
    if context is not None:
        s1_ctx = context[context["season"] == "S1"]
        s2_ctx = context[context["season"] == "S2"]
        if not s1_ctx.empty and not s2_ctx.empty:
            chase_s1 = float(s1_ctx.iloc[0].get("chasing_win_rate", 75.0))
            chase_s2 = float(s2_ctx.iloc[0].get("chasing_win_rate", 25.0))

    with c2:
        delta_chase = f"{chase_s2 - chase_s1:+.1f}pp vs S1"
        st.metric("Chase Win Rate (S2)", f"{chase_s2:.1f}%", delta_chase)

    # Powerplay collapse
    s1_matches, s2_matches = 10, 7
    pp_s1_pg, pp_s2_pg = None, None
    if batting is not None:
        s1_pp = batting[(batting["season"] == "S1") & (batting["phase"] == "powerplay")]
        s2_pp = batting[(batting["season"] == "S2") & (batting["phase"] == "powerplay")]
        if not s1_pp.empty and not s2_pp.empty:
            pp_s1_pg = float(s1_pp.iloc[0]["wickets_lost"]) / s1_matches
            pp_s2_pg = float(s2_pp.iloc[0]["wickets_lost"]) / s2_matches

    with c3:
        s1_val = f"{pp_s1_pg:.1f}" if pp_s1_pg is not None else "1.9"
        s2_val = f"{pp_s2_pg:.1f}" if pp_s2_pg is not None else "2.3"
        label = "Regression" if (pp_s2_pg and pp_s1_pg and pp_s2_pg > pp_s1_pg) else "Stable"
        st.metric("PP Wickets Lost / Game", f"S2: {s2_val}", f"S1: {s1_val} — {label}")

    st.markdown("---")

    # Phase decline heatmap
    if bowling is not None:
        s1_b = bowling[bowling["season"] == "S1"].set_index("phase")
        s2_b = bowling[bowling["season"] == "S2"].set_index("phase")
        shared = [p for p in ["powerplay", "middle", "death"] if p in s1_b.index and p in s2_b.index]
        if shared:
            delta_df = pd.DataFrame({
                "Economy Δ":    [round(s2_b.loc[p, "economy"] - s1_b.loc[p, "economy"], 2) for p in shared],
                "Wickets Δ":    [round(s2_b.loc[p, "wickets_taken"] - s1_b.loc[p, "wickets_taken"], 1) for p in shared],
                "Dot Ball % Δ": [round(s2_b.loc[p, "dot_ball_pct"] - s1_b.loc[p, "dot_ball_pct"], 1) for p in shared],
            }, index=[p.capitalize() for p in shared])

            st.markdown("### Phase Decline Heatmap (S2 minus S1)")
            st.caption("Red = got worse. Green = improved. Economy Δ > 0 means more runs conceded.")
            fig = px.imshow(
                delta_df,
                color_continuous_scale=[[0, "#1a6b51"], [0.5, "#f7f7f7"], [1, "#b42318"]],
                text_auto=".2f",
                aspect="auto",
                color_continuous_midpoint=0,
            )
            fig.update_layout(height=260, margin=dict(l=10, r=10, t=20, b=10))
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Missing: s1_vs_s2_bowling_by_phase.csv — skipping heatmap.")

    #  What Changed vs S1 table 
    if deltas is not None and not deltas.empty:
        st.markdown("### What Changed vs S1 — Bowling")
        rename = {
            "phase": "Phase",
            "economy_s1": "S1 Econ",
            "economy_s2": "S2 Econ",
            "economy_delta": "Δ Econ",
            "wickets_taken_s1": "S1 Wkts",
            "wickets_taken_s2": "S2 Wkts",
            "wickets_taken_delta": "Δ Wkts",
        }
        available = {k: v for k, v in rename.items() if k in deltas.columns}
        if available:
            st.dataframe(
                deltas[list(available.keys())].rename(columns=available),
                use_container_width=True, hide_index=True
            )
    elif bowling is not None:
        # Build inline from phase CSVs if deltas file is missing
        s1_b2 = bowling[bowling["season"] == "S1"].set_index("phase")
        s2_b2 = bowling[bowling["season"] == "S2"].set_index("phase")
        rows = []
        for phase in ["powerplay", "middle", "death"]:
            if phase in s1_b2.index and phase in s2_b2.index:
                rows.append({
                    "Phase": phase.capitalize(),
                    "S1 Econ": round(s1_b2.loc[phase, "economy"], 2),
                    "S2 Econ": round(s2_b2.loc[phase, "economy"], 2),
                    "Δ Econ":  round(s2_b2.loc[phase, "economy"] - s1_b2.loc[phase, "economy"], 2),
                    "S1 Wkts": int(s1_b2.loc[phase, "wickets_taken"]),
                    "S2 Wkts": int(s2_b2.loc[phase, "wickets_taken"]),
                    "Δ Wkts":  int(s2_b2.loc[phase, "wickets_taken"] - s1_b2.loc[phase, "wickets_taken"]),
                })
        if rows:
            st.markdown("### What Changed vs S1 — Bowling")
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    # Root Cause Summary
    st.markdown("### Root Cause Summary")
    st.info(
        "**Death bowling +1.64 rpo** — ~11 extra runs/match conceded in overs 16-20.  \n"
        "**Powerplay wickets 11 → 6** — opponents score freely without early pressure.  \n"
        "**Middle-overs dot ball % dropped 10.7pp** — 40.9% → 30.2%; opponents rotated freely.  \n"
        "**Chase win rate −50pp** — 75% (S1) → 25% (S2); batting order under pressure.  \n"
        "**Overall wickets −22%** — 7.6 → 5.9 per game; the main win mechanism broke down."
    )

def load_roster_data():
    """Load NPL roster data - kept for backward compatibility"""
    data = load_all_data()
    return data['roster'] if data else None

def get_team_phase_performance(data, team_name):
    """Analyze team's phase-wise performance"""
    matches = data['matches']
    phase_summary = data['phase_summary']
    
    # Get team's match IDs
    team_matches = matches[
        (matches['team_1_name'] == team_name) | 
        (matches['team_2_name'] == team_name)
    ]['match_id'].unique()
    
    # Filter phase data
    team_phases = phase_summary[phase_summary['match_id'].isin(team_matches)].copy()
    
    if len(team_phases) == 0:
        return None
    
    # Aggregate by phase
    phase_stats = team_phases.groupby('phase').agg({
        'runs_scored': 'mean',
        'wickets': 'mean',
        'run_rate': 'mean',
        'dot_ball_pct': 'mean',
        'boundary_pct': 'mean'
    }).round(2)
    
    return phase_stats

def get_player_form_curve(data, player_name, team_name):
    """Get match-by-match form for a player"""
    player_innings = data['player_innings']
    matches = data['matches']
    
    # Get player's innings
    player_data = player_innings[
        (player_innings['player_name'] == player_name) &
        (player_innings['team_name'] == team_name)
    ].copy()
    
    if len(player_data) == 0:
        return None
    
    # Merge with match dates
    player_data = player_data.merge(
        matches[['match_id', 'match_date', 'season']], 
        on='match_id', 
        how='left'
    )
    
    # Sort by date
    player_data = player_data.sort_values('match_date')
    
    # Calculate rolling averages
    player_data['rolling_runs'] = player_data['runs_scored'].rolling(3, min_periods=1).mean()
    player_data['rolling_wickets'] = player_data['wickets_taken'].rolling(3, min_periods=1).mean()
    
    return player_data

def get_team_match_results(data, team_name):
    """Get team's match-by-match results"""
    matches = data['matches']
    
    team_matches = matches[
        (matches['team_1_name'] == team_name) | 
        (matches['team_2_name'] == team_name)
    ].copy()
    
    # Add result column
    team_matches['result'] = team_matches.apply(
        lambda row: 'Won' if row['winner_name'] == team_name else 'Lost',
        axis=1
    )
    
    team_matches['opposition'] = team_matches.apply(
        lambda row: row['team_2_name'] if row['team_1_name'] == team_name else row['team_1_name'],
        axis=1
    )
    
    return team_matches.sort_values('match_date')

def analyze_team(df, team_name):
    """Analyze a specific team's performance"""
    s1 = df[(df['team'] == team_name) & (df['season'] == 'Season 1')].copy()
    s2 = df[(df['team'] == team_name) & (df['season'] == 'Season 2')].copy()
    
    if len(s1) == 0 or len(s2) == 0:
        return None
    
    # Calculate team stats
    WICKET_WEIGHT = 20
    
    # Season 1 stats
    s1_wickets = s1[s1['bowling_matches'] > 0]['wickets_taken'].sum()
    s1_runs = s1['runs_scored'].sum()
    s1_economy = s1[s1['bowling_matches'] > 0]['economy_rate'].mean()
    s1_sr = s1[s1['batting_matches'] > 0]['strike_rate'].mean()
    s1_elite_bowlers = len(s1[s1['wickets_taken'] >= 10])
    
    # Season 2 stats
    s2_wickets = s2[s2['bowling_matches'] > 0]['wickets_taken'].sum()
    s2_runs = s2['runs_scored'].sum()
    s2_economy = s2[s2['bowling_matches'] > 0]['economy_rate'].mean()
    s2_sr = s2[s2['batting_matches'] > 0]['strike_rate'].mean()
    s2_elite_bowlers = len(s2[s2['wickets_taken'] >= 10])
    
    # Roster changes
    s1_players = set(s1['player_name'])
    s2_players = set(s2['player_name'])
    departed = s1_players - s2_players
    retained = s1_players & s2_players
    new_players = s2_players - s1_players
    
    # Departed impact
    departed_df = s1[s1['player_name'].isin(departed)].copy()
    departed_df['impact'] = departed_df['runs_scored'] + (departed_df['wickets_taken'] * WICKET_WEIGHT)
    total_departed_impact = departed_df['impact'].sum()
    
    # New players impact
    new_df = s2[s2['player_name'].isin(new_players)].copy()
    new_df['impact'] = new_df['runs_scored'] + (new_df['wickets_taken'] * WICKET_WEIGHT)
    total_new_impact = new_df['impact'].sum()
    
    # Retained player analysis
    retained_decline = 0
    retained_improvement = 0
    for player in retained:
        s1_row = s1[s1['player_name'] == player].iloc[0]
        s2_row = s2[s2['player_name'] == player].iloc[0]
        
        impact_change = ((s2_row['runs_scored'] - s1_row['runs_scored']) + 
                        (s2_row['wickets_taken'] - s1_row['wickets_taken']) * WICKET_WEIGHT)
        
        if impact_change < 0:
            retained_decline += abs(impact_change)
        else:
            retained_improvement += impact_change
    
    net_roster_impact = total_departed_impact - total_new_impact
    total_decline = retained_decline + net_roster_impact
    
    # Attribution
    departed_attr = (net_roster_impact / total_decline * 100) if total_decline > 0 else 0
    retained_attr = (retained_decline / total_decline * 100) if total_decline > 0 else 0
    
    return {
        's1_wickets': int(s1_wickets),
        's2_wickets': int(s2_wickets),
        'wicket_change_pct': ((s2_wickets - s1_wickets) / s1_wickets * 100) if s1_wickets > 0 else 0,
        's1_runs': int(s1_runs),
        's2_runs': int(s2_runs),
        'runs_change_pct': ((s2_runs - s1_runs) / s1_runs * 100) if s1_runs > 0 else 0,
        's1_economy': s1_economy,
        's2_economy': s2_economy,
        's1_sr': s1_sr,
        's2_sr': s2_sr,
        's1_elite_bowlers': s1_elite_bowlers,
        's2_elite_bowlers': s2_elite_bowlers,
        'departed': len(departed),
        'retained': len(retained),
        'new': len(new_players),
        'departed_impact': int(total_departed_impact),
        'new_impact': int(total_new_impact),
        'net_roster_impact': int(net_roster_impact),
        'retained_decline': int(retained_decline),
        'retained_improvement': int(retained_improvement),
        'departed_attr': departed_attr,
        'retained_attr': retained_attr,
        'departed_df': departed_df.sort_values('impact', ascending=False).head(5),
        'new_df': new_df.sort_values('impact', ascending=False).head(5),
        's1': s1,
        's2': s2
    }

def render_team_decline_analysis():
    """Main render function for team decline analysis"""
    st.markdown(
        """
        <div class="jb-page-head">
            <h2 class="page-title">NPL Team Decline Analysis</h2>
            <p class="page-subtitle">Statistical analysis of team performance changes across Season 1 &amp; Season 2</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Load all data
    all_data = load_all_data()

    if all_data is None:
        st.error("Could not load data. Please check data paths.")
        return

    df = all_data['roster']

    # Team selector
    teams = sorted(df['team'].unique())

    col1, col2 = st.columns([1, 3])
    with col1:
        selected_team = st.selectbox(
            "Select Team",
            teams,
            index=teams.index('Janakpur Bolts') if 'Janakpur Bolts' in teams else 0,
            key="team_decline_team_selector",
        )

    with col2:
        st.info("**New tabs:** Win Drivers (S1) and Loss Drivers (S2) now available alongside Phase Analysis, Match Results, and Player Details.")

    # Create tabs for different views
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "Overview",
        "Phase Analysis",
        "Match Results",
        "Player Details",
        "Win Drivers (S1)",
        "Loss Drivers (S2)",
    ])

    with tab1:
        render_overview_tab(all_data, df, selected_team, teams)

    with tab2:
        render_phase_analysis_tab(all_data, selected_team)

    with tab3:
        render_match_results_tab(all_data, selected_team)

    with tab4:
        render_player_details_tab(all_data, df, selected_team)

    with tab5:
        _render_win_drivers_tab()

    with tab6:
        _render_loss_drivers_tab()

def render_overview_tab(all_data, df, selected_team, teams):
    """Render the overview tab with season comparison"""
    # Analyze selected team
    analysis = analyze_team(df, selected_team)
    
    if analysis is None:
        st.warning(f"No data available for {selected_team}")
        return
    
    # Display metrics
    st.markdown("### Season Comparison")
    
    cols = st.columns(5)
    
    with cols[0]:
        st.metric(
            "Total Wickets",
            f"{analysis['s2_wickets']}",
            delta=f"{analysis['wicket_change_pct']:.1f}%",
            help=f"S1: {analysis['s1_wickets']} → S2: {analysis['s2_wickets']}"
        )
    
    with cols[1]:
        st.metric(
            "Total Runs",
            f"{analysis['s2_runs']:,}",
            delta=f"{analysis['runs_change_pct']:.1f}%",
            help=f"S1: {analysis['s1_runs']:,} → S2: {analysis['s2_runs']:,}"
        )
    
    with cols[2]:
        bowler_change = analysis['s2_elite_bowlers'] - analysis['s1_elite_bowlers']
        st.metric(
            "Elite Bowlers (10+ wkts)",
            f"{analysis['s2_elite_bowlers']}",
            delta=f"{bowler_change:+d}",
            help=f"S1: {analysis['s1_elite_bowlers']} → S2: {analysis['s2_elite_bowlers']}"
        )
    
    with cols[3]:
        eco_change = analysis['s2_economy'] - analysis['s1_economy']
        st.metric(
            "Economy Rate",
            f"{analysis['s2_economy']:.2f}",
            delta=f"{eco_change:+.2f}",
            help=f"Lower is better. S1: {analysis['s1_economy']:.2f} → S2: {analysis['s2_economy']:.2f}"
        )
    
    with cols[4]:
        sr_change = analysis['s2_sr'] - analysis['s1_sr']
        st.metric(
            "Strike Rate",
            f"{analysis['s2_sr']:.1f}",
            delta=f"{sr_change:+.1f}",
            help=f"Higher is better. S1: {analysis['s1_sr']:.1f} → S2: {analysis['s2_sr']:.1f}"
        )
    
    st.markdown("---")
    
    # Attribution Analysis
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("###  Roster Changes")
        
        roster_data = pd.DataFrame({
            'Category': ['Departed', 'Retained', 'New'],
            'Count': [analysis['departed'], analysis['retained'], analysis['new']],
            'Color': ['#ef4444', '#3b82f6', '#10b981']
        })
        
        fig = go.Figure(data=[
            go.Bar(
                x=roster_data['Category'],
                y=roster_data['Count'],
                marker_color=roster_data['Color'],
                text=roster_data['Count'],
                textposition='auto',
            )
        ])
        fig.update_layout(
            height=300,
            margin=dict(l=20, r=20, t=20, b=20),
            plot_bgcolor='white',
            paper_bgcolor='white',
            xaxis_title="",
            yaxis_title="Players",
            showlegend=False,
            font=dict(color="#17231f"),
        )
        st.plotly_chart(fig, width='stretch')
        
        st.markdown(f"""
        <div style="background:#fff;border:1px solid #cad4cf;border-radius:10px;padding:14px 16px;margin-top:8px;">
            <strong style="color:#17231f;">Roster Impact:</strong><br/>
            <span style="color:#17231f;">• Departed Impact: <strong>{analysis['departed_impact']:,}</strong><br/>
            • New Players Impact: <strong>{analysis['new_impact']:,}</strong><br/>
            • Net Roster Change: <strong>{analysis['net_roster_impact']:+,}</strong></span>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("### Performance Attribution")
        
        attr_data = pd.DataFrame({
            'Factor': ['Retained Player\nDecline', 'Net Roster\nChange'],
            'Attribution': [analysis['retained_attr'], analysis['departed_attr']],
            'Color': ['#ef4444', '#f59e0b']
        })
        
        fig = go.Figure(data=[
            go.Pie(
                labels=attr_data['Factor'],
                values=attr_data['Attribution'],
                marker=dict(colors=attr_data['Color']),
                textinfo='label+percent',
                textfont_size=14,
                hole=0.4
            )
        ])
        fig.update_layout(
            height=300,
            margin=dict(l=20, r=20, t=20, b=20),
            showlegend=False,
            paper_bgcolor='white',
            plot_bgcolor='white',
            font=dict(color="#17231f"),
            annotations=[dict(text='Decline<br>Attribution', x=0.5, y=0.5, font_size=14, showarrow=False, font=dict(color="#17231f"))],
        )
        st.plotly_chart(fig, width='stretch')
        
        st.markdown(f"""
        <div style="background:#fff;border:1px solid #cad4cf;border-radius:10px;padding:14px 16px;margin-top:8px;">
            <strong style="color:#17231f;">Key Finding:</strong><br/>
            <span style="color:#17231f;">Retained players account for
            <strong>{analysis['retained_attr']:.1f}%</strong> of performance change,
            while roster turnover accounts for
            <strong>{analysis['departed_attr']:.1f}%</strong>.</span>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Detailed player tables
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("###  Top Departed Players")
        if len(analysis['departed_df']) > 0:
            departed_display = analysis['departed_df'][['player_name', 'runs_scored', 'wickets_taken', 'impact']].copy()
            departed_display.columns = ['Player', 'Runs', 'Wickets', 'Impact']
            st.dataframe(departed_display, width='stretch', hide_index=True)
        else:
            st.info("No departed players")
    
    with col2:
        st.markdown("###  Top New Players")
        if len(analysis['new_df']) > 0:
            new_display = analysis['new_df'][['player_name', 'runs_scored', 'wickets_taken', 'impact']].copy()
            new_display.columns = ['Player', 'Runs', 'Wickets', 'Impact']
            st.dataframe(new_display, width='stretch', hide_index=True)
        else:
            st.info("No new players")
    
    # League comparison
    st.markdown("---")
    st.markdown("###  League-Wide Comparison")
    
    league_data = []
    for team in teams:
        team_s1 = df[(df['team'] == team) & (df['season'] == 'Season 1')]
        team_s2 = df[(df['team'] == team) & (df['season'] == 'Season 2')]
        
        if len(team_s1) == 0 or len(team_s2) == 0:
            continue
        
        s1_wkts = team_s1[team_s1['bowling_matches'] > 0]['wickets_taken'].sum()
        s2_wkts = team_s2[team_s2['bowling_matches'] > 0]['wickets_taken'].sum()
        
        league_data.append({
            'Team': team,
            'S1 Wickets': int(s1_wkts),
            'S2 Wickets': int(s2_wkts),
            'Change %': ((s2_wkts - s1_wkts) / s1_wkts * 100) if s1_wkts > 0 else 0,
            'is_selected': team == selected_team
        })
    
    league_df = pd.DataFrame(league_data).sort_values('Change %', ascending=False)
    
    fig = go.Figure()
    
    # Add bars with different colors for selected team
    for _, row in league_df.iterrows():
        color = '#2563eb' if row['is_selected'] else '#94a3b8'
        fig.add_trace(go.Bar(
            x=[row['Team']],
            y=[row['Change %']],
            marker_color=color,
            text=f"{row['Change %']:.1f}%",
            textposition='outside',
            name=row['Team'],
            showlegend=False
        ))
    
    fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
    
    fig.update_layout(
        height=400,
        xaxis_title="",
        yaxis_title="Bowling Change (%)",
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(l=20, r=20, t=40, b=120),
        xaxis=dict(tickangle=-45, tickfont=dict(color="#17231f"), title_font=dict(color="#17231f")),
        yaxis=dict(tickfont=dict(color="#17231f"), title_font=dict(color="#17231f"), gridcolor="rgba(0,0,0,0.06)"),
        font=dict(color="#17231f"),
    )
    
    st.plotly_chart(fig, width='stretch')
    
    # Summary insights
    st.markdown("---")
    st.markdown("### Statistical Summary")
    
    reset_df = league_df.reset_index(drop=True)
    rank = reset_df.loc[reset_df['Team'] == selected_team].index[0] + 1
    league_avg = league_df['Change %'].mean()
    
    st.subheader(f"{selected_team} Performance Summary")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("League Rank", f"{rank} of {len(league_df)}")
    with col2:
        st.metric("Team Change", f"{analysis['wicket_change_pct']:.1f}%")
    with col3:
        st.metric("League Average", f"{league_avg:.1f}%")
    with col4:
        gap_value = abs(analysis['wicket_change_pct'] - league_avg)
        gap_label = 'worse' if analysis['wicket_change_pct'] < league_avg else 'better'
        st.metric("Gap", f"{gap_value:.1f}pp {gap_label}")
    
    st.caption(f"**Sample Size:** {analysis['retained']} retained players (n < 30 = exploratory findings)")
    
    st.info(" **Statistical Note:** This analysis uses correlation, not causation. Multiple factors (opponent strength, pitch conditions, coaching changes) may contribute to performance changes.")

def render_phase_analysis_tab(all_data, team_name):
    """Render phase-level performance analysis"""
    st.markdown("### Phase Performance (Powerplay / Middle / Death)")
    
    phase_stats = get_team_phase_performance(all_data, team_name)
    
    if phase_stats is None or len(phase_stats) == 0:
        st.warning(f"No phase data available for {team_name}")
        return
    
    # Display phase metrics
    cols = st.columns(3)
    phases = ['Powerplay', 'Middle', 'Death']
    
    for i, (col, phase) in enumerate(zip(cols, phases)):
        if phase in phase_stats.index:
            stats = phase_stats.loc[phase]
            with col:
                st.markdown(f"#### {phase}")
                st.metric("Run Rate", f"{stats['run_rate']:.2f}")
                st.metric("Dot Ball %", f"{stats['dot_ball_pct']:.1f}%")
                st.metric("Boundary %", f"{stats['boundary_pct']:.1f}%")
                st.metric("Avg Wickets", f"{stats['wickets']:.2f}")
    
    st.markdown("---")
    
    # Create comparison chart
    st.markdown("### Phase Comparison Chart")
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        name='Run Rate',
        x=phase_stats.index,
        y=phase_stats['run_rate'],
        marker_color='#2563eb'
    ))
    
    fig.add_trace(go.Bar(
        name='Dot Ball %',
        x=phase_stats.index,
        y=phase_stats['dot_ball_pct'],
        marker_color='#ef4444'
    ))
    
    fig.add_trace(go.Bar(
        name='Boundary %',
        x=phase_stats.index,
        y=phase_stats['boundary_pct'],
        marker_color='#10b981'
    ))
    
    fig.update_layout(
        barmode='group',
        height=400,
        xaxis_title="Phase",
        yaxis_title="Value",
        plot_bgcolor='white',
        paper_bgcolor='white',
        margin=dict(l=20, r=20, t=40, b=20),
        font=dict(color="#17231f"),
    )
    
    st.plotly_chart(fig, width='stretch')
    
    st.info("**Insight:** Compare phases to identify strengths and weaknesses. Low dot ball % with high boundary % indicates aggressive batting.")

def render_match_results_tab(all_data, team_name):
    """Render match-by-match results"""
    st.markdown("### Match Results Timeline")
    
    match_results = get_team_match_results(all_data, team_name)
    
    if match_results is None or len(match_results) == 0:
        st.warning(f"No match data available for {team_name}")
        return
    
    # Season filter
    season_filter = st.selectbox("Filter by Season", ['All', 'S1', 'S2'])
    
    if season_filter != 'All':
        match_results = match_results[match_results['season'] == season_filter]
    
    # Display summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    total_matches = len(match_results)
    wins = len(match_results[match_results['result'] == 'Won'])
    losses = total_matches - wins
    win_pct = (wins / total_matches * 100) if total_matches > 0 else 0
    
    with col1:
        st.metric("Total Matches", total_matches)
    with col2:
        st.metric("Wins", wins, delta=f"{win_pct:.1f}%")
    with col3:
        st.metric("Losses", losses)
    with col4:
        batting_first = len(match_results[match_results['toss_winner_name'] == team_name])
        st.metric("Toss Won", batting_first)
    
    # Playoff path for S2 finalists
    if season_filter in ['All', 'S2']:
        playoff_teams = {
            'Lumbini Lions': {
                'path': ['Eliminator vs Kathmandu Gorkhas (Won)', 
                        'Qualifier 2 vs Biratnagar Kings (Won)',
                        'Final vs Sudurpaschim Royals (Won by 6 wickets)'],
                'result': 'Champion',
                'color': '#fbbf24'
            },
            'Sudurpaschim Royals': {
                'path': ['Qualifier 1 vs Biratnagar Kings (Won)',
                        'Final vs Lumbini Lions (Lost by 6 wickets)'],
                'result': 'Runner-Up',
                'color': '#9ca3af'
            },
            'Biratnagar Kings': {
                'path': ['Qualifier 1 vs Sudurpaschim Royals (Lost)',
                        'Qualifier 2 vs Lumbini Lions (Lost)'],
                'result': 'Playoff Finish',
                'color': '#cd7f32'
            },
            'Kathmandu Gorkhas': {
                'path': ['Eliminator vs Lumbini Lions (Lost)'],
                'result': 'Playoff Finish',
                'color': '#6b7280'
            }
        }
        
        if team_name in playoff_teams:
            st.markdown("---")
            st.markdown("###  NPL Season 2 Playoff Path")
            playoff_info = playoff_teams[team_name]
            
            # Use native Streamlit components instead of HTML
            st.success(playoff_info['result'])
            for match in playoff_info['path']:
                st.markdown(f"- {match}")
    
    st.markdown("---")
    
    # Match results table
    st.markdown("###  Match History")
    
    display_df = match_results[[
        'match_date', 'season', 'opposition', 'result', 'winner_name', 
        'win_margin', 'win_by', 'venue_name'
    ]].copy()
    
    display_df.columns = ['Date', 'Season', 'Vs', 'Result', 'Winner', 'Margin', 'Type', 'Venue']
    
    # Color code results
    def highlight_result(row):
        if row['Result'] == 'Won':
            return ['background-color: rgba(16, 185, 129, 0.1)'] * len(row)
        else:
            return ['background-color: rgba(239, 68, 68, 0.1)'] * len(row)
    
    st.dataframe(
        display_df.style.apply(highlight_result, axis=1),
        width='stretch',
        hide_index=True,
        height=400
    )
    
    # Win/Loss timeline
    st.markdown("---")
    st.markdown("### Form Timeline")
    
    match_results['match_num'] = range(1, len(match_results) + 1)
    match_results['result_num'] = match_results['result'].map({'Won': 1, 'Lost': 0})
    match_results['rolling_form'] = match_results['result_num'].rolling(5, min_periods=1).mean() * 100
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=match_results['match_num'],
        y=match_results['rolling_form'],
        mode='lines+markers',
        name='Form (5-match rolling win %)',
        line=dict(color='#2563eb', width=3),
        marker=dict(size=8)
    ))
    
    fig.add_hline(y=50, line_dash="dash", line_color="gray", opacity=0.5, annotation_text="50%")
    
    fig.update_layout(
        height=350,
        xaxis_title="Match Number",
        yaxis_title="Win % (5-match rolling)",
        plot_bgcolor='white',
        paper_bgcolor='white',
        margin=dict(l=20, r=20, t=20, b=20),
        font=dict(color="#17231f"),
        yaxis=dict(range=[0, 100]),
    )
    
    st.plotly_chart(fig, width='stretch')

def render_player_details_tab(all_data, df, team_name):
    """Render detailed player analysis"""
    st.markdown("### Player Performance Details")
    
    # Get enriched player data
    enriched = all_data['enriched']
    roster = df[df['team'] == team_name].copy()
    
    # Merge with enriched data
    roster_enriched = roster.merge(
        enriched[['player_name', 'primary_role', 'batting_hand', 'bowling_type', 'age']], 
        on='player_name', 
        how='left'
    )
    
    # Filter by season
    season_filter = st.selectbox("Season", ['Season 1', 'Season 2'], key='player_season')
    
    season_data = roster_enriched[roster_enriched['season'] == season_filter].copy()
    
    if len(season_data) == 0:
        st.warning(f"No player data for {season_filter}")
        return
    
    # Top performers
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Top Batters")
        top_batters = season_data[season_data['batting_matches'] > 0].nlargest(5, 'runs_scored')
        if len(top_batters) > 0:
            batter_df = top_batters[['player_name', 'runs_scored', 'strike_rate', 'batting_hand', 'age']].copy()
            batter_df.columns = ['Player', 'Runs', 'SR', 'Hand', 'Age']
            st.dataframe(batter_df, width='stretch', hide_index=True)
        else:
            st.info("No batting data")
    
    with col2:
        st.markdown("#### Top Bowlers")
        top_bowlers = season_data[season_data['bowling_matches'] > 0].nlargest(5, 'wickets_taken')
        if len(top_bowlers) > 0:
            bowler_df = top_bowlers[['player_name', 'wickets_taken', 'economy_rate', 'bowling_type', 'age']].copy()
            bowler_df.columns = ['Player', 'Wickets', 'Economy', 'Type', 'Age']
            st.dataframe(bowler_df, width='stretch', hide_index=True)
        else:
            st.info("No bowling data")
    
    st.markdown("---")
    
    # Role distribution
    st.markdown("### Squad Composition")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if 'primary_role' in season_data.columns:
            role_counts = season_data['primary_role'].value_counts()
            
            fig = go.Figure(data=[go.Pie(
                labels=role_counts.index,
                values=role_counts.values,
                hole=0.4,
                marker=dict(colors=['#2563eb', '#10b981', '#f59e0b', '#ef4444'])
            )])
            
            fig.update_layout(
                height=300,
                margin=dict(l=20, r=20, t=20, b=20),
                showlegend=True,
                paper_bgcolor='white',
                font=dict(color="#17231f"),
                annotations=[dict(text='Roles', x=0.5, y=0.5, font_size=14, showarrow=False, font=dict(color="#17231f"))],
            )
            
            st.plotly_chart(fig, width='stretch')
        else:
            st.info("Role data not available")
    
    with col2:
        if 'age' in season_data.columns:
            age_data = season_data.dropna(subset=['age'])
            
            fig = go.Figure(data=[go.Histogram(
                x=age_data['age'],
                nbinsx=10,
                marker_color='#2563eb'
            )])
            
            fig.update_layout(
                height=300,
                xaxis_title="Age",
                yaxis_title="Players",
                plot_bgcolor='white',
                paper_bgcolor='white',
                margin=dict(l=20, r=20, t=20, b=20),
                font=dict(color="#17231f"),
            )
            
            st.plotly_chart(fig, width='stretch')
        else:
            st.info("Age data not available")
    
    # Player selector for detailed view
    st.markdown("---")
    st.markdown("###  Individual Player Analysis")
    
    player_names = sorted(season_data['player_name'].unique())
    selected_player = st.selectbox("Select Player", player_names)
    
    if selected_player:
        player_form = get_player_form_curve(all_data, selected_player, team_name)
        
        if player_form is not None and len(player_form) > 0:
            col1, col2 = st.columns(2)
            
            with col1:
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=list(range(1, len(player_form) + 1)),
                    y=player_form['runs_scored'],
                    mode='lines+markers',
                    name='Runs per innings',
                    line=dict(color='#2563eb')
                ))
                fig.add_trace(go.Scatter(
                    x=list(range(1, len(player_form) + 1)),
                    y=player_form['rolling_runs'],
                    mode='lines',
                    name='3-innings average',
                    line=dict(color='#10b981', dash='dash')
                ))
                fig.update_layout(
                    title=f"{selected_player} - Batting Form",
                    height=300,
                    xaxis_title="Innings",
                    yaxis_title="Runs",
                    plot_bgcolor='white',
                    paper_bgcolor='white',
                    margin=dict(l=20, r=20, t=40, b=20),
                    font=dict(color="#17231f"),
                )
                st.plotly_chart(fig, width='stretch')
            
            with col2:
                if player_form['wickets_taken'].sum() > 0:
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=list(range(1, len(player_form) + 1)),
                        y=player_form['wickets_taken'],
                        mode='lines+markers',
                        name='Wickets per innings',
                        line=dict(color='#ef4444')
                    ))
                    fig.add_trace(go.Scatter(
                        x=list(range(1, len(player_form) + 1)),
                        y=player_form['rolling_wickets'],
                        mode='lines',
                        name='3-innings average',
                        line=dict(color='#f59e0b', dash='dash')
                    ))
                    fig.update_layout(
                        title=f"{selected_player} - Bowling Form",
                        height=300,
                        xaxis_title="Innings",
                        yaxis_title="Wickets",
                        plot_bgcolor='white',
                        paper_bgcolor='white',
                        margin=dict(l=20, r=20, t=40, b=20),
                        font=dict(color="#17231f"),
                    )
                    st.plotly_chart(fig, width='stretch')
                else:
                    st.info("No bowling data for this player")
        else:
            st.info("No match-by-match data available for this player")
    
    # Season 3 Action Plan
    st.markdown("---")
    st.markdown("##  Season 3 Action Plan")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("""
        <div style="background:#fff;border:1px solid #cad4cf;border-radius:10px;overflow:hidden;">
            <div style="padding:12px 16px;border-bottom:1px solid #cad4cf;background:#f8fbf9;">
                <span style="font-weight:700;color:#17231f;"> Key Insight</span>
            </div>
            <div style="padding:14px 16px;">
                <div style="background:rgba(5,122,85,0.07);border-left:3px solid #057a55;border-radius:6px;padding:10px;font-size:13px;color:#17231f;line-height:1.5;">
                    <strong>Data Finding:</strong> 70–90% of S2 decline is retained-player underperformance, not roster turnover. Role execution, not personnel, is the primary driver.
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div style="background:#fff;border:1px solid #cad4cf;border-radius:10px;overflow:hidden;">
            <div style="padding:12px 16px;border-bottom:1px solid #cad4cf;background:#f8fbf9;">
                <span style="font-weight:700;color:#17231f;"> Risk Factor</span>
            </div>
            <div style="padding:14px 16px;">
                <div style="background:rgba(245,158,11,0.07);border-left:3px solid #f59e0b;border-radius:6px;padding:10px;font-size:13px;color:#17231f;line-height:1.5;">
                    <strong>Execution Risk:</strong> Death bowling (+1.64 rpo) and powerplay batting (-0.75 rpo) are the highest-leverage failure points. Combined impact: ~12–15 runs per match.
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown("""
        <div style="background:#fff;border:1px solid #cad4cf;border-radius:10px;overflow:hidden;">
            <div style="padding:12px 16px;border-bottom:1px solid #cad4cf;background:#f8fbf9;">
                <span style="font-weight:700;color:#17231f;"> Recommended Action</span>
            </div>
            <div style="padding:14px 16px;">
                <div style="background:#edf2ef;border-left:3px solid #7d8f88;border-radius:6px;padding:10px;font-size:13px;color:#17231f;line-height:1.6;">
                    <strong>Priority 1:</strong> Fix death bowling discipline (target −1.0 rpo).<br>
                    <strong>Priority 2:</strong> Increase powerplay intent (+0.75 rpo, −3pp dot%).<br>
                    <strong>Priority 3:</strong> Maintain middle-overs rotation strength.
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

