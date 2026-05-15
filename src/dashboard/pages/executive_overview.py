"""
Executive Overview — One Dashboard (Master Command Center)
Matches the professional HTML mockup design exactly.
"""
import streamlit as st


def render_executive_overview():
    """Render the Executive Overview page matching the HTML mockup."""
    
    # Page Header
    st.markdown("""
    <div class="page-header">
        <h1 class="page-title">One Dashboard</h1>
        <p class="page-subtitle">Master Command Center.</p>
        <div class="insight-alert">
            <span class="insight-alert-icon">⚠️</span>
            <p class="insight-alert-text">
                <span class="insight-label">Insight:</span> Death bowling economy is the primary risk factor for Season 3.
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Top Section: 5 KPI Cards
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.markdown("""
        <div class="metric-card">
            <div class="metric-card-header">
                <h3 class="metric-card-label">Win %</h3>
                <span class="metric-card-icon">🏆</span>
            </div>
            <div class="metric-card-value">62.5%</div>
            <div class="metric-card-delta metric-card-delta-positive">
                <span class="metric-card-delta-icon">↗️</span>
                <span class="metric-card-delta-text">+12%</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="metric-card">
            <div class="metric-card-header">
                <h3 class="metric-card-label">NRR</h3>
                <span class="metric-card-icon">📊</span>
            </div>
            <div class="metric-card-value">+0.847</div>
            <div class="metric-card-delta metric-card-delta-positive">
                <span class="metric-card-delta-icon">↗️</span>
                <span class="metric-card-delta-text">+0.3</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="metric-card">
            <div class="metric-card-header">
                <h3 class="metric-card-label">League Rank</h3>
                <span class="metric-card-icon">📈</span>
            </div>
            <div class="metric-card-value">3<span class="metric-card-value-small">/8</span></div>
            <div class="metric-card-delta metric-card-delta-neutral">
                <span class="metric-card-delta-icon">━</span>
                <span class="metric-card-delta-text">Stable</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown("""
        <div class="metric-card">
            <div class="metric-card-header">
                <h3 class="metric-card-label">Team Form Index</h3>
                <span class="metric-card-icon">🔥</span>
            </div>
            <div class="metric-card-value">82<span class="metric-card-value-small">/100</span></div>
            <div class="metric-card-delta metric-card-delta-positive">
                <span class="metric-badge">Hot</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col5:
        st.markdown("""
        <div class="metric-card">
            <div class="metric-card-header">
                <h3 class="metric-card-label">Tactical Efficiency</h3>
                <span class="metric-card-icon">🧠</span>
            </div>
            <div class="metric-card-value">91%</div>
            <div class="metric-card-delta metric-card-delta-positive">
                <span class="metric-card-delta-icon">↗️</span>
                <span class="metric-card-delta-text">Optimal</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<div style='height: 48px;'></div>", unsafe_allow_html=True)
    
    # Middle Section: 2/3 left + 1/3 right layout
    col_left, col_right = st.columns([2, 1])
    
    with col_left:
        # Performance Momentum Chart
        st.markdown("""
        <div class="section-card">
            <div class="section-card-header">
                <h3 class="section-card-title">Performance Momentum</h3>
            </div>
            <div class="section-card-body">
                <div class="chart-placeholder">
                    <span class="chart-placeholder-icon">📊</span>
                    <p class="chart-placeholder-text">Win/Loss Timeline & Phase Efficiency Chart rendering...</p>
                </div>
                <div class="insight-box">
                    <strong>Insight:</strong> Middle overs (7-15) efficiency has driven 80% of our recent victories.
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)
        
        # Intelligence Split: Batting & Bowling
        col_bat, col_bowl = st.columns(2)
        
        with col_bat:
            st.markdown("""
            <div class="section-card">
                <div class="section-card-header">
                    <h3 class="section-card-title">Batting Intelligence</h3>
                </div>
                <div class="section-card-body">
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th>Player</th>
                                <th class="text-right">Runs</th>
                                <th class="text-right">SR</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td>A. Sharma</td>
                                <td class="text-right">342</td>
                                <td class="text-right">145.2</td>
                            </tr>
                            <tr>
                                <td>K. Malla</td>
                                <td class="text-right">289</td>
                                <td class="text-right">132.8</td>
                            </tr>
                            <tr>
                                <td>D. Singh</td>
                                <td class="text-right">156</td>
                                <td class="text-right">168.5</td>
                            </tr>
                        </tbody>
                    </table>
                    <div style="margin-top: auto; padding: 12px; background-color: rgba(225, 227, 228, 0.3); border-radius: 8px; border: 1px solid rgba(193, 200, 194, 0.2); text-align: center; margin-bottom: 12px;">
                        <span style="font-size: 12px; font-weight: 500; color: #414844;">SR vs Bowling Type Heatmap Placeholder</span>
                    </div>
                    <div class="insight-box">
                        <strong>Insight:</strong> Top order struggles against left-arm pace in powerplay.
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        with col_bowl:
            st.markdown("""
            <div class="section-card">
                <div class="section-card-header">
                    <h3 class="section-card-title">Bowling Intelligence</h3>
                </div>
                <div class="section-card-body">
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th>Player</th>
                                <th class="text-right">Wickets</th>
                                <th class="text-right">Econ</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td>S. Kami</td>
                                <td class="text-right">14</td>
                                <td class="text-right">7.2</td>
                            </tr>
                            <tr>
                                <td>L. Rajbanshi</td>
                                <td class="text-right">11</td>
                                <td class="text-right">6.8</td>
                            </tr>
                            <tr>
                                <td>G. Jha</td>
                                <td class="text-right">9</td>
                                <td class="text-right text-error">9.5</td>
                            </tr>
                        </tbody>
                    </table>
                    <div style="display: flex; gap: 12px; margin-top: auto; margin-bottom: 12px;">
                        <div class="phase-box" style="flex: 1;">
                            <div class="phase-box-label">PP Wickets</div>
                            <div class="phase-box-value">18</div>
                        </div>
                        <div class="phase-box" style="flex: 1;">
                            <div class="phase-box-label">Mid Wickets</div>
                            <div class="phase-box-value">24</div>
                        </div>
                        <div class="phase-box phase-box-error" style="flex: 1;">
                            <div class="phase-box-label phase-box-label-error">Death Wickets</div>
                            <div class="phase-box-value phase-box-value-error">8</div>
                        </div>
                    </div>
                    <div class="insight-box">
                        <strong>Insight:</strong> Spinners are controlling the middle overs effectively.
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    with col_right:
        # Tactical Command Card
        st.markdown("""
        <div class="section-card">
            <div class="section-card-header section-card-header-primary">
                <h3 class="section-card-title section-card-title-white">📢 Tactical Command</h3>
            </div>
            <div class="section-card-body" style="gap: 12px;">
                <div class="tactical-box tactical-box-error">
                    <div class="tactical-box-header">
                        <span class="tactical-box-title tactical-box-title-error">Active Warning</span>
                        <span class="tactical-box-badge tactical-box-badge-error">High</span>
                    </div>
                    <div class="tactical-box-body">
                        Opponent Left-Arm Spin vs Top Order.
                    </div>
                </div>
                <div class="tactical-box tactical-box-success">
                    <div class="tactical-box-header">
                        <span class="tactical-box-title tactical-box-title-success">Matchup Advantage</span>
                        <span class="tactical-box-badge" style="background-color: rgba(44, 105, 78, 0.1); color: #2c694e;">Moderate</span>
                    </div>
                    <div class="tactical-box-body">
                        Our Pace attack in PP vs Current Openers.
                    </div>
                </div>
                <div style="padding: 12px; background-color: rgba(225, 227, 228, 0.2); border-radius: 8px; margin-top: auto;">
                    <div style="font-size: 12px; font-weight: 500; color: #414844; margin-bottom: 8px;">
                        <strong>Insight:</strong> Prioritize pace in PP; shield top order from off-spin early.
                    </div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)
        
        # Opposition Snap Card
        st.markdown("""
        <div class="section-card">
            <div class="section-card-header">
                <h3 class="section-card-title">🛡️ Opposition Snap</h3>
            </div>
            <div class="section-card-body">
                <div style="font-size: 16px; font-weight: 600; margin-bottom: 12px;">Next Match</div>
                <div style="font-size: 20px; font-weight: 600; color: #1b4332; margin-bottom: 4px;">Kathmandu Kings</div>
                <div style="font-size: 14px; color: #414844; margin-bottom: 16px;">May 18, 2026 • TU Cricket Ground</div>
                
                <div style="font-size: 14px; font-weight: 500; color: #414844; margin-bottom: 8px;">THREAT LEVELS</div>
                <div style="margin-bottom: 8px;">
                    <div style="font-size: 12px; color: #414844; margin-bottom: 4px;">Batting Depth</div>
                    <div style="height: 8px; background-color: #f3f4f5; border-radius: 4px; overflow: hidden;">
                        <div style="height: 100%; width: 85%; background-color: #ba1a1a;"></div>
                    </div>
                </div>
                <div style="margin-bottom: 8px;">
                    <div style="font-size: 12px; color: #414844; margin-bottom: 4px;">Pace Attack</div>
                    <div style="height: 8px; background-color: #f3f4f5; border-radius: 4px; overflow: hidden;">
                        <div style="height: 100%; width: 70%; background-color: #2c694e;"></div>
                    </div>
                </div>
                <div style="margin-bottom: 16px;">
                    <div style="font-size: 12px; color: #414844; margin-bottom: 4px;">Spin Attack</div>
                    <div style="height: 8px; background-color: #f3f4f5; border-radius: 4px; overflow: hidden;">
                        <div style="height: 100%; width: 45%; background-color: #717973;"></div>
                    </div>
                </div>
                
                <div style="font-size: 14px; font-weight: 500; color: #414844; margin-bottom: 8px;">Key Threat</div>
                <div style="font-size: 16px; font-weight: 600; color: #ba1a1a;">S. Lamichhane <span style="font-size: 12px; color: #414844; font-weight: 400;">(Spin)</span></div>
                
                <div class="insight-box" style="margin-top: 16px;">
                    <strong>Insight:</strong> Focus on aggressive start before their key spinner arrives.
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
