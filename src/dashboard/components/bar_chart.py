"""
Horizontal bar chart & resource heatmap components.
"""
import streamlit as st
from src.dashboard.theme import COLORS


def render_order_contribution(data: list[dict]) -> None:
    """
    Render the batting order contribution horizontal bar chart.

    Args:
        data: List of dicts with keys: label, value (int %), color (CSS class)
    """
    bars_html = ""
    for item in data:
        bars_html += f"""
        <div class="bar-row">
            <span class="bar-label">{item['label']}</span>
            <div class="bar-track">
                <div class="bar-fill {item['color']}" style="width: {item['value']}%;"></div>
            </div>
            <span class="bar-value">{item['value']}%</span>
        </div>
        """

    st.markdown(f"""
    <div class="card">
        <div class="card-header">
            <h3>Order Contribution (%)</h3>
        </div>
        <div class="card-body">
            {bars_html}
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_resource_heatmap(bowlers: list[dict]) -> None:
    """
    Render the bowling resource allocation heatmap.

    Args:
        bowlers: List of dicts with name, color_base, and overs (20 floats 0.0-1.0)
    """
    color_map = {
        "primary": COLORS["primary"],
        "secondary": COLORS["secondary"],
    }
    bg_empty = COLORS["surface_container"]

    # Axis labels
    axis_html = '<div style="display: flex; margin-left: 52px; margin-bottom: 4px;">'
    for i in [1, 5, 10, 15, 20]:
        axis_html += f'<div style="flex:1; text-align:center; font-size:10px; color: {COLORS["outline_variant"]};">{i}</div>'
    axis_html += '</div>'

    rows_html = ""
    for bowler in bowlers:
        base_color = color_map.get(bowler["color_base"], COLORS["primary"])
        cells = ""
        for intensity in bowler["overs"]:
            if intensity == 0:
                bg = bg_empty
            else:
                # Apply opacity via rgba
                r = int(base_color[1:3], 16)
                g = int(base_color[3:5], 16)
                b = int(base_color[5:7], 16)
                bg = f"rgba({r},{g},{b},{intensity})"
            cells += f'<div class="heatmap-cell" style="background:{bg};"></div>'

        rows_html += f"""
        <div class="heatmap-row">
            <span class="heatmap-label">{bowler['name']}</span>
            <div class="heatmap-cells">{cells}</div>
        </div>
        """

    st.markdown(f"""
    <div class="card">
        <div class="card-header">
            <h3>Resource Heatmap (Overs 1-20)</h3>
        </div>
        <div class="card-body">
            {axis_html}
            {rows_html}
        </div>
    </div>
    """, unsafe_allow_html=True)
