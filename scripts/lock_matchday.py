#!/usr/bin/env python
"""Matchday capture: lock P1_post_XI (announced XI) and P2_post_toss.

The biggest real accuracy lever available to this system is replacing
expected XIs with the ANNNOUNCED XIs. Workflow (docs/PREDICTION_SYSTEM.md):

  XI announced (~30-60 min pre-match)
    -> fill data/matchday xi.csv -> python scripts/lock_matchday.py --xi-csv ...
    -> locks stage 'P1_post_XI', model_version 'v1.1' (temperature-
       calibrated champion blend; the locked v1 pre-season rows are
       never touched)
  Toss (~15 min pre-match)
    -> toss.csv -> python scripts/lock_matchday.py --toss-csv ...
    -> locks stage 'P2_post_toss' via engine.p2_probability, adjusting
       the locked P1_post_XI when present, else the pre-season P1
  First ball = freeze.

Validation: exactly 11 players per team; every player must be in that
team's squad in player_master.csv (by player_key or exact canonical
name); no duplicates; batting positions unique 1..11 per team.
OVERSEAS CAP: no check -- no NPL playing-conditions rule for an XI
overseas cap was verified from an opened source during this build, so
none is enforced (see data/matchday/README.md).

--dry-run: compute + print, and write any locks to a temp directory
(the production frozen log is never written in dry-run mode).
--make-example-xi MATCH_ID: write a starter xi.csv (from the expected-
XI selector) to the given --out path or stdout.
"""
import argparse
import json
import sys
import tempfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.prediction import engine  # noqa: E402
from src.prediction import model as M  # noqa: E402
from src.prediction import stages as STAGES  # noqa: E402

MODEL_VERSION_V11 = "v1.1"


# ---------------------------------------------------------------- XI input
def resolve_players(df: pd.DataFrame, master: pd.DataFrame) -> pd.DataFrame:
    """Map the 'player' column (player_key or canonical name) to
    player_key; raise on anything unresolvable."""
    by_key = set(master["player_key"])
    by_name = dict(zip(master["canonical_name"], master["player_key"]))
    out = df.copy()

    def res(v):
        if v in by_key:
            return v
        if v in by_name:
            return by_name[v]
        raise ValueError(f"player not found in player master: {v!r} "
                         f"(use player_key or exact canonical name)")
    out["player_key"] = out["player"].map(res)
    return out


def validate_xi(xi: pd.DataFrame, fixture: pd.Series,
                master: pd.DataFrame) -> dict:
    """Validate a resolved XI frame for ONE fixture. Returns
    {team: [player_key, ...]} in batting order. Raises ValueError on
    any contract violation."""
    teams = [fixture["team_1_name"], fixture["team_2_name"]]
    squad = {t: set(g["player_key"])
             for t, g in master.groupby("team")}
    result = {}
    for team in teams:
        sub = xi[xi["team"] == team]
        if len(sub) != 11:
            raise ValueError(f"{team}: XI must have exactly 11 players, "
                             f"got {len(sub)}")
        if sub["player_key"].duplicated().any():
            dup = sub[sub["player_key"].duplicated()]["player_key"].tolist()
            raise ValueError(f"{team}: duplicate players in XI: {dup}")
        outside = [p for p in sub["player_key"] if p not in squad.get(team, set())]
        if outside:
            raise ValueError(f"{team}: players not in this team's squad "
                             f"(player_master): {outside}")
        pos = pd.to_numeric(sub["batting_position"], errors="coerce")
        if pos.isna().any() or sorted(pos.astype(int)) != list(range(1, 12)):
            raise ValueError(f"{team}: batting_position must be 1..11, unique")
        result[team] = list(sub.assign(_p=pos.astype(int))
                            .sort_values("_p")["player_key"])
    extra = set(xi["team"]) - set(teams)
    if extra:
        raise ValueError(f"XI contains teams not in the fixture: {sorted(extra)}")
    return result


def load_xi_csv(path, fixtures: pd.DataFrame, master: pd.DataFrame):
    """Returns {match_id: {team: [player_key x11 in batting order]}}."""
    df = pd.read_csv(path)
    df = resolve_players(df, master)
    out = {}
    for mid, g in df.groupby("match_id"):
        fx = fixtures[fixtures["match_id"] == mid]
        if not len(fx):
            raise ValueError(f"unknown match_id in XI csv: {mid!r}")
        out[mid] = validate_xi(g, fx.iloc[0], master)
    return out


# ---------------------------------------------------------------- locking
def compute_p1_post_xi(root: Path, match_id: str, xi_by_team: dict,
                       ctx=None) -> dict:
    """v1.1 (temperature-calibrated) P1 for one fixture from the
    ANNOUNCED XI. Returns a one-row prediction frame for locking."""
    ctx = ctx or engine.load_context(root)
    fx = ctx["fixtures"][ctx["fixtures"]["match_id"] == match_id]
    if not len(fx):
        raise ValueError(f"unknown match_id: {match_id!r}")
    fx = fx.iloc[0]
    engine.validate_stage_inputs(
        "P1_post_XI", {"announced_xi": xi_by_team, **{f: 0 for f in M.FEATURES_P1}})
    xi_ctx = dict(ctx["xi_by_team"])
    xi_ctx[fx["team_1_name"]] = xi_by_team[fx["team_1_name"]]
    xi_ctx[fx["team_2_name"]] = xi_by_team[fx["team_2_name"]]
    pred = engine.predict_fixture(fx["team_1_name"], fx["team_2_name"],
                                  fx["match_date"], ctx["ratings"],
                                  ctx["priors_by_key"], xi_ctx, ctx["form"],
                                  ctx["last_played"], ctx["model"])
    p_cal = float(M.apply_temperature(pred["p_team_1_win"], M.TEMPERATURE_V1_1))
    feats = dict(pred["features"])
    # Ratings basis (Amendment #6): the Elo input comes from the
    # engine context, which is provisional-aware -- winner-only
    # manual results (MOV = 1.0) advance ratings for played fixtures
    # cricsheet has not published yet. The basis is recorded on the
    # locked row so a lock made on provisional state is identifiable
    # forever; with no provisional rows it is "canonical".
    pinfo = ctx.get("provisional_info") or {}
    feats.update({"xi_source": "announced", "model_version": MODEL_VERSION_V11,
                  "temperature_T": M.TEMPERATURE_V1_1,
                  "p_v1_uncalibrated": pred["p_team_1_win"],
                  "ratings_basis": pinfo.get("ratings_basis", "canonical"),
                  "n_provisional_applied":
                      pinfo.get("n_provisional_applied", 0),
                  "data_as_of": pinfo.get("data_as_of")})
    return pd.DataFrame([{
        "match_id": match_id, "team_1_name": fx["team_1_name"],
        "team_2_name": fx["team_2_name"], "p_team_1_win": round(p_cal, 4),
        "p_elo": pred["p_elo"],
        "p_logistic_challenger": pred["p_logistic_challenger"],
        "features_json": json.dumps(feats)}])


def compute_p2_post_toss(root: Path, match_id: str, toss_winner: str,
                         toss_decision: str, log_root: Path | None = None) -> pd.DataFrame:
    """P2 for one fixture: adjusts the locked P1_post_XI when present,
    else the locked pre-season P1 (base stage recorded in features)."""
    log_root = log_root or root
    log_path = log_root / "data/predictions/frozen_log.csv"
    if not log_path.exists():
        raise ValueError("no frozen log found -- lock a P1 first")
    log = pd.read_csv(log_path)
    rows = log[log["match_id"] == match_id]
    base = None
    # Base-stage preference, resolved through the canonical registry
    # (G1): confirmed-XI lock (P1_CONFIRMED_XI) first, then the
    # pre-season lock (P0_PRESEASON), then the bare contract alias.
    for stage in (STAGES.stored_stage("P1_CONFIRMED_XI"),
                  STAGES.stored_stage("P0_PRESEASON"), "P1"):
        cand = rows[rows["stage"] == stage]
        if len(cand):
            base = cand.iloc[0]
            base_stage = stage
            break
    if base is None:
        raise ValueError(f"no locked P1 for {match_id} to adjust")
    chase = json.loads((root / "data/predictions/model_v1.json").read_text())["chase"]
    p2 = engine.p2_probability(float(base["p_team_1_win"]), base["team_1_name"],
                               base["team_2_name"], toss_winner, toss_decision, chase)
    feats = {"base_stage": base_stage, "base_p": float(base["p_team_1_win"]),
             "toss_winner_name": toss_winner, "toss_decision": toss_decision,
             "model_version": MODEL_VERSION_V11}
    return pd.DataFrame([{
        "match_id": match_id, "team_1_name": base["team_1_name"],
        "team_2_name": base["team_2_name"], "p_team_1_win": round(p2, 4),
        "p_elo": base["p_elo"], "p_logistic_challenger": base["p_logistic_challenger"],
        "features_json": json.dumps(feats)}])


def make_example_xi(root: Path, match_id: str) -> pd.DataFrame:
    ctx = engine.load_context(root)
    fx = ctx["fixtures"][ctx["fixtures"]["match_id"] == match_id].iloc[0]
    master = pd.read_csv(root / "data/predictions/player_master.csv")
    name_of = dict(zip(master["player_key"], master["canonical_name"]))
    rows = []
    for team in (fx["team_1_name"], fx["team_2_name"]):
        for i, key in enumerate(ctx["xi_by_team"][team], start=1):
            rows.append({"match_id": match_id, "team": team,
                         "player": name_of.get(key, key), "batting_position": i})
    return pd.DataFrame(rows)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--xi-csv")
    ap.add_argument("--toss-csv")
    ap.add_argument("--make-example-xi", metavar="MATCH_ID")
    ap.add_argument("--out")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if args.make_example_xi:
        df = make_example_xi(ROOT, args.make_example_xi)
        if args.out:
            df.to_csv(args.out, index=False)
            print(f"example XI -> {args.out}")
        else:
            print(df.to_csv(index=False))
        sys.exit(0)

    log_root = Path(tempfile.mkdtemp(prefix="matchday_dryrun_")) if args.dry_run else ROOT
    if args.dry_run:
        # dry-run locks go to a temp tree; seed it with the real log so
        # duplicate/stage logic and the P2 base lookup behave exactly
        # as in production, without writing to production.
        import shutil
        dest = log_root / "data/predictions"
        dest.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / "data/predictions/frozen_log.csv",
                    dest / "frozen_log.csv")
        print(f"[dry-run] locks will go to {log_root} (production log untouched)")

    master = pd.read_csv(ROOT / "data/predictions/player_master.csv")
    fixtures = pd.read_csv(ROOT / "data/fixtures/s3_fixtures.csv")

    if args.xi_csv:
        xis = load_xi_csv(args.xi_csv, fixtures, master)
        ctx = engine.load_context(ROOT)
        for mid, xi_by_team in xis.items():
            frame = compute_p1_post_xi(ROOT, mid, xi_by_team, ctx=ctx)
            # Canonical horizon P1_CONFIRMED_XI, written under its
            # existing stored string (registry, G1) — locked rows keep
            # the stage strings they have always used.
            n = engine.lock_predictions(
                log_root, frame, STAGES.stored_stage("P1_CONFIRMED_XI"),
                model_version=MODEL_VERSION_V11)
            print(f"{mid}: P1_post_XI p_team_1_win="
                  f"{frame.iloc[0]['p_team_1_win']} (locked {n})")
    if args.toss_csv:
        toss = pd.read_csv(args.toss_csv)
        for _, t in toss.iterrows():
            frame = compute_p2_post_toss(ROOT, t["match_id"], t["toss_winner"],
                                         t["decision"], log_root=log_root)
            # Canonical horizon P2_POST_TOSS under its stored string.
            n = engine.lock_predictions(
                log_root, frame, STAGES.stored_stage("P2_POST_TOSS"),
                model_version=MODEL_VERSION_V11)
            print(f"{t['match_id']}: P2_post_toss p_team_1_win="
                  f"{frame.iloc[0]['p_team_1_win']} (locked {n})")

    if not args.dry_run and (args.xi_csv or args.toss_csv):
        # Keep the ledger manifest current after a lock event
        # (scripts/build_ledger_manifest.py). Best-effort ONLY: a
        # manifest failure must never block or taint a lock.
        try:
            import subprocess
            subprocess.run([sys.executable,
                            str(ROOT / "scripts/build_ledger_manifest.py")],
                           check=True, capture_output=True, text=True)
            print("ledger manifest regenerated")
        except Exception as exc:  # noqa: BLE001 - warning only, by design
            print(f"WARNING: ledger manifest regeneration failed ({exc}); "
                  f"locks are unaffected. Re-run "
                  f"scripts/build_ledger_manifest.py manually.")
