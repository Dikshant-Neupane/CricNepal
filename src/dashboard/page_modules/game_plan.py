"""Bolts Game Plan — the decision layer of the Season 3 showcase.

Two layers, both read from files the matchday process already produces:
the next-match opponent card (data/capture/opponent_card_m<NN>_*.md,
filed at the T-48h sweep) on top, and the standing season blueprint
(docs/BOLTS_BLUEPRINT.md, revised only at the pre-registered match-10 /
match-20 checkpoints) below. No probabilities here — numbers live on
Match Predictions; this page is decisions only. Nothing is generated:
if a card has not been filed, the page says so.
"""
import re
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[3]
TEAM = "Janakpur Bolts"

# Every static file load_game_plan reads. All must be tracked in git —
# the deployed app clones the repo, and a local-only file is a live
# outage (the 2026-10-24 hub lesson). Card files are dynamic and are
# handled by degradation instead (missing card -> "pending" notice).
# Guarded by test_gameplan_data_files_are_git_tracked.
GAMEPLAN_DATA_FILES = [
    "docs/BOLTS_BLUEPRINT.md",
    "data/fixtures/s3_fixtures.csv",
    "data/normalized/matches_normalized.parquet",
]

_CARD_RE = re.compile(r"opponent_card_m(\d+)_.*\.md$")


def _card_files(root: Path) -> dict:
    """match_number -> card path, from the capture directory."""
    out = {}
    cap = root / "data" / "capture"
    if cap.exists():
        for p in sorted(cap.glob("opponent_card_m*.md")):
            m = _CARD_RE.match(p.name)
            if m:
                out[int(m.group(1))] = p
    return out


def load_game_plan(root: Path = ROOT) -> dict:
    """Pure data assembly for the game plan page (unit-tested)."""
    blueprint_path = root / "docs" / "BOLTS_BLUEPRINT.md"
    blueprint = (blueprint_path.read_text(encoding="utf-8")
                 if blueprint_path.exists() else None)

    fx = pd.read_csv(root / "data" / "fixtures" / "s3_fixtures.csv",
                     parse_dates=["match_date"])
    jb = fx[(fx.team_1_name == TEAM) | (fx.team_2_name == TEAM)].copy()
    jb = jb.sort_values(["match_date", "match_number"])

    # Played Janakpur matches, from ingested results when available.
    matches_available = True
    played_ids = set()
    parquet = root / "data" / "normalized" / "matches_normalized.parquet"
    try:
        matches = pd.read_parquet(parquet)
        if "match_id" in matches.columns:
            played_ids = set(matches.match_id.astype(str))
    except Exception:
        matches_available = False

    upcoming = jb[~jb.match_id.astype(str).isin(played_ids)]
    nxt = upcoming.iloc[0] if len(upcoming) else None

    cards = _card_files(root)
    next_card = None
    next_card_name = None
    if nxt is not None:
        p = cards.get(int(nxt.match_number))
        if p is not None:
            next_card = p.read_text(encoding="utf-8")
            next_card_name = p.name
    past_cards = []
    if nxt is not None:
        for num, p in sorted(cards.items()):
            if num < int(nxt.match_number):
                past_cards.append(p.name)

    return {
        "blueprint": blueprint,
        "next_fixture": (nxt.to_dict() if nxt is not None else None),
        "next_card": next_card,
        "next_card_name": next_card_name,
        "past_cards": past_cards,
        "matches_available": matches_available,
    }


def _cache_key(root: Path):
    parts = []
    for rel in GAMEPLAN_DATA_FILES:
        p = root / rel
        parts.append((rel, p.stat().st_mtime_ns if p.exists() else 0))
    cap = root / "data" / "capture"
    names = tuple(sorted(p.name for p in cap.glob("opponent_card_m*.md"))) \
        if cap.exists() else ()
    return (tuple(parts), names)


@st.cache_data(show_spinner=False)
def _load_game_plan_cached(root_str: str, key: tuple) -> dict:
    return load_game_plan(Path(root_str))


def render_game_plan() -> None:
    data = _load_game_plan_cached(str(ROOT), _cache_key(ROOT))

    st.markdown(
        """
        <div class="jb-page-head">
            <h2 class="page-title">Bolts Game Plan</h2>
            <p class="page-subtitle">What the analysis says Janakpur should do —
            next match first, then the standing season blueprint.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption(
        "Analyst suggestions from the project's model, phase priors and venue "
        "tables — not team instructions. Probabilities live on Match "
        "Predictions; this page is decisions only."
    )
    if not data["matches_available"]:
        st.warning("Results data is unavailable in this deployment, so the "
                   "next-match card is chosen from the fixture list alone.")

    nxt = data["next_fixture"]
    st.subheader("Next match plan")
    if nxt is None:
        st.info("No unplayed Janakpur fixture remains in the loaded schedule.")
    elif data["next_card"] is not None:
        st.markdown(data["next_card"])
    else:
        opp = (nxt["team_2_name"] if nxt["team_1_name"] == TEAM
               else nxt["team_1_name"])
        st.info(
            f"Opponent card for Match {int(nxt['match_number'])} vs {opp} "
            f"({pd.Timestamp(nxt['match_date']).date()}, "
            f"{nxt['start_time_local']}) is pending — it is filed at the "
            "T-48h sweep before the match."
        )

    if data["past_cards"]:
        st.caption("Filed cards for earlier matches: "
                   + ", ".join(data["past_cards"])
                   + " (in the project repo, data/capture/).")

    st.divider()
    if data["blueprint"]:
        st.markdown(data["blueprint"])
    else:
        st.warning("The season blueprint file is unavailable in this "
                   "deployment.")
