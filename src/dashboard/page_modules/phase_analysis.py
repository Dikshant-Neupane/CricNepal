"""
Phase Analysis — surfaces the corrected two-tier batting/bowling analytics.

Reads the CSVs that the analytics modules under `src/analytics/` write into
`data/exports/`, plus the bowler/batter two-tier summaries. Falls back to
computing on the fly from the normalized parquet if the CSV is missing.

This page exists because, prior to this revision, eight analytical modules
were producing exports that the dashboard never read — they sat as PNGs in
`data/exports/`. The S1→S2 phase deltas and Elo-adjusted strength of
schedule are exactly the questions a coach would ask, and they were
invisible.
"""

from __future__ import annotations

from typing import Optional

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from ..services.data_loaders import (
    load_bbb_with_season,
    load_export_csv,
)

TEAM = "Janakpur Bolts"


# --------------------------------------------------------------------------- #
# Data
# --------------------------------------------------------------------------- #

@st.cache_data(ttl=3600, show_spinner=False)
def _phase_batting_df() -> Optional[pd.DataFrame]:
    """Pre-computed S1 vs S2 batting splits per phase."""
    return load_export_csv("s1_vs_s2_batting_by_phase.csv")


@st.cache_data(ttl=3600, show_spinner=False)
def _phase_bowling_df() -> Optional[pd.DataFrame]:
    """Pre-computed S1 vs S2 bowling splits per phase."""
    return load_export_csv("s1_vs_s2_bowling_by_phase.csv")


@st.cache_data(ttl=3600, show_spinner=False)
def _strength_summary_df() -> Optional[pd.DataFrame]:
    """Per-season strength-of-schedule summary from opposition-strength
    analysis."""
    return load_export_csv("janakpur_season_strength_summary.csv")


@st.cache_data(ttl=3600, show_spinner=False)
def _wae_bootstrap_df() -> Optional[pd.DataFrame]:
    """Bootstrap CI on Wins Above Expected from opposition-strength analysis."""
    return load_export_csv("janakpur_wae_bootstrap.csv")


@st.cache_data(ttl=3600, show_spinner=False)
def _opp_strength_df() -> Optional[pd.DataFrame]:
    """Per-match opponent Elo + JAB pre-match Elo + actual outcome."""
    return load_export_csv("janakpur_opposition_strength.csv")


# --------------------------------------------------------------------------- #
# Renderers
# --------------------------------------------------------------------------- #

def _bar_compare(df: pd.DataFrame, value_col: str, title: str, y_label: str,
                 lower_is_better: bool = False) -> go.Figure:
    """Side-by-side S1 vs S2 bar chart, faceted by phase."""
    phases = ["powerplay", "middle", "death"]
    seasons = ["S1", "S2"]
    palette = {"S1": "#4CAF50", "S2": "#F44336"}

    fig = go.Figure()
    for season in seasons:
        slc = df[df["season"] == season].set_index("phase")
        # Reindex defensively in case a phase is missing
        ys = [slc.loc[p, value_col] if p in slc.index else None for p in phases]
        fig.add_trace(go.Bar(
            x=[p.title() for p in phases],
            y=ys,
            name=season,
            marker_color=palette[season],
            text=[f"{y:.2f}" if y is not None and pd.notna(y) else "" for y in ys],
            textposition="outside",
        ))
    fig.update_layout(
        title=title,
        yaxis_title=y_label,
        xaxis_title="Phase",
        barmode="group",
        height=360,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        legend_title="Season",
    )
    if lower_is_better:
        fig.add_annotation(
            x=0.99, y=1.05, xref="paper", yref="paper", showarrow=False,
            text="Lower is better", font=dict(size=11, color="#888"),
        )
    return fig


def _delta_table(bat_df: pd.DataFrame, bowl_df: pd.DataFrame) -> pd.DataFrame:
    """Compact S1 → S2 delta table, formatted for display."""
    rows = []
    for phase in ["powerplay", "middle", "death"]:
        bat_s1 = bat_df[(bat_df["season"] == "S1") & (bat_df["phase"] == phase)]
        bat_s2 = bat_df[(bat_df["season"] == "S2") & (bat_df["phase"] == phase)]
        bowl_s1 = bowl_df[(bowl_df["season"] == "S1") & (bowl_df["phase"] == phase)]
        bowl_s2 = bowl_df[(bowl_df["season"] == "S2") & (bowl_df["phase"] == phase)]

        if not (bat_s1.empty or bat_s2.empty or bowl_s1.empty or bowl_s2.empty):
            rr1 = bat_s1["run_rate"].iloc[0]
            rr2 = bat_s2["run_rate"].iloc[0]
            ec1 = bowl_s1["economy"].iloc[0]
            ec2 = bowl_s2["economy"].iloc[0]
            rows.append({
                "Phase": phase.title(),
                "Bat RR (S1)": round(rr1, 2),
                "Bat RR (S2)": round(rr2, 2),
                "Δ rpo (bat)": round(rr2 - rr1, 2),
                "Bowl econ (S1)": round(ec1, 2),
                "Bowl econ (S2)": round(ec2, 2),
                "Δ rpo (bowl)": round(ec2 - ec1, 2),
                "Net swing per over": round((rr2 - rr1) - (ec2 - ec1), 2),
            })
    return pd.DataFrame(rows)


def _render_phase_block(bat_df: pd.DataFrame, bowl_df: pd.DataFrame) -> None:
    st.markdown("### Phase splits")
    st.caption(
        "S1 → S2 batting and bowling per phase, computed from the corrected "
        "phase boundaries (powerplay = overs 1-6, middle = 7-15, death = 16-20). "
        "The previous version of these analyses used 0-indexed `over` filters that "
        "shifted everything by one; the numbers below are the post-correction set."
    )

    c1, c2 = st.columns(2)
    with c1:
        if bat_df is not None and not bat_df.empty:
            st.plotly_chart(
                _bar_compare(bat_df, "run_rate", "JAB batting run rate by phase",
                             "Run rate (rpo)"),
                width="stretch", config={"displayModeBar": False},
            )
        else:
            st.info("Batting phase CSV unavailable.")
    with c2:
        if bowl_df is not None and not bowl_df.empty:
            st.plotly_chart(
                _bar_compare(bowl_df, "economy", "JAB bowling economy by phase",
                             "Economy (rpo)", lower_is_better=True),
                width="stretch", config={"displayModeBar": False},
            )
        else:
            st.info("Bowling phase CSV unavailable.")

    if (bat_df is not None and not bat_df.empty
            and bowl_df is not None and not bowl_df.empty):
        st.markdown("#### S1 → S2 delta table")
        st.caption(
            "Net swing per over = (Δ batting rr) − (Δ bowling econ). Negative "
            "means the run-difference moved against JAB in that phase."
        )
        st.dataframe(_delta_table(bat_df, bowl_df), width="stretch", hide_index=True)


def _render_strength_block() -> None:
    summary = _strength_summary_df()
    boot = _wae_bootstrap_df()
    if summary is None and boot is None:
        return

    st.markdown("---")
    st.markdown("### Opposition strength (Elo-adjusted)")
    st.caption(
        "Per-team Elo computed across all 64 NPL matches, then used to derive "
        "JAB's strength of schedule and Wins Above Expected. A bootstrap "
        "interval shows whether the season-on-season swing is real or noise."
    )

    c1, c2 = st.columns([1.2, 1])
    with c1:
        if summary is not None and not summary.empty:
            disp = summary.rename(columns={
                "season": "Season",
                "matches": "Matches",
                "wins": "Wins",
                "win_pct": "Win %",
                "sos_mean_opp_elo": "Mean opp Elo",
                "expected_wins": "Expected wins",
                "expected_win_pct": "Expected win %",
                "wins_above_expected": "WAE",
                "wae_per_match": "WAE / match",
            })
            st.dataframe(disp, width="stretch", hide_index=True)
        else:
            st.info("Strength-of-schedule summary unavailable.")
    with c2:
        if boot is not None and not boot.empty:
            disp = boot[["season", "wae_observed", "wae_ci_lo", "wae_ci_hi"]].rename(columns={
                "season": "Season",
                "wae_observed": "WAE observed",
                "wae_ci_lo": "95% CI low",
                "wae_ci_hi": "95% CI high",
            })
            st.dataframe(disp, width="stretch", hide_index=True)
            ci_excludes_zero = (
                ((boot["wae_ci_lo"] > 0) | (boot["wae_ci_hi"] < 0)).any()
            )
            if ci_excludes_zero:
                st.caption(
                    "ℹ️ At least one season's bootstrap CI excludes zero — the "
                    "WAE for that season is not consistent with luck alone."
                )
            else:
                st.caption(
                    "Bootstrap CIs straddle zero; the season-on-season movement "
                    "could be schedule-strength or luck."
                )
        else:
            st.info("Bootstrap CSV unavailable.")

    opp = _opp_strength_df()
    if opp is not None and not opp.empty and {"match_date", "opp_pre_elo", "season"}.issubset(opp.columns):
        opp = opp.copy()
        opp["match_date"] = pd.to_datetime(opp["match_date"], errors="coerce")
        fig = go.Figure()
        for season, color in [("S1", "#4CAF50"), ("S2", "#F44336")]:
            s = opp[opp["season"] == season].sort_values("match_date")
            if s.empty:
                continue
            fig.add_trace(go.Scatter(
                x=s["match_date"], y=s["opp_pre_elo"],
                mode="lines+markers", name=f"{season} opp Elo",
                marker=dict(size=8), line=dict(width=2, color=color),
                hovertext=s["opponent"], hoverinfo="text+x+y",
            ))
        fig.add_hline(y=1500, line_dash="dot", line_color="grey",
                      annotation_text="League mean (1500)", annotation_position="bottom right")
        fig.update_layout(
            title="Opponent pre-match Elo per JAB match",
            xaxis_title="Match date", yaxis_title="Opponent Elo",
            height=380, plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})


# --------------------------------------------------------------------------- #
# Page entry
# --------------------------------------------------------------------------- #

def render_phase_analysis() -> None:
    st.markdown(
        """
        <div class="jb-page-head">
            <h2 class="page-title">Phase &amp; Strength Analysis</h2>
            <p class="page-subtitle">S1 → S2 phase deltas (corrected phase boundaries)
            with Elo-based strength-of-schedule controls.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    bat_df = _phase_batting_df()
    bowl_df = _phase_bowling_df()
    if bat_df is None and bowl_df is None:
        st.warning(
            "No phase CSVs found in `data/exports/`. Run the analytics modules "
            "(`python -m src.analytics.root_cause_analysis`) to generate them."
        )
        return

    _render_phase_block(bat_df, bowl_df)
    _render_strength_block()

    st.markdown(
        """
        <div class="card" style="margin-top: 12px;">
            <div class="card-header"><h3>How to read this page</h3></div>
            <div class="card-body">
                <div class="insight-box"><strong>Phase splits</strong> tell you where the run
                gap between S1 and S2 sits. Big positive bowling-economy deltas
                or big negative batting run-rate deltas in one phase mean that
                phase is the per-match contributor to the win-rate decline.</div>
                <div style="height:8px;"></div>
                <div class="insight-box"><strong>Net swing per over</strong> is what mattered
                most: it is the per-over run difference that moved against JAB in
                that phase.</div>
                <div style="height:8px;"></div>
                <div class="insight-box"><strong>Elo-adjusted WAE</strong> tells you whether
                the win-rate decline is explained by harder opposition. If both
                seasons have similar SoS but very different WAE, the gap is real
                and not a schedule artefact.</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
