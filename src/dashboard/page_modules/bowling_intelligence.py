"""Bowling Intelligence — phase control, resource allocation, pressure plans."""

import streamlit as st
import pandas as pd
import plotly.express as px


TEAM = "Janakpur Bolts"

# Resolved hex values (CSS vars don't resolve inside st.markdown HTML)
_TEXT       = "#17231f"
_TEXT_MUTED = "#4a5a54"
_SURFACE_LO = "#edf2ef"
_BORDER     = "#cad4cf"
_GREEN      = "#103b2f"
_AMBER      = "#e89b3c"
_RED        = "#c74b4b"


def _hand_split_rows() -> list[dict]:
    """Janakpur S2 bowling economy/wickets vs left- and right-hand batters.

    Batter hands come from the tracked player-profiles file (registry
    names, same as ball-by-ball); coverage over Janakpur's S2 bowling
    balls is effectively complete. Returns [] when either source is
    missing so the card can say so honestly instead of rendering a
    permanent "unavailable" placeholder.
    """
    from ..services.data_loaders import load_bbb_with_season
    from src.config.paths import PROFILES_DIR

    bbb = load_bbb_with_season()
    if bbb is None or bbb.empty:
        return []
    jb = bbb[(bbb["bowling_team"] == TEAM) & (bbb["season"] == "S2")]
    if jb.empty:
        return []
    profiles_path = PROFILES_DIR / "enriched_players_20260521.csv"
    if not profiles_path.exists():
        return []
    profiles = pd.read_csv(profiles_path, usecols=["player_name", "batting_hand"])
    hands = dict(zip(profiles["player_name"], profiles["batting_hand"]))
    jb = jb.assign(hand=jb["batter_name"].map(hands))
    known = jb[jb["hand"].isin(["Left", "Right"])]
    if known.empty or len(known) < 0.5 * len(jb):
        return []
    rows = []
    for hand in ["Left", "Right"]:
        g = known[known["hand"] == hand]
        if g.empty:
            continue
        legal = int((~g["extras_type"].isin(["wides", "noballs"])).sum())
        econ = g["runs_total"].sum() / (legal / 6) if legal else 0.0
        rows.append(
            {
                "hand": f"{hand}-hand batters",
                "balls": len(g),
                "econ": econ,
                "wkts": int(g["is_wicket"].sum()),
            }
        )
    return rows


def _tactical_directives(phases: list[dict]) -> list[str]:
    """Directives derived from the phase breakdown shown on this page."""
    if not phases:
        return []
    parsed = []
    for p in phases:
        try:
            parsed.append((p["name"], float(p["econ"]), float(p["dot"].rstrip("%")), int(p["wkts"])))
        except (ValueError, KeyError):
            continue
    if not parsed:
        return []
    directives = []
    worst = max(parsed, key=lambda t: t[1])
    best = min(parsed, key=lambda t: t[1])
    directives.append(
        f"Most expensive phase: {worst[0]} at {worst[1]:.2f} RPO — tighten "
        "fields and bowling changes there first."
    )
    directives.append(
        f"Most controlled phase: {best[0]} at {best[1]:.2f} RPO with "
        f"{best[2]:.1f}% dot balls — protect this strength when planning overs."
    )
    most_wkts = max(parsed, key=lambda t: t[3])
    directives.append(
        f"Wicket threat concentrates in {most_wkts[0]} ({most_wkts[3]} wickets in S2) "
        "— hold attacking options for that window."
    )
    return directives


def _render_live_heatmap() -> None:
    """Bowler runs-conceded heatmap from ball-by-ball data."""
    from ..services.data_loaders import load_ball_by_ball_normalized, load_matches_normalized

    bbb = load_ball_by_ball_normalized()
    if bbb is None:
        st.caption("Heatmap unavailable — ball-by-ball parquet not found.")
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
        st.caption("Not enough data to build heatmap.")
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
    """Calculate bowling phase metrics directly from ball-by-ball data."""
    from ..services.data_loaders import load_bbb_with_season
    
    bbb = load_bbb_with_season()
    if bbb is None or bbb.empty:
        st.caption(" Phase data unavailable — no ball-by-ball data.")
        return []
        
    jb = bbb[(bbb['bowling_team'] == TEAM) & (bbb['season'] == 'S2')]
    if jb.empty:
        st.caption(" Phase data unavailable — no S2 data for Janakpur Bolts.")
        return []

    phases = []
    
    phase_map = [
        ("Powerplay", "POWERPLAY (1–6)"),
        ("Middle", "MIDDLE (7–15)"),
        ("Death", "DEATH (16–20)")
    ]
    
    for key, name in phase_map:
        df = jb[jb['phase'] == key]
        if df.empty:
            continue
            
        runs = df['runs_total'].sum()
        balls = len(df)
        overs = balls / 6.0
        econ = runs / overs if overs > 0 else 0
        wkts = len(df[df['is_wicket'] == True])
        dots = len(df[df['runs_total'] == 0])
        dot_pct = (dots / balls * 100) if balls > 0 else 0
        
        econ_color     = _RED if econ > 8.5 else (_AMBER if econ > 7.5 else _GREEN)
        pressure       = "Critical" if econ > 9.0 else ("High" if econ > 7.5 else "Optimal")
        pressure_color = _RED if econ > 9.0 else (_AMBER if econ > 7.5 else _GREEN)
        
        phases.append({
            "name":       name,
            "econ":       f"{econ:.2f}",
            "econ_c":     econ_color,
            "wkts":       str(int(wkts)),
            "dot":        f"{dot_pct:.1f}%",
            "pressure":   pressure,
            "pressure_c": pressure_color,
        })

    if not phases:
        st.caption(" Phase data estimated — could not compute phases from BBB.")
        return []

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


def _hand_card(h: dict) -> str:
    """Build the HTML for a batter-hand split card."""
    return f"""
    <div style="background:{_SURFACE_LO};padding:16px;border-radius:8px;border:1px solid {_BORDER};margin-bottom:14px;">
        <div style="font-size:12px;font-weight:600;color:{_TEXT_MUTED};margin-bottom:10px;">vs {h['hand']}</div>
        <div style="display:flex;justify-content:space-between;">
            <div>
                <div style="font-size:12px;color:{_TEXT_MUTED};">Economy</div>
                <div style="font-size:16px;font-weight:600;color:{_TEXT};margin-top:4px;">{h['economy']}</div>
            </div>
            <div style="text-align:right;">
                <div style="font-size:12px;color:{_TEXT_MUTED};">Strike Rate</div>
                <div style="font-size:16px;font-weight:600;color:{_TEXT};margin-top:4px;">{h['strike_rate']}</div>
            </div>
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
        hand_rows = _hand_split_rows()
        if hand_rows:
            for r in hand_rows:
                st.markdown(
                    f"<div style='display:flex;justify-content:space-between;font-size:13px;margin-bottom:8px;'>"
                    f"<span style='color:{_TEXT_MUTED};'>{r['hand']}</span>"
                    f"<span style='font-weight:600;color:{_TEXT};'>{r['econ']:.2f} econ · {r['wkts']} wkts · {r['balls']} balls</span></div>",
                    unsafe_allow_html=True,
                )
            st.caption("S2, Janakpur bowling. Hands from player profiles; "
                       "balls with unknown hand excluded.")
        else:
            st.caption("Batter hand data unavailable for this dataset.")
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

    directives = _tactical_directives(phases)
    if directives:
        items = "".join(
            f"<div style='color:#e8f0ec;font-size:14px;line-height:1.6;margin-bottom:8px;'>• {d}</div>"
            for d in directives
        )
        st.markdown(items, unsafe_allow_html=True)
    else:
        st.caption("Tactical directives unavailable — phase data missing.")

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
                <strong>Insight:</strong> Middle-over control remains your most stable wicket-taking phase.
            </div>
            <div style="background:rgba(245,158,11,0.07);border-left:3px solid #f59e0b;border-radius:6px;
                        padding:10px 12px;font-size:13px;color:{_TEXT};line-height:1.5;">
                <strong>Risk:</strong> Death overs leak value when slower-ball patterns are shown too early.
            </div>
            <div style="background:rgba(5,122,85,0.07);border-left:3px solid #057a55;border-radius:6px;
                        padding:10px 12px;font-size:13px;color:{_TEXT};line-height:1.5;">
                <strong>Recommended Action:</strong> Delay variation reveal and keep one specialist fresh for over 19.
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
