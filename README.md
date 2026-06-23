# Janakpur Bolts Analytics Dashboard 🏏

**Live Deployment:** [cricnepal-janakpurbolts.streamlit.app](https://cricnepal-janakpurbolts.streamlit.app/)

The Janakpur Bolts Analytics Dashboard is a comprehensive cricket tactical intelligence platform designed to empower coaching staff with deep, actionable insights. By leveraging advanced statistical modeling and phase-level analysis, this tool transforms raw match data into decision-ready strategies.

---

## 📊 Data Sources Used

Our analytical engine relies on a robust set of structured cricket data to ensure maximum statistical rigor:

1. **Ball-by-Ball Match Data (Parquet):** Highly granular, delivery-level data to power run-equivalency calculations, win probability models, and matchup engines.
2. **Match Summary & Context (Parquet):** Aggregate match results, venue details, season context (S1, S2, S3), and opposition tiering.
3. **Player Innings & Phase Summaries (Parquet):** Segmented performance metrics breaking down games into Powerplay, Middle, and Death overs.
4. **Player Rosters & Profiles (CSV):** Enriched player datasets that track retained squads, player archetypes, and specialized roles.

## ⚙️ How the Data is Used

The dashboard processes these core datasets through an advanced analytics pipeline to deliver specialized intelligence:

- **Phase-Specific Profiling:** Matches are partitioned into Powerplay (1-6), Middle (7-15), and Death (16-20) overs. The data calculates phase-specific strike rates, economy, dot-ball percentages, and boundary frequencies.
- **Matchup Engine:** By joining ball-by-ball batter and bowler interactions, the platform dynamically generates historical matchup statistics to reveal strengths, weaknesses, and optimal matchups.
- **Forecasting & Shrinkage Models:** For S3 recruiting, the data is fed into Bayesian shrinkage models that adjust small sample sizes against league-wide priors, predicting future performance and isolating regression-to-the-mean candidates.
- **Win Probability Processing:** Historical ball-by-ball context is matched with current game states to determine Win Probability Added (WPA) for individual deliveries and key match turning points.

## 🎯 Outcomes and Capabilities

The output of the analytical processing yields several enterprise-grade dashboards, enabling data-driven decision-making for the Janakpur Bolts:

- **Executive KPI Tracking:** Clear visibility into team form index, Win%, and Net Run Rate (NRR) with season-over-season deltas (S1 vs S2).
- **Tactical Match Reviews:** Automated post-match analysis identifying root causes for wins/losses and highlighting crucial game phases.
- **S3 Recruiting & Drafting Intelligence:** "Moneyball" style scouting that visualizes player form, values expected performance, and categorizes talent into specific tactical archetypes.
- **Opposition Threat Reports:** Team-level radar charts and opposition profiling to anticipate tactics from rival franchises in upcoming fixtures.

---

*Built for the Janakpur Bolts Coaching & Analytics Team.*
