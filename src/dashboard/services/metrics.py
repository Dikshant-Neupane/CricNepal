"""Canonical KPI calculations used across dashboard pages."""

from __future__ import annotations

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


def compute_team_kpis(df: pd.DataFrame) -> dict:
    """Compute normalized team KPIs from match-level records."""
    matches = len(df)
    wins = int((df["result"] == "W").sum())
    losses = int((df["result"] == "L").sum())
    no_results = int((df["result"] == "NR").sum())

    win_pct = (wins / matches * 100.0) if matches else 0.0

    total_for = float(df["runs_for"].sum())
    total_against = float(df["runs_against"].sum())
    overs_for = float(df["overs_faced"].sum())
    overs_against = float(df["overs_bowled"].sum())

    nrr = _run_rate(total_for, overs_for) - _run_rate(total_against, overs_against)

    return {
        "matches": matches,
        "wins": wins,
        "losses": losses,
        "no_results": no_results,
        "win_pct": round(win_pct, 1),
        "nrr": round(nrr, 3),
        "avg_runs_for": round(total_for / matches, 1) if matches else 0.0,
        "avg_runs_against": round(total_against / matches, 1) if matches else 0.0,
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
        - nrr: net run rate
    """
    result = {}
    
    if df.empty or "season" not in df.columns:
        return result
    
    for season, grp in df.groupby("season"):
        n = len(grp)
        wins = int((grp["result"] == "W").sum())
        losses = n - wins
        win_pct = (wins / n * 100.0) if n > 0 else 0.0

        # Calculate NRR using runs and overs columns
        runs_for = pd.to_numeric(grp["runs_for"], errors="coerce").fillna(0)
        runs_against = pd.to_numeric(grp["runs_against"], errors="coerce").fillna(0)
        overs_faced = pd.to_numeric(grp["overs_faced"], errors="coerce").fillna(20.0).replace(0, 20.0)
        overs_bowled = pd.to_numeric(grp["overs_bowled"], errors="coerce").fillna(20.0).replace(0, 20.0)
        
        # NRR: (runs_for/overs_faced) - (runs_against/overs_bowled)
        total_for = runs_for.sum()
        total_against = runs_against.sum()
        total_overs_faced = overs_faced.sum()
        total_overs_bowled = overs_bowled.sum()
        
        nrr = _run_rate(total_for, total_overs_faced) - _run_rate(total_against, total_overs_bowled)

        result[season] = {
            "n": n,
            "wins": wins,
            "losses": losses,
            "win_pct": round(win_pct, 1),
            "nrr": round(nrr, 3),
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
    nrr_delta = s2.get("nrr", 0.0) - s1.get("nrr", 0.0)
    matches_delta = s2.get("n", 0) - s1.get("n", 0)
    
    return {
        "win_pct_delta": round(win_pct_delta, 1),
        "nrr_delta": round(nrr_delta, 3),
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
    trend_prefix = "+" if kpis["nrr"] >= 0 else ""

    cards = [
        ("Win %", f"{kpis['win_pct']:.1f}%", f"{delta_prefix}{season_delta:.1f}% S2 vs S1", ""),
        ("NRR", f"{kpis['nrr']:+.3f}", f"{trend_prefix}{kpis['nrr']:.3f} net trend", ""),
        ("Matches", str(kpis["matches"]), f"W {kpis['wins']} / L {kpis['losses']}", ""),
        ("Form Index", f"{weighted_form:.1f}", "Quality-adjusted", ""),
    ]

    return cards
