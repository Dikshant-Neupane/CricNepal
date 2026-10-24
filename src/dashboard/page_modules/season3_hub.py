"""Season 3 Hub — the live season layer on top of the S1/S2 analytics:
fixtures with their locked pre-registered forecasts, the running
forecast scorecard, league standings as results arrive, and the
verified squads/coaches.

Everything shown is read from the project's own locked artefacts
(data/fixtures, data/predictions). Forecasts are the append-only
pre-season locks; nothing here recomputes or revises them.
"""
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[3]
FIXTURES_CSV = ROOT / "data" / "fixtures" / "s3_fixtures.csv"
COACHES_CSV = ROOT / "data" / "fixtures" / "s3_coaches.csv"
PRED_DIR = ROOT / "data" / "predictions"
MATCHES_PARQUET = ROOT / "data" / "normalized" / "matches_normalized.parquet"
BBB_PARQUET = ROOT / "data" / "final" / "parquet" / "ball_by_ball.parquet"

SERIES = [
    ("Champion (locked)", "champion"),
    ("Elo baseline", "elo"),
    ("Simulator shadow", "simulator"),
    ("Coach shadow", "coach"),
]


def _orient(p, series_team_1, fixture_team_1):
    """A lock's p_team_1_win expressed for the fixture's team_1."""
    return p if series_team_1 == fixture_team_1 else 1.0 - p


# Every file load_season3 reads. All of them must be tracked in git —
# the deployed app clones the repo, and a file that exists only locally
# (data/ is gitignored; these are force-added) crashes the live page.
# Guarded by test_hub_data_files_are_git_tracked.
HUB_DATA_FILES = [
    "data/fixtures/s3_fixtures.csv",
    "data/predictions/frozen_log.csv",
    "data/predictions/simulator_preseason.csv",
    "data/predictions/coach_shadow.csv",
    "data/fixtures/s3_coaches.csv",
    "data/normalized/matches_normalized.parquet",
    "data/predictions/player_master.csv",
    "data/predictions/player_priors.csv",
]


def _data_mtimes(root: Path):
    """Cache key: the locked artefacts' mtimes. The hub re-reads its
    files only when one of them actually changes (a lock, a result)."""
    return tuple((r, (root / r).stat().st_mtime_ns if (root / r).exists() else 0)
                 for r in HUB_DATA_FILES)


@st.cache_data(show_spinner=False)
def _load_season3_cached(root_str: str, mtimes_key: tuple) -> dict:
    return load_season3(Path(root_str))


def load_season3(root: Path = ROOT) -> dict:
    """Pure data assembly for the hub (unit-tested without Streamlit)."""
    fx = pd.read_csv(root / "data" / "fixtures" / "s3_fixtures.csv",
                     parse_dates=["match_date"])
    frozen = pd.read_csv(root / "data" / "predictions" / "frozen_log.csv")
    champ = frozen[frozen.stage == "P1_preseason_expected_xi"].set_index("match_id")
    # Latest champion lock per match: post-toss > post-XI > pre-season.
    LOCK_PRIORITY = [("P2_post_toss", "Post-toss lock"),
                     ("P1_post_XI", "Post-XI lock"),
                     ("P1_preseason_expected_xi", "Pre-season lock")]
    latest_lock = {}
    for stage, label in LOCK_PRIORITY:
        for r in frozen[frozen.stage == stage].itertuples():
            latest_lock.setdefault(r.match_id, (r, label))
    sim = pd.read_csv(root / "data" / "predictions" / "simulator_preseason.csv").set_index("match_id")
    coach = pd.read_csv(root / "data" / "predictions" / "coach_shadow.csv").set_index("match_id")

    # Results source. If it is ever unavailable the hub must degrade —
    # fixtures and locked predictions still render — never crash.
    matches_path = root / "data" / "normalized" / "matches_normalized.parquet"
    matches_available = matches_path.exists()
    if matches_available:
        matches = pd.read_parquet(matches_path)
    else:
        matches = pd.DataFrame({"season": [], "match_id": [], "winner_name": []})
    s3 = matches[matches.season == "S3"] if "season" in matches.columns else matches.iloc[0:0]
    results = {}
    for r in s3.itertuples():
        if isinstance(r.winner_name, str) and r.winner_name:
            results[r.match_id] = r.winner_name

    rows = []
    for f in fx.itertuples():
        row = {
            "match_id": f.match_id, "match_number": f.match_number,
            "date": f.match_date, "stage": f.stage,
            "team_1": f.team_1_name, "team_2": f.team_2_name,
            "time": getattr(f, "start_time_local", ""),
            "winner": results.get(f.match_id),
        }
        if f.match_id in champ.index:
            c = champ.loc[f.match_id]
            row["champion_preseason"] = _orient(c.p_team_1_win, c.team_1_name, f.team_1_name)
            row["elo"] = _orient(c.p_elo, c.team_1_name, f.team_1_name)
        if f.match_id in latest_lock:
            r, label = latest_lock[f.match_id]
            row["champion"] = _orient(r.p_team_1_win, r.team_1_name, f.team_1_name)
            row["lock_stage"] = label
        if f.match_id in sim.index:
            s = sim.loc[f.match_id]
            row["simulator"] = _orient(s.p_team_1_win, s.team_1_name, f.team_1_name)
        if f.match_id in coach.index:
            k = coach.loc[f.match_id]
            row["coach"] = _orient(k.p_team_1_win, k.team_1_name, f.team_1_name)
        rows.append(row)
    table = pd.DataFrame(rows).sort_values("match_number").reset_index(drop=True)

    # Running scorecard over matches with a decided winner.
    scored = table[table.winner.notna() & table.team_1.notna()]
    scorecard = {}
    for label, key in SERIES:
        col = "champion_preseason" if key == "champion" else key
        if col not in scored.columns or len(scored) == 0:
            scorecard[label] = {"locked": int(table[col].notna().sum()) if col in table else 0,
                                "scored": 0, "log_loss": None, "accuracy": None}
            continue
        d = scored.dropna(subset=[col])
        y = (d.winner == d.team_1).astype(float)
        p = d[col].clip(1e-6, 1 - 1e-6)
        scorecard[label] = {
            "locked": int(table[col].notna().sum()),
            "scored": int(len(d)),
            "log_loss": float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))) if len(d) else None,
            "accuracy": float(np.mean((d[col] >= 0.5) == (y == 1))) if len(d) else None,
        }

    league = table[table.stage == "League"]
    upcoming = league[league.winner.isna()]
    next_match = upcoming.iloc[0].to_dict() if len(upcoming) else None

    coaches = pd.read_csv(root / "data" / "fixtures" / "s3_coaches.csv")
    master = pd.read_csv(root / "data" / "predictions" / "player_master.csv")
    priors = pd.read_csv(root / "data" / "predictions" / "player_priors.csv")
    squads = master.merge(
        priors[["player_key", "prior_group", "bat_index", "bowl_index"]],
        on="player_key", how="left")
    return {"fixtures": table, "scorecard": scorecard,
            "next_match": next_match, "coaches": coaches, "squads": squads,
            "results": results, "matches_available": matches_available}


def compute_standings(fixtures: pd.DataFrame, teams: list[str]) -> pd.DataFrame:
    """League standings from decided fixtures (win 2 pts, no-result 1)."""
    lg = fixtures[(fixtures.stage == "League") & fixtures.team_1.notna()]
    rows = {t: {"Team": t, "P": 0, "W": 0, "L": 0, "NR": 0, "Pts": 0} for t in teams}
    for f in lg.itertuples():
        if f.team_1 not in rows or f.team_2 not in rows:
            continue
        if not isinstance(f.winner, str):
            continue  # not played yet — a fixture without a recorded winner
        for t in (f.team_1, f.team_2):
            rows[t]["P"] += 1
        if f.winner == f.team_1:
            rows[f.team_1]["W"] += 1; rows[f.team_1]["Pts"] += 2; rows[f.team_2]["L"] += 1
        elif f.winner == f.team_2:
            rows[f.team_2]["W"] += 1; rows[f.team_2]["Pts"] += 2; rows[f.team_1]["L"] += 1
        else:
            rows[f.team_1]["NR"] += 1; rows[f.team_2]["NR"] += 1
            rows[f.team_1]["Pts"] += 1; rows[f.team_2]["Pts"] += 1
    out = pd.DataFrame(rows.values())
    return out.sort_values(["Pts", "W", "Team"], ascending=[False, False, True]).reset_index(drop=True)


def render_season3_hub():
    data = _load_season3_cached(str(ROOT), _data_mtimes(ROOT))
    fx, sc = data["fixtures"], data["scorecard"]
    teams = sorted(data["coaches"].team)
    if not data.get("matches_available", True):
        st.warning("Match-results data is temporarily unavailable — standings and the "
                   "forecast scorecard will populate once it is restored. Fixtures and "
                   "locked predictions are unaffected.")

    st.markdown(
        """
        <div class="jb-page-head">
            <h2 class="page-title">Season 3 Hub</h2>
            <p class="page-subtitle">Nepal Premier League Season 3 · 26 October – 21 November 2026 · TU Ground, Kirtipur · single round-robin + playoffs. Forecasts below are the pre-registered locks — fixed before Match 1 and scored as results arrive.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    nm = data["next_match"]
    if nm is not None:
        st.markdown(f"### Next match — Match {int(nm['match_number'])} · {nm['date']:%a %d %b %Y} · {nm['time']} NPT")
        c1, c2 = st.columns(2)
        p = nm.get("champion")
        c1.metric(nm["team_1"], f"{p:.0%} win (locked)" if pd.notna(p) else "—")
        c2.metric(nm["team_2"], f"{1 - p:.0%} win (locked)" if pd.notna(p) else "—")
        parts = []
        for label, key in [("Champion (latest lock)", "champion"), ("Elo baseline", "elo"),
                           ("Simulator shadow", "simulator"), ("Coach shadow", "coach")]:
            v = nm.get(key)
            if pd.notna(v):
                parts.append(f"{label}: {v:.0%} for {nm['team_1']}")
        if nm.get("lock_stage"):
            parts.append(f"Lock stage: {nm['lock_stage']}")
        if parts:
            st.caption(" · ".join(parts))
    else:
        st.markdown("### League stage complete — see the standings below.")

    st.markdown("### Forecast scorecard (pre-season locks, scored on decided matches)")
    sc_rows = [{
        "Series": label, "Locked": v["locked"], "Scored": v["scored"],
        "Log-loss": "—" if v["log_loss"] is None else round(v["log_loss"], 3),
        "Accuracy": "—" if v["accuracy"] is None else f"{v['accuracy']:.0%}",
    } for label, v in sc.items()]
    st.dataframe(pd.DataFrame(sc_rows), width="stretch", hide_index=True)
    if all(v["scored"] == 0 for v in sc.values()):
        st.caption("No matches scored yet — scoring begins with Match 1 on 26 October. "
                   "In backtesting the champion did not beat the Elo baseline; this log is the prospective test.")

    st.markdown("### Standings")
    st.dataframe(compute_standings(fx, teams), width="stretch", hide_index=True)

    st.markdown("### Prediction list — locked before every match")
    show = fx.copy()
    show["Date"] = show.date.dt.strftime("%a %d %b")
    show["Match"] = show.apply(
        lambda r: f"{r.team_1} v {r.team_2}" if pd.notna(r.team_1) else r.stage, axis=1)
    for col in ["champion", "elo", "simulator", "coach"]:
        show[col] = show[col].map(lambda v: f"{v:.0%}" if pd.notna(v) else "—")
    show["Result"] = show.winner.fillna("—")
    show["Lock"] = show.get("lock_stage", "—")
    if hasattr(show["Lock"], "fillna"):
        show["Lock"] = show["Lock"].fillna("—")
    st.dataframe(
        show[["match_number", "Date", "time", "Match", "champion", "elo", "simulator", "coach", "Lock", "Result"]]
        .rename(columns={"match_number": "#", "time": "Start", "champion": "Champion",
                         "elo": "Elo", "simulator": "Simulator", "coach": "Coach"}),
        width="stretch", hide_index=True)
    st.caption("Percentages are win probabilities for the first-named team. The Champion column "
               "shows the latest lock for the match (post-toss > post-XI > pre-season); Elo, "
               "Simulator and Coach are the frozen pre-season series. Results and the scorecard "
               "update as official match data is published after each match.")

    st.markdown("### Squads & coaches")
    team = st.selectbox("Team", teams, index=teams.index("Janakpur Bolts"))
    crow = data["coaches"][data["coaches"].team == team].iloc[0]
    st.write(f"**Head coach:** {crow.head_coach} ({crow.head_coach_country}) · "
             f"**Captain:** {crow.captain} · **Coach since:** {crow.coach_since}")
    sq = data["squads"][data["squads"].team == team].copy()
    sq["Player"] = sq.canonical_name
    sq["Overseas"] = np.where(sq.is_overseas == True, "Yes", "")  # noqa: E712
    sq = sq.sort_values(["role", "Player"])
    st.dataframe(
        sq[["Player", "role", "Overseas", "prior_group", "bat_index", "bowl_index"]]
        .rename(columns={"role": "Role", "prior_group": "Prior basis",
                         "bat_index": "Bat index", "bowl_index": "Bowl index"})
        .round({"bat_index": 3, "bowl_index": 3}),
        width="stretch", hide_index=True)
    st.caption("Squad and coaching data: verified pre-season research (October 2026), "
               "cross-checked against published sources. Bat/bowl indices are relative to the "
               "league average of 1.000; 'debutant' priors are league-average by construction.")
