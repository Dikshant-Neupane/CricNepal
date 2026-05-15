import streamlit as st
from src.dashboard.demo_data import get_opposition_bowling_plans

def render_opposition_report():
    st.markdown("""
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 32px;">
        <div>
            <h2 class="page-title">Tactical Blueprint</h2>
            <p class="page-subtitle">Configure parameters to generate opposition intelligence report.</p>
        </div>
        <div style="display: flex; gap: 16px;">
            <button class="stButton" style="border: 1px solid var(--outline-variant); background: white; padding: 8px 16px; border-radius: 8px; font-weight: 600; display: flex; align-items: center; gap: 8px;">
                <span style="opacity: 0.7;">📝</span> Analyst Notes
            </button>
            <button class="stButton" style="background: var(--primary); color: white; border: none; padding: 8px 16px; border-radius: 8px; font-weight: 600; display: flex; align-items: center; gap: 8px;">
                <span>📊</span> Export PDF
            </button>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Top Configuration Row
    st.markdown("""
    <div class="card" style="margin-bottom: 32px;">
        <div class="card-body" style="padding: 24px;">
    """, unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
    with col1:
        st.selectbox("Opponent", ["Kathmandu Gurkhas", "Lalitpur Patriots", "Pokhara Rhinos"])
    with col2:
        st.selectbox("Venue", ["TU Cricket Ground", "Mulpani Cricket Ground"])
    with col3:
        st.selectbox("Data Range", ["Last 10 Matches", "All Time", "2024 Season"])
    with col4:
        st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
        st.button("Generate Report", type="primary", use_container_width=True)

    st.markdown("</div></div>", unsafe_allow_html=True)

    col_left, col_right = st.columns([2, 1])
    
    with col_left:
        # Key Threats
        st.markdown("""
        <div class="card" style="height: 100%;">
            <div class="card-header">
                <h3 style="display: flex; align-items: center; gap: 8px;">
                    <span style="color: var(--error);">⚠️</span> Key Threats
                </h3>
            </div>
            <div class="card-body" style="display: flex; gap: 24px; padding: 24px;">
        """, unsafe_allow_html=True)
        
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("""
            <div style="background: var(--surface-container-low); padding: 16px; border-radius: 8px; border: 1px solid var(--border-subtle); height: 100%;">
                <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px;">
                    <div>
                        <div style="font-weight: 600; font-size: 14px;">Kushal Malla</div>
                        <div style="font-size: 12px; color: var(--on-surface-variant);">LHB • Middle Order</div>
                    </div>
                    <div style="background: rgba(186, 26, 26, 0.1); color: var(--error); padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: 600;">SR: 185.4</div>
                </div>
                <p style="font-size: 13px; color: var(--on-surface); line-height: 20px; margin-bottom: 16px;">Highly destructive in overs 15-20. Prefers pace on the ball targeting cow corner.</p>
                <div style="background: var(--surface-container); display: inline-block; padding: 4px 8px; border-radius: 4px; font-size: 11px; color: var(--on-surface-variant);">Spin Weakness: Left-Arm Orthodox</div>
            </div>
            """, unsafe_allow_html=True)
            
        with c2:
            st.markdown("""
            <div style="background: var(--surface-container-low); padding: 16px; border-radius: 8px; border: 1px solid var(--border-subtle); height: 100%;">
                <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px;">
                    <div>
                        <div style="font-weight: 600; font-size: 14px;">Sompal Kami</div>
                        <div style="font-size: 12px; color: var(--on-surface-variant);">RFM • Powerplay Bowler</div>
                    </div>
                    <div style="background: var(--primary); color: white; padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: 600;">Econ: 6.2</div>
                </div>
                <p style="font-size: 13px; color: var(--on-surface); line-height: 20px; margin-bottom: 16px;">Consistently hits hard lengths early. Swings it away from the right-hander.</p>
                <div style="background: var(--surface-container); display: inline-block; padding: 4px 8px; border-radius: 4px; font-size: 11px; color: var(--on-surface-variant);">Target Zone: Late Cut / Third Man</div>
            </div>
            """, unsafe_allow_html=True)
            
        st.markdown("</div></div>", unsafe_allow_html=True)

    with col_right:
        # Top Order Vulnerability
        st.markdown("""
        <div class="card" style="height: 100%;">
            <div class="card-header">
                <h3>Top Order Vulnerability</h3>
            </div>
            <div class="card-body" style="padding: 24px;">
                <div style="background: var(--surface-container-low); border-radius: 8px; border: 1px solid var(--outline-variant); height: 200px; display: flex; justify-content: center; align-items: center; position: relative;">
                    <div style="position: absolute; top: 16px; left: 0; right: 0; text-align: center; font-size: 12px; color: var(--on-surface-variant);">Pitch Map (Mockup)</div>
                    <div style="width: 80px; height: 140px; border: 1px solid var(--outline-variant); position: relative;">
                        <div style="position: absolute; bottom: 30px; left: 20px; width: 12px; height: 12px; background: var(--error); border-radius: 50%;"></div>
                        <div style="position: absolute; bottom: 25px; left: 25px; width: 12px; height: 12px; background: var(--error); border-radius: 50%;"></div>
                        <div style="position: absolute; bottom: 20px; left: 22px; width: 12px; height: 12px; background: var(--error); border-radius: 50%;"></div>
                        <div style="position: absolute; top: 40px; right: 20px; width: 6px; height: 6px; background: var(--secondary); border-radius: 50%;"></div>
                        <div style="position: absolute; top: 50px; right: 30px; width: 6px; height: 6px; background: var(--secondary); border-radius: 50%;"></div>
                        <div style="position: absolute; bottom: 0; left: 0; right: 0; height: 20px; border-top: 1px solid var(--outline-variant);"></div>
                    </div>
                    <div style="position: absolute; bottom: 8px; right: 16px; font-size: 10px; color: var(--on-surface-variant); display: flex; align-items: center; gap: 4px;">
                        <span style="width: 6px; height: 6px; background: var(--error); border-radius: 50%; display: inline-block;"></span> Dismissals
                    </div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
    st.markdown("<div style='height: 32px;'></div>", unsafe_allow_html=True)

    # Suggested Bowling Plans
    st.markdown("""
    <div class="card">
        <div class="card-header">
            <h3>Suggested Bowling Plans</h3>
            <a href="#" style="font-size: 14px; color: var(--secondary); font-weight: 600; text-decoration: none;">View Detailed Matchups</a>
        </div>
        <div class="card-body" style="padding: 0;">
    """, unsafe_allow_html=True)
    
    df = get_opposition_bowling_plans()
    
    table_html = """
    <table class="bolts-table">
        <thead>
            <tr>
                <th>Phase</th>
                <th>Primary Tactic</th>
                <th>Key Bowler(s)</th>
                <th>Field Setting Focus</th>
            </tr>
        </thead>
        <tbody>
    """
    
    for _, row in df.iterrows():
        # process key bowlers into tags
        bowlers = row['Key Bowler(s)'].split(", ")
        bowler_tags = "".join([f"<span style='background: var(--surface-container); padding: 4px 8px; border-radius: 4px; font-size: 11px; margin-right: 4px;'>{b}</span>" for b in bowlers])
        
        table_html += f"""
            <tr>
                <td style="white-space: nowrap;">{row['Phase']}</td>
                <td>{row['Primary Tactic']}</td>
                <td><div style="display: flex; gap: 4px; flex-wrap: wrap;">{bowler_tags}</div></td>
                <td>{row['Field Setting Focus']}</td>
            </tr>
        """
        
    table_html += "</tbody></table>"
    st.markdown(table_html, unsafe_allow_html=True)
    st.markdown("</div></div>", unsafe_allow_html=True)
