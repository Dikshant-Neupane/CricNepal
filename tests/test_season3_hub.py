"""Season 3 Hub: the page's data assembly must reflect the locked
artefacts exactly — 28 league fixtures with all four locked series,
the opener as next match, and standings that start empty."""
import pandas as pd

from src.dashboard.page_modules.season3_hub import compute_standings, load_season3

DATA = load_season3()


def test_hub_fixtures_complete_with_locks():
    fx = DATA["fixtures"]
    league = fx[fx.stage == "League"]
    assert len(league) == 28 and len(fx) == 32  # + Q1, Eliminator, Q2, Final
    for key in ["champion", "elo", "simulator", "coach"]:
        assert league[key].notna().all(), key


def test_hub_next_match_is_the_opener():
    nm = DATA["next_match"]
    assert nm["match_number"] == 1
    assert (nm["team_1"], nm["team_2"]) == ("Lumbini Lions", "Sudurpaschim Royals")
    assert str(nm["date"].date()) == "2026-10-26" and nm["time"] == "17:00"
    # Champion lock for the opener, from the frozen log (team_1 orientation)
    assert abs(nm["champion"] - 0.4799) < 1e-9


def test_hub_scorecard_locked_not_scored_preseason():
    for label, v in DATA["scorecard"].items():
        assert v["locked"] == 28, label
        assert v["scored"] == 0, label  # no S3 results ingested yet


def test_hub_standings_start_empty():
    teams = sorted(DATA["coaches"].team)
    st_ = compute_standings(DATA["fixtures"], teams)
    assert len(st_) == 8 and st_.P.sum() == 0 and st_.Pts.sum() == 0


def test_hub_squads_and_coaches_verified_counts():
    assert len(DATA["coaches"]) == 8
    assert DATA["coaches"].head_coach.notna().all()
    assert DATA["coaches"].captain.notna().all()
    assert len(DATA["squads"]) == 143
    jb = DATA["squads"][DATA["squads"].team == "Janakpur Bolts"]
    assert len(jb) == 18


def test_hub_lock_stage_is_preseason_until_matchday_locks_exist():
    league = DATA["fixtures"][DATA["fixtures"].stage == "League"]
    assert (league.lock_stage == "Pre-season lock").all()
    assert (league.champion == league.champion_preseason).all()


def test_hub_survives_missing_results_parquet(tmp_path, monkeypatch):
    """Regression guard for the 2026-10-24 live outage: the normalized
    matches parquet existed locally but was not tracked in git, so the
    deployed hub crashed with FileNotFoundError. The loader must now
    degrade (no results) instead of raising."""
    import shutil
    from pathlib import Path

    import src.dashboard.page_modules.season3_hub as hub

    root = Path(hub.ROOT)
    for rel in hub.HUB_DATA_FILES:
        if rel.endswith("matches_normalized.parquet"):
            continue
        dest = tmp_path / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(root / rel, dest)
    data = hub.load_season3(tmp_path)
    assert data["matches_available"] is False
    assert data["results"] == {}
    assert len(data["fixtures"]) == 32


def test_hub_data_files_are_git_tracked():
    """Every file the hub reads must be in the git index — the deployed
    app clones the repo, so a local-only file is a live outage."""
    import subprocess
    from pathlib import Path

    import src.dashboard.page_modules.season3_hub as hub

    root = Path(hub.ROOT)
    for rel in hub.HUB_DATA_FILES:
        out = subprocess.run(["git", "ls-files", "--error-unmatch", rel],
                             cwd=root, capture_output=True, text=True)
        assert out.returncode == 0, f"{rel} is not tracked in git"


def test_showcase_nav_freezes_analytics_pages():
    from src.dashboard.config.nav_config import FROZEN_NAV_ITEMS, NAV_ITEMS

    live = {i["key"] for i in NAV_ITEMS}
    assert live == {"season3_hub", "match_predictions", "game_plan",
                    "player_profiles"}
    frozen = {i["key"] for i in FROZEN_NAV_ITEMS}
    assert {"dashboard", "review", "batting_analysis", "win_probability"} <= frozen
    assert not (live & frozen)


def test_app_lands_on_season3_hub():
    from pathlib import Path

    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(Path(__file__).parent.parent / "app.py"),
                           default_timeout=180)
    at.run()
    assert not at.exception
    assert at.session_state["active_page"] == "season3_hub"
