"""Data source helpers for dashboard metrics and validation."""

from __future__ import annotations

import pandas as pd

from src.dashboard.demo_data import get_season_match_records


def _empty_result(columns: list[str]) -> pd.DataFrame:
    return pd.DataFrame(columns=columns)


def _load_from_database() -> pd.DataFrame:
    """Load match-level records from the project database when available."""
    query = """
    WITH jb AS (
        SELECT team_id
        FROM teams
        WHERE LOWER(name) LIKE '%janakpur%'
        ORDER BY team_id
        LIMIT 1
    ),
    match_totals AS (
        SELECT
            m.match_id,
            m.season_id,
            m.match_number,
            m.match_winner_id,
            m.win_type,
            MAX(CASE WHEN i.batting_team_id = jb.team_id THEN i.total_runs END) AS runs_for,
            MAX(CASE WHEN i.batting_team_id <> jb.team_id THEN i.total_runs END) AS runs_against,
            MAX(CASE WHEN i.batting_team_id = jb.team_id THEN i.total_overs END) AS overs_faced,
            MAX(CASE WHEN i.batting_team_id <> jb.team_id THEN i.total_overs END) AS overs_bowled
        FROM matches m
        JOIN innings i ON i.match_id = m.match_id
        CROSS JOIN jb
        WHERE m.team1_id = jb.team_id OR m.team2_id = jb.team_id
        GROUP BY m.match_id, m.season_id, m.match_number, m.match_winner_id, m.win_type
    )
    SELECT
        CASE
            WHEN s.name ILIKE '%season 1%' THEN 'S1'
            WHEN s.name ILIKE '%season 2%' THEN 'S2'
            ELSE COALESCE(s.name, CAST(s.year AS TEXT))
        END AS season,
        c.name AS competition_name,
        CASE
            WHEN c.name ILIKE '%npl%' THEN 'A'
            WHEN c.name ILIKE '%kp oli%' THEN 'B'
            ELSE 'C'
        END AS competition_tier,
        'balanced'::TEXT AS opposition_strength_bucket,
        CASE
            WHEN mt.match_number IS NOT NULL AND mt.match_number >= 30 THEN 'high-pressure'
            ELSE 'league'
        END AS match_context,
        CASE
            WHEN mt.win_type IN ('no result', 'tie') THEN 'NR'
            WHEN mt.match_winner_id = jb.team_id THEN 'W'
            ELSE 'L'
        END AS result,
        COALESCE(mt.runs_for, 0)::FLOAT AS runs_for,
        COALESCE(mt.runs_against, 0)::FLOAT AS runs_against,
        COALESCE(mt.overs_faced, 0)::FLOAT AS overs_faced,
        COALESCE(mt.overs_bowled, 0)::FLOAT AS overs_bowled
    FROM match_totals mt
    JOIN seasons s ON s.season_id = mt.season_id
    JOIN competitions c ON c.competition_id = s.competition_id
    CROSS JOIN jb
    ORDER BY s.year, season;
    """

    from sqlalchemy import text

    # Lazy import avoids hard failure when DB env vars are missing.
    from src.db.connection import get_db

    with get_db() as db:
        rows = db.execute(text(query)).mappings().all()

    if not rows:
        return _empty_result(
            [
                "season",
                "competition_name",
                "competition_tier",
                "opposition_strength_bucket",
                "match_context",
                "result",
                "runs_for",
                "runs_against",
                "overs_faced",
                "overs_bowled",
            ]
        )

    return pd.DataFrame(rows)


def load_match_records() -> tuple[pd.DataFrame, str]:
    """Return match records and source tag (database or demo)."""
    try:
        db_df = _load_from_database()
        if not db_df.empty:
            return db_df, "database"
    except Exception:
        # Fall back to demo data until DB and ingestion are ready.
        pass

    return get_season_match_records(), "demo"
