import streamlit as st
import pandas as pd
from src.dashboard.demo_data import get_batting_phases, get_batting_tactical_summary, get_batting_core_intelligence

def render_batting_intelligence():
    st.markdown("""
    <div style="margin-bottom: 48px;">
        <h2 class="page-title">Batting Intelligence</h2>
        <p class="page-subtitle">Phase dynamics, individual matchups, and tactical execution.</p>
    </div>
    """, unsafe_allow_html=True)

    # Tactical Execution Summary
    st.markdown("""
    <div class="card" style="margin-bottom: 32px;">
        <div class="card-header">
            <h3 style="display: flex; align-items: center; gap: 8px;">
                <span style="font-size: 20px;">🤖</span> Tactical Execution Summary
            </h3>
        </div>
        <div class="card-body" style="padding: 16px 24px;">
    """, unsafe_allow_html=True)
    
    tactical_data = get_batting_tactical_summary()
    cols = st.columns(3)
    for i, col in enumerate(cols):
        with col:
            item = tactical_data[i]
            st.markdown(f"""
            <div style="background: rgba(45, 106, 79, 0.05); padding: 16px; border-radius: 8px; height: 100%;">
                <div style="display: flex; gap: 12px;">
                    <div style="font-size: 20px;">{item['icon']}</div>
                    <div>
                        <span style="font-weight: 600; font-size: 14px; color: var(--on-surface);">{item['phase']}: </span>
                        <span style="font-size: 14px; color: var(--on-surface-variant);">{item['text']}</span>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("</div></div>", unsafe_allow_html=True)

    # Phase Metrics
    st.markdown("""
    <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 16px;">
        <span style="font-size: 20px;">⏱️</span>
        <h3 class="section-header">Phase Metrics</h3>
    </div>
    """, unsafe_allow_html=True)

    phases = get_batting_phases()
    phase_cols = st.columns(3)
    
    # Overriding the phase rendering slightly to match the specific "Phase Metrics" layout 
    # (Strike Rate, Dot Ball %, Boundary %, Dismissal Rate)
    # The mockup shows exactly these 4 stats per phase.
    
    metrics_mapping = [
        {"sr": "145.2", "dot": "38.4%", "bnd": "24.1%", "dis": "21.5", "sr_delta": "↑ 138.0 (Lg Avg)", "dot_delta": "↓ 42.1% (Lg Avg)", "bnd_delta": "↑ 21.0% (Lg Avg)", "dis_delta": "Avg runs/wkt", "sr_c": "var(--secondary)", "dot_c": "var(--error)", "bnd_c": "var(--secondary)", "dis_c": "var(--error)"},
        {"sr": "122.8", "dot": "32.1%", "bnd": "12.5%", "dis": "35.2", "sr_delta": "↓ 128.5 (Lg Avg)", "dot_delta": "↑ 28.5% (Lg Avg)", "bnd_delta": "~ 13.0% (Lg Avg)", "dis_delta": "Avg runs/wkt", "sr_c": "var(--error)", "dot_c": "var(--error)", "bnd_c": "var(--on-surface-variant)", "dis_c": "var(--primary)"},
        {"sr": "185.4", "dot": "22.0%", "bnd": "31.2%", "dis": "14.8", "sr_delta": "↑ 165.0 (Lg Avg)", "dot_delta": "↓ 26.5% (Lg Avg)", "bnd_delta": "↑ 25.0% (Lg Avg)", "dis_delta": "Avg runs/wkt", "sr_c": "var(--secondary)", "dot_c": "var(--secondary)", "bnd_c": "var(--secondary)", "dis_c": "var(--on-surface-variant)"}
    ]

    for i, col in enumerate(phase_cols):
        m = metrics_mapping[i]
        phase_name = phases[i]['name']
        title_split = phase_name.split(" ")
        title_main = title_split[0]
        title_sub = " ".join(title_split[1:])
        
        with col:
            st.markdown(f"""
            <div class="card" style="padding: 24px;">
                <h3 style="margin: 0 0 24px 0; font-size: 18px; font-weight: 600;">{title_main} <span style="font-size: 14px; font-weight: 400; color: var(--on-surface-variant);">{title_sub}</span></h3>
                
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 24px;">
                    <div>
                        <div style="font-size: 12px; color: var(--on-surface-variant); font-weight: 500; margin-bottom: 4px;">Strike Rate</div>
                        <div style="font-size: 24px; font-weight: 700; color: var(--primary);">{m['sr']}</div>
                        <div style="font-size: 12px; color: {m['sr_c']}; margin-top: 4px; font-weight: 500;">{m['sr_delta']}</div>
                    </div>
                    <div>
                        <div style="font-size: 12px; color: var(--on-surface-variant); font-weight: 500; margin-bottom: 4px;">Dot Ball %</div>
                        <div style="font-size: 24px; font-weight: 700; color: var(--primary);">{m['dot']}</div>
                        <div style="font-size: 12px; color: {m['dot_c']}; margin-top: 4px; font-weight: 500;">{m['dot_delta']}</div>
                    </div>
                    <div>
                        <div style="font-size: 12px; color: var(--on-surface-variant); font-weight: 500; margin-bottom: 4px;">Boundary %</div>
                        <div style="font-size: 24px; font-weight: 700; color: var(--primary);">{m['bnd']}</div>
                        <div style="font-size: 12px; color: {m['bnd_c']}; margin-top: 4px; font-weight: 500;">{m['bnd_delta']}</div>
                    </div>
                    <div>
                        <div style="font-size: 12px; color: var(--on-surface-variant); font-weight: 500; margin-bottom: 4px;">Dismissal Rate</div>
                        <div style="font-size: 24px; font-weight: 700; color: {m['dis_c'] if m['dis_c'] != 'var(--primary)' and m['dis_c'] != 'var(--on-surface-variant)' else 'var(--primary)'};">{m['dis']}</div>
                        <div style="font-size: 12px; color: {m['dis_c']}; margin-top: 4px; font-weight: 500;">{m['dis_delta']}</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<div style='height: 32px;'></div>", unsafe_allow_html=True)

    # Heatmap and Table
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        <div class="card" style="height: 100%;">
            <div class="card-header">
                <h3 style="display: flex; align-items: center; gap: 8px;">
                    <span style="font-size: 20px;">🔠</span> SR Matchup Heatmap
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
                    <span style="font-size: 20px;">📊</span> Core Intelligence
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

