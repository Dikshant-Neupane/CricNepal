"""Canonical KPI calculations used across dashboard pages."""

from __future__ import annotations

import pandas as pd

COMPETITION_WEIGHTS = {
    "NPL Season 2": 0.50,
    "KP Oli Cup": 0.30,
    "NPL Season 1": 0.15,
    "President Cup": 0.05,
}


def _result_points(result: str) -> float:
    if result == "W":
        return 1.0
    if result == "NR":
        return 0.5
    return 0.0


def _run_rate(runs: float, overs: float) -> float:
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


def compute_weighted_form_index(df: pd.DataFrame) -> float:
    """Compute quality-adjusted form index using competition weights."""
    if df.empty:
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
    """Compute win percentage for a specific season label."""
    season_df = df[df["season"] == season]
    if season_df.empty:
        return 0.0
    return round((season_df["result"] == "W").mean() * 100.0, 1)


def build_executive_cards(df: pd.DataFrame) -> list[tuple[str, str, str, str]]:
    """Build metric card payload for executive overview page."""
    kpis = compute_team_kpis(df)
    weighted_form = compute_weighted_form_index(df)

    s1_win_pct = compute_season_win_pct(df, "S1")
    s2_win_pct = compute_season_win_pct(df, "S2")
    season_delta = round(s1_win_pct - s2_win_pct, 1)

    delta_prefix = "+" if season_delta >= 0 else ""
    trend_prefix = "+" if kpis["nrr"] >= 0 else ""

    cards = [
        ("Win %", f"{kpis['win_pct']:.1f}%", f"{delta_prefix}{season_delta:.1f}% S1 vs S2", ""),
        ("NRR", f"{kpis['nrr']:+.3f}", f"{trend_prefix}{kpis['nrr']:.3f} net trend", ""),
        ("Matches", str(kpis["matches"]), f"W {kpis['wins']} / L {kpis['losses']}", ""),
        ("Form Index", f"{weighted_form:.1f}", "Quality-adjusted", ""),
    ]

    return cards
