import streamlit as st
from src.dashboard.demo_data import get_batting_phases, get_batting_tactical_summary, get_batting_core_intelligence

def render_batting_intelligence():
    st.markdown(
        """
        <div class="jb-page-head">
            <h2 class="page-title">Batting Intelligence</h2>
            <p class="page-subtitle">Phase behavior, matchup exposure, and batting role recommendations.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<div class='card'><div class='card-header'><h3>Phase Tactical Summary</h3></div><div class='card-body'>", unsafe_allow_html=True)
    tactical_data = get_batting_tactical_summary()
    cols = st.columns(3)
    for i, col in enumerate(cols):
        with col:
            item = tactical_data[i]
            st.markdown(
                f"""
                <div class='insight-box' style='height: 100%;'>
                    <div style='font-size:12px; font-weight:700; color: var(--on-surface-variant); margin-bottom: 8px;'>{item['icon']}</div>
                    <div style='font-weight:700; margin-bottom: 6px;'>{item['phase']}</div>
                    <div style='font-size:13px;'>{item['text']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("</div></div>", unsafe_allow_html=True)

    st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)
    st.markdown("<h3 class='page-subtitle' style='font-size:18px; color: var(--on-surface); font-weight:700;'>Phase Metrics</h3>", unsafe_allow_html=True)

    phases = get_batting_phases()
    phase_cols = st.columns(3)

    for i, col in enumerate(phase_cols):
        p = phases[i]
        phase_name = p['name']
        title_split = phase_name.split(" ")
        title_main = title_split[0]
        title_sub = " ".join(title_split[1:])
        
        with col:
            st.markdown(
                f"""
                <div class="card" style="padding: 18px;">
                    <h3 style="margin:0 0 14px 0;">{title_main} <span style="font-size:13px; color:var(--on-surface-variant);">{title_sub}</span></h3>
                    <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px;">
                        <div><div style="font-size:11px; color:var(--on-surface-variant);">Strike Rate</div><div style="font-size:26px; font-weight:800; color:var(--primary);">{p['sr']}</div><div style="font-size:11px; color:{p['sr_c']};">{p['sr_delta']}</div></div>
                        <div><div style="font-size:11px; color:var(--on-surface-variant);">Dot Ball %</div><div style="font-size:26px; font-weight:800; color:var(--primary);">{p['dot']}</div><div style="font-size:11px; color:{p['dot_c']};">{p['dot_delta']}</div></div>
                        <div><div style="font-size:11px; color:var(--on-surface-variant);">Boundary %</div><div style="font-size:26px; font-weight:800; color:var(--primary);">{p['bnd']}</div><div style="font-size:11px; color:{p['bnd_c']};">{p['bnd_delta']}</div></div>
                        <div><div style="font-size:11px; color:var(--on-surface-variant);">Dismissal Rate</div><div style="font-size:26px; font-weight:800; color:var(--primary);">{p['dis']}</div><div style="font-size:11px; color:{p['dis_c']};">{p['dis_delta']}</div></div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)

    # Heatmap and Table
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        <div class="card" style="height: 100%;">
            <div class="card-header">
                <h3 style="display: flex; align-items: center; gap: 8px;">
                    <span style="font-size: 14px; color: var(--on-surface-variant);">Matrix</span> Matchup Heatmap (SR)
                </h3>
                <span style="font-size: 12px; background: var(--surface-container); padding: 4px 8px; border-radius: 4px;">Top 4 Batters</span>
            </div>
            <div class="card-body">
                <table class="bolts-table">
                    <thead>
                        <tr>
                            <th>Batter</th>
                            <th class="right">RAF</th>
                            <th class="right">LAF</th>
                            <th class="right">OB</th>
                            <th class="right">LBG</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>A. Sharma</td>
                            <td class="right" style="background: var(--primary-container); color: white;">165</td>
                            <td class="right" style="background: rgba(27, 67, 50, 0.7); color: white;">142</td>
                            <td class="right" style="background: rgba(27, 67, 50, 0.1);">118</td>
                            <td class="right" style="background: rgba(27, 67, 50, 0.3);">135</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        df = get_batting_core_intelligence()
        st.markdown("""
        <div class="card" style="height: 100%;">
            <div class="card-header">
                <h3 style="display: flex; align-items: center; gap: 8px;">
                    <span style="font-size: 14px; color: var(--on-surface-variant);">Data</span> Core Intelligence
                </h3>
                <a href="#" style="font-size: 12px; color: var(--primary); font-weight: 600; text-decoration: none;">View All</a>
            </div>
            <div class="card-body" style="padding: 0;">
        """, unsafe_allow_html=True)
        
        table_html = "<table class='bolts-table'><thead><tr><th>Player</th><th class='right'>Inns</th><th class='right'>Runs</th><th class='right'>SR</th><th class='right'>Bndry %</th><th class='right'>Matchup Fit</th></tr></thead><tbody>"
        for _, row in df.iterrows():
            fit = row['Matchup Fit']
            bg = "rgba(45, 106, 79, 0.1)" if fit == "OPTIMAL" else "rgba(82, 183, 136, 0.1)" if fit == "FAVORABLE" else "var(--surface-container)"
            color = "var(--primary)" if fit == "OPTIMAL" else "var(--secondary)" if fit == "FAVORABLE" else "var(--on-surface-variant)"
            fit_badge = f"<span style='background: {bg}; color: {color}; padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: 600;'>{fit}</span>"
            table_html += f"<tr><td>{row['Player']}</td><td class='right'>{row['Inns']}</td><td class='right'>{row['Runs']}</td><td class='right'>{row['SR']}</td><td class='right'>{row['Bndry %']}</td><td class='right'>{fit_badge}</td></tr>"
        table_html += "</tbody></table>"
        st.markdown(table_html, unsafe_allow_html=True)
        st.markdown("</div></div>", unsafe_allow_html=True)

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
    st.markdown(
        """
        <div class="card">
            <div class="card-header"><h3>Decision Summary</h3></div>
            <div class="card-body">
                <div class="insight-box"><strong>Insight:</strong> Boundary efficiency in death overs remains your strongest batting differentiator.</div>
                <div style="height:8px;"></div>
                <div class="insight-box"><strong>Risk:</strong> Powerplay dismissal rate increases when left-arm angle is faced without strike rotation.</div>
                <div style="height:8px;"></div>
                <div class="insight-box"><strong>Recommended Action:</strong> Use one stability role in top three and preserve one accelerator for overs 13-17.</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

