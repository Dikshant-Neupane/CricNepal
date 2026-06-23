"""
Post-Match Tactical Review — Match Intelligence
Maps to the Match Intelligence HTML mockup.
"""
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import sys
import os

# Ensure project root is on path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from src.dashboard.services.data_loaders import load_matches_normalized, load_ball_by_ball_normalized
from src.dashboard.components.match_summary import (
    render_match_summary,
    render_tactical_takeaways,
    render_phase_table,
    render_partnerships_table,
)
from src.dashboard.components.ui_patterns import (
    render_page_header,
    render_spacer,
    render_card_start,
    render_card_end,
    render_insight_card
)
from src.dashboard.theme import COLORS

_REVIEW_TEAM = "Janakpur Bolts"

def _build_manhattan_chart(match_id: str, team1: str, team2: str) -> go.Figure:
    """Build the Runs Per Over Manhattan bar chart using real data."""
    bbb = load_ball_by_ball_normalized()
    df = bbb[bbb['match_id'] == match_id].copy()
    
    if df.empty:
        return go.Figure()
        
    runs = df.groupby(['batting_team', 'over'])['runs_total'].sum().reset_index()
    wickets = df.groupby(['batting_team', 'over'])['is_wicket'].sum().reset_index()
    
    fig = go.Figure()
    
    # Team 1 (Bolts)
    t1_runs = runs[runs['batting_team'] == team1]
    t1_wkts = wickets[wickets['batting_team'] == team1]
    
    fig.add_trace(go.Bar(
        x=t1_runs["over"] + 1,
        y=t1_runs["runs_total"],
        name=team1,
        marker_color=COLORS["primary"],
        marker_cornerradius=4,
    ))
    
    w1_overs = t1_wkts[t1_wkts['is_wicket'] > 0]
    if not w1_overs.empty:
        for _, row in w1_overs.iterrows():
            ov = row['over'] + 1
            y_val = t1_runs[t1_runs['over'] == row['over']]['runs_total'].values[0] + 1.2
            fig.add_trace(go.Scatter(
                x=[ov], y=[y_val],
                mode="markers",
                marker=dict(color=COLORS["error"], size=8, symbol="circle"),
                name=f"Wicket ({team1})",
                showlegend=False,
            ))

    # Team 2
    t2_runs = runs[runs['batting_team'] == team2]
    t2_wkts = wickets[wickets['batting_team'] == team2]
    
    if not t2_runs.empty:
        fig.add_trace(go.Bar(
            x=t2_runs["over"] + 1,
            y=t2_runs["runs_total"],
            name=team2,
            marker_color=COLORS["outline_variant"],
            marker_cornerradius=4,
        ))
        
        w2_overs = t2_wkts[t2_wkts['is_wicket'] > 0]
        if not w2_overs.empty:
            for _, row in w2_overs.iterrows():
                ov = row['over'] + 1
                y_val = t2_runs[t2_runs['over'] == row['over']]['runs_total'].values[0] + 1.2
                fig.add_trace(go.Scatter(
                    x=[ov], y=[y_val],
                    mode="markers",
                    marker=dict(color=COLORS["error"], size=8, symbol="circle"),
                    name=f"Wicket ({team2})",
                    showlegend=False,
                ))

    fig.update_layout(
        barmode="group",
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(family="Inter, sans-serif", color=COLORS["on_surface"]),
        margin=dict(l=40, r=20, t=10, b=40),
        height=340,
        legend=dict(
            orientation="h",
            yanchor="top",
            y=1.12,
            xanchor="right",
            x=1,
            font=dict(size=12),
        ),
        xaxis=dict(
            title="Over",
            tickmode="linear",
            tick0=1,
            dtick=2,
            gridcolor="rgba(193,200,194,0.2)",
            linecolor=COLORS["outline_variant"],
        ),
        yaxis=dict(
            title="Runs",
            gridcolor="rgba(193,200,194,0.15)",
            linecolor=COLORS["outline_variant"],
        ),
        bargap=0.2,
        bargroupgap=0.05,
    )

    return fig


def _build_worm_chart(match_id: str, team1: str, team2: str) -> go.Figure:
    """Build the Cumulative Run Flow worm chart."""
    bbb = load_ball_by_ball_normalized()
    df = bbb[bbb['match_id'] == match_id].copy()
    
    if df.empty:
        return go.Figure()
        
    runs = df.groupby(['batting_team', 'over'])['runs_total'].sum().reset_index()
    
    fig = go.Figure()

    t1_runs = runs[runs['batting_team'] == team1].sort_values('over')
    t1_runs['cum_runs'] = t1_runs['runs_total'].cumsum()
    
    fig.add_trace(go.Scatter(
        x=t1_runs["over"] + 1,
        y=t1_runs["cum_runs"],
        name=team1,
        mode="lines",
        line=dict(color=COLORS["primary"], width=3),
    ))

    t2_runs = runs[runs['batting_team'] == team2].sort_values('over')
    if not t2_runs.empty:
        t2_runs['cum_runs'] = t2_runs['runs_total'].cumsum()
        fig.add_trace(go.Scatter(
            x=t2_runs["over"] + 1,
            y=t2_runs["cum_runs"],
            name=team2,
            mode="lines",
            line=dict(color=COLORS["outline"], width=2.5, dash="dash"),
        ))

    fig.update_layout(
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(family="Inter, sans-serif", color=COLORS["on_surface"]),
        margin=dict(l=40, r=20, t=10, b=40),
        height=340,
        legend=dict(
            orientation="h",
            yanchor="top",
            y=1.12,
            xanchor="right",
            x=1,
            font=dict(size=12),
        ),
        xaxis=dict(
            title="Over",
            tickmode="linear",
            tick0=1,
            dtick=2,
            gridcolor="rgba(193,200,194,0.15)",
            linecolor=COLORS["outline_variant"],
        ),
        yaxis=dict(
            title="Cumulative Runs",
            gridcolor="rgba(193,200,194,0.15)",
            linecolor=COLORS["outline_variant"],
        ),
    )

    return fig

def get_real_phase_execution(match_id: str, team: str) -> pd.DataFrame:
    bbb = load_ball_by_ball_normalized()
    df = bbb[(bbb['match_id'] == match_id) & (bbb['batting_team'] == team)]
    
    if df.empty:
        return pd.DataFrame({"Phase": ["Powerplay (1-6)", "Middle (7-15)", "Death (16-20)"], "Match RR": [0.0, 0.0, 0.0], "Season Avg": [8.1, 8.25, 10.5], "Delta": [0.0, 0.0, 0.0]})
        
    def rr(phase_df):
        balls = len(phase_df)
        if balls == 0: return 0.0
        return (phase_df['runs_total'].sum() / balls) * 6
        
    pp = df[df['over'] < 6]
    mid = df[(df['over'] >= 6) & (df['over'] < 15)]
    death = df[df['over'] >= 15]
    
    # Just mock season averages to avoid full aggregation over all matches here.
    return pd.DataFrame({
        "Phase": ["Powerplay (1-6)", "Middle (7-15)", "Death (16-20)"],
        "Match RR": [round(rr(pp), 2), round(rr(mid), 2), round(rr(death), 2)],
        "Season Avg": [8.10, 8.25, 10.50],
        "Delta": [round(rr(pp)-8.1, 2), round(rr(mid)-8.25, 2), round(rr(death)-10.5, 2)]
    })

def get_real_partnerships(match_id: str, team: str) -> pd.DataFrame:
    bbb = load_ball_by_ball_normalized()
    df = bbb[(bbb['match_id'] == match_id) & (bbb['batting_team'] == team)]
    
    if df.empty:
        return pd.DataFrame({"Batters": [], "Runs": [], "Balls": [], "SR": []})
        
    parts = []
    # simplify by grouping adjacent pairs
    # in real cricket, partnership tracking is complex (tracking who is out), but we can just group by batter + non_striker
    # since we just need the top 3 partnerships
    for (b1, b2), group in df.groupby(['batter_name', 'non_striker_name']):
        runs = group['runs_total'].sum()
        balls = len(group)
        names = sorted([str(b1), str(b2)])
        parts.append({"pair": f"{names[0]} & {names[1]}", "runs": runs, "balls": balls})
        
    pdf = pd.DataFrame(parts)
    if pdf.empty:
        return pd.DataFrame({"Batters": [], "Runs": [], "Balls": [], "SR": []})
        
    pdf = pdf.groupby('pair').sum().reset_index()
    pdf['sr'] = (pdf['runs'] / pdf['balls']) * 100
    pdf = pdf.sort_values('runs', ascending=False).head(4)
    
    return pd.DataFrame({
        "Batters": pdf['pair'],
        "Runs": pdf['runs'].astype(str),
        "Balls": pdf['balls'],
        "SR": pdf['sr'].round(1)
    })

def _load_real_matches() -> pd.DataFrame | None:
    df = load_matches_normalized()
    if df is None:
        return None

    team_df = df[
        (df["team_1_name"] == _REVIEW_TEAM) | (df["team_2_name"] == _REVIEW_TEAM)
    ].copy()

    if team_df.empty:
        return None

    team_df["match_date"] = pd.to_datetime(team_df["match_date"], errors="coerce")
    team_df = team_df.sort_values("match_date", ascending=False).reset_index(drop=True)

    team_df["opposition"] = team_df.apply(
        lambda r: r["team_2_name"] if r["team_1_name"] == _REVIEW_TEAM else r["team_1_name"],
        axis=1,
    )
    team_df["result"] = team_df.apply(
        lambda r: "Won" if r.get("winner_name") == _REVIEW_TEAM else "Lost",
        axis=1,
    )
    team_df["selector_label"] = team_df.apply(
        lambda r: (
            f"{r['match_date'].strftime('%d %b %Y')} vs {r['opposition']} — {r['result']}"
            if pd.notna(r["match_date"])
            else f"Unknown date vs {r['opposition']} — {r['result']}"
        ),
        axis=1,
    )
    return team_df


def render_match_review():
    real_matches = _load_real_matches()
    
    if real_matches is None or real_matches.empty:
        st.error("No matches available for Janakpur Bolts in real data.")
        return

    labels = real_matches["selector_label"].tolist()
    selected_label = st.selectbox("Select match to review", labels, key="match_selector")
    idx = labels.index(selected_label)
    row = real_matches.iloc[idx]
    
    summary = {
        "match_title": selected_label,
        "team1": {
            "name": _REVIEW_TEAM,
            "short": "JKB",
            "score": str(row.get("team_1_total_runs", "—")),
            "overs": "20.0 Overs",
            "rr": "—",
            "is_winner": row["result"] == "Won",
        },
        "team2": {
            "name": row["opposition"],
            "short": row["opposition"][:3].upper(),
            "score": str(row.get("team_2_total_runs", "—")),
            "overs": "20.0 Overs",
            "rr": "—",
            "is_winner": row["result"] == "Lost",
        },
        "potm": row.get('player_of_match', "—"),
    }
    page_subtitle = selected_label

    render_page_header(
        title="Post-Match Tactical Review",
        subtitle=page_subtitle,
        insight_label="Decision Lens",
        insight_text="Confirm repeatable win behaviors and isolate non-repeatable spikes before next match.",
        alert_icon="Key",
    )

    col_summary, col_takeaways = st.columns([2, 1], gap="medium")

    with col_summary:
        render_match_summary(summary)

    with col_takeaways:
        render_tactical_takeaways(get_tactical_takeaways())

    render_spacer(32)

    col_manhattan, col_worm = st.columns(2, gap="medium")

    with col_manhattan:
        render_card_start("Runs Per Over (Real Data)")
        fig_manhattan = _build_manhattan_chart(row['match_id'], _REVIEW_TEAM, row['opposition'])
        st.plotly_chart(fig_manhattan, width="stretch", config={"displayModeBar": False})
        render_card_end()

    with col_worm:
        render_card_start("Cumulative Run Flow (Real Data)")
        fig_worm = _build_worm_chart(row['match_id'], _REVIEW_TEAM, row['opposition'])
        st.plotly_chart(fig_worm, width="stretch", config={"displayModeBar": False})
        render_card_end()

    render_spacer(32)

    col_phase, col_partner = st.columns(2, gap="medium")

    with col_phase:
        render_phase_table(get_real_phase_execution(row['match_id'], _REVIEW_TEAM))

    with col_partner:
        render_partnerships_table(get_real_partnerships(row['match_id'], _REVIEW_TEAM))

    render_spacer(12)

    render_insight_card(
        title="Next-Match Action Pack",
        insights=[
            {
                "label": "Insight",
                "text": "Overs 11-15 acceleration was highest leverage in this win profile.",
                "type": "neutral",
            },
            {
                "label": "Risk",
                "text": "Early dot-ball pressure remains elevated against left-arm pace angles.",
                "type": "warning",
            },
        ],
    )
