"""Executive overview module with stronger hierarchy and clearer strategic narrative."""

import os
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

from src.dashboard.services.data_source import load_match_records
from src.dashboard.services.data_loaders import (
    load_ball_by_ball_normalized,
    load_team_matches_for,
    export_path,
)
from src.dashboard.services.metrics import build_executive_cards
from src.dashboard.services.data_quality import validate_match_records

TEAM = "Janakpur Bolts"


def _load_real_matches() -> pd.DataFrame | None:
    """Load Janakpur Bolts match data via the cached normalized parquet loader."""
    try:
        return load_team_matches_for(TEAM)
    except Exception:
        return None


def _nrr_from_bbb(match_ids: list, season: str) -> float:
    """Calculate NRR from ball-by-ball data (cached underneath)."""
    bbb = load_ball_by_ball_normalized()
    if bbb is None:
        return float("nan")
    bbb = bbb[bbb["match_id"].isin(match_ids)].copy()
    if bbb.empty:
        return float("nan")

    # Runs for (Janakpur batting)
    batting = bbb[bbb["batting_team"] == TEAM]
    # Runs against (Janakpur bowling)
    bowling = bbb[bbb["bowling_team"] == TEAM]

    runs_for_total = pd.to_numeric(batting["runs_total"], errors="coerce").sum()
    runs_against_total = pd.to_numeric(bowling["runs_total"], errors="coerce").sum()

    # Balls (legal deliveries) for overs
    balls_faced = len(batting)
    balls_bowled = len(bowling)
    overs_faced = balls_faced / 6 if balls_faced > 0 else 1.0
    overs_bowled = balls_bowled / 6 if balls_bowled > 0 else 1.0
    return float(runs_for_total / overs_faced - runs_against_total / overs_bowled)


def _season_kpis(jab: pd.DataFrame) -> dict:
    """Calculate win%, NRR, and match counts per season."""
    result = {}
    for season, grp in jab.groupby("season"):
        n = len(grp)
        wins = grp["is_win"].sum()
        win_pct = wins / n * 100 if n > 0 else 0

        # Try innings columns first
        runs_for_col = pd.to_numeric(
            grp.apply(
                lambda r: r["innings_1_runs"] if r.get("innings_1_team") == TEAM else r["innings_2_runs"],
                axis=1,
            ),
            errors="coerce",
        )
        innings_available = runs_for_col.notna().any()

        if innings_available:
            runs_against = pd.to_numeric(
                grp.apply(
                    lambda r: r["innings_2_runs"] if r.get("innings_1_team") == TEAM else r["innings_1_runs"],
                    axis=1,
                ),
                errors="coerce",
            ).fillna(0)
            overs_faced = pd.to_numeric(
                grp.apply(
                    lambda r: r["innings_1_overs"] if r.get("innings_1_team") == TEAM else r["innings_2_overs"],
                    axis=1,
                ),
                errors="coerce",
            ).fillna(20.0).replace(0, 20.0)
            overs_bowled = pd.to_numeric(
                grp.apply(
                    lambda r: r["innings_2_overs"] if r.get("innings_1_team") == TEAM else r["innings_1_overs"],
                    axis=1,
                ),
                errors="coerce",
            ).fillna(20.0).replace(0, 20.0)
            runs_for_col = runs_for_col.fillna(0)
            nrr = (runs_for_col / overs_faced).mean() - (runs_against / overs_bowled).mean()
        else:
            # Compute from ball-by-ball
            nrr = _nrr_from_bbb(grp["match_id"].tolist(), season)

        result[season] = {
            "n": n,
            "wins": int(wins),
            "losses": n - int(wins),
            "win_pct": win_pct,
            "nrr": nrr,
        }
    return result


def _nrr_from_bbb(match_ids: list, season: str) -> float:
    """Calculate NRR from ball-by-ball data."""
    try:
        bbb = pd.read_parquet("data/normalized/ball_by_ball_normalized.parquet")
        bbb = bbb[bbb["match_id"].isin(match_ids)].copy()
        if bbb.empty:
            return float("nan")

        # Runs for (Janakpur batting)
        batting = bbb[bbb["batting_team"] == TEAM]
        # Runs against (Janakpur bowling)
        bowling = bbb[bbb["bowling_team"] == TEAM]

        runs_for_total = pd.to_numeric(batting["runs_total"], errors="coerce").sum()
        runs_against_total = pd.to_numeric(bowling["runs_total"], errors="coerce").sum()

        # Balls (legal deliveries) for overs
        # Each row is one delivery; divide by 6 for overs
        balls_faced = len(batting)
        balls_bowled = len(bowling)
        overs_faced = balls_faced / 6 if balls_faced > 0 else 1.0
        overs_bowled = balls_bowled / 6 if balls_bowled > 0 else 1.0

        nrr = (runs_for_total / overs_faced) - (runs_against_total / overs_bowled)
        return float(nrr)
    except Exception:
        return float("nan")


def _form_index(jab: pd.DataFrame, n_recent: int = 5) -> float:
    """Last N matches win rate."""
    recent = jab.sort_values("match_date").tail(n_recent)
    return recent["is_win"].mean() * 100


def _momentum_chart(jab: pd.DataFrame | None) -> None:
    """Plot win rate trajectory by season."""
    if jab is None or jab.empty:
        # Fallback demo
        data = pd.DataFrame({
            "match": ["M1", "M2", "M3", "M4", "M5", "M6"],
            "team_form": [58, 63, 61, 69, 72, 78],
            "middle_over_index": [52, 55, 60, 67, 70, 74],
        })
        fig = px.line(data, x="match", y=["team_form", "middle_over_index"],
                      markers=True, color_discrete_sequence=["#103b2f", "#b7802f"])
        fig.update_layout(height=280, margin=dict(l=20, r=10, t=20, b=20),
                          paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                          legend_title_text="", yaxis_title="Index", xaxis_title="Recent Matches")
        fig.update_traces(line_width=3)
        st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})
        return

    rows = []
    for season, grp in jab.groupby("season"):
        grp = grp.sort_values("match_date").reset_index(drop=True)
        grp["match_num"] = range(1, len(grp) + 1)
        grp["cum_wins"] = grp["is_win"].cumsum()
        grp["win_rate_pct"] = (grp["cum_wins"] / grp["match_num"] * 100).round(1)
        grp["label"] = season
        rows.append(grp[["match_num", "win_rate_pct", "label", "match_date", "winner_name"]])

    plot_df = pd.concat(rows, ignore_index=True)
    season_colors = {"S1": "#103b2f", "S2": "#b42318"}

    fig = go.Figure()
    for season, grp in plot_df.groupby("label"):
        color = season_colors.get(season, "#b7802f")
        fig.add_trace(go.Scatter(
            x=grp["match_num"], y=grp["win_rate_pct"],
            mode="lines+markers", name=season,
            line=dict(color=color, width=3),
            marker=dict(size=7),
            hovertemplate=(
                f"<b>{season}</b> Match %{{x}}<br>"
                "Win Rate: %{y:.1f}%<extra></extra>"
            ),
        ))

    fig.add_hline(y=50, line_dash="dot", line_color="#7d8f88", line_width=1,
                  annotation_text="50% break-even", annotation_position="bottom right")

    fig.update_layout(
        height=280,
        margin=dict(l=20, r=10, t=20, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend_title_text="Season",
        yaxis_title="Win Rate %",
        xaxis_title="Match Number",
        yaxis=dict(range=[0, 105], gridcolor="rgba(0,0,0,0.06)"),
        xaxis=dict(gridcolor="rgba(0,0,0,0.06)"),
    )
    st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})


def render_executive_overview():
    jab = _load_real_matches()
    season_kpis = _season_kpis(jab) if jab is not None else {}
    s1 = season_kpis.get("S1", {})
    s2 = season_kpis.get("S2", {})
    form_idx = _form_index(jab) if jab is not None else 0.0

    # Legacy data_source for contributor tables + quality check
    match_df, data_source = load_match_records()
    quality_report = validate_match_records(match_df)

    st.markdown(
        """
        <div class="jb-page-head">
            <h2 class="page-title">Executive Overview</h2>
            <p class="page-subtitle">The story of a championship collapse — and the data-driven plan to recover.</p>
            <div class="insight-alert">
                <span class="insight-alert-icon">⚠️</span>
                <p class="insight-alert-text"><span class="insight-label">Core finding:</span> 70-90% of the S2 decline (likely ~80%) is retained-player underperformance, not roster turnover. The two largest execution failures are death bowling (+1.64 rpo, ~+8 runs/match) and powerplay batting (-0.75 rpo, ~-4.5 runs/match). See LIMITATIONS.md for the full sensitivity analysis.</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    s1_win_pct  = s1.get("win_pct", 0.0)
    s2_win_pct  = s2.get("win_pct", 0.0)
    s1_nrr      = s1.get("nrr", float("nan"))
    s2_nrr      = s2.get("nrr", float("nan"))
    s1_n        = s1.get("n", 0)
    s2_n        = s2.get("n", 0)
    win_delta   = s2_win_pct - s1_win_pct

    # Format NRR safely
    def _fmt_nrr(v):
        try:
            import math
            return f"{v:+.3f}" if v is not None and not math.isnan(v) else "N/A"
        except Exception:
            return "N/A"

    s2_nrr_str = _fmt_nrr(s2_nrr)
    nrr_delta_str = f"S1: {_fmt_nrr(s1_nrr)} | S2: {_fmt_nrr(s2_nrr)}"
    nrr_delta_class = "metric-card-delta-neutral"
    try:
        import math
        if not math.isnan(s2_nrr) and not math.isnan(s1_nrr):
            nrr_delta_class = "metric-card-delta-positive" if s2_nrr > s1_nrr else "metric-card-delta-negative"
    except Exception:
        pass

    win_delta_class = "metric-card-delta-negative" if win_delta < 0 else "metric-card-delta-positive"

    reliability_delta = (
        f"{quality_report['error_count']} errors, {quality_report['warning_count']} warnings"
        if quality_report["status"] != "healthy"
        else "Contract checks passing"
    )

    # Responsive columns: 5 on desktop, 2-3 on tablet, 1-2 on mobile
    c1, c2, c3, c4, c5 = st.columns([1, 1, 1, 1, 1])
    kpi_specs = [
        (c1, "S1 Win Rate",   f"{s1_win_pct:.1f}%", f"{s1.get('wins',0)}W/{s1.get('losses',0)}L  Champions", "metric-card-delta-positive"),
        (c2, "S2 Win Rate",   f"{s2_win_pct:.1f}%", f"{win_delta:+.1f}pp vs S1", win_delta_class),
        (c3, "Season NRR",    s2_nrr_str,            nrr_delta_str, nrr_delta_class),
        (c4, "Form Index",    f"{form_idx:.0f}%",    "Win rate — last 5 matches",
         "metric-card-delta-positive" if form_idx >= 50 else "metric-card-delta-negative"),
        (c5, "Data Reliability", str(quality_report["reliability_score"]), reliability_delta,
         "metric-card-delta-positive" if quality_report["status"] == "healthy" else "metric-card-delta-negative"),
    ]
    for col, label, value, delta, delta_class in kpi_specs:
        with col:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-card-label">{label}</div>
                    <div class="metric-card-value">{value}</div>
                    <div class="metric-card-delta {delta_class}">{delta}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.caption(f"📊 Data source: {'Parquet (Real)' if jab is not None else 'Demo'} — {s1_n} S1 matches, {s2_n} S2 matches")

    st.markdown("<div style='height:24px;'></div>", unsafe_allow_html=True)
    st.markdown("### 📖 Season Story Arc")
    st.markdown(f"""
    <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap:16px; margin: 16px 0;">
        <div style="background:linear-gradient(135deg, rgba(16,59,47,0.08), rgba(16,59,47,0.03)); 
                    border-left:4px solid #103b2f; padding:18px 20px; border-radius:var(--radius-md);
                    box-shadow:var(--shadow-sm); transition:all var(--transition-base);
                    animation:slideIn 0.4s ease-out;">
            <div style="font-size:10px; font-weight:700; text-transform:uppercase;
                        letter-spacing:.08em; color:#103b2f; margin-bottom:6px; display:flex; align-items:center; gap:8px;">
                <span style="font-size:16px;">🏆</span> Act 1 — S1: The Glory
            </div>
            <div style="font-size:28px; font-weight:800; color:#103b2f; margin:8px 0;">{s1_win_pct:.0f}% wins</div>
            <div style="font-size:13px; color:var(--on-surface-variant); line-height:1.5;">
                {s1.get('wins',0)}/{s1_n} matches • NPL Champions
            </div>
        </div>
        <div style="background:linear-gradient(135deg, rgba(180,35,24,0.08), rgba(180,35,24,0.03)); 
                    border-left:4px solid #b42318; padding:18px 20px; border-radius:var(--radius-md);
                    box-shadow:var(--shadow-sm); transition:all var(--transition-base);
                    animation:slideIn 0.4s ease-out 0.1s backwards;">
            <div style="font-size:10px; font-weight:700; text-transform:uppercase;
                        letter-spacing:.08em; color:#b42318; margin-bottom:6px; display:flex; align-items:center; gap:8px;">
                <span style="font-size:16px;">📉</span> Act 2 — S2: The Collapse
            </div>
            <div style="font-size:28px; font-weight:800; color:#b42318; margin:8px 0;">{s2_win_pct:.0f}% wins</div>
            <div style="font-size:13px; color:var(--on-surface-variant); line-height:1.5;">
                {s2.get('wins',0)}/{s2_n} matches • {win_delta:+.0f}pp ↓ from S1
            </div>
        </div>
        <div style="background:linear-gradient(135deg, rgba(183,128,47,0.08), rgba(183,128,47,0.03)); 
                    border-left:4px solid #b7802f; padding:18px 20px; border-radius:var(--radius-md);
                    box-shadow:var(--shadow-sm); transition:all var(--transition-base);
                    animation:slideIn 0.4s ease-out 0.2s backwards;">
            <div style="font-size:10px; font-weight:700; text-transform:uppercase;
                        letter-spacing:.08em; color:#b7802f; margin-bottom:6px; display:flex; align-items:center; gap:8px;">
                <span style="font-size:16px;">🎯</span> Act 3 — S3: The Recovery
            </div>
            <div style="font-size:28px; font-weight:800; color:#b7802f; margin:8px 0;">Rebuilding</div>
            <div style="font-size:13px; color:var(--on-surface-variant); line-height:1.5;">
                69 shortlisted targets • AI forecasts ready
            </div>
        </div>
    </div>
    <style>
        div[style*="slideIn"]:hover {{
            transform: translateY(-4px);
            box-shadow: var(--shadow-md) !important;
        }}
    </style>
    """, unsafe_allow_html=True)
    st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)

    left, right = st.columns([2.2, 1])

    with left:
        st.markdown(
            """
            <div class="card">
                <div class="card-header"><h3>Season Win-Rate Trajectory (S1 vs S2)</h3></div>
                <div class="card-body"></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        _momentum_chart(jab)
        st.markdown(
            """
            <div class="insight-box">
                <strong>Insight:</strong> S1 win rate climbed steadily to 70%. S2 opened 0-for-4 and never recovered — the collapse was immediate, not gradual.
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Dynamic contributor tables from real data
        bat_rows = ""
        bat_path = export_path("s3_batter_forecast.csv")
        if bat_path.exists():
            try:
                bdf = pd.read_csv(bat_path)
                top_bat = bdf[bdf['s2_runs'].notna()].nlargest(3, 's2_runs')
                for _, r in top_bat.iterrows():
                    sr_val = f"{r['s2_strike_rate']:.1f}" if pd.notna(r.get('s2_strike_rate')) else "—"
                    bat_rows += f"<tr><td>{r['player_name']}</td><td class='text-right'>{int(r['s2_runs'])}</td><td class='text-right'>{sr_val}</td></tr>"
            except Exception:
                pass
        if not bat_rows:
            bat_rows = "<tr><td colspan='3' style='text-align:center; color:var(--on-surface-variant);'>No data</td></tr>"

        bowl_rows = ""
        pp_wkts, mid_wkts, death_wkts = "—", "—", "—"
        bowl_path = export_path("s3_bowler_forecast.csv")
        phase_path = export_path("s1_vs_s2_bowling_by_phase.csv")
        if bowl_path.exists():
            try:
                bowldf = pd.read_csv(bowl_path)
                top_bowl = bowldf[bowldf['s2_wickets'].notna()].nlargest(3, 's2_wickets')
                for _, r in top_bowl.iterrows():
                    econ_val = f"{r['s2_economy']:.1f}" if pd.notna(r.get('s2_economy')) else "—"
                    econ_class = 'text-right text-error' if pd.notna(r.get('s2_economy')) and r['s2_economy'] > 8.5 else 'text-right'
                    bowl_rows += f"<tr><td>{r['player_name']}</td><td class='text-right'>{int(r['s2_wickets'])}</td><td class='{econ_class}'>{econ_val}</td></tr>"
            except Exception:
                pass
        if not bowl_rows:
            bowl_rows = "<tr><td colspan='3' style='text-align:center; color:var(--on-surface-variant);'>No data</td></tr>"
        if phase_path.exists():
            try:
                pdf = pd.read_csv(phase_path)
                s2 = pdf[pdf['season'] == 'S2']
                pp_wkts = str(int(s2[s2['phase'] == 'powerplay']['wickets_taken'].values[0]))
                mid_wkts = str(int(s2[s2['phase'] == 'middle']['wickets_taken'].values[0]))
                death_wkts = str(int(s2[s2['phase'] == 'death']['wickets_taken'].values[0]))
            except Exception:
                pass

        a, b = st.columns(2)
        with a:
            st.markdown(
                f"""
                <div class="card">
                    <div class="card-header"><h3>Top Batting Contributors (S2)</h3></div>
                    <div class="card-body">
                        <table class="data-table">
                            <thead><tr><th>Player</th><th class="text-right">Runs</th><th class="text-right">SR</th></tr></thead>
                            <tbody>{bat_rows}</tbody>
                        </table>
                        <div class="insight-box"><strong>Watch:</strong> Powerplay dot-ball rate increased +4.3% in S2 — top-order intent needs review.</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with b:
            st.markdown(
                f"""
                <div class="card">
                    <div class="card-header"><h3>Top Bowling Contributors (S2)</h3></div>
                    <div class="card-body">
                        <table class="data-table">
                            <thead><tr><th>Player</th><th class="text-right">Wkts</th><th class="text-right">Econ</th></tr></thead>
                            <tbody>{bowl_rows}</tbody>
                        </table>
                        <div style="display:flex; gap:8px; margin-top: 8px;">
                            <div class="phase-box" style="flex:1;"><div class="phase-box-label">PP Wkts</div><div class="phase-box-value">{pp_wkts}</div></div>
                            <div class="phase-box" style="flex:1;"><div class="phase-box-label">Middle</div><div class="phase-box-value">{mid_wkts}</div></div>
                            <div class="phase-box phase-box-error" style="flex:1;"><div class="phase-box-label phase-box-label-error">Death</div><div class="phase-box-value phase-box-value-error">{death_wkts}</div></div>
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    with right:
        st.markdown(
            """
            <div class="section-card">
                <div class="section-card-header section-card-header-primary">
                    <h3 class="section-card-title section-card-title-white">Tactical Command</h3>
                </div>
                <div class="section-card-body">
                    <div class="tactical-box tactical-box-error">
                        <div class="tactical-box-title tactical-box-title-error">Active Warning</div>
                        <div class="tactical-box-body">Opposition left-arm spin threat in overs 7-12.</div>
                    </div>
                    <div class="tactical-box tactical-box-success">
                        <div class="tactical-box-title tactical-box-title-success">Advantage</div>
                        <div class="tactical-box-body">Bolts pace battery in powerplay remains favorable.</div>
                    </div>
                    <div class="insight-box"><strong>Plan:</strong> attack PP with intent, hold two death specialists for 17-20.</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        findings = quality_report.get("findings", [])
        if findings:
            findings_markup = "".join(
                [
                    f"<li><strong>{item['message']}:</strong> {item['details']}</li>"
                    for item in findings[:3]
                ]
            )
            st.markdown(
                f"""
                <div style="height:12px;"></div>
                <div class="card">
                    <div class="card-header"><h3>Data Contract Findings</h3></div>
                    <div class="card-body">
                        <ul style="padding-left: 18px; margin: 0; line-height: 1.5;">
                            {findings_markup}
                        </ul>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                """
                <div style="height:12px;"></div>
                <div class="card">
                    <div class="card-header"><h3>Data Contract Findings</h3></div>
                    <div class="card-body">
                        <div class="insight-box"><strong>Status:</strong> Required fields, tiers, contexts, and result values are valid.</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        next_date = (datetime.now() + timedelta(days=3)).strftime("%b %d, %Y")
        st.markdown(
            f"""
            <div style="height:12px;"></div>
            <div class="card">
                <div class="card-header"><h3>Season 3 Preparation</h3></div>
                <div class="card-body">
                    <div style="font-size:20px; font-weight:800; color: var(--primary);">NPL Season 3</div>
                    <div style="font-size:13px; color: var(--on-surface-variant); margin-bottom: 12px;">Upcoming • Use Batting & Bowling Intelligence tabs for phase-level prep</div>
                    <div class="insight-box"><strong>Priority:</strong> Address death-over bowling (+1.64 rpo conditional economy) and powerplay batting (run rate -0.75 rpo, dot ball % +4.3pp). Middle overs net -0.68 rpo; powerplay bowling delta is small (+0.28 rpo).</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
