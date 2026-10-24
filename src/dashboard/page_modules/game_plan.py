"""Bolts Game Plan — the decision layer of the Season 3 showcase.

Visual first: match banner, TU venue tiles, a phase-battle table and
both squads' phase-prior tables, all computed from the project's own
files (fixtures, player priors, venue tables). Below the visuals sit
the two source documents the matchday process produces — the next-match
opponent card (data/capture/opponent_card_m<NN>_*.md, filed at the
T-48h sweep) and the standing season blueprint (docs/BOLTS_BLUEPRINT.md,
revised only at the pre-registered checkpoints). No probabilities here —
numbers live on Match Predictions; this page is decisions only. Nothing
is generated: missing files degrade to notices, never filler.
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
    "data/predictions/player_master.csv",
    "data/predictions/player_priors.csv",
    "data/venue/tu_par_summary.csv",
    "data/venue/tu_wickets_by_type.csv",
]

_CARD_RE = re.compile(r"opponent_card_m(\d+)_.*\.md$")
_PHASES = [("powerplay", "Powerplay"), ("middle", "Middle"), ("death", "Death")]


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


def _team_tables(priors: pd.DataFrame, team: str) -> dict:
    """Phase-prior tables for one squad: top batters and bowlers, plus
    the top-11 mean phase line used in the phase battle."""
    t = priors[priors.team == team]
    bat_cols = ["canonical_name", "role", "is_overseas", "bat_index",
                "prior_bat_rpb_powerplay", "prior_bat_rpb_middle",
                "prior_bat_rpb_death"]
    bowl_cols = ["canonical_name", "role", "is_overseas", "bowl_index",
                 "prior_bowl_econ_powerplay", "prior_bowl_econ_middle",
                 "prior_bowl_econ_death"]
    bat = (t.sort_values("bat_index", ascending=False).head(7)[bat_cols]
           .rename(columns={"canonical_name": "Player", "role": "Role",
                            "is_overseas": "OS", "bat_index": "Bat idx",
                            "prior_bat_rpb_powerplay": "PP",
                            "prior_bat_rpb_middle": "Mid",
                            "prior_bat_rpb_death": "Death"}))
    bowl = (t.sort_values("bowl_index", ascending=False).head(7)[bowl_cols]
            .rename(columns={"canonical_name": "Player", "role": "Role",
                             "is_overseas": "OS", "bowl_index": "Bowl idx",
                             "prior_bowl_econ_powerplay": "PP",
                             "prior_bowl_econ_middle": "Mid",
                             "prior_bowl_econ_death": "Death"}))
    top11 = t.sort_values("bat_index", ascending=False).head(11)
    battle = {}
    for key, _ in _PHASES:
        battle[f"bat_{key}"] = float(top11[f"prior_bat_rpb_{key}"].mean())
        battle[f"bowl_{key}"] = float(top11[f"prior_bowl_econ_{key}"].mean())
    return {"bat": bat, "bowl": bowl, "battle": battle}


def load_game_plan(root: Path = ROOT) -> dict:
    """Pure data assembly for the game plan page (unit-tested)."""
    blueprint_path = root / "docs" / "BOLTS_BLUEPRINT.md"
    blueprint = (blueprint_path.read_text(encoding="utf-8")
                 if blueprint_path.exists() else None)

    fx = pd.read_csv(root / "data" / "fixtures" / "s3_fixtures.csv",
                     parse_dates=["match_date"])
    jb = fx[(fx.team_1_name == TEAM) | (fx.team_2_name == TEAM)].copy()
    jb = jb.sort_values(["match_date", "match_number"])

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
    past_cards = []
    opponent = None
    slot_label = None
    if nxt is not None:
        opponent = (nxt.team_2_name if nxt.team_1_name == TEAM
                    else nxt.team_1_name)
        slot_label = ("Day-Night" if str(nxt.start_time_local) >= "16:00"
                      else "Day")
        p = cards.get(int(nxt.match_number))
        if p is not None:
            next_card = p.read_text(encoding="utf-8")
            next_card_name = p.name
        past_cards = [p.name for num, p in sorted(cards.items())
                      if num < int(nxt.match_number)]

    # Venue tiles from the TU tables.
    venue = {}
    par = pd.read_csv(root / "data" / "venue" / "tu_par_summary.csv")
    allrow = par[par.split == "All matches"].iloc[0]
    venue["par_mean"] = float(allrow.inn1_mean)
    venue["par_median"] = float(allrow.inn1_median)
    venue["chase_win_pct"] = float(allrow.chase_win_pct)
    if slot_label:
        slot_row = par[par.split == f"{slot_label} slot"]
        if len(slot_row):
            venue["slot_mean"] = float(slot_row.iloc[0].inn1_mean)
            venue["slot_matches"] = int(slot_row.iloc[0].matches)
            venue["slot_chase_pct"] = float(slot_row.iloc[0].chase_win_pct)
    wk = pd.read_csv(root / "data" / "venue" / "tu_wickets_by_type.csv")
    known = wk.spin_wkts.sum() + wk.pace_wkts.sum()
    venue["spin_share"] = float(100 * wk.spin_wkts.sum() / known)

    # Phase-prior tables for both squads.
    master = pd.read_csv(root / "data" / "predictions" / "player_master.csv")
    priors = pd.read_csv(root / "data" / "predictions" / "player_priors.csv")
    merged = master.merge(priors, on="player_key", how="left",
                          suffixes=("", "_p"))
    tables = {TEAM: _team_tables(merged, TEAM)}
    if opponent:
        tables[opponent] = _team_tables(merged, opponent)

    return {
        "blueprint": blueprint,
        "next_fixture": (nxt.to_dict() if nxt is not None else None),
        "opponent": opponent,
        "slot_label": slot_label,
        "next_card": next_card,
        "next_card_name": next_card_name,
        "past_cards": past_cards,
        "matches_available": matches_available,
        "venue": venue,
        "tables": tables,
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


def _fmt_table(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["OS"] = out["OS"].map(lambda v: "OS" if v is True else "")
    for c in out.columns:
        if c not in ("Player", "Role", "OS"):
            out[c] = out[c].map(lambda v: f"{v:.2f}")
    return out


def _blueprint_sections(md: str):
    """Split the blueprint into (intro, [(heading, body), ...])."""
    parts = re.split(r"^## ", md, flags=re.M)
    intro = parts[0]
    intro = intro.split("\n", 1)[1] if intro.startswith("# ") else intro
    sections = []
    for chunk in parts[1:]:
        head, _, body = chunk.partition("\n")
        sections.append((head.strip(), body.strip()))
    return intro.strip(), sections


def render_game_plan() -> None:
    data = _load_game_plan_cached(str(ROOT), _cache_key(ROOT))
    nxt = data["next_fixture"]
    venue = data["venue"]
    opp = data["opponent"]

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

    # ---- Next match banner + venue tiles ----
    st.subheader("Next match plan")
    if nxt is None:
        st.info("No unplayed Janakpur fixture remains in the loaded schedule.")
    else:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Match", f"{int(nxt['match_number'])} of 32")
        c2.metric("Fixture", f"{nxt['team_1_name']} v {nxt['team_2_name']}")
        c3.metric("When", f"{pd.Timestamp(nxt['match_date']).strftime('%a %d %b')} · "
                            f"{nxt['start_time_local']}")
        c4.metric("Slot / venue", f"{data['slot_label']} · TU Kirtipur")
        v1, v2, v3, v4 = st.columns(4)
        v1.metric("TU par (1st inn mean)", f"{venue['par_mean']:.1f}")
        if "slot_mean" in venue:
            v2.metric(f"{data['slot_label']} slot par",
                      f"{venue['slot_mean']:.1f}")
        v3.metric("Chases won at TU", f"{venue['chase_win_pct']:.0f}%")
        v4.metric("Wickets to spin", f"{venue['spin_share']:.0f}%")
        st.caption(f"Par median {venue['par_median']:.1f} across our 64 "
                   "matches; slot split is indicative only "
                   f"({venue.get('slot_matches', 0)} matches). Spin share = "
                   "bowler wickets with known type, S1+S2.")

        # ---- Phase battle ----
        st.markdown(f"#### Phase battle — squad priors (top-11 means)")
        jb_b = data["tables"][TEAM]["battle"]
        op_b = data["tables"][opp]["battle"]
        battle = pd.DataFrame([
            {"Phase": label,
             "Janakpur bat (runs/ball)": round(jb_b[f"bat_{k}"], 2),
             f"{opp} bat (runs/ball)": round(op_b[f"bat_{k}"], 2),
             "Janakpur bowl (econ)": round(jb_b[f"bowl_{k}"], 2),
             f"{opp} bowl (econ)": round(op_b[f"bowl_{k}"], 2)}
            for k, label in _PHASES
        ])
        st.dataframe(battle, hide_index=True, width="stretch")
        st.caption("Batting: higher is better. Bowling economy: lower is "
                   "better. Priors = S1/S2 ball-by-ball + career T20 history, "
                   "shrunk toward league average.")

        # ---- Squad phase tables ----
        for team_name in (TEAM, opp):
            t = data["tables"][team_name]
            st.markdown(f"#### {team_name} — phase priors")
            b1, b2 = st.columns(2)
            with b1:
                st.markdown("**Batting** (runs per ball by phase)")
                st.dataframe(_fmt_table(t["bat"]), hide_index=True,
                             width="stretch")
            with b2:
                st.markdown("**Bowling** (economy by phase)")
                st.dataframe(_fmt_table(t["bowl"]), hide_index=True,
                             width="stretch")

        # ---- The filed card ----
        if data["next_card"] is not None:
            with st.expander("Full opponent card (as filed)", expanded=True):
                st.markdown(data["next_card"])
        else:
            st.info(
                f"Opponent card for Match {int(nxt['match_number'])} vs {opp} "
                f"is pending — it is filed at the T-48h sweep before the match."
            )
    if data["past_cards"]:
        st.caption("Filed cards for earlier matches: "
                   + ", ".join(data["past_cards"])
                   + " (in the project repo, data/capture/).")

    # ---- Blueprint, sectioned ----
    st.divider()
    if data["blueprint"]:
        intro, sections = _blueprint_sections(data["blueprint"])
        st.markdown("## Janakpur Bolts — Season 3 blueprint")
        st.markdown(intro)
        for i in range(0, len(sections), 2):
            cols = st.columns(2)
            for col, (head, body) in zip(cols, sections[i:i + 2]):
                with col:
                    st.markdown(f"### {head}")
                    st.markdown(body)
    else:
        st.warning("The season blueprint file is unavailable in this "
                   "deployment.")
