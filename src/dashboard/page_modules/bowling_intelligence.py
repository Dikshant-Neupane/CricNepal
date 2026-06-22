"""Bowling Intelligence — phase control, resource allocation, pressure plans."""

import streamlit as st
import pandas as pd
import plotly.express as px

from ..services.data_loaders import load_export_csv

TEAM = "Janakpur Bolts"

# Resolved hex values (CSS vars don't resolve inside st.markdown HTML)
_TEXT       = "#17231f"
_TEXT_MUTED = "#4a5a54"
_SURFACE_LO = "#edf2ef"
_BORDER     = "#cad4cf"
_GREEN      = "#103b2f"
_AMBER      = "#e89b3c"
_RED        = "#c74b4b"


def _render_live_heatmap() -> None:
    """Bowler runs-conceded heatmap from ball-by-ball data."""
    from ..services.data_loaders import load_ball_by_ball_normalized, load_matches_normalized

    bbb = load_ball_by_ball_normalized()
    if bbb is None:
        st.info("Heatmap unavailable — ball-by-ball parquet not found.")
        return

    matches = load_matches_normalized()
    if matches is not None and "season" in matches.columns:
        bbb = bbb.merge(matches[["match_id", "season"]], on="match_id", how="left")

    jab = bbb[bbb["bowling_team"] == TEAM].copy()

    if "season" in jab.columns and not jab[jab["season"] == "S2"].empty:
        data = jab[jab["season"] == "S2"].copy()
        label = "S2"
    else:
        data = jab
        label = "All Seasons"

    data["over_n"] = pd.to_numeric(data["over"], errors="coerce").astype("Int64")
    pivot = data.groupby(["bowler_name", "over_n"])["runs_total"].sum().reset_index()
    wide = pivot.pivot_table(index="bowler_name", columns="over_n", values="runs_total", aggfunc="sum").fillna(0)

    ball_counts = data.groupby("bowler_name").size()
    wide = wide.loc[wide.index.isin(ball_counts[ball_counts >= 12].index)].sort_index()
    wide.columns = [str(int(c)) if pd.notna(c) else str(c) for c in wide.columns]

    if wide.empty:
        st.info("Not enough data to build heatmap.")
        return

    fig = px.imshow(
        wide,
        labels=dict(x="Over", y="Bowler", color="Runs"),
        title=f"Runs Conceded per Over — JB Bowling ({label})",
        color_continuous_scale="RdYlGn_r",
        aspect="auto",
        text_auto=True,
    )
    fig.update_layout(height=350, margin=dict(l=10, r=10, t=40, b=10))
    fig.update_coloraxes(colorbar_title="Runs")
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    st.caption(f"Source: {label}. Bowlers with fewer than 12 balls excluded.")


def _load_bowling_phases() -> list[dict]:
    """Load S2 bowling phase metrics from CSV."""
    df = load_export_csv("s1_vs_s2_bowling_by_phase.csv")
    if df is None or df.empty:
        return []

    s2 = df[df["season"] == "S2"].copy()
    if s2.empty:
        return []

    s2 = s2.set_index("phase")
    phases = []

    for key, name in [("powerplay", "POWERPLAY (1–6)"), ("middle", "MIDDLE (7–15)"), ("death", "DEATH (16–20)")]:
        if key not in s2.index:
            continue
        row  = s2.loc[key]
        econ = float(row.get("economy", 0))
        econ_color     = _RED if econ > 8.5 else (_AMBER if econ > 7.5 else _GREEN)
        pressure       = "Critical" if econ > 9.0 else ("High" if econ > 7.5 else "Optimal")
        pressure_color = _RED if econ > 9.0 else (_AMBER if econ > 7.5 else _GREEN)
        phases.append({
            "name":       name,
            "econ":       f"{econ:.2f}",
            "econ_c":     econ_color,
            "wkts":       str(int(row.get("wickets_taken", 0))),
            "dot":        f"{float(row.get('dot_ball_pct', 0)):.1f}%",
            "pressure":   pressure,
            "pressure_c": pressure_color,
        })

    return phases


def _phase_card(p: dict) -> str:
    """Build the HTML for a single bowling phase card using only literal hex values."""
    return f"""
    <div style="background:{_SURFACE_LO};padding:16px;border-radius:8px;border:1px solid {_BORDER};">
        <div style="font-size:12px;font-weight:600;color:{_TEXT_MUTED};margin-bottom:14px;letter-spacing:0.04em;">
            {p['name']}
        </div>
        <div style="display:flex;justify-content:space-between;margin-bottom:10px;">
            <span style="font-size:13px;color:{_TEXT_MUTED};">Economy</span>
            <span style="font-size:14px;font-weight:600;color:{p['econ_c']};">{p['econ']}</span>
        </div>
        <div style="display:flex;justify-content:space-between;margin-bottom:10px;">
            <span style="font-size:13px;color:{_TEXT_MUTED};">Wickets</span>
            <span style="font-size:14px;font-weight:500;color:{_TEXT};">{p['wkts']}</span>
        </div>
        <div style="display:flex;justify-content:space-between;margin-bottom:10px;">
            <span style="font-size:13px;color:{_TEXT_MUTED};">Dot %</span>
            <span style="font-size:14px;font-weight:500;color:{_TEXT};">{p['dot']}</span>
        </div>
        <div style="display:flex;justify-content:space-between;padding-top:10px;border-top:1px solid {_BORDER};">
            <span style="font-size:13px;color:{_TEXT_MUTED};">Pressure Index</span>
            <span style="font-size:14px;font-weight:600;color:{p['pressure_c']};">{p['pressure']}</span>
        </div>
    </div>"""


def render_bowling_intelligence():
    st.markdown("""
    <div style="margin-bottom:32px;">
        <h2 style="font-size:28px;font-weight:800;color:#103b2f;margin:0 0 6px 0;">Bowling Intelligence</h2>
        <p style="color:#4a5a54;font-size:15px;margin:0;">Phase control, resource allocation, and pressure-over plans.</p>
    </div>
    """, unsafe_allow_html=True)

    #  Phase Breakdown 
    st.markdown(f"""
    <div style="background:#fff;border:1px solid {_BORDER};border-radius:12px;
                margin-bottom:28px;box-shadow:0 2px 8px rgba(12,36,28,0.05);">
        <div style="padding:14px 18px;border-bottom:1px solid {_BORDER};
                    background:linear-gradient(180deg,#fff,#f8fbf9);border-radius:12px 12px 0 0;">
            <span style="font-size:16px;font-weight:700;color:{_TEXT};">Bowling Phase Breakdown</span>
        </div>
        <div style="padding:20px;">
    """, unsafe_allow_html=True)

    phases = _load_bowling_phases()
    
    if not phases:
        st.info("Phase breakdown data is currently unavailable.")
    else:
        cols = st.columns(3)
        for col, p in zip(cols, phases):
            with col:
                st.markdown(_phase_card(p), unsafe_allow_html=True)

    st.markdown("</div></div>", unsafe_allow_html=True)

    #  Heatmap + Hand Split 
    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown(f"""
        <div style="background:#fff;border:1px solid {_BORDER};border-radius:12px;
                    box-shadow:0 2px 8px rgba(12,36,28,0.05);">
            <div style="padding:14px 18px;border-bottom:1px solid {_BORDER};">
                <span style="font-size:15px;font-weight:700;color:{_TEXT};">Resource Allocation by Over (S2)</span>
            </div>
            <div style="padding:12px 16px 16px;">
        """, unsafe_allow_html=True)
        _render_live_heatmap()
        st.markdown("</div></div>", unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div style="background:#fff;border:1px solid {_BORDER};border-radius:12px;
                    box-shadow:0 2px 8px rgba(12,36,28,0.05);">
            <div style="padding:14px 18px;border-bottom:1px solid {_BORDER};">
                <span style="font-size:15px;font-weight:700;color:{_TEXT};">Split: vs Batter Hand</span>
            </div>
            <div style="padding:16px;">
        """, unsafe_allow_html=True)
        st.info("Batter hand split metrics require additional scouting data.")
        st.markdown("</div></div>", unsafe_allow_html=True)

    st.markdown("<div style='height:18px;'></div>", unsafe_allow_html=True)

    #  Tactical Directives
    st.markdown("""
    <div style="background:linear-gradient(135deg,#103b2f,#18503f);padding:20px;border-radius:12px;">
        <div style="color:#ffffff;font-size:17px;font-weight:700;margin-bottom:16px;
                    font-family:Manrope,sans-serif;letter-spacing:-0.01em;">
            Tactical Directives
        </div>
    """, unsafe_allow_html=True)

    st.info("Tactical directives require live tactical scouting integration.")

    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)

    #  Decision Summary 
    st.markdown(f"""
    <div style="background:#fff;border:1px solid {_BORDER};border-radius:12px;
                box-shadow:0 2px 8px rgba(12,36,28,0.05);">
        <div style="padding:14px 18px;border-bottom:1px solid {_BORDER};">
            <span style="font-size:15px;font-weight:700;color:{_TEXT};">Decision Summary</span>
        </div>
        <div style="padding:16px;display:flex;flex-direction:column;gap:8px;">
            <div style="background:#edf2ef;border-left:3px solid #7d8f88;border-radius:6px;
                        padding:10px 12px;font-size:13px;color:{_TEXT};line-height:1.5;">
                <strong>Notice:</strong> Detailed risk/action tracking depends on full ball-by-ball telemetry integration.
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
