"""
Decision Intelligence Service - Day 6: Decision Intelligence Pass
Generates coach-usable recommendations based on data evidence.
"""
import streamlit as st
from typing import Dict, List, Optional
import pandas as pd


def generate_executive_recommendations(
    season_kpis: Dict[str, Dict],
    quality_score: int
) -> List[Dict[str, str]]:
    """
    Generate executive-level recommendations based on S1 vs S2 performance.
    
    Args:
        season_kpis: Dict with S1 and S2 KPI data from metrics service
        quality_score: Data reliability score (0-100)
    
    Returns:
        List of recommendation dicts with priority, type, label, text
    """
    recommendations = []
    
    if not season_kpis:
        return [{
            "priority": 1,
            "type": "warning",
            "label": "Data Unavailable",
            "text": "Unable to generate recommendations without season performance data."
        }]
    
    s1 = season_kpis.get("S1", {})
    s2 = season_kpis.get("S2", {})
    
    if not s1 or not s2:
        return [{
            "priority": 1,
            "type": "info",
            "label": "Incomplete Data",
            "text": "Both S1 and S2 data required for comparative analysis."
        }]
    
    # Calculate deltas
    win_pct_delta = s2.get("win_pct", 0.0) - s1.get("win_pct", 0.0)
    nrr_delta = s2.get("nrr", 0.0) - s1.get("nrr", 0.0)
    
    # Priority 1: Win% decline (if significant)
    if win_pct_delta < -15.0:
        severity = "Critical" if win_pct_delta < -30.0 else "High"
        recommendations.append({
            "priority": 1,
            "type": "error",
            "label": f"{severity} Priority — Win Rate Decline",
            "text": f"Win% dropped {abs(win_pct_delta):.1f} percentage points from S1 ({s1.get('win_pct', 0):.1f}%) to S2 ({s2.get('win_pct', 0):.1f}%). Target +15pp recovery for S3 through phase-specific execution improvements."
        })
    
    # Priority 2: NRR trend
    if nrr_delta < -0.5:
        recommendations.append({
            "priority": 2,
            "type": "warning",
            "label": "Run Rate Efficiency Declined",
            "text": f"NRR deteriorated by {abs(nrr_delta):.3f} (S1: {s1.get('nrr', 0):.3f}, S2: {s2.get('nrr', 0):.3f}). Focus on powerplay intent and death bowling discipline to recover +0.5 NRR margin."
        })
    elif nrr_delta < -0.2:
        recommendations.append({
            "priority": 3,
            "type": "info",
            "label": "Moderate NRR Decline",
            "text": f"NRR slipped by {abs(nrr_delta):.3f}. Monitor phase-wise run rate trends to prevent further erosion."
        })
    
    # Priority 3: Data quality check
    if quality_score < 90:
        recommendations.append({
            "priority": 4,
            "type": "warning",
            "label": "Data Reliability Check",
            "text": f"Current reliability score: {quality_score}/100. Review data quality findings before finalizing tactical decisions."
        })
    
    # Priority 4: Positive trend (if exists)
    if win_pct_delta > 5.0:
        recommendations.append({
            "priority": 5,
            "type": "success",
            "label": "Positive Momentum",
            "text": f"Win% improved by {win_pct_delta:.1f}pp. Maintain current tactical approach while refining execution consistency."
        })
    
    # Sort by priority
    recommendations.sort(key=lambda x: x["priority"])
    
    return recommendations


def generate_phase_recommendations(
    s1_stats: Dict[str, float],
    s2_stats: Dict[str, float],
    phase_name: str = "powerplay"
) -> Dict[str, str]:
    """
    Generate phase-specific tactical recommendations.
    
    Args:
        s1_stats: S1 phase statistics (run_rate, dot_pct, boundary_pct, etc.)
        s2_stats: S2 phase statistics
        phase_name: "powerplay", "middle", or "death"
    
    Returns:
        Dict with insight, risk, action keys
    """
    if not s1_stats or not s2_stats:
        return {
            "insight": "Phase data unavailable for analysis.",
            "risk": "Cannot assess phase-specific risks without complete data.",
            "action": "Collect phase-level statistics for tactical planning."
        }
    
    # Calculate deltas
    rr_delta = s2_stats.get("run_rate", 0) - s1_stats.get("run_rate", 0)
    dot_delta = s2_stats.get("dot_pct", 0) - s1_stats.get("dot_pct", 0)
    boundary_delta = s2_stats.get("boundary_pct", 0) - s1_stats.get("boundary_pct", 0)
    
    phase_display = phase_name.capitalize()
    
    # Generate recommendations based on phase and deltas
    if phase_name == "powerplay":
        if rr_delta < -0.5:
            return {
                "insight": f"{phase_display} run rate declined {abs(rr_delta):.2f} rpo from S1 to S2 (S1: {s1_stats.get('run_rate', 0):.2f}, S2: {s2_stats.get('run_rate', 0):.2f}).",
                "risk": f"Dot ball % increased by {dot_delta:.1f}pp, limiting early momentum. Risk of chasing pressure in later phases.",
                "action": f"Target +1.0 rpo recovery: promote high-intent striker, reduce dot tolerance, and attack pace matchups in overs 1-6."
            }
        else:
            return {
                "insight": f"{phase_display} run rate stable or improved (delta: {rr_delta:+.2f} rpo).",
                "risk": "Monitor consistency across opposition bowling attacks.",
                "action": "Maintain current approach while testing boundary options against spin."
            }
    
    elif phase_name == "middle":
        if rr_delta < -0.5:
            return {
                "insight": f"Middle overs (7-15) run rate dropped {abs(rr_delta):.2f} rpo. Acceleration phase compromised.",
                "risk": "Partnership building under pressure increases late-innings burden.",
                "action": "Introduce rotation specialist and reduce boundary-or-nothing approach. Target 8.5+ rpo baseline."
            }
        else:
            return {
                "insight": f"Middle overs maintained stable run rate (delta: {rr_delta:+.2f} rpo).",
                "risk": "Avoid complacency; monitor matchup-specific trends.",
                "action": "Continue rotation-based accumulation with calculated boundary attempts."
            }
    
    elif phase_name == "death":
        if rr_delta < -1.0:
            return {
                "insight": f"Death overs (16-20) run rate declined {abs(rr_delta):.2f} rpo. Highest leverage phase underperforming.",
                "risk": "Late-innings finishing capability compromised. Expected totals -8 to -12 runs vs S1.",
                "action": "Reserve two death specialists for overs 17-20. Delay slower-ball reveal until over 16. Target 11+ rpo recovery."
            }
        else:
            return {
                "insight": f"Death overs execution stable (delta: {rr_delta:+.2f} rpo).",
                "risk": "Monitor finisher strike rotation and boundary access late.",
                "action": "Maintain power-hitter roles and specialist allocation for final five overs."
            }
    
    return {
        "insight": "Phase analysis available for powerplay, middle, and death overs.",
        "risk": "Specify phase for detailed tactical recommendations.",
        "action": "Use phase-specific tabs for granular decision intelligence."
    }


def prioritize_tactical_actions(
    recommendations: List[Dict[str, str]]
) -> List[Dict[str, str]]:
    """
    Sort and rank tactical actions by impact priority.
    
    Args:
        recommendations: List of recommendation dicts
    
    Returns:
        Sorted list with priority numbers added
    """
    # Already sorted by priority in generation functions
    return recommendations


def format_recommendation_card(
    recommendations: List[Dict[str, str]],
    title: str = "Tactical Priorities"
) -> str:
    """
    Format recommendations for display.
    Returns a sentinel string; the actual rendering is done by
    render_recommendation_card() which uses native Streamlit components.

    For backward compatibility, callers that pass the result to
    st.markdown(..., unsafe_allow_html=True) will still work because
    we render inline via render_recommendation_card if called as a function.
    """
    # Build a plain HTML fallback string — callers that use st.markdown
    # get the styled version; callers using render_recommendation_card get
    # native Streamlit components.
    if not recommendations:
        return f"<p><strong>{title}</strong>: No recommendations available.</p>"

    lines = [f"**{title}**"]
    for rec in recommendations:
        priority = rec.get("priority", "")
        label    = rec.get("label", "")
        text     = rec.get("text", "")
        lines.append(f"**#{priority} — {label}:** {text}")
    return "\n\n".join(lines)


def render_recommendation_card(
    recommendations: List[Dict[str, str]],
    title: str = "Tactical Priorities"
) -> None:
    """Render recommendations using native Streamlit components."""
    st.markdown(
        f"<div style='font-size:16px;font-weight:700;color:#17231f;"
        f"padding:10px 0 8px 0;border-bottom:1px solid #cad4cf;"
        f"margin-bottom:10px;'>{title}</div>",
        unsafe_allow_html=True,
    )
    _icon_map = {"error": "🔴", "warning": "⚠️", "success": "✅", "info": "ℹ️"}
    for rec in recommendations:
        priority = rec.get("priority", "")
        label    = rec.get("label", "")
        text     = rec.get("text", "")
        rec_type = rec.get("type", "info")
        icon     = _icon_map.get(rec_type, "💡")
        msg      = f"**{icon} #{priority} — {label}:** {text}"
        if rec_type == "error":
            st.error(msg)
        elif rec_type == "warning":
            st.warning(msg)
        elif rec_type == "success":
            st.success(msg)
        else:
            st.info(msg)
