import streamlit as st
from src.dashboard.demo_data import get_bowling_phases, get_bowling_vs_batter_hand, get_bowling_tactical_directives

def render_bowling_intelligence():
    st.markdown("""
    <div style="margin-bottom: 48px;">
        <h2 class="page-title">Bowling Intelligence</h2>
        <p class="page-subtitle">Tournament Phase & Tactical Deployment Analysis</p>
    </div>
    """, unsafe_allow_html=True)

    # Bowling Phase Breakdown
    st.markdown("""
    <div class="card" style="margin-bottom: 32px;">
        <div class="card-header">
            <h3>Bowling Phase Breakdown</h3>
        </div>
        <div class="card-body" style="padding: 24px;">
    """, unsafe_allow_html=True)
    
    phases = [
        {"name": "POWERPLAY (1-6)", "econ": "7.8", "wkts": "12", "dot": "45%", "pressure": "High", "pressure_c": "var(--secondary)"},
        {"name": "MIDDLE (7-15)", "econ": "6.5", "wkts": "24", "dot": "32%", "pressure": "Optimal", "pressure_c": "var(--primary)"},
        {"name": "DEATH (16-20)", "econ": "11.2", "econ_c": "var(--error)", "wkts": "8", "dot": "21%", "pressure": "Critical", "pressure_c": "var(--error)"}
    ]
    
    cols = st.columns(3)
    for i, col in enumerate(cols):
        with col:
            p = phases[i]
            econ_c = p.get('econ_c', 'var(--on-surface)')
            st.markdown(f"""
            <div style="background: var(--surface-container-low); padding: 16px; border-radius: 8px;">
                <div style="font-size: 12px; font-weight: 600; color: var(--on-surface-variant); margin-bottom: 16px; letter-spacing: 0.02em;">{p['name']}</div>
                <div style="display: flex; justify-content: space-between; margin-bottom: 12px;">
                    <span style="font-size: 14px; color: var(--on-surface-variant);">Economy</span>
                    <span style="font-size: 14px; font-weight: 500; color: {econ_c};">{p['econ']}</span>
                </div>
                <div style="display: flex; justify-content: space-between; margin-bottom: 12px;">
                    <span style="font-size: 14px; color: var(--on-surface-variant);">Wickets</span>
                    <span style="font-size: 14px; font-weight: 500; color: var(--on-surface);">{p['wkts']}</span>
                </div>
                <div style="display: flex; justify-content: space-between; margin-bottom: 12px;">
                    <span style="font-size: 14px; color: var(--on-surface-variant);">Dot %</span>
                    <span style="font-size: 14px; font-weight: 500; color: var(--on-surface);">{p['dot']}</span>
                </div>
                <div style="display: flex; justify-content: space-between; padding-top: 12px; border-top: 1px solid var(--outline-variant);">
                    <span style="font-size: 14px; color: var(--on-surface-variant);">Pressure Index</span>
                    <span style="font-size: 14px; font-weight: 600; color: {p['pressure_c']};">{p['pressure']}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
    st.markdown("</div></div>", unsafe_allow_html=True)

    # Resource Allocation and vs Batter Hand
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("""
        <div class="card" style="height: 100%;">
            <div class="card-header">
                <h3>Resource Allocation Heatmap</h3>
            </div>
            <div class="card-body" style="display: flex; align-items: center; justify-content: center; height: 300px; background: var(--surface-container-low); margin: 24px; border-radius: 8px;">
                <span style="color: var(--on-surface-variant);">Heatmap Visualization (Bowler vs Over)</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
    with col2:
        st.markdown("""
        <div class="card" style="height: 100%;">
            <div class="card-header">
                <h3>vs Batter Hand</h3>
            </div>
            <div class="card-body" style="padding: 24px;">
        """, unsafe_allow_html=True)
        
        hands = get_bowling_vs_batter_hand()
        for h in hands:
            st.markdown(f"""
            <div style="background: var(--surface-container-low); padding: 16px; border-radius: 8px; margin-bottom: 16px;">
                <div style="font-size: 12px; font-weight: 600; color: var(--on-surface-variant); margin-bottom: 12px;">vs {h['hand']}</div>
                <div style="display: flex; justify-content: space-between;">
                    <div>
                        <div style="font-size: 12px; color: var(--on-surface-variant);">Economy</div>
                        <div style="font-size: 14px; font-weight: 500; margin-top: 4px;">{h['economy']}</div>
                    </div>
                    <div style="text-align: right;">
                        <div style="font-size: 12px; color: var(--on-surface-variant);">Strike Rate</div>
                        <div style="font-size: 14px; font-weight: 500; margin-top: 4px;">{h['strike_rate']}</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        st.markdown("</div></div>", unsafe_allow_html=True)

    st.markdown("<div style='height: 32px;'></div>", unsafe_allow_html=True)

    # Tactical Directives
    dirs = get_bowling_tactical_directives()
    st.markdown("""
    <div style="background: var(--primary); padding: 24px; border-radius: 8px;">
        <h3 style="color: var(--on-primary-container); margin: 0 0 24px 0; font-size: 18px; display: flex; align-items: center; gap: 8px;">
            <span style="font-size: 20px;">💡</span> Tactical Directives
        </h3>
    """, unsafe_allow_html=True)
    
    for d in dirs:
        st.markdown(f"""
        <div style="background: rgba(255, 255, 255, 0.1); padding: 16px; border-radius: 8px; margin-bottom: 12px; display: flex; align-items: flex-start; gap: 12px;">
            <span style="color: var(--secondary-container); font-size: 18px;">✔️</span>
            <span style="color: var(--on-primary-container); font-size: 14px;">{d}</span>
        </div>
        """, unsafe_allow_html=True)
        
    st.markdown("</div>", unsafe_allow_html=True)
