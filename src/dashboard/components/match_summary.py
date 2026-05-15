"""
Match summary & tactical takeaways components for the Match Review page.
"""
import streamlit as st


def render_match_summary(data: dict) -> None:
    """
    Render the full match summary card: header + scores + POTM footer.

    Args:
        data: Match summary dict from demo_data.get_match_summary()
    """
    t1 = data["team1"]
    t2 = data["team2"]

    t1_color = "var(--primary)" if t1["is_winner"] else "var(--on-surface-variant)"
    t2_color = "var(--primary)" if t2["is_winner"] else "var(--on-surface-variant)"

    st.markdown(f"""
    <div class="card">
        <!-- Header -->
        <div class="match-summary-header">
            <h3>Match Summary</h3>
            <span class="result-badge">{data['result']}</span>
        </div>

        <!-- Scores -->
        <div style="padding: 24px; display: flex; justify-content: center; align-items: center; gap: 32px; flex-wrap: wrap;">
            <!-- Team 1 -->
            <div style="text-align: center; flex: 1; min-width: 180px;">
                <div class="score-team-name" style="color: {t1_color};">{t1['name']}</div>
                <div class="score-display" style="color: var(--on-surface);">{t1['score']}</div>
                <div class="score-details">{t1['overs']} ({t1['rr']})</div>
            </div>

            <!-- VS -->
            <div style="text-align: center; padding: 0 24px; border-left: 1px solid rgba(193,200,194,0.3); border-right: 1px solid rgba(193,200,194,0.3);">
                <span style="font-size: 14px; font-weight: 600; color: var(--outline); letter-spacing: 0.01em;">VS</span>
            </div>

            <!-- Team 2 -->
            <div style="text-align: center; flex: 1; min-width: 180px;">
                <div class="score-team-name" style="color: {t2_color};">{t2['name']}</div>
                <div class="score-display" style="color: var(--on-surface-variant);">{t2['score']}</div>
                <div class="score-details">{t2['overs']} ({t2['rr']})</div>
            </div>
        </div>

        <!-- POTM Footer -->
        <div class="potm-footer">
            <div style="display: flex; align-items: center; gap: 8px;">
                <span class="award">🏆</span>
                <span>POTM: {data['potm']}</span>
            </div>
            <span style="font-size: 12px; font-weight: 500; color: var(--primary); cursor: pointer;">
                Full Scorecard →
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_tactical_takeaways(takeaways: list[dict]) -> None:
    """
    Render the tactical takeaways sidebar card.

    Args:
        takeaways: List of dicts with type, title, desc from demo_data
    """
    items_html = ""
    for t in takeaways:
        icon = "✅" if t["type"] == "success" else "⚠️"
        icon_class = "success" if t["type"] == "success" else "warning"

        items_html += f"""
        <div class="takeaway-item">
            <span class="takeaway-icon {icon_class}">{icon}</span>
            <div>
                <div class="takeaway-title">{t['title']}</div>
                <div class="takeaway-desc">{t['desc']}</div>
            </div>
        </div>
        """

    st.markdown(f"""
    <div class="card" style="height: 100%;">
        <div class="card-header">
            <div style="display: flex; align-items: center; gap: 8px;">
                <span style="font-size: 20px;">💡</span>
                <h3 style="color: var(--primary);">Tactical Takeaways</h3>
            </div>
        </div>
        <div style="padding: 24px; background: rgba(44, 105, 78, 0.05);">
            {items_html}
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_phase_table(df, title: str = "Phase Execution (Batting)") -> None:
    """Render a phase comparison table with delta coloring."""
    rows_html = ""
    for _, row in df.iterrows():
        delta_val = row["Delta"]
        if delta_val > 0:
            delta_class = "delta-positive"
            arrow = "▲"
            sign = "+"
        else:
            delta_class = "delta-negative"
            arrow = "▼"
            sign = ""

        rows_html += f"""
        <tr>
            <td style="font-weight: 500;">{row['Phase']}</td>
            <td class="right">{row['Match RR']:.2f}</td>
            <td class="right" style="color: var(--on-surface-variant);">{row['Season Avg']:.2f}</td>
            <td class="right {delta_class}">{arrow} {sign}{delta_val:.2f}</td>
        </tr>
        """

    st.markdown(f"""
    <div class="card">
        <div style="padding: 10px 24px; border-bottom: 1px solid var(--outline-variant); background: var(--surface);">
            <h3 class="section-header" style="color: var(--primary);">{title}</h3>
        </div>
        <table class="bolts-table">
            <thead>
                <tr>
                    <th>Phase</th>
                    <th class="right">Match RR</th>
                    <th class="right">Season Avg</th>
                    <th class="right">Delta</th>
                </tr>
            </thead>
            <tbody>{rows_html}</tbody>
        </table>
    </div>
    """, unsafe_allow_html=True)


def render_partnerships_table(df, title: str = "Defining Partnerships") -> None:
    """Render a partnerships data table."""
    rows_html = ""
    for _, row in df.iterrows():
        sr_val = row["SR"]
        sr_style = ""
        if sr_val > 200:
            sr_style = "font-weight: 600; color: var(--secondary);"

        rows_html += f"""
        <tr>
            <td style="font-weight: 500;">{row['Batters']}</td>
            <td class="right" style="font-weight: 600;">{row['Runs']}</td>
            <td class="right" style="color: var(--on-surface-variant);">{row['Balls']}</td>
            <td class="right" style="{sr_style}">{sr_val:.1f}</td>
        </tr>
        """

    st.markdown(f"""
    <div class="card">
        <div style="padding: 10px 24px; border-bottom: 1px solid var(--outline-variant); background: var(--surface);">
            <h3 class="section-header" style="color: var(--primary);">{title}</h3>
        </div>
        <table class="bolts-table">
            <thead>
                <tr>
                    <th>Batters</th>
                    <th class="right">Runs</th>
                    <th class="right">Balls</th>
                    <th class="right">SR</th>
                </tr>
            </thead>
            <tbody>{rows_html}</tbody>
        </table>
    </div>
    """, unsafe_allow_html=True)
