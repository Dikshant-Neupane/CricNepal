"""Bolts Game Plan — the decision layer of the Season 3 showcase.

Visual first, and every Janakpur match is reachable from the match
selector at the top: banner, TU venue tiles, a phase-battle table and
both squads' phase-prior tables, all computed from the project's own
files (fixtures, player priors, venue tables) for the selected match.
The default selection is the next unplayed match. Below the visuals
sit the source documents the matchday process produces — the selected
match's opponent card (data/capture/opponent_card_m<NN>_*.md, filed at
the T-48h sweep; a "pending" notice until then) and the standing
season blueprint (docs/BOLTS_BLUEPRINT.md, revised only at the
pre-registered checkpoints). No probabilities here — numbers live on
Match Predictions; this page is decisions only.

Two further layers (2026-10-26 brief integration): an approach panel
per selected opponent — how that team actually plays, computed from
the ball-by-ball dataset by scripts/build_approach_profiles.py into
data/approach/ and rebuilt by the morning ingest — and the written
team briefs (data/briefs/brief_m<NN>.md), one per played match, filed
the same evening as the scorecard capture. The profiles carry the
comparable numbers; the briefs carry the analyst's judgement.
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
    "data/approach/team_approach_profiles.csv",
    "data/approach/head_to_head.csv",
]

_CARD_RE = re.compile(r"opponent_card_m(\d+)_.*\.md$")
_BRIEF_RE = re.compile(r"brief_m(\d+)\.md$")
_PHASES = [("powerplay", "Powerplay"), ("middle", "Middle"), ("death", "Death")]

# Version of load_game_plan's return shape, folded into the cache key.
# Bump whenever the shape changes: Streamlit Cloud keeps the process
# (and st.cache_data) alive across redeploys, and the data files do
# not change when only code does — without this, a new render reads a
# stale dict cached by the old loader and crashes (the 2026-10-24
# live KeyError: data["fixtures"]).
# v3 (2026-10-26): loader also returns "approach", "h2h" and "briefs".
DATA_SCHEMA = 3


def _card_files(root: Path) -> dict:
    """match_number -> card text, from the capture directory."""
    out = {}
    cap = root / "data" / "capture"
    if cap.exists():
        for p in sorted(cap.glob("opponent_card_m*.md")):
            m = _CARD_RE.match(p.name)
            if m:
                out[int(m.group(1))] = p.read_text(encoding="utf-8")
    return out


def _brief_files(root: Path) -> dict:
    """match_number -> brief text, from data/briefs/ (one written team
    brief per played match, filed the same evening as the scorecard)."""
    out = {}
    bdir = root / "data" / "briefs"
    if bdir.exists():
        for p in sorted(bdir.glob("brief_m*.md")):
            m = _BRIEF_RE.match(p.name)
            if m:
                out[int(m.group(1))] = p.read_text(encoding="utf-8")
    return out


def _brief_title(text: str, match_number: int) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return f"Match {match_number} brief"


def _identity_tags(row: dict) -> list:
    """Plain-language identity tags derived from an approach profile —
    computed from the numbers, never hand-written, so they cannot drift
    from the table beside them."""
    tags = []
    if row["chase_win_pct"] - row["bat_first_win_pct"] >= 15:
        tags.append("chase-first side")
    elif row["bat_first_win_pct"] - row["chase_win_pct"] >= 15:
        tags.append("bat-first side")
    if row["pp_bowl_wkts_per_match"] >= 2.0:
        tags.append("powerplay-wicket attack")
    if row["pp_bat_wkts_per_match"] <= 1.6:
        tags.append("powerplay-safe batting")
    elif row["pp_bat_wkts_per_match"] >= 2.0:
        tags.append("powerplay-fragile batting")
    if row["death_bat_runs_per_match"] >= 33:
        tags.append("strong death batting")
    elif row["death_bat_runs_per_match"] <= 27:
        tags.append("weak death batting")
    if row["toss_field_pct"] >= 75:
        tags.append("fields first at the toss")
    return tags


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

    fixtures = []
    next_match_number = None
    for r in jb.itertuples():
        played = str(r.match_id) in played_ids
        if not played and next_match_number is None:
            next_match_number = int(r.match_number)
        fixtures.append({
            "match_id": r.match_id,
            "match_number": int(r.match_number),
            "match_date": r.match_date,
            "start_time_local": r.start_time_local,
            "team_1_name": r.team_1_name,
            "team_2_name": r.team_2_name,
            "opponent": (r.team_2_name if r.team_1_name == TEAM
                         else r.team_1_name),
            "slot_label": ("Day-Night" if str(r.start_time_local) >= "16:00"
                           else "Day"),
            "played": played,
        })

    cards = _card_files(root)
    briefs = _brief_files(root)

    # Approach profiles + head-to-head: computed from the ball-by-ball
    # dataset by scripts/build_approach_profiles.py (rebuilt by the
    # morning ingest). Degrade to empty when the derived files are
    # absent, like every other optional layer on this page.
    approach = {}
    profiles_path = root / "data" / "approach" / "team_approach_profiles.csv"
    if profiles_path.exists():
        prof = pd.read_csv(profiles_path)
        approach = {r.team: r._asdict() for r in prof.itertuples()}
    h2h = {}
    h2h_path = root / "data" / "approach" / "head_to_head.csv"
    if h2h_path.exists():
        hh = pd.read_csv(h2h_path)
        for r in hh.itertuples():
            h2h[(r.team_a, r.team_b)] = {
                "matches": int(r.matches),
                "a_wins": int(r.a_wins), "b_wins": int(r.b_wins)}
            h2h[(r.team_b, r.team_a)] = {
                "matches": int(r.matches),
                "a_wins": int(r.b_wins), "b_wins": int(r.a_wins)}

    # Venue tiles from the TU tables (overall + per slot).
    par = pd.read_csv(root / "data" / "venue" / "tu_par_summary.csv")
    allrow = par[par.split == "All matches"].iloc[0]
    venue = {"par_mean": float(allrow.inn1_mean),
             "par_median": float(allrow.inn1_median),
             "chase_win_pct": float(allrow.chase_win_pct),
             "by_slot": {}}
    for slot in ("Day", "Day-Night"):
        srow = par[par.split == f"{slot} slot"]
        if len(srow):
            venue["by_slot"][slot] = {
                "mean": float(srow.iloc[0].inn1_mean),
                "matches": int(srow.iloc[0].matches),
                "chase_pct": float(srow.iloc[0].chase_win_pct),
            }
    wk = pd.read_csv(root / "data" / "venue" / "tu_wickets_by_type.csv")
    known = wk.spin_wkts.sum() + wk.pace_wkts.sum()
    venue["spin_share"] = float(100 * wk.spin_wkts.sum() / known)

    # Phase-prior tables for Janakpur and every opponent it faces.
    master = pd.read_csv(root / "data" / "predictions" / "player_master.csv")
    priors = pd.read_csv(root / "data" / "predictions" / "player_priors.csv")
    merged = master.merge(priors, on="player_key", how="left",
                          suffixes=("", "_p"))
    tables = {TEAM: _team_tables(merged, TEAM)}
    for f in fixtures:
        if f["opponent"] not in tables:
            tables[f["opponent"]] = _team_tables(merged, f["opponent"])

    return {
        "blueprint": blueprint,
        "fixtures": fixtures,
        "next_match_number": next_match_number,
        "cards": cards,
        "briefs": briefs,
        "approach": approach,
        "h2h": h2h,
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
    bdir = root / "data" / "briefs"
    brief_names = tuple(sorted(p.name for p in bdir.glob("brief_m*.md"))) \
        if bdir.exists() else ()
    return (DATA_SCHEMA, tuple(parts), names, brief_names)


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


def _fixture_label(f: dict) -> str:
    date = pd.Timestamp(f["match_date"]).strftime("%a %d %b")
    state = "played" if f["played"] else "upcoming"
    return (f"Match {f['match_number']} · {date} · {f['start_time_local']} · "
            f"v {f['opponent']} ({state})")


def render_game_plan() -> None:
    data = _load_game_plan_cached(str(ROOT), _cache_key(ROOT))
    venue = data["venue"]

    st.markdown(
        """
        <div class="jb-page-head">
            <h2 class="page-title">Bolts Game Plan</h2>
            <p class="page-subtitle">What the analysis says Janakpur should do —
            pick any match, then the standing season blueprint.</p>
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
        st.warning("Results data is unavailable in this deployment, so "
                   "played/upcoming status comes from the fixture list alone.")

    fixtures = data["fixtures"]
    if not fixtures:
        st.info("No Janakpur fixtures are loaded.")
        return
    labels = [_fixture_label(f) for f in fixtures]
    default = next((i for i, f in enumerate(fixtures)
                    if f["match_number"] == data["next_match_number"]), 0)
    picked = st.selectbox("Choose a match", labels, index=default,
                          key="game_plan_match")
    sel = fixtures[labels.index(picked)]
    opp = sel["opponent"]
    slot = venue["by_slot"].get(sel["slot_label"], {})

    st.subheader(f"Match {sel['match_number']} plan — v {opp}")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Match", f"{sel['match_number']} of 32")
    c2.metric("Fixture", f"{sel['team_1_name']} v {sel['team_2_name']}")
    c3.metric("When", f"{pd.Timestamp(sel['match_date']).strftime('%a %d %b')} · "
                        f"{sel['start_time_local']}")
    c4.metric("Slot / venue", f"{sel['slot_label']} · TU Kirtipur")
    v1, v2, v3, v4 = st.columns(4)
    v1.metric("TU par (1st inn mean)", f"{venue['par_mean']:.1f}")
    if slot:
        v2.metric(f"{sel['slot_label']} slot par", f"{slot['mean']:.1f}")
    v3.metric("Chases won at TU", f"{venue['chase_win_pct']:.0f}%")
    v4.metric("Wickets to spin", f"{venue['spin_share']:.0f}%")
    st.caption(f"Par median {venue['par_median']:.1f} across our 64 matches; "
               f"slot split is indicative only ({slot.get('matches', 0)} "
               "matches). Spin share = bowler wickets with known type, S1+S2.")

    st.markdown("#### Phase battle — squad priors (top-11 means)")
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
    st.caption("Batting: higher is better. Bowling economy: lower is better. "
               "Priors = S1/S2 ball-by-ball + career T20 history, shrunk "
               "toward league average.")

    approach = data.get("approach", {})
    if opp in approach and TEAM in approach:
        jb_a, op_a = approach[TEAM], approach[opp]
        st.markdown(f"#### How {opp} play — approach since Season 1")
        rows = [
            ("Win % (all matches)", "win_pct", "{:.1f}%"),
            ("Batting first — average total", "bat_first_avg", "{:.0f}"),
            ("Batting first — win %", "bat_first_win_pct", "{:.1f}%"),
            ("Chasing — win %", "chase_win_pct", "{:.1f}%"),
            ("Powerplay batting — wickets lost / match",
             "pp_bat_wkts_per_match", "{:.2f}"),
            ("Powerplay bowling — wickets taken / match",
             "pp_bowl_wkts_per_match", "{:.2f}"),
            ("Death batting (overs 16–20) — runs / match",
             "death_bat_runs_per_match", "{:.1f}"),
            ("Totals under 120", "totals_under_120", "{:.0f}"),
            ("Bowled out", "times_all_out", "{:.0f}"),
        ]
        panel = pd.DataFrame([
            {"Measure": label, "Janakpur Bolts": fmt.format(jb_a[key]),
             opp: fmt.format(op_a[key])}
            for label, key, fmt in rows
        ])
        st.dataframe(panel, hide_index=True, width="stretch")
        tags = _identity_tags(op_a)
        h2h = data.get("h2h", {}).get((TEAM, opp))
        bits = []
        if tags:
            bits.append(f"{opp} identity: " + ", ".join(tags) + ".")
        if h2h:
            bits.append(
                f"Head-to-head since Season 1: Janakpur {h2h['a_wins']}–"
                f"{h2h['b_wins']} {opp} ({h2h['matches']} matches).")
        if bits:
            st.caption(" ".join(bits))
        st.caption("Computed from the project's ball-by-ball dataset "
                   "(Seasons 1–2; Season 3 matches join as Cricsheet "
                   "ingests them each morning). Rebuilt nightly by "
                   "scripts/build_approach_profiles.py.")

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

    card = data["cards"].get(sel["match_number"])
    if card is not None:
        with st.expander("Full opponent card (as filed)", expanded=True):
            st.markdown(card)
    else:
        st.info(f"Opponent card for Match {sel['match_number']} vs {opp} is "
                "pending — it is filed at the T-48h sweep before the match. "
                "The phase tables above are live from the priors in the "
                "meantime.")
    other_cards = [n for n in sorted(data["cards"])
                   if n != sel["match_number"]]
    if other_cards:
        st.caption("Cards also filed for match(es): "
                   + ", ".join(str(n) for n in other_cards)
                   + " — pick the match above to read them.")

    briefs = data.get("briefs", {})
    st.divider()
    st.markdown("## Team briefs — what the matches are teaching us")
    if briefs:
        st.caption("One written brief per played match, filed the same "
                   "evening as the scorecard: how each team approached "
                   "the game, which players beat or missed their priors, "
                   "and what it means for Janakpur's next fixtures.")
        for n in sorted(briefs, reverse=True):
            with st.expander(_brief_title(briefs[n], n),
                             expanded=(n == max(briefs))):
                st.markdown(briefs[n])
    else:
        st.info("No match briefs filed yet — the first is written on the "
                "evening of the season's first match.")

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
