"""Team brief integration (2026-10-26, option C): computed approach
profiles + written per-match briefs on the Bolts Game Plan page.

Pins: the profile builder reproduces the hand-verified Season 1–2
approach numbers (so silent data or name drift fails loudly), team
names are canonicalised to the Season 3 fixture spellings, the loader
exposes approach/head-to-head/briefs and degrades without them, the
static derived files are git-tracked, and the page renders the new
sections under AppTest.
"""
from pathlib import Path


def _profiles():
    import pandas as pd

    import scripts.build_approach_profiles as bap

    root = Path(bap.ROOT)
    matches = pd.read_parquet(root / "data" / "final" / "parquet" / "matches.parquet")
    balls = pd.read_parquet(root / "data" / "final" / "parquet" / "ball_by_ball.parquet")
    return bap, bap.compute_profiles(matches, balls), bap.compute_head_to_head(matches)


def test_approach_profiles_match_hand_verified_values():
    _, prof, _ = _profiles()
    by_team = prof.set_index("team")
    # Hand-computed from the same dataset on 2026-10-26 (Match 1 brief).
    assert by_team.loc["Lumbini Lions", "pp_bowl_wkts_per_match"] == 2.00
    assert by_team.loc["Sudurpaschim Royals", "wins"] == 14
    assert by_team.loc["Sudurpaschim Royals", "matches"] == 18
    assert by_team.loc["Janakpur Bolts", "pp_bat_wkts_per_match"] == 2.06
    assert by_team.loc["Janakpur Bolts", "pp_bowl_wkts_per_match"] == 1.00
    # Canonical Season 3 spellings only — no historical variants leak.
    assert "Sudur Paschim Royals" not in by_team.index
    assert "Kathmandu Gurkhas" not in by_team.index
    assert len(prof) == 8


def test_head_to_head_janakpur_records():
    _, _, h2h = _profiles()
    pair = h2h[((h2h.team_a == "Janakpur Bolts") & (h2h.team_b == "Sudurpaschim Royals"))]
    assert len(pair) == 1
    row = pair.iloc[0]
    assert row.matches == 4 and row.a_wins == 1 and row.b_wins == 3


def test_loader_exposes_approach_h2h_and_briefs():
    import src.dashboard.page_modules.game_plan as gp

    data = gp.load_game_plan(Path(gp.ROOT))
    assert data["approach"]["Lumbini Lions"]["pp_bowl_wkts_per_match"] == 2.00
    assert data["h2h"][("Janakpur Bolts", "Sudurpaschim Royals")]["a_wins"] == 1
    assert 1 in data["briefs"]  # Match 1 brief filed the same evening
    assert "Sudurpaschim" in data["briefs"][1]
    assert gp.DATA_SCHEMA >= 3  # shape changed -> cache bust (24 Oct lesson)


def test_approach_files_are_git_tracked():
    import subprocess

    import src.dashboard.page_modules.game_plan as gp

    root = Path(gp.ROOT)
    for rel in ("data/approach/team_approach_profiles.csv",
                "data/approach/head_to_head.csv",
                "data/briefs/brief_m01.md"):
        out = subprocess.run(["git", "ls-files", "--error-unmatch", rel],
                             cwd=root, capture_output=True, text=True)
        assert out.returncode == 0, f"{rel} is not tracked in git"


def test_identity_tags_are_derived_from_numbers():
    import src.dashboard.page_modules.game_plan as gp

    base = {"chase_win_pct": 55.0, "bat_first_win_pct": 33.0,
            "pp_bowl_wkts_per_match": 2.0, "pp_bat_wkts_per_match": 1.9,
            "death_bat_runs_per_match": 32.0, "toss_field_pct": 87.5}
    tags = gp._identity_tags(base)
    assert "chase-first side" in tags
    assert "powerplay-wicket attack" in tags
    assert "fields first at the toss" in tags


def test_game_plan_page_renders_brief_sections():
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(Path(__file__).parent.parent / "app.py"),
                           default_timeout=180)
    at.session_state["active_page"] = "game_plan"
    at.run()
    assert not at.exception
    text = "\n".join(m.value for m in at.markdown)
    assert "approach since Season 1" in text
    assert "Team briefs" in text
    assert "Match 1 prep brief" in text  # the filed brief's own title
