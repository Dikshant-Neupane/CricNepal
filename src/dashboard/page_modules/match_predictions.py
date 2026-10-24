"""
Match Predictions Module — CricNepal Performance Lab
Pre-match probabilities for every Season 3 fixture (champion blend),
team ratings, XI-strength drivers, and the frozen-log scorecard.
Data: data/predictions/*.csv produced by the prediction pipeline
(scripts/refresh_predictions.py). See docs/PREDICTION_SYSTEM.md.
"""
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent.parent.parent
PRED_DIR = ROOT / "data" / "predictions"


def _load(name):
    p = PRED_DIR / name
    return pd.read_csv(p) if p.exists() else None


def render_match_predictions():
    st.markdown(
        """
        <div class="jb-page-head">
            <h2 class="page-title">Match Predictions</h2>
            <p class="page-subtitle">Pre-match win probabilities for every Season 3 fixture — Elo + playing-XI strength blend, locked before each match.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    preds = _load("upcoming_predictions.csv")
    ratings = _load("team_ratings_current.csv")
    if preds is None:
        st.warning("Prediction data not found. Run scripts/refresh_predictions.py.")
        return

    if ratings is not None:
        st.markdown("### Team Ratings (start of Season 3)")
        st.dataframe(ratings.rename(columns={"team": "Team", "rating_s3_start": "Elo"}),
                     hide_index=True, use_container_width=True)

    st.markdown("### Upcoming Fixtures — P1 Probabilities")
    show = preds.copy()
    show["Favourite"] = show.apply(
        lambda r: r.team_1_name if r.p_team_1_win >= 0.5 else r.team_2_name, axis=1)
    show["Win probability"] = show.apply(
        lambda r: max(r.p_team_1_win, 1 - r.p_team_1_win), axis=1)
    st.dataframe(
        show[["match_date", "team_1_name", "team_2_name", "rating_1", "rating_2",
              "p_team_1_win", "Favourite", "Win probability"]].rename(columns={
                  "match_date": "Date", "team_1_name": "Team 1", "team_2_name": "Team 2",
                  "rating_1": "Elo 1", "rating_2": "Elo 2",
                  "p_team_1_win": "P(Team 1 win)"}),
        hide_index=True, use_container_width=True)

    st.markdown("### Why — XI-strength drivers")
    st.caption("Feature snapshot per fixture: a positive value favours Team 1. "
               "elo_diff is per 100 Elo points; xi diffs are mean prior-index differences of the expected XIs.")
    feats = pd.json_normalize(show["features_json"].apply(lambda s: __import__("json").loads(s)))
    drv = pd.concat([show[["match_date", "team_1_name", "team_2_name"]].reset_index(drop=True),
                     feats], axis=1)
    st.dataframe(drv, hide_index=True, use_container_width=True)

    st.markdown("### Frozen-Log Scorecard")
    score = _load("scorecard.csv")
    if score is not None and len(score):
        st.dataframe(score, hide_index=True, use_container_width=True)
    else:
        st.info("No Season 3 results have landed yet, so no locked prediction "
                "has been scored. Season 2 walk-forward backtest: champion blend "
                "accuracy 46.9%, log-loss 0.689 (higher-Elo baseline 0.689, coin "
                "flip 0.693) — the system has not yet demonstrated an edge over "
                "Elo alone; the frozen Season 3 log is the decisive test.")
