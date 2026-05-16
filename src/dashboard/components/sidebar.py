"""
Sidebar navigation component for Janakpur Bolts dashboard.
Renders the branded sidebar matching the HTML mockup.
"""
import streamlit as st
from src.dashboard.demo_data import NAV_ITEMS, NAV_BOTTOM


def render_sidebar() -> str:
    """
    Render the sidebar navigation and return the selected page key.
    Uses st.session_state to persist selection.
    """
    if "active_page" not in st.session_state:
        st.session_state.active_page = "executive_overview"

    with st.sidebar:
        # Brand header
        st.markdown("""
        <div class="sidebar-brand">
            <h1>Janakpur Bolts</h1>
            <p>Elite Performance Unit</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("#### Analysis")

        # Main navigation
        for item in NAV_ITEMS:
            is_active = st.session_state.active_page == item["key"]

            # Use a button styled as a nav item
            if st.button(
                f"{item['icon']}  {item['label']}",
                key=f"nav_{item['key']}",
                use_container_width=True,
                type="primary" if is_active else "secondary",
            ):
                st.session_state.active_page = item["key"]
                st.rerun()

        st.markdown("---")
        st.markdown("#### Workspace")

        # Bottom items (Settings, Support)
        for item in NAV_BOTTOM:
            if st.button(
                f"{item['icon']}  {item['label']}",
                key=f"nav_{item['key']}",
                use_container_width=True,
                type="secondary",
            ):
                st.session_state.active_page = item["key"]
                st.rerun()

        st.markdown("---")
        st.caption("Model focus: S1 win drivers, S2 loss drivers, S3 tactical plan")

    return st.session_state.active_page
