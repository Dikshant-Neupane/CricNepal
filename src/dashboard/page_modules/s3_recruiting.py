"""S3 Recruiting Shortlist page — wired to deliverables CSVs."""

import os
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))

_SHORTLIST_PATH = os.path.join(ROOT, "deliverables", "janakpur_s3_shortlist_matrix.csv")
_RIDGE_PATH = os.path.join(ROOT, "deliverables", "s3_predictions_ridge_ranked.csv")


def _load_data() -> pd.DataFrame | None:
    """Load and merge shortlist with model predictions."""
    try:
        shortlist = pd.read_csv(_SHORTLIST_PATH)
        ridge = pd.read_csv(_RIDGE_PATH)
        merged = shortlist.merge(
            ridge[["player_name", "pred_s3_final", "pred_s3_shrinkage",
                   "s2_balls", "confidence_tier", "perf_tier", "model_rationale"]],
            on="player_name",
            how="left",
        )
        return merged
    except FileNotFoundError as e:
        st.error(f"Shortlist data not found: {e}")
        return None
    except Exception as e:
        st.error(f"Error loading shortlist: {e}")
        return None


def _tier_color(tier: str) -> str:
    return {
        "TIER-1 PRIORITY": "#103b2f",
        "TIER-2 CONSIDER": "#b7802f",
        "TIER-3 MONITOR": "#7d8f88",
    }.get(tier, "#999")


def _delta_arrow(val: float | None) -> str:
    if val is None or pd.isna(val):
        return "—"
    return f"▲ {val:.2f}" if val > 0 else f"▼ {abs(val):.2f}"


def render_s3_recruiting() -> None:
    st.markdown("""
    <div class="jb-page-head">
        <h2 class="page-title">🎯 S3 Recruiting Shortlist</h2>
        <p class="page-subtitle">Bayesian shrinkage forecasts for S3 bowler economy.
        Ranked by multi-criteria weighted score (SOS economy, dot-ball %, death economy, volume).</p>
    </div>
    """, unsafe_allow_html=True)

    with st.expander("📊 **Model Methodology** — Click to expand", expanded=False):
        st.markdown("""
        **Bayesian Shrinkage Estimator** trained on n=33 paired seasons:
        - Ridge regression did **NOT** beat the shrinkage baseline (LOO-MSE 6.31 vs 3.51)
        - Formula: `reliability = balls / (balls + 30)`
        - Prediction: `S3 estimate = reliability × S2_economy + (1 − reliability) × league_avg (8.2)`
        - Higher confidence = more data = more trustworthy forecast
        """)

    st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)
    if df is None:
        return

    t1 = df[df["shortlist_tier"] == "TIER-1 PRIORITY"]
    t2 = df[df["shortlist_tier"] == "TIER-2 CONSIDER"]
    t3 = df[df["shortlist_tier"] == "TIER-3 MONITOR"]
    high_conf = df[df.get("confidence_tier", pd.Series(dtype=str)).str.startswith("HIGH", na=False)]
    
    st.markdown("### 📊 Shortlist Summary")
    k1, k2, k3, k4 = st.columns(4)
    for col, label, value, color, icon in [
        (k1, "Tier-1 Priorities", len(t1), "#103b2f", "🎯"),
        (k2, "Tier-2 Candidates", len(t2), "#b7802f", "🔶"),
        (k3, "Tier-3 Monitors",   len(t3), "#7d8f88", "⚪"),
        (k4, "High Confidence",   len(high_conf), "#1a6b51", "✅"),
    ]:
        with col:
            st.markdown(f"""
            <div class="metric-card">
                <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                    <div class="metric-card-label">{label}</div>
                    <span style="font-size:20px;">{icon}</span>
                </div>
                <div class="metric-card-value" style="color:{color};">{value}</div>
                <div style="font-size:11px; color:var(--on-surface-variant); margin-top:8px;">
                    {(value/len(df)*100):.1f}% of pool
                </div>
            </div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:24px;'></div>", unsafe_allow_html=True)
    st.markdown("### 🎛️ Filter Players")
    
    f1, f2, f3 = st.columns(3)
    all_tiers = ["TIER-1 PRIORITY", "TIER-2 CONSIDER", "TIER-3 MONITOR"]
    all_confs = sorted(df["confidence_tier"].dropna().unique().tolist()) if "confidence_tier" in df.columns else []
    all_types = sorted([x for x in df["bowling_type"].dropna().unique() if str(x) not in ("nan", "")]) if "bowling_type" in df.columns else []

    with f1:
        tier_filter = st.multiselect(
            "📋 Shortlist Tier", all_tiers,
            default=["TIER-1 PRIORITY", "TIER-2 CONSIDER"],
            key="s3_tier_filter",
            help="Filter by recruitment priority tier"
        )
    with f2:
        conf_filter = st.multiselect(
            "📈 Confidence Level", all_confs,
            default=[c for c in all_confs if "HIGH" in c or "MEDIUM" in c],
            key="s3_conf_filter",
            help="Filter by prediction confidence (based on balls bowled)"
        )
    with f3:
        type_filter = st.multiselect(
            "🎳 Bowling Type", all_types, default=all_types,
            key="s3_type_filter",
            help="Filter by bowling style"
        )

    filtered = df.copy()
    if tier_filter:
        filtered = filtered[filtered["shortlist_tier"].isin(tier_filter)]
    if conf_filter and "confidence_tier" in filtered.columns:
        filtered = filtered[filtered["confidence_tier"].isin(conf_filter)]
    if type_filter and "bowling_type" in filtered.columns:
        filtered = filtered[filtered["bowling_type"].isin(type_filter)]

    if len(filtered) == 0:
        st.warning("🔍 No players match the current filters. Try adjusting your selection.")
        return
    
    st.success(f"✅ **{len(filtered)} players** match filters ({(len(filtered)/len(df)*100):.1f}% of total pool)")

    st.markdown("<div style='height:20px;'></div>", unsafe_allow_html=True)

    scatter_df = filtered.dropna(subset=["sos_economy", "pred_s3_final"]).copy()
    if not scatter_df.empty:
        st.markdown("### 📊 S2 Economy vs S3 Forecast")
        st.caption("💡 Bubble size = balls bowled in S2. Better players sit **bottom-left** (lower economy). Hover for details.")
        fig = px.scatter(
            scatter_df,
            x="sos_economy",
            y="pred_s3_final",
            size=scatter_df["s2_balls"].clip(lower=5),
            color="shortlist_tier",
            hover_name="player_name",
            hover_data={
                "sos_economy": ":.2f",
                "pred_s3_final": ":.2f",
                "s2_balls": True,
                "confidence_tier": True,
                "shortlist_tier": False,
            },
            color_discrete_map={
                "TIER-1 PRIORITY": "#103b2f",
                "TIER-2 CONSIDER": "#b7802f",
                "TIER-3 MONITOR": "#7d8f88",
            },
            labels={
                "sos_economy": "S2 SOS Economy (runs/over)",
                "pred_s3_final": "S3 Predicted Economy",
            },
        )
        # Add diagonal reference line
        min_val = min(scatter_df["sos_economy"].min(), scatter_df["pred_s3_final"].min()) - 0.3
        max_val = max(scatter_df["sos_economy"].max(), scatter_df["pred_s3_final"].max()) + 0.3
        fig.add_trace(go.Scatter(
            x=[min_val, max_val], y=[min_val, max_val],
            mode="lines", line=dict(dash="dot", color="#999", width=1),
            name="No change (S2=S3)", showlegend=True,
        ))
        fig.update_layout(
            height=420,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            legend_title_text="Tier",
            xaxis=dict(gridcolor="rgba(0,0,0,0.06)"),
            yaxis=dict(gridcolor="rgba(0,0,0,0.06)"),
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    else:
        st.info("No scatter data for current filters.")

    st.markdown("#### Full Shortlist Rankings")
    display_cols = [
        "rank", "player_name", "shortlist_score", "shortlist_tier",
        "sos_economy", "dot_ball_pct", "death_econ_raw",
        "pred_s3_final", "confidence_tier",
        "age", "bowling_type",
    ]
    display_cols = [c for c in display_cols if c in filtered.columns]
    table = filtered[display_cols].sort_values("rank").reset_index(drop=True)

    # Rename for display clarity
    rename_map = {
        "rank": "#",
        "player_name": "Player",
        "shortlist_score": "Score",
        "shortlist_tier": "Tier",
        "sos_economy": "SOS Econ",
        "dot_ball_pct": "Dot%",
        "death_econ_raw": "Death Econ",
        "pred_s3_final": "S3 Forecast",
        "confidence_tier": "Confidence",
        "age": "Age",
        "bowling_type": "Type",
    }
    table = table.rename(columns={k: v for k, v in rename_map.items() if k in table.columns})

    st.dataframe(table, use_container_width=True, hide_index=True)

    # ── Model explanation expander ────────────────────────────────────────────
    with st.expander("Model Methodology & Confidence Tiers"):
        st.markdown("""
**Bayesian Shrinkage Formula:**
```
reliability   = balls_s2 / (balls_s2 + 30)
S3_estimate   = reliability × S2_economy + (1 - reliability) × 8.20
```

**Confidence Tiers:**
| Tier | Balls Bowled | Interpretation |
|------|-------------|----------------|
| HIGH (≥60 balls) | ≥60 | Reliable — trust the forecast |
| MEDIUM (30–59 balls) | 30–59 | Moderate shrinkage toward average |
| LOW (<30 balls) | <30 | High uncertainty — near-average forecast |

**Shortlist Score weights:**
- 40% SOS-adjusted economy
- 20% dot-ball percentage
- 20% death-over economy
- 20% volume (balls bowled)

**Why shrinkage beat Ridge:** With only 33 paired seasons, Ridge regression overfit on sparse features.
LOO cross-validation MSE: Ridge = 6.31 vs Shrinkage = 3.51.
        """)

    st.markdown("---")
    st.markdown("#### Player Deep-Dive")
    player_names = filtered["player_name"].dropna().sort_values().tolist()
    if player_names:
        selected = st.selectbox("Select a player to inspect", player_names, key="s3_player_select")
        row = filtered[filtered["player_name"] == selected].iloc[0]
        pc1, pc2, pc3, pc4 = st.columns(4)
        for col, label, val in [
            (pc1, "S3 Forecast Economy", f"{row.get('pred_s3_final', '—'):.2f}" if pd.notna(row.get("pred_s3_final")) else "—"),
            (pc2, "S2 SOS Economy",       f"{row.get('sos_economy', '—'):.2f}" if pd.notna(row.get("sos_economy")) else "—"),
            (pc3, "Shortlist Score",      f"{row.get('shortlist_score', '—'):.3f}" if pd.notna(row.get("shortlist_score")) else "—"),
            (pc4, "Confidence Tier",      str(row.get("confidence_tier", "—"))),
        ]:
            with col:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-card-label">{label}</div>
                    <div class="metric-card-value">{val}</div>
                </div>""", unsafe_allow_html=True)
        if pd.notna(row.get("model_rationale")):
            st.caption(f"Model note: {row['model_rationale']}")
