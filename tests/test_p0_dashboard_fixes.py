"""P0 dashboard fixes (2026-10-24 QA pass).

1. Dashboard top contributors were ranked from league-wide recruiting
   forecast exports with no team filter — other teams' players (Rossington,
   Bohara) were presented as Janakpur contributors.
2. Season NRR displayed +0.000 for both seasons: matches.parquet innings
   summaries are all NaN, so the loader defaulted runs to 0 / overs to 20.
3. Match Review crashed with KeyError 'result' (summary builder omitted
   the key and hardcoded scores) and was not linked in the sidebar.
"""
import pandas as pd
import pytest


def test_nrr_backfilled_from_ball_by_ball():
    from src.dashboard.services.data_source import load_match_records
    from src.dashboard.services.metrics import compute_season_kpis

    df, _ = load_match_records()
    assert (df["runs_for"] > 0).all()
    kpis = compute_season_kpis(df)
    # Hand-computed from ball_by_ball.parquet (legal-ball overs, all-out
    # innings counted as 20 overs, super overs excluded).
    assert kpis["S1"]["nrr"] == pytest.approx(0.139, abs=0.01)
    assert kpis["S2"]["nrr"] == pytest.approx(-0.443, abs=0.01)


def test_top_contributors_are_janakpur_only():
    from src.config.paths import PARQUET_DIR
    from src.dashboard.page_modules.executive_overview import _top_contributors

    lineups = pd.read_parquet(PARQUET_DIR / "match_lineups.parquet")
    matches = pd.read_parquet(
        PARQUET_DIR / "matches.parquet", columns=["match_id", "season"]
    )
    lineups = lineups.merge(matches, on="match_id", how="left")
    squad = set(
        lineups[
            (lineups["team_name"] == "Janakpur Bolts")
            & (lineups["season"] == "S2")
        ]["player_name"]
    )
    batting, bowling = _top_contributors("S2")
    assert batting and bowling
    for row in batting + bowling:
        assert row["player_name"] in squad
    # Verified against ball-by-ball: Krishnamurthi is Janakpur's real top
    # S2 scorer; Rossington (Pokhara) and Bohara (Sudur Paschim) must not
    # appear at all.
    assert batting[0]["player_name"] == "SP Krishnamurthi"
    assert int(batting[0]["runs"]) == 167
    names = {r["player_name"] for r in batting + bowling}
    assert "AM Rossington" not in names
    assert "A Bohara" not in names


def test_match_review_summary_contract():
    from src.dashboard.page_modules.match_review import (
        _build_match_summary,
        _load_real_matches,
    )

    matches = _load_real_matches()
    assert matches is not None and not matches.empty
    summary = _build_match_summary(matches.iloc[0])
    assert "result" in summary and "won" in summary["result"]
    assert summary["team1"]["score"] != "—"
    assert summary["team1"]["rr"] != "—"  # was hardcoded "—" before the fix
    assert summary["team1"]["is_winner"] != summary["team2"]["is_winner"]


def test_match_review_in_nav_and_renders():
    from src.dashboard.config.nav_config import FROZEN_NAV_ITEMS, NAV_ITEMS

    # Reachable in the live nav, or deliberately frozen for the Season 3
    # showcase — never silently orphaned (the original bug).
    assert any(item["key"] == "review" for item in NAV_ITEMS + FROZEN_NAV_ITEMS)

    from pathlib import Path

    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(Path(__file__).parent.parent / "app.py"))
    at.session_state["active_page"] = "review"
    at.run(timeout=180)
    assert len(at.exception) == 0
