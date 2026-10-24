"""
Prediction engine: fixture probabilities, expected XIs, frozen log.

Headline probability = champion blend (Elo + fixed XI mapping, see
model.blend_probability). The fitted logistic is emitted alongside as
`p_logistic_challenger` and never headlines in v1.

Frozen log rules: append-only CSV; a (match_id, stage) pair can be locked
ONCE; refreshes never rewrite it. Stages: 'P1_preseason_expected_xi'
(pre-season, expected XI from priors), 'P1' (post-XI-announcement),
'P2' (post-toss).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from . import elo as E
from . import model as M

MODEL_VERSION = "v1"
FROZEN_FIELDS = ["match_id", "season", "stage", "timestamp_locked",
                 "model_version", "team_1_name", "team_2_name",
                 "p_team_1_win", "p_elo", "p_logistic_challenger",
                 "features_json"]

# --- Three-system input contracts (review fix R2) -------------------------
# Pre-match (P1), toss-adjusted (P2) and in-play are DIFFERENT prediction
# tasks. Their allowed inputs are declared here and enforced: a P1
# computation must never see a toss field, and P2 refuses to run without
# the toss result. The in-play system (src/analytics/win_probability_
# model.py) is separate code and is evaluated separately -- it never
# enters this engine.
TOSS_FIELDS = ("toss_winner_name", "toss_decision", "bat_first_team",
               "team_1_bats_first")
_P1_INPUTS = ["elo_diff", "xi_batting_diff", "xi_bowling_diff",
              "form_nrr_diff", "rest_diff", "expected_xi", "player_priors",
              "team_ratings"]
STAGE_INPUTS = {
    "P1_preseason_expected_xi": {
        "system": "pre_match", "allowed": list(_P1_INPUTS),
        "forbidden": list(TOSS_FIELDS), "requires": []},
    "P1": {
        "system": "pre_match", "allowed": list(_P1_INPUTS),
        "forbidden": list(TOSS_FIELDS), "requires": []},
    "P2": {
        "system": "toss_adjusted",
        "allowed": list(_P1_INPUTS) + ["toss_winner_name", "toss_decision"],
        "forbidden": [], "requires": ["toss_winner_name", "toss_decision"]},
}


def validate_stage_inputs(stage: str, inputs) -> None:
    """Enforce the input contract for a prediction stage.

    - Unknown stage: refuse.
    - P1 stages: refuse if any toss field is present in `inputs`.
    - P2: refuse unless toss_winner_name and toss_decision are present
      and the decision is 'bat' or 'field'.
    `inputs` is any mapping (or iterable of keys) of supplied input names.
    """
    if stage not in STAGE_INPUTS:
        raise ValueError(f"unknown prediction stage: {stage!r}")
    keys = set(inputs.keys()) if hasattr(inputs, "keys") else set(inputs)
    spec = STAGE_INPUTS[stage]
    bad = keys & set(spec["forbidden"])
    if bad:
        raise ValueError(
            f"stage {stage} is a pre-match (P1) prediction and must not "
            f"use toss inputs: {sorted(bad)}")
    for req in spec["requires"]:
        if req not in keys:
            raise ValueError(f"stage {stage} requires input {req!r}")
    if stage == "P2":
        vals = dict(inputs) if hasattr(inputs, "keys") else {}
        if vals.get("toss_decision") not in ("bat", "field"):
            raise ValueError(
                "stage P2 requires toss_decision in {'bat', 'field'}, "
                f"got {vals.get('toss_decision')!r}")


def p2_probability(p1: float, team_1_name: str, team_2_name: str,
                   toss_winner_name: str, toss_decision: str,
                   chase: dict) -> float:
    """Toss-adjusted (P2) probability from a locked P1 probability.

    This is the ONLY sanctioned P1->P2 path: it validates the toss
    inputs against the stage contract before adjusting."""
    validate_stage_inputs("P2", {"toss_winner_name": toss_winner_name,
                                 "toss_decision": toss_decision})
    if toss_winner_name not in (team_1_name, team_2_name):
        raise ValueError(
            f"toss winner {toss_winner_name!r} is not one of the fixture teams")
    bat_first_team = toss_winner_name if toss_decision == "bat" else (
        team_2_name if toss_winner_name == team_1_name else team_1_name)
    return M.p2_adjust(float(p1), bat_first_team == team_1_name, chase)


def select_expected_xi(squad_priors: pd.DataFrame) -> list:
    """Strongest likely XI from priors (documented pre-season assumption).

    Score = role-weighted bat/bowl index blend. Constraints repaired in:
    at least 1 Wicketkeeper (if the squad has one) and at least 5 bowling
    options (bowl_balls_eff >= 60 or role Bowler/All-rounder). No overseas
    cap is imposed -- no sourced NPL playing-condition was found for one.
    Returns player_keys in batting-priority order.
    """
    s = squad_priors.copy()
    def score(r):
        if r["role"] == "Bowler":
            return 0.3 * r["bat_index"] + 0.7 * r["bowl_index"]
        if r["role"] == "Batter" or r["role"] == "Wicketkeeper":
            return 0.8 * r["bat_index"] + 0.2 * r["bowl_index"]
        return 0.55 * r["bat_index"] + 0.45 * r["bowl_index"]
    s["sel_score"] = s.apply(score, axis=1)
    s = s.sort_values("sel_score", ascending=False)
    xi = list(s.head(11)["player_key"])
    def is_bowling_option(r):
        return r["bowl_balls_eff"] >= 60 or r["role"] in ("Bowler", "All-rounder")
    def repair():
        cur = s[s["player_key"].isin(xi)]
        if (cur["role"] == "Wicketkeeper").sum() == 0 and (s["role"] == "Wicketkeeper").any():
            wk = s[(s["role"] == "Wicketkeeper") & (~s["player_key"].isin(xi))].iloc[0]
            drop = cur[(cur["role"] != "Wicketkeeper")].sort_values("sel_score").iloc[0]
            xi.remove(drop["player_key"]); xi.append(wk["player_key"]); return True
        cur = s[s["player_key"].isin(xi)]
        if sum(is_bowling_option(r) for _, r in cur.iterrows()) < 5:
            cand = s[(~s["player_key"].isin(xi)) & (s.apply(is_bowling_option, axis=1))]
            if len(cand):
                add = cand.iloc[0]
                drop = cur[~cur.apply(is_bowling_option, axis=1)].sort_values("sel_score").iloc[0]
                xi.remove(drop["player_key"]); xi.append(add["player_key"]); return True
        return False
    while repair():
        pass
    order = s.set_index("player_key")["sel_score"]
    return sorted(xi, key=lambda k: -order.get(k, 0))


def team_form_state(matches: pd.DataFrame):
    """Final EWMA-NRR form + last-played date per team, from completed
    matches only."""
    m = matches.copy()
    m["match_date"] = pd.to_datetime(m["match_date"])
    m = m.sort_values(["match_date", "match_id"])
    form, last = {}, {}
    for _, row in m.iterrows():
        for team in (row["team_1_name"], row["team_2_name"]):
            nrr = M.match_nrr(row, team)
            if nrr is not None:
                form[team] = nrr if team not in form else 0.75 * form[team] + 0.25 * nrr
            last[team] = row["match_date"]
    return form, last


def predict_fixture(team_1, team_2, match_date, ratings, priors_by_key,
                    xi_by_team, form, last_played, model_json) -> dict:
    xi1 = xi_by_team.get(team_1, [])
    xi2 = xi_by_team.get(team_2, [])
    by_id = {}
    # xi_strength works on registry ids; map keys -> registry ids via priors
    def reg_ids(keys):
        return [priors_by_key[k]["cricsheet_registry_id"] for k in keys
                if priors_by_key.get(k, {}).get("cricsheet_registry_id")]
    priors_by_id = {}
    for k, v in priors_by_key.items():
        rid = v.get("cricsheet_registry_id")
        if isinstance(rid, str):
            priors_by_id[rid] = v
    b1, w1 = M.xi_strength(reg_ids(xi1), priors_by_id)
    b2, w2 = M.xi_strength(reg_ids(xi2), priors_by_id)
    r1 = ratings.get(team_1, E.INITIAL_ELO)
    r2 = ratings.get(team_2, E.INITIAL_ELO)
    p_elo = E.expected(r1, r2)
    p1 = M.blend_probability(p_elo, b1 - b2, w1 - w2)
    def rest(team):
        lp = last_played.get(team)
        if lp is None:
            return 7.0
        return min(14.0, float((pd.Timestamp(match_date) - lp).days))
    feats = {
        "elo_diff": (r1 - r2) / 100.0,
        "xi_batting_diff": b1 - b2,
        "xi_bowling_diff": w1 - w2,
        "form_nrr_diff": form.get(team_1, 0.0) - form.get(team_2, 0.0),
        "rest_diff": (rest(team_1) - rest(team_2)) / 7.0,
    }
    # P1 contract enforcement: the feature set computed here must not
    # contain any toss field (review fix R2a). Raises if it ever does.
    validate_stage_inputs("P1", feats)
    assert set(feats) == set(M.FEATURES_P1)
    p_log = float(M.predict_raw(model_json, pd.DataFrame([feats]))[0]) if model_json else None
    return {"team_1_name": team_1, "team_2_name": team_2,
            "rating_1": round(r1, 1), "rating_2": round(r2, 1),
            "p_elo": round(p_elo, 4), "p_team_1_win": round(p1, 4),
            "p_logistic_challenger": round(p_log, 4) if p_log is not None else None,
            "xi_1": xi1, "xi_2": xi2, "features": feats}


def load_context(root: Path):
    root = Path(root)
    matches = pd.read_parquet(root / "data/normalized/matches_normalized.parquet")
    priors = pd.read_csv(root / "data/predictions/player_priors.csv")
    priors_by_key = {r.player_key: r._asdict() for r in priors.itertuples()}
    hist = E.compute_history(matches)
    ratings = E.final_ratings(hist)
    fixtures = pd.read_csv(root / "data/fixtures/s3_fixtures.csv")
    latest_season = sorted(matches["season"].unique())[-1]
    if len(fixtures) and fixtures["season"].iloc[0] != latest_season:
        ratings = E.regress(ratings, E.DEFAULT_SEASON_REGRESSION)
    form, last_played = team_form_state(matches)
    xi_by_team = {}
    for team, squad in priors.groupby("team"):
        xi_by_team[team] = select_expected_xi(squad)
    model_json = None
    mj = root / "data/predictions/model_v1.json"
    if mj.exists():
        model_json = json.loads(mj.read_text())
    return {"matches": matches, "ratings": ratings, "priors": priors,
            "priors_by_key": priors_by_key, "xi_by_team": xi_by_team,
            "form": form, "last_played": last_played, "model": model_json,
            "fixtures": fixtures}


def generate_predictions(root: Path) -> pd.DataFrame:
    ctx = load_context(root)
    rows = []
    for _, fx in ctx["fixtures"].iterrows():
        if not isinstance(fx["team_1_name"], str) or not fx["team_1_name"]:
            continue  # playoff fixtures: teams TBA
        pred = predict_fixture(fx["team_1_name"], fx["team_2_name"], fx["match_date"],
                               ctx["ratings"], ctx["priors_by_key"], ctx["xi_by_team"],
                               ctx["form"], ctx["last_played"], ctx["model"])
        rows.append({"match_id": fx["match_id"], "match_date": fx["match_date"],
                     "stage_fixture": fx["stage"], **{k: v for k, v in pred.items()
                     if k not in ("xi_1", "xi_2", "features")},
                     "xi_1_keys": ";".join(pred["xi_1"]), "xi_2_keys": ";".join(pred["xi_2"]),
                     "features_json": json.dumps(pred["features"])})
    return pd.DataFrame(rows)


def lock_predictions(root: Path, preds: pd.DataFrame, stage: str) -> int:
    """Append predictions to the frozen log. Refuses duplicates of
    (match_id, stage) -- a locked prediction is never rewritten."""
    if stage not in STAGE_INPUTS:
        raise ValueError(f"unknown prediction stage: {stage!r}")
    root = Path(root)
    path = root / "data/predictions/frozen_log.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = pd.read_csv(path) if path.exists() else pd.DataFrame(columns=FROZEN_FIELDS)
    locked = {(r.match_id, r.stage) for r in existing.itertuples()} if len(existing) else set()
    now = datetime.now(timezone.utc).isoformat()
    new_rows = []
    for _, p in preds.iterrows():
        if (p["match_id"], stage) in locked:
            continue
        new_rows.append({
            "match_id": p["match_id"], "season": "S3", "stage": stage,
            "timestamp_locked": now, "model_version": MODEL_VERSION,
            "team_1_name": p["team_1_name"], "team_2_name": p["team_2_name"],
            "p_team_1_win": p["p_team_1_win"], "p_elo": p["p_elo"],
            "p_logistic_challenger": p.get("p_logistic_challenger"),
            "features_json": p["features_json"],
        })
    if new_rows:
        out = pd.concat([existing, pd.DataFrame(new_rows)], ignore_index=True)
        out.to_csv(path, index=False)
    return len(new_rows)
