"""
Janakpur Bolts Analytics Dashboard
Main Streamlit Application
"""
import streamlit as st
from loguru import logger
import sys

# Add parent directory to path for imports
sys.path.insert(0, '/app')

from src.db.connection import test_connection, get_team_count
from src.config.settings import get_settings

# Page configuration
st.set_page_config(
    page_title="Janakpur Bolts Analytics",
    page_icon="🏏",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        color: #1E88E5;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1.5rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .status-success {
        color: #28a745;
        font-weight: bold;
    }
    .status-error {
        color: #dc3545;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

def main():
    """Main application entry point"""
    
    # Header
    st.markdown('<h1 class="main-header">🏏 Janakpur Bolts Analytics</h1>', unsafe_allow_html=True)
    st.markdown("### Nepal Premier League Data Science Platform")
    
    st.divider()
    
    # Sidebar
    with st.sidebar:
        st.image("https://via.placeholder.com/200x100/1E88E5/FFFFFF?text=Janakpur+Bolts", 
                 use_column_width=True)
        st.markdown("---")
        st.markdown("### Navigation")
        page = st.radio(
            "Select Page",
            ["🏠 Home", "📊 Team Stats", "👤 Player Stats", "📈 Match Analysis", "⚙️ Settings"],
            label_visibility="collapsed"
        )
        st.markdown("---")
        st.markdown("### Quick Stats")
        if st.button("🔄 Refresh", use_container_width=True):
            st.rerun()
    
    # Main content based on selected page
    if page == "🏠 Home":
        show_home()
    elif page == "📊 Team Stats":
        show_team_stats()
    elif page == "👤 Player Stats":
        show_player_stats()
    elif page == "📈 Match Analysis":
        show_match_analysis()
    elif page == "⚙️ Settings":
        show_settings()


def show_home():
    """Home page - system status and overview"""
    st.markdown("## System Status")
    
    col1, col2, col3 = st.columns(3)
    
    # Database connection test
    with col1:
        st.markdown("### Database")
        with st.spinner("Testing connection..."):
            db_status = test_connection()
        if db_status:
            st.markdown('<p class="status-success">✅ Connected</p>', unsafe_allow_html=True)
            team_count = get_team_count()
            st.metric("Teams", team_count)
        else:
            st.markdown('<p class="status-error">❌ Disconnected</p>', unsafe_allow_html=True)
            st.error("Check database configuration")
    
    with col2:
        st.markdown("### Data Status")
        st.metric("Matches", 0, help="Total matches in database")
        st.metric("Players", 0, help="Total players registered")
        st.metric("Deliveries", 0, help="Total ball-by-ball records")
    
    with col3:
        st.markdown("### Project Phase")
        st.info("**Current:** Foundation Setup")
        st.warning("⏳ Awaiting data source audit")
        st.caption("Next: ETL Pipeline Development")
    
    st.divider()
    
    # Project information
    st.markdown("## About This Project")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        ### 🎯 Objective
        Comprehensive cricket analytics platform for:
        - **Janakpur Bolts** team analysis
        - **Nepal Premier League** statistics
        - **Prime Minister Cup** tracking
        - Player performance metrics
        - Match outcome predictions
        """)
    
    with col2:
        st.markdown("""
        ### 🛠️ Tech Stack
        - **Database:** PostgreSQL 16
        - **ETL:** Python (Pandas, NumPy)
        - **Dashboard:** Streamlit
        - **Infrastructure:** Docker
        - **Data Sources:** ESPNcricinfo, Cricsheet, Manual
        """)
    
    st.divider()
    
    # Next steps
    st.markdown("## 📋 Next Steps")
    
    steps = [
        ("✅", "Environment Setup", "Docker, PostgreSQL, Project Structure", True),
        ("🟡", "Data Source Audit", "Find match URLs, document data availability", False),
        ("⏳", "ETL Pipeline", "Build scrapers and data ingestion", False),
        ("⏳", "Analytics Layer", "Calculate phase-wise stats and metrics", False),
        ("⏳", "Dashboard Development", "Build interactive visualizations", False),
    ]
    
    for icon, title, description, completed in steps:
        col1, col2 = st.columns([1, 5])
        with col1:
            st.markdown(f"### {icon}")
        with col2:
            st.markdown(f"**{title}**")
            st.caption(description)


def show_team_stats():
    """Team statistics page (placeholder)"""
    st.markdown("## 📊 Team Statistics")
    st.info("This page will display team-level analytics once data is loaded.")
    st.markdown("""
    **Coming Soon:**
    - Win/loss records by season
    - Phase-wise run rates (powerplay, middle, death)
    - Venue performance
    - Opposition matchups
    """)


def show_player_stats():
    """Player statistics page (placeholder)"""
    st.markdown("## 👤 Player Statistics")
    st.info("This page will display individual player analytics once data is loaded.")
    st.markdown("""
    **Coming Soon:**
    - Batting averages and strike rates
    - Bowling economy and wicket rates
    - Phase-wise performance breakdown
    - Player comparisons
    """)


def show_match_analysis():
    """Match analysis page (placeholder)"""
    st.markdown("## 📈 Match Analysis")
    st.info("This page will display ball-by-ball match analysis once data is loaded.")
    st.markdown("""
    **Coming Soon:**
    - Manhattan charts (run progression)
    - Worm charts (run rate comparison)
    - Wagon wheels (shot distribution)
    - Pitch maps (bowling length)
    """)


def show_settings():
    """Settings page"""
    st.markdown("## ⚙️ Settings")
    
    settings = get_settings()
    
    st.markdown("### Database Configuration")
    col1, col2 = st.columns(2)
    with col1:
        st.text_input("Host", value=settings.postgres_host, disabled=True)
        st.text_input("Database", value=settings.postgres_db, disabled=True)
    with col2:
        st.text_input("Port", value=str(settings.postgres_port), disabled=True)
        st.text_input("User", value=settings.postgres_user, disabled=True)
    
    st.markdown("### Application")
    st.text_input("Environment", value=settings.environment, disabled=True)
    st.text_input("Log Level", value=settings.log_level, disabled=True)
    
    st.info("💡 To change settings, update the `.env` file and restart the application.")


if __name__ == "__main__":
    main()
