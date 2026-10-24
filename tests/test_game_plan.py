"""Bolts Game Plan page: next-match card + standing blueprint.

The page reads only files the matchday process already produces. These
tests pin: the loader finds Janakpur's next fixture and its filed card,
degrades to a "pending" state when no card exists (never crashes, never
invents content), the static files it reads are git-tracked (the
2026-10-24 hub outage lesson), and the page renders under AppTest.
"""
from pathlib import Path


def test_gameplan_loader_finds_next_match_card_and_blueprint():
    import src.dashboard.page_modules.game_plan as gp

    data = gp.load_game_plan(Path(gp.ROOT))
    nxt = data["next_fixture"]
    assert nxt is not None
    assert nxt["match_id"] == "s3_2026_03"  # Janakpur opener, Tue 27 Oct
    assert data["next_card"] is not None
    assert "Karnali" in data["next_card"]
    assert data["next_card_name"] == "opponent_card_m03_karnali.md"
    assert data["blueprint"] is not None
    assert "Harmeet owns the powerplay" in data["blueprint"]


def test_gameplan_loader_degrades_without_card(tmp_path):
    """No card filed yet -> next_card is None and the fixture is still
    identified, so the page shows 'pending' instead of failing."""
    import shutil

    import src.dashboard.page_modules.game_plan as gp

    root = Path(gp.ROOT)
    for rel in ["docs/BOLTS_BLUEPRINT.md", "data/fixtures/s3_fixtures.csv",
                "data/normalized/matches_normalized.parquet"]:
        dest = tmp_path / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(root / rel, dest)
    (tmp_path / "data" / "capture").mkdir(parents=True, exist_ok=True)

    data = gp.load_game_plan(tmp_path)
    assert data["next_fixture"]["match_id"] == "s3_2026_03"
    assert data["next_card"] is None
    assert data["blueprint"] is not None


def test_gameplan_data_files_are_git_tracked():
    import subprocess

    import src.dashboard.page_modules.game_plan as gp

    root = Path(gp.ROOT)
    for rel in gp.GAMEPLAN_DATA_FILES:
        out = subprocess.run(["git", "ls-files", "--error-unmatch", rel],
                             cwd=root, capture_output=True, text=True)
        assert out.returncode == 0, f"{rel} is not tracked in git"


def test_game_plan_page_renders():
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(Path(__file__).parent.parent / "app.py"),
                           default_timeout=180)
    at.session_state["active_page"] = "game_plan"
    at.run()
    assert not at.exception
    text = "\n".join(m.value for m in at.markdown)
    assert "Bolts Game Plan" in text
    assert "Karnali" in text  # the filed Match 3 card is the top layer
