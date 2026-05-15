"""
Reusable metric card component — renders a KPI card matching the HTML mockup style.
"""
import streamlit as st


def render_metric_card(
    title: str,
    value: str,
    delta: str,
    description: str,
    icon: str = "",
    delta_type: str = "positive",
) -> None:
    """
    Render a single metric card.

    Args:
        title: Card header label (e.g. "Toss Impact")
        value: Large display value (e.g. "68%")
        delta: Delta text (e.g. "+12% vs Lg")
        description: Footer description
        icon: Emoji icon for top-right
        delta_type: "positive", "negative", or "neutral" for color
    """
    delta_class = delta_type  # maps to CSS .metric-delta.positive etc.

    st.markdown(f"""
    <div class="metric-card-bolts">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 16px;">
            <p class="metric-label">{title}</p>
            <span style="font-size: 22px;">{icon}</span>
        </div>
        <div style="display: flex; align-items: baseline;">
            <span class="metric-value">{value}</span>
            <span class="metric-delta {delta_class}">{delta}</span>
        </div>
        <p class="metric-desc">{description}</p>
    </div>
    """, unsafe_allow_html=True)


def render_metric_row(metrics: list[dict]) -> None:
    """Render a row of metric cards (typically 3)."""
    cols = st.columns(len(metrics))
    for col, m in zip(cols, metrics):
        with col:
            render_metric_card(
                title=m["title"],
                value=m["value"],
                delta=m["delta"],
                description=m["description"],
                icon=m.get("icon", ""),
                delta_type=m.get("delta_type", "positive"),
            )
