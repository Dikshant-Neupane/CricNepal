"""Player Profiles — career and per-season aggregates from real NPL data.

Replaces the "Module In Progress" stub. Every number is computed from
player_innings.parquet (with team attribution from match lineups); no
form curves or shot maps are promised, because the underlying data for
those is not in the project.
"""
import pandas as pd
import streamlit as st

from src.config.paths import PARQUET_DIR


@st.cache_data(ttl=600, show_spinner=False)
def _load_profile_data():
    innings = pd.read_parquet(PARQUET_DIR / "player_innings.parquet")
    matches = pd.read_parquet(
        PARQUET_DIR / "matches.parquet", columns=["match_id", "season"]
    )
    lineups = pd.read_parquet(PARQUET_DIR / "match_lineups.parquet")
    innings = innings.merge(matches, on="match_id", how="left")
    lineups = lineups.merge(matches, on="match_id", how="left")
    return innings, lineups


def _season_rows(inn: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for season, grp in inn.groupby("season"):
        runs = int(grp["runs_scored"].sum())
        balls = int(grp["balls_faced"].sum())
        dismissals = int(grp["dismissed"].sum())
        wkts = int(grp["wickets_taken"].sum())
        conceded = int(grp["runs_conceded"].sum())
        bowled = int(grp["balls_bowled"].sum())
        rows.append(
            {
                "Season": season,
                "Matches": int(grp["match_id"].nunique()),
                "Runs": runs,
                "Balls Faced": balls,
                "Strike Rate": round(runs / balls * 100, 1) if balls else None,
                "Dismissals": dismissals,
                "Batting Avg": round(runs / dismissals, 1) if dismissals else None,
                "Wickets": wkts,
                "Runs Conceded": conceded,
                "Balls Bowled": bowled,
                "Economy": round(conceded / (bowled / 6), 2) if bowled else None,
            }
        )
    return pd.DataFrame(rows).sort_values("Season")


def render_player_profiles():
    st.markdown(
        """
        <div class="jb-page-head">
            <h2 class="page-title">Player Profiles</h2>
            <p class="page-subtitle">Career and per-season batting and bowling aggregates, computed from NPL ball-by-ball data (Seasons 1-2).</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    innings, lineups = _load_profile_data()
    players = sorted(innings["player_name"].dropna().unique())
    default = "Aasif Sheikh" if "Aasif Sheikh" in players else players[0]
    player = st.selectbox("Player", players, index=players.index(default))

    inn = innings[innings["player_name"] == player]
    teams = (
        lineups[lineups["player_name"] == player]
        .groupby("season")["team_name"]
        .agg(lambda s: ", ".join(sorted(set(s))))
        .to_dict()
    )
    team_line = " · ".join(f"{s}: {t}" for s, t in sorted(teams.items()))
    if team_line:
        st.caption(f"Teams — {team_line}")

    career = _season_rows(inn)
    totals = career.sum(numeric_only=True)
    runs = int(totals["Runs"])
    balls = int(totals["Balls Faced"])
    wkts = int(totals["Wickets"])
    bowled = int(totals["Balls Bowled"])
    conceded = int(totals["Runs Conceded"])

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Matches", int(inn["match_id"].nunique()))
    c2.metric("Runs", runs)
    c3.metric("Batting SR", f"{runs / balls * 100:.1f}" if balls else "—")
    c4.metric("Wickets", wkts)
    c5.metric("Economy", f"{conceded / (bowled / 6):.2f}" if bowled else "—")

    st.markdown("### Per-Season Breakdown")
    st.dataframe(career.fillna("—"), width="stretch", hide_index=True)
    st.caption(
        "Batting average shows — when the player was never dismissed in a "
        "season; economy shows — when they did not bowl. Wickets are "
        "bowler-credited dismissals (run outs excluded). Player names "
        "follow Cricsheet registry style (e.g. LN Rajbanshi); Season 3 "
        "signings appear here once their first matches are published."
    )
