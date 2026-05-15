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

# Custom CSS for better UI
st.markdown("""
<style>
    /* Main styling */
    .main {
        background-color: #f8f9fa;
    }
    
    /* Headers */
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1a1a1a;
        text-align: center;
        margin-bottom: 0.5rem;
        font-family: 'Helvetica Neue', sans-serif;
    }
    
    .subtitle {
        text-align: center;
        color: #6c757d;
        font-size: 1.1rem;
        margin-bottom: 2rem;
    }
    
    /* Cards */
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        margin: 0.5rem 0;
        border-left: 4px solid #1E88E5;
    }
    
    .info-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 12px;
        color: white;
        margin: 1rem 0;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    
    .welcome-card {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        padding: 2rem;
        border-radius: 12px;
        color: white;
        margin: 1rem 0;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    
    /* Status badges */
    .status-success {
        background: #d4edda;
        color: #155724;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-weight: 600;
        display: inline-block;
    }
    
    .status-error {
        background: #f8d7da;
        color: #721c24;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-weight: 600;
        display: inline-block;
    }
    
    .status-warning {
        background: #fff3cd;
        color: #856404;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-weight: 600;
        display: inline-block;
    }
    
    /* Metrics */
    div[data-testid="stMetricValue"] {
        font-size: 2rem;
        font-weight: 700;
        color: #1E88E5;
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1E88E5 0%, #1565C0 100%);
    }
    
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] {
        color: white;
    }
    
    /* Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 2rem;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.2);
    }
</style>
""", unsafe_allow_html=True)

def main():
    """Main application entry point"""
    
    # Header with better styling
    st.markdown('<h1 class="main-header">🏏 Janakpur Bolts Analytics</h1>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Your complete cricket analytics platform for Nepal Premier League</p>', unsafe_allow_html=True)
    
    st.divider()
    
    # Sidebar
    with st.sidebar:
        st.markdown("### 🏏 Janakpur Bolts")
        st.markdown("---")
        
        st.markdown("#### 📍 Navigation")
        page = st.radio(
            "Go to",
            ["🏠 Home", "📊 Team Stats", "👤 Player Stats", "📈 Match Analysis", "⚙️ Settings"],
            label_visibility="collapsed"
        )
        
        st.markdown("---")
        st.markdown("#### ⚡ Quick Actions")
        
        if st.button("🔄 Refresh Data", use_container_width=True):
            st.rerun()
        
        if st.button("📥 Export Report", use_container_width=True):
            st.info("Coming soon!")
        
        st.markdown("---")
        st.markdown("#### 💡 Tips")
        st.caption("Complete the data source audit to unlock all features")
    
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
    
    # Welcome message
    st.markdown("""
    <div class="welcome-card">
        <h2 style="margin-top: 0;">👋 Welcome to Janakpur Bolts Analytics!</h2>
        <p style="font-size: 1.1rem; margin-bottom: 0;">
            Your complete cricket analytics platform for tracking performance, 
            analyzing matches, and gaining insights from ball-by-ball data.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("### 📊 System Status")
    
    # System status checks
    col1, col2, col3, col4 = st.columns(4)
    
    # Database status
    with col1:
        with st.container():
            db_status = test_connection()
            if db_status:
                st.markdown("### ✅")
                st.markdown("**Database**")
                st.success("Connected")
            else:
                st.markdown("### ❌")
                st.markdown("**Database**")
                st.error("Disconnected")
    
    # Get metrics
    try:
        team_count = get_team_count()
    except Exception:
        team_count = 0
    
    # Teams count
    with col2:
        st.metric(
            label="🏏 Teams",
            value=team_count,
            delta="NPL Teams" if team_count > 0 else None
        )
    
    # Matches count (placeholder)
    with col3:
        st.metric(
            label="🎯 Matches",
            value=0,
            delta="Waiting for data",
            delta_color="off"
        )
    
    # Players count (placeholder)
    with col4:
        st.metric(
            label="👤 Players",
            value=0,
            delta="Waiting for data",
            delta_color="off"
        )
    
    st.divider()
    
    # Next steps card
    st.markdown("""
    <div class="info-card">
        <h3 style="margin-top: 0;">🚀 Getting Started</h3>
        <p style="font-size: 1.05rem;">
            Your analytics platform is ready! Here's what you need to do next:
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Next steps
    col1, col2 = st.columns([3, 2])
    
    with col1:
        st.markdown("#### 📋 Next Steps:")
        
        st.markdown("""
        1. **🔍 Complete Data Source Audit** (2-3 hours)
           - Find 6 Janakpur Bolts match URLs
           - Check data availability (ball-by-ball vs scorecard)
           - Verify scraping permissions (robots.txt)
           - Document in `context/data_source_audit.md`
        
        2. **📥 Data Collection** (After audit)
           - Manual entry via Google Sheets, or
           - Automated scraping (if permitted)
        
        3. **📊 Analytics & Insights**
           - Phase-wise statistics (Powerplay, Middle, Death)
           - Player performance tracking
           - Match trend analysis
        """)
    
    with col2:
        st.markdown("#### 🔗 Quick Links:")
        
        if st.button("📝 Open Audit Template", use_container_width=True, type="primary"):
            st.info("Open `context/data_source_audit.md` in your editor")
        
        if st.button("📚 View Setup Guide", use_container_width=True):
            st.info("Open `SETUP.md` for complete documentation")
        
        if st.button("🔍 Find Match URLs", use_container_width=True):
            st.info("Open `context/how_to_find_matches.md` for guidance")
        
        st.markdown("---")
        
        st.markdown("##### 🌐 External Tools:")
        st.markdown("- [PgAdmin](http://localhost:5050) - Database Manager")
        st.markdown("- [GitHub Repo](https://github.com/Dikshant-Neupane/CricNepal) - Source Code")
    
    st.divider()
    
    # Tips section
    with st.expander("💡 Pro Tips", expanded=False):
        st.markdown("""
        - **Ball-by-ball data** is gold! It enables phase-wise analysis and detailed insights
        - Check **robots.txt** before scraping any website
        - Start with **manual data entry** for 2-3 matches to validate your workflow
        - Use **PgAdmin** (http://localhost:5050) to explore your database structure
        - The database has **15 tables** ready for cricket analytics
        """)
    
    # Project info
    with st.expander("ℹ️ About This Project", expanded=False):
        st.markdown("""
        **Janakpur Bolts Analytics Platform**
        
        A production-ready cricket analytics system built for Nepal Premier League data science.
        
        **Tech Stack:**
        - 🐘 PostgreSQL 16 - Normalized database with 15 tables
        - 🐍 Python 3.11 - Data processing and analytics
        - 📊 Streamlit - Interactive dashboards
        - 🐳 Docker - Containerized environment
        - 🔴 Redis - Caching layer
        
        **Features:**
        - Ball-by-ball data tracking
        - Phase-wise T20 analytics (Powerplay/Middle/Death)
        - Player entity resolution (fuzzy name matching)
        - Scorecard validation system
        - Real-time performance metrics
        
        **Built with ❤️ for cricket analytics**
        """)
    
    st.divider()
    
    # Footer
    st.caption("🏏 Janakpur Bolts Analytics • Nepal Premier League • Powered by Claude & Python")


def show_team_stats():
    """Team statistics page (placeholder)"""
    st.markdown("## 📊 Team Statistics")
    
    st.markdown("""
    <div class="info-card">
        <h3 style="margin-top: 0;">🏏 Team Analytics Coming Soon!</h3>
        <p style="font-size: 1.05rem; margin-bottom: 0;">
            Once you complete the data source audit and load match data, 
            this page will show comprehensive team-level insights.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("### What You'll See Here:")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        #### 📈 Performance Metrics
        - **Win/Loss Records** by season and opponent
        - **Run Rates** across different match phases
        - **Powerplay Success** rate (overs 1-6)
        - **Death Overs Performance** (overs 16-20)
        - **Home vs Away** statistics
        """)
        
    with col2:
        st.markdown("""
        #### 🎯 Advanced Analytics
        - **Venue Analysis** - Best and worst grounds
        - **Opposition Matchups** - H2H records
        - **Batting Order Contribution** - Top/middle/lower order
        - **Bowling Attack Breakdown** - Pace vs spin
        - **Trend Analysis** - Performance over time
        """)
    
    st.divider()
    
    st.markdown("### 📊 Preview: Sample Dashboard")
    
    # Sample metrics (placeholder visualization)
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Matches Played", "-", help="Total matches in database")
    with col2:
        st.metric("Win Rate", "-", help="Overall win percentage")
    with col3:
        st.metric("Avg Score", "-", help="Average total scored")
    
    st.info("💡 Complete the data audit to unlock these analytics!")


def show_player_stats():
    """Player statistics page (placeholder)"""
    st.markdown("## 👤 Player Statistics")
    
    st.markdown("""
    <div class="info-card">
        <h3 style="margin-top: 0;">👨‍🏫 Player Analytics Coming Soon!</h3>
        <p style="font-size: 1.05rem; margin-bottom: 0;">
            Track individual player performance with detailed ball-by-ball insights 
            once match data is loaded into the system.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("### What You'll See Here:")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        #### 🏏 Batting Analytics
        - **Career Stats** - Runs, average, strike rate
        - **Phase-wise Performance** - Powerplay/middle/death
        - **Boundary Analysis** - 4s and 6s distribution
        - **Match-winning Contributions**
        - **vs Pace/Spin** breakdown
        """)
        
    with col2:
        st.markdown("""
        #### ⚾ Bowling Analytics
        - **Wickets & Economy** rate statistics
        - **Powerplay vs Death** overs performance
        - **Dot Ball Percentage**
        - **Key Dismissals** - Top batsmen removed
        - **Yorker Success Rate**
        """)
    
    st.divider()
    
    st.markdown("### 🎯 Player Comparison Tool")
    st.markdown("Compare any two players side-by-side across all metrics")
    
    col1, col2 = st.columns(2)
    with col1:
        st.selectbox("Select Player 1", ["Coming soon..."], disabled=True)
    with col2:
        st.selectbox("Select Player 2", ["Coming soon..."], disabled=True)
    
    st.info("💡 Player data will be available after completing the data audit!")


def show_match_analysis():
    """Match analysis page (placeholder)"""
    st.markdown("## 📈 Match Analysis")
    
    st.markdown("""
    <div class="info-card">
        <h3 style="margin-top: 0;">🔍 Ball-by-Ball Analysis Coming Soon!</h3>
        <p style="font-size: 1.05rem; margin-bottom: 0;">
            Deep-dive into individual matches with interactive visualizations 
            showing every delivery and turning point.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("### What You'll See Here:")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        #### 📊 Match Visualizations
        - **Manhattan Chart** - Run progression over by over
        - **Worm Chart** - Comparing both innings
        - **Wagon Wheel** - Shot distribution map
        - **Pitch Map** - Bowling length & line
        - **Partnership Analysis** - Key stands
        """)
        
    with col2:
        st.markdown("""
        #### 🎯 Key Moments
        - **Turning Points** - Match-winning spells
        - **Boundary Timeline** - When 4s and 6s were hit
        - **Wicket Fall** - Impact on run rate
        - **Strategic Timeouts** - Before/after analysis
        - **Win Probability** - Live prediction tracker
        """)
    
    st.divider()
    
    st.markdown("### 🏏 Match Selector")
    st.selectbox("Select a Match", ["No matches loaded yet"], disabled=True)
    
    st.info("💡 Match analysis will be available once ball-by-ball data is collected!")


def show_settings():
    """Settings page"""
    st.markdown("## ⚙️ Settings & Configuration")
    
    settings = get_settings()
    
    # System info card
    st.markdown("""
    <div class="welcome-card">
        <h3 style="margin-top: 0;">🔧 System Configuration</h3>
        <p style="font-size: 1.05rem; margin-bottom: 0;">
            View your current environment settings and database configuration.
            These are read-only for security.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("### 🗄️ Database Configuration")
    
    col1, col2 = st.columns(2)
    with col1:
        st.text_input("📍 Host", value=settings.postgres_host, disabled=True, 
                     help="Database server hostname")
        st.text_input("🏢 Database Name", value=settings.postgres_db, disabled=True,
                     help="Name of the PostgreSQL database")
    with col2:
        st.text_input("🔌 Port", value=str(settings.postgres_port), disabled=True,
                     help="Database connection port")
        st.text_input("👤 Username", value=settings.postgres_user, disabled=True,
                     help="Database user account")
    
    # Test connection
    if st.button("🔍 Test Database Connection", use_container_width=True):
        with st.spinner("Testing connection..."):
            if test_connection():
                st.success("✅ Database connection successful!")
                try:
                    team_count = get_team_count()
                    st.info(f"Found {team_count} teams in the database")
                except Exception as e:
                    st.warning(f"Connected but query failed: {str(e)}")
            else:
                st.error("❌ Database connection failed")
    
    st.divider()
    
    st.markdown("### 🌍 Application Settings")
    
    col1, col2 = st.columns(2)
    with col1:
        st.text_input("🏷️ Environment", value=settings.environment, disabled=True,
                     help="Current deployment environment")
    with col2:
        st.text_input("📝 Log Level", value=settings.log_level, disabled=True,
                     help="Application logging verbosity")
    
    st.divider()
    
    st.markdown("### 🔐 Security & Maintenance")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        #### ✏️ Editing Configuration
        To modify settings:
        1. Open the `.env` file in your project root
        2. Update the desired values
        3. Restart Docker containers:
           ```bash
           docker compose restart
           ```
        """)
    
    with col2:
        st.markdown("""
        #### 🔒 Security Best Practices
        - Never commit `.env` to version control
        - Use strong passwords in production
        - Change default credentials before deployment
        - Regularly update dependencies
        """)
    
    st.divider()
    
    # System info
    with st.expander("ℹ️ System Information", expanded=False):
        st.markdown("""
        **Docker Services:**
        - PostgreSQL 16-alpine (Port 5432)
        - Redis 7-alpine (Port 6379)
        - PgAdmin 4 (Port 5050)
        - Streamlit App (Port 8501)
        
        **Volumes:**
        - `postgres_data` - Database persistence
        - `redis_data` - Cache persistence
        
        **External Links:**
        - [PgAdmin Dashboard](http://localhost:5050)
        - [GitHub Repository](https://github.com/Dikshant-Neupane/CricNepal)
        """)


if __name__ == "__main__":
    main()
