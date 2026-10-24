"""Bolts Game Plan page: match selector, next-match card, blueprint.

The page reads only files the matchday process already produces. These
tests pin: the loader lists every Janakpur fixture with its opponent
and filed cards keyed by match number, degrades when no card exists
(never crashes, never invents content), the visual data (venue tiles,
phase tables) comes from the project's own files, the static files it
reads are git-tracked (the 2026-10-24 hub outage lesson), and the page
renders under AppTest with the selector defaulting to the next match.
"""
from pathlib import Path


def test_gameplan_loader_fixtures_cards_blueprint():
    import src.dashboard.page_modules.game_plan as gp

    data = gp.load_game_plan(Path(gp.ROOT))
    assert len(data["fixtures"]) == 7  # Janakpur's league fixtures
    assert data["next_match_number"] == 3  # the opener, Tue 27 Oct
    first = data["fixtures"][0]
    assert first["match_id"] == "s3_2026_03"
    assert first["opponent"] == "Karnali Yaks"
    assert first["slot_label"] == "Day-Night"  # 17:00 start
    assert "Karnali" in data["cards"][3]
    assert data["blueprint"] is not None
    assert "Harmeet owns the powerplay" in data["blueprint"]
    opponents = {f["opponent"] for f in data["fixtures"]}
    assert opponents <= set(data["tables"])  # a table per opponent


def test_gameplan_loader_visual_data():
    """The visual layer: venue tiles from the TU tables and phase-prior
    tables for both squads, from the project's own files."""
    import src.dashboard.page_modules.game_plan as gp

    data = gp.load_game_plan(Path(gp.ROOT))
    venue = data["venue"]
    assert venue["par_mean"] == 147.5
    dn = venue["by_slot"]["Day-Night"]
    assert dn["mean"] == 160.3 and dn["matches"] == 9
    assert 55.0 < venue["spin_share"] < 58.0

    jb = data["tables"]["Janakpur Bolts"]
    assert jb["bat"].iloc[0]["Player"] == "Jimmy Neesham"  # top bat index
    assert jb["bowl"].iloc[0]["Player"] == "Harmeet Singh"  # top bowl index
    kar = data["tables"]["Karnali Yaks"]
    assert kar["bat"].iloc[0]["Player"] == "Sahibzada Farhan"
    battle = jb["battle"]
    assert 1.3 < battle["bat_death"] < 1.6  # top-11 mean, sane range
    assert 6.0 < battle["bowl_powerplay"] < 7.5


def test_gameplan_loader_degrades_without_card(tmp_path):
    """No card filed yet -> cards is empty and the fixtures are still
    identified, so the page shows 'pending' instead of failing."""
    import shutil

    import src.dashboard.page_modules.game_plan as gp

    root = Path(gp.ROOT)
    for rel in gp.GAMEPLAN_DATA_FILES:
        dest = tmp_path / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(root / rel, dest)
    (tmp_path / "data" / "capture").mkdir(parents=True, exist_ok=True)

    data = gp.load_game_plan(tmp_path)
    assert data["cards"] == {}
    assert data["next_match_number"] == 3
    assert data["blueprint"] is not None


def test_gameplan_data_files_are_git_tracked():
    import subprocess

    import src.dashboard.page_modules.game_plan as gp

    root = Path(gp.ROOT)
    for rel in gp.GAMEPLAN_DATA_FILES:
        out = subprocess.run(["git", "ls-files", "--error-unmatch", rel],
                             cwd=root, capture_output=True, text=True)
        assert out.returncode == 0, f"{rel} is not tracked in git"


def test_app_header_has_no_date_pill():
    app_src = (Path(__file__).parent.parent / "src" / "dashboard"
               / "app.py").read_text()
    assert "jb-date-pill" not in app_src
    assert "datetime" not in app_src


def test_game_plan_page_renders():
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(Path(__file__).parent.parent / "app.py"),
                           default_timeout=180)
    at.session_state["active_page"] = "game_plan"
    at.run()
    assert not at.exception
    text = "\n".join(m.value for m in at.markdown)
    assert "Bolts Game Plan" in text
    assert "Phase battle" in text
    assert "Karnali" in text  # default selection: the next match (M3)
    assert len(at.dataframe) >= 5  # battle + 2x2 squad phase tables
    assert len(at.selectbox) >= 1  # the match selector
