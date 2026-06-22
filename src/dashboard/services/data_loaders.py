"""
Centralised, cached data loaders for the Streamlit dashboard.

All dashboard pages should pull their data through this module rather than
calling `pd.read_parquet` / `pd.read_csv` directly. Two reasons:

1. **Performance.** Each Streamlit rerun (every filter change, every checkbox
   click) re-executes the page from the top. Without caching, a parquet read
   happens on every interaction. `@st.cache_data` keeps a single in-memory
   copy per process and re-uses it across pages and reruns.

2. **One source of truth for paths.** Path resolution is delegated to
   `src.config.paths`, which respects `CRIC_DATA_DIR` / `CRICNEPAL_ROOT`
   environment variables and gives clear errors when files are missing.
   Hardcoded `D:/Cric_Data/...` paths used to be sprinkled across page
   modules; this is now the only place they live.

The cache TTL is 1 hour, which is long enough to make tab-switches snappy
but short enough that re-running a script (e.g., `ridge_primary_model.py`)
will be picked up on the next visit. Pages that need a manual refresh can
call `st.cache_data.clear()` from a button.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd
import streamlit as st

from src.config.paths import (
    CRIC_DATA_DIR,
    DELIVERABLES_DIR,
    EXPORT_DIR,
    NORMALIZED_DIR,
    PARQUET_DIR,
    PROFILES_DIR,
    ROSTER_DIR,
)
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

CACHE_TTL_SECONDS = 60 * 60  # 1 hour

# Roster / profile filenames are dated; surface them as constants so the
# update path is "rename the constant" rather than "grep for the date string".
ROSTER_FILE = "npl_player_rosters_20260521.csv"
PROFILES_FILE = "enriched_players_20260521.csv"


# --------------------------------------------------------------------------- #
# Path helpers
# --------------------------------------------------------------------------- #

def _exists(p: Path) -> bool:
    try:
        return p.exists()
    except OSError:
        return False


def normalized_path(filename: str) -> Path:
    return NORMALIZED_DIR / filename


def export_path(filename: str) -> Path:
    return EXPORT_DIR / filename


def deliverable_path(filename: str) -> Path:
    return DELIVERABLES_DIR / filename


def cric_data_path(*parts: str) -> Path:
    return CRIC_DATA_DIR.joinpath(*parts)


# --------------------------------------------------------------------------- #
# Normalized parquet loaders (the canonical data the dashboard reads)
# --------------------------------------------------------------------------- #

@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def load_matches_normalized() -> Optional[pd.DataFrame]:
    """Normalized match-level parquet. Falls back to external parquet if local is missing."""
    p = normalized_path("matches_normalized.parquet")
    if _exists(p):
        return pd.read_parquet(p)
    # Fallback: attempt external Cric_Data parquet
    fallback = PARQUET_DIR / "matches.parquet"
    if _exists(fallback):
        logger.warning(
            "matches_normalized parquet not found at %s — using external fallback %s",
            p, fallback,
        )
        return pd.read_parquet(fallback)
    logger.warning("matches_normalized parquet not found at %s (no fallback available)", p)
    return None


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def load_ball_by_ball_normalized() -> Optional[pd.DataFrame]:
    """Normalized ball-by-ball parquet. Falls back to external parquet if local is missing."""
    p = normalized_path("ball_by_ball_normalized.parquet")
    if _exists(p):
        return pd.read_parquet(p)
    # Fallback: attempt external ball_by_ball parquet (may not exist)
    fallback = PARQUET_DIR / "ball_by_ball.parquet"
    if _exists(fallback):
        logger.warning(
            "ball_by_ball_normalized parquet not found at %s — using external fallback %s",
            p, fallback,
        )
        return pd.read_parquet(fallback)
    logger.warning("ball_by_ball_normalized parquet not found at %s (no fallback available)", p)
    return None


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def load_team_matches_for(team: str = "Janakpur Bolts") -> Optional[pd.DataFrame]:
    """All matches involving `team` (sorted by date), with `is_win` flag.

    Cached separately from `load_matches_normalized` so pages that only need
    the team's slice avoid repeating the same filter.
    """
    df = load_matches_normalized()
    if df is None:
        return None
    out = df[
        (df["team_1_name"] == team) | (df["team_2_name"] == team)
    ].sort_values("match_date").copy()
    out["is_win"] = (out["winner_name"] == team).astype(int)
    return out


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def load_bbb_with_season() -> Optional[pd.DataFrame]:
    """Ball-by-ball joined with `season` from the matches parquet.

    A common pattern across pages — caching the joined frame avoids running
    the merge on every render.
    """
    bbb = load_ball_by_ball_normalized()
    matches = load_matches_normalized()
    if bbb is None or matches is None:
        return None
    return bbb.merge(matches[["match_id", "season"]], on="match_id", how="left")


# --------------------------------------------------------------------------- #
# External Cric_Data CSVs (rosters, enriched profiles, raw NPL parquets)
# --------------------------------------------------------------------------- #

@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def load_npl_rosters() -> Optional[pd.DataFrame]:
    """League-wide roster CSV used by the opposition + team-decline pages.

    Normalises the team-name spelling drift (`Gurkhas` → `Gorkhas`) and
    pre-computes the `wickets_per_match` column the dashboard reads.
    """
    p = ROSTER_DIR / ROSTER_FILE
    if not _exists(p):
        logger.warning("Roster CSV not found at %s", p)
        return None
    df = pd.read_csv(p)
    if "team" in df.columns:
        df["team"] = df["team"].replace({"Kathmandu Gurkhas": "Kathmandu Gorkhas"})
    if {"wickets_taken", "bowling_matches"}.issubset(df.columns):
        df["wickets_per_match"] = (
            df["wickets_taken"] / df["bowling_matches"].replace(0, 1)
        )
    return df


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def load_player_profiles() -> Optional[pd.DataFrame]:
    """Enriched player profiles (age, bowling type, etc.)."""
    p = PROFILES_DIR / PROFILES_FILE
    if not _exists(p):
        logger.warning("Player profiles CSV not found at %s", p)
        return None
    return pd.read_csv(p)


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def load_raw_matches_parquet() -> Optional[pd.DataFrame]:
    """Pre-normalisation matches parquet from the external Cric_Data tree.

    Used by the legacy `services.data_source._load_from_parquet`. New code
    should prefer `load_matches_normalized()`.
    """
    p = PARQUET_DIR / "matches.parquet"
    if not _exists(p):
        return None
    return pd.read_parquet(p)


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def load_raw_player_innings_parquet() -> Optional[pd.DataFrame]:
    p = PARQUET_DIR / "player_innings.parquet"
    if not _exists(p):
        return None
    return pd.read_parquet(p)


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def load_raw_phase_summary_parquet() -> Optional[pd.DataFrame]:
    p = PARQUET_DIR / "phase_summary.parquet"
    if not _exists(p):
        return None
    return pd.read_parquet(p)


# --------------------------------------------------------------------------- #
# Generic export-folder CSV loader (analytics outputs + S3 deliverables)
# --------------------------------------------------------------------------- #

@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def load_export_csv(filename: str) -> Optional[pd.DataFrame]:
    """Load a CSV from `data/exports/`, returning None if absent."""
    p = export_path(filename)
    if not _exists(p):
        return None
    return pd.read_csv(p)


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def load_deliverable_csv(filename: str) -> Optional[pd.DataFrame]:
    """Load a CSV from `deliverables/`, returning None if absent."""
    p = deliverable_path(filename)
    if not _exists(p):
        return None
    return pd.read_csv(p)
