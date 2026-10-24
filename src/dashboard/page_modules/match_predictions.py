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


@st.cache_data(show_spinner=False)
def _load_cached(name: str, mtime_ns: int):
    return pd.read_csv(PRED_DIR / name)


def _load(name):
    p = PRED_DIR / name
    return _load_cached(name, p.stat().st_mtime_ns) if p.exists() else None


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


def load_match_analysis(root: Path = ROOT) -> list:
    """Per-fixture analysis for the match picker: every Season 3
    fixture (all 32), with the four locked series oriented to the
    fixture's Team 1, the latest champion lock stage, expected-XI
    names and the XI-strength drivers. Playoff fixtures carry no
    probabilities until their teams are known. Pure — unit-tested."""
    import json as _json

    fx = pd.read_csv(root / "data" / "fixtures" / "s3_fixtures.csv",
                     parse_dates=["match_date"])
    fx = fx.sort_values(["match_date", "match_number"])

    def _by_id(name):
        p = root / "data" / "predictions" / name
        if not p.exists():
            return {}
        df = pd.read_csv(p)
        return {r.match_id: r for r in df.itertuples()}

    up = _by_id("upcoming_predictions.csv")
    sim = _by_id("simulator_preseason.csv")
    coach = _by_id("coach_shadow.csv")

    frozen_path = root / "data" / "predictions" / "frozen_log.csv"
    lock_stage = {}
    if frozen_path.exists():
        frozen = pd.read_csv(frozen_path)
        priority = {"P2_post_toss": 3, "P1_post_XI": 2,
                    "P1_preseason_expected_xi": 1}
        for r in frozen.itertuples():
            if r.stage in priority:
                cur = lock_stage.get(r.match_id)
                if cur is None or priority[r.stage] > priority[cur]:
                    lock_stage[r.match_id] = r.stage

    master_path = root / "data" / "predictions" / "player_master.csv"
    names, overseas = {}, {}
    if master_path.exists():
        master = pd.read_csv(master_path)
        names = dict(zip(master.player_key, master.canonical_name))
        overseas = dict(zip(master.player_key, master.is_overseas))

    def _orient(row, fixture_t1):
        if row is None:
            return None
        return (float(row.p_team_1_win) if row.team_1_name == fixture_t1
                else 1.0 - float(row.p_team_1_win))

    def _xi(keys):
        if not isinstance(keys, str):
            return []
        return [(names.get(k, k), bool(overseas.get(k, False)))
                for k in keys.split(";") if k]

    out = []
    for r in fx.itertuples():
        u = up.get(r.match_id)
        item = {
            "match_id": r.match_id,
            "match_number": int(r.match_number),
            "match_date": r.match_date,
            "stage": r.stage,
            "start_time_local": r.start_time_local,
            "team_1_name": r.team_1_name if isinstance(r.team_1_name, str)
                           else None,
            "team_2_name": r.team_2_name if isinstance(r.team_2_name, str)
                           else None,
            "lock_stage": lock_stage.get(r.match_id),
            "champion": None, "elo": None, "simulator": None,
            "coach": None, "rating_1": None, "rating_2": None,
            "xi_1": [], "xi_2": [], "drivers": {},
        }
        if u is not None and item["team_1_name"]:
            item["champion"] = _orient(u, item["team_1_name"])
            item["elo"] = _orient(
                type("R", (), {"team_1_name": u.team_1_name,
                               "p_team_1_win": u.p_elo})(),
                item["team_1_name"])
            item["rating_1"] = float(u.rating_1)
            item["rating_2"] = float(u.rating_2)
            item["xi_1"] = _xi(u.xi_1_keys)
            item["xi_2"] = _xi(u.xi_2_keys)
            item["drivers"] = _json.loads(u.features_json)
            item["simulator"] = _orient(sim.get(r.match_id),
                                        item["team_1_name"])
            item["coach"] = _orient(coach.get(r.match_id),
                                    item["team_1_name"])
        out.append(item)
    return out


def _render_match_analysis():
    """The match picker: choose any fixture, get its full analysis in
    one place — all four locked series, expected XIs, drivers."""
    st.markdown("### Match Analysis — pick a match")
    try:
        analysis = load_match_analysis()
    except Exception:
        st.info("Match analysis is unavailable in this deployment.")
        return

    def _label(m):
        date = pd.Timestamp(m["match_date"]).strftime("%a %d %b")
        if m["team_1_name"]:
            return (f"Match {m['match_number']} · {date} · "
                    f"{m['team_1_name']} v {m['team_2_name']}")
        return f"Match {m['match_number']} · {date} · {m['stage']} · teams TBD"

    labels = [_label(m) for m in analysis]
    default = next((i for i, m in enumerate(analysis)
                    if m["champion"] is not None), 0)
    picked = st.selectbox("Choose a match", labels, index=default,
                          key="predictions_match")
    m = analysis[labels.index(picked)]

    if m["champion"] is None:
        st.info("Playoff fixture — teams, probabilities and locks land "
                "when the league stage settles. The pre-registered "
                "pipeline prices it from the confirmed XIs.")
        return

    t1, t2 = m["team_1_name"], m["team_2_name"]
    series = [("Champion (locked)", m["champion"]), ("Elo baseline", m["elo"]),
              ("Simulator shadow", m["simulator"]),
              ("Coach shadow", m["coach"])]
    cols = st.columns(4)
    for col, (name, p) in zip(cols, series):
        if p is None:
            col.metric(name, "—")
        else:
            fav = t1 if p >= 0.5 else t2
            col.metric(name, f"{max(p, 1 - p):.0%}", delta=fav,
                       delta_color="off")
    lock_labels = {"P1_preseason_expected_xi": "Pre-season lock",
                   "P1_post_XI": "Post-XI lock",
                   "P2_post_toss": "Post-toss lock"}
    st.caption(
        f"Elo: {t1} {m['rating_1']:.0f} · {t2} {m['rating_2']:.0f}. "
        f"Latest champion lock: "
        f"{lock_labels.get(m['lock_stage'], 'none yet')}. "
        "Percentages are the favourite's win probability per series; "
        "series are scored separately, never pooled.")

    x1, x2 = st.columns(2)
    for col, team, xi in ((x1, t1, m["xi_1"]), (x2, t2, m["xi_2"])):
        with col:
            st.markdown(f"**{team} — expected XI**")
            if xi:
                st.dataframe(
                    pd.DataFrame(
                        [{"Player": n, "OS": "OS" if o else ""}
                         for n, o in xi]),
                    hide_index=True, width="stretch")
            else:
                st.caption("Expected XI not available.")
    if m["drivers"]:
        st.markdown("**Why — XI-strength drivers** (positive favours "
                    f"{t1})")
        labels = {"elo_diff": "Elo diff", "xi_batting_diff": "XI batting diff",
                  "xi_bowling_diff": "XI bowling diff",
                  "form_nrr_diff": "Form/NRR diff", "rest_diff": "Rest diff"}
        drv = pd.DataFrame([
            {"Driver": labels.get(k, k), "Value": round(float(v), 3),
             "Favours": t1 if v > 0 else (t2 if v < 0 else "—")}
            for k, v in m["drivers"].items()])
        st.dataframe(drv, hide_index=True, width="stretch")


def render_match_predictions():
    st.markdown(
        """
        <div class="jb-page-head">
            <h2 class="page-title">Match Predictions</h2>
            <p class="page-subtitle">Pre-match win probabilities for Season 3 fixtures — Elo + playing-XI strength blend. Probabilities for all 28 league fixtures were locked before the season; the table below shows the next fixtures first.</p>
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
                     hide_index=True, width="stretch")

    _render_match_analysis()

    st.markdown("### Upcoming Fixtures — P1 Probabilities")
    show = preds.copy()
    show["Favourite"] = show.apply(
        lambda r: r.team_1_name if r.p_team_1_win >= 0.5 else r.team_2_name, axis=1)
    show["Win probability"] = show.apply(
        lambda r: max(r.p_team_1_win, 1 - r.p_team_1_win), axis=1)
    show["p_team_1_win"] = show["p_team_1_win"].round(4)
    show["Win probability"] = show["Win probability"].round(4)
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
            "p_team_1_win": "P(Team 1 win)",
            "Win probability": "Favourite win prob"}),
        hide_index=True, width="stretch")
    st.caption("XI data quality = players in the fixture's two expected XIs "
               "whose identity is not yet resolved to a cricsheet registry ID "
               "in the player master; their priors carry wider uncertainty.")

    st.markdown("### XI-strength drivers — all fixtures")
    st.caption("Feature snapshot per fixture: a positive value favours Team 1. "
               "Elo diff is per 100 Elo points; XI diffs are mean prior-index differences of the expected XIs.")
    feats = pd.json_normalize(show["features_json"].apply(lambda s: __import__("json").loads(s)))
    drv = pd.concat([show[["match_date", "team_1_name", "team_2_name"]].reset_index(drop=True),
                     feats], axis=1)
    drv = drv.rename(columns={
        "match_date": "Date", "team_1_name": "Team 1",
        "team_2_name": "Team 2", "elo_diff": "Elo diff",
        "xi_batting_diff": "XI batting diff",
        "xi_bowling_diff": "XI bowling diff",
        "form_nrr_diff": "Form/NRR diff", "rest_diff": "Rest diff"})
    # Round feature values for display: raw floats rendered with full
    # binary precision (e.g. elo_diff -0.32497301929533023) in the table.
    for _col in drv.select_dtypes(include="float").columns:
        drv[_col] = drv[_col].round(3)
    st.dataframe(drv, hide_index=True, width="stretch")

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
            hide_index=True, width="stretch")

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
        st.dataframe(p1, hide_index=True, width="stretch")
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
        st.dataframe(p2, hide_index=True, width="stretch")
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
