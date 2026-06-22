import streamlit as st

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
    
    st.info("Matchup Engine requires a live database connection to query ball-by-ball pairings. This feature is currently disabled in the static cloud deployment.")

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
