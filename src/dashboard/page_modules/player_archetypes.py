"""
Player Archetypes Module — CricNepal Performance Lab
Visualizes KMeans-based player clustering and archetype identification.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path

from ..theme import COLORS

try:
    from ...config.paths import EXPORT_DIR
except ImportError:
    EXPORT_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "exports"


@st.cache_data(ttl=600, show_spinner=False)
def load_archetype_data():
    """Load pre-computed archetype data."""
    archetypes_path = EXPORT_DIR / "player_archetypes.csv"
    centroids_path = EXPORT_DIR / "archetype_centroids.csv"

    if not archetypes_path.exists():
        return None, None

    archetypes = pd.read_csv(archetypes_path)
    centroids = pd.read_csv(centroids_path) if centroids_path.exists() else None
    return archetypes, centroids


def render_player_archetypes():
    st.markdown(
        """
        <div class="jb-page-head">
            <h2 class="page-title">Player Archetypes</h2>
            <p class="page-subtitle">KMeans clustering to identify player roles and scouting profiles.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    archetypes, centroids = load_archetype_data()

    if archetypes is None:
        st.warning("Player archetype data not found. Run the pipeline to generate clusters.")
        return

    tab1, tab2 = st.tabs(["Archetype Map", "Player Explorer"])

    with tab1:
        st.markdown("### Player Role Clustering (2D Projection)")

        # Scatter: bat_sr vs bowl_economy colored by archetype
        plot_df = archetypes.copy()
        plot_df['bat_sr'] = plot_df['bat_sr'].clip(0, 250)
        plot_df['bowl_economy'] = plot_df['bowl_economy'].clip(0, 20)

        fig = px.scatter(
            plot_df,
            x="bat_sr",
            y="bowl_economy",
            color="archetype",
            hover_name="player_name",
            hover_data={
                "bat_sr": ":.1f",
                "bowl_economy": ":.2f",
                "bat_boundary_pct": ":.1f",
                "bowl_dot_pct": ":.1f",
                "archetype": True,
            },
            size=plot_df['bat_balls'].clip(10, 300),
            color_discrete_map={
                'Power Hitter':         '#b7802f',
                'Anchor Batter':        '#103b2f',
                'Wicket-Taking Bowler':  '#1a6b51',
                'Economy Bowler':       '#4a5a54',
                'Death Specialist':     '#b42318',
                'Powerplay Specialist': '#057a55',
                'All-Rounder':          '#7d8f88',
                'Balanced Batter':      '#18503f',
            },
            labels={
                "bat_sr": "Batting Strike Rate",
                "bowl_economy": "Bowling Economy",
            },
        )
        fig.update_layout(
            height=500,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(gridcolor="rgba(0,0,0,0.06)"),
            yaxis=dict(gridcolor="rgba(0,0,0,0.06)"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            font=dict(color="#17231f"),
        )
        st.plotly_chart(fig, use_container_width=True)

        # Archetype distribution summary
        st.markdown("### Archetype Distribution")
        dist = archetypes['archetype'].value_counts().reset_index()
        dist.columns = ['Archetype', 'Count']

        fig_bar = px.bar(
            dist,
            x="Archetype",
            y="Count",
            color="Archetype",
            color_discrete_map={
                'Power Hitter':         '#b7802f',
                'Anchor Batter':        '#103b2f',
                'Wicket-Taking Bowler':  '#1a6b51',
                'Economy Bowler':       '#4a5a54',
                'Death Specialist':     '#b42318',
                'Powerplay Specialist': '#057a55',
                'All-Rounder':          '#7d8f88',
                'Balanced Batter':      '#18503f',
            },
            text="Count",
        )
        fig_bar.update_layout(
            height=350,
            showlegend=False,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(gridcolor="rgba(0,0,0,0.04)"),
            yaxis=dict(gridcolor="rgba(0,0,0,0.06)"),
            font=dict(color="#17231f"),
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    with tab2:
        st.markdown("### Explore Players by Archetype")

        selected_archetype = st.selectbox(
            "Filter by Archetype",
            ["All"] + sorted(archetypes['archetype'].unique().tolist()),
        )

        if selected_archetype != "All":
            filtered = archetypes[archetypes['archetype'] == selected_archetype]
        else:
            filtered = archetypes

        search = st.text_input("Search player", "")
        if search:
            filtered = filtered[filtered['player_name'].str.contains(search, case=False)]

        display_cols = [
            'player_name', 'archetype', 'bat_balls', 'bat_runs', 'bat_sr',
            'bat_boundary_pct', 'bowl_balls', 'bowl_economy', 'bowl_wickets',
            'bowl_dot_pct',
        ]
        display_cols = [c for c in display_cols if c in filtered.columns]

        rename = {
            'player_name': 'Player',
            'archetype': 'Archetype',
            'bat_balls': 'Bat Balls',
            'bat_runs': 'Bat Runs',
            'bat_sr': 'Bat SR',
            'bat_boundary_pct': 'Boundary %',
            'bowl_balls': 'Bowl Balls',
            'bowl_economy': 'Economy',
            'bowl_wickets': 'Wickets',
            'bowl_dot_pct': 'Dot %',
        }

        st.dataframe(
            filtered[display_cols].rename(columns=rename).reset_index(drop=True),
            use_container_width=True,
            hide_index=True,
        )
