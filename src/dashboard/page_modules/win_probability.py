"""
Win Probability Module — CricNepal Performance Lab
Visualizes live win probability charts and identifies clutch performers using WPA.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from pathlib import Path

# Theme configuration
from src.dashboard.theme import COLORS

try:
    from src.config.paths import EXPORT_DIR, NORMALIZED_DIR
except ImportError:
    EXPORT_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "exports"
    NORMALIZED_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "normalized"

@st.cache_data(ttl=600, show_spinner=False)
def load_wpa_data():
    """Load pre-computed WPA datasets."""
    delivery_path = EXPORT_DIR / "win_probability_by_delivery.csv"
    leaderboard_path = EXPORT_DIR / "player_wpa_leaderboard.csv"
    matches_path = NORMALIZED_DIR / "matches_normalized.parquet"
    
    if not (delivery_path.exists() and leaderboard_path.exists() and matches_path.exists()):
        return None, None, None
        
    delivery_df = pd.read_csv(delivery_path)
    leaderboard_df = pd.read_csv(leaderboard_path)
    matches_df = pd.read_parquet(matches_path)
    
    return delivery_df, leaderboard_df, matches_df

def render_win_probability():
    st.markdown(
        """
        <div class="jb-page-head">
            <h2 class="page-title">Win Probability Model</h2>
            <p class="page-subtitle">Probabilistic Match Modeling & Win Probability Added (WPA) tracking.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    delivery_df, leaderboard_df, matches_df = load_wpa_data()
    
    if delivery_df is None or leaderboard_df is None or matches_df is None:
        st.warning("Win Probability data exports not found. Please run the Automated Pipeline to train the model.")
        return
        
    # Create tabs
    tab1, tab2 = st.tabs(["Match WP Tracker", "Player WPA Leaderboard"])
    
    with tab1:
        st.markdown("### Interactive Win Probability Chart")
        
        # Select Match
        match_options = {}
        for _, row in matches_df.iterrows():
            label = f"{row['season']} - vs {row['opposition_name']} (Winner: {row['winner_name']})"
            match_options[row['match_id']] = label
            
        selected_match_id = st.selectbox(
            "Select Match to View",
            options=list(match_options.keys()),
            format_func=lambda x: match_options[x]
        )
        
        match_deliveries = delivery_df[delivery_df['match_id'] == selected_match_id].copy()
        
        if match_deliveries.empty:
            st.info("No ball-by-ball win probability states computed for this match.")
        else:
            # Sort deliveries chronologically
            match_deliveries = match_deliveries.sort_values(['innings', 'over', 'ball']).reset_index(drop=True)
            match_deliveries['ball_index'] = match_deliveries.index + 1
            
            # Identify batting/bowling team names
            inn1_batting = match_deliveries[match_deliveries['innings'] == 1]['batting_team'].iloc[0]
            inn2_batting = match_deliveries[match_deliveries['innings'] == 2]['batting_team'].iloc[0]
            
            # Plotly Chart
            fig = go.Figure()
            
            # Innings 1 Curve
            inn1_data = match_deliveries[match_deliveries['innings'] == 1]
            fig.add_trace(go.Scatter(
                x=inn1_data['ball_index'],
                y=inn1_data['p_win'] * 100,
                mode='lines',
                name=f"Innings 1: {inn1_batting}",
                line=dict(color='#103b2f', width=3),
                hovertemplate="<b>Ball %{x}</b><br>WP: %{y:.1f}%<br><extra></extra>"
            ))
            
            # Innings 2 Curve
            inn2_data = match_deliveries[match_deliveries['innings'] == 2]
            fig.add_trace(go.Scatter(
                x=inn2_data['ball_index'],
                y=inn2_data['p_win'] * 100,
                mode='lines',
                name=f"Innings 2: {inn2_batting}",
                line=dict(color='#b7802f', width=3),
                hovertemplate="<b>Ball %{x}</b><br>WP: %{y:.1f}%<br><extra></extra>"
            ))
            
            # Add horizontal 50% baseline line
            fig.add_shape(
                type="line",
                x0=0,
                y0=50,
                x1=len(match_deliveries),
                y1=50,
                line=dict(color="#cad4cf", width=2, dash="dash")
            )
            
            fig.update_layout(
                title=dict(
                    text="Win Probability Curve",
                    font=dict(family="Manrope", size=18, color="#17231f")
                ),
                xaxis=dict(
                    title="Deliveries Bowled",
                    gridcolor="rgba(202, 212, 207, 0.2)"
                ),
                yaxis=dict(
                    title="Batting Team Win Probability (%)",
                    range=[0, 100],
                    gridcolor="rgba(202, 212, 207, 0.2)"
                ),
                plot_bgcolor='white',
                paper_bgcolor='white',
                margin=dict(l=40, r=40, t=50, b=40),
                font=dict(color="#17231f"),
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1
                )
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Show "Pressure Moments"
            st.markdown("###  Highest Impact Deliveries (Clutch/Pressure Moments)")
            match_deliveries['abs_wpa'] = match_deliveries['wpa'].abs()
            top_moments = match_deliveries.sort_values('abs_wpa', ascending=False).head(5)
            
            moments_cols = st.columns(2)
            
            with moments_cols[0]:
                st.markdown("#### Top 5 Momentum-Shifting Ball Deliveries")
                for _, row in top_moments.iterrows():
                    sign = "+" if row['wpa'] >= 0 else ""
                    color = "#057a55" if row['wpa'] >= 0 else "#b42318"
                    badge_style = f"background: {color}20; color: {color}; border: 1px solid {color}40;"
                    
                    st.markdown(
                        f"""
                        <div class="takeaway-item">
                            <div class="takeaway-icon"></div>
                            <div style="flex: 1;">
                                <div class="takeaway-title">
                                    Innings {row['innings']}, Over {row['over']}.{row['ball']} — {row['batter_name']} vs {row['bowler_name']}
                                </div>
                                <div class="takeaway-desc">
                                    Runs off bat: <strong>{row['runs_total']}</strong> | Wicket: <strong>{'Yes' if row['is_wicket'] else 'No'}</strong>
                                </div>
                            </div>
                            <div style="display: flex; align-items: center; justify-content: center; padding: 4px 8px; border-radius: 8px; font-weight: 700; font-size: 13px; {badge_style}">
                                {sign}{row['wpa']*100:.1f}%
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
            
            with moments_cols[1]:
                st.markdown("#### Match Analytical Takeaway")
                # Summarize match final state
                final_wp = match_deliveries['p_win'].iloc[-1]
                match_winner = matches_df[matches_df['match_id'] == selected_match_id]['winner_name'].iloc[0]
                
                st.info(
                    f"""
                    **Win Probability Model Analysis:**
                    - The match ended with **{match_winner}** securing the victory.
                    - The highest momentum swing occurred at Innings {top_moments['innings'].iloc[0]}, Over {top_moments['over'].iloc[0]}.{top_moments['ball'].iloc[0]} when **{top_moments['wpa'].iloc[0]*100:.1f}%** Win Probability Added was registered.
                    - This delivery was bowled by **{top_moments['bowler_name'].iloc[0]}** to batter **{top_moments['batter_name'].iloc[0]}**.
                    """
                )

    with tab2:
        st.markdown("### Player Win Probability Added (WPA) Leaderboard")
        st.markdown(
            """
            *Win Probability Added (WPA) measures the exact percentage change in victory chance caused by each player's deliveries.*
            *Positive values denote positive clutch performance under pressure, while negative values show players who let the match slip away.*
            """
        )
        
        # Sort and Search Leaderboard
        search_query = st.text_input("Search Player by Name", "")
        
        filtered_wpa = leaderboard_df.copy()
        if search_query:
            filtered_wpa = filtered_wpa[filtered_wpa['player_name'].str.contains(search_query, case=False)]
            
        st.markdown(
            """
            <table class="bolts-table">
                <thead>
                    <tr>
                        <th>Player Name</th>
                        <th class="right">Balls Faced/Bowled</th>
                        <th class="right">Runs / Wickets</th>
                        <th class="right">Batting WPA</th>
                        <th class="right">Bowling WPA</th>
                        <th class="right">Combined WPA</th>
                    </tr>
                </thead>
                <tbody>
            """,
            unsafe_allow_html=True
        )
        
        for _, row in filtered_wpa.iterrows():
            bat_sign = "+" if row['batting_wpa'] >= 0 else ""
            bowl_sign = "+" if row['bowling_wpa'] >= 0 else ""
            comb_sign = "+" if row['combined_wpa'] >= 0 else ""
            
            bat_class = "delta-positive" if row['batting_wpa'] >= 0 else "delta-negative"
            bowl_class = "delta-positive" if row['bowling_wpa'] >= 0 else "delta-negative"
            comb_class = "delta-positive" if row['combined_wpa'] >= 0 else "delta-negative"
            
            st.markdown(
                f"""
                <tr>
                    <td><strong>{row['player_name']}</strong></td>
                    <td class="right">{int(row['balls'])}</td>
                    <td class="right">{int(row['runs'])} runs / {int(row['wickets'])} wkts</td>
                    <td class="right {bat_class}">{bat_sign}{row['batting_wpa']:.3f}</td>
                    <td class="right {bowl_class}">{bowl_sign}{row['bowling_wpa']:.3f}</td>
                    <td class="right {comb_class}"><strong>{comb_sign}{row['combined_wpa']:.3f}</strong></td>
                </tr>
                """,
                unsafe_allow_html=True
            )
            
        st.markdown("</tbody></table>", unsafe_allow_html=True)
