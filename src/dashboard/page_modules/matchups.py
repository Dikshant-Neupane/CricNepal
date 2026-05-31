import streamlit as st
from ..demo_data import get_matchup_plan

def render_matchups():
    st.markdown(
        """
        <div class="jb-page-head">
            <h2 class="page-title">Matchup Engine</h2>
            <p class="page-subtitle">Head-to-head probabilities and tactical plans by phase.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns([1, 3])
    
    with col1:
        st.markdown("""
        <h3 class="section-header" style="margin-bottom: 16px;">Configuration</h3>
        """, unsafe_allow_html=True)
        
        st.selectbox("Batter (Bolts)", ["A. Sheikh", "A. Sharma", "R. Singh"])
        st.selectbox("Bowler (Opposition)", ["S. Lamichhane", "K. Malla", "L. Rajbanshi"])
        
        st.markdown("<div style='margin-bottom: 16px;'></div>", unsafe_allow_html=True)
        st.markdown("<div style='font-size: 14px; font-weight: 600; margin-bottom: 8px;'>Season Filter</div>", unsafe_allow_html=True)
        
        st.radio("Season Filter", ["All", "2024", "2023"], horizontal=True)
        
        st.slider("Sample Min Threshold Balls", 0, 100, 30, label_visibility="visible")
        
        st.markdown("<div style='margin-top: 18px;'></div>", unsafe_allow_html=True)
        st.button("Run Engine", type="primary", width="stretch")
        
    with col2:
        # Matchup Score Card
        st.markdown("""
        <div class="card" style="margin-bottom: 24px;">
            <div class="card-body" style="display: flex; justify-content: space-between; align-items: center; padding: 32px;">
                <div>
                    <div style="font-size: 12px; font-weight: 600; color: var(--on-surface-variant); text-transform: uppercase; letter-spacing: 0.02em; margin-bottom: 8px;">Matchup Score</div>
                    <div style="display: flex; align-items: baseline; gap: 8px;">
                        <span style="font-size: 64px; font-weight: 700; color: var(--primary); line-height: 1;">78</span>
                        <span style="font-size: 24px; color: var(--on-surface-variant);">/ 100</span>
                    </div>
                </div>
                <div style="text-align: right;">
                    <div style="display: inline-flex; align-items: center; gap: 8px; background: rgba(82, 183, 136, 0.1); color: var(--secondary); padding: 8px 16px; border-radius: 999px; font-size: 14px; font-weight: 600; border: 1px solid var(--secondary-soft); margin-bottom: 8px;">
                        <span style="width: 8px; height: 8px; background: var(--secondary); border-radius: 50%; display: inline-block;"></span> Favorable to Batter
                    </div>
                    <div style="font-size: 12px; color: var(--on-surface-variant);">Data Confidence:<br><span style="font-weight: 600; color: var(--on-surface);">Strong (142 Balls)</span></div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Stats Cards
        c1, c2, c3, c4 = st.columns(4)
        
        with c1:
            st.markdown("""
            <div class="card" style="height: 100%;">
                <div class="card-body">
                    <div style="font-size: 14px; font-weight: 600; margin-bottom: 16px;">Dismissal Prob.</div>
                    <div style="font-size: 32px; font-weight: 700; color: var(--primary); margin-bottom: 8px;">12.4%</div>
                    <div style="font-size: 12px; color: var(--on-surface-variant);">Per 10 balls faced</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        with c2:
            st.markdown("""
            <div class="card" style="height: 100%;">
                <div class="card-body">
                    <div style="font-size: 14px; font-weight: 600; margin-bottom: 16px;">Expected SR</div>
                    <div style="font-size: 32px; font-weight: 700; color: var(--primary); margin-bottom: 8px;">148.5</div>
                    <div style="font-size: 12px; color: var(--on-surface-variant);">+12 over average</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        with c3:
            st.markdown("""
            <div class="card" style="height: 100%;">
                <div class="card-body">
                    <div style="font-size: 14px; font-weight: 600; margin-bottom: 16px;">Dot Pressure</div>
                    <div style="font-size: 32px; font-weight: 700; color: var(--primary); margin-bottom: 8px;">32%</div>
                    <div style="font-size: 12px; color: var(--on-surface-variant);">Balls resulting in 0 runs</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        # Recommended Plan
        st.markdown("<div style='margin-bottom: 14px;'></div>", unsafe_allow_html=True)
        
        plan = get_matchup_plan()
        
        st.markdown("""
        <div class="card">
            <div class="card-header" style="background: var(--primary); border-bottom: none; border-radius: 8px 8px 0 0;">
                <h3 style="color: white; display: flex; justify-content: space-between; width: 100%;">
                    <span>Recommended Plan</span>
                    <span style="opacity: 0.8;">Detail</span>
                </h3>
            </div>
            <div class="card-body" style="padding: 32px;">
                <p style="font-size: 16px; line-height: 24px; margin-bottom: 24px; color: var(--on-surface);">
                    Look to attack early in the over. The bowler consistently misses lengths on the pads during deliveries 1 and 2.
                </p>
                <ul style="padding-left: 20px; font-size: 14px; color: var(--on-surface-variant); line-height: 24px;">
        """ + "".join([f"<li style='margin-bottom: 12px;'>{p}</li>" for p in plan]) + """
                </ul>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
    st.markdown(
        """
        <div class="card">
            <div class="card-header"><h3>Decision Summary</h3></div>
            <div class="card-body">
                <div class="insight-box"><strong>Insight:</strong> This batter-bowler pairing is favorable when attacking first two balls of the over.</div>
                <div style="height:8px;"></div>
                <div class="insight-box"><strong>Risk:</strong> Dot pressure rises if line is forced square on the off side in balls 3-4.</div>
                <div style="height:8px;"></div>
                <div class="insight-box"><strong>Recommended Action:</strong> Keep rotation option open and target leg-side release zones early.</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
