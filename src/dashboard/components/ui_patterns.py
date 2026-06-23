"""
Shared UI patterns and layout components for dashboard consistency.
Centralizes card, spacing, insight box, and section header patterns.
"""
import streamlit as st
from typing import Optional, List, Dict


def render_card_header(title: str, subtitle: Optional[str] = None) -> None:
    """
    Render a card with just the header and optional subtitle.
    
    Args:
        title: Card title
        subtitle: Optional subtitle text
    """
    subtitle_html = f"<p class='card-subtitle'>{subtitle}</p>" if subtitle else ""
    
    st.markdown(f"""
    <div class="card">
        <div class="card-header">
            <h3>{title}</h3>
            {subtitle_html}
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_card_start(title: str, subtitle: Optional[str] = None) -> None:
    """
    Render opening tags for a card with header.
    Must be followed by content and then render_card_end().
    
    Args:
        title: Card title
        subtitle: Optional subtitle text
    """
    subtitle_html = f"<p class='card-subtitle'>{subtitle}</p>" if subtitle else ""
    
    st.markdown(f"""
    <div class="card">
        <div class="card-header">
            <h3>{title}</h3>
            {subtitle_html}
        </div>
        <div class="card-body">
    """, unsafe_allow_html=True)


def render_card_end() -> None:
    """Close card body and card div. Pair with render_card_start()."""
    st.markdown("</div></div>", unsafe_allow_html=True)


def render_spacer(height_px: int = 32) -> None:
    """
    Render vertical spacing div.
    
    Args:
        height_px: Height in pixels (default 32)
    """
    st.markdown(f"<div style='height: {height_px}px;'></div>", unsafe_allow_html=True)


def render_insight_box(
    label: str,
    text: str,
    box_type: str = "neutral"
) -> None:
    """
    Render an insight/alert box with label and text.
    
    Args:
        label: Bold label text (e.g., "Insight:", "Risk:", "Action:")
        text: Main message text
        box_type: "neutral", "success", "warning", "error" for color styling
    """
    box_class = f"insight-box-{box_type}" if box_type != "neutral" else "insight-box"
    
    st.markdown(f"""
    <div class="{box_class}">
        <strong>{label}</strong> {text}
    </div>
    """, unsafe_allow_html=True)


def render_insight_card(title: str, insights: list[dict]) -> None:
    """Render a titled card with colored insight rows.

    Each insight dict needs: label (str), text (str), type (str).
    Type maps to a border color: success=green, warning=amber, error=red, neutral=grey.
    """
    border_colors = {
        "success": "#057a55",
        "warning": "#f59e0b",
        "error":   "#b42318",
        "info":    "#3b82f6",
    }
    bg_colors = {
        "success": "rgba(5,122,85,0.07)",
        "warning": "rgba(245,158,11,0.07)",
        "error":   "rgba(180,35,24,0.07)",
        "info":    "rgba(59,130,246,0.07)",
    }

    rows_html = ""
    for item in insights:
        label    = item.get("label", "")
        text     = item.get("text", "")
        t        = item.get("type", "neutral")
        border   = border_colors.get(t, "#7d8f88")
        bg       = bg_colors.get(t, "rgba(0,0,0,0.03)")
        rows_html += (
            f'<div style="background:{bg};border-left:3px solid {border};'
            f'border-radius:6px;padding:9px 12px;margin-bottom:8px;'
            f'font-size:13px;color:#17231f;line-height:1.5;">'
            f'<strong>{label}:</strong> {text}</div>'
        )

    st.markdown(
        f'<div style="background:#fff;border:1px solid #cad4cf;border-radius:12px;'
        f'overflow:hidden;box-shadow:0 2px 8px rgba(12,36,28,0.05);margin-bottom:12px;">'
        f'<div style="padding:12px 16px;border-bottom:1px solid #cad4cf;'
        f'background:linear-gradient(180deg,#fff,#f8fbf9);">'
        f'<span style="font-size:15px;font-weight:700;color:#17231f;">{title}</span></div>'
        f'<div style="padding:14px 16px;">{rows_html}</div></div>',
        unsafe_allow_html=True,
    )


def render_section_header(
    title: str,
    subtitle: str,
    icon: Optional[str] = None
) -> None:
    """
    Render a section header with title, subtitle, and optional icon.
    
    Args:
        title: Section title
        subtitle: Descriptive subtitle
        icon: Optional emoji icon (e.g., "", "")
    """
    icon_html = f"{icon} " if icon else ""
    
    st.markdown(f"### {icon_html}{title}")
    st.markdown(f"**{subtitle}**")


def render_page_header(
    title: str,
    subtitle: str,
    insight_label: str,
    insight_text: str,
    alert_icon: str = ""
) -> None:
    """
    Render a full page header with title, subtitle, and insight alert box.
    
    Args:
        title: Page title
        subtitle: Page subtitle
        insight_label: Alert box label (e.g., "Core finding", "Decision Lens")
        insight_text: Alert box message
        alert_icon: Icon for alert box (default "")
    """
    st.markdown(f"""
    <div class="jb-page-head">
        <h2 class="page-title">{title}</h2>
        <p class="page-subtitle">{subtitle}</p>
        <div class="insight-alert">
            <span class="insight-alert-icon">{alert_icon}</span>
            <p class="insight-alert-text">
                <span class="insight-label">{insight_label}:</span> {insight_text}
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_table_card(
    title: str,
    headers: List[str],
    rows: List[List[str]],
    column_classes: Optional[List[str]] = None
) -> None:
    """
    Render a card containing a styled data table.
    
    Args:
        title: Card title
        headers: List of column header names
        rows: List of row data (each row is a list of cell values)
        column_classes: Optional list of CSS classes for columns (e.g., ["right", "right"])
    """
    if column_classes is None:
        column_classes = [""] * len(headers)
    
    # Build header row
    header_html = "<tr>"
    for header, col_class in zip(headers, column_classes):
        header_html += f'<th class="{col_class}">{header}</th>'
    header_html += "</tr>"
    
    # Build body rows
    body_html = ""
    for row in rows:
        body_html += "<tr>"
        for cell, col_class in zip(row, column_classes):
            body_html += f'<td class="{col_class}">{cell}</td>'
        body_html += "</tr>"
    
    st.markdown(f"""
    <div class="card">
        <div class="card-header">
            <h3>{title}</h3>
        </div>
        <table class="bolts-table">
            <thead>{header_html}</thead>
            <tbody>{body_html}</tbody>
        </table>
    </div>
    """, unsafe_allow_html=True)
