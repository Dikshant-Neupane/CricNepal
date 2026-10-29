"""Canonical KPI calculations used across dashboard pages."""

from __future__ import annotations

import math

import pandas as pd
from typing import Dict, Any

COMPETITION_WEIGHTS = {
    "NPL Season 2": 0.50,
    "KP Oli Cup": 0.30,
    "NPL Season 1": 0.15,
    "President Cup": 0.05,
}


def _result_points(result: str) -> float:
    """Convert result to points (W=1.0, NR=0.5, L=0.0)."""
    if result == "W":
        return 1.0
    if result == "NR":
        return 0.5
    return 0.0


def _run_rate(runs: float, overs: float) -> float:
    """Calculate run rate safely handling division by zero."""
    if overs <= 0:
        return 0.0
    return float(runs / overs)


_NRR_COLUMNS = ("runs_for", "runs_against", "overs_faced", "overs_bowled")


def _nrr_aggregation(df: pd.DataFrame) -> tuple[float | None, int, int]:
    """Aggregate NRR over the rows that actually carry innings data.

    A row contributes only when all four NRR inputs are present and
    both overs values are positive. Rows are never repaired with
    defaults (plan 1.3 / criteria D7 — missing stays missing):

    - rows with any missing input are excluded and counted as
      ``n_missing`` (a data-quality problem);
    - rows with zero overs (no innings played, e.g. a no-result) are
      excluded and counted as ``n_no_innings`` (a legitimate absence —
      NRR conventions do not count matches with no play).

    Returns ``(nrr, n_missing, n_no_innings)``; ``nrr`` is None when
    no row contributes.
    """
    if not all(c in df.columns for c in _NRR_COLUMNS):
        return None, len(df), 0
    vals = {c: pd.to_numeric(df[c], errors="coerce") for c in _NRR_COLUMNS}
    missing = pd.concat(vals, axis=1).isna().any(axis=1)
    no_innings = ~missing & ((vals["overs_faced"] <= 0) | (vals["overs_bowled"] <= 0))
    valid = ~missing & ~no_innings
    if not bool(valid.any()):
        return None, int(missing.sum()), int(no_innings.sum())
    nrr = (
        float(vals["runs_for"][valid].sum()) / float(vals["overs_faced"][valid].sum())
        - float(vals["runs_against"][valid].sum()) / float(vals["overs_bowled"][valid].sum())
    )
    return nrr, int(missing.sum()), int(no_innings.sum())


def _data_quality(n_missing: int, n_no_innings: int) -> str:
    return "ok" if (n_missing + n_no_innings) == 0 else "incomplete"


def compute_team_kpis(df: pd.DataFrame) -> dict:
    """Compute normalized team KPIs from match-level records."""
    matches = len(df)
    wins = int((df["result"] == "W").sum())
    losses = int((df["result"] == "L").sum())
    no_results = int((df["result"] == "NR").sum())

    win_pct = (wins / matches * 100.0) if matches else 0.0

    nrr_value, n_missing, n_no_innings = _nrr_aggregation(df)
    nrr = round(nrr_value, 3) if nrr_value is not None else float("nan")

    return {
        "matches": matches,
        "wins": wins,
        "losses": losses,
        "no_results": no_results,
        "win_pct": round(win_pct, 1),
        "nrr": nrr,
        "data_quality": _data_quality(n_missing, n_no_innings),
        "nrr_missing_rows": n_missing,
        "nrr_no_innings_rows": n_no_innings,
        "nrr_excluded": n_missing + n_no_innings,
        "avg_runs_for": round(float(df["runs_for"].mean()), 1) if matches and df["runs_for"].notna().any() else 0.0,
        "avg_runs_against": round(float(df["runs_against"].mean()), 1) if matches and df["runs_against"].notna().any() else 0.0,
    }


def compute_season_kpis(df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
    """
    Calculate KPIs per season (win%, NRR, match counts).
    
    Args:
        df: DataFrame with columns: season, result, runs_for, runs_against, 
            overs_faced, overs_bowled
    
    Returns:
        Dict mapping season label to KPI dict with keys:
        - n: number of matches
        - wins: win count
        - losses: loss count
        - win_pct: win percentage
        - nrr: net run rate over the matches that carry innings data,
          or None when no match in the season does
        - data_quality: "ok" when every match contributed to NRR,
          else "incomplete"
        - nrr_missing_rows / nrr_no_innings_rows / nrr_excluded:
          how many matches were excluded from NRR, and why

    Missing runs/overs are never defaulted (plan 1.3 / criteria D7):
    previously this filled missing overs with 20.0 and missing runs
    with 0, silently pricing an unplayed or unrecorded innings as a
    full 20 overs.
    """
    result = {}

    if df.empty or "season" not in df.columns:
        return result

    for season, grp in df.groupby("season"):
        n = len(grp)
        wins = int((grp["result"] == "W").sum())
        losses = n - wins
        win_pct = (wins / n * 100.0) if n > 0 else 0.0

        nrr_value, n_missing, n_no_innings = _nrr_aggregation(grp)

        result[season] = {
            "n": n,
            "wins": wins,
            "losses": losses,
            "win_pct": round(win_pct, 1),
            "nrr": round(nrr_value, 3) if nrr_value is not None else None,
            "data_quality": _data_quality(n_missing, n_no_innings),
            "nrr_missing_rows": n_missing,
            "nrr_no_innings_rows": n_no_innings,
            "nrr_excluded": n_missing + n_no_innings,
        }

    return result


def compute_season_delta(season_kpis: Dict[str, Dict[str, Any]], 
                         s1_label: str = "S1", 
                         s2_label: str = "S2") -> Dict[str, float]:
    """
    Calculate delta between two seasons for narrative comparison.
    
    Args:
        season_kpis: Output from compute_season_kpis()
        s1_label: Season 1 label (default "S1")
        s2_label: Season 2 label (default "S2")
    
    Returns:
        Dict with delta metrics:
        - win_pct_delta: S2 - S1 win percentage
        - nrr_delta: S2 - S1 NRR
        - matches_delta: S2 - S1 match count
    """
    s1 = season_kpis.get(s1_label, {})
    s2 = season_kpis.get(s2_label, {})

    win_pct_delta = s2.get("win_pct", 0.0) - s1.get("win_pct", 0.0)
    # A season whose NRR is None (no innings data at all) has no
    # meaningful delta; a wholly absent season keeps the legacy 0.0.
    s1_nrr = s1.get("nrr", 0.0)
    s2_nrr = s2.get("nrr", 0.0)
    nrr_delta = (
        round(s2_nrr - s1_nrr, 3)
        if s1_nrr is not None and s2_nrr is not None
        else None
    )
    matches_delta = s2.get("n", 0) - s1.get("n", 0)

    return {
        "win_pct_delta": round(win_pct_delta, 1),
        "nrr_delta": nrr_delta,
        "matches_delta": matches_delta,
    }


def compute_form_index(df: pd.DataFrame, n_recent: int = 5) -> float:
    """
    Calculate recent form index (win rate over last N matches).
    
    Args:
        df: DataFrame with 'result' column
        n_recent: Number of recent matches to consider (default 5)
    
    Returns:
        Win percentage over last N matches (0-100)
    """
    if df.empty or "result" not in df.columns:
        return 0.0
    
    # Sort by match date if available, otherwise use dataframe order
    if "match_date" in df.columns:
        recent = df.sort_values("match_date").tail(n_recent)
    else:
        recent = df.tail(n_recent)
    
    if recent.empty:
        return 0.0
    
    wins = (recent["result"] == "W").sum()
    return round((wins / len(recent)) * 100.0, 1)


def compute_weighted_form_index(df: pd.DataFrame) -> float:
    """
    Compute quality-adjusted form index using competition weights.
    
    Args:
        df: DataFrame with columns: competition_name, result
    
    Returns:
        Weighted form index (0-100) based on competition tier weights
    """
    if df.empty or "competition_name" not in df.columns or "result" not in df.columns:
        return 0.0

    weighted_points = 0.0
    total_weight = 0.0

    for _, row in df.iterrows():
        weight = float(COMPETITION_WEIGHTS.get(row["competition_name"], 0.05))
        weighted_points += weight * _result_points(str(row["result"]))
        total_weight += weight

    if total_weight == 0:
        return 0.0

    return round((weighted_points / total_weight) * 100.0, 1)


def compute_season_win_pct(df: pd.DataFrame, season: str) -> float:
    """
    Compute win percentage for a specific season label.
    
    Args:
        df: DataFrame with columns: season, result
        season: Season label to filter (e.g., "S1", "S2")
    
    Returns:
        Win percentage for the specified season (0-100)
    """
    if df.empty or "season" not in df.columns or "result" not in df.columns:
        return 0.0
    
    season_df = df[df["season"] == season]
    if season_df.empty:
        return 0.0
    return round((season_df["result"] == "W").mean() * 100.0, 1)


def build_executive_cards(df: pd.DataFrame) -> list[tuple[str, str, str, str]]:
    """
    Build metric card payload for executive overview page.
    
    Args:
        df: DataFrame with match records
    
    Returns:
        List of tuples: (label, value, delta_text, trend_class)
    """
    if df.empty:
        return [
            ("Win %", "0.0%", "No data", ""),
            ("NRR", "+0.000", "No data", ""),
            ("Matches", "0", "No data", ""),
            ("Form Index", "0.0", "No data", ""),
        ]
    
    kpis = compute_team_kpis(df)
    weighted_form = compute_weighted_form_index(df)

    s1_win_pct = compute_season_win_pct(df, "S1")
    s2_win_pct = compute_season_win_pct(df, "S2")
    season_delta = round(s2_win_pct - s1_win_pct, 1)

    delta_prefix = "+" if season_delta >= 0 else ""
    nrr = kpis["nrr"]
    if isinstance(nrr, float) and math.isnan(nrr):
        # No innings data at all: show the gap, never a fake number.
        nrr_card = ("NRR", "N/A", "No innings data", "")
    else:
        trend_prefix = "+" if nrr >= 0 else ""
        nrr_note = " net trend" if kpis.get("data_quality", "ok") == "ok" else " net trend (incomplete data)"
        nrr_card = ("NRR", f"{nrr:+.3f}", f"{trend_prefix}{nrr:.3f}{nrr_note}", "")

    cards = [
        ("Win %", f"{kpis['win_pct']:.1f}%", f"{delta_prefix}{season_delta:.1f}% S2 vs S1", ""),
        nrr_card,
        ("Matches", str(kpis["matches"]), f"W {kpis['wins']} / L {kpis['losses']}", ""),
        ("Form Index", f"{weighted_form:.1f}", "Quality-adjusted", ""),
    ]

    return cards
