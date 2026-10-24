"""Provisional results: winner-only manual capture bridging the
cricsheet publication lag (Pre-registration Amendment #6, 2026-10-24).

Source-of-truth policy (docs/PREDICTION_SYSTEM.md, "Provisional
results"): cricsheet is canonical. A provisional result is a
WINNER-ONLY record captured manually from an official source (CAN /
NPL official posts / broadcast) into data/results/provisional_results
.csv, with source description and capture timestamp. It exists so
in-season ratings do not sit frozen at pre-season values while
cricsheet publication lags (Season 2 measured median: 8 days).

Semantics, exactly:
- Winner only: no margin is captured (margin fields stay blank), so
  the Elo margin-of-victory multiplier for a provisional match is the
  NEUTRAL 1.0 -- a provisional win moves ratings exactly as a
  margin-free canonical win would, never more.
- Ratings including provisional results are a PURE function of
  (ingested matches, fixtures, provisional file): start from the
  canonical current ratings (the engine's load_context base: final
  history ratings, regressed once into the fixtures' season when the
  ingested data has not reached it), then apply each provisional
  result in fixture-date order using the same expected-score/update
  math as elo.compute_history with MOV = 1.0. Deterministic and
  recomputable at any time; nothing is stored incrementally.
- Reconciliation: once a fixture's match exists in the ingested
  normalized matches (matched on date + unordered team pair), its
  provisional row is IGNORED by the computation -- canonical data
  wins -- and reported as superseded. If the provisional winner
  DISAGREES with the ingested winner, that is surfaced as a
  data-quality warning in the reconciliation report (never an
  exception; it must not block the pipeline).
- Corrections: the last row in the file for a match_id is the
  effective one (record_result.py appends corrections as new rows
  marked correction_of, never edits in place).
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from . import elo as E

PROVISIONAL_PATH = Path("data/results/provisional_results.csv")
PROVISIONAL_COLUMNS = ["match_id", "winner_team_name", "margin_runs",
                       "margin_wickets", "source", "captured_at",
                       "status", "superseded_by_cricsheet",
                       "correction_of", "correction_reason"]
# Winner-only capture carries no margin information, so the Elo MOV
# multiplier for provisional matches is the neutral 1.0 by policy
# (Amendment #6). Do not "estimate" a margin here.
MOV_PROVISIONAL = 1.0


def provisional_path(root) -> Path:
    return Path(root) / PROVISIONAL_PATH


def load_provisional(root) -> pd.DataFrame:
    """Effective provisional rows (last row per match_id wins, so a
    correction row supersedes the row it corrects). Empty frame with
    the canonical columns when the file does not exist."""
    path = provisional_path(root)
    if not path.exists():
        return pd.DataFrame(columns=PROVISIONAL_COLUMNS)
    df = pd.read_csv(path, dtype=str).fillna("")
    for col in PROVISIONAL_COLUMNS:
        if col not in df.columns:
            df[col] = ""
    return df


def effective_rows(df: pd.DataFrame) -> pd.DataFrame:
    """One effective row per match_id: the last in file order."""
    if not len(df):
        return df
    return df.drop_duplicates(subset=["match_id"], keep="last")


def _ingested_index(matches: pd.DataFrame) -> dict:
    """(date, frozenset(teams)) -> ingested match row, for matching
    fixtures to their canonical (cricsheet) record once published."""
    idx = {}
    if matches is None or not len(matches):
        return idx
    m = matches.copy()
    m["match_date"] = pd.to_datetime(m["match_date"])
    for _, r in m.iterrows():
        key = (r["match_date"].date(),
               frozenset([r["team_1_name"], r["team_2_name"]]))
        idx[key] = r
    return idx


def reconcile(matches: pd.DataFrame, fixtures: pd.DataFrame,
              provisional: pd.DataFrame) -> dict:
    """Split effective provisional rows into applied / superseded and
    flag winner disagreements against ingested canonical data."""
    eff = effective_rows(provisional)
    fx = {r["match_id"]: r for _, r in fixtures.iterrows()} \
        if fixtures is not None and len(fixtures) else {}
    idx = _ingested_index(matches)
    applied, superseded, disagreements = [], [], []
    for _, row in eff.iterrows():
        mid = row["match_id"]
        f = fx.get(mid)
        if f is None:
            disagreements.append({
                "match_id": mid,
                "issue": "provisional row references unknown fixture",
                "provisional_winner": row["winner_team_name"]})
            continue
        fdate = pd.to_datetime(f["match_date"]).date()
        key = (fdate, frozenset([f["team_1_name"], f["team_2_name"]]))
        ing = idx.get(key)
        entry = {"match_id": mid, "match_date": str(fdate),
                 "winner_team_name": row["winner_team_name"],
                 "source": row.get("source", ""),
                 "captured_at": row.get("captured_at", "")}
        if ing is None:
            applied.append(entry)
        else:
            sup = dict(entry)
            sup["ingested_match_id"] = str(ing["match_id"])
            sup["ingested_winner"] = \
                None if pd.isna(ing.get("winner_name")) else ing["winner_name"]
            superseded.append(sup)
            if sup["ingested_winner"] is not None and \
                    sup["ingested_winner"] != row["winner_team_name"]:
                disagreements.append({
                    "match_id": mid,
                    "issue": "provisional winner disagrees with "
                             "ingested (cricsheet) winner",
                    "provisional_winner": row["winner_team_name"],
                    "ingested_winner": sup["ingested_winner"]})
    applied.sort(key=lambda e: (e["match_date"], e["match_id"]))
    return {"applied": applied, "superseded": superseded,
            "disagreements": disagreements}


def base_ratings(matches: pd.DataFrame, fixtures: pd.DataFrame,
                 k: float = E.DEFAULT_K,
                 season_regression: float = E.DEFAULT_SEASON_REGRESSION) -> dict:
    """Canonical current ratings -- the same base engine.load_context
    uses: final history ratings, regressed once into the fixtures'
    season when the ingested data has not reached that season."""
    hist = E.compute_history(matches, k=k, season_regression=season_regression)
    ratings = E.final_ratings(hist)
    if fixtures is not None and len(fixtures) and len(matches):
        latest_season = sorted(matches["season"].unique())[-1]
        if fixtures["season"].iloc[0] != latest_season:
            ratings = E.regress(ratings, season_regression)
    return ratings


def apply_provisional(ratings: dict, applied: list,
                      fixtures: pd.DataFrame,
                      k: float = E.DEFAULT_K) -> dict:
    """Apply reconciled provisional results (fixture-date order) to a
    ratings dict. Winner-only: MOV multiplier is MOV_PROVISIONAL (1.0,
    neutral) because no margin was captured."""
    out = dict(ratings)
    fx = {r["match_id"]: r for _, r in fixtures.iterrows()}
    for entry in applied:
        f = fx[entry["match_id"]]
        t1, t2 = f["team_1_name"], f["team_2_name"]
        winner = entry["winner_team_name"]
        if winner not in (t1, t2):
            raise ValueError(
                f"provisional winner {winner!r} is not a team in fixture "
                f"{entry['match_id']} ({t1} vs {t2})")
        loser = t2 if winner == t1 else t1
        rw = out.get(winner, E.INITIAL_ELO)
        rl = out.get(loser, E.INITIAL_ELO)
        ew = E.expected(rw, rl)
        out[winner] = rw + k * MOV_PROVISIONAL * (1.0 - ew)
        out[loser] = rl + k * MOV_PROVISIONAL * (0.0 - (1.0 - ew))
    return out


def ratings_with_provisional(matches: pd.DataFrame, fixtures: pd.DataFrame,
                             provisional: pd.DataFrame,
                             base: dict | None = None,
                             k: float = E.DEFAULT_K,
                             season_regression: float = E.DEFAULT_SEASON_REGRESSION
                             ) -> tuple[dict, dict]:
    """(ratings, info). Pure function of the three inputs.

    info carries: ratings_basis ("canonical" when no provisional
    result applies, else "canonical+provisional"),
    n_provisional_applied, applied/superseded match ids, winner
    disagreements (data-quality warnings), data_as_of (latest
    ingested match date) and latest_provisional_match_date.
    """
    if base is None:
        base = base_ratings(matches, fixtures, k=k,
                             season_regression=season_regression)
    rec = reconcile(matches, fixtures, provisional)
    ratings = apply_provisional(base, rec["applied"], fixtures, k=k) \
        if rec["applied"] else dict(base)
    dates = pd.to_datetime(matches["match_date"]) if len(matches) else []
    info = {
        "ratings_basis": "canonical+provisional" if rec["applied"]
                         else "canonical",
        "n_provisional_applied": len(rec["applied"]),
        "applied_match_ids": [e["match_id"] for e in rec["applied"]],
        "superseded_match_ids": [e["match_id"] for e in rec["superseded"]],
        "n_provisional_superseded": len(rec["superseded"]),
        "provisional_disagreements": rec["disagreements"],
        "data_as_of": str(dates.max().date()) if len(matches) else None,
        "latest_provisional_match_date":
            max((e["match_date"] for e in rec["applied"]), default=None),
    }
    return ratings, info
