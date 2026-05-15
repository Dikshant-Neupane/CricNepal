"""
Phase analysis card component — renders the Batting/Bowling phase grids.
"""
import streamlit as st
import textwrap


def _render_single_phase(phase: dict) -> str:
    """Build HTML for one phase sub-card (Powerplay/Middle/Death)."""
    highlight = phase.get("highlight")
    card_class = "phase-card"
    title_class = "phase-title"

    if highlight == "secondary":
        card_class += " highlight-secondary"
        title_class += " secondary"
    elif highlight == "error":
        card_class += " highlight-error"
        title_class += " error"

    stats_html = ""
    for s in phase["stats"]:
        val_class = f"phase-stat-value {s['style']}"
        stats_html += f"""
        <div>
            <p class="phase-stat-label">{s['label']}</p>
            <p class="{val_class}">{s['value']}</p>
        </div>
        """

    return textwrap.dedent(f"""
    <div class="{card_class}">
        <h4 class="{title_class}">{phase['name']}</h4>
        <div class="phase-stat-grid">
            {stats_html}
        </div>
    </div>
    """)


def render_phase_section(title: str, icon: str, phases: list[dict]) -> None:
    """
    Render a full phase analysis panel (header bar + 3 phase sub-cards).

    Args:
        title: Section title (e.g. "Batting Phase Analysis")
        icon: Emoji icon for the header bar
        phases: List of phase dicts from demo_data
    """
    # Header bar
    header_html = f"""
    <div class="section-header-bar">
        <h3>{title}</h3>
        <span class="icon">{icon}</span>
    </div>
    """

    # Phase grid
    phase_cards = "".join(_render_single_phase(p) for p in phases)
    grid_html = f'<div class="phase-grid">{phase_cards}</div>'

    # Wrap in card
    st.markdown(textwrap.dedent(f"""
    <div class="card" style="margin-bottom: 0;">
        {header_html}
        {grid_html}
    </div>
    """), unsafe_allow_html=True)
