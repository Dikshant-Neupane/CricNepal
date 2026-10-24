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

# Communication gate (review §10): the standing label shown on this
# page. The system is a prospective experiment, not a proven model.
STANDING_LABEL = ("Prospective evaluation — experimental forecasting; "
                  "not a validated high-accuracy predictor")


def _stages():
    """The canonical stage registry (src/prediction/stages.py, G1),
    imported lazily with the same sys.path guard as the engine import
    in expected_xi_unresolved."""
    import sys
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from src.prediction import stages
    return stages


def _canonical_of(stage_str):
    """Canonical horizon for a stored stage string; unregistered
    strings fall back to themselves so a future stage can never crash
    the page (scoring, by contrast, refuses them)."""
    try:
        return _stages().canonical_stage(stage_str)
    except ValueError:
        return stage_str


def _load(name):
    p = PRED_DIR / name
    return pd.read_csv(p) if p.exists() else None


def expected_xi_unresolved(master: pd.DataFrame, priors: pd.DataFrame) -> dict:
    """Per team: how many players in the expected XI (the engine's
    selector over the priors) have an UNRESOLVED cricsheet registry ID
    in the player master. Computed from the real files on every call —
    a data-quality flag for display, never a model input and never
    hardcoded."""
    import sys
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from src.prediction import engine
    unresolved = set(master.loc[master["cricsheet_registry_id"].isna(),
                                "player_key"])
    out = {}
    for team, squad in priors.groupby("team"):
        xi = engine.select_expected_xi(squad)
        out[str(team)] = int(sum(1 for k in xi if k in unresolved))
    return out


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
    st.warning(STANDING_LABEL)
    # Canonical stage names (G1, review S13): "P1" alone named two
    # different information sets, so horizons carry canonical names
    # everywhere on this page; the frozen log keeps its stored stage
    # strings, mapped here exactly once.
    st.caption("Forecast stages use canonical names: "
               + _stages().mapping_note() + ".")
    preds = _load("upcoming_predictions.csv")
    ratings = _load("team_ratings_current.csv")
    if preds is None:
        st.warning("Prediction data not found. Run scripts/refresh_predictions.py.")
        return

    if ratings is not None:
        st.markdown("### Team Ratings (start of Season 3)")
        # As-of labelling (F3): ratings rest on the latest PUBLISHED
        # match, which lags the latest played match (cricsheet lag).
        status_path = PRED_DIR / "predictions_status.json"
        if status_path.exists():
            import json as _json2
            _status = _json2.loads(status_path.read_text())
            _prov_n = int(_status.get("n_provisional", 0) or 0)
            _prov_txt = (f" + {_prov_n} provisional result(s) "
                         "included in the ratings basis."
                         if _prov_n else "")
            st.caption(f"Ratings as of: {_status['data_as_of']} "
                       f"(latest published match; "
                       f"{_status['n_matches_ingested']} matches ingested). "
                       "Cricsheet publication lags real time, so in-season "
                       "ratings can trail the latest played match."
                       + _prov_txt)
        else:
            st.caption("Ratings as of: unknown — predictions_status.json "
                       "has not been generated yet (run "
                       "scripts/refresh_predictions.py).")
        st.dataframe(ratings.rename(columns={"team": "Team", "rating_s3_start": "Elo"}),
                     hide_index=True, use_container_width=True)

    st.markdown("### Upcoming Fixtures — P1 Probabilities")
    show = preds.copy()
    show["Favourite"] = show.apply(
        lambda r: r.team_1_name if r.p_team_1_win >= 0.5 else r.team_2_name, axis=1)
    show["Win probability"] = show.apply(
        lambda r: max(r.p_team_1_win, 1 - r.p_team_1_win), axis=1)
    # XI data-quality flag: players in the two expected XIs whose
    # cricsheet registry ID is unresolved in the player master
    # (computed live from player_master.csv + player_priors.csv).
    cols = ["match_date", "team_1_name", "team_2_name", "rating_1", "rating_2",
            "p_team_1_win", "Favourite", "Win probability"]
    master, priors = _load("player_master.csv"), _load("player_priors.csv")
    if master is not None and priors is not None:
        dq = expected_xi_unresolved(master, priors)
        show["XI data quality"] = show.apply(
            lambda r: f"{dq.get(r.team_1_name, 0) + dq.get(r.team_2_name, 0)} unresolved",
            axis=1)
        cols.append("XI data quality")
    st.dataframe(
        show[cols].rename(columns={
            "match_date": "Date", "team_1_name": "Team 1", "team_2_name": "Team 2",
            "rating_1": "Elo 1", "rating_2": "Elo 2",
            "p_team_1_win": "P(Team 1 win)"}),
        hide_index=True, use_container_width=True)
    st.caption("XI data quality = players in the fixture's two expected XIs "
               "whose identity is not yet resolved to a cricsheet registry ID "
               "in the player master; their priors carry wider uncertainty.")

    st.markdown("### Why — XI-strength drivers")
    st.caption("Feature snapshot per fixture: a positive value favours Team 1. "
               "elo_diff is per 100 Elo points; xi diffs are mean prior-index differences of the expected XIs.")
    feats = pd.json_normalize(show["features_json"].apply(lambda s: __import__("json").loads(s)))
    drv = pd.concat([show[["match_date", "team_1_name", "team_2_name"]].reset_index(drop=True),
                     feats], axis=1)
    st.dataframe(drv, hide_index=True, use_container_width=True)

    # --- Shadow simulator (Phase 2, A1): locked, scored separately,
    # never the headline. Shown distinctly from the champion P1s above.
    frozen = _load("frozen_log.csv")
    if frozen is not None and (frozen.stage == "SIM_shadow_preseason").any():
        sim = frozen[frozen.stage == "SIM_shadow_preseason"].copy()
        dates = preds.set_index("match_id")["match_date"].to_dict()
        sim["match_date"] = sim["match_id"].map(dates)
        sim["Simulator favourite"] = sim.apply(
            lambda r: r.team_1_name if r.p_team_1_win >= 0.5 else r.team_2_name,
            axis=1)
        st.markdown("### Shadow Simulator — Locked Pre-Season (SIM_SHADOW)")
        st.caption("Monte Carlo simulator probabilities (10,000 sims per "
                   "match, expected XIs), locked in the frozen log as stage "
                   "SIM_shadow_preseason (canonical: SIM_SHADOW) BEFORE the "
                   "season. Shadow only: "
                   "scored separately after the season, never the headline "
                   "prediction, and not comparable row-by-row with P1 until "
                   "both are scored.")
        st.dataframe(
            sim[["match_date", "team_1_name", "team_2_name", "p_team_1_win",
                 "Simulator favourite"]].rename(columns={
                     "match_date": "Date", "team_1_name": "Team 1",
                     "team_2_name": "Team 2", "p_team_1_win": "Sim P(Team 1 win)"}),
            hide_index=True, use_container_width=True)

    # --- Three systems, scored separately (review fix R2d) ----------------
    # Pre-match, toss-adjusted and in-play are different prediction tasks;
    # their numbers are never pooled or presented as equivalent.
    st.markdown("### System 1 — Pre-Match (P0_PRESEASON / P1_CONFIRMED_XI)")
    st.caption("Inputs: team ratings, expected/confirmed XI strength, form, "
               "rest. Locked before the toss. One prediction per match. "
               "P0 = pre-season expected XI; P1 = matchday confirmed XI — "
               "different information sets, scored separately.")
    score = _load("scorecard.csv")
    if score is not None and len(score):
        _canon = score["stage"].map(_canonical_of)
        p1 = score[_canon.isin(["P0_PRESEASON", "P1_CONFIRMED_XI"])]
    else:
        p1 = None
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

    st.markdown("### System 2 — Toss-Adjusted (P2_POST_TOSS)")
    st.caption("Inputs: everything in P1, plus the toss winner and decision. "
               "Locked after the toss, before the first ball. Scored separately "
               "from P1, never pooled with it.")
    if score is not None and len(score):
        p2 = score[score["stage"].map(_canonical_of) == "P2_POST_TOSS"]
    else:
        p2 = None
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
