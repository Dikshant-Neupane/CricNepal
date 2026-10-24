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

    # --- Three systems, scored separately (review fix R2d) ----------------
    # Pre-match, toss-adjusted and in-play are different prediction tasks;
    # their numbers are never pooled or presented as equivalent.
    st.markdown("### System 1 — Pre-Match (P1)")
    st.caption("Inputs: team ratings, expected/confirmed XI strength, form, "
               "rest. Locked before the toss. One prediction per match.")
    score = _load("scorecard.csv")
    p1 = score[score.stage != "P2"] if score is not None and len(score) else None
    if p1 is not None and len(p1):
        st.dataframe(p1, hide_index=True, use_container_width=True)
    else:
        st.info("No Season 3 results have landed yet, so no locked pre-match "
                "prediction has been scored. Season 2 walk-forward backtest: "
                "champion blend log-loss 0.6891 vs higher-Elo 0.6888 — paired "
                "bootstrap 95% CI for the difference is [-0.023, +0.023], which "
                "includes zero: no demonstrated edge over Elo. The shadow "
                "simulator's backtest advantage (log-loss 0.655) is likewise "
                "NOT established — its bootstrap CI vs the champion "
                "[-0.104, +0.043] includes zero. The frozen Season 3 log is "
                "the decisive test for both.")

    st.markdown("### System 2 — Toss-Adjusted (P2)")
    st.caption("Inputs: everything in P1, plus the toss winner and decision. "
               "Locked after the toss, before the first ball. Scored separately "
               "from P1, never pooled with it.")
    p2 = score[score.stage == "P2"] if score is not None and len(score) else None
    if p2 is not None and len(p2):
        st.dataframe(p2, hide_index=True, use_container_width=True)
    else:
        st.info("No toss-adjusted (P2) predictions have been locked and scored "
                "yet. P2 locks on matchdays, after the toss, via "
                "scripts/predict_fixtures.py --toss-csv.")

    st.markdown("### System 3 — In-Play Win Probability")
    st.caption("A different task: the probability of the batting team winning "
               "from the current match state, updated delivery by delivery. "
               "Its metrics are delivery-level and are NOT comparable to the "
               "pre-match or toss-adjusted numbers above.")
    inplay_path = PRED_DIR / "inplay_wp_evaluation.json"
    if inplay_path.exists():
        import json as _json
        ev = _json.loads(inplay_path.read_text())
        o, b1, b2 = ev["overall"], ev["by_innings"]["1"], ev["by_innings"]["2"]
        st.info(f"Out-of-sample evaluation (trained on Season 1 only, scored "
                f"on Season 2 deliveries): log-loss {o['log_loss']:.3f}, "
                f"Brier {o['brier']:.3f}, delivery-level accuracy "
                f"{o['accuracy']:.1%} over {o['n_deliveries']} deliveries "
                f"(innings 1 log-loss {b1['log_loss']:.3f}; innings 2 "
                f"log-loss {b2['log_loss']:.3f}). In-play, delivery-level — "
                f"not comparable to pre-match metrics.")
    else:
        st.info("In-play out-of-sample evaluation not generated yet — run "
                "scripts/evaluate_inplay_wp.py.")
