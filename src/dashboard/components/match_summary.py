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
        <div class="match-summary-header">
            <h3>Match Summary</h3>
            <span class="result-badge">{data['result']}</span>
        </div>

        <div class="mr-score-grid">
            <div class="mr-team-col">
                <div class="score-team-name" style="color: {t1_color};">{t1['name']}</div>
                <div class="score-display" style="color: var(--on-surface);">{t1['score']}</div>
                <div class="score-details">{t1['overs']} ({t1['rr']})</div>
            </div>

            <div class="mr-vs-divider">
                <span class="mr-vs-text">VS</span>
            </div>

            <div class="mr-team-col">
                <div class="score-team-name" style="color: {t2_color};">{t2['name']}</div>
                <div class="score-display" style="color: var(--on-surface-variant);">{t2['score']}</div>
                <div class="score-details">{t2['overs']} ({t2['rr']})</div>
            </div>
        </div>

        <div class="potm-footer">
            <div class="mr-potm-group">
                <span class="award">POTM</span>
                <span>POTM: {data['potm']}</span>
            </div>
            <span class="mr-potm-link">Full Scorecard →</span>
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
        icon = "OK" if t["type"] == "success" else "Risk"
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
    <div class="card mr-full-height">
        <div class="card-header">
            <div class="mr-title-row">
                <h3>Tactical Takeaways</h3>
            </div>
        </div>
        <div class="mr-takeaway-body">
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
            <td class="mr-cell-strong">{row['Phase']}</td>
            <td class="right">{row['Match RR']:.2f}</td>
            <td class="right mr-cell-muted">{row['Season Avg']:.2f}</td>
            <td class="right {delta_class}">{arrow} {sign}{delta_val:.2f}</td>
        </tr>
        """

    st.markdown(f"""
    <div class="card">
        <div class="card-header">
            <h3>{title}</h3>
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
            <td class="mr-cell-strong">{row['Batters']}</td>
            <td class="right mr-cell-strong">{row['Runs']}</td>
            <td class="right mr-cell-muted">{row['Balls']}</td>
            <td class="right" style="{sr_style}">{sr_val:.1f}</td>
        </tr>
        """

    st.markdown(f"""
    <div class="card">
        <div class="card-header">
            <h3>{title}</h3>
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
