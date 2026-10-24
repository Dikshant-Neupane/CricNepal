#!/usr/bin/env python
"""Cross-league architecture check (Phase 2, Task A6).

Runs the SAME architecture as the NPL model -- canonical Elo
(src/prediction/elo.py compute_history) + champion blend
(src/prediction/model.py blend_probability over priors-based XI
strength, priors from src/prediction/priors.py) -- walk-forward on
ONE other cricsheet league's most recent season, reporting
log-loss / Brier / accuracy for the blend vs the higher-Elo baseline
vs the coin. Architecture sanity outside the NPL; NOT a new NPL claim.

Basis differences vs the NPL setup (also recorded in the output):
- XI basis = ACTUAL XIs (post-hoc, from the scorecards' info.players);
- priors use that league's own history only, walk-forward as-of each
  match (aggregate_cricsheet with ref_date = match date), translated
  at the league's own COMPETITIONS factor against its own means
  (compute_priors' no-NPL reference branch);
- every player is 'external_pro' relative to the NPL reference, so
  prior uncertainties carry the x1.5 group multiplier -- uncertainty
  is not used by the blend, so this does not affect the numbers.
"""
import argparse
import json
import sys
import zipfile
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
SCRATCH = Path.home() / "workspace/.scratch/predbuild"
sys.path.insert(0, str(ROOT))
from src.prediction import elo as E  # noqa: E402
from src.prediction import model as M  # noqa: E402
from src.prediction import priors as P  # noqa: E402
from src.prediction.metrics import accuracy, brier, log_loss  # noqa: E402

BUNDLES = {label: fname for fname, (label, _t) in P.COMPETITIONS.items()
           if label not in ("NPL", "T20I")}


def parse_bundle(zip_path: Path):
    matches, lineups = [], {}
    with zipfile.ZipFile(zip_path) as z:
        for name in z.namelist():
            if not name.endswith(".json") or "info" in name:
                continue
            try:
                d = json.loads(z.read(name))
            except Exception:
                continue
            info = d.get("info", {})
            teams = info.get("teams", [])
            if len(teams) != 2 or not info.get("dates"):
                continue
            mid = Path(name).stem
            totals = []
            for inn in d.get("innings", []):
                tot = sum(dlv["runs"]["total"]
                          for ov in inn.get("overs", [])
                          for dlv in ov.get("deliveries", []))
                totals.append(tot)
            outcome = info.get("outcome", {})
            matches.append({
                "match_id": mid,
                "match_date": info["dates"][0],
                "season": str(info.get("season", "")),
                "team_1_name": teams[0], "team_2_name": teams[1],
                "winner_name": outcome.get("winner"),
                "result_status": ("tie" if outcome.get("result") == "tie"
                                  else "completed"),
                "innings_1_runs": totals[0] if len(totals) > 0 else None,
                "innings_2_runs": totals[1] if len(totals) > 1 else None})
            people = info.get("registry", {}).get("people", {})
            listed = {t: [people[p] for p in players if p in people]
                      for t, players in info.get("players", {}).items()}
            if all(len(v) == 11 for v in listed.values()):
                lineups[mid] = listed
            else:
                # Impact-player-era scorecards list 12 names; fall back
                # to the effective XI = players who actually batted
                # (for their team) or bowled (against it).
                part = {t: set() for t in teams}
                for inn in d.get("innings", []):
                    bat_team = inn.get("team")
                    bowl_team = [t for t in teams if t != bat_team][0]
                    for ov in inn.get("overs", []):
                        for dlv in ov.get("deliveries", []):
                            if dlv.get("batter") in people:
                                part[bat_team].add(people[dlv["batter"]])
                            if dlv.get("bowler") in people:
                                part[bowl_team].add(people[dlv["bowler"]])
                lineups[mid] = {t: sorted(part[t]) for t in teams}
    return pd.DataFrame(matches), lineups


def run(league: str) -> dict:
    zip_path = SCRATCH / BUNDLES[league]
    matches, lineups = parse_bundle(zip_path)
    matches["match_date"] = pd.to_datetime(matches["match_date"])
    matches = matches.sort_values(["match_date", "match_id"]).reset_index(drop=True)
    seasons = sorted(matches["season"].unique())
    target = seasons[-1]
    season_matches = matches[matches["season"] == target]
    history = E.compute_history(matches).set_index("match_id")

    ids = sorted({pid for lu in lineups.values()
                  for players in lu.values() for pid in players})
    team_of = {}
    for _, m in matches.iterrows():
        for t, players in lineups.get(m["match_id"], {}).items():
            for pid in players:
                team_of[pid] = t
    master = pd.DataFrame({
        "player_key": ids, "cricsheet_registry_id": ids,
        "canonical_name": ids,
        "team": [team_of.get(i, "") for i in ids], "role": "Batter"})

    agg_cache: dict[date, pd.DataFrame] = {}
    rows = []
    for _, fx in season_matches.iterrows():
        mid = fx["match_id"]
        if fx["winner_name"] not in (fx["team_1_name"], fx["team_2_name"]):
            continue
        lu = lineups.get(mid, {})
        xi1, xi2 = lu.get(fx["team_1_name"], []), lu.get(fx["team_2_name"], [])
        # Effective XI: 11 listed, or 11-12 actual participants in the
        # impact-player era (the substitute genuinely played).
        if len(xi1) not in (11, 12) or len(xi2) not in (11, 12):
            continue
        mdate = fx["match_date"].date()
        if mdate not in agg_cache:
            agg_cache[mdate] = P.aggregate_cricsheet(
                {zip_path: league}, ref_date=mdate,
                cutoff=mdate - timedelta(days=3 * 365))
        priors = P.compute_priors(agg_cache[mdate], master)
        p_by = {r["cricsheet_registry_id"]: r.to_dict()
                for _, r in priors.iterrows()}
        s1 = M.xi_strength(xi1, p_by)
        s2 = M.xi_strength(xi2, p_by)
        p_elo = float(history.loc[mid, "expected_team_1"])
        rows.append({"match_id": mid,
                     "p_blend": M.blend_probability(p_elo, s1[0] - s2[0],
                                                    s1[1] - s2[1]),
                     "p_elo": p_elo,
                     "y": int(fx["winner_name"] == fx["team_1_name"])})
    df = pd.DataFrame(rows)
    out = {"league": league, "bundle": BUNDLES[league],
           "target_season": target,
           "n_prior_matches_all_seasons": int(len(matches) - len(season_matches)),
           "n_target_season_matches": int(len(season_matches)),
           "n_scored": int(len(df)),
           "xi_basis": "actual XIs (post-hoc): listed XI, or effective participants (11-12) in the impact-player era",
           "priors_basis": f"{league} history only, walk-forward as-of each match, 3y window",
           "caveats": [
               "Different league strength distribution and team count "
               "from the NPL; absolute metric levels are not comparable "
               "to NPL numbers.",
               "XI basis is post-hoc actual XIs, unlike the NPL "
               "pre-season expected-XI locks (flatters the XI channel).",
               "Architecture sanity only -- no NPL claim is updated."]}
    if len(df):
        for name, col in (("blend", "p_blend"), ("higher_elo", "p_elo")):
            out[name] = {"log_loss": round(log_loss(df[col], df["y"]), 4),
                         "brier": round(brier(df[col], df["y"]), 4),
                         "accuracy": round(accuracy(df[col], df["y"]), 4)}
        out["coin"] = {"log_loss": round(log_loss([0.5] * len(df), df["y"]), 4),
                       "brier": 0.25, "accuracy": None}
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--league", default="LPL", choices=sorted(BUNDLES))
    args = ap.parse_args()
    result = run(args.league)
    path = ROOT / "data/predictions/cross_league_check.json"
    path.write_text(json.dumps(result, indent=1))
    print(json.dumps(result, indent=1))
    print(f"-> {path}")
