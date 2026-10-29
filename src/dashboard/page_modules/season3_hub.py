"""Season 3 Hub — the live season layer on top of the S1/S2 analytics:
fixtures with their locked pre-registered forecasts, the running
forecast scorecard, league standings as results arrive, and the
verified squads/coaches.

Everything shown is read from the project's own locked artefacts
(data/fixtures, data/predictions). Forecasts are the append-only
pre-season locks; nothing here recomputes or revises them.
"""
import json
from datetime import datetime
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

    scorecard_ci = _champion_vs_elo_ci(scored)

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
            "scorecard_ci": scorecard_ci,
            "next_match": next_match, "coaches": coaches, "squads": squads,
            "results": results, "matches_available": matches_available}


# ------------------------------------------------------------------
# Data & model health (plan 7.1). A Hub section, not a new page: the
# showcase navigation is frozen. Everything here is surfaced, never
# hidden — a missing file, a stale status or an open conflict renders
# as a visible warning (plan 7.3 / criteria B3).
# ------------------------------------------------------------------

HEALTH_DATASETS = [
    ("S3 fixtures", "data/fixtures/s3_fixtures.csv"),
    ("Frozen prediction log", "data/predictions/frozen_log.csv"),
    ("Normalized matches (canonical)", "data/normalized/matches_normalized.parquet"),
    ("Ball-by-ball", "data/final/parquet/ball_by_ball.parquet"),
    ("Player master", "data/predictions/player_master.csv"),
    ("Player priors", "data/predictions/player_priors.csv"),
    ("Conflicts register", "data/conflicts_register.csv"),
]


def _file_rows(path: Path):
    """Row count of a CSV/parquet file, or None if unreadable."""
    try:
        if path.suffix == ".parquet":
            import pyarrow.parquet as pq

            return pq.ParquetFile(path).metadata.num_rows
        return len(pd.read_csv(path, usecols=[0]))
    except Exception:
        return None


def _read_json(path: Path):
    """Parsed JSON at path, or None when missing/unreadable."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def load_health(root: Path = ROOT) -> dict:
    """Pure assembly of the health section's data (unit-tested).

    Degrades field by field: every source reports available=False
    rather than raising, and the renderer turns each absence into a
    visible notice.
    """
    datasets = []
    for label, rel in HEALTH_DATASETS:
        p = root / rel
        entry = {"dataset": label, "path": rel, "exists": p.exists(),
                 "updated": None, "rows": None}
        if p.exists():
            entry["updated"] = datetime.fromtimestamp(
                p.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
            entry["rows"] = _file_rows(p)
        datasets.append(entry)

    status = {"available": False, "data_as_of": None,
              "generated_at": None, "stale": False}
    status_path = root / "data" / "predictions" / "predictions_status.json"
    if status_path.exists():
        try:
            raw = json.loads(status_path.read_text(encoding="utf-8"))
            status.update(available=True,
                          data_as_of=raw.get("data_as_of"),
                          generated_at=raw.get("generated_at"))
        except Exception:
            pass
    if status["data_as_of"]:
        # Stale = a played match exists in the canonical data that the
        # prediction artefacts predate.
        try:
            matches = pd.read_parquet(
                root / "data" / "normalized" / "matches_normalized.parquet",
                columns=["match_date"])
            latest = pd.to_datetime(matches["match_date"]).max()
            if pd.notna(latest):
                status["stale"] = str(status["data_as_of"]) < latest.strftime("%Y-%m-%d")
        except Exception:
            pass

    conflicts = {"available": False, "rows": []}
    register_path = root / "data" / "conflicts_register.csv"
    if register_path.exists():
        try:
            reg = pd.read_csv(register_path, dtype=str).fillna("")
            conflicts = {"available": True,
                         "rows": reg.to_dict("records")}
        except Exception:
            pass

    models = {"available": False}
    metrics_path = root / "data" / "predictions" / "backtest_metrics.json"
    if metrics_path.exists():
        try:
            raw = json.loads(metrics_path.read_text(encoding="utf-8"))
            boot = raw.get("champion_vs_elo_bootstrap", {})
            models = {
                "available": True,
                "n": raw.get("n_test"),
                "champion_log_loss": raw["champion_blend"]["log_loss"],
                "elo_log_loss": raw["baseline_higher_elo"]["log_loss"],
                "champion_vs_elo_ci": (boot.get("ci_low"), boot.get("ci_high")),
                "champion_vs_elo_ci_includes_zero": bool(boot.get("ci_includes_zero")),
                "label": ("no demonstrated improvement over Elo"
                          if boot.get("ci_includes_zero") else
                          "champion differs from Elo on the S2 backtest"),
            }
        except Exception:
            models = {"available": False}
    inplay_ci = _read_json(
        root / "data/predictions/inplay_wp_vs_baseline_ci.json")
    if inplay_ci:
        boot = inplay_ci.get("difference_bootstrap") or {}
        models["inplay_vs_baseline"] = {
            "mean_diff": boot.get("mean_diff"),
            "ci_low": boot.get("ci_low"), "ci_high": boot.get("ci_high"),
            "includes_zero": boot.get("ci_includes_zero"),
            "verdict": inplay_ci.get("verdict"),
        }

    test_status = {"available": False, "status": None, "evidence": None}
    matrix_path = root / "docs" / "CRITERIA_MATRIX.md"
    if matrix_path.exists():
        for line in matrix_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("| B5 |"):
                cells = [c.strip() for c in line.strip().strip("|").split("|")]
                if len(cells) >= 3:
                    test_status = {"available": True,
                                   "status": cells[1], "evidence": cells[2]}
                break

    return {"datasets": datasets, "predictions_status": status,
            "conflicts": conflicts, "models": models,
            "test_status": test_status}


def _render_health_section(health: dict):
    st.markdown("### Data & model health")
    rows = [{
        "Dataset": d["dataset"],
        "Updated": d["updated"] if d["exists"] else "MISSING",
        "Rows": "—" if d["rows"] is None else f"{d['rows']:,}",
        "Status": "ok" if d["exists"] else "MISSING",
    } for d in health["datasets"]]
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)

    status = health["predictions_status"]
    if status["available"]:
        text = (f"Prediction artefacts: data as of {status['data_as_of']}; "
                f"status generated {status['generated_at']}.")
        if status["stale"]:
            st.warning(text + " A played match in the canonical data is "
                              "newer than that watermark — the prediction "
                              "artefacts predate it.")
        else:
            st.caption(text)
    else:
        st.warning("Prediction status file is unavailable — artefact "
                   "freshness cannot be verified here.")

    conflicts = health["conflicts"]
    if conflicts["available"] and conflicts["rows"]:
        st.warning(f"Cross-source conflicts on record: "
                   f"{len(conflicts['rows'])} — surfaced here, not "
                   f"silently resolved (see the conflicts register).")
        st.dataframe(pd.DataFrame(conflicts["rows"])[
            ["conflict_id", "type", "scope", "status"]],
            width="stretch", hide_index=True)
    elif conflicts["available"]:
        st.caption("Conflicts register: no open conflicts recorded.")
    else:
        st.warning("Conflicts register is unavailable in this deployment "
                   "— cross-source conflicts cannot be surfaced here "
                   "(run scripts/check_conflicts.py to generate it).")

    models = health["models"]
    if models["available"]:
        lo, hi = models["champion_vs_elo_ci"]
        st.caption(
            f"Model label (S2 backtest, n={models['n']}): Champion "
            f"log-loss {models['champion_log_loss']:.3f} vs Elo "
            f"{models['elo_log_loss']:.3f}; paired bootstrap 95% CI for "
            f"the difference [{lo:+.3f}, {hi:+.3f}] — "
            f"{models['label']} (Section 5 labelling rule).")
    else:
        st.warning("Backtest metrics are unavailable — model labels "
                   "cannot be verified here.")
    ip = models.get("inplay_vs_baseline")
    if ip and ip.get("mean_diff") is not None:
        st.caption(
            f"In-play model vs simple baseline (paired states, S2): "
            f"mean log-loss difference {ip['mean_diff']:+.4f} (95% CI "
            f"[{ip['ci_low']:+.4f}, {ip['ci_high']:+.4f}]) — "
            f"{ip.get('verdict') or ''}.")

    ts = health["test_status"]
    if ts["available"]:
        st.caption(f"Test-suite status (criteria matrix B5): {ts['status']}.")


def _champion_vs_elo_ci(scored: pd.DataFrame):
    """Paired bootstrap of the champion-minus-Elo per-match log-loss
    difference over the matches scored so far (plan 5.5 / V4).
    Match-level resampling, fixed seed; None until at least one match
    is scored for both series."""
    if scored is None or len(scored) == 0:
        return None
    if "champion" not in scored.columns or "elo" not in scored.columns:
        return None
    d = scored.dropna(subset=["champion", "elo"])
    if len(d) == 0:
        return None
    from src.prediction.metrics import paired_bootstrap, per_match_log_loss

    y = (d["winner"] == d["team_1"]).astype(float)
    diffs = (per_match_log_loss(d["champion"], y)
             - per_match_log_loss(d["elo"], y))
    boot = paired_bootstrap(np.asarray(diffs, dtype=float))
    return {"n": boot["n_matches"], "mean_diff": boot["mean_diff"],
            "ci_low": boot["ci_low"], "ci_high": boot["ci_high"],
            "includes_zero": boot["ci_includes_zero"]}


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
    ci = data.get("scorecard_ci")
    if ci:
        verdict = ("includes zero — no demonstrated difference yet"
                   if ci["includes_zero"] else "excludes zero")
        st.caption(
            f"Champion − Elo on scored matches: mean log-loss difference "
            f"{ci['mean_diff']:+.3f} (paired bootstrap 95% CI "
            f"[{ci['ci_low']:+.3f}, {ci['ci_high']:+.3f}], "
            f"n={ci['n']} matches) — {verdict}.")

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
    disp = (sq[["Player", "role", "Overseas", "prior_group", "bat_index",
                "bowl_index"]]
            .rename(columns={"role": "Role", "prior_group": "Prior basis",
                             "bat_index": "Bat index",
                             "bowl_index": "Bowl index"}))
    disp["Prior basis"] = disp["Prior basis"].map(
        {"npl_experienced": "NPL experience", "external_pro": "External pro",
         "debutant": "Debutant"}.get, na_action="ignore").fillna(
             disp["Prior basis"])
    disp["Bat index"] = disp["Bat index"].map(lambda v: f"{v:.3f}")
    disp["Bowl index"] = disp["Bowl index"].map(lambda v: f"{v:.3f}")
    st.dataframe(disp, width="stretch", hide_index=True)
    st.caption("Squad and coaching data: verified pre-season research (October 2026), "
               "cross-checked against published sources. Bat/bowl indices are relative to the "
               "league average of 1.000; 'debutant' priors are league-average by construction.")

    st.divider()
    _render_health_section(load_health(ROOT))
