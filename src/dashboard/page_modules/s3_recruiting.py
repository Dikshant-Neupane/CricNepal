"""S3 selection intelligence page with form rankings and recruiting shortlist."""

import os

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from ..components.ui_patterns import render_insight_card, render_page_header, render_spacer
from ..services.player_form import load_player_form_table, summarize_selection_decisions

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))

_SHORTLIST_PATH = os.path.join(ROOT, "deliverables", "janakpur_s3_shortlist_matrix.csv")
_RIDGE_PATH = os.path.join(ROOT, "deliverables", "s3_predictions_ridge_ranked.csv")
MIN_VOLUME_FOR_SHORTLIST = 12


def _load_data() -> pd.DataFrame | None:
    """Load and merge shortlist with model predictions."""
    try:
        shortlist = pd.read_csv(_SHORTLIST_PATH)
        ridge = pd.read_csv(_RIDGE_PATH)
        merged = shortlist.merge(
            ridge[[
                "player_name",
                "pred_s3_final",
                "pred_s3_shrinkage",
                "pred_s3_low",
                "pred_s3_high",
                "s2_balls",
                "confidence_tier",
                "perf_tier",
                "model_rationale",
            ]],
            on="player_name",
            how="left",
        )
        if "balls_bowled" not in merged.columns and "s2_balls" in merged.columns:
            merged["balls_bowled"] = merged["s2_balls"]
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


def _analyze_priority_gaps(form_table: pd.DataFrame) -> list[dict[str, str]]:
    """Identify critical tactical role gaps for recruitment priority."""
    critical_roles = {
        "Death specialist": {"min_stable": 2, "priority": "HIGH"},
        "Powerplay strike bowler": {"min_stable": 2, "priority": "HIGH"},
        "Finisher (explosive)": {"min_stable": 1, "priority": "MEDIUM"},
        "Opener (intent)": {"min_stable": 1, "priority": "MEDIUM"},
        "Middle-overs controller": {"min_stable": 3, "priority": "MEDIUM"},
    }
    
    gaps = []
    for role, targets in critical_roles.items():
        role_data = form_table[form_table["recommended_role"] == role]
        total = len(role_data)
        stable_or_better = int(role_data["form_band"].isin(["In Form", "Stable"]).sum())
        gap_size = max(0, targets["min_stable"] - stable_or_better)
        
        if gap_size > 0 or total == 0:
            status = "🔴 URGENT" if targets["priority"] == "HIGH" else "🟡 MONITOR"
            if total == 0:
                recommendation = f"Zero {role.lower()} players identified. Recruit external talent immediately."
            elif stable_or_better == 0:
                recommendation = f"{total} player(s) present but all risky/out of form. Seek backup or upgrade."
            else:
                recommendation = f"Need {gap_size} more stable {role.lower()}(s) to meet minimum squad depth."
            
            gaps.append({
                "status": status,
                "role": role,
                "current": f"{stable_or_better}/{targets['min_stable']}",
                "recommendation": recommendation,
            })
    
    return gaps


def _delta_arrow(val: float | None) -> str:
    if val is None or pd.isna(val):
        return "—"
    return f"▲ {val:.2f}" if val > 0 else f"▼ {abs(val):.2f}"


def _render_form_ranking_tab() -> None:
    form_table = load_player_form_table()
    if form_table.empty:
        st.warning("Player form data is unavailable. Check parquet inputs before using the S3 selection view.")
        return

    render_insight_card("Selection Decision Lens", summarize_selection_decisions(form_table))
    render_spacer(20)

    summary_columns = st.columns(4)
    summary_metrics = [
        ("Players Ranked", len(form_table), "📋"),
        ("In Form", int((form_table["form_band"] == "In Form").sum()), "🔥"),
        ("Risky / Out", int(form_table["form_band"].isin(["Risky", "Out of Form"]).sum()), "⚠️"),
        ("Top Weighted Form", f"{form_table['weighted_form_score'].max():.1f}", "🎯"),
    ]
    for column, (label, value, icon) in zip(summary_columns, summary_metrics):
        with column:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                        <div class="metric-card-label">{label}</div>
                        <span style="font-size:20px;">{icon}</span>
                    </div>
                    <div class="metric-card-value">{value}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    render_spacer(20)
    
    # Visual insights section
    st.markdown("### Squad Intelligence Overview")
    chart_col1, chart_col2 = st.columns(2)
    
    with chart_col1:
        # Form band distribution
        band_counts = form_table["form_band"].value_counts().reindex(
            ["In Form", "Stable", "Risky", "Out of Form"], fill_value=0
        )
        fig_bands = go.Figure(data=[
            go.Bar(
                x=band_counts.index,
                y=band_counts.values,
                marker_color=["#1e7d5e", "#3a9679", "#e89b3c", "#c74b4b"],
                text=band_counts.values,
                textposition="outside",
            )
        ])
        fig_bands.update_layout(
            title="Form Band Distribution",
            xaxis_title="Form Band",
            yaxis_title="Player Count",
            height=300,
            margin=dict(l=20, r=20, t=40, b=20),
            showlegend=False,
        )
        st.plotly_chart(fig_bands, use_container_width=True)
    
    with chart_col2:
        # Role coverage by form band
        role_form_matrix = pd.crosstab(
            form_table["recommended_role"],
            form_table["form_band"],
        )
        # Reorder columns to match band priority
        role_form_matrix = role_form_matrix.reindex(
            columns=["In Form", "Stable", "Risky", "Out of Form"], fill_value=0
        )
        # Sort by total count descending
        role_form_matrix["_total"] = role_form_matrix.sum(axis=1)
        role_form_matrix = role_form_matrix.sort_values("_total", ascending=False).drop("_total", axis=1)
        
        fig_coverage = go.Figure(data=go.Heatmap(
            z=role_form_matrix.values,
            x=role_form_matrix.columns,
            y=role_form_matrix.index,
            colorscale=[[0, "#f5f5f5"], [0.5, "#3a9679"], [1, "#1e7d5e"]],
            text=role_form_matrix.values,
            texttemplate="%{text}",
            textfont={"size": 10},
            showscale=False,
        ))
        fig_coverage.update_layout(
            title="Role Coverage by Form Band",
            xaxis_title="Form Band",
            yaxis_title="S3 Tactical Role",
            height=400,
            margin=dict(l=20, r=20, t=40, b=20),
        )
        st.plotly_chart(fig_coverage, use_container_width=True)
    
    render_spacer(20)
    
    # Priority recruitment recommendations
    priority_gaps = _analyze_priority_gaps(form_table)
    if priority_gaps:
        st.markdown("### Priority Recruitment Recommendations")
        st.caption("Based on minimum squad depth targets for critical tactical roles.")
        
        for gap in priority_gaps:
            st.markdown(
                f"""
                <div style="
                    background: var(--surface-secondary); 
                    border-left: 4px solid {'#c74b4b' if '🔴' in gap['status'] else '#e89b3c'}; 
                    padding: 12px 16px; 
                    margin-bottom: 12px; 
                    border-radius: 4px;
                ">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                        <strong>{gap['status']} {gap['role']}</strong>
                        <span style="
                            background: var(--surface); 
                            padding: 4px 10px; 
                            border-radius: 12px; 
                            font-size: 12px;
                            font-weight: 600;
                        ">Coverage: {gap['current']}</span>
                    </div>
                    <div style="color: var(--on-surface-variant); font-size: 14px;">
                        {gap['recommendation']}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    
    render_spacer(20)
    filter_col_1, filter_col_2, filter_col_3 = st.columns(3)
    with filter_col_1:
        roles = ["All"] + sorted(form_table["primary_role"].dropna().unique().tolist())
        role_filter = st.selectbox("Primary Role", roles, index=0, key="s3_form_role")
    with filter_col_2:
        bands = ["All", "In Form", "Stable", "Risky", "Out of Form"]
        band_filter = st.selectbox("Form Band", bands, index=0, key="s3_form_band")
    with filter_col_3:
        s3_roles = ["All"] + sorted(form_table["recommended_role"].dropna().unique().tolist())
        s3_role_filter = st.selectbox("S3 Tactical Role", s3_roles, index=0, key="s3_form_s3_role")

    filtered = form_table.copy()
    if role_filter != "All":
        filtered = filtered[filtered["primary_role"] == role_filter]
    if band_filter != "All":
        filtered = filtered[filtered["form_band"] == band_filter]
    if s3_role_filter != "All":
        filtered = filtered[filtered["recommended_role"] == s3_role_filter]

    filtered = filtered.reset_index(drop=True)
    filtered.insert(0, "rank", filtered.index + 1)

    display_table = filtered[
        [
            "rank",
            "player_name",
            "primary_role",
            "recent_matches",
            "raw_form_score",
            "weighted_form_score",
            "form_band",
            "recommended_role",
            "avg_runs",
            "avg_strike_rate",
            "avg_balls_faced",
            "avg_wickets",
            "avg_economy",
        ]
    ].rename(
        columns={
            "rank": "#",
            "player_name": "Player",
            "primary_role": "Role",
            "recent_matches": "Recent Matches",
            "raw_form_score": "Raw Form",
            "weighted_form_score": "Weighted Form",
            "form_band": "Band",
            "recommended_role": "S3 Role",
            "avg_runs": "Avg Runs",
            "avg_strike_rate": "Avg SR",
            "avg_balls_faced": "Avg Balls",
            "avg_wickets": "Avg Wkts",
            "avg_economy": "Avg Econ",
        }
    )

    st.markdown("### Player Form Ranking")
    st.caption("Weighted form uses tournament-quality evidence. Selection calls should prefer weighted form, then confirm with S1 vs S2 role deltas.")
    st.dataframe(display_table, width="stretch", hide_index=True)

    render_spacer(16)
    st.markdown("### Role Guidance")
    selected_player = st.selectbox(
        "Inspect a player",
        filtered["player_name"].tolist(),
        key="s3_form_player_detail",
    )
    row = filtered[filtered["player_name"] == selected_player].iloc[0]
    detail_columns = st.columns(3)
    detail_metrics = [
        ("Weighted Form", f"{row['weighted_form_score']:.1f}"),
        ("Recommended S3 Role", row["recommended_role"]),
        ("Form Band", row["form_band"]),
    ]
    for column, (label, value) in zip(detail_columns, detail_metrics):
        with column:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-card-label">{label}</div>
                    <div class="metric-card-value">{value}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    render_insight_card(
        f"{selected_player} — Season 3 Selection Call",
        [
            {"label": "Role", "text": row["role_recommendation"], "type": "success" if row["form_band"] in ["In Form", "Stable"] else "warning"},
            {"label": "S1 vs S2", "text": row["s1_s2_reference"], "type": "neutral"},
            {"label": "Action", "text": f"Use {row['recommended_role'].lower()} as the default S3 role if the next squad build needs {row['primary_role'].lower()} cover.", "type": "neutral"},
        ],
    )


def _render_shortlist_tab() -> None:
    with st.expander("📊 **Model Methodology** — Click to expand", expanded=False):
        st.markdown("""
        **Bayesian Shrinkage Estimator** trained on n=33 paired seasons:
        - Ridge regression did **NOT** beat the shrinkage baseline (LOO-MSE 6.31 vs 3.51)
        - Formula: `reliability = balls / (balls + 30)`
        - Prediction: `S3 estimate = reliability × S2_economy + (1 − reliability) × league_avg (8.2)`
        - Higher confidence = more data = more trustworthy forecast
        """)

    st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)
    df = _load_data()
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
        (k3, "Tier-3 Monitors", len(t3), "#7d8f88", "⚪"),
        (k4, "High Confidence", len(high_conf), "#1a6b51", "✅"),
    ]:
        with col:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                        <div class="metric-card-label">{label}</div>
                        <span style="font-size:20px;">{icon}</span>
                    </div>
                    <div class="metric-card-value" style="color:{color};">{value}</div>
                    <div style="font-size:11px; color:var(--on-surface-variant); margin-top:8px;">
                        {(value / len(df) * 100):.1f}% of pool
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("<div style='height:24px;'></div>", unsafe_allow_html=True)
    st.markdown("### 🎛️ Filter Players")

    f1, f2, f3 = st.columns(3)
    all_tiers = ["TIER-1 PRIORITY", "TIER-2 CONSIDER", "TIER-3 MONITOR"]
    all_confs = sorted(df["confidence_tier"].dropna().unique().tolist()) if "confidence_tier" in df.columns else []
    all_types = sorted([x for x in df["bowling_type"].dropna().unique() if str(x) not in ("nan", "")]) if "bowling_type" in df.columns else []

    with f1:
        tier_filter = st.multiselect(
            "📋 Shortlist Tier",
            all_tiers,
            default=["TIER-1 PRIORITY", "TIER-2 CONSIDER"],
            key="s3_tier_filter",
            help="Filter by recruitment priority tier",
        )
    with f2:
        conf_filter = st.multiselect(
            "📈 Confidence Level",
            all_confs,
            default=[c for c in all_confs if "HIGH" in c or "MEDIUM" in c],
            key="s3_conf_filter",
            help="Filter by prediction confidence (based on balls bowled)",
        )
    with f3:
        type_filter = st.multiselect(
            "🎳 Bowling Type",
            all_types,
            default=all_types,
            key="s3_type_filter",
            help="Filter by bowling style",
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

    st.success(f"✅ **{len(filtered)} players** match filters ({(len(filtered) / len(df) * 100):.1f}% of total pool)")
    st.markdown("<div style='height:20px;'></div>", unsafe_allow_html=True)

    scatter_df = filtered.dropna(subset=["sos_economy", "pred_s3_final"]).copy()
    if not scatter_df.empty:
        st.markdown("### 📊 S2 Economy vs S3 Forecast")
        st.caption("💡 Bubble size = balls bowled in S2. Better players sit bottom-left with lower economy forecasts.")
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
        min_val = min(scatter_df["sos_economy"].min(), scatter_df["pred_s3_final"].min()) - 0.3
        max_val = max(scatter_df["sos_economy"].max(), scatter_df["pred_s3_final"].max()) + 0.3
        fig.add_trace(
            go.Scatter(
                x=[min_val, max_val],
                y=[min_val, max_val],
                mode="lines",
                line=dict(dash="dot", color="#999", width=1),
                name="No change (S2=S3)",
                showlegend=True,
            )
        )
        fig.update_layout(
            height=420,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            legend_title_text="Tier",
            xaxis=dict(gridcolor="rgba(0,0,0,0.06)"),
            yaxis=dict(gridcolor="rgba(0,0,0,0.06)"),
        )
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    else:
        st.info("No scatter data for current filters.")

    st.markdown("#### Full Shortlist Rankings")
    display_cols = [
        "rank",
        "player_name",
        "shortlist_score",
        "shortlist_tier",
        "sos_economy",
        "dot_ball_pct",
        "death_econ_raw",
        "pred_s3_final",
        "confidence_tier",
        "age",
        "bowling_type",
    ]
    display_cols = [column for column in display_cols if column in filtered.columns]
    table = filtered[display_cols].sort_values("rank").reset_index(drop=True)
    table = table.rename(
        columns={
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
    )
    st.dataframe(table, width="stretch", hide_index=True)

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
            (pc2, "S2 SOS Economy", f"{row.get('sos_economy', '—'):.2f}" if pd.notna(row.get("sos_economy")) else "—"),
            (pc3, "Shortlist Score", f"{row.get('shortlist_score', '—'):.3f}" if pd.notna(row.get("shortlist_score")) else "—"),
            (pc4, "Confidence Tier", str(row.get("confidence_tier", "—"))),
        ]:
            with col:
                st.markdown(
                    f"""
                    <div class="metric-card">
                        <div class="metric-card-label">{label}</div>
                        <div class="metric-card-value">{val}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        if pd.notna(row.get("model_rationale")):
            st.caption(f"Model note: {row['model_rationale']}")


def render_s3_recruiting() -> None:
    render_page_header(
        title="Season 3 Selection Intelligence",
        subtitle="Rank players by raw recent form, quality-adjusted form, and role fit; then use the bowler recruiting shortlist for external reinforcement.",
        insight_label="Decision Lens",
        insight_text="Select the XI from weighted form first, then use S1 vs S2 deltas to decide which roles need protection, replacement, or recruiting support.",
        alert_icon="🎯",
    )

    form_tab, recruiting_tab = st.tabs(["Player Form Ranking", "Bowler Recruiting Shortlist"])
    with form_tab:
        _render_form_ranking_tab()
    with recruiting_tab:
        _render_shortlist_tab()

    with st.expander("📊 **Model Methodology** — Click to expand", expanded=False):
        st.markdown("""
        **Bayesian Shrinkage Estimator** trained on n=33 paired seasons:
        - Ridge regression did **NOT** beat the shrinkage baseline (LOO-MSE 6.31 vs 3.51)
        - Formula: `reliability = balls / (balls + 30)`
        - Prediction: `S3 estimate = reliability × S2_economy + (1 − reliability) × league_avg (8.2)`
        - Higher confidence = more data = more trustworthy forecast
        """)

    st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)
    df = _load_data()
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
        st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})
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

    st.dataframe(table, width='stretch', hide_index=True)

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
